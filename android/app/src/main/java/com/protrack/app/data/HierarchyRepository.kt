package com.protrack.app.data

import com.protrack.app.data.db.HierarchyDao
import com.protrack.app.data.db.LocationEntity
import com.protrack.app.data.db.ProjectEntity
import com.protrack.app.data.db.RegionEntity
import com.protrack.app.data.db.ZoneEntity
import com.protrack.app.domain.CodeGenerator
import com.protrack.app.domain.NodeType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import java.time.OffsetDateTime

data class HierarchyData(
    val projects: List<ProjectEntity>,
    val regions: List<RegionEntity>,
    val zones: List<ZoneEntity>,
    val locations: List<LocationEntity>,
)

class HierarchyRepository(private val dao: HierarchyDao) {

    val data: Flow<HierarchyData> = combine(
        dao.projects(), dao.regions(), dao.zones(), dao.locations(),
    ) { projects, regions, zones, locations ->
        HierarchyData(projects, regions, zones, locations)
    }

    suspend fun addNode(type: NodeType, name: String, parentCode: String?) {
        val now = nowIso()
        val code = when (type) {
            NodeType.PROJECT -> CodeGenerator.nextCode(type, dao.projectCodes())
            NodeType.REGION -> CodeGenerator.nextCode(type, dao.regionCodes())
            NodeType.ZONE -> CodeGenerator.nextCode(type, dao.zoneCodes())
            NodeType.LOCATION -> CodeGenerator.nextCode(type, dao.locationCodes())
        }
        when (type) {
            NodeType.PROJECT -> dao.insertProject(
                ProjectEntity(code = code, name = name, createdAt = now, updatedAt = now)
            )
            NodeType.REGION -> dao.insertRegion(
                RegionEntity(
                    code = code, projectCode = parentCode.orEmpty(), name = name,
                    createdAt = now, updatedAt = now,
                )
            )
            NodeType.ZONE -> dao.insertZone(
                ZoneEntity(
                    code = code, regionCode = parentCode.orEmpty(), name = name,
                    createdAt = now, updatedAt = now,
                )
            )
            NodeType.LOCATION -> dao.insertLocation(
                LocationEntity(
                    code = code, zoneCode = parentCode.orEmpty(), name = name,
                    createdAt = now, updatedAt = now,
                )
            )
        }
    }

    suspend fun rename(type: NodeType, code: String, newName: String) {
        val now = nowIso()
        when (type) {
            NodeType.PROJECT -> dao.projectByCode(code)?.let {
                dao.updateProject(it.copy(name = newName, syncState = "UPDATED", updatedAt = now))
            }
            NodeType.REGION -> dao.regionByCode(code)?.let {
                dao.updateRegion(it.copy(name = newName, syncState = "UPDATED", updatedAt = now))
            }
            NodeType.ZONE -> dao.zoneByCode(code)?.let {
                dao.updateZone(it.copy(name = newName, syncState = "UPDATED", updatedAt = now))
            }
            NodeType.LOCATION -> dao.locationByCode(code)?.let {
                dao.updateLocation(it.copy(name = newName, syncState = "UPDATED", updatedAt = now))
            }
        }
    }

    suspend fun setStatus(type: NodeType, code: String, status: String) {
        val now = nowIso()
        when (type) {
            NodeType.PROJECT -> dao.projectByCode(code)?.let {
                dao.updateProject(it.copy(status = status, syncState = "UPDATED", updatedAt = now))
            }
            NodeType.REGION -> dao.regionByCode(code)?.let {
                dao.updateRegion(it.copy(status = status, syncState = "UPDATED", updatedAt = now))
            }
            NodeType.ZONE -> dao.zoneByCode(code)?.let {
                dao.updateZone(it.copy(status = status, syncState = "UPDATED", updatedAt = now))
            }
            NodeType.LOCATION -> dao.locationByCode(code)?.let {
                dao.updateLocation(it.copy(status = status, syncState = "UPDATED", updatedAt = now))
            }
        }
    }

    private fun nowIso(): String = OffsetDateTime.now().toString()
}
