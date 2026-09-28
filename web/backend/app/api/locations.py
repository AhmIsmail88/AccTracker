# -*- coding: utf-8 -*-
"""API شجرة المواقع والتعارضات."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import ConflictResolve, LocationCreate, LocationUpdate
from app.services import locations as svc

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/tree")
def tree(include_inactive: bool = False, db: Session = Depends(get_db)):
    return svc.build_tree(db, include_inactive)


@router.get("/conflicts")
def conflicts(status: str = "OPEN", db: Session = Depends(get_db)):
    return svc.list_conflicts(db, status)


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: int, payload: ConflictResolve, db: Session = Depends(get_db)):
    try:
        row = svc.resolve_conflict(db, conflict_id, payload.action)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": row.id, "status": row.status}


@router.post("")
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    try:
        obj = svc.create_node(db, payload.type, payload.name, payload.parent_code,
                              payload.code, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "code": obj.code, "name": obj.name, "type": payload.type.upper(),
        "status": obj.status, "source": obj.source, "review_status": obj.review_status,
    }


@router.patch("/{code}")
def update_location(code: str, payload: LocationUpdate, db: Session = Depends(get_db)):
    try:
        obj = svc.update_node(db, code, name=payload.name,
                              parent_code=payload.parent_code, status=payload.status)
    except ValueError as e:
        sc = 404 if "غير موجود" in str(e) else 422
        raise HTTPException(status_code=sc, detail=str(e))
    return {"code": obj.code, "name": obj.name, "status": obj.status}


@router.post("/{code}/review")
def review_location(code: str, db: Session = Depends(get_db)):
    try:
        obj = svc.mark_reviewed(db, code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": obj.code, "review_status": obj.review_status}
