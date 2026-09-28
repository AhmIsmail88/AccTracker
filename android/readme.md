# ProTrack — Android (Phase 2 — الجزء الأول)

تطبيق الفني (أوفلاين). المبني حاليًا:

- مشروع Gradle (Kotlin 1.9.20 + Jetpack Compose + Material 3 + Room).
- **إدارة شجرة المواقع أوفلاين**: إضافة / إعادة تسمية / تعطيل-تفعيل، وأكواد تلقائية `PRJ/RGN/ZN/LOC`.
- عربي (افتراضي) + إنجليزي مع دعم RTL.

## البناء والفحوص

```bash
cd android
.\gradlew.bat :app:assembleDebug        # ينتج app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat :app:testDebugUnitTest    # فحوص الوحدة (منطق الأكواد + بناء الشجرة)
```

> يحتاج JDK 17+ و Android SDK (يُحدد مساره في `local.properties`، وهو غير مُتتبع في Git).

## القادم (الجزء الثاني)

- شاشة أول تشغيل (اسم الفني + اللغة).
- شاشات الزيارة: المعدات والقراءات والبنود.
- الكاميرا وGPS.
- تصدير حزمة الزيارة (نفس عقد `contract/`).
