# -*- coding: utf-8 -*-
"""فحوص محرك التنبيهات الحتمي (§22)."""
import os

from app.config import CONTRACT_DIR

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


def _types(alerts):
    return [a["type"] for a in alerts]


def test_alerts_after_sample_import(client):
    _import_sample(client)
    body = client.get("/api/alerts").json()
    assert body["total"] >= 1

    # MP-03 عليه عطل مسجّل → عطل نشط
    fault = [a for a in body["alerts"] if a["type"] == "FAULT_ACTIVE"]
    assert len(fault) == 1
    assert fault[0]["asset_code"] == "LOC-001-MP-03"
    assert fault[0]["severity"] == "CRITICAL"

    # ترتيب الشدة: الحرجة أولًا
    sevs = [a["severity"] for a in body["alerts"]]
    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    assert sevs == sorted(sevs, key=lambda s: order[s])


def test_alerts_pm_overdue(client):
    from app.db.base import SessionLocal
    from app.db.models import MaintenanceRule

    _import_sample(client)
    with SessionLocal() as db:
        db.add(MaintenanceRule(
            equipment_kind="MAIN_PUMP", model="ABC-500",
            maintenance_type="INSPECTION", interval_hours=1800.0,
            description="Inspect bearing every 1800 hours", status="APPROVED",
        ))
        db.commit()

    # MP-03: ساعات 2360 ولها عطل (FAULT) — لا نحتاج قراءة إضافية لحساب OVERDUE:
    # baseline=2340 لأول قراءة MP-03... في العينة كل مضخة لها قراءة واحدة؛
    # المستهلك = 0 والمتبقي = 1800 → NORMAL، لذا نضيف قراءة أعلى لـMP-01.
    with SessionLocal() as db:
        from app.db.models import Visit, VisitEquipment

        v = Visit(visit_id="VISIT-002", location_code="LOC-001", visit_type="ROUTINE",
                  started_at="2026-10-05T09:00:00+03:00", status="EXPORTED")
        db.add(v)
        db.flush()
        db.add(VisitEquipment(visit_ref_id=v.id, kind="MAIN_PUMP", tag="01", model="ABC-500",
                              running_hours=4300.0, pressure_bar=5.9, status="RUNNING"))
        db.commit()

    body = client.get("/api/alerts").json()
    overdue = [a for a in body["alerts"] if a["type"] == "PM_OVERDUE" and a["asset_code"] == "LOC-001-MP-01"]
    assert len(overdue) == 1
    assert overdue[0]["severity"] == "CRITICAL"
    assert "160" in overdue[0]["detail"]  # 1800 - 1960 = -160


def test_alerts_severity_filter(client):
    _import_sample(client)
    r = client.get("/api/alerts", params={"severity": "critical"}).json()
    assert all(a["severity"] == "CRITICAL" for a in r["alerts"])
    assert r["counts"]["CRITICAL"] == len(r["alerts"])

    r2 = client.get("/api/alerts", params={"severity": "info"}).json()
    assert all(a["severity"] == "INFO" for a in r2["alerts"])


def test_alerts_checklist_and_hours_and_photo(client):
    from app.db.base import SessionLocal
    from app.db.models import Visit, VisitChecklist, VisitEquipment, VisitPhoto

    _import_sample(client)
    with SessionLocal() as db:
        v = Visit(visit_id="VISIT-002", location_code="LOC-001", visit_type="ROUTINE",
                  started_at="2026-10-05T09:00:00+03:00", status="EXPORTED")
        db.add(v)
        db.flush()
        # ساعات أقل من السابق → شذوذ عدّاد
        db.add(VisitEquipment(visit_ref_id=v.id, kind="MAIN_PUMP", tag="01", model="ABC-500",
                              running_hours=2200.0, status="RUNNING"))
        # بند فحص بحالة عطل
        db.add(VisitChecklist(visit_ref_id=v.id, item_code="CHK-99", status="FAULT"))
        # صورة بلا GPS
        db.add(VisitPhoto(visit_ref_id=v.id, target_type="EQUIPMENT", target_ref="01",
                          file_path="", taken_at="2026-10-05T10:00:00+03:00", lat=None, lon=None))
        db.commit()

    body = client.get("/api/alerts").json()
    types = _types(body["alerts"])
    assert "RUNNING_HOURS_ANOMALY" in types
    assert "CHECKLIST_FAULT" in types
    assert "PHOTO_NO_GPS" in types

    h = [a for a in body["alerts"] if a["type"] == "RUNNING_HOURS_ANOMALY"][0]
    assert h["asset_code"] == "LOC-001-MP-01"
    assert "2200" in h["detail"]
