# -*- coding: utf-8 -*-
"""Phase 3 — الـManuals: رفع PDF → استخراج نص (مع OCR للصفحات الممسوحة) → أقسام → تقطيع → FTS5.

راجع ARCHITECTURE.md §6 و§18 (جداول manual / manual_section / manual_chunk).
"""
import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app import config
from app.db.models import Manual, ManualChunk, ManualSection
from app.services import ocr as ocr_service

MANUALS_DIR = config.DATA_DIR / "manuals"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
SPARSE_TEXT_MIN = 15  # أقل من هذا العدد من الأحرف = صفحة بدون طبقة نص (ممسوحة)
OCR_RENDER_DPI = 200

FTS_TABLE_DDL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS manual_chunk_fts "
    "USING fts5(text, manual_id UNINDEXED, tokenize='unicode61')"
)

_HEADING_WORDS = (
    "chapter", "section", "maintenance", "installation", "operation",
    "troubleshooting", "specifications", "safety", "introduction",
    "overview", "general", "parts", "warranty", "lubrication", "service",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 90:
        return False
    if re.match(r"^\d+(\.\d+)*[.)]?\s+\S", s):
        return True
    first = s.split(" ", 1)[0].strip(":.،- ").lower()
    if first in _HEADING_WORDS and len(s) <= 60:
        return True
    if s.isupper() and 3 <= len(s) <= 60:
        return True
    return False


def extract_pages(pdf_path, *, enable_ocr: bool = True) -> tuple:
    """استخراج نص كل صفحة عبر PyMuPDF، مع OCR احتياطي للصفحات الممسوحة.

    يرجّع (قائمة الصفحات، عدد الصفحات المستخرجة عبر OCR).
    """
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    try:
        pages = []
        ocr_pages = 0
        use_ocr = bool(enable_ocr) and ocr_service.is_available()
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            if len(text.strip()) < SPARSE_TEXT_MIN and use_ocr:
                try:
                    zoom = OCR_RENDER_DPI / 72.0
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                    ocr_text, _conf = ocr_service.run_ocr(pix.tobytes("png"))
                    if len((ocr_text or "").strip()) >= SPARSE_TEXT_MIN:
                        text = ocr_text
                        ocr_pages += 1
                except Exception:  # noqa: BLE001 — فشل صفحة واحدة لا يفشل الرفع
                    pass
            pages.append({"page": i, "text": text})
        return pages, ocr_pages
    finally:
        doc.close()


def _sections_from_pages(pages: list) -> list:
    sections = []
    current = None
    for p in pages:
        for line in (p["text"] or "").splitlines():
            if _is_heading(line):
                current = {
                    "section_title": line.strip()[:120],
                    "page_start": p["page"],
                    "page_end": p["page"],
                    "lines": [],
                }
                sections.append(current)
            if current is not None:
                current["lines"].append(line)
                current["page_end"] = p["page"]
    cleaned = []
    for s in sections:
        text = "\n".join(s["lines"]).strip()
        if text:
            cleaned.append({
                "section_title": s["section_title"],
                "page_start": s["page_start"],
                "page_end": s["page_end"],
                "text": text,
            })
    if not cleaned:
        body = "\n".join(p["text"] for p in pages).strip()
        if body:
            cleaned = [{
                "section_title": "Full Document",
                "page_start": pages[0]["page"],
                "page_end": pages[-1]["page"],
                "text": body,
            }]
    return cleaned


def _chunk_text(text_block: str) -> list:
    text_block = (text_block or "").strip()
    if not text_block:
        return []
    chunks = []
    start = 0
    n = len(text_block)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        if end < n:
            cut = text_block.rfind("\n", start + CHUNK_SIZE // 2, end)
            if cut == -1:
                cut = text_block.rfind(" ", start + CHUNK_SIZE // 2, end)
            if cut != -1:
                end = cut
        piece = text_block[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _section_title_for_page(sections: list, page: int):
    for s in sections:
        if s["page_start"] <= page <= (s["page_end"] or s["page_start"]):
            return s["section_title"]
    return None


def ensure_fts(db: Session) -> None:
    db.execute(sql_text(FTS_TABLE_DDL))


def _process_manual(db: Session, manual: Manual) -> dict:
    """(يعيد) بناء الأقسام والمقاطع وفهرس FTS لملف مانوال — يستخدمه الرفع وإعادة الـOCR."""
    pages, ocr_pages = extract_pages(manual.file_path)
    sections = _sections_from_pages(pages)
    manual.ocr_pages = ocr_pages

    for s in sections:
        db.add(ManualSection(
            manual_id=manual.id,
            page_start=s["page_start"],
            page_end=s["page_end"],
            section_title=s["section_title"],
            text=s["text"],
        ))

    chunk_count = 0
    for p in pages:
        section_title = _section_title_for_page(sections, p["page"])
        for idx, chunk in enumerate(_chunk_text(p["text"])):
            db.add(ManualChunk(
                manual_id=manual.id,
                page=p["page"],
                section_title=section_title,
                chunk_index=idx,
                text=chunk,
            ))
            chunk_count += 1
    db.flush()

    ensure_fts(db)
    db.execute(
        sql_text(
            "INSERT INTO manual_chunk_fts(rowid, text, manual_id) "
            "SELECT id, text, manual_id FROM manual_chunk WHERE manual_id = :mid"
        ),
        {"mid": manual.id},
    )

    scanned_pages = [p["page"] for p in pages if len((p["text"] or "").strip()) < SPARSE_TEXT_MIN]
    return {
        "pages": len(pages),
        "sections": len(sections),
        "chunks": chunk_count,
        "ocr_pages": ocr_pages,
        "scanned_pages": scanned_pages,
    }


def ingest_manual(
    db: Session,
    *,
    title: str,
    manufacturer: str = "",
    model: str = "",
    equipment_kind: str = "",
    revision: str = "",
    filename: str = "manual.pdf",
    file_bytes: bytes,
) -> dict:
    sha = _sha256(file_bytes)
    existing = db.query(Manual).filter(Manual.sha256 == sha).first()
    if existing is not None:
        return {"status": "DUPLICATE", "manual_id": existing.id, "title": existing.title}

    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename or "manual.pdf")
    dest = MANUALS_DIR / ("%s_%s" % (sha[:12], safe_name))
    dest.write_bytes(file_bytes)

    manual = Manual(
        title=title,
        manufacturer=manufacturer or None,
        model=model or None,
        equipment_kind=equipment_kind or None,
        revision=revision or None,
        file_path=str(dest),
        sha256=sha,
        uploaded_at=_now(),
        status="READY",
    )
    db.add(manual)
    db.flush()

    counts = _process_manual(db, manual)
    db.commit()

    return {
        "status": "READY",
        "manual_id": manual.id,
        "pages": counts["pages"],
        "sections": counts["sections"],
        "chunks": counts["chunks"],
        "ocr_pages": counts["ocr_pages"],
        "scanned_pages": counts["scanned_pages"],
        "ocr_note": (
            "بعض الصفحات بلا نص حتى بعد OCR — جودة مسح منخفضة"
            if counts["scanned_pages"]
            else None
        ),
    }


def reocr_manual(db: Session, manual_id: int) -> dict:
    """يعيد استخراج المانوال مع OCR (مفيد بعد تثبيت/تحديث المحرك أو لجودة مسح أفضل)."""
    if not ocr_service.is_available():
        raise ocr_service.OcrUnavailable("محرك OCR غير متاح على الخادم")

    manual = db.get(Manual, manual_id)
    if manual is None:
        raise LookupError("manual not found")

    # مسح المحتوى القديم (المقاطع + فهرس FTS) وإعادة البناء
    ensure_fts(db)
    db.execute(
        sql_text("DELETE FROM manual_chunk_fts WHERE manual_id = :mid"), {"mid": manual_id}
    )
    db.query(ManualChunk).filter(ManualChunk.manual_id == manual_id).delete()
    db.query(ManualSection).filter(ManualSection.manual_id == manual_id).delete()
    db.flush()

    counts = _process_manual(db, manual)
    db.commit()
    return {"status": "READY", "manual_id": manual_id, **counts}


def _fts_query(raw: str) -> str:
    tokens = re.findall(r"[\w\u0600-\u06FF]+", raw or "")
    if not tokens:
        return ""
    return " ".join('"%s"' % t for t in tokens)


def search_chunks(db: Session, query: str, limit: int = 10) -> list:
    q = _fts_query(query)
    if not q:
        return []
    rows = db.execute(
        sql_text(
            "SELECT rowid AS chunk_id, manual_id, "
            "       snippet(manual_chunk_fts, 0, '[', ']', '…', 14) AS snippet, "
            "       bm25(manual_chunk_fts) AS rank "
            "FROM manual_chunk_fts WHERE manual_chunk_fts MATCH :q "
            "ORDER BY rank LIMIT :lim"
        ),
        {"q": q, "lim": limit},
    ).fetchall()
    out = []
    for r in rows:
        chunk = db.get(ManualChunk, r.chunk_id)
        if chunk is None:
            continue
        manual = db.get(Manual, r.manual_id)
        out.append({
            "chunk_id": chunk.id,
            "manual_id": manual.id if manual else None,
            "manual_title": manual.title if manual else None,
            "page": chunk.page,
            "section": chunk.section_title,
            "snippet": r.snippet,
            "text": (chunk.text or "")[:400],
            "score": float(r.rank) if r.rank is not None else None,
        })
    return out
