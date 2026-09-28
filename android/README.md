# ProTrack — Android (Phase 2) ✅

تطبيق الفني (أوفلاين): Kotlin 1.9.20 + Jetpack Compose + Material 3 + Room + CameraX + FusedLocation.

## المنفَّذ (Phase 2 مكتملة)

- **أول تشغيل**: اسم الفني + اختيار اللغة (عربي/إنجليزي — مع RTL كامل وتحويل حي).
- **إدارة شجرة المواقع أوفلاين**: إضافة / إعادة تسمية / تعطيل-تفعيل (مشروع/منطقة/Zone/موقع)، أكواد تلقائية `PRJ/RGN/ZN/LOC`.
- **تدفق الزيارة**: اختيار الموقع ← المعدات (نوع/موديل/عدد + قراءات لكل معدة) ← بنود العنبر الـ12 ← مراجعة.
- **الكاميرا وGPS**: التقاط صور من كاميرا التطبيق فقط (بدون معرض)، مع إحداثيات GPS
  وبصمة SHA-256 وتوقيع الالتقاط لكل صورة.
- **تصدير حزمة الزيارة**: `visit.xlsx` + `photos/` + `manifest.json` + `manifest.sig`
  (توقيع ECDSA P-256 من Android Keystore) داخل ZIP، باسم يتضمن اسم الفني، وتُشارك من التطبيق.
- **متـحقَّقة على جهاز حقيقي** (Samsung SM-A176B): من إنشاء الشجرة على الهاتف حتى استيراد
  الحزمة في باك-إند الويب (مع مطابقة المعدات وتحديث القراءات بلا تكرار).

## البناء والفحوص

```bash
cd android
.\gradlew.bat :app:assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat :app:testDebugUnitTest    # فحوص الوحدة (أكواد/شجرة/حزمة/أسماء ملفات)
```

> يحتاج JDK 17+ و Android SDK (`sdk.dir` في `local.properties` — غير مُتتبع في Git).

### 16KB page size

مكتبات CameraX (منذ 1.4.x) متوافقة مع 16KB — تم التحقق من محاذاة ELF (p_align = 0x4000)
و zipalign -P 16، واختفى تحذير التوافق الذي كانت تعرضه سامسونج للتطبيقات التجريبية القديمة.

## القادم

- Phase 3: Manuals / Maintenance Engine / AI (راجع §33/§34 في `ARCHITECTURE.md`).
