# -*- coding: utf-8 -*-
"""فحوص محرك حالة الصيانة: دوال الحساب النقية + التكامل عبر API الأصول."""
import os

from app.config import CONTRACT_DIR
from app.services.maintenance import compute_due_status

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _read_valid_package() -> bytes:
    with open(os.path.join(SAMPLES, "valid_package.zip"), "rb") as f:
        return f.read()


def _import_sample(client):
    r = client.post(
        "/api/imports",
        files={"file": ("valid_package.zip", _read_valid_package(), "application/zip")},
    )
    assert r.status_code == 200, r.text


# ---------- الحساب النقي (§23) ----------

def test_compute_due_status_examples_from_spec():
    # مثال المواصفة: فحص كل 2000 ساعة، آخر صيانة 10000، الحالي 11950 → 50 متبقية → SOON
    status, remaining = compute_due_status(2000, 10000, 11950)
    assert status == "MAINTENANCE_SOON"
    assert abs(remaining - 50) < 0.01

    # 12000 → DUE
    status, remaining = compute_due_status(2000, 10000, 12000)
    assert status == "MAINTENANCE_DUE"
    assert remaining == 0

    # 12100 → OVERDUE
    status, remaining = compute_due_status(2000, 10000, 12100)
    assert status == "MAINTENANCE_OVERDUE"
    assert remaining < 0

    # 10500 → NORMAL (1500 متبقية)
    status, remaining = compute_due_status(2000, 10000, 10500)
    assert status == "NORMAL"
    assert abs(remaining - 1500) < 0.01


def test_compute_due_status_soon_threshold_floor():
    # فترة صغيرة: العتبة لا تقل عن 25 ساعة
    status, _ = compute_due_status(100, 0, 80)
    assert status == "MAINTENANCE_SOON"  # 20 متبقية ≤ 25


# ---------- التكامل عبر API ----------

def test_assets_health_without_rules(client):
    _import_sample(client)
    assets = client.get("/api/assets").json()
    assert len(assets) == 4
    first = assets[0]
    assert "health" in first
    assert first["health"]["status"] == "UNKNOWN"  # لا توجد قواعد معتمدة بعد
    assert first["health"]["readings_count"] >= 1


def _add_rule(db, interval_hours, kind="MAIN_PUMP", model="ABC-500"):
    from app.db.models import MaintenanceRule

    rule = MaintenanceRule(
        equipment_kind=kind,
        model=model,
        maintenance_type="INSPECTION",
        interval_hours=interval_hours,
        description="Inspect bearing every %d hours" % interval_hours,
        source_page=47,
        source_section="Maintenance",
        status="APPROVED",
    )
    db.add(rule)
    db.commit()
    return rule


def _add_reading(db, hours, visit_id="VISIT-002"):
    from app.db.models import Visit, VisitEquipment

    v = Visit(
        visit_id=visit_id,
        location_code="LOC-001",
        visit_type="ROUTINE",
        started_at="2026-10-05T09:00:00+03:00",
        status="EXPORTED",
    )
    db.add(v)
    db.flush()
    db.add(VisitEquipment(
        visit_ref_id=v.id, kind="MAIN_PUMP", tag="01", model="ABC-500",
        running_hours=hours, pressure_bar=5.9, status="RUNNING",
    ))
    db.commit()


def test_health_maintenance_soon(client):
    from app.db.base import SessionLocal

    _import_sample(client)
    with SessionLocal() as db:
        _add_rule(db, 2000)
        _add_reading(db, 4300.0)  # baseline 2340 → المستهلك 1960 → المتبقي 40 → SOON

    detail = client.get("/api/assets/LOC-001-MP-01").json()
    h = detail["health"]
    assert h["status"] == "MAINTENANCE_SOON"
    assert h["rules_count"] == 1
    assert abs(h["hours_remaining"] - 40) < 0.01
    assert abs(h["due_at_hours"] - 4340) < 0.01
    assert h["readings_count"] == 2
    assert h["last_reading_at"] == "2026-10-05T09:00:00+03:00"


def test_health_overdue_and_fault_priority(client):
    from app.db.base import SessionLocal

    _import_sample(client)
    with SessionLocal() as db:
        _add_rule(db, 1800)  # المستهلك 1960 → المتبقي -160 → OVERDUE
        _add_reading(db, 4300.0)

    detail = client.get("/api/assets/LOC-001-MP-01").json()
    assert detail["health"]["status"] == "MAINTENANCE_OVERDUE"

    # MP-03 عطلها مسجل في القراءة (FAULT) → الحالة FAULT تعلو
    fault_detail = client.get("/api/assets/LOC-001-MP-03").json()
    assert fault_detail["health"]["status"] == "FAULT"
