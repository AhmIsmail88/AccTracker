# -*- coding: utf-8 -*-
"""AI Chat (§28) — مساعد الصيانة الذكي: RAG على المانوالات + سياق الأسطول.

المبدأ (§10): لا نرسل المانوال كله للنموذج — النظام «يجمع» السياق حتميًا:
  1) ملخص الأسطول (حالة كل أصل + ساعات + المتبقي)
  2) التنبيهات المفتوحة (أعلى 10)
  3) الأصول المذكورة في السؤال (تفاصيل + قراءات + قواعد)
  4) مقتطفات المانوال ذات الصلة (FTS على السؤال + قواعد الأصول المذكورة)

ثم يرسل Context مختصر إلى الـLLM ويعيد إجابة Structured JSON:
  {answer, related_assets, sources} — والمصادر تُتحقق فعليًا (§16)
  والثقة تُحسب حتميًا (§25): HIGH/MEDIUM/LOW.
"""
import json
import re

from sqlalchemy.orm import Session

from app.db.models import Equipment, MaintenanceRule, ManualChunk, Manual
from app.services.alerts import build_alerts
from app.services.llm import get_client
from app.services.maintenance import asset_health
from app.services.manuals import search_chunks

MAX_QUESTION_CHARS = 600
MAX_CHUNKS = 6
MAX_ALERTS = 10

SYSTEM_PROMPT = """أنت "مساعد الصيانة الذكي" في نظام AccTracker لصيانة المضخات والفلترة.
تجيب على أسئلة المهندس بالعربية بالاعتماد حصريًا على السياق المرفق.

قواعد إلزامية:
1. أجب بـ JSON فقط بهذه البنية بالضبط:
{
  "answer": "الإجابة منظمة بفقرات/أسطر قصيرة",
  "related_assets": ["كود أصل", "..."],
  "sources": [{"type": "MANUAL", "manual_id": رقم, "page": رقم}]
}
2. لا تخترع أي أرقام — استخدم فقط الساعات والقراءات والحالات الموجودة في السياق حرفيًا.
3. لا تخترع مراجع مانوال — استخدم فقط manual_id/page الموجودة في مقتطفات السياق.
4. لو السؤال عن الأسطول عمومًا: رتّب الإجابة حسب الأهمية (الأخطر أولًا) واذكر الأكواد.
5. لو البيانات غير كافية: قُل ذلك صراحة واذكر ما ينقص.
6. الاختصار مطلوب — لا حشو.
"""

_VALID_SOURCES = ("MANUAL", "ASSET", "ALERT")


def _mentioned_assets(db: Session, question: str) -> list:
    """الأصول المذكورة صراحةً في السؤال (كود كامل أو قصير مثل MP-03)."""
    q = question.upper()
    out = []
    for e in db.query(Equipment).all():
        code = (e.asset_code or "").upper()
        if not code:
            continue
        short = "-".join(code.split("-")[-2:])
        if code in q or short in q:
            out.append(e)
        elif e.tag and re.search(r"\b%s\b" % re.escape(e.tag.upper()), q) and (e.kind or "").upper() in q:
            out.append(e)
    return out[:4]


def _fleet_summary(db: Session, full: bool = False) -> list:
    rows = []
    for e in db.query(Equipment).order_by(Equipment.asset_code).all():
        h = asset_health(db, e, include_readings=full)
        row = {
            "asset_code": e.asset_code,
            "kind": e.kind,
            "model": e.model,
            "status": h["status"],
            "current_hours": h["current_hours"],
            "hours_remaining": h["hours_remaining"],
            "due_at_hours": h["due_at_hours"],
        }
        if full:
            row["note"] = h.get("note")
            row["baseline_hours"] = h.get("baseline_hours")
            row["readings"] = h.get("readings", [])[-5:]
            row["rules"] = [
                {
                    "maintenance_type": ev.get("maintenance_type"),
                    "interval_hours": ev.get("interval_hours"),
                    "description": ev.get("description"),
                    "manual_id": ev.get("manual_id"),
                    "source_page": ev.get("source_page"),
                    "hours_remaining": ev.get("hours_remaining"),
                }
                for ev in h.get("rules", [])
            ]
        rows.append(row)
    return rows


def _alerts_digest(db: Session) -> list:
    alerts = build_alerts(db)[:MAX_ALERTS]
    return [
        {"type": a["type"], "severity": a["severity"], "asset_code": a.get("asset_code"),
         "visit_id": a.get("visit_id"), "detail": a.get("detail")}
        for a in alerts
    ]


