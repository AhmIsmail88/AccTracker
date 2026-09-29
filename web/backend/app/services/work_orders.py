# -*- coding: utf-8 -*-
"""أوامر العمل — إنشاء/تخطيط قطع/إصدار/إرجاع/إغلاق + تكلفة + أحداث المعدات (§20/§21).

- ترقيم أوامر العمل: WO-YYYY-#### تسلسلي.
- الإصدار يُنشئ حركة مخزون OUT + حدث PART_REPLACEMENT على المعدة المرتبطة.
- الإغلاق (DONE) يُسجّل حدث REPAIR على المعدة إن كانت مرتبطة بأصل.
- لا تعديل/إصدار/إرجاع على أوامر مغلقة أو ملغاة.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Equipment, EquipmentEvent, SparePart, WorkOrder, WorkOrderPart
from app.services.stock import add_movement

STATUSES = ("OPEN", "IN_PROGRESS", "DONE", "CANCELLED")
PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
WO_TYPES = ("CORRECTIVE", "PREVENTIVE", "INSPECTION", "INSTALLATION")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wo_event(db: Session, equipment, event_type: str, wo: WorkOrder, description: str) -> None:
    if equipment is None:
        return
    db.add(EquipmentEvent(
        equipment_id=equipment.id,
        event_at=_now(),
        event_type=event_type,
        source="WORK_ORDER",
        reference_id=wo.wo_number,
        description=description,
    ))


def wo_to_dict(db: Session, wo: WorkOrder, *, with_parts: bool = True) -> dict:
    parts = db.query(WorkOrderPart).filter(WorkOrderPart.work_order_id == wo.id).all()
    parts_info = {p.id: p for p in db.query(SparePart).filter(SparePart.id.in_([p.part_id for p in parts])).all()} if parts else {}
    planned_cost = sum((pr.planned_qty or 0.0) * (pr.unit_cost or 0.0) for pr in parts)
    issued_cost = sum((pr.issued_qty or 0.0) * (pr.unit_cost or 0.0) for pr in parts)
    out = {
        "id": wo.id,
        "wo_number": wo.wo_number,
        "asset_code": wo.asset_code,
        "location_code": wo.location_code,
        "title": wo.title,
        "description": wo.description,
        "status": wo.status,
        "priority": wo.priority,
        "source": wo.source,
        "source_ref": wo.source_ref,
        "assigned_to": wo.assigned_to,
        "opened_at": wo.opened_at,
        "updated_at": wo.updated_at,
        "closed_at": wo.closed_at,
        "closing_note": wo.closing_note,
        "parts_count": len(parts),
        "planned_cost": round(planned_cost, 2),
        "parts_cost": round(issued_cost, 2),
    }
    if with_parts:
        out["parts"] = [{
            "id": pr.id,
            "part_id": pr.part_id,
            "part_code": parts_info[pr.part_id].part_code if pr.part_id in parts_info else None,
            "part_name": parts_info[pr.part_id].name if pr.part_id in parts_info else None,
            "unit": parts_info[pr.part_id].unit if pr.part_id in parts_info else None,
            "planned_qty": pr.planned_qty,
            "issued_qty": pr.issued_qty,
            "returned_qty": pr.returned_qty,
            "unit_cost": pr.unit_cost,
            "cost": round((pr.issued_qty or 0.0) * (pr.unit_cost or 0.0), 2),
        } for pr in parts]
    return out


def _gen_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(WorkOrder).filter(WorkOrder.wo_number.like("WO-%d-%%" % year)).count()
    return "WO-%d-%04d" % (year, count + 1)


def create_wo(db: Session, *, title: str, asset_code: str = "", location_code: str = "",
              description: str = "", priority: str = "MEDIUM", source: str = "MANUAL",
              source_ref: str = "", assigned_to: str = "") -> dict:
    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")
    priority = (priority or "MEDIUM").strip().upper()
    if priority not in PRIORITIES:
        raise ValueError("priority must be one of %s" % ", ".join(PRIORITIES))

    # ربط بالمعدة إن وُجد الأصل (لوراثة الموقع + تسجيل الأحداث)
    equipment = None
    asset_code = (asset_code or "").strip()
    if asset_code:
        equipment = db.query(Equipment).filter(Equipment.asset_code == asset_code).first()

    wo = WorkOrder(
        wo_number=_gen_number(db),
        asset_code=asset_code or None,
        location_code=(location_code or "").strip() or (equipment.location_code if equipment else None),
        title=title,
        description=description.strip() or None,
        status="OPEN",
        priority=priority,
        source=(source or "MANUAL").strip().upper(),
        source_ref=source_ref.strip() or None,
        assigned_to=assigned_to.strip() or None,
        opened_at=_now(),
        updated_at=_now(),
    )
    db.add(wo)
    db.flush()
    _wo_event(db, equipment, "STATUS_CHANGE", wo, "أمر عمل جديد: %s" % wo.title)

    db.commit()
    return wo_to_dict(db, wo)


def list_wo(db: Session, *, status: str = None, asset_code: str = None,
            priority: str = None, limit: int = 100) -> list:
    q = db.query(WorkOrder)
    if status:
        q = q.filter(WorkOrder.status == status.strip().upper())
    if asset_code:
        q = q.filter(WorkOrder.asset_code == asset_code.strip())
    if priority:
        q = q.filter(WorkOrder.priority == priority.strip().upper())
    rows = q.order_by(WorkOrder.id.desc()).limit(min(limit, 500)).all()
    return [wo_to_dict(db, wo) for wo in rows]


def get_wo(db: Session, wo_id: int) -> dict:
    wo = db.get(WorkOrder, wo_id)
    if wo is None:
        raise LookupError("work order not found")
    return wo_to_dict(db, wo, with_parts=True)


def update_wo(db: Session, wo_id: int, *, status: str = None, priority: str = None,
              assigned_to: str = None, closing_note: str = None,
              title: str = None, description: str = None) -> dict:
    wo = db.get(WorkOrder, wo_id)
    if wo is None:
        raise LookupError("work order not found")

    changed_status = False
    if status is not None:
        status = status.strip().upper()
        if status not in STATUSES:
            raise ValueError("status must be one of %s" % ", ".join(STATUSES))
        if status != wo.status:
            wo.status = status
            changed_status = True
            if status in ("DONE", "CANCELLED"):
                wo.closed_at = _now()
    if priority is not None:
        priority = priority.strip().upper()
        if priority not in PRIORITIES:
            raise ValueError("priority must be one of %s" % ", ".join(PRIORITIES))
        wo.priority = priority
    if assigned_to is not None:
        wo.assigned_to = assigned_to.strip() or None
    if title is not None:
        wo.title = title.strip()
    if description is not None:
        wo.description = description.strip() or None
    if closing_note is not None:
        wo.closing_note = closing_note.strip() or None

    if changed_status and wo.asset_code:
        equipment = db.query(Equipment).filter(Equipment.asset_code == wo.asset_code).first()
        if equipment is not None:
            if wo.status == "DONE":
                _wo_event(db, equipment, "REPAIR", wo, "تم إغلاق أمر العمل %s — %s" % (wo.wo_number, wo.title))
            else:
                _wo_event(db, equipment, "STATUS_CHANGE", wo, "أمر العمل %s → %s" % (wo.wo_number, wo.status))

    wo.updated_at = _now()
    db.commit()
    return wo_to_dict(db, wo, with_parts=True)


def _wo_part(db: Session, wo_id: int, part_id: int) -> WorkOrderPart:
    return (
        db.query(WorkOrderPart)
        .filter(WorkOrderPart.work_order_id == wo_id, WorkOrderPart.part_id == part_id)
        .first()
    )


def add_part(db: Session, wo_id: int, *, part_id: int, planned_qty: float,
             unit_cost: float = None) -> dict:
    wo = db.get(WorkOrder, wo_id)
    if wo is None:
        raise LookupError("work order not found")
    if wo.status in ("DONE", "CANCELLED"):
        raise ValueError("لا يمكن تعديل قطع أمر عمل مغلق")
    part = db.get(SparePart, part_id)
    if part is None:
        raise LookupError("part not found")
    try:
        planned = float(planned_qty)
    except (TypeError, ValueError):
        raise ValueError("planned_qty must be a number")
    if planned <= 0:
        raise ValueError("planned_qty must be > 0")

    existing = _wo_part(db, wo_id, part_id)
    if existing is not None:
        existing.planned_qty += planned
        if unit_cost is not None:
            existing.unit_cost = float(unit_cost)
    else:
        db.add(WorkOrderPart(
            work_order_id=wo_id, part_id=part_id, planned_qty=planned,
            unit_cost=float(unit_cost) if unit_cost is not None else (float(part.unit_cost) if part.unit_cost is not None else None),
        ))
    wo.updated_at = _now()
    db.commit()
    return wo_to_dict(db, wo, with_parts=True)


def issue_part(db: Session, wo_id: int, part_id: int, qty: float, note: str = "") -> dict:
    wo = db.get(WorkOrder, wo_id)
    if wo is None:
        raise LookupError("work order not found")
    if wo.status in ("DONE", "CANCELLED"):
        raise ValueError("لا يمكن إصدار قطع لأمر عمل مغلق")
    wp = _wo_part(db, wo_id, part_id)
    if wp is None:
        raise LookupError("part not planned in this work order")
    try:
        value = float(qty)
    except (TypeError, ValueError):
        raise ValueError("qty must be a number")
    if value <= 0:
        raise ValueError("qty must be > 0")
    add_movement(
        db, part_id=part_id, movement_type="OUT", qty=value,
        work_order_id=wo_id, reference=wo.wo_number, note=note,
    )
    wp.issued_qty = (wp.issued_qty or 0.0) + value
    wo.updated_at = _now()

    equipment = None
    if wo.asset_code:
        equipment = db.query(Equipment).filter(Equipment.asset_code == wo.asset_code).first()
    part = db.get(SparePart, part_id)
    _wo_event(db, equipment, "PART_REPLACEMENT", wo,
              "إصدار %s %s (%s) لأمر عمل %s" % (value, (part.unit if part else "قطعة"), part.part_code if part else part_id, wo.wo_number))
    db.commit()
    return wo_to_dict(db, wo, with_parts=True)


def return_part(db: Session, wo_id: int, part_id: int, qty: float, note: str = "") -> dict:
    wo = db.get(WorkOrder, wo_id)
    if wo is None:
        raise LookupError("work order not found")
    if wo.status in ("DONE", "CANCELLED"):
        raise ValueError("لا يمكن إرجاع قطع لأمر عمل مغلق")
    wp = _wo_part(db, wo_id, part_id)
    if wp is None:
        raise LookupError("part not planned in this work order")
    try:
        value = float(qty)
    except (TypeError, ValueError):
        raise ValueError("qty must be a number")
    if value <= 0:
        raise ValueError("qty must be > 0")
    if value > (wp.issued_qty or 0.0) - (wp.returned_qty or 0.0) + 1e-9:
        raise ValueError("الكمية المرتجعة أكبر من المُصدَر غير المرتجع")
    add_movement(
        db, part_id=part_id, movement_type="RETURN", qty=value,
        work_order_id=wo_id, reference=wo.wo_number, note=note,
    )
    wp.returned_qty = (wp.returned_qty or 0.0) + value
    wo.updated_at = _now()
    db.commit()
    return wo_to_dict(db, wo, with_parts=True)
