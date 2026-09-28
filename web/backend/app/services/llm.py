# -*- coding: utf-8 -*-
"""عميل LLM محلي (Ollama) — قابل للاستبدال في الفحوص.

متغيرات البيئة:
- PROTRACK_OLLAMA_URL (افتراضي http://127.0.0.1:11434)
- PROTRACK_LLM_MODEL  (افتراضي qwen3.5:9b)
- PROTRACK_LLM_TIMEOUT (ثوانٍ، افتراضي 240)
"""
import json
import os

import httpx

DEFAULT_MODEL = "qwen3.5:9b"


class LLMUnavailable(RuntimeError):
    """تعذّر الوصول للنموذج المحلي أو الرد غير صالح."""


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

    def generate_json(self, *, system: str, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
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
            text = resp.json().get("response") or ""
            data = json.loads(text)
        except (ValueError, AttributeError):
            raise LLMUnavailable("رد النموذج ليس JSON صالحًا")
        if not isinstance(data, dict):
            raise LLMUnavailable("رد النموذج ليس كائن JSON")
        return data


def get_client() -> OllamaClient:
    return OllamaClient()
