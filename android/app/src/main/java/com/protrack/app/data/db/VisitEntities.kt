package com.protrack.app.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

/** جداول الزيارة أوفلاين (مطابقة لأعمدة العقد — §4.3). */

@Entity(tableName = "visit")
data class VisitEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val visitId: String,
    val locationCode: String,
    val visitType: String = "ROUTINE",
    val startedAt: String,
    val endedAt: String? = null,
    val notes: String = "",
    val status: String = "DRAFT",
    val packageName: String? = null,
    val exportedAt: String? = null,
)

@Entity(tableName = "visit_equipment")
data class VisitEquipmentEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val visitRefId: Long,
    val kind: String,
    val tag: String,
    val model: String,
    val runningHours: Double? = null,
    val pressureBar: Double? = null,
    val status: String = "RUNNING",
    val note: String = "",
)

@Entity(tableName = "visit_checklist_item")
data class VisitChecklistEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val visitRefId: Long,
    val itemCode: String,
    val status: String = "OK",
    val note: String = "",
)

@Entity(tableName = "visit_photo")
data class VisitPhotoEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val visitRefId: Long,
    val targetType: String,
    val targetRef: String,
    val filePath: String,
    val takenAt: String,
    val lat: Double? = null,
    val lon: Double? = null,
    val accuracyM: Double? = null,
    val sha256: String,
    val captureSig: String,
)
