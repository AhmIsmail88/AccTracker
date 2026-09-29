package com.protrack.app.data

import android.content.Context
import android.content.res.Configuration
import com.protrack.app.R
import com.protrack.app.data.cloud.PackageSyncWorker
import com.protrack.app.domain.ChecklistCatalog
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.export.ExportChecklist
import com.protrack.app.domain.export.ExportEquipment
import com.protrack.app.domain.export.ExportLocation
import com.protrack.app.domain.export.ExportMeta
import com.protrack.app.domain.export.ExportNames
import com.protrack.app.domain.export.ExportPhoto
import com.protrack.app.domain.export.ExportVisit
import com.protrack.app.domain.export.PackageBuilder
import com.protrack.app.domain.export.ReportLabels
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.UUID

data class ExportOutcome(
    val ok: Boolean,
    val error: String? = null,
    val file: File? = null,
    val fileName: String? = null,
)

/**
 * تصدير حزمة الزيارة: يبني visit.xlsx + الصور + manifest.json + manifest.sig داخل ZIP
 * في مجلد التطبيق الخاص (packages/) ثم يعلّم العناصر المُصدَّرة كـ SYNCED.
 */
class PackageExporter(
    private val context: Context,
    private val visitRepository: VisitRepository,
    private val hierarchyRepository: HierarchyRepository,
    private val deviceInfo: DeviceInfoProvider,
    private val settings: AppSettings,
) {

    suspend fun export(visitId: Long, notes: String): ExportOutcome = withContext(Dispatchers.IO) {
        try {
            val visit = visitRepository.visitById(visitId)
                ?: return@withContext ExportOutcome(false, "visit not found")

            visitRepository.setNotes(visitId, notes)
            val endedAt = OffsetDateTime.now().toString()
            visitRepository.markEnded(visitId, endedAt)

            val equipment = visitRepository.equipmentForOnce(visitId)
            val checklist = visitRepository.checklistForOnce(visitId)

            val photos = visitRepository.photosForOnce(visitId).mapNotNull { p ->
                try {
                    val f = File(p.filePath)
                    if (!f.exists()) {
                        null
                    } else {
                        ExportPhoto(
                            fileName = f.name,
                            bytes = f.readBytes(),
                            takenAt = p.takenAt,
                            lat = p.lat ?: 0.0,
                            lon = p.lon ?: 0.0,
                            accuracyM = p.accuracyM ?: 0.0,
                            targetType = p.targetType,
                            targetRef = p.targetRef,
                        )
                    }
                } catch (e: Exception) {
                    null
                }
            }

            val chain = hierarchyRepository.locationChain(visit.locationCode)
            val pending = hierarchyRepository.pendingNodes()
            val locationNodes = (chain + pending)
                .distinctBy { it.type to it.code }
                .sortedWith(compareBy({ typeOrder(it.type) }, { it.code }))

            val meta = ExportMeta(
                packageId = UUID.randomUUID().toString(),
                createdAt = OffsetDateTime.now().toString(),
                deviceId = deviceInfo.deviceId(),
                publicKeyB64 = deviceInfo.publicKeyB64(),
                fingerprint = deviceInfo.fingerprint(),
            )

            val builder = PackageBuilder(deviceInfo.signer)
            val bytes = builder.build(
                meta = meta,
                visit = ExportVisit(
                    visitId = visit.visitId,
                    locationCode = visit.locationCode,
                    visitType = visit.visitType,
                    startedAt = visit.startedAt,
                    endedAt = endedAt,
                    notes = notes,
                    status = "EXPORTED",
                ),
                equipment = equipment.map {
                    ExportEquipment(
                        kind = it.kind, tag = it.tag, model = it.model,
                        runningHours = it.runningHours, pressureBar = it.pressureBar,
                        status = it.status, note = it.note,
                    )
                },
                checklist = checklist.map {
                    ExportChecklist(
                        itemCode = it.itemCode,
                        status = it.status,
                        note = it.note,
                        itemName = if (it.itemName.isNotBlank()) it.itemName else ChecklistCatalog.nameFor(it.itemCode),
                    )
                },
                locations = locationNodes.map {
                    ExportLocation(
                        code = it.code, type = it.type.name, parentCode = it.parentCode,
                        name = it.name, status = it.status, updatedAt = it.updatedAt,
                    )
                },
                photos = photos,
                technician = settings.technicianName,
                appVersion = appVersion(),
                labels = reportLabels(),
            )

            val dir = File(context.getExternalFilesDir(null), "packages").apply { mkdirs() }
            val stamp = OffsetDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))
            val fileName = ExportNames.visitFileName(visit.locationCode, stamp, settings.technicianName)
            val file = File(dir, fileName)
            file.writeBytes(bytes)

            visitRepository.markExported(visitId, fileName)
            val toSync = locationNodes.filter { it.syncState != "SYNCED" }
            if (toSync.isNotEmpty()) {
                hierarchyRepository.markSynced(toSync)
            }
            // مزامنة سحابية تلقائية أول ما النت يتوفر
            PackageSyncWorker.enqueue(context)

            ExportOutcome(true, null, file, fileName)
        } catch (e: Exception) {
            ExportOutcome(false, e.message ?: e.toString())
        }
    }

    private fun appVersion(): String = try {
        context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: ""
    } catch (e: Exception) {
        ""
    }

    /** سياق موارد بلغة التطبيق المختارة (لو محددة) — يضمن أن تقرير الإدارة بلغة المستخدم. */
    private fun localizedContext(): Context {
        val language = settings.languageCode
        if (language.isNullOrBlank()) return context
        return try {
            val config = Configuration(context.resources.configuration)
            config.setLocale(Locale(language))
            context.createConfigurationContext(config)
        } catch (e: Exception) {
            context
        }
    }

    private fun reportLabels(): ReportLabels {
        // applicationContext لا يحمل لغة التطبيق المختارة — نستخدم سياقًا بلغة التطبيق.
        val context = localizedContext()
        return ReportLabels(
        title = context.getString(R.string.report_title),
        location = context.getString(R.string.report_label_location),
        dateTime = context.getString(R.string.report_label_datetime),
        technician = context.getString(R.string.report_label_technician),
        summary = context.getString(R.string.report_label_summary),
        summaryOk = context.getString(R.string.report_summary_ok),
        summaryMinor = context.getString(R.string.report_summary_minor),
        summaryFault = context.getString(R.string.report_summary_fault),
        summaryExtra = context.getString(R.string.report_summary_extra),
        equipmentSection = context.getString(R.string.report_section_equipment),
        checklistSection = context.getString(R.string.report_section_checklist),
        photosSection = context.getString(R.string.report_section_photos),
        notesSection = context.getString(R.string.report_section_notes),
        colEquipment = context.getString(R.string.report_col_equipment),
        colModel = context.getString(R.string.report_col_model),
        colHours = context.getString(R.string.report_col_hours),
        colPressure = context.getString(R.string.report_col_pressure),
        colStatus = context.getString(R.string.report_col_status),
        colNotes = context.getString(R.string.report_col_notes),
        colItem = context.getString(R.string.report_col_item),
        colItemNotes = context.getString(R.string.report_col_item_notes),
        ok = context.getString(R.string.chk_ok),
        minor = context.getString(R.string.chk_minor),
        fault = context.getString(R.string.chk_fault),
        eqRunning = context.getString(R.string.report_eq_running),
        eqStopped = context.getString(R.string.report_eq_stopped),
        eqFault = context.getString(R.string.chk_fault),
        kindNames = mapOf(
            "MAIN_PUMP" to context.getString(R.string.kind_main_pump),
            "SUBMERSIBLE_PUMP" to context.getString(R.string.kind_submersible),
            "FILTER" to context.getString(R.string.kind_filter),
        ),
        photoLabel = context.getString(R.string.report_photo_line),
        footer = context.getString(R.string.report_footer),
        emptyEquipment = context.getString(R.string.report_empty_equipment),
        emptyPhotos = context.getString(R.string.report_empty_photos),
        signatureBy = context.getString(R.string.report_signature_by),
        signatureLine = context.getString(R.string.report_signature_line),
        )
    }

    private fun typeOrder(type: NodeType): Int = when (type) {
        NodeType.PROJECT -> 0
        NodeType.REGION -> 1
        NodeType.ZONE -> 2
        NodeType.LOCATION -> 3
    }
}
