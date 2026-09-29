# -*- coding: utf-8 -*-
"""API المخزون (قطع الغيار + الحركات) — §33 Phase 6."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.stock import (
    add_movement, create_part, list_movements, list_parts, purchasing_suggestions,
)

router = APIRouter(prefix="/api/stock", tags=["stock"])


class PartIn(BaseModel):
    part_code: str
    name: str
    manufacturer: str = ""
    model: str = ""
    unit: str = "قطعة"
    min_stock: float = 0.0
    unit_cost: Optional[float] = None
    notes: str = ""


class MovementIn(BaseModel):
    part_id: int
    movement_type: str
    qty: float
    work_order_id: Optional[int] = None
    reference: str = ""
    note: str = ""


@router.get("/parts")
def parts(low_only: bool = False, db: Session = Depends(get_db)):
    return list_parts(db, low_only=low_only)


@router.post("/parts")
def add_part(payload: PartIn, db: Session = Depends(get_db)):
    try:
        return create_part(
            db,
            part_code=payload.part_code, name=payload.name,
            manufacturer=payload.manufacturer, model=payload.model,
            unit=payload.unit, min_stock=payload.min_stock,
            unit_cost=payload.unit_cost, notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/movements")
def movements(part_id: Optional[int] = None, work_order_id: Optional[int] = None,
              limit: int = 100, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 500))
    return list_movements(db, part_id=part_id, work_order_id=work_order_id, limit=safe_limit)


@router.post("/movements")
def new_movement(payload: MovementIn, db: Session = Depends(get_db)):
    try:
        return add_movement(
            db, part_id=payload.part_id, movement_type=payload.movement_type,
            qty=payload.qty, work_order_id=payload.work_order_id,
            reference=payload.reference, note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/suggestions")
def suggestions(db: Session = Depends(get_db)):
    return purchasing_suggestions(db)
