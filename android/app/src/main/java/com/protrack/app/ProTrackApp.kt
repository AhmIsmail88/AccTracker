package com.protrack.app

import android.app.Application
import android.content.Context
import androidx.room.Room
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.data.db.AppDatabase

class ProTrackApp : Application() {
    val container: AppContainer by lazy { AppContainer(this) }
}

class AppContainer(context: Context) {
    private val database: AppDatabase = Room.databaseBuilder(
        context.applicationContext,
        AppDatabase::class.java,
        "protrack.db",
    ).build()

    val repository: HierarchyRepository = HierarchyRepository(database.hierarchyDao())
}
