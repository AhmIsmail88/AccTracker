# -*- coding: utf-8 -*-
"""تحليل الصيانة بالذكاء الاصطناعي (§11) — مخرجات Structured JSON + أدلة إلزامية (§16).

المبادئ:
- الـAI يقرأ ويحلل ويقترح فقط — لا يكتب في قاعدة البيانات شيئًا تشغيليًا (§14).
- كل مقترح يجب أن يشير إلى مرجع من المانوالات المرفقة — المراجع الوهمية تُستبعد.
- الثقة تُحسب حتميًا (§25): HIGH = قاعدة معتمدة + قراءة صالحة؛ MEDIUM = دليل مانوال؛ LOW = بدون.
- الاقتراح يُحفظ بحالة SUGGESTED — والمهندس يعتمد/يرفض.
"""
import json

from sqlalchemy.orm import Session

from app.db.models import AiSuggestion, Equipment, MaintenanceRule, Manual, ManualChunk, VisitChecklist, Visit
from app.services.llm import LLMUnavailable, get_client
from app.services.maintenance import asset_health

VALID_REVIEW = ("APPROVED", "REJECTED")

SYSTEM_PROMPT = """أنت "مهندس صيانة أول" تعمل داخل نظام AccTracker لصيانة المضخات والفلترة.
مهمتك: تحليل حالة الأصل المعطى وإصدار تحليل ومقترحات صيانة مبنية حصريًا على البيانات والمانوالات المرفقة.

قواعد إلزامية:
1. أجب بـ JSON فقط، بدون أي نص خارج الـJSON، بهذه البنية بالضبط:
{
  "summary": "ملخص قصير لحالة الأصل",
  "reason": ["سبب 1", "سبب 2"],
  "maintenance_suggestions": [
    {"action": "الإجراء المقترح", "reason": "لماذا", "source": {"manual_id": رقم, "page": رقم, "section": "اسم القسم"}}
  ],
  "evidence": [
    {"type": "MANUAL", "manual_id": رقم, "page": رقم},
    {"type": "METER_READING", "asset_code": "كود الأصل"}
  ]
}
2. لا تخترع أرقام صفحات أو manual_id — استخدم فقط ما هو موجود في قائمة manuals المرفقة.
3. كل رقم تستخدمه (ساعات، ضغط) لازم يكون موجودًا في البيانات المرفقة حرفيًا.
4. من 1 إلى 3 مقترحات فقط، الأهم أولًا. لو البيانات غير كافية لا تقترح.
5. اكتب بالعربية (المصطلحات التقنية بالإنجليزية عند اللزوم).
"""


def _keywords(text: str) -> bool:
    keys = ("maint", "inspect", "replac", "lubric", "bear", "seal", "hour", "check", "فحص", "صيان")
    t = (text or "").lower()
    return any(k in t for k in keys)


