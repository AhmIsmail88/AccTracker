package com.protrack.app.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        ProjectEntity::class, RegionEntity::class, ZoneEntity::class, LocationEntity::class,
        VisitEntity::class, VisitEquipmentEntity::class, VisitChecklistEntity::class,
    ],
    version = 2,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun hierarchyDao(): HierarchyDao
    abstract fun visitDao(): VisitDao
}
