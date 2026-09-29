# -*- coding: utf-8 -*-
"""التقارير (§15) — تجميع بيانات النظام في تقارير قابلة للتصدير (JSON / CSV / XLSX).

التقارير المتاحة:
- SUMMARY       : ملخص عام (عدد المواقع/الأصول/الزيارات/الأوامر + توزيع الحالات + المخزون)
- ASSETS        : تقرير حالة الأصول (حالة الصيانة + المتبقي + آخر قراءة)
- WORK_ORDERS   : تقرير أوامر العمل (حالة/أولوية/تكاليف)
- STOCK         : تقرير المخزون (أرصدة + اقتراحات شراء)
- VISITS        : تقرير الزيارات (آخر الزيارات + عدد المعدات والفحوص)
- ALERTS        : تقرير التنبيهات الحالية
"""
import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Equipment, ImportedPackage, SparePart, StockMovement, Visit, VisitChecklist, VisitEquipment, WorkOrder
from app.services.alerts import build_alerts
from app.services.maintenance import asset_health
from app.services.stock import purchasing_suggestions, stock_level

REPORT_KINDS = ("SUMMARY", "ASSETS", "WORK_ORDERS", "STOCK", "VISITS", "ALERTS")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _csv_bytes(header: list, rows: list) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    # BOM ليفتح العربي صح في Excel
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def _summary(db: Session) -> dict:
    from app.db.models import Location

    visits = db.query(Visit).all()
    assets = db.query(Equipment).all()
    works = db.query(WorkOrder).all()
    parts = db.query(SparePart).all()

    status_counts = {}
    for a in assets:
        h = asset_health(db, a, include_readings=False)
        status_counts[h["status"]] = status_counts.get(h["status"], 0) + 1

    wo_counts = {}
    for w in works:
        wo_counts[w.status] = wo_counts.get(w.status, 0) + 1

    stock_value = 0.0
    low_parts = 0
    for p in parts:
        lvl = stock_level(db, p.id)
        if p.unit_cost:
            stock_value += lvl * p.unit_cost
        if lvl <= (p.min_stock or 0.0):
            low_parts += 1

    alerts = build_alerts(db)
    alerts_counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for a in alerts:
        alerts_counts[a["severity"]] = alerts_counts.get(a["severity"], 0) + 1

    return {
        "generated_at": _now(),
        "counts": {
            "locations": db.query(Location).count(),
            "assets": len(assets),
            "visits": len(visits),
            "packages": db.query(ImportedPackage).count(),
            "work_orders_open": sum(1 for w in works if w.status in ("OPEN", "IN_PROGRESS")),
            "parts": len(parts),
        },
        "asset_status": status_counts,
        "work_order_status": wo_counts,
        "stock": {
            "parts": len(parts),
            "low_stock_parts": low_parts,
            "stock_value": round(stock_value, 2),
        },
        "alerts": {"total": len(alerts), **alerts_counts},
    }


def _assets_report(db: Session) -> dict:
    rows = []
    for a in db.query(Equipment).order_by(Equipment.asset_code).all():
        h = asset_health(db, a, include_readings=False)
        rows.append({
            "asset_code": a.asset_code,
            "location_code": a.location_code,
            "kind": a.kind,
            "model": a.model,
            "status": h["status"],
            "current_hours": h["current_hours"],
            "hours_remaining": h["hours_remaining"],
            "due_at_hours": h["due_at_hours"],
            "rules_count": h["rules_count"],
            "last_reading_at": h["last_reading_at"],
        })
    header = ["asset_code", "location_code", "kind", "model", "status", "current_hours",
              "hours_remaining", "due_at_hours", "rules_count", "last_reading_at"]
    return {"columns": header, "rows": rows}


def _work_orders_report(db: Session) -> dict:
    from app.services.work_orders import wo_to_dict

    rows = []
    for w in db.query(WorkOrder).order_by(WorkOrder.id.desc()).limit(500).all():
        d = wo_to_dict(db, w, with_parts=False)
        rows.append({
            "wo_number": d["wo_number"],
            "title": d["title"],
            "asset_code": d["asset_code"],
            "status": d["status"],
            "priority": d["priority"],
            "opened_at": d["opened_at"],
            "closed_at": d["closed_at"],
            "parts_count": d["parts_count"],
            "parts_cost": d["parts_cost"],
        })
    header = ["wo_number", "title", "asset_code", "status", "priority", "opened_at",
              "closed_at", "parts_count", "parts_cost"]
    return {"columns": header, "rows": rows}


