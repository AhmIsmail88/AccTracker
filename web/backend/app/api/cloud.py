# -*- coding: utf-8 -*-
"""API المزامنة السحابية: حالة الإعداد + سحب يدوي + سحب دوري (أولًا بأول)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.auto_pull import manager as auto_manager
from app.services.cloud_pull import CloudNotConfigured, pull_from_cloud, service_account_path

router = APIRouter(prefix="/api/cloud", tags=["cloud"])


class AutoSettingsIn(BaseModel):
    enabled: bool
    interval_seconds: int | None = None


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


@router.get("/auto")
def cloud_auto_status():
    return auto_manager.status()


@router.post("/auto")
def cloud_auto_update(payload: AutoSettingsIn):
    return auto_manager.apply(payload.enabled, payload.interval_seconds)


@router.post("/auto/run")
def cloud_auto_run_now():
    """تنفيذ دورة سحب واحدة الآن (حتى لو السحب الدوري متوقف)."""
    return auto_manager.run_once_sync()
