package com.protrack.app

import android.content.Context
import android.content.res.Configuration
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.protrack.app.ui.HomeScreen
import com.protrack.app.ui.locations.LocationsScreen
import com.protrack.app.ui.onboarding.OnboardingScreen
import com.protrack.app.ui.settings.SettingsScreen
import com.protrack.app.ui.theme.ProTrackTheme
import com.protrack.app.ui.visit.VisitScreen
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
                onOpenSettings = { navController.navigate("settings") },
            )
        }
        composable("settings") {
            SettingsScreen(
                settings = container.settings,
                onBack = { navController.popBackStack() },
            )
        }
        composable("locations") {
            LocationsScreen(
                repository = container.repository,
                onBack = { navController.popBackStack() },
            )
        }
        composable("visit") {
            VisitScreen(
                hierarchyRepository = container.repository,
                visitRepository = container.visitRepository,
                photoManager = container.photoManager,
                exporter = container.exporter,
                onBack = { navController.popBackStack() },
            )
        }
    }
}
