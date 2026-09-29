package com.protrack.app

import android.content.Context
import android.content.res.Configuration
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.protrack.app.ui.HomeScreen
import com.protrack.app.ui.locations.LocationsScreen
import com.protrack.app.ui.onboarding.OnboardingScreen
import com.protrack.app.ui.settings.SettingsScreen
import com.protrack.app.ui.theme.ProTrackTheme
import com.protrack.app.ui.visit.VisitScreen
import com.protrack.app.ui.visit.VisitsHistoryScreen
import java.util.Locale

class MainActivity : ComponentActivity() {

    /** تطبيق لغة التطبيق المختارة (من أول تشغيل) — تعمل على كل إصدارات أندرويد المدعومة. */
    override fun attachBaseContext(newBase: Context) {
        val language = newBase.getSharedPreferences("protrack_device", Context.MODE_PRIVATE)
            .getString("language", null)
        if (language.isNullOrBlank()) {
            super.attachBaseContext(newBase)
            return
        }
        val locale = Locale(language)
        Locale.setDefault(locale)
        val config = Configuration(newBase.resources.configuration)
        config.setLocale(locale)
        super.attachBaseContext(newBase.createConfigurationContext(config))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as ProTrackApp).container
        val startOnboarding = !container.settings.isOnboarded()
        setContent {
            ProTrackTheme {
                AppNav(container = container, startOnboarding = startOnboarding)
            }
        }
    }
}

@Composable
fun AppNav(container: AppContainer, startOnboarding: Boolean) {
    val navController = rememberNavController()
    NavHost(
        navController = navController,
        startDestination = if (startOnboarding) "onboarding" else "home",
    ) {
        composable("onboarding") {
            OnboardingScreen(settings = container.settings) {
                navController.navigate("home") {
                    popUpTo("onboarding") { inclusive = true }
                }
            }
        }
        composable("home") {
            HomeScreen(
                technicianName = container.settings.technicianName,
                onManageLocations = { navController.navigate("locations") },
                onNewVisit = { navController.navigate("visit") },
                onVisitHistory = { navController.navigate("visits") },
                onOpenSettings = { navController.navigate("settings") },
            )
        }
        composable("settings") {
            SettingsScreen(
                settings = container.settings,
                onBack = { navController.popBackStack() },
            )
        }
        composable(
            "locations?addUnder={addUnder}",
            arguments = listOf(navArgument("addUnder") { type = NavType.StringType; defaultValue = "" }),
        ) { entry ->
            LocationsScreen(
                repository = container.repository,
                onBack = { navController.popBackStack() },
                autoAddUnder = entry.arguments?.getString("addUnder")?.takeIf { it.isNotBlank() },
            )
        }
        composable("visit") {
            VisitScreen(
                hierarchyRepository = container.repository,
                visitRepository = container.visitRepository,
                photoManager = container.photoManager,
                exporter = container.exporter,
                onBack = { navController.popBackStack() },
                onAddLocation = { under ->
                    navController.navigate(
                        if (under.isNullOrBlank()) "locations" else "locations?addUnder=$under",
                    )
                },
            )
        }
        composable("visits") {
            VisitsHistoryScreen(
                visitRepository = container.visitRepository,
                hierarchyRepository = container.repository,
                onOpenVisit = { visitId -> navController.navigate("visitResume/$visitId") },
                onBack = { navController.popBackStack() },
            )
        }
        composable(
            "visitResume/{visitId}",
            arguments = listOf(navArgument("visitId") { type = NavType.LongType }),
        ) { entry ->
            VisitScreen(
                hierarchyRepository = container.repository,
                visitRepository = container.visitRepository,
                photoManager = container.photoManager,
                exporter = container.exporter,
                onBack = { navController.popBackStack() },
                resumeVisitId = entry.arguments?.getLong("visitId"),
                onAddLocation = { under ->
                    navController.navigate(
                        if (under.isNullOrBlank()) "locations" else "locations?addUnder=$under",
                    )
                },
            )
        }
    }
}
