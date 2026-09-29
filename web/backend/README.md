# ProTrack — Web Backend (Phase 1)

باك-إند الويب: FastAPI + SQLAlchemy 2 + SQLite (WAL) + Alembic.

## التجهيز

```bash
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m alembic upgrade head
```

## التشغيل

```bash
.venv\Scripts\python -m uvicorn app.main:app --reload
```

واجهات API الأساسية:

| الوصف | المسار |
|---|---|
| Health | `GET /api/health` |
| شجرة المواقع | `GET /api/locations/tree?include_inactive=true` |
| إنشاء/تعديل موقع | `POST /api/locations` · `PATCH /api/locations/{code}` |
| إنهاء "جديد من الميدان" | `POST /api/locations/{code}/review` |
| التعارضات | `GET /api/locations/conflicts` · `POST /api/locations/conflicts/{id}/resolve` |
| استيراد حزمة | `POST /api/imports` (رفع ZIP) |
| سجل الاستيراد | `GET /api/imports` |
| الأصول | `GET /api/assets` · `GET /api/assets/{asset_code}` |
| الزيارات | `GET /api/visits` · `GET /api/visits/{visit_id}` |
| الـManuals | `POST /api/manuals` (رفع PDF) · `GET /api/manuals` · `GET /api/manuals/{id}` · `GET /api/manuals/{id}/chunks` · `GET /api/manuals/search?q=` |
| قواعد الصيانة | `POST /api/manuals/{id}/extract-rules` (LLM محلي) · `GET /api/manuals/{id}/rules` · `GET /api/rules` · `PATCH /api/rules/{id}` (اعتماد/رفض/تعديل) |
| المزامنة السحابية | `GET /api/cloud/status` · `POST /api/cloud/pull` (سحب حزم Firebase واستيرادها) · CLI: `python -m app.scripts.pull_cloud` |
| السحب الدوري (أولًا بأول) | `GET /api/cloud/auto` · `POST /api/cloud/auto` (تشغيل/إيقاف + ضبط الفترة) · `POST /api/cloud/auto/run` (دورة فورية) |

## الفحوص

```bash
.venv\Scripts\python -m pytest
```

## بيانات Seed

```bash
.venv\Scripts\python -m app.scripts.seed make
.venv\Scripts\python -m app.scripts.seed load seed\sample_seed.xlsx
```

## ملاحظات

- قاعدة البيانات الافتراضية: `data/protrack.db` (قابلة للتغيير عبر `PROTRAK_DB` / `PROTRAK_DATA_DIR`).
- الصور المستوردة: `data/photos/<package_id>/`.
- الاستيراد يعيد استخدام فحوص `tools/validate_package.py` — نفس مصدر الحقيقة (توقيع ECDSA + هاشات + قواعد الشيتات).
- قواعد دمج التقسيم مطبقة حرفيًا من §4.5 — والتفاصيل في `contract/README.md`.
- صيغة `asset_code` عند إنشاء أصل من الحزمة: `<LOCATION_CODE>-<ABBREV>-<TAG>` مثل `LOC-001-MP-03`.

## تحزيم سطح المكتب (EXE)

الخادم يخدم واجهة الويب المبنية تلقائيًا من `web/frontend/dist` عند وجودها — يعني EXE واحد فيه اللوحة + الـAPI.

خطوات البناء:

```powershell
# 1) ابنِ الواجهة
cd web\frontend
npm install        # أول مرة فقط
npm run build      # ينتج dist/

# 2) ثبّت PyInstaller (أول مرة فقط)
cd ..\backend
.venv\Scripts\python -m pip install pyinstaller

# 3) ابنِ الـEXE
.venv\Scripts\pyinstaller acctracker_desktop.spec --noconfirm --distpath dist_desktop --workpath build_desktop
```

الناتج: `web\backend\dist_desktop\AccTracker.exe` — دبل-كليك يشغّل اللوحة على `http://127.0.0.1:8000` (أو أول منفذ شاغر) ويفتح المتصفح تلقائيًا.

- مجلد البيانات (قاعدة البيانات + الصور) يُنشأ بجانب الـEXE في `data\`، ويمكن تغييره بـ`PROTRAK_DATA_DIR`.
- لتفعيل السحب السحابي: ضع `firebase-service-account.json` في مجلد `data\` بجانب الـEXE.
- البناء يشمل: الواجهة المبنية + tools/ + contract/ + alembic/ (تحديث قاعدة البيانات تلقائيًا عند التشغيل).
