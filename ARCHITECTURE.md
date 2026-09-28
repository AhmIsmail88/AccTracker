# نظام متابعة المواقع والصيانة — المعمارية وخطة التنفيذ

> تطبيقان يتبادلان حزمة واحدة: **Visit Package (.zip)** = تقرير Excel + صور مختومة بالتاريخ والوقت + توقيع رقمي للجهاز.

* **Android (الفني):** بسيط جداً، أوفلاين، عربي/إنجليزي، يسجّل الزيارة، عدد المعدات والموديلات وساعات التشغيل والضغط، يصوّر المعدات، ويدير شجرة المواقع (مشروع / منطقة / Zone / موقع) إضافةً وتعديلاً، ويصدّر حزمة Excel + صور موقعة.
* **Web (المهندس):** يستورد الحزمة ويتحقق من هوية المرسل، ويدير الأصول والصيانة وقطع الغيار والمخازن والـManuals.
* **التقسيم الإداري للمواقع:** مشروع / منطقة / Zone / موقع — يديره المستخدم من الأندرويد أوفلاين، وينتقل للويب داخل حزمة الزيارة (Hierarchy Merge).
* **AI Layer:** يعمل بمصدرين:

  1. **Ollama محليًا** باستخدام `Qwen3.5:9b`.
  2. **OpenRouter** كمزود خارجي قابل للتبديل.
* الـAI يقرأ الـManuals وبيانات المعدات والزيارات ويقترح الصيانة ويعطي **حالة للمضخة** بناءً على ساعات التشغيل ومتطلبات الـManual والقراءات التاريخية.
* **القرار النهائي للمهندس**. الـAI لا يعدّل قاعدة البيانات ولا يغلق أوامر صيانة تلقائياً.

---

# 1. المبادئ

1. **الفني يسجّل الأساسيات فقط:** الموقع/الزون + نوع الزيارة + عدد المضخات/المعدات + الموديل + ساعات التشغيل + الضغط + الحالة + بنود العنبر الـ12 + الصور.
2. **الموديل وعدد المعدات أساسيان وليسَا اختيارياً للـUX:** لأنهما يستخدمان لتحديد الأصول وربط الـManual ومتطلبات الصيانة.
3. **العقد بين التطبيقين هو Visit Package**.
4. **Android أوفلاين 100%** — لا سيرفر، لا تسجيل دخول، لا إنترنت مطلوب أثناء الزيارة.
5. **الويب محلي:** قاعدة SQLite واحدة على جهاز المكتب.
6. **القواعد Deterministic أولاً، والـAI ثانياً.**
7. **AI يقرأ ولا يكتب:** أي اقتراح صيانة أو حالة يحتاج اعتماد المهندس قبل تحويله إلى إجراء.
8. **الاستيراد Idempotent:** نفس الحزمة لا تدخل مرتين.
9. **كل حزمة موقعة من الجهاز.**
10. **الصور من كاميرا التطبيق فقط.**
11. **الـManual هو مصدر مرجعي للصيانة:** أي توصية مستخرجة منه يجب أن تحتوي على مرجع للصفحة/القسم إن أمكن.
12. **لا يتم اعتبار ساعات التشغيل وحدها حكماً نهائياً على حالة المضخة:** الحالة تعتمد على قواعد + بيانات التشغيل + متطلبات الـManual + تاريخ الأعطال + القراءات المتاحة.
13. **AI لا يخترع متطلبات صيانة غير موجودة في الـManual دون تمييزها كتوصية تحليلية.**
14. عند عدم وجود دليل كافٍ، يظهر ذلك بوضوح بدلاً من اختلاق حالة.
15. **التقسيم الإداري للمواقع من إدارة المستخدم:** مشروع / منطقة / Zone / موقع، ولكل عنصر كود ثابت (Code) هو هويته بين التطبيقين.
16. **تعديلات التقسيم تنتقل مع حزمة الزيارة وتُدمج Idempotent بالكود:** لا تكرار ولا حذف عند الاستيراد، وأي تعارض بين نسخة الأندرويد والويب يُرفع للمهندس للمراجعة.

---

# 2. الصورة الكبيرة

```text
┌─────────────────────────────┐
│ Android - الفني             │
│ Kotlin + Compose            │
│                             │
│ Offline                     │
│ - Locations Tree            │
│   Project/Region/Zone/Site  │
│ - Add / Edit (Offline)      │
│ - Equipment count           │
│ - Model                     │
│ - Running hours             │
│ - Pressure                  │
│ - Status                    │
│ - 12 Checklist Items        │
│ - Camera + GPS              │
│                             │
│ Export Visit Package        │
└──────────────┬──────────────┘
               │
               │ ZIP
               │
               ▼
┌────────────────────────────────────────┐
│ Web App - Engineer Office              │
│                                        │
│ FastAPI + React + SQLite               │
│                                        │
│ Import → Verify → Review → Commit      │
│                                        │
│ Locations (Tree)                        │
│ Assets                                  │
│ Visits                                  │
│ PM / Corrective Maintenance             │
│ Work Orders                             │
│ Spare Parts / Stock                     │
│ Manuals                                 │
│ Alerts                                  │
│ AI                                      │
└──────────────┬─────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌────────────────┐
│ Ollama      │  │ OpenRouter     │
│ Local       │  │ External       │
│ Qwen3.5:9b  │  │ Configurable   │
└─────────────┘  └────────────────┘
```

---

# 3. تطبيق Android

## 3.1 التقنية

| البند           | الاختيار                                           |
| --------------- | -------------------------------------------------- |
| اللغة/الواجهة   | Kotlin + Jetpack Compose + Material 3              |
| المعمارية       | MVVM بسيطة: UI → ViewModel → Repository → Room     |
| التخزين         | Room (SQLite) للمسودات والسجل، DataStore للإعدادات |
| DI              | Hilt أو يدوي                                       |
| اللغات          | عربي / English + RTL                               |
| Excel           | مكتبة خفيفة مثل `fastexcel`، ويتم اختبارها مبكراً  |
| الكاميرا        | CameraX                                            |
| GPS             | FusedLocationProvider                              |
| التوقيع         | Android Keystore + ECDSA P-256                     |
| ZIP             | ZipOutputStream                                    |
| Minimum Android | Android 8.0 / API 26 مبدئياً                       |

