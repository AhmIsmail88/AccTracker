package com.protrack.app.domain.export

import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import java.util.Base64
import java.util.Locale
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
    val itemName: String = "",
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
    val targetType: String = "EQUIPMENT",
    val targetRef: String = "",
)

/** نصوص ورقة "Report" — تأتي من موارد التطبيق حسب اللغة. */
data class ReportLabels(
    val title: String = "تقرير زيارة صيانة",
    val location: String = "الموقع",
    val dateTime: String = "التاريخ والوقت",
    val technician: String = "الفني",
    val summary: String = "ملخص الحالة",
    val summaryOk: String = "سليمة: %d",
    val summaryMinor: String = "ملاحظات: %d",
    val summaryFault: String = "أعطال: %d",
    val summaryExtra: String = "معدات: %d • صور: %d",
    val equipmentSection: String = "المعدات والقراءات",
    val checklistSection: String = "قائمة الفحص",
    val photosSection: String = "الصور المرفقة",
    val notesSection: String = "ملاحظات الزيارة",
    val colEquipment: String = "المعدة",
    val colModel: String = "الموديل",
    val colHours: String = "ساعات التشغيل",
    val colPressure: String = "الضغط (bar)",
    val colStatus: String = "الحالة",
    val colNotes: String = "ملاحظات",
    val colItem: String = "البند",
    val colItemNotes: String = "الملاحظات",
    val ok: String = "سليم",
    val minor: String = "ملاحظة",
    val fault: String = "عطل",
    val eqRunning: String = "تعمل",
    val eqStopped: String = "متوقفة",
    val eqFault: String = "عطل",
    val kindNames: Map<String, String> = emptyMap(),
    val photoLabel: String = "صورة",
    val footer: String = "تم إنشاء هذا التقرير آليًا بواسطة ProTrack",
    val emptyEquipment: String = "لا توجد معدات مسجلة",
    val emptyPhotos: String = "لا توجد صور مرفقة",
    val signatureBy: String = "إعداد وتوقيع الفني: %s",
    val signatureLine: String = "التوقيع: ________________",
)

/**
 * بناء حزمة الزيارة الكاملة: visit.xlsx (ورقة Report للإدارة + شيتات آلية مخفية)
 * + photos/ + manifest.json + manifest.sig.
 */
class PackageBuilder(private val signer: PackageSigner) {

