# -*- coding: utf-8 -*-
"""عميل LLM محلي (Ollama) — قابل للاستبدال في الفحوص.

متغيرات البيئة:
- PROTRACK_OLLAMA_URL (افتراضي http://127.0.0.1:11434)
- PROTRACK_LLM_MODEL  (افتراضي qwen3.5:9b)
- PROTRACK_LLM_TIMEOUT (ثوانٍ، افتراضي 240)
- PROTRAK_LLM_THINK=1 لتفعيل وضع التفكير (معطّل افتراضيًا لأن مخرجاتنا JSON منظّم)

ملاحظات:
- نماذج التفكير (qwen3.5 وغيرها) قد تصرف ميزانية التوليد كاملةً على «التفكير»
  فيرجع حقل response فارغًا أو مقطوعًا — لذلك نمرّر think=false افتراضيًا
  مع إعادة محاولة تلقائية لنسخ Ollama الأقدم التي لا تعرف هذا الوسيط.
- التحليل النصي يقبل فكّ أسوار ```json إذا تجاهل النموذج قيد format=json.
"""
import json
import os
import re

import httpx

DEFAULT_MODEL = "qwen3.5:9b"


class LLMUnavailable(RuntimeError):
    """تعذّر الوصول للنموذج المحلي أو الرد غير صالح."""


def _parse_json_text(text: str) -> dict:
    """يحلل رد النموذج إلى dict — مع محاولات تنظيف متدرجة."""
    text = (text or "").strip()
    if not text:
        raise LLMUnavailable("رد النموذج فارغ (تحقق من num_predict/وضع التفكير)")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except ValueError:
        pass
    # إزالة أسوار الماركداون إن وُجدت
    t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
    t = re.sub(r"\s*```\s*$", "", t).strip()
    # استخراج أول كائن JSON من النص
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(t[start:end + 1])
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    raise LLMUnavailable("رد النموذج ليس JSON صالحًا")


class OllamaClient:
    def __init__(self, base_url=None, model=None, timeout=None):
        self.base_url = (
            base_url or os.environ.get("PROTRACK_OLLAMA_URL") or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = model or os.environ.get("PROTRACK_LLM_MODEL") or DEFAULT_MODEL
        try:
            self.timeout = float(timeout or os.environ.get("PROTRACK_LLM_TIMEOUT") or 240.0)
        except (TypeError, ValueError):
            self.timeout = 240.0

    def available(self) -> bool:
        try:
            resp = httpx.get(self.base_url + "/api/tags", timeout=4.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self):
        try:
            resp = httpx.get(self.base_url + "/api/tags", timeout=6.0)
            resp.raise_for_status()
            return [m.get("name") for m in (resp.json().get("models") or [])]
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMUnavailable("Ollama غير متاح: %s" % exc)

    def _post_generate(self, payload: dict) -> dict:
        try:
            resp = httpx.post(self.base_url + "/api/generate", json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise LLMUnavailable("Ollama غير متاح: %s" % exc)
        if resp.status_code == 404:
            raise LLMUnavailable(
                "النموذج %s غير مثبّت — نفّذ: ollama pull %s" % (self.model, self.model)
            )
        if resp.status_code != 200:
            raise LLMUnavailable("Ollama HTTP %d: %s" % (resp.status_code, resp.text[:200]))
        try:
            return resp.json()
        except ValueError:
            raise LLMUnavailable("رد Ollama ليس JSON صالحًا")

    def generate_json(self, *, system: str, prompt: str) -> dict:
        think_env = (os.environ.get("PROTRAK_LLM_THINK") or "").strip().lower()
        think = think_env in ("1", "true", "yes", "on")
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": think,
            "options": {"temperature": 0, "num_predict": 2048},
        }
        meta = self._post_generate(payload)
        if meta.get("error") and "think" in str(meta.get("error")).lower():
            # نسخة Ollama قديمة لا تعرف وسيط think
            payload.pop("think", None)
            meta = self._post_generate(payload)

        text = meta.get("response") or ""
        if not text.strip() and (meta.get("thinking") or "").strip():
            # احتياطي: بعض النسخ تضع كل الناتج في thinking — نجرّب الفرز منه
            text = meta.get("thinking") or ""
        return _parse_json_text(text)


def get_client() -> OllamaClient:
    return OllamaClient()
