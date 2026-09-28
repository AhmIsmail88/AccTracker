package com.protrack.app.data

import android.content.Context
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.export.ExportChecklist
import com.protrack.app.domain.export.ExportEquipment
import com.protrack.app.domain.export.ExportLocation
import com.protrack.app.domain.export.ExportMeta
import com.protrack.app.domain.export.ExportVisit
import com.protrack.app.domain.export.PackageBuilder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID

data class ExportOutcome(
    val ok: Boolean,
    val error: String? = null,
    val file: File? = null,
    val fileName: String? = null,
)

/**
 * تصدير حزمة الزيارة: يبني visit.xlsx + manifest.json + manifest.sig داخل ZIP
 * في مجلد التطبيق الخاص (packages/) ثم يعلّم العناصر المُصدَّرة كـ SYNCED.
 */
class PackageExporter(
    private val context: Context,
    private val visitRepository: VisitRepository,
    private val hierarchyRepository: HierarchyRepository,
    private val deviceInfo: DeviceInfoProvider,
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
                    ExportChecklist(itemCode = it.itemCode, status = it.status, note = it.note)
                },
                locations = locationNodes.map {
                    ExportLocation(
                        code = it.code, type = it.type.name, parentCode = it.parentCode,
                        name = it.name, status = it.status, updatedAt = it.updatedAt,
                    )
                },
                photos = emptyList(), // الكاميرا تُوصل في الجزء التالي
            )

            val dir = File(context.getExternalFilesDir(null), "packages").apply { mkdirs() }
            val stamp = OffsetDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))
            val fileName = "Visit_${visit.locationCode}_$stamp.zip"
            val file = File(dir, fileName)
            file.writeBytes(bytes)

            visitRepository.markExported(visitId, fileName)
            val toSync = locationNodes.filter { it.syncState != "SYNCED" }
            if (toSync.isNotEmpty()) {
                hierarchyRepository.markSynced(toSync)
            }

            ExportOutcome(true, null, file, fileName)
        } catch (e: Exception) {
            ExportOutcome(false, e.message ?: e.toString())
        }
    }

    private fun typeOrder(type: NodeType): Int = when (type) {
        NodeType.PROJECT -> 0
        NodeType.REGION -> 1
        NodeType.ZONE -> 2
        NodeType.LOCATION -> 3
    }
}
