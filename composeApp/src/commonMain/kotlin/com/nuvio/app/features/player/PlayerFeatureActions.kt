package com.nuvio.app.features.player

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.NightsStay
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.nuvio.app.features.home.MetaPreview
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.stringResource

/** Shared by modern and legacy layouts; these actions must not depend on toolbar presets. */
@Composable
internal fun PlayerFeatureActions(
    nightModeVisible: Boolean,
    nightModeEnabled: Boolean,
    nightModeSupported: Boolean,
    glassEnabled: Boolean,
    onNightModeToggle: () -> Unit,
    recommendationsVisible: Boolean,
    onRecommendations: () -> Unit,
) {
    Box(Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.align(Alignment.CenterEnd).padding(end = 24.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (nightModeVisible) {
                FilledTonalIconButton(
                    onClick = onNightModeToggle,
                    enabled = nightModeSupported,
                    colors = IconButtonDefaults.filledTonalIconButtonColors(
                        containerColor = if (glassEnabled) Color.Black.copy(alpha = 0.6f) else Color.Transparent,
                        contentColor = if (nightModeEnabled) MaterialTheme.colorScheme.primary else Color.White,
                    ),
                ) {
                    Icon(Icons.Rounded.NightsStay, stringResource(
                        if (nightModeSupported) {
                            if (nightModeEnabled) Res.string.v121_night_mode_on else Res.string.v121_night_mode_off
                        } else Res.string.v121_night_mode_unsupported,
                    ))
                }
            }
            if (recommendationsVisible) {
                FilledTonalIconButton(onClick = onRecommendations,
                    colors = IconButtonDefaults.filledTonalIconButtonColors(
                        containerColor = if (glassEnabled) Color.Black.copy(alpha = 0.6f) else Color.Transparent,
                        contentColor = Color.White,
                    ),
                ) {
                    Icon(Icons.Rounded.AutoAwesome, stringResource(Res.string.v121_recommendations))
                }
            }
        }
    }
}

@Composable
internal fun PlayerRecommendationsDialog(
    visible: Boolean,
    items: List<MetaPreview>,
    onOpen: (MetaPreview) -> Unit,
    onDismiss: () -> Unit,
) {
    if (!visible) return
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(Res.string.v121_recommendations)) },
        text = {
            if (items.isEmpty()) {
                Text(stringResource(Res.string.v121_recommendations_empty))
            } else {
                LazyColumn(Modifier.heightIn(max = 280.dp)) {
                    items(items, key = { "${it.type}:${it.id}" }) { item ->
                        ListItem(
                            headlineContent = { Text(item.name) },
                            supportingContent = { Text(item.releaseInfo.orEmpty()) },
                            modifier = Modifier.clickable { onOpen(item) },
                        )
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text(stringResource(Res.string.action_close)) } },
    )
}