    fun build(
        meta: ExportMeta,
        visit: ExportVisit,
        equipment: List<ExportEquipment>,
        checklist: List<ExportChecklist>,
        locations: List<ExportLocation>,
        photos: List<ExportPhoto>,
        technician: String = "",
        appVersion: String = "",
        labels: ReportLabels = ReportLabels(),
    ): ByteArray {
        val sheets = mutableListOf<XlsxSheet>()

        // 1) ورقة التقرير — أول ورقة مرئية، معدّة للعرض والمشاركة مع الإدارة
        sheets += buildReportSheet(
            meta, visit, equipment, checklist, locations, photos, technician, appVersion, labels,
        )

        // 2) الشيتات الآلية (يقرأها الويب + أدوات التحقق) — مخفية داخل الملف
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
        sheets += XlsxWriter.plain("_meta", metaSheet, hidden = true)

        val visitSheet = mutableListOf<List<Any?>>()
        visitSheet.add(
            listOf<Any?>("visit_id", "location_code", "visit_type", "started_at", "ended_at", "notes", "status"),
        )
        visitSheet.add(
            listOf<Any?>(visit.visitId, visit.locationCode, visit.visitType, visit.startedAt, visit.endedAt ?: "", visit.notes, visit.status),
        )
        sheets += XlsxWriter.plain("visit", visitSheet, hidden = true)

        val equipmentSheet = mutableListOf<List<Any?>>()
        equipmentSheet.add(
            listOf<Any?>("row_id", "visit_id", "kind", "tag", "model", "running_hours", "pressure_bar", "status", "note"),
        )
        equipment.forEachIndexed { i, e ->
            equipmentSheet.add(
                listOf<Any?>(i + 1, visit.visitId, e.kind, e.tag, e.model, e.runningHours, e.pressureBar, e.status, e.note),
            )
        }
        sheets += XlsxWriter.plain("equipment", equipmentSheet, hidden = true)

        val checklistSheet = mutableListOf<List<Any?>>()
        checklistSheet.add(listOf<Any?>("visit_id", "item_code", "status", "note"))
        checklist.forEach { c ->
            checklistSheet.add(listOf<Any?>(visit.visitId, c.itemCode, c.status, c.note))
        }
        sheets += XlsxWriter.plain("checklist", checklistSheet, hidden = true)

        val locationsSheet = mutableListOf<List<Any?>>()
        locationsSheet.add(listOf<Any?>("row_id", "code", "type", "parent_code", "name", "status", "updated_at"))
        locations.forEachIndexed { i, l ->
            locationsSheet.add(listOf<Any?>(i + 1, l.code, l.type, l.parentCode ?: "", l.name, l.status, l.updatedAt))
        }
        sheets += XlsxWriter.plain("locations", locationsSheet, hidden = true)

        val photosSheet = mutableListOf<List<Any?>>()
        photosSheet.add(
            listOf<Any?>("row_id", "file", "target_type", "target_ref", "taken_at", "lat", "lon", "accuracy_m", "sha256", "capture_sig"),
        )
        photos.forEachIndexed { i, p ->
            val sha = sha256Hex(p.bytes)
            val sig = Base64.getEncoder().encodeToString(signer.sign(p.bytes))
            photosSheet.add(
                listOf<Any?>(i + 1, p.fileName, p.targetType, p.targetRef, p.takenAt, p.lat, p.lon, p.accuracyM, sha, sig),
            )
        }
        sheets += XlsxWriter.plain("photos", photosSheet, hidden = true)

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

    // ===================== ورقة "Report" =====================

    private fun buildReportSheet(
        meta: ExportMeta,
        visit: ExportVisit,
        equipment: List<ExportEquipment>,
        checklist: List<ExportChecklist>,
        locations: List<ExportLocation>,
        photos: List<ExportPhoto>,
        technician: String,
        appVersion: String,
        labels: ReportLabels,
    ): XlsxSheet {
        val rows = mutableListOf<XlsxRow>()
        val merges = mutableListOf<String>()
        var rowNumber = 0

        fun nextRow(cells: List<XlsxCell> = emptyList(), height: Double? = null): Int {
            rows.add(XlsxRow(cells, height))
            rowNumber += 1
            return rowNumber
        }

        fun mergeRow(row: Int, from: String, to: String) {
            merges += "$from$row:$to$row"
        }

        fun cell(value: Any?, style: Int = XlsxStyle.VALUE) = XlsxCell(value, style)
        fun blank(style: Int) = XlsxCell(null, style)
        fun six(vararg cells: XlsxCell): List<XlsxCell> {
            val list = cells.toMutableList()
            while (list.size < 6) list.add(blank(XlsxStyle.DEFAULT))
            return list
        }

        val okCount = checklist.count { it.status == "OK" }
        val minorCount = checklist.count { it.status == "MINOR" }
        val faultCount = checklist.size - okCount - minorCount

        // العنوان
        val r1 = nextRow(
            six(
                cell(labels.title, XlsxStyle.TITLE), blank(XlsxStyle.TITLE), blank(XlsxStyle.TITLE),
                blank(XlsxStyle.TITLE), blank(XlsxStyle.TITLE), blank(XlsxStyle.TITLE),
            ),
            height = 34.0,
        )
        mergeRow(r1, "A", "F")

        // معلومات أساسية
        val r2 = nextRow(six(cell(labels.location, XlsxStyle.LABEL), cell(locationPath(visit, locations), XlsxStyle.BOLD_VALUE)))
        mergeRow(r2, "B", "F")
        val r3 = nextRow(six(cell(labels.dateTime, XlsxStyle.LABEL), cell(visitRange(visit), XlsxStyle.BOLD_VALUE)))
        mergeRow(r3, "B", "F")
        val r4 = nextRow(six(cell(labels.technician, XlsxStyle.LABEL), cell(technician.ifBlank { "—" }, XlsxStyle.BOLD_VALUE)))
        mergeRow(r4, "B", "F")

        // ملخص الحالة
        val r5 = nextRow(
            six(
                cell(labels.summary, XlsxStyle.LABEL),
                cell(String.format(Locale.US, labels.summaryOk, okCount), XlsxStyle.OK),
                cell(String.format(Locale.US, labels.summaryMinor, minorCount), XlsxStyle.MINOR),
                cell(String.format(Locale.US, labels.summaryFault, faultCount), XlsxStyle.FAULT),
                cell(String.format(Locale.US, labels.summaryExtra, equipment.size, photos.size), XlsxStyle.VALUE),
            ),
        )
        mergeRow(r5, "E", "F")

        nextRow(height = 6.0)

        // المعدات
        val r7 = nextRow(
            six(
                cell(labels.equipmentSection, XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
                blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
            ),
            height = 22.0,
        )
        mergeRow(r7, "A", "F")
        nextRow(
            six(
                cell(labels.colEquipment, XlsxStyle.HEADER), cell(labels.colModel, XlsxStyle.HEADER),
                cell(labels.colHours, XlsxStyle.HEADER), cell(labels.colPressure, XlsxStyle.HEADER),
                cell(labels.colStatus, XlsxStyle.HEADER), cell(labels.colNotes, XlsxStyle.HEADER),
            ),
            height = 24.0,
        )
        if (equipment.isEmpty()) {
            val r = nextRow(six(cell(labels.emptyEquipment, XlsxStyle.VALUE)))
            mergeRow(r, "A", "F")
        } else {
            equipment.forEach { e ->
                nextRow(
                    six(
                        cell(equipmentName(e, labels), XlsxStyle.CELL),
                        cell(e.model, XlsxStyle.CELL),
                        cell(e.runningHours ?: "-", XlsxStyle.CELL_NUM),
                        cell(e.pressureBar ?: "-", XlsxStyle.CELL_NUM),
                        cell(equipmentStatusLabel(e.status, labels), equipmentStatusStyle(e.status)),
                        cell(e.note, XlsxStyle.CELL),
                    ),
                )
            }
        }

        nextRow(height = 6.0)

        // قائمة الفحص
        val rc = nextRow(
            six(
                cell(labels.checklistSection, XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
                blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
            ),
            height = 22.0,
        )
        mergeRow(rc, "A", "F")
        val rh = nextRow(
            six(
                cell(labels.colItem, XlsxStyle.HEADER), blank(XlsxStyle.HEADER),
                cell(labels.colStatus, XlsxStyle.HEADER), cell(labels.colItemNotes, XlsxStyle.HEADER),
                blank(XlsxStyle.HEADER), blank(XlsxStyle.HEADER),
            ),
            height = 24.0,
        )
        mergeRow(rh, "A", "B")
        mergeRow(rh, "D", "F")
        checklist.forEach { item ->
            val r = nextRow(
                six(
                    cell(checklistName(item), XlsxStyle.CELL), blank(XlsxStyle.CELL),
                    cell(checklistStatusLabel(item.status, labels), checklistStatusStyle(item.status)),
                    cell(item.note, XlsxStyle.CELL), blank(XlsxStyle.CELL), blank(XlsxStyle.CELL),
                ),
            )
            mergeRow(r, "A", "B")
            mergeRow(r, "D", "F")
        }

        nextRow(height = 6.0)

        // الصور
        val rp = nextRow(
            six(
                cell(labels.photosSection, XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
                blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
            ),
            height = 22.0,
        )
        mergeRow(rp, "A", "F")
        if (photos.isEmpty()) {
            val r = nextRow(six(cell(labels.emptyPhotos, XlsxStyle.VALUE)))
            mergeRow(r, "A", "F")
        } else {
            photos.forEachIndexed { i, p ->
                val gps = if (p.lat != 0.0 || p.lon != 0.0) {
                    " — GPS " + String.format(Locale.US, "%.4f, %.4f", p.lat, p.lon)
                } else {
                    ""
                }
                val r = nextRow(
                    six(cell("${labels.photoLabel} ${i + 1} — ${p.fileName} — ${shortDateTime(p.takenAt)}$gps", XlsxStyle.VALUE)),
                )
                mergeRow(r, "A", "F")
            }
        }

        // ملاحظات الزيارة
        if (visit.notes.isNotBlank()) {
            nextRow(height = 6.0)
            val rn = nextRow(
                six(
                    cell(labels.notesSection, XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
                    blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION), blank(XlsxStyle.SECTION),
                ),
                height = 22.0,
            )
            mergeRow(rn, "A", "F")
            val rb = nextRow(
                six(
                    cell(visit.notes, XlsxStyle.CELL), blank(XlsxStyle.CELL), blank(XlsxStyle.CELL),
                    blank(XlsxStyle.CELL), blank(XlsxStyle.CELL), blank(XlsxStyle.CELL),
                ),
                height = 30.0,
            )
            mergeRow(rb, "A", "F")
        }

        // توقيع الفني — أسفل التقرير للإدارة
        nextRow(height = 6.0)
        val techSign = technician.ifBlank { "—" }
        val rs = nextRow(
            six(cell(String.format(Locale.US, labels.signatureBy, techSign), XlsxStyle.BOLD_VALUE)),
        )
        mergeRow(rs, "A", "F")
        val rsl = nextRow(six(cell(labels.signatureLine, XlsxStyle.VALUE)))
        mergeRow(rsl, "A", "F")

        nextRow(height = 6.0)
        val rf = nextRow(
            six(cell(labels.footer + " — " + appVersion + " — " + shortDateTime(meta.createdAt), XlsxStyle.FOOTER)),
        )
        mergeRow(rf, "A", "F")

        return XlsxSheet(
            name = "Report",
            rows = rows,
            colWidths = listOf(24.0, 14.0, 14.0, 13.0, 12.0, 30.0),
            merges = merges,
            rightToLeft = true,
            hidden = false,
        )
    }

    private fun locationPath(visit: ExportVisit, locations: List<ExportLocation>): String {
        val byCode = locations.associateBy { it.code }
        val chain = mutableListOf<String>()
        var current = byCode[visit.locationCode]
        var guard = 0
        while (current != null && guard < 10) {
            val node = current
            chain.add(0, node.name.ifBlank { node.code })
            current = node.parentCode?.let { byCode[it] }
            guard += 1
        }
        return if (chain.isEmpty()) visit.locationCode else chain.joinToString(" / ")
    }

    private fun visitRange(visit: ExportVisit): String {
        val start = shortDateTime(visit.startedAt)
        val end = visit.endedAt?.let { " → " + shortTime(it) }
        return start + (end ?: "")
    }

    private fun shortDateTime(iso: String): String = iso.replace('T', ' ').take(16)

    private fun shortTime(iso: String): String = iso.replace('T', ' ').drop(11).take(5)

    private fun equipmentName(e: ExportEquipment, labels: ReportLabels): String {
        val kind = labels.kindNames[e.kind] ?: e.kind
        return "$kind ${e.tag}".trim()
    }

    private fun equipmentStatusLabel(status: String, labels: ReportLabels): String = when (status) {
        "RUNNING" -> labels.eqRunning
        "STOPPED" -> labels.eqStopped
        else -> labels.eqFault
    }

    private fun equipmentStatusStyle(status: String): Int = when (status) {
        "RUNNING" -> XlsxStyle.OK
        "STOPPED" -> XlsxStyle.MINOR
        else -> XlsxStyle.FAULT
    }

    private fun checklistName(item: ExportChecklist): String =
        if (item.itemName.isNotBlank()) item.itemName else item.itemCode

    private fun checklistStatusLabel(status: String, labels: ReportLabels): String = when (status) {
        "OK" -> labels.ok
        "MINOR" -> labels.minor
        else -> labels.fault
    }

    private fun checklistStatusStyle(status: String): Int = when (status) {
        "OK" -> XlsxStyle.OK
        "MINOR" -> XlsxStyle.MINOR
        else -> XlsxStyle.FAULT
    }

    companion object {
        fun sha256Hex(data: ByteArray): String {
            val md = MessageDigest.getInstance("SHA-256")
            return md.digest(data).joinToString("") { "%02x".format(it) }
        }
    }
}
