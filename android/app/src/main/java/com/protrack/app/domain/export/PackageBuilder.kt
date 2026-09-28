package com.protrack.app.domain.export

import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import java.util.Base64
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

data class ExportMeta(
    val packageId: String,
    val createdAt: String,
    val deviceId: String,
    val publicKeyB64: String,
    val fingerprint: String,
)

data class ExportVisit(
    val visitId: String,
    val locationCode: String,
    val visitType: String,
    val startedAt: String,
    val endedAt: String?,
    val notes: String,
    val status: String,
)

data class ExportEquipment(
    val kind: String,
    val tag: String,
    val model: String,
    val runningHours: Double?,
    val pressureBar: Double?,
    val status: String,
    val note: String,
)

data class ExportChecklist(
    val itemCode: String,
    val status: String,
    val note: String,
)

data class ExportLocation(
    val code: String,
    val type: String,
    val parentCode: String?,
    val name: String,
    val status: String,
    val updatedAt: String,
)

data class ExportPhoto(
    val fileName: String,
    val bytes: ByteArray,
    val takenAt: String,
    val lat: Double,
    val lon: Double,
    val accuracyM: Double,
)

/**
 * بناء حزمة الزيارة الكاملة: visit.xlsx + photos/ + manifest.json + manifest.sig.
 */
class PackageBuilder(private val signer: PackageSigner) {

    fun build(
        meta: ExportMeta,
        visit: ExportVisit,
        equipment: List<ExportEquipment>,
        checklist: List<ExportChecklist>,
        locations: List<ExportLocation>,
        photos: List<ExportPhoto>,
    ): ByteArray {
        val sheets = linkedMapOf<String, List<List<Any?>>>()

        val metaSheet = mutableListOf<List<Any?>>()
        metaSheet.add(
            listOf<Any?>(
                "package_id", "schema_version", "created_at",
                "device_id", "device_public_key", "device_fingerprint",
            ),
        )
        metaSheet.add(
            listOf<Any?>(meta.packageId, 1, meta.createdAt, meta.deviceId, meta.publicKeyB64, meta.fingerprint),
        )
        sheets["_meta"] = metaSheet

        val visitSheet = mutableListOf<List<Any?>>()
        visitSheet.add(
            listOf<Any?>("visit_id", "location_code", "visit_type", "started_at", "ended_at", "notes", "status"),
        )
        visitSheet.add(
            listOf<Any?>(visit.visitId, visit.locationCode, visit.visitType, visit.startedAt, visit.endedAt ?: "", visit.notes, visit.status),
        )
        sheets["visit"] = visitSheet

        val equipmentSheet = mutableListOf<List<Any?>>()
        equipmentSheet.add(
            listOf<Any?>("row_id", "visit_id", "kind", "tag", "model", "running_hours", "pressure_bar", "status", "note"),
        )
        equipment.forEachIndexed { i, e ->
            equipmentSheet.add(
                listOf<Any?>(i + 1, visit.visitId, e.kind, e.tag, e.model, e.runningHours, e.pressureBar, e.status, e.note),
            )
        }
        sheets["equipment"] = equipmentSheet

        val checklistSheet = mutableListOf<List<Any?>>()
        checklistSheet.add(listOf<Any?>("visit_id", "item_code", "status", "note"))
        checklist.forEach { c ->
            checklistSheet.add(listOf<Any?>(visit.visitId, c.itemCode, c.status, c.note))
        }
        sheets["checklist"] = checklistSheet

        val locationsSheet = mutableListOf<List<Any?>>()
        locationsSheet.add(listOf<Any?>("row_id", "code", "type", "parent_code", "name", "status", "updated_at"))
        locations.forEachIndexed { i, l ->
            locationsSheet.add(listOf<Any?>(i + 1, l.code, l.type, l.parentCode ?: "", l.name, l.status, l.updatedAt))
        }
        sheets["locations"] = locationsSheet

        val photosSheet = mutableListOf<List<Any?>>()
        photosSheet.add(
            listOf<Any?>("row_id", "file", "target_type", "target_ref", "taken_at", "lat", "lon", "accuracy_m", "sha256", "capture_sig"),
        )
        photos.forEachIndexed { i, p ->
            val sha = sha256Hex(p.bytes)
            val sig = Base64.getEncoder().encodeToString(signer.sign(p.bytes))
            photosSheet.add(
                listOf<Any?>(i + 1, p.fileName, "EQUIPMENT", "", p.takenAt, p.lat, p.lon, p.accuracyM, sha, sig),
            )
        }
        sheets["photos"] = photosSheet

        val xlsx = XlsxWriter.write(sheets)

        val files = mutableListOf<ManifestFile>()
        files += ManifestFile(path = "visit.xlsx", sha256 = sha256Hex(xlsx))
        photos.forEach { p ->
            files += ManifestFile(
                path = "photos/${p.fileName}",
                sha256 = sha256Hex(p.bytes),
                takenAt = p.takenAt,
                lat = p.lat,
                lon = p.lon,
                accuracyM = p.accuracyM,
                captureSig = Base64.getEncoder().encodeToString(signer.sign(p.bytes)),
            )
        }

        val manifestBytes = ManifestBuilder.build(meta, files)
        val manifestSigB64 = Base64.getEncoder().encodeToString(signer.sign(manifestBytes))

        val baos = ByteArrayOutputStream()
        ZipOutputStream(baos).use { zos ->
            fun put(name: String, bytes: ByteArray) {
                zos.putNextEntry(ZipEntry(name))
                zos.write(bytes)
                zos.closeEntry()
            }
            put("visit.xlsx", xlsx)
            photos.forEach { put("photos/${it.fileName}", it.bytes) }
            put("manifest.json", manifestBytes)
            put("manifest.sig", manifestSigB64.toByteArray(Charsets.US_ASCII))
        }
        return baos.toByteArray()
    }

    companion object {
        fun sha256Hex(data: ByteArray): String {
            val md = MessageDigest.getInstance("SHA-256")
            return md.digest(data).joinToString("") { "%02x".format(it) }
        }
    }
}
