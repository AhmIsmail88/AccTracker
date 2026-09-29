# -*- coding: utf-8 -*-
"""OCR للمانوالات الممسوحة ضوئيًا — محرك RapidOCR يعمل محليًا بالكامل (بدون إنترنت).

- تحميل كسول: لا يُحمَّل المحرك إلا عند أول استخدام فعلي (استيراد سريع للخادم)
- لو المكتبة غير مثبتة: `is_available()` ترجع False ولا يفشل أي استيراد
- `run_ocr` يعيد بناء الأسطر من صناديق الإحداثيات (ترتيب قراءة صحيح) ثم
  يفكّ الكلمات الإنجليزية الملتصقة (wordninja إن توفرت) — لأن نموذج PP-OCR
  قد يسقط المسافات في النصوص الإنجليزية والأرقام داخل النصوص الطويلة.
"""
from __future__ import annotations

import re
import statistics
import threading

_ENGINE = None
_ENGINE_LOCK = threading.Lock()

# كتلة حروف إنجليزية طويلة ملتصقة بلا مسافات (مرشحة للتفكيك)
_LONG_RUN = re.compile(r"[A-Za-z]{12,}")
# كتلة أبجدية-رقمية طويلة (مرشحة لفصل حدود الحروف/الأرقام)
_ALNUM_RUN = re.compile(r"[A-Za-z0-9]{12,}")


class OcrUnavailable(RuntimeError):
    """محرك OCR غير متاح (المكتبة غير مثبتة)."""


def is_available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _get_engine():
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            from rapidocr_onnxruntime import RapidOCR

            _ENGINE = RapidOCR()
        return _ENGINE


def _parse_items(out) -> list:
    """يطبّع نتيجة المحرك إلى [(box, text, conf)]."""
    items = []
    # v1.x: (list[[box, text, score], ...], elapse)
    if isinstance(out, tuple) and len(out) >= 1:
        for item in out[0] or []:
            if isinstance(item, (list, tuple)) and len(item) >= 3 and item[1]:
                try:
                    conf = float(item[2])
                except (TypeError, ValueError):
                    conf = 0.0
                items.append((item[0], str(item[1]), conf))
    else:
        # v2+: كائن نتيجة يحتوي boxes / txts / scores
        boxes = getattr(out, "boxes", None) or []
        txts = getattr(out, "txts", None) or []
        scores = getattr(out, "scores", None) or []
        for i, t in enumerate(txts):
            box = boxes[i] if i < len(boxes) else [[0, 0], [0, 0], [0, 0], [0, 0]]
            try:
                conf = float(scores[i])
            except (TypeError, ValueError, IndexError):
                conf = 0.0
            items.append((box, str(t), conf))
    return items


def _lines_from_items(items: list) -> list:
    """يرتّب الصناديق في أسطر بترتيب قراءة (أعلى→أسفل، يسار→يمين داخل السطر)."""
    parsed = []
    for box, text, conf in items:
        try:
            points = list(box)
            if len(points) < 4:
                continue  # صندوق غير مكتمل (ليس رباعيًا) — تجاهل
            xs = [float(p[0]) for p in points]
            ys = [float(p[1]) for p in points]
        except (TypeError, ValueError, IndexError):
            continue
        parsed.append({
            "top": min(ys),
            "bottom": max(ys),
            "left": min(xs),
            "right": max(xs),
            "text": text,
            "conf": conf,
        })
    if not parsed:
        return []

    heights = [p["bottom"] - p["top"] for p in parsed if p["bottom"] > p["top"]]
    med_h = statistics.median(heights) if heights else 1.0

    parsed.sort(key=lambda p: (p["top"], p["left"]))
    lines: list = []
    for p in parsed:
        cy = (p["top"] + p["bottom"]) / 2.0
        placed = False
        for line in lines:
            if abs(cy - line["cy"]) < 0.6 * max(med_h, 1.0):
                line["items"].append(p)
                line["cy"] = (line["cy"] * (len(line["items"]) - 1) + cy) / len(line["items"])
                placed = True
                break
        if not placed:
            lines.append({"cy": cy, "items": [p]})

    lines.sort(key=lambda l: l["cy"])
    for line in lines:
        line["items"].sort(key=lambda p: p["left"])
    return lines


def _split_alnum_run(run: str) -> str:
    """يفصل حدود الحروف/الأرقام في كتلة طويلة — فقط لو فيها مقطع حروف ≥5.

    «EVERY2000HOURS» → «EVERY 2000 HOURS» مع الحفاظ على أرقام القطع القصيرة
    (مثال محمي: «ABC123456XYZ789» تبقى كما هي).
    """
    parts = re.findall(r"[A-Za-z]+|\d+", run)
    if not any(len(p) >= 5 and p[0].isalpha() for p in parts):
        return run
    return " ".join(parts)


def _respace_long_runs(text: str) -> str:
    """يفكّ الكلمات الإنجليزية الملتصقة (مثل CENTRIFUGALPUMPBEARING) باستخدام wordninja."""
    try:
        import wordninja
    except Exception:
        wordninja = None

    # 1) فصل حدود الأرقام داخل الكتل الطويلة
    text = _ALNUM_RUN.sub(lambda m: _split_alnum_run(m.group(0)), text)

    # 2) تفكيك كتل الحروف الطويلة إلى كلمات
    def repl(match: re.Match) -> str:
        word = match.group(0)
        if wordninja is None:
            return word
        parts = [p for p in wordninja.split(word.lower()) if p]
        if len(parts) <= 1:
            return word
        joined = " ".join(parts)
        return joined.upper() if word.isupper() else joined

    return _LONG_RUN.sub(repl, text)


def run_ocr(png_bytes: bytes) -> tuple[str, float]:
    """يشغّل OCR على صورة PNG ويرجّع (النص بترتيب قراءة مع مسافات، متوسط الثقة 0..1)."""
    engine = _get_engine()
    items = _parse_items(engine(png_bytes))
    if not items:
        return "", 0.0

    lines = _lines_from_items(items)
    if lines:
        text = "\n".join(" ".join(i["text"] for i in line["items"]) for line in lines)
    else:
        text = "\n".join(i[1] for i in items)

    text = _respace_long_runs(text.strip())
    confs = [i[2] for i in items if i[2] > 0]
    mean_conf = (sum(confs) / len(confs)) if confs else 0.0
    return text, round(mean_conf, 4)
