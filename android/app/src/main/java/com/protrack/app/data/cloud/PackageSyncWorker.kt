package com.protrack.app.data.cloud

import android.content.Context
import android.net.Uri
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.storage.FirebaseStorage
import com.protrack.app.ProTrackApp
import java.io.File
import java.time.OffsetDateTime
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.tasks.await

/**
 * مزامنة الحزم المصدَّرة إلى السحابة (Firebase) — تعمل تلقائيًا عند توفر الشبكة:
 * ترفع ملف الحزمة إلى Storage + تسجّل بياناتها في Firestore، ثم تعلّم الزيارة كمُزامَنة.
 * الفني يعمل أوفلاين بالكامل؛ الرفع لا يحدث إلا عند وجود إنترنت.
 */
class PackageSyncWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val container = (applicationContext as? ProTrackApp)?.container ?: return Result.failure()

        // دخول مجهول (لأجهزة الفنيين بدون حسابات) لتأمين الرفع بقواعد الأمان
        val auth = FirebaseAuth.getInstance()
        if (auth.currentUser == null) {
            try {
                auth.signInAnonymously().await()
            } catch (e: Exception) {
                return Result.retry()
            }
        }

        val pending = container.visitRepository.pendingCloudUploads()
        if (pending.isEmpty()) return Result.success()

        val deviceId = container.deviceInfo.deviceId()
        val packagesDir = File(applicationContext.getExternalFilesDir(null), "packages")
        var hadFailure = false

        for (visit in pending) {
            val name = visit.packageName ?: continue
            val file = File(packagesDir, name)
            if (!file.exists()) {
                // الملف غير موجود — نعلّمه كمُزامَن لتجنّب إعادة المحاولة الأبدية
                container.visitRepository.markCloudUploaded(visit.id)
                continue
            }
            try {
                FirebaseStorage.getInstance()
                    .reference.child("packages/$deviceId/$name")
                    .putFile(Uri.fromFile(file))
                    .await()
                FirebaseFirestore.getInstance()
                    .collection("packages")
                    .document(name)
                    .set(
                        mapOf(
                            "fileName" to name,
                            "deviceId" to deviceId,
                            "locationCode" to visit.locationCode,
                            "visitId" to visit.visitId,
                            "exportedAt" to (visit.exportedAt ?: ""),
                            "uploadedAt" to OffsetDateTime.now().toString(),
                            "sizeBytes" to file.length(),
                        ),
                    )
                    .await()
                container.visitRepository.markCloudUploaded(visit.id)
            } catch (e: Exception) {
                hadFailure = true
            }
        }
        return if (hadFailure) Result.retry() else Result.success()
    }

    companion object {
        private const val UNIQUE_NAME = "package_sync"

        /** يجدول مزامنة الحزم المعلقة — آمن للنداء أكثر من مرة. */
        fun enqueue(context: Context) {
            val request = OneTimeWorkRequestBuilder<PackageSyncWorker>()
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build(),
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork(UNIQUE_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
        }
    }
}
