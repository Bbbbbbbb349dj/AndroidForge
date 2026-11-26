package com.nuvio.app.features.search

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Extension
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.NorthWest
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioLoadingIndicator
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.nuvio
import com.nuvio.app.features.cloudstream.CloudStreamPluginItem
import com.nuvio.app.features.cloudstream.CloudStreamRepository
import com.nuvio.app.features.cloudstream.CloudStreamSearchItem
import com.nuvio.app.features.catalog.CatalogTarget
import com.nuvio.app.features.cloudstream.toMetaPreview
import com.nuvio.app.features.home.HomeCatalogSection
import com.nuvio.app.features.home.MetaPreview
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withTimeoutOrNull

data class SearchSuggestionItem(
    val text: String,
    val subtitle: String? = null,
    val isHistory: Boolean = false,
    val preview: MetaPreview? = null,
)

data class CloudStreamProviderSearchOutcome(
    val plugin: CloudStreamPluginItem,
    val items: List<CloudStreamSearchItem>,
    val errorMessage: String? = null,
)

suspend fun searchRunnableCloudStreamProviders(
    query: String,
    timeoutPerProviderMs: Long = 14_000L,
): List<CloudStreamProviderSearchOutcome> {
    val trimmed = query.trim()
    if (trimmed.isBlank()) return emptyList()
    CloudStreamRepository.initialize()
    val runnablePlugins = CloudStreamRepository.uiState.value.plugins
        .filter(CloudStreamPluginItem::isRunnable)
    if (runnablePlugins.isEmpty()) return emptyList()

    return coroutineScope {
        runnablePlugins.map { plugin ->
            async {
                val outcome = runCatching {
                    withTimeoutOrNull(timeoutPerProviderMs) {
                        CloudStreamRepository.search(
                            query = trimmed,
                            providerId = plugin.metadata.id.value,
                        ).firstOrNull()
                    }
                }.getOrElse { error ->
                    Result.failure(error)
                }
                when {
                    outcome == null -> CloudStreamProviderSearchOutcome(
                        plugin = plugin,
                        items = emptyList(),
                        errorMessage = "${plugin.metadata.name} timed out",
                    )
                    outcome.isSuccess -> {
                        val deduped = outcome.getOrDefault(emptyList())
                            .filter { it.name.isNotBlank() && it.data.isNotBlank() }
                            .distinctBy { "${it.type}:${it.data.trim().lowercase()}" }
                        CloudStreamProviderSearchOutcome(
                            plugin = plugin,
                            items = deduped,
                            errorMessage = null,
                        )
                    }
                    else -> CloudStreamProviderSearchOutcome(
                        plugin = plugin,
                        items = emptyList(),
                        errorMessage = outcome.exceptionOrNull()?.message ?: "${plugin.metadata.name} search failed",
                    )
                }
            }
        }.awaitAll()
    }
}

fun buildCloudStreamSearchSections(
    outcomes: List<CloudStreamProviderSearchOutcome>,
): List<HomeCatalogSection> {
    val seenGlobalKeys = HashSet<String>()
    return outcomes.mapNotNull { outcome ->
        if (outcome.items.isEmpty()) return@mapNotNull null
        val previews = outcome.items.mapNotNull { item ->
            val preview = item.toMetaPreview()
            val dedupKey = "${outcome.plugin.metadata.id.value}:${preview.id}"
            if (!seenGlobalKeys.add(dedupKey)) null else preview
        }
        if (previews.isEmpty()) return@mapNotNull null
        HomeCatalogSection(
            key = "cloudstream_search:${outcome.plugin.metadata.id.value}",
            title = outcome.plugin.metadata.name,
            subtitle = "CloudStream Extension",
            addonName = "${outcome.plugin.metadata.name} · CloudStream",
            target = CatalogTarget.Addon(
                manifestUrl = "cloudstream://${outcome.plugin.metadata.id.value}",
                contentType = previews.first().type,
                catalogId = "search",
            ),
            items = previews,
        )
    }
}

fun buildSearchAutocompleteSuggestions(
    rawQuery: String,
    recentSearches: List<String>,
    sections: List<HomeCatalogSection>,
    tmdbTitles: List<MetaPreview> = emptyList(),
    limit: Int = 8,
): List<SearchSuggestionItem> {
    val trimmed = rawQuery.trim()
    if (trimmed.isBlank()) return emptyList()
    val queryLower = trimmed.lowercase()
    val seen = LinkedHashSet<String>()
    val result = ArrayList<SearchSuggestionItem>(limit)

    recentSearches
        .filter { it.lowercase().contains(queryLower) && !it.equals(trimmed, ignoreCase = true) }
        .take(3)
        .forEach { historyEntry ->
            if (seen.add(historyEntry.lowercase())) {
                result += SearchSuggestionItem(
                    text = historyEntry,
                    subtitle = "Recent search",
                    isHistory = true,
                )
            }
        }

    tmdbTitles.forEach { title ->
        if (result.size >= limit) return@forEach
        val cleanName = title.name.trim()
        if (cleanName.isBlank()) return@forEach
        if (!seen.add(cleanName.lowercase())) return@forEach
        val yearLabel = title.releaseInfo?.take(4)?.takeIf { it.all(Char::isDigit) }
        val typeLabel = title.type.replaceFirstChar { char ->
            if (char.isLowerCase()) char.titlecase() else char.toString()
        }
        result += SearchSuggestionItem(
            text = cleanName,
            subtitle = listOfNotNull(typeLabel, yearLabel, "TMDB").joinToString(" · "),
            isHistory = false,
            preview = title,
        )
    }

    sections.asSequence()
        .flatMap { section ->
            section.items.asSequence().map { item -> section to item }
        }
        .forEach { (section, item) ->
            if (result.size >= limit) return@forEach
            val cleanName = item.name.trim()
            if (cleanName.isBlank()) return@forEach
            if (!seen.add(cleanName.lowercase())) return@forEach
            val yearLabel = item.releaseInfo?.take(4)?.takeIf { it.all(Char::isDigit) }
            val sourceLabel = section.addonName.takeIf { it.isNotBlank() } ?: section.title
            val metaParts = listOfNotNull(
                item.type.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() },
                yearLabel,
                sourceLabel,
            )
            result += SearchSuggestionItem(
                text = cleanName,
                subtitle = metaParts.joinToString(" · "),
                isHistory = false,
                preview = item,
            )
        }

    return result
}

