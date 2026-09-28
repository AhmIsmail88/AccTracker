package com.protrack.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.protrack.app.ui.HomeScreen
import com.protrack.app.ui.locations.LocationsScreen
import com.protrack.app.ui.theme.ProTrackTheme
import com.protrack.app.ui.visit.VisitScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as ProTrackApp).container
        setContent {
            ProTrackTheme {
                AppNav(container = container)
            }
        }
    }
}

@Composable
fun AppNav(container: AppContainer) {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "home") {
        composable("home") {
            HomeScreen(
                onManageLocations = { navController.navigate("locations") },
                onNewVisit = { navController.navigate("visit") },
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
                exporter = container.exporter,
                onBack = { navController.popBackStack() },
            )
        }
    }
}
