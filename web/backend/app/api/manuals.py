# -*- coding: utf-8 -*-
"""API الـManuals (Phase 3): رفع + قائمة + تفاصيل + مقاطع + بحث + استخراج قواعد."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Manual, MaintenanceRule, ManualChunk, ManualSection
from app.services.manuals import ingest_manual, search_chunks
from app.services.rules import LLMUnavailable, extract_rules, rule_to_dict

router = APIRouter(prefix="/api/manuals", tags=["manuals"])


@router.post("")
async def upload_manual(
    file: UploadFile = File(...),
    title: str = Form(...),
    manufacturer: str = Form(""),
    model: str = Form(""),
    equipment_kind: str = Form(""),
    revision: str = Form(""),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    if not data[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="not a PDF file")
    return ingest_manual(
        db,
        title=title.strip(),
        manufacturer=manufacturer.strip(),
        model=model.strip(),
        equipment_kind=equipment_kind.strip(),
        revision=revision.strip(),
        filename=file.filename or "manual.pdf",
        file_bytes=data,
    )


@router.get("")
def list_manuals(db: Session = Depends(get_db)):
    items = db.query(Manual).order_by(Manual.id.desc()).all()
    counts = dict(
        db.query(ManualChunk.manual_id, func.count(ManualChunk.id))
        .group_by(ManualChunk.manual_id)
        .all()
    )
    return [{
        "id": m.id,
        "title": m.title,
        "manufacturer": m.manufacturer,
        "model": m.model,
        "equipment_kind": m.equipment_kind,
        "revision": m.revision,
        "status": m.status,
        "uploaded_at": m.uploaded_at,
        "chunks": counts.get(m.id, 0),
    } for m in items]


@router.get("/search")
def search(q: str, limit: int = 10, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 50))
    return search_chunks(db, q, safe_limit)


@router.post("/{manual_id}/extract-rules")
def extract_manual_rules(manual_id: int, limit_chunks: int = 25, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit_chunks, 100))
    try:
        return extract_rules(db, manual_id, limit_chunks=safe_limit)
    except LookupError:
        raise HTTPException(status_code=404, detail="manual not found")
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{manual_id}/rules")
def get_manual_rules(manual_id: int, db: Session = Depends(get_db)):
    manual = db.get(Manual, manual_id)
    if manual is None:
        raise HTTPException(status_code=404, detail="manual not found")
    rows = (
        db.query(MaintenanceRule)
        .filter(MaintenanceRule.manual_id == manual_id)
        .order_by(MaintenanceRule.id)
        .all()
    )
    return [rule_to_dict(row) for row in rows]


@router.get("/{manual_id}")
def get_manual(manual_id: int, db: Session = Depends(get_db)):
    manual = db.get(Manual, manual_id)
    if manual is None:
        raise HTTPException(status_code=404, detail="manual not found")
    sections = (
        db.query(ManualSection)
        .filter(ManualSection.manual_id == manual_id)
        .order_by(ManualSection.page_start)
        .all()
    )
    chunk_count = (
        db.query(func.count(ManualChunk.id))
        .filter(ManualChunk.manual_id == manual_id)
        .scalar()
        or 0
    )
    return {
        "manual": {
            "id": manual.id,
            "title": manual.title,
            "manufacturer": manual.manufacturer,
            "model": manual.model,
            "equipment_kind": manual.equipment_kind,
            "revision": manual.revision,
            "status": manual.status,
            "uploaded_at": manual.uploaded_at,
        },
        "chunks": chunk_count,
        "sections": [{
            "id": s.id,
            "section_title": s.section_title,
            "page_start": s.page_start,
            "page_end": s.page_end,
            "chars": len(s.text or ""),
        } for s in sections],
    }


@router.get("/{manual_id}/chunks")
def get_chunks(manual_id: int, page: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(ManualChunk).filter(ManualChunk.manual_id == manual_id)
    if page is not None:
        q = q.filter(ManualChunk.page == page)
    rows = q.order_by(ManualChunk.page, ManualChunk.chunk_index).limit(200).all()
    return [{
        "id": c.id,
        "page": c.page,
        "section": c.section_title,
        "chunk_index": c.chunk_index,
        "text": c.text,
    } for c in rows]
