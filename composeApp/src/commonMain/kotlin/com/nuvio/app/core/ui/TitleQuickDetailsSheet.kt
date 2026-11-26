package com.nuvio.app.core.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.OpenInNew
import androidx.compose.material.icons.rounded.BookmarkAdd
import androidx.compose.material.icons.rounded.BookmarkAdded
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.DeleteOutline
import androidx.compose.material.icons.rounded.Visibility
import androidx.compose.material.icons.rounded.VisibilityOff
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.nuvio.app.core.format.extractReleaseYearForDisplay
import com.nuvio.app.features.details.MetaDetails
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.details.formatRuntimeForDisplay
import com.nuvio.app.features.home.MetaPreview
import com.nuvio.app.features.library.LocalLibraryCategory
import com.nuvio.app.features.library.normalizeLocalCategoryKeys

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
internal fun TitleQuickDetailsSheet(
    item: MetaPreview,
    isSaved: Boolean,
    savedCategoryKeys: List<String>,
    isWatched: Boolean,
    isRemoteLibrarySource: Boolean,
    onOpenDetails: () -> Unit,
    onSelectLocalCategory: (LocalLibraryCategory) -> Unit,
    onOpenRemoteListPicker: () -> Unit,
    onRemoveFromLibrary: () -> Unit,
    onToggleWatched: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scrollState = rememberScrollState()
    var enrichedDetails by remember(item.type, item.id) { mutableStateOf<MetaDetails?>(null) }

    LaunchedEffect(item.type, item.id) {
        enrichedDetails = runCatching {
            MetaDetailsRepository.fetch(item.type, item.id)
        }.getOrNull()
    }

    val title = enrichedDetails?.name?.takeIf(String::isNotBlank) ?: item.name
    val posterUrl = enrichedDetails?.poster?.takeIf(String::isNotBlank) ?: item.poster
    val releaseYear = (enrichedDetails?.releaseInfo ?: item.releaseInfo)
        ?.let(::extractReleaseYearForDisplay)
        ?.toString()
    val runtimeLabel = (enrichedDetails?.runtime ?: item.runtime)?.let(::formatRuntimeForDisplay)
    val ratingLabel = (enrichedDetails?.imdbRating ?: item.imdbRating)
        ?.trim()
        ?.takeIf { it.isNotBlank() && it != "0" && it != "0.0" }
    val ageRating = (enrichedDetails?.ageRating ?: item.ageRating)?.takeIf(String::isNotBlank)
    val genres = (enrichedDetails?.genres?.takeIf { it.isNotEmpty() } ?: item.genres).take(6)
    val synopsis = (enrichedDetails?.description?.takeIf(String::isNotBlank)
        ?: item.description?.takeIf(String::isNotBlank))
        ?.trim()
    val castMembers = enrichedDetails?.cast?.take(5).orEmpty()
    val sourceBadge = remember(item.id) {
        when {
            item.id.startsWith("cloudstream:", ignoreCase = true) -> {
                val provider = item.id.removePrefix("cloudstream:").substringBefore(':')
                "CloudStream • $provider"
            }
            item.id.startsWith("tmdb:", ignoreCase = true) -> "TMDB"
            item.id.startsWith("tt", ignoreCase = true) -> "IMDb / Addons"
            else -> null
        }
    }
    val typeBadge = remember(item.type) {
        when (item.type.trim().lowercase()) {
            "movie" -> "Movie"
            "series", "tv", "show" -> "Series"
            "anime" -> "Anime"
            else -> item.type.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        }
    }

    NuvioModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        contentColor = MaterialTheme.colorScheme.onSurface,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 640.dp)
                .verticalScroll(scrollState)
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.Top,
            ) {
                Box(
                    modifier = Modifier
                        .width(96.dp)
                        .aspectRatio(2f / 3f)
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                ) {
                    if (!posterUrl.isNullOrBlank()) {
                        AsyncImage(
                            model = posterUrl,
                            contentDescription = title,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop,
                        )
                    }
                }

                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        QuickDetailBadge(text = typeBadge, accent = true)
                        releaseYear?.let { QuickDetailBadge(text = it) }
                        runtimeLabel?.let { QuickDetailBadge(text = it) }
                        ratingLabel?.let { QuickDetailBadge(text = "★ $it") }
                        ageRating?.let { QuickDetailBadge(text = it) }
                        sourceBadge?.let { QuickDetailBadge(text = it) }
                    }

                    if (genres.isNotEmpty()) {
                        Text(
                            text = genres.joinToString(" • "),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }

            if (!synopsis.isNullOrBlank()) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        text = "Synopsis",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        text = synopsis,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }

            if (castMembers.isNotEmpty()) {
                Text(
                    text = "Cast: " + castMembers.joinToString(", ") { it.name },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.primary)
                        .clickable(onClick = onOpenDetails)
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Rounded.OpenInNew,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Open Full Details",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                }

            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = if (isSaved) Icons.Rounded.BookmarkAdded else Icons.Rounded.BookmarkAdd,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp),
                        )
                        Text(
                            text = if (isSaved) "Library Category" else "Save to Library",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                    }

                    if (isSaved) {
                        Row(
                            modifier = Modifier
                                .clip(RoundedCornerShape(999.dp))
                                .clickable(onClick = onRemoveFromLibrary)
                                .padding(horizontal = 10.dp, vertical = 4.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.DeleteOutline,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.error,
                                modifier = Modifier.size(16.dp),
                            )
                            Text(
                                text = "Remove",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                    }
                }

                if (isRemoteLibrarySource) {
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f))
                            .border(
                                1.dp,
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                                RoundedCornerShape(12.dp),
                            )
                            .clickable(onClick = onOpenRemoteListPicker)
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = if (isSaved) "Manage Synced Lists…" else "Choose Synced Lists…",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                } else {
                    val normalizedSelected = remember(savedCategoryKeys, isSaved) {
                        if (isSaved) normalizeLocalCategoryKeys(savedCategoryKeys).toSet() else emptySet()
                    }

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        LocalLibraryCategory.entries.forEach { category ->
                            val selected = category.key in normalizedSelected
                            val bg = if (selected) {
                                MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
                            } else {
                                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f)
                            }
                            val border = if (selected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)
                            }
                            Row(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(999.dp))
                                    .background(bg)
                                    .border(1.dp, border, RoundedCornerShape(999.dp))
                                    .clickable { onSelectLocalCategory(category) }
                                    .padding(horizontal = 12.dp, vertical = 7.dp),
                                horizontalArrangement = Arrangement.spacedBy(5.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                if (selected) {
                                    Icon(
                                        imageVector = Icons.Rounded.Check,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.size(15.dp),
                                    )
                                }
                                Text(
                                    text = category.label,
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                                    color = if (selected) {
                                        MaterialTheme.colorScheme.primary
                                    } else {
                                        MaterialTheme.colorScheme.onSurface
                                    },
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun QuickDetailBadge(
    text: String,
    accent: Boolean = false,
) {
    val bg = if (accent) {
        MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    val fg = if (accent) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(bg)
            .padding(horizontal = 9.dp, vertical = 4.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            color = fg,
            maxLines = 1,
        )
    }
}
