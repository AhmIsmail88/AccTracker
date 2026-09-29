package com.protrack.app

import com.protrack.app.data.db.LocationEntity
import com.protrack.app.data.db.ProjectEntity
import com.protrack.app.data.db.RegionEntity
import com.protrack.app.data.db.ZoneEntity
import com.protrack.app.domain.NodeType
import com.protrack.app.domain.TreeBuilder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TreeBuilderTest {

    private fun project(code: String, name: String) =
        ProjectEntity(code = code, name = name, createdAt = "t", updatedAt = "t")

    private fun region(code: String, parent: String, name: String) =
        RegionEntity(code = code, projectCode = parent, name = name, createdAt = "t", updatedAt = "t")

    private fun zone(code: String, parent: String, name: String) =
        ZoneEntity(code = code, regionCode = parent, name = name, createdAt = "t", updatedAt = "t")

    private fun location(code: String, parent: String, name: String) =
        LocationEntity(code = code, zoneCode = parent, name = name, createdAt = "t", updatedAt = "t")

    @Test
    fun buildsNestedTree() {
        val tree = TreeBuilder.build(
            projects = listOf(project("PRJ-001", "مشروع الرياض")),
            regions = listOf(region("RGN-001", "PRJ-001", "المنطقة الشرقية")),
            zones = listOf(zone("ZN-001", "RGN-001", "محطة الشمال")),
            locations = listOf(location("LOC-001", "ZN-001", "غرفة المضخات")),
        )
        assertEquals(1, tree.size)
        val projectNode = tree[0]
        assertEquals("PRJ-001", projectNode.code)
        val regionNode = projectNode.children[0]
        val zoneNode = regionNode.children[0]
        val locationNode = zoneNode.children[0]
        assertEquals(NodeType.LOCATION, locationNode.type)
        assertEquals("LOC-001", locationNode.code)
        assertEquals("غرفة المضخات", locationNode.name)
    }

    @Test
    fun flattenShowsRootsOnlyWhenCollapsed() {
        val tree = TreeBuilder.build(
            projects = listOf(project("PRJ-001", "P")),
            regions = listOf(region("RGN-001", "PRJ-001", "R")),
            zones = emptyList(),
            locations = emptyList(),
        )
        val collapsed = TreeBuilder.flatten(tree, emptySet())
        assertEquals(1, collapsed.size)
        assertTrue(collapsed[0].hasChildren)

        val expandedRows = TreeBuilder.flatten(tree, setOf("PRJ-001"))
        assertEquals(2, expandedRows.size)
        assertEquals(1, expandedRows[1].depth)
    }

    // ===================== الحالات المرنة (تخطي مستويات ناقصة) =====================

    @Test
    fun locationDirectlyUnderProjectSkipsMissingLevels() {
        val tree = TreeBuilder.build(
            projects = listOf(project("PRJ-001", "مشروع الخندق")),
            regions = emptyList(),
            zones = emptyList(),
            locations = listOf(location("LOC-001", "PRJ-001", "غرفة المضخات")),
        )
        assertEquals(1, tree.size)
        val locationNode = tree[0].children[0]
        assertEquals(NodeType.LOCATION, locationNode.type)
        assertEquals("LOC-001", locationNode.code)
        assertEquals("غرفة المضخات", locationNode.name)
    }

    @Test
    fun zoneDirectlyUnderProjectSkipsRegion() {
        val tree = TreeBuilder.build(
            projects = listOf(project("PRJ-001", "P")),
            regions = emptyList(),
            zones = listOf(zone("ZN-001", "PRJ-001", "زون مباشر")),
            locations = listOf(location("LOC-001", "ZN-001", "موقع")),
        )
        val zoneNode = tree[0].children[0]
        assertEquals(NodeType.ZONE, zoneNode.type)
        assertEquals("ZN-001", zoneNode.code)
        assertEquals(NodeType.LOCATION, zoneNode.children[0].type)
    }

    @Test
    fun mixedChildrenUnderSameParentAreAllAttached() {
        val tree = TreeBuilder.build(
            projects = listOf(project("PRJ-001", "P")),
            regions = listOf(region("RGN-001", "PRJ-001", "R")),
            zones = emptyList(),
            locations = listOf(
                location("LOC-001", "PRJ-001", "موقع مباشر"),
                location("LOC-002", "RGN-001", "موقع تحت المنطقة"),
            ),
        )
        val projectChildren = tree[0].children
        assertEquals(2, projectChildren.size)
        assertTrue(projectChildren.any { it.code == "LOC-001" })
        val regionNode = projectChildren.first { it.code == "RGN-001" }
        assertEquals(1, regionNode.children.size)
        assertEquals("LOC-002", regionNode.children[0].code)
    }

    @Test
    fun orphanNodesAreNotAttached() {
        val tree = TreeBuilder.build(
            projects = listOf(project("PRJ-001", "P")),
            regions = listOf(region("RGN-999", "PRJ-404", "يتيم")),
            zones = emptyList(),
            locations = emptyList(),
        )
        assertEquals(1, tree.size)
        assertTrue(tree[0].children.isEmpty())
    }
}
