package com.protrack.app.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface VisitDao {

    @Insert
    suspend fun insertVisit(entity: VisitEntity): Long

    @Insert
    suspend fun insertEquipment(entity: VisitEquipmentEntity): Long

    @Insert
    suspend fun insertChecklist(entity: VisitChecklistEntity): Long

    @Insert
    suspend fun insertPhoto(entity: VisitPhotoEntity): Long

    @Update
    suspend fun updateEquipment(entity: VisitEquipmentEntity)

    @Update
    suspend fun updateChecklist(entity: VisitChecklistEntity)

    @Query("SELECT * FROM visit WHERE id = :id")
    suspend fun visitById(id: Long): VisitEntity?

    @Query("SELECT * FROM visit WHERE id = :id")
    fun visitByIdFlow(id: Long): Flow<VisitEntity?>

    @Query("SELECT * FROM visit_equipment WHERE visitRefId = :visitRefId ORDER BY id")
    fun equipmentFlow(visitRefId: Long): Flow<List<VisitEquipmentEntity>>

    @Query("SELECT * FROM visit_equipment WHERE visitRefId = :visitRefId ORDER BY id")
    suspend fun equipmentOnce(visitRefId: Long): List<VisitEquipmentEntity>

    @Query("SELECT * FROM visit_checklist_item WHERE visitRefId = :visitRefId ORDER BY id")
    fun checklistFlow(visitRefId: Long): Flow<List<VisitChecklistEntity>>

    @Query("SELECT * FROM visit_checklist_item WHERE visitRefId = :visitRefId ORDER BY id")
    suspend fun checklistOnce(visitRefId: Long): List<VisitChecklistEntity>

    @Query("SELECT * FROM visit_photo WHERE visitRefId = :visitRefId ORDER BY id")
    fun photosFlow(visitRefId: Long): Flow<List<VisitPhotoEntity>>

    @Query("SELECT * FROM visit_photo WHERE visitRefId = :visitRefId ORDER BY id")
    suspend fun photosOnce(visitRefId: Long): List<VisitPhotoEntity>

    @Query("UPDATE visit SET notes = :notes WHERE id = :id")
    suspend fun setNotes(id: Long, notes: String)

    @Query("UPDATE visit SET endedAt = :endedAt WHERE id = :id")
    suspend fun setEndedAt(id: Long, endedAt: String)

    @Query("UPDATE visit SET status = 'EXPORTED', packageName = :packageName, exportedAt = :exportedAt WHERE id = :id")
    suspend fun markExported(id: Long, packageName: String, exportedAt: String)
}
