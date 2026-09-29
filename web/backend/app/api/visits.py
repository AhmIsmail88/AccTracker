# -*- coding: utf-8 -*-
"""API الزيارات المستوردة + عرض ملفات صور الزيارة."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import config
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
            "id": p.id, "target_type": p.target_type, "target_ref": p.target_ref,
            "taken_at": p.taken_at, "lat": p.lat, "lon": p.lon,
            "url": ("/api/visits/%s/photos/%d/file" % (v.visit_id, p.id)) if p.file_path else None,
        } for p in photos],
    }


@router.get("/{visit_id}/photos/{photo_id}/file")
def get_visit_photo_file(visit_id: str, photo_id: int, db: Session = Depends(get_db)):
    """يعرض صورة زيارة — بفحص أمان: الملف لازم يكون داخل مجلد صور البيانات فقط."""
    v = db.query(Visit).filter(Visit.visit_id == visit_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail="visit not found")
    photo = (
        db.query(VisitPhoto)
        .filter(VisitPhoto.id == photo_id, VisitPhoto.visit_ref_id == v.id)
        .first()
    )
    if photo is None or not photo.file_path:
        raise HTTPException(status_code=404, detail="photo not found")
    path = Path(photo.file_path).resolve()
    root = Path(config.PHOTOS_DIR).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=403, detail="forbidden")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file missing")
    return FileResponse(str(path))
