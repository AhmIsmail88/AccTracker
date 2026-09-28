package com.protrack.app

import android.app.Application
import android.content.Context
import androidx.room.Room
import com.protrack.app.data.AppSettings
import com.protrack.app.data.DeviceInfoProvider
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.data.LocationProvider
import com.protrack.app.data.PackageExporter
import com.protrack.app.data.PhotoManager
import com.protrack.app.data.VisitRepository
import com.protrack.app.data.db.AppDatabase

class ProTrackApp : Application() {
    val container: AppContainer by lazy { AppContainer(this) }
}

class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    // ملاحظة: fallbackToDestructiveMigration شبكة أمان فقط — الترحيلات الحقيقية مُضافة.
    private val database: AppDatabase = Room.databaseBuilder(
        appContext,
        AppDatabase::class.java,
        "protrack.db",
    ).addMigrations(AppDatabase.MIGRATION_2_3, AppDatabase.MIGRATION_3_4)
        .fallbackToDestructiveMigration()
        .build()

    val settings = AppSettings(appContext)

    val repository: HierarchyRepository = HierarchyRepository(database.hierarchyDao(), database.visitDao())
    val visitRepository: VisitRepository = VisitRepository(database.visitDao())

    private val deviceInfo = DeviceInfoProvider(appContext)
    private val locationProvider = LocationProvider(appContext)

    val photoManager = PhotoManager(appContext, visitRepository, deviceInfo, locationProvider)
    val exporter: PackageExporter =
        PackageExporter(appContext, visitRepository, repository, deviceInfo, settings)
}
