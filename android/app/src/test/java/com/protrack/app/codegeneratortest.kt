package com.protrack.app

import com.protrack.app.domain.CodeGenerator
import com.protrack.app.domain.NodeType
import org.junit.Assert.assertEquals
import org.junit.Test

class CodeGeneratorTest {

    @Test
    fun firstProjectCode() {
        assertEquals("PRJ-001", CodeGenerator.nextCode(NodeType.PROJECT, emptyList()))
    }

    @Test
    fun incrementsWithinPrefix() {
        assertEquals("ZN-003", CodeGenerator.nextCode(NodeType.ZONE, listOf("ZN-001", "ZN-002")))
    }

    @Test
    fun ignoresGarbageAndOtherPrefixes() {
        assertEquals(
            "LOC-002",
            CodeGenerator.nextCode(NodeType.LOCATION, listOf("LOC-001", "PRJ-009", "LOC-abc")),
        )
    }

    @Test
    fun crossesIntoNewHundreds() {
        assertEquals("LOC-100", CodeGenerator.nextCode(NodeType.LOCATION, listOf("LOC-099")))
    }
}
