package com.protrack.app.domain

/**
 * توليد أكواد العناصر أوفلاين وفق العقد:
 * PRJ-### / RGN-### / ZN-### / LOC-###
 */
object CodeGenerator {

    fun prefixFor(type: NodeType): String = when (type) {
        NodeType.PROJECT -> "PRJ"
        NodeType.REGION -> "RGN"
        NodeType.ZONE -> "ZN"
        NodeType.LOCATION -> "LOC"
    }

    fun nextCode(type: NodeType, existingCodes: List<String>): String {
        val prefix = prefixFor(type) + "-"
        val max = existingCodes
            .filter { it.startsWith(prefix) }
            .mapNotNull { it.removePrefix(prefix).toIntOrNull() }
            .maxOrNull() ?: 0
        return prefix + (max + 1).toString().padStart(3, '0')
    }
}
