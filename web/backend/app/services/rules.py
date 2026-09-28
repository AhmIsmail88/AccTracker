# -*- coding: utf-8 -*-
"""Phase 3 — استخراج قواعد الصيانة من الـManuals عبر LLM محلي.

§6.3: تُستخرج القواعد إلى maintenance_rule بحالة DRAFT مع حفظ المصدر {page, section}.
لا يُرسل الـPDF كاملًا للنموذج أبدًا — كل نداء يستقبل مقطعًا واحدًا فقط (§6.2).
"""
import re

from sqlalchemy.orm import Session

from app.db.models import Manual, MaintenanceRule, ManualChunk
from app.services.llm import LLMUnavailable, get_client  # noqa: F401 (get_client قابل للاستبدال في الفحوص)

DEFAULT_CHUNK_LIMIT = 25
MAX_CHUNK_LIMIT = 100

SYSTEM_PROMPT = """You are an industrial maintenance data extractor.
From the manual excerpt, extract EVERY maintenance rule: inspections, lubrication,
oil changes, part replacement, cleaning, calibration, adjustment, limits
(pressure/temperature/vibration), alarms and troubleshooting checks.

Field rules:
- maintenance_type: INSPECTION | LUBRICATION | OIL_CHANGE | PART_REPLACEMENT | CLEANING | CALIBRATION | ADJUSTMENT | THRESHOLD | ALARM | OTHER
- interval_hours / interval_days: numeric interval when stated ("every 2,000 operating hours" -> 2000); else null
- threshold_value / threshold_unit: limit values ("vibration 4.5 mm/s" -> 4.5, "mm/s"); else null
- description: one short actionable sentence keeping original terms and numbers
- confidence: "high" when explicit in text, "medium" when implied, "low" when uncertain

Only extract rules supported by the excerpt. Output pure JSON only:
{"rules": [{"maintenance_type": "...", "interval_hours": null, "interval_days": null, "threshold_value": null, "threshold_unit": null, "description": "...", "confidence": "high"}]}
If the excerpt has no maintenance rules, return {"rules": []}."""

_RULE_HINT_RE = re.compile(
    r"(interval|every\s+\d|\d[\d,.]*\s*(hours?|hrs?|days?|months?)\b|inspect|lubricat|greas|bearings?|seals?|"
    r"oil\s*(change|level|filter)?|filter|replace|clean|check|alarm|pressure|temperature|vibration|"
    r"mm/s|bar|psi|rpm|tolerance|wear|torque|flush|"
    r"صيانة|فحص|تزييت|تغيير|ساعات|ضغط|حرارة|اهتزاز|محمل|مانع|فلتر|تنظيف|شحم)",
    re.IGNORECASE,
)

_VALID_TYPES = (
    "INSPECTION", "LUBRICATION", "OIL_CHANGE", "PART_REPLACEMENT", "CLEANING",
    "CALIBRATION", "ADJUSTMENT", "THRESHOLD", "ALARM", "OTHER",
)


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def _rule_from_llm(raw: dict, manual: Manual, chunk: ManualChunk):
    if not isinstance(raw, dict):
        return None
    description = str(raw.get("description") or "").strip()
    if not description:
        return None
    mtype = str(raw.get("maintenance_type") or "OTHER").strip().upper()
    if mtype not in _VALID_TYPES:
        mtype = "OTHER"
    confidence = str(raw.get("confidence") or "medium").strip().lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"
    interval_days = _num(raw.get("interval_days"))
    unit = raw.get("threshold_unit")
    unit = str(unit).strip()[:20] if unit else None
    return {
        "maintenance_type": mtype,
        "interval_hours": _num(raw.get("interval_hours")),
        "interval_days": int(interval_days) if interval_days is not None else None,
        "threshold_value": _num(raw.get("threshold_value")),
        "threshold_unit": unit,
        "description": description[:500],
        "confidence": confidence,
        "source_page": chunk.page,
        "source_section": chunk.section_title,
    }


def _key(mtype, interval_hours, description):
    hours = None
    if interval_hours is not None:
        try:
            hours = round(float(interval_hours), 4)
        except (TypeError, ValueError):
            hours = None
    return ((mtype or "").strip().upper(), hours, (description or "").strip()[:80].lower())


