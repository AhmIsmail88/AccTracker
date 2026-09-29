# -*- coding: utf-8 -*-
"""فحوص دوال OCR النقية: ترتيب الأسطر + إعادة المسافات (بدون محرك)."""
from app.services import ocr as ocr_service


def test_lines_from_items_reading_order():
    items = [
        ([[0, 100], [50, 100], [50, 120], [0, 120]], "world", 0.9),
        ([[0, 10], [50, 10], [50, 30], [0, 30]], "hello", 0.9),
        ([[60, 10], [110, 10], [110, 30], [60, 30]], "again", 0.8),
    ]
    lines = ocr_service._lines_from_items(items)
    text = "\n".join(" ".join(i["text"] for i in line["items"]) for line in lines)
    assert text == "hello again\nworld"


def test_lines_from_items_skips_malformed():
    items = [
        ([[0, 0], [10, 0]], "bad", 0.5),  # صندوق ناقص
        ([[0, 10], [50, 10], [50, 30], [0, 30]], "ok", 0.9),
    ]
    lines = ocr_service._lines_from_items(items)
    assert len(lines) == 1
    assert lines[0]["items"][0]["text"] == "ok"


def test_respace_long_letter_runs():
    text = ocr_service._respace_long_runs("CENTRIFUGALPUMPBEARINGREPLACEMENT")
    assert " " in text
    assert "centrifugal" in text.lower()


def test_respace_keeps_single_words():
    text = ocr_service._respace_long_runs("MAINTENANCE TROUBLESHOOTING")
    assert text == "MAINTENANCE TROUBLESHOOTING"


def test_respace_digit_boundaries():
    text = ocr_service._respace_long_runs("GREASECHECKEVERY2000HOURS")
    upper = text.upper()
    assert "EVERY" in upper and "2000" in upper and "HOURS" in upper
    assert "EVERY2000" not in upper


def test_respace_protects_short_part_numbers():
    # كتلة قصيرة المقاطع الأبجدية — لا تُمس
    assert ocr_service._respace_long_runs("ABC123456XYZ789") == "ABC123456XYZ789"
