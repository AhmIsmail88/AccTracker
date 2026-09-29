package com.protrack.app.data

import com.protrack.app.data.db.VisitChecklistEntity
import com.protrack.app.data.db.VisitDao
import com.protrack.app.data.db.VisitEntity
import com.protrack.app.data.db.VisitEquipmentEntity
import com.protrack.app.data.db.VisitPhotoEntity
import com.protrack.app.domain.ChecklistCatalog
import kotlinx.coroutines.flow.Flow
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

class VisitRepository(private val dao: VisitDao) {

    suspend fun createVisit(locationCode: String): Long {
        val now = OffsetDateTime.now()
        val visitId = "VISIT-" + now.format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))
        val id = dao.insertVisit(
            VisitEntity(visitId = visitId, locationCode = locationCode, startedAt = now.toString()),
        )
        ChecklistCatalog.items.forEachIndexed { index, item ->
            dao.insertChecklist(
                VisitChecklistEntity(visitRefId = id, itemCode = item.code, sortOrder = (index + 1).toLong()),
            )
        }
        // معدات آخر زيارة لنفس الموقع بالظبط (نفس عقدة الشجرة) — بقراءات جديدة للزيارة الحالية فقط
        val lastVisit = dao.lastVisitForLocation(locationCode, id)
        if (lastVisit != null) {
            dao.equipmentOnce(lastVisit.id).forEach { e ->
                dao.insertEquipment(
                    VisitEquipmentEntity(
                        visitRefId = id,
                        kind = e.kind,
                        tag = e.tag,
                        model = e.model,
                    ),
                )
            }
        }
        return id
    }

    fun visit(id: Long): Flow<VisitEntity?> = dao.visitByIdFlow(id)

    suspend fun visitById(id: Long): VisitEntity? = dao.visitById(id)

    fun equipment(visitRefId: Long): Flow<List<VisitEquipmentEntity>> = dao.equipmentFlow(visitRefId)

    suspend fun equipmentForOnce(visitRefId: Long): List<VisitEquipmentEntity> = dao.equipmentOnce(visitRefId)

    fun checklist(visitRefId: Long): Flow<List<VisitChecklistEntity>> = dao.checklistFlow(visitRefId)

    suspend fun checklistForOnce(visitRefId: Long): List<VisitChecklistEntity> = dao.checklistOnce(visitRefId)

    fun photos(visitRefId: Long): Flow<List<VisitPhotoEntity>> = dao.photosFlow(visitRefId)

    suspend fun photosForOnce(visitRefId: Long): List<VisitPhotoEntity> = dao.photosOnce(visitRefId)

    suspend fun addPhoto(entity: VisitPhotoEntity) {
        dao.insertPhoto(entity)
    }

    suspend fun addEquipment(visitRefId: Long, kind: String, model: String, quantity: Int) {
        val existing = dao.equipmentOnce(visitRefId)
        var n = existing.count { it.kind == kind }
        repeat(quantity) {
            n += 1
            dao.insertEquipment(
                VisitEquipmentEntity(
                    visitRefId = visitRefId,
                    kind = kind,
                    tag = n.toString().padStart(2, '0'),
                    model = model,
                ),
            )
        }
    }

    suspend fun updateEquipment(entity: VisitEquipmentEntity) = dao.updateEquipment(entity)

    suspend fun deleteEquipment(entity: VisitEquipmentEntity) = dao.deleteEquipment(entity.id)

    suspend fun updateChecklist(entity: VisitChecklistEntity) = dao.updateChecklist(entity)

    /** إضافة بند مخصص (من الميدان) — يظهر آخر القائمة. */
    suspend fun addChecklistItem(visitRefId: Long, name: String, status: String, note: String) {
        val existing = dao.checklistOnce(visitRefId)
        val customCount = existing.count { it.isCustom }
        val nextOrder = (existing.maxOfOrNull { it.sortOrder } ?: 0L) + 1
        dao.insertChecklist(
            VisitChecklistEntity(
                visitRefId = visitRefId,
                itemCode = "CUSTOM-" + (customCount + 1),
                itemName = name.trim(),
                isCustom = true,
                sortOrder = nextOrder,
                status = status,
                note = note.trim(),
            ),
        )
    }

    suspend fun setNotes(id: Long, notes: String) = dao.setNotes(id, notes)

    suspend fun markEnded(id: Long, endedAt: String) = dao.setEndedAt(id, endedAt)

    suspend fun markExported(id: Long, packageName: String) =
        dao.markExported(id, packageName, OffsetDateTime.now().toString())

    suspend fun deleteChecklistItem(entity: VisitChecklistEntity) = dao.deleteChecklist(entity.id)

    suspend fun allVisitsOnce(): List<VisitEntity> = dao.allVisitsOnce()

    suspend fun equipmentCountOnce(visitRefId: Long): Int = dao.equipmentCountOnce(visitRefId)

    suspend fun issueCountOnce(visitRefId: Long): Int = dao.issueCountOnce(visitRefId)

    suspend fun photoCountOnce(visitRefId: Long): Int = dao.photoCountOnce(visitRefId)
}
