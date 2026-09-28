# ProTrack — نظام متابعة المواقع والصيانة

مستودع المشروع: تطبيق **Android** للفني (أوفلاين) + تطبيق **Web** للمهندس، يتبادلان
**Visit Package** (تقرير Excel + صور موقعة + توقيع رقمي للجهاز).

> المرجع الأساسي للمعمارية وخطة التنفيذ: `ARCHITECTURE.md` (في الجذر).

## الحالة الحالية

- ✅ **Phase 0 (Contract):** مخططات العقد (`contract/`) + أدوات التحقق والبناء (`tools/`) + فحوص (`tests/`) — بلا تبعيات خارجية.
- ✅ **Phase 1 (Web Core):** باك-إند الويب (`web/backend/`): FastAPI + SQLite + Alembic + شجرة المواقع + استيراد الحزم ودمج التقسيم + مطابقة المعدات.
- ✅ **Phase 2 (Android MVP — مكتملة):** مشروع `android/` (Kotlin + Compose + Room + CameraX + FusedLocation):
  - إدارة شجرة المواقع أوفلاين (مشروع/منطقة/Zone/موقع) بأكواد تلقائية.
  - أول تشغيل: اسم الفني + اختيار اللغة (عربي/إنجليزي مع RTL).
  - تدفق الزيارة: الموقع ← المعدات بقراءاتها ← بنود العنبر ← مراجعة.
  - الكاميرا (بدون معرض) وGPS: كل صورة ببصمة SHA-256 + توقيع التقاط + إحداثيات.
  - تصدير **حزمة موقّعة** (ECDSA P-256 من Android Keystore) + مشاركة.
  - **متـحقَّقة على جهاز حقيقي (Samsung SM-A176B)** من الهاتف إلى قاعدة بيانات الويب،
    بما فيها تحديث قراءات معدة موجودة بدون تكرار، وصورة بإحداثيات GPS حقيقية.

## تشغيل سريع — أدوات العقد (Phase 0)

```bash
python tools/make_sample_package.py
python tools/validate_package.py contract/samples/valid_package.zip --seen-db tests/_tmp/seen.json
python tests/run_tests.py
```

## تشغيل سريع — الويب (Phase 1)

```bash
cd web/backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload
.venv\Scripts\python -m pytest
```

- API: `http://127.0.0.1:8000/api/health`
- تفاصيل أكثر: `web/backend/README.md`.

## تشغيل سريع — الأندرويد (Phase 2)

```bash
cd android
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:testDebugUnitTest
```

- تفاصيل أكثر: `android/README.md`.

## خريطة العمل القادمة

- Phase 3+: Manuals / Maintenance Engine / AI (راجع `ARCHITECTURE.md` §33/§34).
