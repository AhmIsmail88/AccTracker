package com.protrack.app

import com.protrack.app.domain.export.ExportNames
import org.junit.Assert.assertEquals
import org.junit.Test

class ExportNamesTest {

    @Test
    fun standardName() {
        assertEquals(
            "Visit_LOC-001_20260928-150506_Ahmed.zip",
            ExportNames.visitFileName("LOC-001", "20260928-150506", "Ahmed"),
        )
    }

    @Test
    fun sanitizesUnsafeCharacters() {
        assertEquals(
            "Visit_LOC-001_20260928-150506_Ahmed_Ali.zip",
            ExportNames.visitFileName("LOC-001", "20260928-150506", "  Ahmed  Ali! "),
        )
    }

    @Test
    fun emptyTechnicianOmitsSuffix() {
        assertEquals(
            "Visit_LOC-001_20260928-150506.zip",
            ExportNames.visitFileName("LOC-001", "20260928-150506", "   "),
        )
    }

    @Test
    fun arabicNameIsKept() {
        assertEquals(
            "Visit_LOC-001_20260928-150506_أحمد.zip",
            ExportNames.visitFileName("LOC-001", "20260928-150506", "أحمد"),
        )
    }
}
