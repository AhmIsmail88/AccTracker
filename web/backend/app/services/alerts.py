# -*- coding: utf-8 -*-
"""محرك التنبيهات الحتمي (§22) — تنبيهات محسوبة من البيانات، بلا AI.

القواعد المفعّلة في v1 (كلها مغطاة بالبيانات المتاحة):
  1. PM_OVERDUE          — صيانة متأخرة (من محرك الصيانة §8.3)
  2. PM_DUE              — صيانة مستحقة الآن
  3. PM_SOON             — صيانة قريبة (≤ 10% من الفترة)
  4. FAULT_ACTIVE        — عطل نشط (آخر قراءة أو حالة الأصل)
  5. REPEATED_FAULT      — عطل متكرر (≥2 قراءات عطل في آخر 3 زيارات)
  6. PRESSURE_ANOMALY    — ضغط صفر/منخفض مع حالة RUNNING
  7. RUNNING_HOURS_ANOMALY — عداد الساعات انخفض بين زيارتين (تناقض ميداني)
  8. CHECKLIST_FAULT     — بند فحص بحالة FAULT
  9. PHOTO_NO_GPS        — صور توثيق بلا إحداثيات GPS

قواعد مؤجلة (تحتاج وحدات لم تُبنَ بعد): Low Stock، Model Conflict، Missing Visit.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Equipment, Visit, VisitChecklist, VisitPhoto
from app.services.maintenance import STATUS_ORDER, asset_health

SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}

TYPE_LABELS = {
    "PM_OVERDUE": "صيانة متأخرة",
    "PM_DUE": "صيانة مستحقة",
    "PM_SOON": "صيانة قريبة",
    "FAULT_ACTIVE": "عطل نشط",
    "REPEATED_FAULT": "عطل متكرر",
    "PRESSURE_ANOMALY": "شذوذ ضغط",
    "RUNNING_HOURS_ANOMALY": "شذوذ عداد الساعات",
    "CHECKLIST_FAULT": "بند فحص بحالة عطل",
    "PHOTO_NO_GPS": "صور بدون موقع GPS",
}


def _alert(key, atype, severity, *, asset_code=None, location_code=None, visit_id=None,
           title=None, detail=None, ref=None, at=None):
    return {
        "key": key,
        "type": atype,
        "severity": severity,
        "title": title or TYPE_LABELS.get(atype, atype),
        "detail": detail,
        "asset_code": asset_code,
        "location_code": location_code,
        "visit_id": visit_id,
        "ref": ref or {},
        "at": at,
    }


def _asset_alerts(db: Session, equipment: Equipment) -> list:
    out = []
    h = asset_health(db, equipment, include_readings=True)
    code = equipment.asset_code

    # 1-3) صيانة (من تقييمات المحرك)
    for ev in h.get("rules", []):
        st = ev.get("status")
        if st not in ("MAINTENANCE_SOON", "MAINTENANCE_DUE", "MAINTENANCE_OVERDUE"):
            continue
        interval = ev.get("interval_hours")
        remaining = ev.get("hours_remaining")
        ref = {
            "rule_id": ev.get("rule_id"),
            "manual_id": ev.get("manual_id"),
            "page": ev.get("source_page"),
            "section": ev.get("source_section"),
        }
        if st == "MAINTENANCE_OVERDUE":
            out.append(_alert(
                "pm-overdue:%s:%s" % (code, ev.get("rule_id")), "PM_OVERDUE", "CRITICAL",
                asset_code=code, location_code=equipment.location_code,
                detail="تجاوزت الاستحقاق بمقدار %.0f ساعة (الفترة: كل %.0f ساعة)" % (abs(remaining or 0), interval or 0),
                ref=ref, at=h.get("last_reading_at"),
            ))
        elif st == "MAINTENANCE_DUE":
            out.append(_alert(
                "pm-due:%s:%s" % (code, ev.get("rule_id")), "PM_DUE", "WARNING",
                asset_code=code, location_code=equipment.location_code,
                detail="وصلت إلى 100%% من الفترة (كل %.0f ساعة)" % (interval or 0),
                ref=ref, at=h.get("last_reading_at"),
            ))
        elif st == "MAINTENANCE_SOON":
            out.append(_alert(
                "pm-soon:%s:%s" % (code, ev.get("rule_id")), "PM_SOON", "INFO",
                asset_code=code, location_code=equipment.location_code,
                detail="المتبقي %.0f ساعة من أصل %.0f" % (remaining or 0, interval or 0),
                ref=ref, at=h.get("last_reading_at"),
            ))

    readings = h.get("readings", [])
    latest = readings[-1] if readings else None

    # 4) عطل نشط
    latest_fault = latest is not None and (latest.get("status") or "").upper() == "FAULT"
    asset_fault = (equipment.status or "").upper() == "FAULT"
    if latest_fault or asset_fault:
        out.append(_alert(
            "fault-active:%s" % code, "FAULT_ACTIVE", "CRITICAL",
            asset_code=code, location_code=equipment.location_code,
            visit_id=latest.get("visit_id") if latest else None,
            detail="حالة العطل مسجّلة%s" % (
                " في آخر قراءة (زيارة %s)" % latest["visit_id"] if latest_fault else " على الأصل"
            ),
            at=(latest or {}).get("at"),
        ))

    # 5) عطل متكرر
    recent = readings[-3:]
    faults = [r for r in recent if (r.get("status") or "").upper() == "FAULT"]
    if len(faults) >= 2:
        out.append(_alert(
            "fault-repeated:%s" % code, "REPEATED_FAULT", "CRITICAL",
            asset_code=code, location_code=equipment.location_code,
            detail="%d قراءات عطل في آخر %d زيارات — يلزم فحص جذري" % (len(faults), len(recent)),
            at=faults[-1].get("at"),
        ))

    # 6) شذوذ ضغط
    if latest and latest.get("pressure_bar") is not None:
        p = float(latest["pressure_bar"])
        if p < 0.5 and (latest.get("status") or "").upper() == "RUNNING":
            out.append(_alert(
                "pressure:%s" % code, "PRESSURE_ANOMALY", "CRITICAL",
                asset_code=code, location_code=equipment.location_code,
                visit_id=latest.get("visit_id"),
                detail="ضغط %.1f bar مع حالة RUNNING — تحقق من المضخة/الخط" % p,
                at=latest.get("at"),
            ))

    # 7) شذوذ عداد الساعات
    if len(readings) >= 2:
        prev_h, last_h = readings[-2].get("hours"), readings[-1].get("hours")
        if prev_h is not None and last_h is not None and float(last_h) < float(prev_h):
            out.append(_alert(
                "hours:%s" % code, "RUNNING_HOURS_ANOMALY", "WARNING",
                asset_code=code, location_code=equipment.location_code,
                visit_id=readings[-1].get("visit_id"),
                detail="الساعات انخفضت من %.0f إلى %.0f بين زيارتين" % (float(prev_h), float(last_h)),
                at=readings[-1].get("at"),
            ))

    return out


def _checklist_alerts(db: Session) -> list:
    rows = (
        db.query(VisitChecklist, Visit)
        .join(Visit, VisitChecklist.visit_ref_id == Visit.id)
        .filter(VisitChecklist.status == "FAULT")
        .all()
    )
    out = []
    for c, v in rows:
        out.append(_alert(
            "checklist:%s:%s" % (v.visit_id, c.item_code), "CHECKLIST_FAULT", "WARNING",
            location_code=v.location_code, visit_id=v.visit_id,
            detail="البند %s بحالة عطل" % c.item_code,
            at=v.started_at,
        ))
    return out


def _photo_gps_alerts(db: Session) -> list:
    rows = (
        db.query(VisitPhoto, Visit)
        .join(Visit, VisitPhoto.visit_ref_id == Visit.id)
        .filter(or_(VisitPhoto.lat.is_(None), VisitPhoto.lon.is_(None)))
        .all()
    )
    by_visit: dict = {}
    for p, v in rows:
        entry = by_visit.setdefault(v.visit_id, {"location": v.location_code, "count": 0, "at": v.started_at})
        entry["count"] += 1
    out = []
    for visit_id, info in by_visit.items():
        out.append(_alert(
            "photo-gps:%s" % visit_id, "PHOTO_NO_GPS", "INFO",
            location_code=info["location"], visit_id=visit_id,
            detail="%d صورة بلا إحداثيات GPS" % info["count"],
            at=info["at"],
        ))
    return out


def build_alerts(db: Session) -> list:
    """يبني كل التنبيهات الحالية مرتبة بالشدة (الأخطر أولًا)."""
    alerts = []
    for e in db.query(Equipment).order_by(Equipment.asset_code).all():
        alerts.extend(_asset_alerts(db, e))
    alerts.extend(_checklist_alerts(db))
    alerts.extend(_photo_gps_alerts(db))

    alerts.sort(key=lambda a: (
        SEVERITY_ORDER.get(a["severity"], 9),
        a.get("asset_code") or "",
        a.get("key") or "",
    ))
    return alerts


def counts_by_severity(alerts: list) -> dict:
    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for a in alerts:
        counts[a["severity"]] = counts.get(a["severity"], 0) + 1
    return counts
