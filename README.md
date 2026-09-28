# ProTrack — نظام متابعة المواقع والصيانة

مستودع المشروع: تطبيق **Android** للفني (أوفلاين) + تطبيق **Web** للمهندس، يتبادلان
**Visit Package** (تقرير Excel + صور موقعة + توقيع رقمي للجهاز).

> المرجع الأساسي للمعمارية وخطة التنفيذ: `ARCHITECTURE.md` (في الجذر).

## الحالة الحالية

- ✅ **Phase 0 (Contract):** مخططات العقد (`contract/`) + أدوات التحقق والبناء (`tools/`) + فحوص (`tests/`) — بلا تبعيات خارجية.
- ✅ **Phase 1 (Web Core):** باك-إند الويب (`web/backend/`): FastAPI + SQLite + Alembic + شجرة المواقع + استيراد الحزم ودمج التقسيم + مطابقة المعدات.
- ✅ **Phase 2 (Android MVP — الجزء الأول):** مشروع `android/` (Kotlin + Compose + Room) مع إدارة شجرة المواقع أوفلاين.
- ✅ **Phase 2 (الجزء الثاني):** تدفق الزيارة + تصدير حزمة موقّعة (ECDSA P-256 من Android Keystore) + مشاركة — متحقق على هاتف حقيقي Samsung SM-A176B.
- ✅ **Phase 2 (الجزء الثالث):** الكاميرا (CameraX) وGPS (FusedLocation) + ربط الصور بالحزمة
  (بصمة SHA-256 + توقيع الالتقاط + إحداثيات) — متحقق على الهاتف: صورة حقيقية بإحداثيات GPS
  وصلت قاعدة بيانات الويب عبر الحزمة، مع تحديث قراءة المعدة وإعادة استخدام الشجرة بلا تكرار.

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

- إكمال Phase 2: شاشة أول تشغيل (اسم الفني + اللغة).
- Phase 3+: Manuals / Maintenance Engine / AI (راجع `ARCHITECTURE.md` §33/§34).
