package com.protrack.app.data.db

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        ProjectEntity::class, RegionEntity::class, ZoneEntity::class, LocationEntity::class,
        VisitEntity::class, VisitEquipmentEntity::class, VisitChecklistEntity::class,
        VisitPhotoEntity::class,
    ],
    version = 3,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun hierarchyDao(): HierarchyDao
    abstract fun visitDao(): VisitDao

    companion object {
        /** v2 → v3: إضافة جدول صور الزيارة. */
        val MIGRATION_2_3: Migration = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `visit_photo` (" +
                        "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                        "`visitRefId` INTEGER NOT NULL, " +
                        "`targetType` TEXT NOT NULL, " +
                        "`targetRef` TEXT NOT NULL, " +
                        "`filePath` TEXT NOT NULL, " +
                        "`takenAt` TEXT NOT NULL, " +
                        "`lat` REAL, `lon` REAL, `accuracyM` REAL, " +
                        "`sha256` TEXT NOT NULL, `captureSig` TEXT NOT NULL)",
                )
            }
        }
    }
}
