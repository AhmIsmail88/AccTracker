# -*- coding: utf-8 -*-
"""محرك حالة الصيانة — يحسب حالة كل أصل من قواعد المانوال + قراءات الزيارات.

- المدخلات: قواعد صيانة معتمدة (APPROVED) بفترة ساعات + سجل قراءات الأصل من الزيارات.
- المبدأ (§23): due_at = baseline + interval، والباقي = due_at − current.
  - الباقي >  عتبة "قريب" (10% من الفترة، بحد أدنى 25 ساعة) → NORMAL
  - 0 < الباقي ≤ العتبة → MAINTENANCE_SOON
  - الباقي = 0 → MAINTENANCE_DUE
  - الباقي < 0 → MAINTENANCE_OVERDUE
- baseline = أقدم قراءة مسجّلة للأصل (أثناء التجربة: أول قراءة = نقطة البداية).
- عطل تشغيلي (FAULT من القراءات أو من حالة الأصل) يعلو فوق حالة الصيانة.
- «محرك حتمي» — الحساب رياضي وليس من الـAI (راجع §8.3 و§8.2).

راجع ARCHITECTURE.md §8.1 (الحالات) و§8.3 و§23.
"""
from sqlalchemy.orm import Session

from app.db.models import Equipment, EquipmentEvent, MaintenanceRule, Visit, VisitEquipment

# ترتيب شدة الحالة (تختار «الأسوأ» عند وجود أكثر من قاعدة)
STATUS_ORDER = {
    "UNKNOWN": -1,
    "NORMAL": 0,
    "MAINTENANCE_SOON": 1,
    "MAINTENANCE_DUE": 2,
    "MAINTENANCE_OVERDUE": 3,
    "FAULT": 4,
}

SOON_MIN_HOURS = 25.0  # حد أدنى لعتبة «قريب»


def compute_due_status(interval_hours: float, baseline_hours: float, current_hours: float) -> tuple:
    """يحسب (الحالة، الساعات المتبقية) لقاعدة فترة بالساعات."""
    interval = float(interval_hours)
    used = max(0.0, float(current_hours) - float(baseline_hours))
    remaining = interval - used
    soon_threshold = max(interval * 0.1, SOON_MIN_HOURS)
    if remaining < -1e-9:
        return "MAINTENANCE_OVERDUE", remaining
    if remaining <= 1e-9:
        return "MAINTENANCE_DUE", 0.0
    if remaining <= soon_threshold:
        return "MAINTENANCE_SOON", remaining
    return "NORMAL", remaining


def _approved_rules(db: Session, equipment: Equipment) -> list:
    rules = db.query(MaintenanceRule).filter(MaintenanceRule.status == "APPROVED").all()
    out = []
    for r in rules:
        kind_ok = (not r.equipment_kind) or (r.equipment_kind.upper() == (equipment.kind or "").upper())
        model_ok = (not r.model) or (r.model.upper() == (equipment.model or "").upper())
        if kind_ok and model_ok:
            out.append(r)
    return out


def asset_readings(db: Session, equipment: Equipment) -> list:
    """قراءات الأصل من الزيارات (مرتبة زمنيًا من الأقدم للأحدث)."""
    rows = (
        db.query(VisitEquipment, Visit)
        .join(Visit, VisitEquipment.visit_ref_id == Visit.id)
        .filter(
            Visit.location_code == equipment.location_code,
            VisitEquipment.kind == equipment.kind,
            VisitEquipment.tag == (equipment.tag or ""),
        )
        .order_by(Visit.started_at.asc(), Visit.id.asc())
        .all()
    )
    out = []
    for ve, v in rows:
        out.append({
            "visit_id": v.visit_id,
            "at": v.started_at,
            "hours": ve.running_hours,
            "pressure_bar": ve.pressure_bar,
            "status": ve.status,
        })
    return out


def _last_pm_event(db: Session, equipment: Equipment):
    ev = (
        db.query(EquipmentEvent)
        .filter(EquipmentEvent.equipment_id == equipment.id, EquipmentEvent.event_type == "PM")
        .order_by(EquipmentEvent.event_at.desc())
        .first()
    )
    return ev


def asset_health(db: Session, equipment: Equipment, include_readings: bool = True) -> dict:
    """يحسب حالة أصل واحد: الحالة الإجمالية + تقييم كل قاعدة + القراءات."""
    readings = asset_readings(db, equipment)
    current = equipment.running_hours
    if readings and readings[-1]["hours"] is not None:
        current = readings[-1]["hours"]
    baseline = readings[0]["hours"] if readings and readings[0]["hours"] is not None else None

    rules = _approved_rules(db, equipment)
    evaluations = []
    for r in rules:
        if r.interval_hours:
            item = {
                "rule_id": r.id,
                "maintenance_type": r.maintenance_type,
                "interval_hours": r.interval_hours,
                "description": r.description,
                "manual_id": r.manual_id,
                "source_page": r.source_page,
                "source_section": r.source_section,
                "due_at_hours": round(float(baseline) + float(r.interval_hours), 1) if baseline is not None else None,
            }
            if baseline is None or current is None:
                item.update({"status": "UNKNOWN", "hours_remaining": None, "note": "لا توجد قراءات مسجّلة"})
            else:
                status, remaining = compute_due_status(r.interval_hours, baseline, current)
                item.update({"status": status, "hours_remaining": round(remaining, 1)})
            evaluations.append(item)
        elif r.interval_days:
            evaluations.append({
                "rule_id": r.id,
                "maintenance_type": r.maintenance_type,
                "interval_days": r.interval_days,
                "description": r.description,
                "manual_id": r.manual_id,
                "source_page": r.source_page,
                "source_section": r.source_section,
                "status": "UNKNOWN",
                "hours_remaining": None,
                "note": "قاعدة زمنية (بالأيام) — تتطلب تاريخ آخر صيانة",
            })

    evaluated = [e for e in evaluations if e["status"] != "UNKNOWN"]
    if not evaluations:
        overall, note = "UNKNOWN", "لا توجد قواعد صيانة معتمدة لهذا الطراز"
        hours_remaining = None
        due_at = None
    elif not evaluated:
        overall, note = "UNKNOWN", "قواعد موجودة لكن بلا بيانات كافية"
        hours_remaining = None
        due_at = None
    else:
        worst = max(evaluated, key=lambda e: STATUS_ORDER.get(e["status"], -1))
        overall = worst["status"]
        note = None
        remaining_values = [e["hours_remaining"] for e in evaluated if e.get("hours_remaining") is not None]
        hours_remaining = min(remaining_values) if remaining_values else None
        due_values = [e["due_at_hours"] for e in evaluated if e.get("due_at_hours") is not None]
        due_at = min(due_values) if due_values else None

    # العطل التشغيلي يعلو فوق حالة الصيانة
    latest_reading_status = readings[-1]["status"] if readings else None
    fault = (equipment.status or "").upper() == "FAULT" or (latest_reading_status or "").upper() == "FAULT"
    if fault:
        overall = "FAULT"
        note = "عطل تشغيلي مسجّل — راجع القراءات"

    health = {
        "status": overall,
        "note": note,
        "baseline_hours": baseline,
        "current_hours": current,
        "hours_remaining": hours_remaining,
        "due_at_hours": due_at,
        "rules_count": len(evaluations),
        "rules": evaluations,
        "readings_count": len(readings),
        "last_reading_at": readings[-1]["at"] if readings else None,
    }
    if include_readings:
        health["readings"] = readings[-20:]
    return health
