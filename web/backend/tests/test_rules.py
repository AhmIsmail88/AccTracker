# -*- coding: utf-8 -*-
"""فحوص استخراج قواعد الصيانة (LLM مزيّف — بدون شبكة)."""
import fitz

from app.services import rules as rules_service
from app.services.llm import LLMUnavailable


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


class FakeLLM:
    model = "fake-model"

    def __init__(self):
        self.prompts = []

    def generate_json(self, *, system, prompt):
        self.prompts.append(prompt)
        return {"rules": [
            {"maintenance_type": "INSPECTION", "interval_hours": 2000, "interval_days": None,
             "threshold_value": None, "threshold_unit": None,
             "description": "Inspect bearing every 2000 operating hours", "confidence": "high"},
            {"maintenance_type": "LUBRICATION", "interval_hours": 4000, "interval_days": None,
             "threshold_value": None, "threshold_unit": None,
             "description": "Replace lubricant every 4000 operating hours", "confidence": "high"},
        ]}


def _upload_pdf(client):
    resp = client.post(
        "/api/manuals",
        files={"file": ("pump_manual.pdf", make_pdf_bytes(), "application/pdf")},
        data={"title": "Pump O&M", "manufacturer": "Grundfos", "model": "ABC-500",
              "equipment_kind": "MAIN_PUMP", "revision": "Rev.03"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["manual_id"]


def test_extract_rules_with_fake_llm(client, monkeypatch):
    manual_id = _upload_pdf(client)
    fake = FakeLLM()
    monkeypatch.setattr(rules_service, "get_client", lambda: fake)

    resp = client.post("/api/manuals/%d/extract-rules" % manual_id, params={"limit_chunks": 10})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["rules_created"] == 2
    assert body["candidates"] >= 2
    assert len(fake.prompts) >= 2  # نداء لكل مقطع مرشح
    assert "MAIN_PUMP" in fake.prompts[0]

    # المصدر محفوظ (صفحة + قسم) + حالة DRAFT + بيانات المانوال
    rules = client.get("/api/manuals/%d/rules" % manual_id).json()
    assert len(rules) == 2
    by_type = {r["maintenance_type"]: r for r in rules}
    inspection = by_type["INSPECTION"]
    assert inspection["source_page"] == 1
    assert inspection["source_section"]
    assert inspection["status"] == "DRAFT"
    assert inspection["equipment_kind"] == "MAIN_PUMP"
    assert inspection["model"] == "ABC-500"
    assert inspection["manual_id"] == manual_id

    # إعادة التشغيل لا تكرّر (dedupe)
    resp2 = client.post("/api/manuals/%d/extract-rules" % manual_id)
    assert resp2.json()["rules_created"] == 0

    # اعتماد / رفض / تعديل
    rule_id = inspection["id"]
    resp3 = client.patch("/api/rules/%d" % rule_id, json={"status": "APPROVED"})
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "APPROVED"
    resp4 = client.patch("/api/rules/%d" % rule_id, json={"status": "WHATEVER"})
    assert resp4.status_code == 422

    # الفلاتر
    approved = client.get("/api/rules", params={"status": "APPROVED"}).json()
    assert len(approved) == 1
    every_rule = client.get("/api/rules").json()
    assert len(every_rule) == 2
    by_manual = client.get("/api/rules", params={"manual_id": manual_id}).json()
    assert len(by_manual) == 2


def test_extract_rules_llm_down(client, monkeypatch):
    manual_id = _upload_pdf(client)

    def boom():
        raise LLMUnavailable("ollama down")

    monkeypatch.setattr(rules_service, "get_client", boom)
    resp = client.post("/api/manuals/%d/extract-rules" % manual_id)
    assert resp.status_code == 503

    # مانوال غير موجود → 404 (قبل أي نداء للنموذج)
    resp404 = client.post("/api/manuals/99999/extract-rules")
    assert resp404.status_code == 404