def _existing_keys(db: Session, manual_id: int):
    keys = set()
    for row in db.query(MaintenanceRule).filter(MaintenanceRule.manual_id == manual_id).all():
        keys.add(_key(row.maintenance_type, row.interval_hours, row.description))
    return keys


def get_candidates(db: Session, manual_id: int, limit: int):
    rows = (
        db.query(ManualChunk)
        .filter(ManualChunk.manual_id == manual_id)
        .order_by(ManualChunk.page, ManualChunk.chunk_index)
        .all()
    )
    picked = []
    for chunk in rows:
        if _RULE_HINT_RE.search(chunk.text or ""):
            picked.append(chunk)
            if limit and len(picked) >= limit:
                break
    return picked


def _build_prompt(manual: Manual, chunk: ManualChunk) -> str:
    equipment = " ".join(x for x in (manual.manufacturer, manual.model) if x) or "(unknown)"
    return "\n".join([
        "Extract maintenance rules from this manual excerpt.",
        "Equipment: %s (%s)" % (equipment, manual.equipment_kind or "unknown"),
        "Page: %s" % chunk.page,
        "Section: %s" % (chunk.section_title or ""),
        "Excerpt:",
        "---",
        chunk.text or "",
        "---",
        'Respond with pure JSON: {"rules": [{"maintenance_type": "...", "interval_hours": null, "interval_days": null, "threshold_value": null, "threshold_unit": null, "description": "...", "confidence": "high|medium|low"}]}. Return {"rules": []} if none.',
    ])


def extract_rules(db: Session, manual_id: int, *, llm_client=None, limit_chunks: int = DEFAULT_CHUNK_LIMIT) -> dict:
    manual = db.get(Manual, manual_id)
    if manual is None:
        raise LookupError("manual not found")
    limit = max(1, min(int(limit_chunks or DEFAULT_CHUNK_LIMIT), MAX_CHUNK_LIMIT))
    client = llm_client or get_client()

    candidates = get_candidates(db, manual_id, limit)
    known = _existing_keys(db, manual_id)
    created = 0
    processed = 0
    errors = 0

    for chunk in candidates:
        processed += 1
        try:
            data = client.generate_json(system=SYSTEM_PROMPT, prompt=_build_prompt(manual, chunk))
        except LLMUnavailable:
            if processed == 1:
                raise
            errors += 1
            continue
        for raw in (data.get("rules") or []):
            rule = _rule_from_llm(raw, manual, chunk)
            if rule is None:
                continue
            key = _key(rule["maintenance_type"], rule["interval_hours"], rule["description"])
            if key in known:
                continue
            known.add(key)
            db.add(MaintenanceRule(
                manual_id=manual.id,
                equipment_kind=manual.equipment_kind,
                model=manual.model,
                maintenance_type=rule["maintenance_type"],
                interval_hours=rule["interval_hours"],
                interval_days=rule["interval_days"],
                threshold_value=rule["threshold_value"],
                threshold_unit=rule["threshold_unit"],
                description=rule["description"],
                source_page=rule["source_page"],
                source_section=rule["source_section"],
                confidence=rule["confidence"],
                status="DRAFT",
            ))
            created += 1

    db.commit()
    return {
        "manual_id": manual_id,
        "model": getattr(client, "model", "unknown"),
        "candidates": len(candidates),
        "processed": processed,
        "rules_created": created,
        "errors": errors,
    }


def rule_to_dict(row: MaintenanceRule) -> dict:
    return {
        "id": row.id,
        "manual_id": row.manual_id,
        "equipment_kind": row.equipment_kind,
        "model": row.model,
        "maintenance_type": row.maintenance_type,
        "interval_hours": row.interval_hours,
        "interval_days": row.interval_days,
        "threshold_value": row.threshold_value,
        "threshold_unit": row.threshold_unit,
        "description": row.description,
        "source_page": row.source_page,
        "source_section": row.source_section,
        "confidence": row.confidence,
        "status": row.status,
    }