---

# 3.2 تدفق الشاشات

```text
[1] أول تشغيل
    اسم الفني + اللغة
          ↓
[2] إدارة المواقع
    مشروع / منطقة / Zone / موقع
    إضافة عنصر / تعديل عنصر
          ↓
[3] زيارة جديدة
    اختيار الموقع من الشجرة
    (أو إضافة موقع جديد فوراً)
    التاريخ والوقت
    نوع الزيارة
          ↓
[4] المعدات
    Main Pumps
    Submersible Pumps
    Filters
    + Add Equipment
    + Quick Add Model + Quantity
          ↓
[5] بنود العنبر
    12 Checklist Items
          ↓
[6] مراجعة وتصدير
    Summary
    Generate Visit Package
```

---

# 3.2.1 شاشة المعدات

**عدد المعدات والموديل جزء أساسي من تسجيل الزيارة.**

مثال:

```text
Main Pumps
----------------------------
Model: XXXXXX
Quantity: 4

[Create 4 Pumps]

MP-01
Running Hours: 2,340
Pressure: 5.8 bar
Status: Running
📷

MP-02
Running Hours: 2,410
Pressure: 5.7 bar
Status: Running
📷

MP-03
Running Hours: 2,360
Pressure: 5.9 bar
Status: Fault
📷

MP-04
Running Hours: 2,390
Pressure: 5.8 bar
Status: Running
📷
```

### لماذا Model + Quantity مهمان؟

لأن Web يستخدم:

```text
Location
+
Equipment Kind
+
Tag
+
Model
```

لتحديد الأصل وربطه بـ:

* Manual
* PM Schedule
* Running Hours
* Fault History
* Spare Parts
* Maintenance Status

### Quick Add

إذا أدخل الفني:

```text
Model = ABC-500
Quantity = 6
```

يتم إنشاء:

```text
ABC-500 / MP-01
ABC-500 / MP-02
ABC-500 / MP-03
ABC-500 / MP-04
ABC-500 / MP-05
ABC-500 / MP-06
```

ثم يكتب الفني ساعات التشغيل لكل مضخة.

---

# 3.2.2 قواعد تبسيط الاستخدام

* الموديلات السابقة تظهر كاقتراحات.
* عند اختيار موقع يتم اقتراح المعدات المسجلة سابقاً.
* آخر Reading يظهر أسفل خانة ساعات التشغيل.
* إذا كانت القراءة الجديدة أقل من السابقة يظهر Warning.
* يقبل الأرقام العربية والإنجليزية.
* الحفظ تلقائي.
* أقل كتابة ممكنة.
* التصوير متاح لكل معدة ولكل بند.
* عند Fault يقترح التصوير.
* لا يتم منع الفني من إكمال الزيارة بسبب Warning غير حرج.

---

# 3.2.3 شجرة المواقع (Project / Region / Zone / Location)

التقسيم الإداري للمواقع من إدارة المستخدم وليس ثابتاً في الكود، ويتكون من 4 مستويات:

```text
Project
  └── Region
        └── Zone
              └── Location    (المستوى الذي تُسجَّل عليه الزيارة)
```

* الفني يقدر يضيف عنصراً جديداً في أي مستوى (مشروع / منطقة / Zone / موقع).
* الفني يقدر يعدّل اسم أي عنصر، وينقله لأب آخر عند الحاجة.
* لا يوجد حذف مباشر: يُعطَّل العنصر (INACTIVE) بدل حذفه، حتى لا تنكسر مراجع الزيارات القديمة.
* الأكواد تتولّد تلقائياً لكل نوع: `PRJ-xxx` / `RGN-xxx` / `ZN-xxx` / `LOC-xxx`، ولا يتغير الكود بعد الإنشاء.
* كل عنصر له:
  * كود ثابت (Code) — هو الهوية بين الأندرويد والويب.
  * اسم (Name) — قابل للتعديل.
  * حالة (ACTIVE / INACTIVE).
  * آخر تعديل (updated_at) وحالة مزامنة (sync_state).

مثال:

```text
PRJ-001    مشروع الرياض
  RGN-001    المنطقة الشرقية
    ZN-001     محطة الشمال
      LOC-001    غرفة المضخات الرئيسية
      LOC-002    غرفة الفلاتر
    ZN-002     محطة الجنوب
      LOC-003    بئر رقم 3
```

* عند بدء زيارة جديدة يتم اختيار الموقع بالنزول في الشجرة: مشروع / منطقة / Zone / موقع.
* زر "+" متاح في كل مستوى لإضافة عنصر فوراً دون الخروج من شاشة الزيارة.
* تعديلات الشجرة المحلية (Pending) تُصدَّر مع أول حزمة زيارة تالية وتُدمج في الويب Idempotent — تفاصيل الدمج في القسم 4.5.

---

# 3.3 الصور

* CameraX فقط.
* لا Gallery.
* لا ACTION_PICK.
* لا GET_CONTENT.
* الصورة تحفظ في App Private Storage.
* SHA-256 لكل صورة.
* Capture Signature.
* GPS.
* Timestamp.
* Burn-in على الصورة.
* EXIF.
* الحد المقترح 3 صور لكل Checklist Item.
* ضغط الصور إلى ~1600px.
* JPEG quality ~80.

---

# 3.4 نموذج بيانات Android

