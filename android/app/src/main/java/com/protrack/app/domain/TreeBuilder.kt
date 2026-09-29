package com.protrack.app.domain

import com.protrack.app.data.db.LocationEntity
import com.protrack.app.data.db.ProjectEntity
import com.protrack.app.data.db.RegionEntity
import com.protrack.app.data.db.ZoneEntity

private data class FlatNode(
    val type: NodeType,
    val code: String,
    val name: String,
    val status: String,
    val parent: String?,
)

object TreeBuilder {

    /**
     * يبني الشجرة بمرونة: أي عقدة تتعلّق بأي أب أعلى حسب الكود المخزّن —
     * مش لازم كل المستويات موجودة (يتخطى الناقص). الجذور = المشاريع.
     */
    fun build(
        projects: List<ProjectEntity>,
        regions: List<RegionEntity>,
        zones: List<ZoneEntity>,
        locations: List<LocationEntity>,
    ): List<TreeNode> {
        val flat = mutableListOf<FlatNode>()
        projects.forEach { flat += FlatNode(NodeType.PROJECT, it.code, it.name, it.status, null) }
        regions.forEach { flat += FlatNode(NodeType.REGION, it.code, it.name, it.status, it.projectCode.ifBlank { null }) }
        zones.forEach { flat += FlatNode(NodeType.ZONE, it.code, it.name, it.status, it.regionCode.ifBlank { null }) }
        locations.forEach { flat += FlatNode(NodeType.LOCATION, it.code, it.name, it.status, it.zoneCode.ifBlank { null }) }

        val childrenByParent = flat.filter { !it.parent.isNullOrBlank() }.groupBy { it.parent }

        fun nodeOf(f: FlatNode, seen: Set<String>): TreeNode {
            val next = seen + f.code
            val kids = childrenByParent[f.code].orEmpty()
                .filter { it.code !in next }
                .sortedBy { it.code }
            return TreeNode(
                type = f.type,
                code = f.code,
                name = f.name,
                status = f.status,
                children = kids.map { nodeOf(it, next) },
            )
        }

        return flat
            .filter { it.type == NodeType.PROJECT }
            .sortedBy { it.code }
            .map { nodeOf(it, emptySet()) }
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
