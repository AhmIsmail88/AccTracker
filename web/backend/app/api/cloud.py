# -*- coding: utf-8 -*-
"""API المزامنة السحابية: حالة الإعداد + سحب الحزم الواردة من Firebase."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.cloud_pull import CloudNotConfigured, pull_from_cloud, service_account_path

router = APIRouter(prefix="/api/cloud", tags=["cloud"])


@router.get("/status")
def cloud_status():
    path = service_account_path()
    return {"configured": path is not None, "service_account_path": path}


@router.post("/pull")
def cloud_pull(limit: int = 20, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 100))
    try:
        return pull_from_cloud(db, limit=safe_limit)
    except CloudNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
