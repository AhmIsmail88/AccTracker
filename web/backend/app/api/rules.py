# -*- coding: utf-8 -*-
"""API قواعد الصيانة المستخرجة (Phase 3): عرض + اعتماد/رفض/تعديل."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import MaintenanceRule
from app.services.rules import rule_to_dict

router = APIRouter(prefix="/api/rules", tags=["rules"])

_VALID_STATUS = ("DRAFT", "APPROVED", "REJECTED")


class RulePatch(BaseModel):
    status: Optional[str] = None
    maintenance_type: Optional[str] = None
    interval_hours: Optional[float] = None
    interval_days: Optional[int] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    description: Optional[str] = None


@router.get("")
def list_rules(
    status: Optional[str] = None,
    manual_id: Optional[int] = None,
    equipment_kind: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(MaintenanceRule)
    if status:
        query = query.filter(MaintenanceRule.status == status)
    if manual_id is not None:
        query = query.filter(MaintenanceRule.manual_id == manual_id)
    if equipment_kind:
        query = query.filter(MaintenanceRule.equipment_kind == equipment_kind)
    rows = query.order_by(MaintenanceRule.id.desc()).limit(max(1, min(limit, 500))).all()
    return [rule_to_dict(row) for row in rows]


@router.patch("/{rule_id}")
def patch_rule(rule_id: int, patch: RulePatch, db: Session = Depends(get_db)):
    rule = db.get(MaintenanceRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    data = patch.model_dump(exclude_none=True)
    if "status" in data and data["status"] not in _VALID_STATUS:
        raise HTTPException(
            status_code=422,
            detail="status must be one of %s" % ", ".join(_VALID_STATUS),
        )
    for key, value in data.items():
        setattr(rule, key, value)
    db.commit()
    return rule_to_dict(rule)