```text
technician_profile
------------------
name
language


visit
-----
id
location_code
visit_type
started_at
ended_at
notes
status
package_id
exported_at


visit_equipment
---------------
id
visit_id
kind
tag
model
running_hours
pressure_bar
status
note


visit_checklist
---------------
visit_id
item_code
status
note


visit_photo
-----------
id
visit_id
target_type
target_ref
file_path
taken_at
lat
lon
accuracy_m
sha256
capture_sig


known_model
-----------
kind
model


project
-------
id
code
name
status
updated_at
sync_state


region
------
id
code
project_code
name
status
updated_at
sync_state


zone
----
id
code
region_code
name
status
updated_at
sync_state


location
--------
id
code
zone_code
name
status
updated_at
sync_state


last_reading
------------
location_code
kind
tag
running_hours
read_at


device_identity
---------------
device_id
key_alias
fingerprint
enrolled_at
```

**ملاحظة:** `visit.location_code` و `last_reading.location_code` يشيران إلى `location.code`، وقيم `sync_state`: `NEW` / `UPDATED` / `SYNCED`.

---

# 4. Visit Package v1

## 4.1 Structure

```text
Visit_SITE_20260928-1030_Ahmed.zip

├── visit.xlsx
├── photos/
│   ├── IMG_....jpg
│   └── IMG_....jpg
├── manifest.json
└── manifest.sig
```

---

# 4.2 Manifest

```json
{
  "package_id": "uuid",
  "schema_version": 1,
  "created_at": "2026-09-28T10:52:00+03:00",

  "device": {
    "device_id": "uuid",
    "public_key": "<base64 X.509>",
    "fingerprint": "A1B2C3D4"
  },

  "files": [
    {
      "path": "visit.xlsx",
      "sha256": "..."
    },
    {
      "path": "photos/IMG_001.jpg",
      "sha256": "...",
      "taken_at": "2026-09-28T10:45:12+03:00",
      "lat": 12.3456,
      "lon": 23.4567,
      "accuracy_m": 8,
      "capture_sig": "<base64>"
    }
  ]
}
```

**ملاحظة:** `enrollment_code` يستخدم فقط أثناء التسجيل الأول للجهاز ولا يلزم تخزينه داخل كل Package بعد نجاح Enrollment.

---

# 4.3 Excel Sheets

الشيتات الآلية التي يقرأها Web:

```text
_meta
visit
equipment
checklist
locations
photos
```

وشيت:

```text
Report
```

للعرض والطباعة فقط.

---

# 4.4 Equipment Sheet

```text
row_id
visit_id
kind
tag
model
running_hours
pressure_bar
status
note
```

مثال:

```text
1 | VISIT-001 | MAIN_PUMP | 01 | ABC-500 | 2340 | 5.8 | RUNNING
2 | VISIT-001 | MAIN_PUMP | 02 | ABC-500 | 2410 | 5.7 | RUNNING
3 | VISIT-001 | MAIN_PUMP | 03 | ABC-500 | 2360 | 0.0 | FAULT
4 | VISIT-001 | MAIN_PUMP | 04 | ABC-500 | 2390 | 5.8 | RUNNING
```

---

# 4.5 Locations Sheet — عناصر التقسيم

شيت إضافي داخل visit.xlsx يحتوي عناصر التقسيم:

```text
row_id
code
type          -- PROJECT / REGION / ZONE / LOCATION
parent_code
name
status        -- ACTIVE / INACTIVE
updated_at
```

يحتوي على:

1. السلسلة الكاملة للموقع المستخدم في الزيارة (المشروع / المنطقة / الزون / الموقع).
2. أي عنصر تقسيم أضافه أو عدّله الفني محلياً ولم يُصدَّر بعد (Pending Changes).

### Hierarchy Merge Rules — قواعد الدمج في الويب

1. الكود هو الهوية: كود جديد → إنشاء عنصر جديد (source = ANDROID).
2. كود موجود بنفس البيانات → No-op.
3. كود موجود ببيانات مختلفة → Conflict → يظهر للمهندس مع القيمة الحالية والقيمة الواردة و updated_at.
4. اسم مكرر تحت نفس الأب بكود مختلف → اشتباه تكرار → Flag للمراجعة.
5. لا يتم حذف أي عنصر بسبب الاستيراد — التعطيل (INACTIVE) فقط.
6. الاستيراد Idempotent: نفس الحزمة مرتين لا تُنشئ نسخاً مكررة.

العناصر الجديدة القادمة من الميدان تظهر في صفحة Locations بحالة "جديد من الميدان" إلى أن يراجعها المهندس.

---

# 5. تطبيق Web

## 5.1 التقنية

| البند           | الاختيار                                 |
| --------------- | ---------------------------------------- |
| Backend         | Python 3.12 + FastAPI                    |
| ORM             | SQLAlchemy 2                             |
| Migrations      | Alembic                                  |
| Database        | SQLite + WAL + Foreign Keys              |
| Frontend        | React + Vite + TypeScript                |
| UI              | Tailwind + shadcn/ui                     |
| Tables          | TanStack Table                           |
| Charts          | Recharts                                 |
| Excel           | openpyxl                                 |
| Background Jobs | APScheduler                              |
| AI Local        | Ollama                                   |
| Local Model     | `Qwen3.5:9b`                             |
| AI External     | OpenRouter                               |
| PDF             | PyMuPDF / مناسب لاستخراج النص من PDF     |
| OCR             | Tesseract أو OCR engine مناسب عند الحاجة |

---

# 5.2 صفحات Web

1. Dashboard
2. Import Inbox
3. Locations (Project → Region → Zone → Location)
4. Assets
5. Asset Details
6. Visits
7. Preventive Maintenance
8. Corrective Maintenance
9. Work Orders
10. Spare Parts
11. Stock
12. Manuals
13. Alerts
14. AI Chat
15. Reports
16. Devices & Technicians
17. Settings

---

# 6. إدارة الـManuals

## 6.1 رفع Manual

من صفحة:

```text
Manuals
```

المهندس يستطيع:

```text
[Upload PDF]
```

ثم يدخل:

```text
Manufacturer
Model
Equipment Kind
Manual Title
Revision
Date
```

مثال:

