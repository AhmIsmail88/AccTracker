# -*- coding: utf-8 -*-
"""API الزيارات المستوردة."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Visit, VisitChecklist, VisitEquipment, VisitPhoto

router = APIRouter(prefix="/api/visits", tags=["visits"])


@router.get("")
def list_visits(db: Session = Depends(get_db)):
    rows = db.query(Visit).order_by(Visit.id.desc()).all()
    return [{
        "visit_id": v.visit_id, "location_code": v.location_code, "visit_type": v.visit_type,
        "started_at": v.started_at, "ended_at": v.ended_at, "status": v.status,
        "package_id": v.package_id, "imported_at": v.imported_at,
    } for v in rows]


@router.get("/{visit_id}")
def get_visit(visit_id: str, db: Session = Depends(get_db)):
    v = db.query(Visit).filter(Visit.visit_id == visit_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail="visit not found")
    equips = db.query(VisitEquipment).filter(VisitEquipment.visit_ref_id == v.id).all()
    checks = db.query(VisitChecklist).filter(VisitChecklist.visit_ref_id == v.id).all()
    photos = db.query(VisitPhoto).filter(VisitPhoto.visit_ref_id == v.id).all()
    return {
        "visit_id": v.visit_id, "location_code": v.location_code, "visit_type": v.visit_type,
        "started_at": v.started_at, "ended_at": v.ended_at, "status": v.status,
        "equipment": [{
            "kind": e.kind, "tag": e.tag, "model": e.model,
            "running_hours": e.running_hours, "pressure_bar": e.pressure_bar, "status": e.status,
        } for e in equips],
        "checklist": [{"item_code": c.item_code, "status": c.status} for c in checks],
        "photos": [{
            "file": p.file_path, "target_type": p.target_type, "target_ref": p.target_ref,
        } for p in photos],
    }
