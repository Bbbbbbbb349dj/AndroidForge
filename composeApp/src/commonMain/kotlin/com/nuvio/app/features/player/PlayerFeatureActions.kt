package com.nuvio.app.features.player

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Movie
import androidx.compose.material.icons.rounded.NightsStay
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.nuvio.app.features.home.MetaPreview
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.stringResource

/** Part of the measured bottom controls, never a full-screen overlay or side rail. */
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
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        if (nightModeVisible) {
            TextButton(
                onClick = onNightModeToggle, enabled = nightModeSupported,
                modifier = Modifier.playerLiquidGlass(RoundedCornerShape(10.dp)).height(40.dp),
                contentPadding = PaddingValues(horizontal = 10.dp),
            ) {
                val tint = if (!nightModeSupported) playerControlForeground.copy(alpha = 0.4f)
                    else if (nightModeEnabled) MaterialTheme.colorScheme.primary else playerControlForeground
                Icon(Icons.Rounded.NightsStay, if (nightModeSupported) "Night mode" else "Night mode unavailable", Modifier.size(18.dp), tint = tint)
                Spacer(Modifier.width(6.dp))
                Text("Night", color = tint, style = MaterialTheme.typography.labelMedium)
            }
        }
        if (recommendationsVisible) PlayerActionPillButton(
            label = "Discover", icon = Icons.Rounded.AutoAwesome, onClick = onRecommendations,
        )
    }
}

/** Always a bottom sheet on phones AND landscape; no adaptive side-panel substitution. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun PlayerRecommendationsDialog(
    visible: Boolean,
    items: List<MetaPreview>,
    onOpen: (MetaPreview) -> Unit,
    onDismiss: () -> Unit,
) {
    if (!visible) return
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        sheetMaxWidth = 760.dp,
        containerColor = MaterialTheme.colorScheme.surface,
        contentColor = MaterialTheme.colorScheme.onSurface,
    ) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(stringResource(Res.string.v121_recommendations), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text("Find your next watch", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = onDismiss) { Icon(Icons.Rounded.Close, stringResource(Res.string.action_close)) }
        }
        LazyColumn(
            modifier = Modifier.fillMaxWidth().weight(1f, fill = false),
            contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (items.isEmpty()) item {
                Text(stringResource(Res.string.v121_recommendations_empty), Modifier.padding(16.dp))
            }
            items(items, key = { "${it.type}:${it.id}" }) { preview ->
                Surface(
                    modifier = Modifier.fillMaxWidth().clickable { onOpen(preview) },
                    shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceContainer,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                ) {
                    Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        Box(Modifier.width(84.dp).height(126.dp).clip(RoundedCornerShape(10.dp))
                            .background(MaterialTheme.colorScheme.surfaceContainerHigh), contentAlignment = Alignment.Center) {
                            Icon(Icons.Rounded.Movie, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            AsyncImage(preview.poster ?: preview.rawPosterUrl, preview.name,
                                modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                        }
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(preview.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                            Text(listOfNotNull(preview.releaseInfo?.takeIf { it.isNotBlank() }, preview.imdbRating?.let { "★ $it" }, preview.runtime)
                                .joinToString(" · "), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                            if (preview.genres.isNotEmpty()) Text(preview.genres.take(3).joinToString(" · "),
                                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(preview.description?.takeIf { it.isNotBlank() } ?: "No synopsis available from this provider.",
                                style = MaterialTheme.typography.bodySmall, maxLines = 3, overflow = TextOverflow.Ellipsis,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("View details →", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
        }
    }
}

/** A dismissible end-of-movie prompt; the full collection only opens by deliberate interaction. */
@Composable
internal fun PlayerRecommendationsPrompt(onBrowse: () -> Unit, onDismiss: () -> Unit, modifier: Modifier = Modifier) {
    Surface(modifier.widthIn(max = 560.dp).fillMaxWidth(), shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface, border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("What to watch next", Modifier.weight(1f), style = MaterialTheme.typography.titleSmall)
            TextButton(onClick = onBrowse) { Text("Browse movies") }
            IconButton(onClick = onDismiss) { Icon(Icons.Rounded.Close, "Dismiss recommendations") }
        }
    }
}