def _stock_report(db: Session) -> dict:
    rows = []
    for p in db.query(SparePart).order_by(SparePart.part_code).all():
        lvl = stock_level(db, p.id)
        rows.append({
            "part_code": p.part_code,
            "name": p.name,
            "unit": p.unit,
            "stock": round(lvl, 3),
            "min_stock": p.min_stock,
            "low_stock": lvl <= (p.min_stock or 0.0),
            "unit_cost": p.unit_cost,
            "stock_value": round(lvl * p.unit_cost, 2) if p.unit_cost else None,
        })
    header = ["part_code", "name", "unit", "stock", "min_stock", "low_stock", "unit_cost", "stock_value"]
    return {"columns": header, "rows": rows, "suggestions": purchasing_suggestions(db)}


def _visits_report(db: Session) -> dict:
    visits = db.query(Visit).order_by(Visit.id.desc()).limit(300).all()
    rows = []
    for v in visits:
        equips = db.query(VisitEquipment).filter(VisitEquipment.visit_ref_id == v.id).count()
        checks = db.query(VisitChecklist).filter(VisitChecklist.visit_ref_id == v.id).count()
        faults = (
            db.query(VisitChecklist)
            .filter(VisitChecklist.visit_ref_id == v.id, VisitChecklist.status == "FAULT")
            .count()
        )
        rows.append({
            "visit_id": v.visit_id,
            "location_code": v.location_code,
            "visit_type": v.visit_type,
            "started_at": v.started_at,
            "status": v.status,
            "equipment": equips,
            "checklist": checks,
            "faults": faults,
            "package_id": v.package_id,
        })
    header = ["visit_id", "location_code", "visit_type", "started_at", "status",
              "equipment", "checklist", "faults", "package_id"]
    return {"columns": header, "rows": rows}


def _alerts_report(db: Session) -> dict:
    alerts = build_alerts(db)
    rows = [{
        "type": a["type"],
        "severity": a["severity"],
        "asset_code": a.get("asset_code") or "",
        "location_code": a.get("location_code") or "",
        "visit_id": a.get("visit_id") or "",
        "detail": a.get("detail") or "",
        "at": a.get("at") or "",
    } for a in alerts]
    header = ["type", "severity", "asset_code", "location_code", "visit_id", "detail", "at"]
    return {"columns": header, "rows": rows}


_BUILDERS = {
    "SUMMARY": _summary,
    "ASSETS": _assets_report,
    "WORK_ORDERS": _work_orders_report,
    "STOCK": _stock_report,
    "VISITS": _visits_report,
    "ALERTS": _alerts_report,
}


def build_report(db: Session, kind: str) -> dict:
    kind = (kind or "").strip().upper()
    if kind not in REPORT_KINDS:
        raise ValueError("نوع تقرير غير معروف: %s (المتاح: %s)" % (kind, ", ".join(REPORT_KINDS)))
    data = _BUILDERS[kind](db)
    return {"kind": kind, "generated_at": _now(), **data}


def report_as_csv(db: Session, kind: str) -> tuple:
    """(اسم الملف، بايتات CSV)."""
    data = build_report(db, kind)
    if "columns" in data:
        body = _csv_bytes(data["columns"], [[_scalar(r.get(c)) for c in data["columns"]] for r in data["rows"]])
    else:
        # ملخص: صفوف مفتاح/قيمة
        rows = []
        for section, value in data.items():
            if section in ("kind", "generated_at"):
                continue
            if isinstance(value, dict):
                for k, v in value.items():
                    rows.append([section, k, v])
            else:
                rows.append([section, "", value])
        body = _csv_bytes(["section", "key", "value"], rows)
    fname = "acctracker-%s-%s.csv" % (kind.lower(), datetime.now(timezone.utc).strftime("%Y%m%d-%H%M"))
    return fname, body


def _scalar(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "نعم" if value else "لا"
    return value
