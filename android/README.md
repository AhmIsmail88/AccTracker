# ProTrack — Android (Phase 2)

تطبيق الفني (أوفلاين): Kotlin 1.9.20 + Jetpack Compose + Material 3 + Room.

## المنفَّذ

- **إدارة شجرة المواقع أوفلاين**: إضافة / إعادة تسمية / تعطيل-تفعيل (مشروع/منطقة/Zone/موقع)، أكواد تلقائية `PRJ/RGN/ZN/LOC`.
- **تدفق الزيارة**: اختيار الموقع ← المعدات (نوع/موديل/عدد + قراءات لكل معدة) ← بنود العنبر الـ12 ← مراجعة.
- **تصدير حزمة الزيارة**: `visit.xlsx` + `manifest.json` + `manifest.sig` (توقيع ECDSA P-256 من Android Keystore) داخل ZIP، يُحفظ في `packages/` ويمكن مشاركته.
- عربي (افتراضي) + إنجليزي مع RTL.

## البناء والفحوص

```bash
cd android
.\gradlew.bat :app:assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat :app:testDebugUnitTest    # فحوص الوحدة (أكواد/شجرة/بناء الحزمة)
```

> يحتاج JDK 17+ و Android SDK (`sdk.dir` في `local.properties` — غير مُتتبع في Git).
> فحص `PackageBuilderTest` ينتج artifact في `app/build/test-artifacts/` يعدّي validator المشروع بحالة PASS
> وتم استيراده فعليًا في باك-إند الويب.

## القادم

- أول تشغيل (اسم الفني + اللغة).
- الكاميرا وGPS وربطهما بالصور داخل الحزمة.