def build_asset_context(db: Session, equipment: Equipment) -> dict:
    """يجمع كل ما يحتاجه التحليل: الأصل + حالته + القراءات + عطلات الفحوص + مقتطفات المانوالات ذات الصلة."""
    health = asset_health(db, equipment, include_readings=True)

    # عطلات الفحوص من زيارات نفس الموقع
    fault_checks = (
        db.query(VisitChecklist, Visit)
        .join(Visit, VisitChecklist.visit_ref_id == Visit.id)
        .filter(Visit.location_code == equipment.location_code, VisitChecklist.status == "FAULT")
        .limit(10)
        .all()
    )

    # المانوالات ذات الصلة: بالكود/الموديل + مانوالات القواعد المعتمدة
    related_manuals = []
    seen_ids = set()
    q = db.query(Manual)
    candidates = q.filter(
        ((Manual.model.isnot(None)) & (Manual.model == equipment.model)) if equipment.model else False
    ).all() if equipment.model else []
    for m in candidates:
        if m.id not in seen_ids:
            related_manuals.append(m)
            seen_ids.add(m.id)
    rule_manual_ids = [
        ev.get("manual_id")
        for ev in health.get("rules", [])
        if ev.get("manual_id") is not None
    ]
    for mid in rule_manual_ids:
        if mid in seen_ids:
            continue
        m = db.get(Manual, mid)
        if m is not None:
            related_manuals.append(m)
            seen_ids.add(m.id)
    # مانوالات بنفس نوع المعدة كخطة أخيرة
    if not related_manuals and equipment.kind:
        for m in db.query(Manual).filter(Manual.equipment_kind == equipment.kind).limit(2):
            related_manuals.append(m)
            seen_ids.add(m.id)

    manuals_ctx = []
    for m in related_manuals[:3]:
        chunks = (
            db.query(ManualChunk)
            .filter(ManualChunk.manual_id == m.id)
            .order_by(ManualChunk.page, ManualChunk.chunk_index)
            .limit(40)
            .all()
        )
        picked = [c for c in chunks if _keywords(c.text)][:6] or chunks[:3]
        manuals_ctx.append({
            "manual_id": m.id,
            "title": m.title,
            "model": m.model,
            "chunks": [
                {"page": c.page, "section": c.section_title, "text": (c.text or "")[:400]}
                for c in picked
            ],
        })

    rules_ctx = [
        {
            "rule_id": ev.get("rule_id"),
            "maintenance_type": ev.get("maintenance_type"),
            "interval_hours": ev.get("interval_hours"),
            "threshold_value": ev.get("threshold_value"),
            "description": ev.get("description"),
            "manual_id": ev.get("manual_id"),
            "source_page": ev.get("source_page"),
            "status": ev.get("status"),
            "hours_remaining": ev.get("hours_remaining"),
            "due_at_hours": ev.get("due_at_hours"),
        }
        for ev in health.get("rules", [])
    ]

    return {
        "asset": {
            "asset_code": equipment.asset_code,
            "location_code": equipment.location_code,
            "kind": equipment.kind,
            "tag": equipment.tag,
            "model": equipment.model,
            "status": equipment.status,
        },
        "health": {
            "status": health["status"],
            "note": health.get("note"),
            "baseline_hours": health.get("baseline_hours"),
            "current_hours": health.get("current_hours"),
            "hours_remaining": health.get("hours_remaining"),
            "due_at_hours": health.get("due_at_hours"),
        },
        "rules": rules_ctx,
        "readings": health.get("readings", [])[-10:],
        "checklist_faults": [
            {"visit_id": v.visit_id, "item_code": c.item_code, "at": v.started_at}
            for c, v in fault_checks
        ],
        "manuals": manuals_ctx,
    }


def _severity(health_status: str) -> str:
    return {
        "FAULT": "CRITICAL",
        "MAINTENANCE_OVERDUE": "CRITICAL",
        "MAINTENANCE_DUE": "WARNING",
        "MAINTENANCE_SOON": "WARNING",
    }.get(health_status, "INFO")


def _confidence(context: dict) -> tuple:
    """الثقة الحتمية (§25) — لا أرقام وهمية."""
    has_rules = bool(context["rules"])
    has_readings = bool(context["readings"])
    has_manual = bool(context["manuals"])
    if has_rules and has_readings:
        return "HIGH", "قاعدة معتمدة مباشرة + قراءة صالحة"
    if has_manual or has_rules:
        return "MEDIUM", "دليل مانوال/قاعدة بدون سجل قراءات كامل"
    return "LOW", "بدون دليل مباشر — تحليل استنتاجي"


def _clean_str_list(raw) -> list:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()][:10]


