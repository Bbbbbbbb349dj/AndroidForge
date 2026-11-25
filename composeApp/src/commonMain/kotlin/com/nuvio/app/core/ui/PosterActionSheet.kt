package com.nuvio.app.core.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.Dp

// Watched/unwatched UI was removed app-wide (the user tracks watched state through their own
// library categories: Watched / Plan to Watch / Completed). These badge composables remain as
// no-ops so existing call sites compile and render nothing.

@Composable
fun NuvioWatchedBadge(
    modifier: Modifier = Modifier,
) {
    // No-op: watched badges removed.
}

@Composable
fun NuvioAnimatedWatchedBadge(
    isVisible: Boolean,
    modifier: Modifier = Modifier,
) {
    // No-op: watched badges removed.
}

@Composable
fun androidx.compose.foundation.layout.BoxScope.NuvioPosterWatchedOverlay(
    isWatched: Boolean,
    modifier: Modifier = Modifier,
    padding: Dp = NuvioTokens.Space.s6,
) {
    // No-op: watched badges removed.
}
