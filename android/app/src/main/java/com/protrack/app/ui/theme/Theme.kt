package com.protrack.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * ثيم AccTracker — هوية Advanced Construction Co. ثابتة: فاتح دائمًا
 * (أحمر #D2262C وأبيض) لتوحيد الشكل مهما كان وضع النظام (فاتح/داكن).
 */
private val LightColors = lightColorScheme(
    primary = Color(0xFFD2262C),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFFBDADD),
    onPrimaryContainer = Color(0xFF3F0206),
    secondary = Color(0xFF5F5E62),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFE5E1E5),
    onSecondaryContainer = Color(0xFF1B1B1F),
    background = Color(0xFFFAF9FB),
    onBackground = Color(0xFF1B1B1F),
    surface = Color(0xFFFAF9FB),
    onSurface = Color(0xFF1B1B1F),
    surfaceVariant = Color(0xFFE5E1E5),
    onSurfaceVariant = Color(0xFF47464A),
    outline = Color(0xFF78767B),
    error = Color(0xFFB3261E),
    onError = Color(0xFFFFFFFF),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFFFB3B4),
    onPrimary = Color(0xFF67000A),
    primaryContainer = Color(0xFF941019),
    onPrimaryContainer = Color(0xFFFFDADA),
    secondary = Color(0xFFC9C5CA),
    onSecondary = Color(0xFF303034),
    background = Color(0xFF141315),
    onBackground = Color(0xFFE5E1E4),
    surface = Color(0xFF141315),
    onSurface = Color(0xFFE5E1E4),
    surfaceVariant = Color(0xFF47464A),
    onSurfaceVariant = Color(0xFFC9C5CA),
    outline = Color(0xFF938F94),
)

@Composable
fun ProTrackTheme(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit,
) {
    // الهوية فاتحة دائمًا — نتجاهل الوضع الليلي لضمان شكل الشركة الموحد
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
