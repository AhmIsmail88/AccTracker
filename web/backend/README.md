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
