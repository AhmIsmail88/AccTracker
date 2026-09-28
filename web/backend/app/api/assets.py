# -*- coding: utf-8 -*-
"""API الأصول (المعدات)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Equipment

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _row(e):
    return {
        "asset_code": e.asset_code, "location_code": e.location_code, "kind": e.kind,
        "tag": e.tag, "model": e.model, "status": e.status,
        "running_hours": e.running_hours, "running_hours_at": e.running_hours_at,
        "updated_at": e.updated_at,
    }


@router.get("")
def list_assets(location_code: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Equipment)
    if location_code:
        q = q.filter(Equipment.location_code == location_code)
    return [_row(e) for e in q.order_by(Equipment.asset_code).all()]


@router.get("/{asset_code}")
def get_asset(asset_code: str, db: Session = Depends(get_db)):
    e = db.query(Equipment).filter(Equipment.asset_code == asset_code).first()
    if e is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return _row(e)
