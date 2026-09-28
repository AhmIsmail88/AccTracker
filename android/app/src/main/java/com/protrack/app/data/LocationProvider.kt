package com.protrack.app.data

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * مزوّد الموقع (FusedLocationProvider) — يجيب آخر موقع معروف بدون أي انتظار طويل.
 * لو مفيش إذن أو مفيش fix متاح، يرجّع null (وتُصدَّر الصورة بـ0,0).
 */
class LocationProvider(private val context: Context) {

    data class Fix(val lat: Double, val lon: Double, val accuracyM: Double)

    private val client by lazy {
        try {
            LocationServices.getFusedLocationProviderClient(context)
        } catch (e: Exception) {
            null
        }
    }

    fun hasPermission(): Boolean {
        val fine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    suspend fun lastKnown(): Fix? = withContext(Dispatchers.IO) {
        val c = client ?: return@withContext null
        if (!hasPermission()) return@withContext null
        try {
            val location = com.google.android.gms.tasks.Tasks.await(c.lastLocation)
            location?.let { Fix(it.latitude, it.longitude, it.accuracy.toDouble()) }
        } catch (e: Exception) {
            null
        }
    }
}
