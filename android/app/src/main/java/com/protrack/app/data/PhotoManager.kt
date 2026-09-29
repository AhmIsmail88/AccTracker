package com.protrack.app.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Typeface
import com.protrack.app.data.db.VisitPhotoEntity
import com.protrack.app.domain.export.PackageBuilder
import java.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * إدارة صور الزيارة: مسار الحفظ داخل مجلد التطبيق، والبصمة (SHA-256)،
 * وتوقيع الالتقاط (capture_sig) بمفتاح الجهاز، مع ختم التاريخ والموقع على الصورة نفسها.
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

    /** بعد الالتقاط: ختم التاريخ/الموقع على الصورة + البصمة + التوقيع + الموقع ويسجّل الصف. */
    suspend fun attachPhoto(
        visitRefId: Long,
        targetType: String,
        targetRef: String,
        file: File,
    ): Boolean = withContext(Dispatchers.IO) {
        try {
            val fix = locationProvider.lastKnown()
            val takenAt = OffsetDateTime.now()
            stampPhoto(file, takenAt, fix?.lat, fix?.lon)
            val bytes = file.readBytes()
            val sha = PackageBuilder.sha256Hex(bytes)
            val sig = Base64.getEncoder().encodeToString(deviceInfo.signer.sign(bytes))
            visitRepository.addPhoto(
                VisitPhotoEntity(
                    visitRefId = visitRefId,
                    targetType = targetType,
                    targetRef = targetRef,
                    filePath = file.absolutePath,
                    takenAt = takenAt.toString(),
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

    /**
     * يرسم شريطًا سفليًا على الصورة يحمل التاريخ/الوقت والإحداثيات (قبل حساب البصمة).
     * يصحّح اتجاه EXIF أولًا حتى يظهر الختم في المكان الصحيح دائمًا.
     */
    private fun stampPhoto(file: File, time: OffsetDateTime, lat: Double?, lon: Double?) {
        var decoded: Bitmap? = null
        var target: Bitmap? = null
        try {
            val path = file.absolutePath
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(path, bounds)
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return
            var sample = 1
            while (bounds.outWidth / sample > 2560 || bounds.outHeight / sample > 2560) {
                sample *= 2
            }
            decoded = BitmapFactory.decodeFile(
                path,
                BitmapFactory.Options().apply { inSampleSize = sample },
            ) ?: return

            val orientation = try {
                android.media.ExifInterface(path).getAttributeInt(
                    android.media.ExifInterface.TAG_ORIENTATION,
                    1,
                )
            } catch (e: Exception) {
                1
            }
            val matrix = Matrix()
            when (orientation) {
                3 -> matrix.postRotate(180f)
                6 -> matrix.postRotate(90f)
                8 -> matrix.postRotate(270f)
            }
            val base = if (!matrix.isIdentity) {
                Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
            } else {
                decoded
            }
            target = if (base.isMutable) base else base.copy(Bitmap.Config.ARGB_8888, true) ?: base

            val canvas = Canvas(target)
            val w = target.width.toFloat()
            val h = target.height.toFloat()
            val text1 = time.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
            val text2 = if (lat != null && lon != null) {
                String.format(Locale.US, "GPS %.5f, %.5f", lat, lon)
            } else {
                "GPS N/A"
            }
            val textSize = (w / 42f).coerceAtLeast(22f)
            val paint = Paint().apply {
                isAntiAlias = true
                color = Color.WHITE
                this.textSize = textSize
                typeface = Typeface.DEFAULT_BOLD
                setShadowLayer(4f, 0f, 2f, Color.BLACK)
            }
            val pad = textSize * 0.6f
            val lineHeight = textSize * 1.35f
            val boxTop = h - (lineHeight * 2 + pad * 2)
            val background = Paint().apply { color = Color.argb(120, 0, 0, 0) }
            canvas.drawRect(0f, boxTop, w, h, background)
            canvas.drawText(text1, pad, boxTop + pad + textSize, paint)
            canvas.drawText(text2, pad, boxTop + pad + textSize + lineHeight, paint)

            file.outputStream().use { out ->
                target.compress(Bitmap.CompressFormat.JPEG, 92, out)
            }
        } catch (e: Exception) {
            // فشل الختم لا يمنع حفظ الصورة الأصلية
        } finally {
            try {
                target?.recycle()
            } catch (e: Exception) {
            }
            try {
                decoded?.recycle()
            } catch (e: Exception) {
            }
        }
    }
}
