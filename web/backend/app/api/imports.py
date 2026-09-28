# -*- coding: utf-8 -*-
"""API استيراد الحزم وسجل الاستيراد (Import Inbox)."""
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ImportedPackage
from app.services.importer import import_package

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("")
async def upload_package(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    return import_package(db, data, file.filename or "package.zip")


@router.get("")
def list_imports(db: Session = Depends(get_db)):
    rows = db.query(ImportedPackage).order_by(ImportedPackage.id.desc()).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id, "package_id": r.package_id, "filename": r.filename,
            "status": r.status, "device_id": r.device_id,
            "counts": json.loads(r.counts_json) if r.counts_json else {},
            "imported_at": r.imported_at,
        })
    return out
