# -*- coding: utf-8 -*-
"""فحوص التقارير (§15): الملخص، تقارير الأقسام، وتصدير CSV."""
import os

from app.config import CONTRACT_DIR

SAMPLES = os.path.join(str(CONTRACT_DIR), "samples")


def _import_sample(client):
    with open(os.path.join(SAMPLES, "valid_package.zip"), "rb") as f:
        data = f.read()
    r = client.post("/api/imports", files={"file": ("valid_package.zip", data, "application/zip")})
    assert r.status_code == 200, r.text


def test_report_kinds(client):
    r = client.get("/api/reports/kinds")
    assert r.status_code == 200
    kinds = r.json()["kinds"]
    assert "SUMMARY" in kinds and "ASSETS" in kinds and "STOCK" in kinds


def test_summary_report(client):
    _import_sample(client)
    r = client.get("/api/reports/SUMMARY")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "SUMMARY"
    assert body["counts"]["assets"] == 4
    assert body["counts"]["visits"] == 1
    assert "asset_status" in body
    assert body["alerts"]["total"] >= 1


def test_assets_and_wo_reports(client):
    from app.db.base import SessionLocal
    from app.db.models import MaintenanceRule, Visit, VisitEquipment, WorkOrder

    _import_sample(client)
    with SessionLocal() as db:
        db.add(MaintenanceRule(
            equipment_kind="MAIN_PUMP", model="ABC-500",
            maintenance_type="INSPECTION", interval_hours=2000.0,
            description="Inspect bearing every 2000h", status="APPROVED",
        ))
        db.add(WorkOrder(wo_number="WO-TEST-1", title="اختبار", status="OPEN",
                         priority="HIGH", opened_at="2026-10-01T00:00:00+00:00",
                         updated_at="2026-10-01T00:00:00+00:00"))
        db.commit()

    r = client.get("/api/reports/ASSETS").json()
    assert len(r["rows"]) == 4
    assert "status" in r["rows"][0]

    r2 = client.get("/api/reports/WORK_ORDERS").json()
    assert len(r2["rows"]) == 1
    assert r2["rows"][0]["wo_number"] == "WO-TEST-1"


def test_csv_export(client):
    _import_sample(client)
    r = client.get("/api/reports/STOCK/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8-sig")
    assert "part_code" in text.splitlines()[0]

    # نوع غير معروف
    assert client.get("/api/reports/NOPE").status_code == 404
    assert client.get("/api/reports/NOPE/export.csv").status_code == 404


def test_visits_and_alerts_reports(client):
    _import_sample(client)
    v = client.get("/api/reports/VISITS").json()
    assert len(v["rows"]) == 1
    assert v["rows"][0]["visit_id"] == "VISIT-001"
    assert v["rows"][0]["equipment"] == 4

    a = client.get("/api/reports/ALERTS").json()
    assert len(a["rows"]) >= 1
    assert any(row["type"] == "FAULT_ACTIVE" for row in a["rows"])
