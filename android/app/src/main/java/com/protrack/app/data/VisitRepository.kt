package com.protrack.app.data

import com.protrack.app.data.db.VisitChecklistEntity
import com.protrack.app.data.db.VisitDao
import com.protrack.app.data.db.VisitEntity
import com.protrack.app.data.db.VisitEquipmentEntity
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
        ChecklistCatalog.items.forEach { item ->
            dao.insertChecklist(VisitChecklistEntity(visitRefId = id, itemCode = item.code))
        }
        return id
    }

    fun visit(id: Long): Flow<VisitEntity?> = dao.visitByIdFlow(id)

    suspend fun visitById(id: Long): VisitEntity? = dao.visitById(id)

    fun equipment(visitRefId: Long): Flow<List<VisitEquipmentEntity>> = dao.equipmentFlow(visitRefId)

    suspend fun equipmentForOnce(visitRefId: Long): List<VisitEquipmentEntity> = dao.equipmentOnce(visitRefId)

    fun checklist(visitRefId: Long): Flow<List<VisitChecklistEntity>> = dao.checklistFlow(visitRefId)

    suspend fun checklistForOnce(visitRefId: Long): List<VisitChecklistEntity> = dao.checklistOnce(visitRefId)

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

    suspend fun updateChecklist(entity: VisitChecklistEntity) = dao.updateChecklist(entity)

    suspend fun setNotes(id: Long, notes: String) = dao.setNotes(id, notes)

    suspend fun markEnded(id: Long, endedAt: String) = dao.setEndedAt(id, endedAt)

    suspend fun markExported(id: Long, packageName: String) =
        dao.markExported(id, packageName, OffsetDateTime.now().toString())
}
