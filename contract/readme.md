# Contract — عقد الحزمة (Phase 0)

هذه الطبقة تحدد **Visit Package v1** الذي ينتقل من تطبيق Android (الفني) إلى تطبيق Web (المهندس).
المرجع الأساسي: `ARCHITECTURE.md` — القسم §4 بالكامل.

## بنية الحزمة (ZIP)

| العنصر | الوصف |
|---|---|
| `visit.xlsx` | الشيتات: `_meta`, `visit`, `equipment`, `checklist`, `locations`, `photos` (+ شيت `Report` للعرض فقط إن وُجد). |
| `photos/` | صور JPEG بأسماء `IMG_*.jpg`. |
| `manifest.json` | المانيفست الكامل (انظر `manifest.schema.json`). |
| `manifest.sig` | توقيع ECDSA P-256 على بايتات `manifest.json` (DER ثم base64). **حزمة بدون هذا الملف = REJECT.** |

## المخططات

| الملف | الوصف |
|---|---|
| `visit_package.schema.json` | وصف الحزمة الكاملة وأعمدة كل شيت. |
| `manifest.schema.json` | حقول المانيفست وأنواعها. |
| `locations.schema.json` | صفوف شيت locations وقواعد الشجرة. |
| `checklist_items.json` | بنود العنبر — **قائمة مؤقتة (PROVISIONAL)** حتى اعتماد القائمة النهائية. |

## أعمدة شيت locations

`row_id, code, type, parent_code, name, status, updated_at`

- `type`: PROJECT / REGION / ZONE / LOCATION.
- `code`: `PRJ-###` / `RGN-###` / `ZN-###` / `LOC-###` — والكود هو الهوية الثابتة للعنصر.
- لا حذف — التعطيل `INACTIVE` فقط.

## قواعد الدمج في الويب (Hierarchy Merge Rules — §4.5)

1. كود جديد → إنشاء عنصر جديد (source = ANDROID).
2. كود موجود بنفس البيانات → No-op.
3. كود موجود ببيانات مختلفة → Conflict → يظهر للمهندس للمراجعة.
4. اسم مكرر تحت نفس الأب بكود مختلف → اشتباه تكرار → مراجعة.
5. لا يتم حذف أي عنصر بسبب الاستيراد.
6. الاستيراد Idempotent — نفس الحزمة مرتين لا تُنشئ نسخاً مكررة.

## أدوات التحقق

```bash
python tools/make_sample_package.py
python tools/validate_package.py contract/samples/valid_package.zip --seen-db tests/_tmp/seen.json
python tests/run_tests.py
```

حالة الـValidator الواحدة + كود الخروج:

| الحالة | Exit | المعنى |
|---|---|---|
| `PASS` | 0 | حزمة سليمة وموقعة. |
| `FAIL` | 1 | خرق بنيوي أو عدم تطابق hash/توقيع. |
| `REJECT` | 2 | حزمة غير موقعة (لا `manifest.sig`). |
| `DUPLICATE` | 3 | نفس `package_id` سبق استيراده (عبر `--seen-db`). |
| `FLAG` | 4 | مشاكل غير قاتلة تحتاج مراجعة (تعارضات الشجرة، بيانات صور ناقصة). |

## ملاحظات

- أدوات Phase 0 تعمل ببايثون القياسي فقط (بدون تبعيات خارجية).
  فحص التوقيع يستخدم `cryptography` إن كانت متوفرة، وإلا تنفيذاً داخلياً مكافئاً (pure Python).
- `contract/samples/dev_key.json` مفتاح تطوير فقط — لا يُستخدم في الإنتاج.
- العينات في `contract/samples/` تُبنى بأمر واحد وتُستخدم في الفحوص الآلية.
