# -*- coding: utf-8 -*-
"""API الأصول (المعدات) + حالة الصيانة."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Equipment
from app.services.maintenance import asset_health

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _row(e):
    return {
        "asset_code": e.asset_code, "location_code": e.location_code, "kind": e.kind,
        "tag": e.tag, "model": e.model, "status": e.status,
        "running_hours": e.running_hours, "running_hours_at": e.running_hours_at,
        "updated_at": e.updated_at,
    }


def _health_summary(h: dict) -> dict:
    return {
        "status": h["status"],
        "note": h.get("note"),
        "current_hours": h.get("current_hours"),
        "hours_remaining": h.get("hours_remaining"),
        "due_at_hours": h.get("due_at_hours"),
        "rules_count": h.get("rules_count", 0),
        "readings_count": h.get("readings_count", 0),
    }


@router.get("")
def list_assets(location_code: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Equipment)
    if location_code:
        q = q.filter(Equipment.location_code == location_code)
    out = []
    for e in q.order_by(Equipment.asset_code).all():
        row = _row(e)
        row["health"] = _health_summary(asset_health(db, e, include_readings=False))
        out.append(row)
    return out


@router.get("/{asset_code}")
def get_asset(asset_code: str, db: Session = Depends(get_db)):
    e = db.query(Equipment).filter(Equipment.asset_code == asset_code).first()
    if e is None:
        raise HTTPException(status_code=404, detail="asset not found")
    row = _row(e)
    row["health"] = asset_health(db, e, include_readings=True)
    return row
