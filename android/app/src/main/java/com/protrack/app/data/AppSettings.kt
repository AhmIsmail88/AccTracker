package com.protrack.app.data

import android.content.Context

/**
 * إعدادات التطبيق المحلية: اسم الفني + اللغة (تُحفظ في نفس ملف تفضيلات الجهاز).
 */
class AppSettings(context: Context) {

    private val prefs = context.getSharedPreferences("protrack_device", Context.MODE_PRIVATE)

    var technicianName: String
        get() = prefs.getString("technician_name", "") ?: ""
        set(value) {
            prefs.edit().putString("technician_name", value).apply()
        }

    /** "ar" أو "en" — فاضية = لغة النظام. */
    var languageCode: String
        get() = prefs.getString("language", "") ?: ""
        set(value) {
            prefs.edit().putString("language", value).apply()
        }

    fun isOnboarded(): Boolean = technicianName.isNotBlank()
}
