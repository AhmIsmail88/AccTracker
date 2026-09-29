# -*- coding: utf-8 -*-
"""API الإعدادات (§23) + الأجهزة والفنيين (§5.2/16)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ImportedPackage, Visit
from app.services.settings import DEFAULTS, get_settings, update_settings

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsPatch(BaseModel):
    model_config = {"extra": "allow"}


@router.get("/settings")
def settings_get(db: Session = Depends(get_db)):
    values = get_settings(db)
    return {
        "values": values,
        "defaults": DEFAULTS,
    }


@router.patch("/settings")
def settings_patch(payload: SettingsPatch, db: Session = Depends(get_db)):
    patch = payload.model_dump()
    if not patch:
        raise HTTPException(status_code=422, detail="لا يوجد أي مفتاح للتحديث")
    try:
        values = update_settings(db, patch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"values": values}


@router.get("/devices")
def devices(db: Session = Depends(get_db)):
    """الأجهزة (سامسونج/تابلت الفنيين) التي وصلت منها حزم — مع آخر ظهور وأرقام الحزم."""
    rows = db.query(ImportedPackage).all()
    visits = {}
    for v in db.query(Visit.package_id, Visit.visit_id).all():
        visits.setdefault(v.package_id, []).append(v.visit_id)

    by_device = {}
    for r in rows:
        key = r.device_id or "(غير معروف)"
        d = by_device.setdefault(key, {
            "device_id": key,
            "fingerprint": None,
            "packages": 0,
            "imported_ok": 0,
            "last_seen": None,
            "last_file": None,
            "visits": [],
        })
        d["packages"] += 1
        if r.status == "PASS":
            d["imported_ok"] += 1
        if d["last_seen"] is None or (r.imported_at or "") > d["last_seen"]:
            d["last_seen"] = r.imported_at
            d["last_file"] = r.filename
        if r.device_fingerprint:
            d["fingerprint"] = r.device_fingerprint
        d["visits"].extend(visits.get(r.package_id, []))

    out = sorted(by_device.values(), key=lambda x: x["last_seen"] or "", reverse=True)
    for d in out:
        d["visits"] = sorted(set(d["visits"]), reverse=True)[:10]
    return out