```text
Manufacturer: Grundfos
Model: XXXXX
Kind: MAIN_PUMP
Manual: Installation & Maintenance Manual
Revision: Rev.03
```

---

# 6.2 Manual Processing Pipeline

عند رفع PDF:

```text
PDF
 ↓
File Hash
 ↓
PDF Text Extraction
 ↓
OCR إذا كان Scanned PDF
 ↓
Page Segmentation
 ↓
Section Detection
 ↓
Text Chunking
 ↓
Manual Index
 ↓
Maintenance Knowledge
 ↓
Link to Equipment Model
```

لا يتم إرسال الـPDF بالكامل إلى الـLLM في كل سؤال.

يتم أولاً تجهيز الـManual وفهرسته.

---

# 6.3 استخراج معلومات الصيانة من الـManual

النظام يبحث عن معلومات مثل:

```text
Maintenance Interval
Inspection Interval
Lubrication
Bearing Inspection
Mechanical Seal
Oil Change
Filter Replacement
Wear Parts
Inspection Procedure
Recommended Hours
Recommended Days
Alarm Conditions
Operating Limits
Pressure Limits
Temperature Limits
Vibration Limits
Troubleshooting
```

مثال:

إذا وجد في الـManual:

```text
Inspect bearing every 2,000 operating hours.
Replace lubricant every 4,000 operating hours.
```

يتم تحويلها إلى Knowledge Record:

```json
{
  "equipment_model": "ABC-500",
  "maintenance_type": "BEARING_INSPECTION",
  "interval_hours": 2000,
  "source": {
    "manual_id": 12,
    "page": 47,
    "section": "Maintenance"
  }
}
```

**المصدر لا يُحفظ كنص AI فقط؛ يجب الاحتفاظ برقم الصفحة/القسم.**

---

# 6.4 Manual Knowledge Database

إضافة جداول:

```text
manual
------
id
title
manufacturer
model
equipment_kind
revision
file_path
sha256
uploaded_at
status


manual_section
--------------
id
manual_id
page_start
page_end
section_title
text


maintenance_rule
----------------
id
manual_id
equipment_kind
model
maintenance_type
interval_hours
interval_days
threshold_value
threshold_unit
description
source_page
source_section
confidence
status
```

`status`:

```text
DRAFT
APPROVED
REJECTED
```

أي Rule يستخرجها الـAI من الـManual تبدأ:

```text
DRAFT
```

ولا تصبح جزءاً من PM الرسمي إلا بعد اعتماد المهندس.

---

# 7. ربط الـManual بالمضخة

كل Asset يمكن ربطه بـManual:

```text
equipment
    ↓
manufacturer
    ↓
model
    ↓
manual
```

ولو يوجد Manual خاص بالموديل:

```text
ABC-500
   ↓
ABC-500 Maintenance Manual
```

يتم استخدامه في تحليل حالة المضخة.

إذا لم يوجد Manual مطابق:

```text
MANUAL_NOT_AVAILABLE
```

ولا يتم اختلاق Maintenance Interval.

---

# 8. حالة المضخة

النظام يجب أن يعطي حالة واضحة للمضخة، لكن **الحالة ليست قرار AI فقط**.

يتم حسابها من عدة مصادر:

```text
Running Hours
+
Manual Maintenance Requirements
+
Pressure
+
Historical Readings
+
Fault History
+
Checklist
+
Last Maintenance
```

---

# 8.1 حالات المضخة

```text
NORMAL
MAINTENANCE_DUE
MAINTENANCE_OVERDUE
MAINTENANCE_SOON
WARNING
FAULT
CRITICAL
UNKNOWN
```

### مثال

Manual:

```text
Inspection = every 2,000 hours
```

Current:

```text
Last Inspection = 1,850 hours
Current = 1,940 hours
```

الحالة:

```text
MAINTENANCE_SOON
```

أما:

```text
Current = 2,120 hours
```

الحالة:

```text
MAINTENANCE_DUE
```

---

# 8.2 لا تعتمد على الـAI وحده

يجب أن يكون هناك Deterministic Maintenance Engine.

مثال:

```text
current_hours = 2410
last_service_hours = 2000
interval_hours = 500

hours_since_service = 410
```

إذا:

```text
hours_since_service >= 500
```

→ `MAINTENANCE_DUE`

ولو:

```text
hours_since_service >= 400
```

→ `MAINTENANCE_SOON`

النسب والحدود تكون قابلة للضبط.

---

# 8.3 Maintenance Status Engine

```text
Manual Rule
      ↓
Last Maintenance
      ↓
Current Running Hours
      ↓
Calculate Due
      ↓
Check Readings
      ↓
Check Fault History
      ↓
Final Status
```

الـAI يفسر ويحلل، لكنه لا يستبدل الحسابات الأساسية.

---

# 9. AI Architecture

## 9.1 مصدران للـAI

### Local

```text
Ollama
  ↓
Qwen3.5:9b
```

يستخدم للمهام التي يمكن تنفيذها محليًا:

* قراءة وتحليل أجزاء الـManual
* استخراج Maintenance Rules
* تلخيص Manual Sections
* تحليل بيانات المضخة
* إنشاء اقتراحات أولية
* AI Chat
* تحليل الزيارات
* RAG على Manuals

### OpenRouter

يستخدم كـExternal Provider اختياري:

* Model قابل للتغيير.
* يمكن استخدامه عندما تكون المهمة تحتاج نموذجًا أقوى.
* لا يتم تثبيت موديل داخل الكود.
* يمكن تعطيله بالكامل.

---

# 9.2 AI Provider Abstraction

لا يتم ربط التطبيق مباشرة بـQwen أو OpenRouter.

يكون لدينا Interface موحد:

```text
AIProvider
│
├── OllamaProvider
│
└── OpenRouterProvider
```

مثال:

```python
class AIProvider:
    def generate(...)
    def structured(...)
    def embed(...)
```

والإعداد:

