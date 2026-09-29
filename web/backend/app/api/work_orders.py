# -*- coding: utf-8 -*-
"""API أوامر العمل (§20)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.work_orders import (
    add_part, create_wo, get_wo, issue_part, list_wo, return_part, update_wo,
)

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


class WoIn(BaseModel):
    title: str
    asset_code: str = ""
    location_code: str = ""
    description: str = ""
    priority: str = "MEDIUM"
    status: str = "OPEN"
    source: str = "MANUAL"
    source_ref: str = ""
    assigned_to: str = ""


class WoUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    closing_note: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class WoPartIn(BaseModel):
    part_id: int
    planned_qty: float
    unit_cost: Optional[float] = None


class QtyIn(BaseModel):
    qty: float
    note: str = ""


@router.get("")
def works(status: Optional[str] = None, asset_code: Optional[str] = None,
          priority: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 500))
    return list_wo(db, status=status, asset_code=asset_code, priority=priority, limit=safe_limit)


@router.post("")
def new_wo(payload: WoIn, db: Session = Depends(get_db)):
    try:
        return create_wo(
            db, title=payload.title, asset_code=payload.asset_code,
            location_code=payload.location_code, description=payload.description,
            priority=payload.priority,
            source=payload.source, source_ref=payload.source_ref,
            assigned_to=payload.assigned_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{wo_id}")
def one_wo(wo_id: int, db: Session = Depends(get_db)):
    try:
        return get_wo(db, wo_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{wo_id}")
def patch_wo(wo_id: int, payload: WoUpdate, db: Session = Depends(get_db)):
    try:
        return update_wo(
            db, wo_id, status=payload.status, priority=payload.priority,
            assigned_to=payload.assigned_to, closing_note=payload.closing_note,
            title=payload.title, description=payload.description,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{wo_id}/parts")
def wo_add_part(wo_id: int, payload: WoPartIn, db: Session = Depends(get_db)):
    try:
        return add_part(db, wo_id, part_id=payload.part_id, planned_qty=payload.planned_qty,
                        unit_cost=payload.unit_cost)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{wo_id}/parts/{part_id}/issue")
def wo_issue(wo_id: int, part_id: int, payload: QtyIn, db: Session = Depends(get_db)):
    try:
        return issue_part(db, wo_id, part_id, payload.qty, note=payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{wo_id}/parts/{part_id}/return")
def wo_return(wo_id: int, part_id: int, payload: QtyIn, db: Session = Depends(get_db)):
    try:
        return return_part(db, wo_id, part_id, payload.qty, note=payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
