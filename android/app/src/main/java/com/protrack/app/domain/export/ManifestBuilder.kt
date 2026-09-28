package com.protrack.app.domain.export

data class ManifestFile(
    val path: String,
    val sha256: String,
    val takenAt: String? = null,
    val lat: Double? = null,
    val lon: Double? = null,
    val accuracyM: Double? = null,
    val captureSig: String? = null,
)

/**
 * بناء manifest.json يدويًا (بدون تبعيات) — مطابق لـ manifest.schema.json.
 */
object ManifestBuilder {

    fun build(meta: ExportMeta, files: List<ManifestFile>): ByteArray {
        val sb = StringBuilder()
        sb.append("{\n")
        sb.append("  \"package_id\": ").append(jsonString(meta.packageId)).append(",\n")
        sb.append("  \"schema_version\": 1,\n")
        sb.append("  \"created_at\": ").append(jsonString(meta.createdAt)).append(",\n")
        sb.append("  \"device\": {\n")
        sb.append("    \"device_id\": ").append(jsonString(meta.deviceId)).append(",\n")
        sb.append("    \"public_key\": ").append(jsonString(meta.publicKeyB64)).append(",\n")
        sb.append("    \"fingerprint\": ").append(jsonString(meta.fingerprint)).append("\n")
        sb.append("  },\n")
        sb.append("  \"files\": [\n")
        files.forEachIndexed { i, f ->
            sb.append("    {")
            sb.append("\"path\": ").append(jsonString(f.path)).append(", ")
            sb.append("\"sha256\": ").append(jsonString(f.sha256))
            if (f.takenAt != null) {
                sb.append(", \"taken_at\": ").append(jsonString(f.takenAt))
                sb.append(", \"lat\": ").append(f.lat ?: 0.0)
                sb.append(", \"lon\": ").append(f.lon ?: 0.0)
                sb.append(", \"accuracy_m\": ").append(f.accuracyM ?: 0.0)
                sb.append(", \"capture_sig\": ").append(jsonString(f.captureSig ?: ""))
            }
            sb.append("}")
            if (i < files.size - 1) sb.append(",")
            sb.append("\n")
        }
        sb.append("  ]\n")
        sb.append("}\n")
        return sb.toString().toByteArray(Charsets.UTF_8)
    }

    fun jsonString(s: String): String {
        val sb = StringBuilder("\"")
        for (ch in s) {
            when (ch) {
                '\\' -> sb.append("\\\\")
                '"' -> sb.append("\\\"")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                else -> if (ch < ' ') sb.append("\\u").append(ch.code.toString(16).padStart(4, '0')) else sb.append(ch)
            }
        }
        sb.append("\"")
        return sb.toString()
    }
}
