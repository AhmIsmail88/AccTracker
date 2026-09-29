# -*- coding: utf-8 -*-
"""API التنبيهات الحتمية (§22)."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.alerts import build_alerts, counts_by_severity

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_VALID_SEVERITY = ("CRITICAL", "WARNING", "INFO")


@router.get("")
def list_alerts(severity: Optional[str] = None, asset_code: Optional[str] = None,
                location_code: Optional[str] = None, db: Session = Depends(get_db)):
    all_alerts = build_alerts(db)
    counts = counts_by_severity(all_alerts)

    filtered = all_alerts
    if severity:
        wanted = severity.upper()
        if wanted in _VALID_SEVERITY:
            filtered = [a for a in filtered if a["severity"] == wanted]
    if asset_code:
        filtered = [a for a in filtered if a.get("asset_code") == asset_code]
    if location_code:
        filtered = [a for a in filtered if a.get("location_code") == location_code]

    return {
        "counts": counts,
        "total": len(all_alerts),
        "filtered": len(filtered),
        "alerts": filtered,
    }
