package com.protrack.app

import android.app.Application
import android.content.Context
import androidx.room.Room
import com.protrack.app.data.DeviceInfoProvider
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.data.PackageExporter
import com.protrack.app.data.VisitRepository
import com.protrack.app.data.db.AppDatabase

class ProTrackApp : Application() {
    val container: AppContainer by lazy { AppContainer(this) }
}

class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    // ملاحظة: قبل الإطلاق الرسمي تُستبدل بـ migrations حقيقية بدل الحذف عند تغيير الإصدار.
    private val database: AppDatabase = Room.databaseBuilder(
        appContext,
        AppDatabase::class.java,
        "protrack.db",
    ).fallbackToDestructiveMigration().build()

    val repository: HierarchyRepository = HierarchyRepository(database.hierarchyDao())
    val visitRepository: VisitRepository = VisitRepository(database.visitDao())

    private val deviceInfo = DeviceInfoProvider(appContext)
    val exporter: PackageExporter = PackageExporter(appContext, visitRepository, repository, deviceInfo)
}
