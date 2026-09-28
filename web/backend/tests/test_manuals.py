# -*- coding: utf-8 -*-
"""فحوص الـManuals: رفع PDF → استخراج/تقسيم/تقطيع → بحث FTS."""
import fitz  # PyMuPDF


def make_pdf_bytes() -> bytes:
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Grundfos ABC-500 Installation and Maintenance Manual", fontsize=13)
    page1.insert_text((72, 120), "1. Maintenance")
    page1.insert_text((72, 150), "Inspect bearing every 2,000 operating hours.")
    page1.insert_text((72, 180), "Replace lubricant every 4,000 operating hours.")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "2. Troubleshooting")
    page2.insert_text((72, 120), "If vibration exceeds 4.5 mm/s check the mechanical seal.")
    data = doc.tobytes()
    doc.close()
    return data


def test_manual_upload_process_and_search(client):
    pdf = make_pdf_bytes()
    r = client.post(
        "/api/manuals",
        files={"file": ("manual.pdf", pdf, "application/pdf")},
        data={
            "title": "ABC-500 O&M",
            "manufacturer": "Grundfos",
            "model": "ABC-500",
            "equipment_kind": "MAIN_PUMP",
            "revision": "Rev.03",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "READY"
    manual_id = body["manual_id"]
    assert body["pages"] == 2
    assert body["chunks"] >= 2
    assert body["sections"] >= 2

    # منع التكرار بنفس البصمة
    r2 = client.post(
        "/api/manuals",
        files={"file": ("manual.pdf", pdf, "application/pdf")},
        data={"title": "ABC-500 O&M (copy)"},
    )
    assert r2.json()["status"] == "DUPLICATE"

    # القائمة
    listed = client.get("/api/manuals").json()
    assert len(listed) == 1
    assert listed[0]["model"] == "ABC-500"

    # التفاصيل
    det = client.get("/api/manuals/%d" % manual_id).json()
    assert det["manual"]["revision"] == "Rev.03"
    assert det["chunks"] >= 2
    assert len(det["sections"]) >= 2

    # البحث
    res = client.get("/api/manuals/search", params={"q": "bearing"}).json()
    assert len(res) >= 1
    assert res[0]["page"] == 1
    assert "bearing" in (res[0]["snippet"] + res[0]["text"]).lower()
    assert res[0]["manual_title"] == "ABC-500 O&M"

    res2 = client.get("/api/manuals/search", params={"q": "mechanical seal"}).json()
    assert len(res2) >= 1
    assert res2[0]["page"] == 2

    # غير PDF
    r3 = client.post(
        "/api/manuals",
        files={"file": ("bad.txt", b"hello", "text/plain")},
        data={"title": "bad"},
    )
    assert r3.status_code == 422
