package com.protrack.app.data.db

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * جداول التقسيم الإداري أوفلاين (وفق عقد §3.4):
 * الكود هو الهوية، وsyncState لتتبع ما لم يُصدَّر بعد.
 */

@Entity(tableName = "project", indices = [Index(value = ["code"], unique = true)])
data class ProjectEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String,
    val name: String,
    val status: String = "ACTIVE",
    val syncState: String = "NEW",
    val createdAt: String,
    val updatedAt: String,
)

@Entity(tableName = "region", indices = [Index(value = ["code"], unique = true)])
data class RegionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String,
    val projectCode: String,
    val name: String,
    val status: String = "ACTIVE",
    val syncState: String = "NEW",
    val createdAt: String,
    val updatedAt: String,
)

@Entity(tableName = "zone", indices = [Index(value = ["code"], unique = true)])
data class ZoneEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String,
    val regionCode: String,
    val name: String,
    val status: String = "ACTIVE",
    val syncState: String = "NEW",
    val createdAt: String,
    val updatedAt: String,
)

@Entity(tableName = "location", indices = [Index(value = ["code"], unique = true)])
data class LocationEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String,
    val zoneCode: String,
    val name: String,
    val status: String = "ACTIVE",
    val syncState: String = "NEW",
    val createdAt: String,
    val updatedAt: String,
)
