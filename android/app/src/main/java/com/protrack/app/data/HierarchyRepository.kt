package com.protrack.app.data

import com.protrack.app.data.db.HierarchyDao
import com.protrack.app.data.db.LocationEntity
import com.protrack.app.data.db.ProjectEntity
import com.protrack.app.data.db.RegionEntity
import com.protrack.app.data.db.VisitDao
import com.protrack.app.data.db.ZoneEntity
import com.protrack.app.domain.CodeGenerator
import com.protrack.app.domain.NodeType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import java.time.OffsetDateTime

data class HierarchyData(
    val projects: List<ProjectEntity>,
    val regions: List<RegionEntity>,
    val zones: List<ZoneEntity>,
    val locations: List<LocationEntity>,
)

/** عقدة تقسيم موحّدة تُستخدم في التصدير (الكود + الأب + حالة المزامنة). */
data class HierarchyNode(
    val type: NodeType,
    val code: String,
    val parentCode: String?,
    val name: String,
    val status: String,
    val updatedAt: String,
    val syncState: String,
)

/** نتيجة محاولة حذف عنصر تقسيم. */
enum class DeleteNodeResult { DELETED, BLOCKED_HAS_CHILDREN, BLOCKED_HAS_VISITS }

class HierarchyRepository(
    private val dao: HierarchyDao,
    private val visitDao: VisitDao? = null,
) {

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

    /** سلسلة الموقع الكاملة من الموقع للأعلى — بتدعم تخطي المستويات (أي أب أعلى). */
    suspend fun locationChain(locationCode: String): List<HierarchyNode> {
        val out = mutableListOf<HierarchyNode>()
        var code: String? = locationCode
        var guard = 0
        while (!code.isNullOrBlank() && guard < 10) {
            val node = nodeByCode(code) ?: break
            out += node
            code = node.parentCode
            guard += 1
        }
        return out
    }

    /** العقدة بالكود — النوع يتحدد من بادئة الكود (PRJ/RGN/ZN/LOC). */
    suspend fun nodeByCode(code: String): HierarchyNode? = when {
        code.startsWith("PRJ-") -> dao.projectByCode(code)?.let {
            HierarchyNode(NodeType.PROJECT, it.code, null, it.name, it.status, it.updatedAt, it.syncState)
        }
        code.startsWith("RGN-") -> dao.regionByCode(code)?.let {
            HierarchyNode(NodeType.REGION, it.code, it.projectCode.ifBlank { null }, it.name, it.status, it.updatedAt, it.syncState)
        }
        code.startsWith("ZN-") -> dao.zoneByCode(code)?.let {
            HierarchyNode(NodeType.ZONE, it.code, it.regionCode.ifBlank { null }, it.name, it.status, it.updatedAt, it.syncState)
        }
        code.startsWith("LOC-") -> dao.locationByCode(code)?.let {
            HierarchyNode(NodeType.LOCATION, it.code, it.zoneCode.ifBlank { null }, it.name, it.status, it.updatedAt, it.syncState)
        }
        else -> null
    }

    /** كل العناصر المعلّقة (أُضيفت/عُدّلت محليًا ولم تُصدَّر بعد). */
    suspend fun pendingNodes(): List<HierarchyNode> {
        val out = mutableListOf<HierarchyNode>()
        dao.projects().first().forEach {
            if (it.syncState != "SYNCED") {
                out += HierarchyNode(NodeType.PROJECT, it.code, null, it.name, it.status, it.updatedAt, it.syncState)
            }
        }
        dao.regions().first().forEach {
            if (it.syncState != "SYNCED") {
                out += HierarchyNode(NodeType.REGION, it.code, it.projectCode.ifBlank { null }, it.name, it.status, it.updatedAt, it.syncState)
            }
        }
        dao.zones().first().forEach {
            if (it.syncState != "SYNCED") {
                out += HierarchyNode(NodeType.ZONE, it.code, it.regionCode.ifBlank { null }, it.name, it.status, it.updatedAt, it.syncState)
            }
        }
        dao.locations().first().forEach {
            if (it.syncState != "SYNCED") {
                out += HierarchyNode(NodeType.LOCATION, it.code, it.zoneCode.ifBlank { null }, it.name, it.status, it.updatedAt, it.syncState)
            }
        }
        return out
    }

    suspend fun markSynced(nodes: List<HierarchyNode>) {
        nodes.forEach { node ->
            when (node.type) {
                NodeType.PROJECT -> dao.markProjectSynced(node.code)
                NodeType.REGION -> dao.markRegionSynced(node.code)
                NodeType.ZONE -> dao.markZoneSynced(node.code)
                NodeType.LOCATION -> dao.markLocationSynced(node.code)
            }
        }
    }

    /** حذف عنصر — مسموح فقط لو مفيش عناصر تحته ولا زيارات مرتبطة بالموقع. */
    suspend fun deleteNode(type: NodeType, code: String): DeleteNodeResult {
        val childCount = when (type) {
            NodeType.PROJECT -> dao.regionCountUnderProject(code) +
                dao.zoneCountUnderRegion(code) + dao.locationCountUnderZone(code)
            NodeType.REGION -> dao.zoneCountUnderRegion(code) + dao.locationCountUnderZone(code)
            NodeType.ZONE -> dao.locationCountUnderZone(code)
            NodeType.LOCATION -> 0
        }
        if (childCount > 0) return DeleteNodeResult.BLOCKED_HAS_CHILDREN
        if (type == NodeType.LOCATION && visitDao != null && visitDao.visitCountForLocation(code) > 0) {
            return DeleteNodeResult.BLOCKED_HAS_VISITS
        }
        when (type) {
            NodeType.PROJECT -> dao.deleteProject(code)
            NodeType.REGION -> dao.deleteRegion(code)
            NodeType.ZONE -> dao.deleteZone(code)
            NodeType.LOCATION -> dao.deleteLocation(code)
        }
        return DeleteNodeResult.DELETED
    }

    private fun nowIso(): String = OffsetDateTime.now().toString()
}