def _manual_chunks(db: Session, question: str, mentioned: list) -> list:
    picked = {}
    # 1) FTS على نص السؤال
    for hit in search_chunks(db, question, limit=MAX_CHUNKS):
        picked[hit["chunk_id"]] = {
            "manual_id": hit["manual_id"],
            "manual_title": hit["manual_title"],
            "page": hit["page"],
            "section": hit["section"],
            "text": hit["text"],
        }
    # 2) صفحات المصدر لقواعد الأصول المذكورة
    for e in mentioned[:2]:
        h = asset_health(db, e, include_readings=False)
        for ev in h.get("rules", [])[:2]:
            mid, page = ev.get("manual_id"), ev.get("source_page")
            if mid is None or page is None:
                continue
            rows = (
                db.query(ManualChunk, Manual)
                .join(Manual, ManualChunk.manual_id == Manual.id)
                .filter(ManualChunk.manual_id == mid, ManualChunk.page == page)
                .limit(2)
                .all()
            )
            for c, m in rows:
                picked.setdefault(c.id, {
                    "manual_id": m.id, "manual_title": m.title, "page": c.page,
                    "section": c.section_title, "text": (c.text or "")[:400],
                })
    return list(picked.values())[:10]


def build_chat_context(db: Session, question: str) -> dict:
    mentioned = _mentioned_assets(db, question)
    fleet = _fleet_summary(db, full=False)
    focus_ids = {e.asset_code for e in mentioned}
    focus = [row for row in _fleet_summary(db, full=True) if row["asset_code"] in focus_ids]
    return {
        "question": question,
        "fleet": fleet,
        "focus_assets": focus,
        "open_alerts": _alerts_digest(db),
        "manual_excerpts": _manual_chunks(db, question, mentioned),
    }


def _clean_str_list(raw) -> list:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()][:8]


def chat_answer(db: Session, question: str, *, llm_client=None) -> dict:
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("question is required")

    context = build_chat_context(db, question)
    client = llm_client or get_client()
    data = client.generate_json(
        system=SYSTEM_PROMPT,
        prompt=json.dumps(context, ensure_ascii=False),
    )

    # تحقق المصادر (§16): احتفظ فقط بما هو موجود فعلًا في السياق
    valid_manuals = {}
    for c in context["manual_excerpts"]:
        valid_manuals.setdefault(c["manual_id"], set()).add(c["page"])
    valid_assets = {row["asset_code"] for row in context["fleet"]}

    sources, dropped = [], 0
    for raw in (data.get("sources") or [])[:10]:
        if not isinstance(raw, dict):
            continue
        stype = str(raw.get("type") or "").upper()
        if stype == "MANUAL":
            mid, page = raw.get("manual_id"), raw.get("page")
            ok = mid in valid_manuals and (page is None or page in valid_manuals.get(mid, set()))
        elif stype in ("ASSET", "ALERT"):
            ok = raw.get("asset_code") in valid_assets
        else:
            ok = False
        if not ok:
            dropped += 1
            continue
        item = {"type": stype, "verified": True}
        if stype == "MANUAL":
            item.update({"manual_id": raw.get("manual_id"), "page": raw.get("page")})
        else:
            item.update({"asset_code": raw.get("asset_code")})
        sources.append(item)

    related = [a for a in _clean_str_list(data.get("related_assets")) if a in valid_assets]

    has_manual = bool(context["manual_excerpts"])
    has_fleet = bool(context["fleet"])
    if has_manual and has_fleet and sources:
        confidence, note = "HIGH", "إجابة مستندة إلى المانوالات + بيانات أسطول فعلية"
    elif has_manual or has_fleet:
        confidence, note = "MEDIUM", "سياق جزئي — راجع المصادر المرفقة"
    else:
        confidence, note = "LOW", "لا توجد بيانات كافية في النظام"

    # تطبيع الإجابة: بعض النماذج ترجع مصفوفة أسطر بدل نص
    raw_answer = data.get("answer")
    if isinstance(raw_answer, list):
        answer = "\n".join(str(x).strip() for x in raw_answer if str(x).strip())
    else:
        answer = str(raw_answer or "").strip()

    return {
        "answer": answer,
        "related_assets": related,
        "sources": sources,
        "sources_dropped": dropped,
        "confidence": confidence,
        "confidence_note": note,
        "model_name": getattr(client, "model", None),
        "context": {
            "fleet": len(context["fleet"]),
            "focus": len(context["focus_assets"]),
            "chunks": len(context["manual_excerpts"]),
            "alerts": len(context["open_alerts"]),
        },
    }
