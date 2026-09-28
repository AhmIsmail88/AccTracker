package com.protrack.app.data

import android.content.Context
import java.util.Base64
import com.protrack.app.data.db.VisitPhotoEntity
import com.protrack.app.domain.export.PackageBuilder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

/**
 * إدارة صور الزيارة: مسار الحفظ داخل مجلد التطبيق، والبصمة (SHA-256)،
 * وتوقيع الالتقاط (capture_sig) بمفتاح الجهاز.
 */
class PhotoManager(
    private val context: Context,
    private val visitRepository: VisitRepository,
    private val deviceInfo: DeviceInfoProvider,
    private val locationProvider: LocationProvider,
) {

    /** ملف وجهة جديد للكاميرا (تُكتب الصورة فيه مباشرة من الكاميرا). */
    fun newPhotoFile(visitRefId: Long): File {
        val dir = File(context.getExternalFilesDir(null), "photos/visit_$visitRefId").apply { mkdirs() }
        val stamp = OffsetDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))
        return File(dir, "IMG_$stamp.jpg")
    }

    /** بعد الالتقاط: يحسب البصمة + التوقيع + الموقع ويسجّل الصف. */
    suspend fun attachPhoto(
        visitRefId: Long,
        targetType: String,
        targetRef: String,
        file: File,
    ): Boolean = withContext(Dispatchers.IO) {
        try {
            val bytes = file.readBytes()
            val sha = PackageBuilder.sha256Hex(bytes)
            val sig = Base64.getEncoder().encodeToString(deviceInfo.signer.sign(bytes))
            val fix = locationProvider.lastKnown()
            visitRepository.addPhoto(
                VisitPhotoEntity(
                    visitRefId = visitRefId,
                    targetType = targetType,
                    targetRef = targetRef,
                    filePath = file.absolutePath,
                    takenAt = OffsetDateTime.now().toString(),
                    lat = fix?.lat,
                    lon = fix?.lon,
                    accuracyM = fix?.accuracyM,
                    sha256 = sha,
                    captureSig = sig,
                ),
            )
            true
        } catch (e: Exception) {
            false
        }
    }
}
