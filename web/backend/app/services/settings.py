# -*- coding: utf-8 -*-
"""إعدادات النظام — قراءة/كتابة فوق جدول app_setting مع تحقق وافتراضيات.

المفاتيح المستخدمة:
- maintenance.grace_hours   : فترة السماح بعد الاستحقاق قبل اعتبارها «متأخرة» (§23)
- maintenance.soon_percent  : نسبة «قرب الصيانة» من الفترة (افتراضي 10%)
- maintenance.soon_min_hours: حد أدنى لساعات «قرب الصيانة» (افتراضي 25)
"""
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.models import AppSetting

DEFAULTS = {
    "maintenance.grace_hours": 0.0,
    "maintenance.soon_percent": 10.0,
    "maintenance.soon_min_hours": 25.0,
}

LIMITS = {
    "maintenance.grace_hours": (0.0, 10000.0),
    "maintenance.soon_percent": (1.0, 50.0),
    "maintenance.soon_min_hours": (0.0, 1000.0),
}


def _read_rows(db: Session) -> dict:
    try:
        return {r.key: r.value for r in db.query(AppSetting).all()}
    except OperationalError:
        return {}


def get_settings(db: Session) -> dict:
    rows = _read_rows(db)
    out = {}
    for key, default in DEFAULTS.items():
        raw = rows.get(key)
        try:
            out[key] = float(raw) if raw is not None else float(default)
        except (TypeError, ValueError):
            out[key] = float(default)
    return out


def get_maintenance_config(db: Session) -> dict:
    s = get_settings(db)
    return {
        "grace_hours": s["maintenance.grace_hours"],
        "soon_percent": s["maintenance.soon_percent"],
        "soon_min_hours": s["maintenance.soon_min_hours"],
    }


def update_settings(db: Session, patch: dict) -> dict:
    """تحديث مفاتيح معروفة فقط مع تحقق من النطاق — وبلا مفاتيح صالحة يرفض الطلب."""
    clean = {}
    for key, value in (patch or {}).items():
        if key not in DEFAULTS:
            continue
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise ValueError("قيمة غير رقمية للمفتاح %s" % key)
        lo, hi = LIMITS[key]
        if not (lo <= num <= hi):
            raise ValueError("قيمة %s خارج النطاق [%s, %s]" % (key, lo, hi))
        clean[key] = str(num)
    if not clean:
        raise ValueError("لا توجد مفاتيح معروفة للتحديث")

    for key, value in clean.items():
        row = db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_settings(db)
