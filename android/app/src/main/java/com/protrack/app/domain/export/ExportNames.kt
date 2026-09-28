package com.protrack.app.domain.export

/** أسماء ملفات التصدير — Visit_<LOCATION>_<yyyyMMdd-HHmmss>[_<اسم الفني>].zip */
object ExportNames {

    fun sanitizeTechnician(name: String): String =
        name.trim()
            .replace(Regex("[^\\p{L}\\p{N}_-]+"), "_")
            .trim('_')
            .take(20)

    fun visitFileName(locationCode: String, stamp: String, technician: String): String {
        val cleaned = sanitizeTechnician(technician)
        val suffix = if (cleaned.isNotBlank()) "_$cleaned" else ""
        return "Visit_${locationCode}_$stamp$suffix.zip"
    }
}