@Composable
internal fun SearchCloudStreamExtensionToggleRow(
    enabled: Boolean,
    runnableExtensionCount: Int,
    onToggle: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    val shape = RoundedCornerShape(NuvioTokens.Radius.lg)
    Surface(
        shape = shape,
        color = if (enabled) tokens.colors.accent.copy(alpha = 0.12f) else tokens.colors.surfaceCard,
        border = BorderStroke(
            width = 1.dp,
            color = if (enabled) tokens.colors.accent.copy(alpha = 0.5f) else tokens.colors.borderSubtle,
        ),
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .clickable { onToggle(!enabled) },
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.weight(1f),
            ) {
                Icon(
                    imageVector = Icons.Rounded.Extension,
                    contentDescription = null,
                    tint = if (enabled) tokens.colors.accent else tokens.colors.textMuted,
                    modifier = Modifier.size(18.dp),
                )
                Column {
                    Text(
                        text = "Include CloudStream Extensions",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.textPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = when {
                            !enabled -> "Off · Searching Nuvio catalogs only"
                            runnableExtensionCount == 0 -> "On · No runnable CloudStream extensions enabled"
                            runnableExtensionCount == 1 -> "On · Searching 1 enabled extension concurrently"
                            else -> "On · Searching $runnableExtensionCount enabled extensions concurrently"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = tokens.colors.textMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Switch(
                checked = enabled,
                onCheckedChange = onToggle,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = tokens.colors.onAccent,
                    checkedTrackColor = tokens.colors.accent,
                ),
            )
        }
    }
}

@Composable
@OptIn(ExperimentalFoundationApi::class)
internal fun SearchAutocompleteSuggestionsCard(
    visible: Boolean,
    isLoading: Boolean,
    suggestions: List<SearchSuggestionItem>,
    errorMessage: String?,
    onSelectSuggestion: (SearchSuggestionItem) -> Unit,
    onFillQuery: (String) -> Unit,
    onSuggestionLongPress: ((SearchSuggestionItem) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    AnimatedVisibility(
        visible = visible,
        enter = expandVertically() + fadeIn(),
        exit = shrinkVertically() + fadeOut(),
        modifier = modifier,
    ) {
        Surface(
            shape = RoundedCornerShape(NuvioTokens.Radius.lg),
            color = tokens.colors.surfaceCard,
            border = BorderStroke(1.dp, tokens.colors.borderSubtle),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "SUGGESTIONS",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = tokens.colors.textMuted,
                    )
                    if (isLoading) {
                        NuvioLoadingIndicator(modifier = Modifier.size(14.dp))
                    }
                }
                HorizontalDivider(color = tokens.colors.borderSubtle)
                when {
                    suggestions.isNotEmpty() -> {
                        suggestions.forEachIndexed { index, item ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .combinedClickable(
                                        onClick = { onSelectSuggestion(item) },
                                        // Long press only for suggestions that carry metadata;
                                        // plain tap keeps searching and never navigates.
                                        onLongClick = if (item.preview != null) {
                                            { onSuggestionLongPress?.invoke(item) }
                                        } else {
                                            null
                                        },
                                    )
                                    .padding(horizontal = 14.dp, vertical = 9.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                            ) {
                                Icon(
                                    imageVector = if (item.isHistory) Icons.Rounded.History else Icons.Rounded.Search,
                                    contentDescription = null,
                                    tint = tokens.colors.textMuted,
                                    modifier = Modifier.size(17.dp),
                                )
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = item.text,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.Medium,
                                        color = tokens.colors.textPrimary,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    item.subtitle?.takeIf { it.isNotBlank() }?.let { sub ->
                                        Text(
                                            text = sub,
                                            style = MaterialTheme.typography.labelSmall,
                                            color = tokens.colors.textMuted,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                        )
                                    }
                                }
                                IconButton(
                                    onClick = { onFillQuery(item.text) },
                                    modifier = Modifier.size(28.dp),
                                ) {
                                    Icon(
                                        imageVector = Icons.Rounded.NorthWest,
                                        contentDescription = "Fill search query",
                                        tint = tokens.colors.textMuted,
                                        modifier = Modifier.size(15.dp),
                                    )
                                }
                            }
                            if (index < suggestions.lastIndex) {
                                HorizontalDivider(color = tokens.colors.borderSubtle.copy(alpha = 0.5f))
                            }
                        }
                    }
                    isLoading -> {
                        Text(
                            text = "Finding matching titles…",
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        )
                    }
                    !errorMessage.isNullOrBlank() -> {
                        Text(
                            text = errorMessage,
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.warning,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        )
                    }
                    else -> {
                        Text(
                            text = "No instant suggestions — results appear below",
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        )
                    }
                }
            }
        }
    }
}
