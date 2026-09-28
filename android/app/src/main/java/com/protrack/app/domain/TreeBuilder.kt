package com.protrack.app.domain

import com.protrack.app.data.db.LocationEntity
import com.protrack.app.data.db.ProjectEntity
import com.protrack.app.data.db.RegionEntity
import com.protrack.app.data.db.ZoneEntity

object TreeBuilder {

    fun build(
        projects: List<ProjectEntity>,
        regions: List<RegionEntity>,
        zones: List<ZoneEntity>,
        locations: List<LocationEntity>,
    ): List<TreeNode> {
        val regionsByProject = regions.groupBy { it.projectCode }
        val zonesByRegion = zones.groupBy { it.regionCode }
        val locationsByZone = locations.groupBy { it.zoneCode }

        return projects.sortedBy { it.code }.map { p ->
            TreeNode(
                type = NodeType.PROJECT,
                code = p.code,
                name = p.name,
                status = p.status,
                children = regionsByProject[p.code].orEmpty().sortedBy { it.code }.map { r ->
                    TreeNode(
                        type = NodeType.REGION,
                        code = r.code,
                        name = r.name,
                        status = r.status,
                        children = zonesByRegion[r.code].orEmpty().sortedBy { it.code }.map { z ->
                            TreeNode(
                                type = NodeType.ZONE,
                                code = z.code,
                                name = z.name,
                                status = z.status,
                                children = locationsByZone[z.code].orEmpty().sortedBy { it.code }.map { l ->
                                    TreeNode(
                                        type = NodeType.LOCATION,
                                        code = l.code,
                                        name = l.name,
                                        status = l.status,
                                    )
                                },
                            )
                        },
                    )
                },
            )
        }
    }

    fun flatten(tree: List<TreeNode>, expanded: Set<String>): List<TreeRow> {
        val out = mutableListOf<TreeRow>()

        fun rec(nodes: List<TreeNode>, depth: Int) {
            for (node in nodes) {
                val hasChildren = node.children.isNotEmpty()
                val isExpanded = node.code in expanded
                out += TreeRow(node, depth, hasChildren, isExpanded)
                if (hasChildren && isExpanded) {
                    rec(node.children, depth + 1)
                }
            }
        }

        rec(tree, 0)
        return out
    }
}
