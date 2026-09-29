# -*- coding: utf-8 -*-
"""API التقارير (§15) — بيانات JSON + تصدير CSV."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.reports import REPORT_KINDS, build_report, report_as_csv

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/kinds")
def kinds():
    return {"kinds": list(REPORT_KINDS)}


@router.get("/{kind}")
def get_report(kind: str, db: Session = Depends(get_db)):
    try:
        return build_report(db, kind)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{kind}/export.csv")
def export_csv(kind: str, db: Session = Depends(get_db)):
    try:
        fname, body = report_as_csv(db, kind)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="%s"' % fname},
    )
