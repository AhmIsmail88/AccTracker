package com.protrack.app.domain

enum class NodeType {
    PROJECT, REGION, ZONE, LOCATION;

    val childType: NodeType?
        get() = when (this) {
            PROJECT -> REGION
            REGION -> ZONE
            ZONE -> LOCATION
            LOCATION -> null
        }

    val parentType: NodeType?
        get() = when (this) {
            PROJECT -> null
            REGION -> PROJECT
            ZONE -> REGION
            LOCATION -> ZONE
        }
}

data class TreeNode(
    val type: NodeType,
    val code: String,
    val name: String,
    val status: String,
    val children: List<TreeNode> = emptyList(),
)

data class TreeRow(
    val node: TreeNode,
    val depth: Int,
    val hasChildren: Boolean,
    val expanded: Boolean,
)
