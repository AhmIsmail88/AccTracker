package com.protrack.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.protrack.app.data.HierarchyRepository
import com.protrack.app.ui.HomeScreen
import com.protrack.app.ui.locations.LocationsScreen
import com.protrack.app.ui.theme.ProTrackTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val repository = (application as ProTrackApp).container.repository
        setContent {
            ProTrackTheme {
                AppNav(repository = repository)
            }
        }
    }
}

@Composable
fun AppNav(repository: HierarchyRepository) {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "home") {
        composable("home") {
            HomeScreen(onManageLocations = { navController.navigate("locations") })
        }
        composable("locations") {
            LocationsScreen(
                repository = repository,
                onBack = { navController.popBackStack() },
            )
        }
    }
}
