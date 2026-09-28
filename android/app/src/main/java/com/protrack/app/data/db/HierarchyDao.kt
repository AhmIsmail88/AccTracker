package com.protrack.app.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface HierarchyDao {

    @Query("SELECT * FROM project ORDER BY code")
    fun projects(): Flow<List<ProjectEntity>>

    @Query("SELECT * FROM region ORDER BY code")
    fun regions(): Flow<List<RegionEntity>>

    @Query("SELECT * FROM zone ORDER BY code")
    fun zones(): Flow<List<ZoneEntity>>

    @Query("SELECT * FROM location ORDER BY code")
    fun locations(): Flow<List<LocationEntity>>

    @Query("SELECT code FROM project")
    suspend fun projectCodes(): List<String>

    @Query("SELECT code FROM region")
    suspend fun regionCodes(): List<String>

    @Query("SELECT code FROM zone")
    suspend fun zoneCodes(): List<String>

    @Query("SELECT code FROM location")
    suspend fun locationCodes(): List<String>

    @Query("SELECT * FROM project WHERE code = :code")
    suspend fun projectByCode(code: String): ProjectEntity?

    @Query("SELECT * FROM region WHERE code = :code")
    suspend fun regionByCode(code: String): RegionEntity?

    @Query("SELECT * FROM zone WHERE code = :code")
    suspend fun zoneByCode(code: String): ZoneEntity?

    @Query("SELECT * FROM location WHERE code = :code")
    suspend fun locationByCode(code: String): LocationEntity?

    @Insert
    suspend fun insertProject(entity: ProjectEntity)

    @Insert
    suspend fun insertRegion(entity: RegionEntity)

    @Insert
    suspend fun insertZone(entity: ZoneEntity)

    @Insert
    suspend fun insertLocation(entity: LocationEntity)

    @Update
    suspend fun updateProject(entity: ProjectEntity)

    @Update
    suspend fun updateRegion(entity: RegionEntity)

    @Update
    suspend fun updateZone(entity: ZoneEntity)

    @Update
    suspend fun updateLocation(entity: LocationEntity)

    @Query("UPDATE project SET syncState = 'SYNCED' WHERE code = :code")
    suspend fun markProjectSynced(code: String)

    @Query("UPDATE region SET syncState = 'SYNCED' WHERE code = :code")
    suspend fun markRegionSynced(code: String)

    @Query("UPDATE zone SET syncState = 'SYNCED' WHERE code = :code")
    suspend fun markZoneSynced(code: String)

    @Query("UPDATE location SET syncState = 'SYNCED' WHERE code = :code")
    suspend fun markLocationSynced(code: String)

    @Query("SELECT COUNT(*) FROM region WHERE projectCode = :code")
    suspend fun regionCountUnderProject(code: String): Int

    @Query("SELECT COUNT(*) FROM zone WHERE regionCode = :code")
    suspend fun zoneCountUnderRegion(code: String): Int

    @Query("SELECT COUNT(*) FROM location WHERE zoneCode = :code")
    suspend fun locationCountUnderZone(code: String): Int

    @Query("DELETE FROM project WHERE code = :code")
    suspend fun deleteProject(code: String)

    @Query("DELETE FROM region WHERE code = :code")
    suspend fun deleteRegion(code: String)

    @Query("DELETE FROM zone WHERE code = :code")
    suspend fun deleteZone(code: String)

    @Query("DELETE FROM location WHERE code = :code")
    suspend fun deleteLocation(code: String)
}
