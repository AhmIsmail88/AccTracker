# -*- coding: utf-8 -*-
"""فحوص تحليل الصيانة بالـAI (§11) — بمزود مزيّف، مع فحص الأدلة (§16)."""
import fitz

from app.services import ai_analysis as ai_service
from app.services.llm import LLMUnavailable

SAMPLES_MANUAL_PAGES = 2


def make_pdf_bytes() -> bytes:
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Grundfos ABC-500 Installation and Maintenance Manual", fontsize=13)
    page1.insert_text((72, 120), "1. Maintenance")
    page1.insert_text((72, 150), "Inspect bearing every 2,000 operating hours.")
    data = doc.tobytes()
    doc.close()
    return data


def _import_sample(client):
    import os

    from app.config import CONTRACT_DIR

    with open(os.path.join(str(CONTRACT_DIR), "samples", "valid_package.zip"), "rb") as f:
        data = f.read()
    r = client.post("/api/imports", files={"file": ("valid_package.zip", data, "application/zip")})
    assert r.status_code == 200, r.text


def _upload_manual(client) -> int:
    resp = client.post(
        "/api/manuals",
        files={"file": ("pump_manual.pdf", make_pdf_bytes(), "application/pdf")},
        data={"title": "ABC-500 O&M", "manufacturer": "Grundfos", "model": "ABC-500",
              "equipment_kind": "MAIN_PUMP", "revision": "Rev.03"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["manual_id"]


def _add_approved_rule(db, manual_id: int):
    from app.db.models import MaintenanceRule

    db.add(MaintenanceRule(
        manual_id=manual_id, equipment_kind="MAIN_PUMP", model="ABC-500",
        maintenance_type="INSPECTION", interval_hours=2000.0,
        description="Inspect bearing every 2000 hours",
        source_page=1, source_section="Maintenance", status="APPROVED",
    ))
    db.commit()


class FakeLLM:
    model = "fake-model"

    def __init__(self, manual_id: int):
        self.manual_id = manual_id
        self.prompts = []

    def generate_json(self, *, system, prompt):
        self.prompts.append(prompt)
        return {
            "summary": "المضخة بحالة عطل — الضغط صفر رغم حالة التشغيل",
            "reason": ["ضغط 0.0 bar مع FAULT", "ساعات التشغيل تجاوزت فحص البيرنج"],
            "maintenance_suggestions": [
                {"action": "فحص البيرنج", "reason": "متطلب مانوال",
                 "source": {"manual_id": self.manual_id, "page": 1, "section": "Maintenance"}},
                {"action": "إجراء بمرجع وهمي", "reason": "لا يجب أن يمر",
                 "source": {"manual_id": 999, "page": 42}},
            ],
            "evidence": [
                {"type": "MANUAL", "manual_id": self.manual_id, "page": 1},
                {"type": "MANUAL", "manual_id": 999, "page": 5},
                {"type": "METER_READING", "asset_code": "LOC-001-MP-03"},
            ],
        }


def test_analyze_with_fake_llm_filters_fake_refs(client, monkeypatch):
    from app.db.base import SessionLocal

    _import_sample(client)
    manual_id = _upload_manual(client)
    with SessionLocal() as db:
        _add_approved_rule(db, manual_id)
    fake = FakeLLM(manual_id)
    monkeypatch.setattr(ai_service, "get_client", lambda: fake)

    r = client.post("/api/ai/analyze/LOC-001-MP-03")
    assert r.status_code == 200, r.text
    s = r.json()["suggestion"]
    assert s["status"] == "SUGGESTED"
    assert s["severity"] == "CRITICAL"  # FAULT
    assert s["confidence"] == "HIGH"    # قاعدة معتمدة + قراءة
    assert s["id"] is not None

    # §16: مرجع المانوال الوهمي أُسقط والبقية موثّقة
    assert len(s["maintenance_suggestions"]) == 1
    assert s["maintenance_suggestions"][0]["source"]["manual_id"] == manual_id
    assert s["actions_dropped"] == 1
    verified = [(e["type"], e.get("verified")) for e in s["evidence"]]
    assert ("MANUAL", True) in verified
    assert ("MANUAL", False) in verified
    assert ("METER_READING", True) in verified

    # القائمة والفلترة
    listed = client.get("/api/ai/suggestions", params={"asset_code": "LOC-001-MP-03"}).json()
    assert len(listed) == 1
    assert listed[0]["id"] == s["id"]


def test_review_flow(client, monkeypatch):
    from app.db.base import SessionLocal

    _import_sample(client)
    manual_id = _upload_manual(client)
    with SessionLocal() as db:
        _add_approved_rule(db, manual_id)
    monkeypatch.setattr(ai_service, "get_client", lambda: FakeLLM(manual_id))

    sid = client.post("/api/ai/analyze/LOC-001-MP-03").json()["suggestion"]["id"]

    r = client.patch("/api/ai/suggestions/%d" % sid, json={"status": "approved"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "APPROVED"
    assert body["reviewed_at"] is not None

    # حالة غير صالحة
    r2 = client.patch("/api/ai/suggestions/%d" % sid, json={"status": "deleted"})
    assert r2.status_code == 422

    # فلتر الحالة
    approved = client.get("/api/ai/suggestions", params={"status": "APPROVED"}).json()
    assert len(approved) == 1
    rejected = client.get("/api/ai/suggestions", params={"status": "REJECTED"}).json()
    assert rejected == []


def test_analyze_llm_unavailable(client, monkeypatch):
    _import_sample(client)

    class DownLLM:
        model = "down"

        def generate_json(self, *, system, prompt):
            raise LLMUnavailable("Ollama غير متاح")

    monkeypatch.setattr(ai_service, "get_client", lambda: DownLLM())
    r = client.post("/api/ai/analyze/LOC-001-MP-03")
    assert r.status_code == 503

    # أصل غير موجود
    r2 = client.post("/api/ai/analyze/NOPE-999")
    assert r2.status_code == 404


def test_confidence_levels(client, monkeypatch):
    from app.db.base import SessionLocal

    # بدون قاعدة معتمدة وبدون مانوال → LOW
    _import_sample(client)
    fake = FakeLLM(manual_id=1)
    monkeypatch.setattr(ai_service, "get_client", lambda: fake)
    r = client.post("/api/ai/analyze/LOC-001-MP-01")
    assert r.status_code == 200
    assert r.json()["suggestion"]["confidence"] == "LOW"
