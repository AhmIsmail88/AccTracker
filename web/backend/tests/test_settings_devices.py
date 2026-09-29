# -*- coding: utf-8 -*-
"""فحوص الإعدادات (§23) + الأجهزة + أثر Grace Period على محرك الصيانة."""
import os

from app.config import CONTRACT_DIR
from app.services.maintenance import compute_due_status

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _import_sample(client):
    with open(os.path.join(SAMPLES, "valid_package.zip"), "rb") as f:
        data = f.read()
    r = client.post("/api/imports", files={"file": ("valid_package.zip", data, "application/zip")})
    assert r.status_code == 200, r.text


# ---------- الحساب النقي مع فترة السماح ----------

def test_grace_period_math():
    # متأخرة بـ50 ساعة، سماح 100 → تبقى DUE مش OVERDUE
    status, remaining = compute_due_status(2000, 0, 2050, grace_hours=100)
    assert status == "MAINTENANCE_DUE"

    # متأخرة بـ150 ساعة، سماح 100 → OVERDUE
    status, _ = compute_due_status(2000, 0, 2150, grace_hours=100)
    assert status == "MAINTENANCE_OVERDUE"

    # بدون سماح (السلوك الأصلي)
    status, _ = compute_due_status(2000, 0, 2050, grace_hours=0)
    assert status == "MAINTENANCE_OVERDUE"

    # soon_percent=20 → عتبة 400 ساعة
    status, _ = compute_due_status(2000, 0, 1700, soon_percent=20)
    assert status == "MAINTENANCE_SOON"
    # 1700 متبقية 300 > 200 (10% افتراضي) → NORMAL بدون التعديل... مع 20% → SOON
    status, _ = compute_due_status(2000, 0, 1700, soon_percent=10)
    assert status == "NORMAL"


# ---------- API الإعدادات ----------

def test_settings_defaults_and_update(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["values"]["maintenance.grace_hours"] == 0.0
    assert body["values"]["maintenance.soon_percent"] == 10.0

    r = client.patch("/api/settings", json={"maintenance.grace_hours": 120})
    assert r.status_code == 200, r.text
    assert r.json()["values"]["maintenance.grace_hours"] == 120.0

    # الاستمرارية عبر قراءة جديدة
    r2 = client.get("/api/settings").json()
    assert r2["values"]["maintenance.grace_hours"] == 120.0

    # قيمة خارج النطاق
    r3 = client.patch("/api/settings", json={"maintenance.grace_hours": -5})
    assert r3.status_code == 422

    # قيمة غير رقمية
    r4 = client.patch("/api/settings", json={"maintenance.soon_percent": "abc"})
    assert r4.status_code == 422

    # مفتاح غير معروف → تجاهل (لا تغيير)
    r5 = client.patch("/api/settings", json={"nonsense.key": 5})
    assert r5.status_code == 422  # لا يوجد مفتاح صالح ⇒ 422


def test_settings_affect_asset_health(client):
    """سماح 100 ساعة يحول MP-01 من OVERDUE إلى DUE عبر API الإعدادات."""
    from app.db.base import SessionLocal
    from app.db.models import MaintenanceRule, Visit, VisitEquipment

    _import_sample(client)
    with SessionLocal() as db:
        db.add(MaintenanceRule(
            equipment_kind="MAIN_PUMP", model="ABC-500",
            maintenance_type="INSPECTION", interval_hours=1800.0,
            description="Inspect every 1800h", status="APPROVED",
        ))
        v = Visit(visit_id="VISIT-002", location_code="LOC-001", visit_type="ROUTINE",
                  started_at="2026-10-05T09:00:00+03:00", status="EXPORTED")
        db.add(v)
        db.flush()
        db.add(VisitEquipment(visit_ref_id=v.id, kind="MAIN_PUMP", tag="01", model="ABC-500",
                              running_hours=4300.0, pressure_bar=5.9, status="RUNNING"))
        db.commit()

    # بدقة 1800: المستهلك 1960 → متأخرة 160 ساعة
    d1 = client.get("/api/assets/LOC-001-MP-01").json()
    assert d1["health"]["status"] == "MAINTENANCE_OVERDUE"

    # تفعيل سماح 200 ساعة → DUE
    r = client.patch("/api/settings", json={"maintenance.grace_hours": 200})
    assert r.status_code == 200

    d2 = client.get("/api/assets/LOC-001-MP-01").json()
    assert d2["health"]["status"] == "MAINTENANCE_DUE"

    # والتنبيه يتبع الحالة (PM_OVERDUE يختفي ويظهر PM_DUE)
    alerts = client.get("/api/alerts").json()["alerts"]
    types = [a["type"] for a in alerts if a.get("asset_code") == "LOC-001-MP-01"]
    assert "PM_OVERDUE" not in types
    assert "PM_DUE" in types


# ---------- الأجهزة ----------

def test_devices_endpoint(client):
    _import_sample(client)
    r = client.get("/api/devices")
    assert r.status_code == 200
    devs = r.json()
    assert len(devs) == 1
    d = devs[0]
    assert d["packages"] >= 1
    assert d["imported_ok"] >= 1
    assert d["last_seen"] is not None
    assert "VISIT-001" in d["visits"]