def analyze_asset(db: Session, asset_code: str, *, llm_client=None, persist: bool = True) -> dict:
    """يحلل أصلاً واحدًا ويعيد اقتراحًا — ويسجله بحالة SUGGESTED (إن persist)."""
    equipment = db.query(Equipment).filter(Equipment.asset_code == asset_code).first()
    if equipment is None:
        raise LookupError("asset not found")

    context = build_asset_context(db, equipment)
    client = llm_client or get_client()
    data = client.generate_json(
        system=SYSTEM_PROMPT,
        prompt=json.dumps(context, ensure_ascii=False),
    )

    valid_manual_ids = {m["manual_id"] for m in context["manuals"]}
    manual_pages = {m["manual_id"]: {c["page"] for c in m["chunks"]} for m in context["manuals"]}

    # المقترحات: تستبعد أي مرجع مانوال وهمي (§16)
    actions, dropped_actions = [], 0
    for raw in (data.get("maintenance_suggestions") or [])[:5]:
        if not isinstance(raw, dict):
            continue
        src = raw.get("source") or {}
        mid = src.get("manual_id")
        page = src.get("page")
        ok = mid in valid_manual_ids and (page in manual_pages.get(mid, set()) if page is not None else True)
        if not ok:
            dropped_actions += 1
            continue
        actions.append({
            "action": str(raw.get("action") or "").strip(),
            "reason": str(raw.get("reason") or "").strip(),
            "source": {"manual_id": mid, "page": page, "section": src.get("section")},
        })

    # الأدلة: تُوسم صالحة/غير صالحة (§16)
    evidence = []
    for raw in (data.get("evidence") or [])[:10]:
        if not isinstance(raw, dict):
            continue
        etype = str(raw.get("type") or "").upper()
        item = {"type": etype}
        if etype == "MANUAL":
            mid = raw.get("manual_id")
            page = raw.get("page")
            item.update({"manual_id": mid, "page": page,
                         "verified": mid in valid_manual_ids and (page in manual_pages.get(mid, set()) if page is not None else True)})
        elif etype in ("METER_READING", "FAULT_HISTORY"):
            item.update({"asset_code": raw.get("asset_code"),
                         "verified": raw.get("asset_code") == equipment.asset_code})
        else:
            item.update({"verified": False})
        evidence.append(item)

    confidence, confidence_note = _confidence(context)

    suggestion = {
        "asset_code": equipment.asset_code,
        "model_name": getattr(client, "model", None),
        "severity": _severity(context["health"]["status"]),
        "confidence": confidence,
        "confidence_note": confidence_note,
        "status": "SUGGESTED",
        "summary": str(data.get("summary") or "").strip(),
        "reason": _clean_str_list(data.get("reason")),
        "maintenance_suggestions": actions,
        "actions_dropped": dropped_actions,
        "evidence": evidence,
    }

    if persist:
        row = AiSuggestion(
            asset_code=equipment.asset_code,
            model_name=suggestion["model_name"],
            severity=suggestion["severity"],
            confidence=confidence,
            confidence_note=confidence_note,
            status="SUGGESTED",
            summary=suggestion["summary"],
            reasons_json=json.dumps(suggestion["reason"], ensure_ascii=False),
            actions_json=json.dumps(actions, ensure_ascii=False),
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            context_json=json.dumps(
                {
                    "health": context["health"],
                    "rules_count": len(context["rules"]),
                    "readings_count": len(context["readings"]),
                    "manuals": [{"manual_id": m["manual_id"], "title": m["title"]} for m in context["manuals"]],
                    "actions_dropped": dropped_actions,
                },
                ensure_ascii=False,
            ),
        )
        db.add(row)
        db.commit()
        suggestion["id"] = row.id
        suggestion["created_at"] = row.created_at
        suggestion["reviewed_at"] = None

    return suggestion


def suggestion_to_dict(row: AiSuggestion) -> dict:
    return {
        "id": row.id,
        "asset_code": row.asset_code,
        "model_name": row.model_name,
        "severity": row.severity,
        "confidence": row.confidence,
        "confidence_note": row.confidence_note,
        "status": row.status,
        "summary": row.summary,
        "reason": json.loads(row.reasons_json or "[]"),
        "maintenance_suggestions": json.loads(row.actions_json or "[]"),
        "evidence": json.loads(row.evidence_json or "[]"),
        "created_at": row.created_at,
        "reviewed_at": row.reviewed_at,
    }


def list_suggestions(db: Session, *, asset_code=None, status=None, limit: int = 50) -> list:
    q = db.query(AiSuggestion)
    if asset_code:
        q = q.filter(AiSuggestion.asset_code == asset_code)
    if status:
        q = q.filter(AiSuggestion.status == status)
    return [suggestion_to_dict(r) for r in q.order_by(AiSuggestion.id.desc()).limit(limit).all()]


def review_suggestion(db: Session, suggestion_id: int, new_status: str) -> dict:
    """قرار المهندس (§14) — اعتماد/رفض فقط، وليس الكتابة في بيانات التشغيل."""
    if new_status not in VALID_REVIEW:
        raise ValueError("status must be one of %s" % ", ".join(VALID_REVIEW))
    row = db.get(AiSuggestion, suggestion_id)
    if row is None:
        raise LookupError("suggestion not found")
    from datetime import datetime, timezone

    row.status = new_status
    row.reviewed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.commit()
    return suggestion_to_dict(row)
