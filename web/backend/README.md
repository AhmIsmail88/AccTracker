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
| الأصول | `GET /api/assets` · `GET /api/assets/{asset_code}` (مع حالة الصيانة المحسوبة) |
| الزيارات | `GET /api/visits` · `GET /api/visits/{visit_id}` · `GET /api/visits/{visit_id}/photos/{photo_id}/file` (عرض صورة) |
| الـManuals | `POST /api/manuals` (رفع PDF) · `GET /api/manuals` · `GET /api/manuals/{id}` · `GET /api/manuals/{id}/chunks` · `GET /api/manuals/search?q=` |
| قواعد الصيانة | `POST /api/manuals/{id}/extract-rules` (LLM محلي) · `GET /api/manuals/{id}/rules` · `GET /api/rules` · `PATCH /api/rules/{id}` (اعتماد/رفض/تعديل) |
| تحليل AI للأصول |
| المساعد الذكي (RAG §28) | `POST /api/ai/chat` {question} — يجمع سياق الأسطول + التنبيهات + مقتطفات المانوالات ويجيب بمصادر موثّقة | `POST /api/ai/analyze/{asset_code}` (§11 — تحليل ومقترحات بمراجع) · `GET /api/ai/suggestions` · `PATCH /api/ai/suggestions/{id}` (اعتماد/رفض المهندس §14) · `GET /api/ai/status` |
| المخزون — قطع الغيار | `GET /api/stock/parts` (مع الرصيد) · `POST /api/stock/parts` · `GET /api/stock/movements` · `POST /api/stock/movements` (IN/OUT/RETURN/ADJUST) · `GET /api/stock/suggestions` (اقتراحات شراء) |
| الإعدادات (§23) | `GET /api/settings` · `PATCH /api/settings` (grace_hours / soon_percent / soon_min_hours) — تُطبق فورًا على محرك الصيانة |
| الأجهزة والفنيون | `GET /api/devices` (أجهزة رفع الحزم + آخر ظهور + العدد) |
| أوامر العمل | `GET /api/work-orders` · `POST /api/work-orders` · `GET/PATCH /api/work-orders/{id}` · `POST /api/work-orders/{id}/parts` · `.../parts/{part}/issue` + `.../return` (إصدار/إرجاع مع حركة مخزون وأحداث) |
| المزامنة السحابية | `GET /api/cloud/status` · `POST /api/cloud/pull` (سحب حزم Firebase واستيرادها) · CLI: `python -m app.scripts.pull_cloud` |
| OCR للمانوالات الممسوحة | تلقائي عند الرفع (صفحات بلا نص) · `POST /api/manuals/{id}/ocr` (إعادة استخراج) — RapidOCR محلي بالكامل + تفكيك كلمات |
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

- نماذج التفكير (qwen3.5 وأمثالها): عميل Ollama يمرر `think=false` افتراضيًا لأن مخرجاتنا JSON منظّم — نماذج التفكير قد تستهلك ميزانية التوليد كاملةً في التفكير فيرجع الرد فارغًا. لتفعيله: `PROTRAK_LLM_THINK=1`.
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
