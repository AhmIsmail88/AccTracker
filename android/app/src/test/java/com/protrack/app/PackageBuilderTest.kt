package com.protrack.app

import com.protrack.app.domain.export.ExportChecklist
import com.protrack.app.domain.export.ExportEquipment
import com.protrack.app.domain.export.ExportLocation
import com.protrack.app.domain.export.ExportMeta
import com.protrack.app.domain.export.ExportPhoto
import com.protrack.app.domain.export.ExportVisit
import com.protrack.app.domain.export.JcaPackageSigner
import com.protrack.app.domain.export.PackageBuilder
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.security.KeyPairGenerator
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.Base64
import java.util.zip.ZipFile

/**
 * يبني حزمة زيارة كاملة (بنفس مسار التصدير في التطبيق) ويكتبها كـ artifact
 * ليتم التحقق منها خارجيًا بنفس validator المشروع (tools/validate_package.py).
 */
class PackageBuilderTest {

    @Test
    fun buildsPackageArtifact() {
        val kpg = KeyPairGenerator.getInstance("EC")
        kpg.initialize(ECGenParameterSpec("secp256r1"))
        val keyPair = kpg.generateKeyPair()
        val signer = JcaPackageSigner(keyPair)
        val builder = PackageBuilder(signer)

        val photo = ExportPhoto(
            fileName = "IMG_001.jpg",
            bytes = fakeJpeg(),
            takenAt = "2026-09-28T10:15:00+03:00",
            lat = 24.7136,
            lon = 46.6753,
            accuracyM = 8.0,
        )

        val bytes = builder.build(
            meta = ExportMeta(
                packageId = "11111111-2222-4333-8444-555555555555",
                createdAt = "2026-09-28T10:52:00+03:00",
                deviceId = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                publicKeyB64 = signer.publicKeyBase64(),
                fingerprint = "61DF275D",
            ),
            visit = ExportVisit(
                visitId = "VISIT-20260928-105000",
                locationCode = "LOC-001",
                visitType = "ROUTINE",
                startedAt = "2026-09-28T09:40:00+03:00",
                endedAt = "2026-09-28T10:45:00+03:00",
                notes = "تجربة تصدير",
                status = "EXPORTED",
            ),
            equipment = listOf(
                ExportEquipment("MAIN_PUMP", "01", "ABC-500", 2340.0, 5.8, "RUNNING", ""),
                ExportEquipment("MAIN_PUMP", "02", "ABC-500", 2410.0, 5.7, "RUNNING", ""),
            ),
            checklist = (1..12).map { i ->
                ExportChecklist(
                    "CHK-" + i.toString().padStart(2, '0'),
                    if (i == 2) "MINOR" else "OK",
                    "",
                )
            },
            locations = listOf(
                ExportLocation("PRJ-001", "PROJECT", null, "مشروع الرياض", "ACTIVE", "2026-09-20T08:00:00+03:00"),
                ExportLocation("RGN-001", "REGION", "PRJ-001", "المنطقة الشرقية", "ACTIVE", "2026-09-20T08:01:00+03:00"),
                ExportLocation("ZN-001", "ZONE", "RGN-001", "محطة الشمال", "ACTIVE", "2026-09-20T08:02:00+03:00"),
                ExportLocation("LOC-001", "LOCATION", "ZN-001", "غرفة المضخات الرئيسية", "ACTIVE", "2026-09-20T08:03:00+03:00"),
            ),
            photos = listOf(photo),
        )

        assertTrue(bytes.isNotEmpty())

        val outDir = File("build/test-artifacts").apply { mkdirs() }
        val artifact = File(outDir, "export-test-package.zip")
        artifact.writeBytes(bytes)

        ZipFile(artifact).use { zf ->
            val names = zf.entries().toList().map { it.name }
            assertTrue(names.contains("visit.xlsx"))
            assertTrue(names.contains("manifest.json"))
            assertTrue(names.contains("manifest.sig"))
            assertTrue(names.contains("photos/IMG_001.jpg"))

            val manifestBytes = zf.getInputStream(zf.getEntry("manifest.json")).readBytes()
            val manifestText = String(manifestBytes, Charsets.UTF_8)
            assertTrue(manifestText.contains("\"package_id\""))
            assertTrue(manifestText.contains("photos/IMG_001.jpg"))
            assertTrue(manifestText.contains("\"capture_sig\""))

            val sigB64 = String(
                zf.getInputStream(zf.getEntry("manifest.sig")).readBytes(),
                Charsets.US_ASCII,
            )
            val verified = Signature.getInstance("SHA256withECDSA").run {
                initVerify(keyPair.public)
                update(manifestBytes)
                verify(Base64.getDecoder().decode(sigB64))
            }
            assertTrue(verified)
        }

        println("TEST-ARTIFACT: " + artifact.absolutePath)
    }

    private fun fakeJpeg(): ByteArray =
        byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xE0.toByte()) +
            "ProTrack sample photo".toByteArray(Charsets.UTF_8) +
            byteArrayOf(0xFF.toByte(), 0xD9.toByte())
}