```text
AI Provider:
[ Local Ollama ▼ ]

Model:
[ Qwen3.5:9b ▼ ]
```

أو:

```text
AI Provider:
[ OpenRouter ▼ ]

Model:
[ configurable ]
```

---

# 9.3 Ollama Configuration

الإعدادات:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=Qwen3.5:9b
```

ويجب اكتشاف الموديلات الموجودة من Ollama API بدلاً من افتراض وجود موديل واحد.

إذا كان Ollama غير متاح:

```text
Local AI unavailable
```

ويستمر التطبيق في العمل بالقواعد.

---

# 10. Manual RAG

لا نرسل الـManual كله إلى Qwen في كل مرة.

العملية:

```text
Question / Analysis
       ↓
Retrieve relevant Manual chunks
       ↓
Equipment Model filter
       ↓
Maintenance context
       ↓
Running Hours
       ↓
Historical readings
       ↓
Qwen3.5:9b
       ↓
Structured result
```

مثال:

```text
User:
ما حالة MP-03؟
```

النظام يجمع:

```text
Equipment:
ABC-500

Current Hours:
2410

Last Maintenance:
2000

Manual:
ABC-500 Maintenance Manual

Relevant Manual Sections:
- Maintenance Schedule
- Bearing Inspection
- Troubleshooting

Recent Pressure:
5.8 → 5.6 → 5.1 bar

Recent Faults:
1 fault in last 3 visits
```

ثم يرسل Context مختصر إلى الـLLM.

---

# 11. AI Maintenance Analysis

الـAI يخرج Structured JSON وليس نصًا حرًا فقط.

مثال:

```json
{
  "equipment_code": "SITE1-MP-03",
  "model": "ABC-500",

  "status": "MAINTENANCE_DUE",

  "severity": "WARNING",

  "reason": [
    "Running hours exceeded manual maintenance interval",
    "Current hours: 2410",
    "Last maintenance: 2000",
    "Manual interval: 400 hours"
  ],

  "maintenance_suggestions": [
    {
      "action": "Bearing inspection",
      "reason": "Manual maintenance requirement",
      "source": {
        "manual_id": 12,
        "page": 47,
        "section": "Maintenance"
      }
    }
  ],

  "evidence": [
    {
      "source": "manual",
      "ref": "manual#12/page47"
    },
    {
      "source": "meter_reading",
      "ref": "meter_reading#345"
    }
  ],

  "recommended_action":
    "Schedule inspection and verify bearing condition.",

  "requires_engineer_review": true
}
```

---

# 12. AI Alert

أي اقتراح مهم يمكن أن يتحول إلى Alert:

```text
┌───────────────────────────────────────────┐
│ ⚠ Maintenance Due                         │
│                                           │
│ Main Pump MP-03                           │
│ Model: ABC-500                             │
│                                           │
│ Running Hours: 2,410                      │
│ Manual Interval: 2,000 / 400 interval    │
│                                           │
│ Manual: ABC-500 Maintenance Manual       │
│ Page: 47                                  │
│                                           │
│ Reason:                                   │
│ Maintenance interval exceeded.            │
│                                           │
│ Suggested Action:                         │
│ Inspect bearing and lubrication system.   │
│                                           │
│ [View Evidence] [Approve] [Reject]        │
└───────────────────────────────────────────┘
```

---

# 13. Pump Health / Condition View

صفحة الـAsset يجب أن تعرض:

```text
ABC-500 / MP-03

STATUS
● MAINTENANCE DUE

Running Hours
2,410 h

Last Maintenance
2,000 h

Next Maintenance
2,400 h

Manual
ABC-500 Maintenance Manual

Recent Pressure
[Chart]

Running Hours
[Chart]

Fault History
[Timeline]

Maintenance
[Timeline]

AI Insights
[Alerts]
```

---

# 14. AI لا يكتب مباشرة

الـAI يستطيع:

```text
READ
ANALYZE
EXPLAIN
SUGGEST
ALERT
```

ولا يستطيع مباشرة:

```text
DELETE
EDIT ASSET
CHANGE STOCK
CLOSE WORK ORDER
APPROVE MAINTENANCE
CHANGE PM RULE
```

الـEngineer:

```text
AI Suggestion
     ↓
Review
     ↓
Approve / Reject
     ↓
System Action
```

---

# 15. AI Tools — Read Only

Tools:

```text
get_equipment_status(asset_code)

get_equipment_manual(asset_code)

search_manual(asset_code, query)

get_manual_section(manual_id, page, section)

get_maintenance_rules(asset_code)

get_reading_trend(asset_code, days)

get_last_maintenance(asset_code)

get_fault_history(asset_code)

list_overdue_pm()

get_stock_status(part_code?)

compare_visits(location, n)

