# -*- coding: utf-8 -*-
"""فحوص OCR للمانوالات الممسوحة (بمحرك مزيّف — بدون RapidOCR حقيقي أثناء الفحوص)."""
import io

import fitz  # PyMuPDF
from PIL import Image, ImageDraw

from app.services import ocr as ocr_service


def make_mixed_pdf_bytes(ocr_text: str = "PUMP BEARING GREASE CHECK EVERY 2000 HOURS") -> bytes:
    """PDF من صفحتين: أولى بطبقة نص، ثانية صورة فقط (تحاكي ملفًا ممسوحًا)."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "1. Maintenance", fontsize=13)
    p1.insert_text((72, 110), "Inspect bearing every 2,000 operating hours.", fontsize=11)

    img = Image.new("RGB", (900, 200), "white")
    d = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 34)
    except Exception:
        font = None
    d.text((30, 70), ocr_text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    p2 = doc.new_page()
    p2.insert_image(fitz.Rect(40, 40, 560, 240), stream=buf.getvalue())

    data = doc.tobytes()
    doc.close()
    return data


def _upload(client, pdf, title="Scanned O&M"):
    return client.post(
        "/api/manuals",
        files={"file": ("scanned.pdf", pdf, "application/pdf")},
        data={"title": title, "manufacturer": "Grundfos", "model": "ABC-500"},
    )


def test_scanned_pdf_without_engine(client, monkeypatch):
    """بدون محرك OCR: الصفحة الممسوحة تُبلَّغ كممسوحة بلا نص."""
    monkeypatch.setattr(ocr_service, "is_available", lambda: False)
    r = _upload(client, make_mixed_pdf_bytes())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages"] == 2
    assert body["ocr_pages"] == 0
    assert body["scanned_pages"] == [2]


def test_scanned_pdf_with_fake_ocr(client, monkeypatch):
    """مع محرك (مزيّف): نص الـOCR يدخل الفهرس ويظبط البحث."""
    monkeypatch.setattr(ocr_service, "is_available", lambda: True)
    monkeypatch.setattr(
        ocr_service,
        "run_ocr",
        lambda png: ("PUMP BEARING GREASE CHECK EVERY 2000 HOURS", 0.93),
    )
    r = _upload(client, make_mixed_pdf_bytes())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages"] == 2
    assert body["ocr_pages"] == 1
    assert body["scanned_pages"] == []
    mid = body["manual_id"]

    hits = client.get("/api/manuals/search", params={"q": "grease check"}).json()
    assert len(hits) >= 1
    assert hits[0]["manual_id"] == mid
    assert hits[0]["page"] == 2

    # القائمة تعرض عداد صفحات الـOCR
    listed = client.get("/api/manuals").json()
    assert listed[0]["ocr_pages"] == 1

    # التفاصيل كذلك
    det = client.get("/api/manuals/%d" % mid).json()
    assert det["manual"]["ocr_pages"] == 1


def test_reocr_endpoint(client, monkeypatch):
    """رفع بدون محرك ثم إعادة OCR بعد تفعيله — عبر endpoint."""
    monkeypatch.setattr(ocr_service, "is_available", lambda: False)
    r = _upload(client, make_mixed_pdf_bytes())
    mid = r.json()["manual_id"]
    assert r.json()["ocr_pages"] == 0

    monkeypatch.setattr(ocr_service, "is_available", lambda: True)
    monkeypatch.setattr(
        ocr_service,
        "run_ocr",
        lambda png: ("SEAL REPLACEMENT EVERY 4000 HOURS", 0.9),
    )
    r2 = client.post("/api/manuals/%d/ocr" % mid)
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["ocr_pages"] == 1
    assert body["chunks"] >= 1

    hits = client.get("/api/manuals/search", params={"q": "seal replacement"}).json()
    assert len(hits) >= 1
    assert hits[0]["manual_id"] == mid
    assert hits[0]["page"] == 2


def test_reocr_unavailable_returns_503(client, monkeypatch):
    monkeypatch.setattr(ocr_service, "is_available", lambda: False)
    r = _upload(client, make_mixed_pdf_bytes())
    mid = r.json()["manual_id"]
    r2 = client.post("/api/manuals/%d/ocr" % mid)
    assert r2.status_code == 503
