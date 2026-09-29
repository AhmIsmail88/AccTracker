# -*- coding: utf-8 -*-
"""فحوص المساعد الذكي (§28) — بمزود مزيّف، مع فحص المصادر (§16)."""
import os

from app.config import CONTRACT_DIR
from app.services import ai_chat as chat_service
from app.services.llm import LLMUnavailable


def _import_sample(client):
    with open(os.path.join(str(CONTRACT_DIR), "samples", "valid_package.zip"), "rb") as f:
        data = f.read()
    r = client.post("/api/imports", files={"file": ("valid_package.zip", data, "application/zip")})
    assert r.status_code == 200, r.text


class FakeChatLLM:
    model = "fake-chat"

    def __init__(self, manual_id=None, asset_code="LOC-001-MP-03"):
        self.manual_id = manual_id
        self.asset_code = asset_code
        self.last_prompt = None

    def generate_json(self, *, system, prompt):
        self.last_prompt = prompt
        return {
            "answer": "MP-03 في حالة عطل — ضغط صفر. يلزم فحص الختم.",
            "related_assets": [self.asset_code, "NOPE-000"],
            "sources": (
                [{"type": "MANUAL", "manual_id": self.manual_id, "page": 1}] if self.manual_id else []
            ) + [
                {"type": "ASSET", "asset_code": self.asset_code},
                {"type": "MANUAL", "manual_id": 999, "page": 42},
            ],
        }


def test_chat_flow_with_fake_llm(client, monkeypatch):
    from app.db.base import SessionLocal

    _import_sample(client)
    fake = FakeChatLLM()
    monkeypatch.setattr(chat_service, "get_client", lambda: fake)

    r = client.post("/api/ai/chat", json={"question": "ما حالة MP-03؟"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "عطل" in body["answer"]
    # أصل غير موجود استُبعد
    assert body["related_assets"] == ["LOC-001-MP-03"]
    # مصدر مانوال وهمي استُبعد (§16)
    types = [(s["type"], s.get("verified")) for s in body["sources"]]
    assert ("ASSET", True) in types
    assert all(s.get("manual_id") != 999 for s in body["sources"])
    assert body["sources_dropped"] >= 1
    # سياق حقيقي: الأسطول موجود + الأصول المذكورة في focus
    assert body["context"]["fleet"] == 4
    assert body["context"]["focus"] == 1


def test_chat_fleet_question(client, monkeypatch):
    _import_sample(client)
    fake = FakeChatLLM()
    monkeypatch.setattr(chat_service, "get_client", lambda: fake)

    r = client.post("/api/ai/chat", json={"question": "أي مضخة محتاجة صيانة قريبة؟"})
    assert r.status_code == 200
    body = r.json()
    # لم يُذكر أي أصل صراحةً
    assert body["context"]["focus"] == 0
    assert body["context"]["alerts"] >= 1  # عطل MP-03 موجود


def test_chat_validation_and_unavailable(client, monkeypatch):
    # سؤال فارغ
    r = client.post("/api/ai/chat", json={"question": "   "})
    assert r.status_code == 422

    class DownLLM:
        model = "down"

        def generate_json(self, *, system, prompt):
            raise LLMUnavailable("Ollama غير متاح")

    monkeypatch.setattr(chat_service, "get_client", lambda: DownLLM())
    r2 = client.post("/api/ai/chat", json={"question": "اختبار"})
    assert r2.status_code == 503


def test_chat_includes_manual_excerpts_for_mentioned_asset(client, monkeypatch):
    """عند ذكر أصل له قاعدة معتمدة بمرجع مانوال — المقتطف يدخل السياق."""
    import fitz
    from app.db.base import SessionLocal
    from app.db.models import MaintenanceRule

    _import_sample(client)
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 72), "1. Maintenance", fontsize=12)
    p.insert_text((72, 110), "Inspect bearing every 2000 hours.", fontsize=11)
    pdf = doc.tobytes()
    doc.close()
    r = client.post(
        "/api/manuals",
        files={"file": ("m.pdf", pdf, "application/pdf")},
        data={"title": "ABC-500 O&M", "model": "ABC-500", "equipment_kind": "MAIN_PUMP"},
    )
    mid = r.json()["manual_id"]
    with SessionLocal() as db:
        db.add(MaintenanceRule(
            manual_id=mid, equipment_kind="MAIN_PUMP", model="ABC-500",
            maintenance_type="INSPECTION", interval_hours=2000.0,
            description="Inspect bearing every 2000 hours",
            source_page=1, source_section="Maintenance", status="APPROVED",
        ))
        db.commit()

    fake = FakeChatLLM(manual_id=mid)
    monkeypatch.setattr(chat_service, "get_client", lambda: fake)
    r2 = client.post("/api/ai/chat", json={"question": "إيه إجراءات صيانة MP-03؟"})
    body = r2.json()
    assert body["context"]["chunks"] >= 1
    # مصدر المانوال الحقيقي مرّ (verified)
    manual_sources = [s for s in body["sources"] if s["type"] == "MANUAL"]
    assert manual_sources and manual_sources[0]["manual_id"] == mid
    assert body["confidence"] in ("HIGH", "MEDIUM")