get_equipment_timeline(asset_code)
```

---

# 16. AI Evidence Requirement

أي AI Alert يجب أن يحتوي على Evidence.

لا يتم حفظ:

```text
"المضخة تبدو سيئة"
```

بدون دليل.

يجب أن يحتوي على:

```text
Manual Evidence
+
Equipment Data
+
Reading / Fault Evidence
```

مثال:

```json
{
  "evidence": [
    {
      "type": "MANUAL",
      "manual_id": 12,
      "page": 47
    },
    {
      "type": "METER_READING",
      "id": 345
    },
    {
      "type": "FAULT_HISTORY",
      "asset_code": "SITE1-MP-03"
    }
  ]
}
```

---

# 17. قاعدة مهمة للـManual

هناك فرق بين:

### Manual Fact

```text
"Inspect bearing every 2,000 hours."
```

و:

### AI Recommendation

```text
"Because the pump has exceeded the interval and pressure
has decreased, schedule an inspection."
```

يجب تخزين الاثنين منفصلين.

الـManual = Source.

الـAI = Interpretation.

---

# 18. قاعدة البيانات

إضافة / تعديل الجداول التالية:

```sql
CREATE TABLE manual (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    equipment_kind TEXT,
    revision TEXT,
    file_path TEXT NOT NULL,
    sha256 TEXT UNIQUE,
    uploaded_at TEXT,
    status TEXT DEFAULT 'READY'
);
```

```sql
CREATE TABLE manual_section (
    id INTEGER PRIMARY KEY,
    manual_id INTEGER NOT NULL REFERENCES manual(id),
    page_start INTEGER,
    page_end INTEGER,
    section_title TEXT,
    text TEXT NOT NULL
);
```

```sql
CREATE TABLE maintenance_rule (
    id INTEGER PRIMARY KEY,
    manual_id INTEGER REFERENCES manual(id),
    equipment_kind TEXT,
    model TEXT,
    maintenance_type TEXT,
    interval_hours REAL,
    interval_days INTEGER,
    threshold_value REAL,
    threshold_unit TEXT,
    description TEXT,
    source_page INTEGER,
    source_section TEXT,
    confidence TEXT,
    status TEXT DEFAULT 'DRAFT'
);
```

```sql
CREATE TABLE manual_chunk (
    id INTEGER PRIMARY KEY,
    manual_id INTEGER NOT NULL REFERENCES manual(id),
    page INTEGER,
    section_title TEXT,
    chunk_index INTEGER,
    text TEXT NOT NULL,
    embedding_ref TEXT
);
```

### جداول التقسيم الإداري (Project / Region / Zone / Location)

```sql
CREATE TABLE project (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    source TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

```sql
CREATE TABLE region (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    project_id INTEGER NOT NULL REFERENCES project(id),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    source TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

```sql
CREATE TABLE zone (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    region_id INTEGER NOT NULL REFERENCES region(id),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    source TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

```sql
CREATE TABLE location (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    zone_id INTEGER NOT NULL REFERENCES zone(id),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    source TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

```sql
CREATE TABLE hierarchy_conflict (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    code TEXT NOT NULL,
    incoming_value TEXT,
    existing_value TEXT,
    source_package TEXT,
    detected_at TEXT,
    status TEXT DEFAULT 'OPEN'
);
```

**ملاحظات:**

* `equipment.location_code` يشير إلى `location.code`.
* `source` = `ANDROID` أو `WEB` أو `SEED`.
* العناصر الجديدة القادمة من الحزم تظهر في صفحة Locations بحالة "جديد من الميدان" إلى أن يراجعها المهندس.
* الأكواد تتولّد أوفلاين، لذلك قد يحدث تعارض كود أو اسم — يُكتشف عند الدمج ويُرفع للمهندس (Hierarchy Merge Rules في القسم 4.5).

---

# 19. تعديل Equipment

```sql
CREATE TABLE equipment (
    id INTEGER PRIMARY KEY,
    asset_code TEXT UNIQUE NOT NULL,
    location_code TEXT NOT NULL REFERENCES location(code),

    kind TEXT NOT NULL,

    name TEXT,
    manufacturer TEXT,
    model TEXT,
    serial_no TEXT,

    power_kw REAL,
    flow_m3h REAL,
    head_bar REAL,
    voltage REAL,

    installed_on TEXT,
    warranty_until TEXT,

    status TEXT DEFAULT 'RUNNING',

    running_hours REAL,
    running_hours_at TEXT,

    manual_id INTEGER REFERENCES manual(id),

    notes TEXT
);
```

---

# 20. Work Order Parts

إضافة:

```sql
CREATE TABLE work_order_part (
    id INTEGER PRIMARY KEY,
    work_order_id INTEGER REFERENCES work_order(id),
    part_id INTEGER REFERENCES spare_part(id),
    planned_qty REAL,
    issued_qty REAL DEFAULT 0,
    returned_qty REAL DEFAULT 0,
    unit_cost REAL
);
```

بحيث نفرق بين:

```text
Planned
Issued
Returned
Actual Consumption
```

---

# 21. Equipment Timeline

إضافة:

```sql
CREATE TABLE equipment_event (
    id INTEGER PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    event_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT,
    reference_id TEXT,
    description TEXT
);
```

Events:

```text
INSTALLATION
VISIT
FAULT
REPAIR
PM
PART_REPLACEMENT
STATUS_CHANGE
MODEL_CHANGE
MANUAL_ASSIGNED
```

---

# 22. Deterministic Alert Engine

القواعد الأساسية:

```text
1. PM Due
2. PM Soon
3. Running Hours Anomaly
4. Pressure Anomaly
5. Repeated Fault
6. Critical Checklist Fault
7. Missing Visit
8. Low Stock
9. Model Conflict
10. GPS / Photo Warning
11. Manual Maintenance Due
12. Manual Operating Limit Exceeded
```

---

# 23. Manual + Running Hours Logic

مثال:

```text
Manual:
Inspection every 2000 hours

Last Inspection:
10000 hours

Current:
11950 hours
```

النتيجة:

```text
50 hours remaining
```

الحالة:

```text
MAINTENANCE_SOON
```

عند:

```text
12000 hours
```

تصبح:

```text
MAINTENANCE_DUE
```

وعند:

```text
12100 hours
```

تبقى:

```text
MAINTENANCE_OVERDUE
```

مع إمكانية إضافة Grace Period من Settings.

---

# 24. Manual Operating Limits

إذا وجد الـManual حدود تشغيل:

```text
Maximum Pressure
Maximum Temperature
Minimum Flow
Maximum Vibration
Maximum Running Hours
```

يتم إنشاء Rules.

مثال:

```text
Manual:
Maximum operating pressure = 8 bar

Current:
9.2 bar
```

→

```text
CRITICAL
```

لكن فقط إذا كانت الوحدة والشرط والـmeasurement متوافقة مع Manual Evidence.

---

# 25. AI Confidence

لا نستخدم أرقامًا وهمية مثل:

```text
87% confidence
```

بدون Calibration.

بدلاً من ذلك:

```text
HIGH
MEDIUM
LOW
```

ويجب توضيح مصدر الثقة:

```text
HIGH:
Direct Manual Rule + Valid Reading

MEDIUM:
Manual Evidence + Historical Pattern

LOW:
AI inference with insufficient direct evidence
```

---

# 26. AI Provider Selection

Settings:

```text
AI Provider
────────────────────────

○ Local Ollama
○ OpenRouter
○ Disabled

Local Model
[ Qwen3.5:9b ]

Ollama URL
[ http://localhost:11434 ]

OpenRouter Model
[ configurable ]

[ Test Connection ]
```

---

# 27. Privacy

Default:

```text
Send Personal Names to External AI: OFF
Send Phone Numbers: OFF
Send GPS: OFF
Send Photos: OFF
```

عند استخدام Ollama:

```text
Data remains on the local machine.
```

عند استخدام OpenRouter:

```text
Only required context is sent.
```

لا يتم إرسال SQLite بالكامل إلى أي LLM.

---

# 28. AI Chat

مثال:

```text
User:
أي مضخة محتاجة صيانة قريب؟

System:
1. اقرأ PM rules
2. اقرأ running hours
3. اقرأ آخر maintenance
4. اقرأ faults
5. اقرأ relevant manual sections
6. Analyze
7. Return evidence
```

مثال Response:

```text
MP-03

Status:
MAINTENANCE_SOON

Reason:
Current running hours are approaching the
maintenance interval defined in the manual.

Current:
2,350 h

Maintenance threshold:
2,400 h

Manual:
ABC-500 Maintenance Manual
Page 47

Recommendation:
Schedule inspection before reaching 2,400 h.
```

---

# 29. AI Cost / Performance Strategy

## Local Ollama

يفضل استخدامه في:

```text
Manual extraction
Manual summarization
RAG
Routine equipment analysis
Local AI Chat
```

## OpenRouter

يمكن استخدامه في:

```text
Complex reasoning
Large Manual analysis
Advanced cross-visit analysis
Tasks where local model quality is insufficient
```

لكن التطبيق لا يعتمد على OpenRouter لكي يعمل.

---

# 30. Fail-Safe

إذا فشل AI:

```text
Ollama unavailable
```

أو:

```text
OpenRouter unavailable
```

النظام يستمر:

```text
Database ✓
Visits ✓
Maintenance Rules ✓
Deterministic Alerts ✓
Stock ✓
Reports ✓
```

ويظهر:

```text
AI Analysis unavailable
```

---

# 31. AI Evaluation

يجب إنشاء Eval Set ثابت:

```text
Manual extraction tests
Maintenance interval tests
Running-hour tests
Fault-history tests
Pressure anomaly tests
Arabic questions
English questions
No-evidence questions
Conflicting-data questions
```

الـAI لا يُعتبر ناجحاً لأنه أعطى إجابة جيدة مرة واحدة.

---

# 32. Project Structure

```text
repo/
│
├── docs/
│   ├── architecture.md
│   ├── visit-package.v1.md
│   ├── locations-hierarchy.md
│   ├── device-signing.md
│   └── ai-manual-spec.md
│
├── contract/
│   ├── visit_package.schema.json
│   ├── manifest.schema.json
│   ├── checklist_items.json
│   ├── locations.schema.json
│   └── samples/
│
├── android/
│
└── web/
    │
    ├── backend/
    │   └── app/
    │       ├── api/
    │       ├── domain/
    │       │   ├── assets/
    │       │   ├── maintenance/
    │       │   ├── stock/
    │       │   └── alerts/
    │       │
    │       ├── importers/
    │       ├── manuals/
    │       │   ├── parser/
    │       │   ├── extractor/
    │       │   ├── chunker/
    │       │   └── rag/
    │       │
    │       ├── ai/
    │       │   ├── providers/
    │       │   │   ├── ollama.py
    │       │   │   └── openrouter.py
    │       │   ├── tools/
    │       │   ├── prompts/
    │       │   ├── schemas/
    │       │   └── evaluator/
    │       │
    │       ├── db/
    │       └── tests/
    │
    └── frontend/
        └── src/
```

---

# 33. خطة التنفيذ الجديدة

## Phase 0 — Contract

```text
visit_package.schema.json (ويشمل شيت locations)
manifest.schema.json
checklist_items.json
locations.schema.json
sample packages
signature verification
package validator
hierarchy merge rules
```

Acceptance:

```text
Valid package → PASS
Modified package → FAIL
Duplicate package → DUPLICATE
Unsigned package → REJECT
Invalid photo → FLAG
Hierarchy conflict → FLAG
```

---

## Phase 1 — Web Core

```text
FastAPI
SQLite
Alembic
Seed workbook
Locations Tree
Assets
Visits
Import Inbox + Hierarchy Merge
```

---

## Phase 2 — Android MVP

```text
6 screens
Arabic / English
Locations Tree (Add / Edit)
Equipment count
Model
Running hours
Pressure
Checklist
Camera
GPS
Signing
ZIP export (يشمل عناصر التقسيم)
```

**Acceptance:**

الفني يقدر:

```text
إدارة شجرة المواقع (إضافة / تعديل)
+
زيارة على Location
+
4 Main Pumps
+
Model
+
Hours
+
Pressure
+
Checklist
+
Photos
```

وتصل الحزمة للـWeb ويتم استيرادها بدون أخطاء، وتُدمج عناصر التقسيم Idempotent.

---

## Phase 3 — Manuals

```text
PDF Upload
PDF Hash
Text Extraction
OCR
Page Detection
Chunking
Manual Search
Manual → Model Linking
Maintenance Rule Extraction
Manual Evidence
```

---

## Phase 4 — Maintenance Engine

```text
Running Hours
+
Manual Rules
+
Last Maintenance
+
Readings
+
Fault History
        ↓
Maintenance Status
        ↓
Alerts
```

---

## Phase 5 — AI

```text
Ollama
Qwen3.5:9b
        +
OpenRouter
        ↓
AI Provider Layer
        ↓
Manual RAG
        ↓
Equipment Analysis
        ↓
AI Alerts
        ↓
AI Chat
```

---

## Phase 6 — Stock & Work Orders

```text
Spare Parts
Stock
Work Orders
Work Order Parts
Purchasing Suggestions
Cost Tracking
```

---

## Phase 7 — Advanced AI

لاحقاً:

```text
Image Analysis
Manual Deep Analysis
Cross-site Failure Patterns
Predictive Maintenance
Advanced Reports
```

ولا يتم تنفيذ أي Predictive Maintenance بشكل تلقائي؛ النتائج تظل Recommendations للمهندس.

---

# 34. أول Sprint — التنفيذ الفعلي

ابدأ بهذا الترتيب:

```text
1. إنشاء Repository
2. إنشاء contract/
3. إنشاء visit_package.schema.json (ويشمل شيت locations)
4. إنشاء manifest.schema.json
5. إنشاء checklist_items.json
6. إنشاء locations.schema.json
7. إنشاء Sample Visit Package (بما فيه شجرة مواقع)
8. إنشاء Package Validator
9. إنشاء Signature Verification
10. إنشاء FastAPI
11. إنشاء SQLite + Alembic (جداول مشروع / منطقة / Zone / موقع)
12. إنشاء Seed Workbook Importer
13. إنشاء Locations Tree في الويب
14. إنشاء Import Inbox + دمج عناصر التقسيم (Hierarchy Merge)
15. إنشاء Equipment Matching
16. إنشاء Android Compose Project
17. إنشاء شاشة إدارة المواقع (إضافة / تعديل)
18. إنشاء شاشة المعدات
19. إضافة Model + Quantity
20. إضافة Running Hours
21. إضافة Camera + GPS
22. تصدير عناصر التقسيم داخل الحزمة
23. إنشاء ZIP Package
24. اختبار Android → Web (زيارة + عناصر تقسيم جديدة)
```

**بعد نجاح هذه المرحلة فقط:**

```text
25. Manual Upload
26. PDF Parser
27. Manual Chunking
28. Manual Search
29. Maintenance Rule Extraction
30. Ollama Integration
31. Qwen3.5:9b
32. Manual RAG
33. Maintenance Status Engine
34. AI Alerts
35. OpenRouter Provider
```

---

# 35. Acceptance Criteria الأساسية

المشروع لا يعتبر جاهزًا للـMVP إلا عندما يستطيع النظام:

### Android

```text
✓ إدارة شجرة المواقع أوفلاين (إضافة / تعديل / تعطيل)
✓ إنشاء زيارة Offline
✓ تحديد الموقع من الشجرة (مشروع / منطقة / Zone / موقع)
✓ تحديد عدد المضخات
✓ إدخال Model
✓ إنشاء N معدات
✓ إدخال Running Hours لكل مضخة
✓ إدخال Pressure
✓ تسجيل الحالة
✓ Checklist
✓ Camera
✓ GPS
✓ Timestamp
✓ Digital Signature
✓ Export ZIP (يشمل عناصر التقسيم)
```

### Web

```text
✓ Verify Package
✓ Detect Duplicate
✓ Merge Locations (Idempotent)
✓ Flag Hierarchy Conflict
✓ Match Equipment
✓ Detect New Equipment
✓ Detect Model Conflict
✓ Store Photos
✓ Store Readings
✓ Display Asset History
```

### Manuals

```text
✓ Upload PDF
✓ Hash PDF
✓ Extract Text
✓ OCR Scanned PDF
✓ Search Manual
✓ Link Manual to Model
✓ Extract Maintenance Rules
✓ Store Page Evidence
✓ Engineer Approval
```

### Maintenance

```text
✓ Calculate PM Due from Hours
✓ Calculate PM Due from Days
✓ Compare Current vs Last Maintenance
✓ Detect Overdue
✓ Detect Upcoming Maintenance
✓ Generate Deterministic Alerts
```

### AI

```text
✓ Ollama connection
✓ Qwen3.5:9b
✓ OpenRouter connection
✓ Provider switching
✓ Manual RAG
✓ Equipment analysis
✓ Maintenance suggestions
✓ Pump status explanation
✓ Evidence for every AI alert
✓ No AI direct database mutation
✓ AI failure does not stop the application
```

---

# 36. خارج النطاق حاليًا

```text
Real-time cloud synchronization
Real-time hierarchy sync (التقسيم ينتقل عبر الحزم فقط)
Technician login
Cloud database
Online technician operation
Financial ERP
Electronic purchasing
Push notifications
Automatic AI execution of maintenance
Automatic work-order closing
Automatic stock adjustment
```

---

# 37. المبدأ النهائي للمشروع

```text
          FIELD
            │
            ▼
       Android App
            │
            ▼
      Visit Package
            │
            ▼
       Web Import
            │
            ▼
       Asset History
            │
       ┌────┴─────┐
       ▼          ▼
   Manual      Readings
       │          │
       └────┬─────┘
            ▼
   Maintenance Engine
            │
       ┌────┴─────┐
       ▼          ▼
    Rules        AI
       │       ┌──┴─────────┐
       │       │            │
       │    Ollama      OpenRouter
       │    Qwen3.5:9b
       │       │
       └───────┴──────┐
                      ▼
                 AI Analysis
                      │
                      ▼
               Evidence-based
                  Alerts
                      │
                      ▼
                ENGINEER REVIEW
                      │
             ┌────────┴────────┐
             ▼                 ▼
          APPROVE             REJECT
             │
             ▼
       Maintenance Action
```

**القاعدة الأساسية:**

> **Manual يحدد ما يجب عمله، ساعات التشغيل تحدد متى، بيانات الزيارة والقراءات تحدد ما يحدث فعليًا، والـAI يربط هذه المعلومات ويشرحها للمهندس.**

ولا يتم اعتبار الـAI مصدر الحقيقة؛ **المصدر هو البيانات + الـManual + قواعد الصيانة، والـAI طبقة تحليل وتفسير فوقها.**
