# ProTrack — نظام متابعة المواقع والصيانة

مستودع المشروع: تطبيق **Android** للفني (أوفلاين) + تطبيق **Web** للمهندس، يتبادلان
**Visit Package** (تقرير Excel + صور موقعة + توقيع رقمي للجهاز).

> المرجع الأساسي للمعمارية وخطة التنفيذ: `ARCHITECTURE.md` (في الجذر). لا يُعدَّل من الأدوات.

## الحالة الحالية — Phase 0 (Contract) ✅

- `contract/` — مخططات JSON + قائمة بنود العنبر + عينات الحزم.
- `tools/` — بناء حزم نموذجية + Validator + أدوات توقيع للتطوير.
  تعمل ببايثون القياسي بدون تبعيات خارجية (فسح التوقيع يستخدم `cryptography` إن توفرت، وإلا تنفيذاً مكافئاً داخلياً).
- `tests/` — فحوص آلية للسيناريوهات: `PASS / FAIL / DUPLICATE / REJECT / FLAG`.

## تشغيل سريع

```bash
:: بناء الحزم النموذجية
python tools/make_sample_package.py

:: فحص حزمة (اختياري: --seen-db لمنع التكرار)
python tools/validate_package.py contract/samples/valid_package.zip --seen-db tests/_tmp/seen.json

:: كل الفحوص
python tests/run_tests.py
```

## خريطة العمل القادمة

- Phase 1: Web Core (FastAPI + SQLite + Locations Tree + Import Inbox).
- Phase 2: Android MVP (شاشات الزيارة + إدارة المواقع + تصدير الحزمة).
- راجع `ARCHITECTURE.md` §33/§34 للتفاصيل الكاملة.
