# -*- coding: utf-8 -*-
"""المخزون — قطع الغيار وحركاتها (§33 Phase 6).

- الرصيد يُحسب من الحركات نفسها (IN +, OUT −, RETURN +, ADJUST ±) — مصدر واحد للحقيقة.
- اقتراحات الشراء: القطع التي وصل رصيدها إلى حد إعادة الطلب (min_stock).
"""
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import SparePart, StockMovement

MOVEMENT_TYPES = ("IN", "OUT", "RETURN", "ADJUST")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def part_to_dict(p: SparePart, stock: float = None) -> dict:
    out = {
        "id": p.id,
        "part_code": p.part_code,
        "name": p.name,
        "manufacturer": p.manufacturer,
        "model": p.model,
        "unit": p.unit,
        "min_stock": p.min_stock,
        "unit_cost": p.unit_cost,
        "notes": p.notes,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
    if stock is not None:
        out["stock"] = round(stock, 3)
        out["low_stock"] = stock <= (p.min_stock or 0.0)
    return out


def stock_level(db: Session, part_id: int) -> float:
    rows = (
        db.query(StockMovement.movement_type, func.coalesce(func.sum(StockMovement.qty), 0.0))
        .filter(StockMovement.part_id == part_id)
        .group_by(StockMovement.movement_type)
        .all()
    )
    totals = {t: float(v) for t, v in rows}
    return (
        totals.get("IN", 0.0)
        + totals.get("RETURN", 0.0)
        - totals.get("OUT", 0.0)
        + totals.get("ADJUST", 0.0)
    )


def create_part(db: Session, *, part_code: str, name: str, manufacturer: str = "", model: str = "",
                unit: str = "قطعة", min_stock: float = 0.0, unit_cost: float = None,
                notes: str = "") -> dict:
    code = (part_code or "").strip().upper()
    if not code:
        raise ValueError("part_code is required")
    if not (name or "").strip():
        raise ValueError("name is required")
    existing = db.query(SparePart).filter(SparePart.part_code == code).first()
    if existing is not None:
        raise ValueError("part_code موجود بالفعل: %s" % code)
    p = SparePart(
        part_code=code,
        name=name.strip(),
        manufacturer=manufacturer.strip() or None,
        model=model.strip() or None,
        unit=(unit or "قطعة").strip(),
        min_stock=float(min_stock or 0.0),
        unit_cost=float(unit_cost) if unit_cost is not None else None,
        notes=notes.strip() or None,
    )
    db.add(p)
    db.commit()
    return part_to_dict(p, stock=0.0)


def list_parts(db: Session, *, low_only: bool = False) -> list:
    parts = db.query(SparePart).order_by(SparePart.part_code).all()
    out = []
    for p in parts:
        row = part_to_dict(p, stock=stock_level(db, p.id))
        if low_only and not row["low_stock"]:
            continue
        out.append(row)
    return out


def add_movement(db: Session, *, part_id: int, movement_type: str, qty: float,
                 work_order_id: int = None, reference: str = "", note: str = "") -> dict:
    mtype = (movement_type or "").strip().upper()
    if mtype not in MOVEMENT_TYPES:
        raise ValueError("movement_type must be one of %s" % ", ".join(MOVEMENT_TYPES))
    try:
        value = float(qty)
    except (TypeError, ValueError):
        raise ValueError("qty must be a number")
    if value <= 0:
        raise ValueError("qty must be > 0")
    part = db.get(SparePart, part_id)
    if part is None:
        raise LookupError("part not found")

    # لا نخرج أكثر من الرصيد المتاح
    if mtype == "OUT":
        level = stock_level(db, part_id)
        if value > level + 1e-9:
            raise ValueError("الرصيد غير كافٍ: المتاح %.3f %s" % (level, part.unit))

    m = StockMovement(
        part_id=part_id,
        movement_type=mtype,
        qty=value,
        work_order_id=work_order_id,
        reference=reference.strip() or None,
        note=note.strip() or None,
        created_at=_now(),
    )
    db.add(m)
    part.updated_at = _now()
    db.commit()
    return {
        "id": m.id, "part_id": part_id, "movement_type": mtype, "qty": value,
        "work_order_id": work_order_id, "created_at": m.created_at,
        "stock_after": round(stock_level(db, part_id), 3),
    }


def list_movements(db: Session, *, part_id: int = None, work_order_id: int = None, limit: int = 100) -> list:
    q = db.query(StockMovement)
    if part_id:
        q = q.filter(StockMovement.part_id == part_id)
    if work_order_id:
        q = q.filter(StockMovement.work_order_id == work_order_id)
    rows = q.order_by(StockMovement.id.desc()).limit(limit).all()
    parts = {p.id: p for p in db.query(SparePart).all()}
    return [{
        "id": m.id, "part_id": m.part_id,
        "part_code": parts[m.part_id].part_code if m.part_id in parts else None,
        "part_name": parts[m.part_id].name if m.part_id in parts else None,
        "movement_type": m.movement_type, "qty": m.qty,
        "work_order_id": m.work_order_id, "reference": m.reference,
        "note": m.note, "created_at": m.created_at,
    } for m in rows]


def purchasing_suggestions(db: Session) -> list:
    """اقتراحات شراء: كل قطعة رصيدها ≤ حد إعادة الطلب."""
    out = []
    for p in db.query(SparePart).order_by(SparePart.part_code).all():
        level = stock_level(db, p.id)
        if level <= (p.min_stock or 0.0):
            suggested = max((p.min_stock or 0.0) * 2 - level, 1.0)
            out.append({
                "part_id": p.id,
                "part_code": p.part_code,
                "name": p.name,
                "unit": p.unit,
                "stock": round(level, 3),
                "min_stock": p.min_stock,
                "suggested_qty": round(suggested, 3),
                "est_cost": round(suggested * p.unit_cost, 2) if p.unit_cost else None,
            })
    return out
