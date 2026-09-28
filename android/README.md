# ProTrack — Android (Phase 2)

تطبيق الفني (أوفلاين): Kotlin 1.9.20 + Jetpack Compose + Material 3 + Room + CameraX + FusedLocation.

## المنفَّذ

- **إدارة شجرة المواقع أوفلاين**: إضافة / إعادة تسمية / تعطيل-تفعيل (مشروع/منطقة/Zone/موقع)، أكواد تلقائية `PRJ/RGN/ZN/LOC`.
- **تدفق الزيارة**: اختيار الموقع ← المعدات (نوع/موديل/عدد + قراءات لكل معدة) ← بنود العنبر الـ12 ← مراجعة.
- **الكاميرا وGPS**: التقاط صور من كاميرا التطبيق فقط (بدون معرض)، مع إحداثيات GPS
  وبصمة SHA-256 وتوقيع الالتقاط لكل صورة.
- **تصدير حزمة الزيارة**: `visit.xlsx` + `photos/` + `manifest.json` + `manifest.sig`
  (توقيع ECDSA P-256 من Android Keystore) داخل ZIP، تُحفظ في `packages/` ويمكن مشاركتها.
- عربي (افتراضي) + إنجليزي مع RTL.

## البناء والفحوص

```bash
cd android
.\gradlew.bat :app:assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat :app:testDebugUnitTest    # فحوص الوحدة (أكواد/شجرة/بناء الحزمة)
```

> يحتاج JDK 17+ و Android SDK (`sdk.dir` في `local.properties` — غير مُتتبع في Git).
> ملاحظة: تحذير النظام عن 16KB page-size من مكتبة كاميرا 1.3.1 يظهر للتطبيقات التجريبية فقط (غير مؤثر).

## القادم

- أول تشغيل (اسم الفني + اللغة).
