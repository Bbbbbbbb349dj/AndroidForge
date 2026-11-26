package com.nuvio.app.features.details.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.app.core.ui.DialogButton
import com.nuvio.app.core.ui.DialogButtonStyle
import com.nuvio.app.core.ui.DialogButtons
import com.nuvio.app.core.ui.DialogSurface
import com.nuvio.app.core.ui.NuvioInputField
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.nuvio
import com.nuvio.app.features.debrid.DebridStreamMetadata
import com.nuvio.app.features.debrid.DebridStreamPreferences
import com.nuvio.app.features.details.MetaVideo
import com.nuvio.app.features.details.seasonLabel
import com.nuvio.app.features.downloads.BatchDialogStep
import com.nuvio.app.features.downloads.BatchDownloadCoordinator
import com.nuvio.app.features.downloads.BatchDownloadPlan
import com.nuvio.app.features.downloads.BatchSourceFilter
import com.nuvio.app.features.downloads.DownloadsRepository
import com.nuvio.app.features.downloads.EpisodePlanStatus
import com.nuvio.app.features.downloads.PlannedEpisodeItem
import com.nuvio.app.features.downloads.batchKey
import com.nuvio.app.features.downloads.formatBytes
import com.nuvio.app.features.downloads.isBatchEpisodeDownloaded
import com.nuvio.app.features.downloads.isBatchEpisodeUnavailable
import com.nuvio.app.features.downloads.isCloudStreamBatchSource
import com.nuvio.app.features.downloads.isDownloadableDirectUrl
import com.nuvio.app.features.downloads.localizedEpisodeLabel
import com.nuvio.app.features.downloads.matchesBatchSearchQuery
import com.nuvio.app.features.downloads.matchesBatchSourceFilter
import com.nuvio.app.features.downloads.qualityBadge
import com.nuvio.app.features.streams.StreamBadgePresentation
import com.nuvio.app.features.streams.StreamItem
import com.nuvio.app.features.streams.StreamSourcePrefillSelector
import com.nuvio.app.features.streams.isResolverDependent
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource

private val WideBatchDialogProperties = DialogProperties(usePlatformDefaultWidth = false)

@Composable
fun BatchDownloadDialog(
    plan: BatchDownloadPlan,
    isEpisodeWatched: (MetaVideo) -> Boolean = { false },
    onDismissRequest: () -> Unit,
    onConfirm: () -> Unit,
) {
    var overrideTargetItem by remember { mutableStateOf<PlannedEpisodeItem?>(null) }

    when (val step = plan.step) {
        is BatchDialogStep.EpisodeSelection -> {
            EpisodeSelectionDialog(
                plan = plan,
                isEpisodeWatched = isEpisodeWatched,
                onDismissRequest = onDismissRequest,
            )
        }
        is BatchDialogStep.SourceSelection -> {
            SourceSelectionDialog(
                plan = plan,
                seasonIndex = step.seasonIndex,
                onDismissRequest = onDismissRequest,
                onConfirm = onConfirm,
                onOverrideClicked = { overrideTargetItem = it },
            )
        }
    }

    val overrideItem = overrideTargetItem
    if (overrideItem != null) {
        val currentSeason = when (val step = plan.step) {
            is BatchDialogStep.SourceSelection -> plan.seasonsToSource[step.seasonIndex]
            else -> plan.visibleSeason
        }
        StreamOverrideDialog(
            target = overrideItem,
            initialFilter = plan.sourceFilter,
            initialQuery = plan.searchQuery,
            showSyncSeasonAction = !plan.isSingleTitle &&
                (plan.seasonPlans[currentSeason]?.episodes?.size ?: 0) > 1,
            onSelectAndApplySeason = { stream ->
                BatchDownloadCoordinator.overrideEpisodeStream(
                    season = currentSeason,
                    episode = overrideItem.episode,
                    stream = stream,
                )
                BatchDownloadCoordinator.applyAddonProviderToSeason(
                    season = currentSeason,
                    preferredAddonName = stream.addonName,
                )
                overrideTargetItem = null
            },
            onSelect = { stream ->
                BatchDownloadCoordinator.overrideEpisodeStream(
                    season = currentSeason,
                    episode = overrideItem.episode,
                    stream = stream,
                )
                overrideTargetItem = null
            },
            onDismiss = { overrideTargetItem = null },
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EpisodeSelectionDialog(
    plan: BatchDownloadPlan,
    isEpisodeWatched: (MetaVideo) -> Boolean,
    onDismissRequest: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    DialogSurface(
        onDismissRequest = onDismissRequest,
        modifier = Modifier.fillMaxWidth(0.94f),
        title = plan.meta.name,
        properties = WideBatchDialogProperties,
    ) {
        val downloadsUiState by remember {
            DownloadsRepository.ensureLoaded()
            DownloadsRepository.uiState
        }.collectAsStateWithLifecycle()
        val currentDownloads = downloadsUiState.items

        fun isUnavailable(episode: MetaVideo, season: Int): Boolean =
            isBatchEpisodeUnavailable(currentDownloads, plan.meta.id, episode, season)

        fun isDownloaded(episode: MetaVideo, season: Int): Boolean =
            isBatchEpisodeDownloaded(currentDownloads, plan.meta.id, episode, season)

        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (plan.availableSeasons.size > 1) {
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(plan.availableSeasons) { seasonNumber ->
                        val sLabel = seasonLabel(seasonNumber)
                        val countInSeason = plan.episodesBySeason[seasonNumber].orEmpty().count { episode ->
                            episode.batchKey(seasonNumber) in plan.selectedEpisodeKeys
                        }
                        val chipText = if (countInSeason > 0) {
                            stringResource(Res.string.season_download_season_count, sLabel, countInSeason)
                        } else sLabel
                        val isSelectedSeason = plan.visibleSeason == seasonNumber

                        FilterChip(
                            selected = isSelectedSeason,
                            onClick = { BatchDownloadCoordinator.showSeason(seasonNumber) },
                            label = { Text(chipText, style = MaterialTheme.typography.labelMedium, maxLines = 1) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = tokens.colors.accent.copy(alpha = 0.2f),
                                selectedLabelColor = tokens.colors.accent,
                            ),
                        )
                    }
                }
            }
            val currentSeasonEpisodes = plan.episodesBySeason[plan.visibleSeason].orEmpty()
            val currentSeasonLabel = seasonLabel(plan.visibleSeason)

            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = currentSeasonLabel,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = tokens.colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    SelectionTextButton(Res.string.downloads_select_unwatched) {
                        BatchDownloadCoordinator.selectUnwatchedForSeason(
                            season = plan.visibleSeason,
                            isEpisodeWatched = isEpisodeWatched,
                        )
                    }
                    listOf(3, 5, 10).forEach { packCount ->
                        if (currentSeasonEpisodes.size > packCount) {
                            TextButton(
                                onClick = {
                                    BatchDownloadCoordinator.selectNextUnwatchedForSeason(
                                        season = plan.visibleSeason,
                                        limit = packCount,
                                        isEpisodeWatched = isEpisodeWatched,
                                    )
                                },
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                            ) {
                                Text(
                                    text = "Next $packCount",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = tokens.colors.accent,
                                )
                            }
                        }
                    }
                    SelectionTextButton(Res.string.downloads_select_all) {
                        BatchDownloadCoordinator.selectAllForSeason(plan.visibleSeason)
                    }
                    SelectionTextButton(Res.string.downloads_deselect_all) {
                        BatchDownloadCoordinator.deselectAllForSeason(plan.visibleSeason)
                    }
                }
            }

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 280.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                items(
                    items = currentSeasonEpisodes,
                    key = { it.id.ifBlank { "${it.season}_${it.episode}" } },
                ) { episode ->
                    val episodeNumber = episode.episode ?: 0
                    val key = episode.batchKey(plan.visibleSeason)
                    val isChecked = key in plan.selectedEpisodeKeys
                    val unavailable = isUnavailable(episode, plan.visibleSeason)
                    val completed = isDownloaded(episode, plan.visibleSeason)
                    val watched = isEpisodeWatched(episode)

                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable(enabled = !unavailable) {
                                BatchDownloadCoordinator.toggleEpisodeSelection(plan.visibleSeason, episodeNumber)
                            },
                        shape = RoundedCornerShape(NuvioTokens.Radius.md),
                        color = if (isChecked) tokens.colors.accent.copy(alpha = 0.14f) else tokens.colors.surfaceCard,
                        border = BorderStroke(
                            width = 1.dp,
                            color = if (isChecked) tokens.colors.accent.copy(alpha = 0.65f) else tokens.colors.borderSubtle,
                        ),
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 10.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Checkbox(
                                checked = if (unavailable) true else isChecked,
                                enabled = !unavailable,
                                onCheckedChange = {
                                    BatchDownloadCoordinator.toggleEpisodeSelection(plan.visibleSeason, episodeNumber)
                                },
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                val episodeTitle = episode.title?.takeIf { it.isNotBlank() }
                                    ?: stringResource(Res.string.downloads_episode_fallback_title, episodeNumber)
                                Text(
                                    text = localizedEpisodeLabel(plan.visibleSeason, episodeNumber, episodeTitle),
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                                    color = if (unavailable) tokens.colors.textMuted else tokens.colors.textPrimary,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                val tags = mutableListOf<String>()
                                if (completed) tags.add(stringResource(Res.string.season_download_already_downloaded))
                                else if (unavailable) tags.add(stringResource(Res.string.downloads_status_already_in_progress))
                                if (watched) tags.add(stringResource(Res.string.episodes_cd_watched))
                                if (tags.isNotEmpty()) {
                                    Text(
                                        text = tags.joinToString(" • "),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = if (completed) tokens.colors.accent else tokens.colors.textSecondary,
                                    )
                                }
                            }
                        }
                    }
                }
            }
            val selectedCount = plan.totalSelectedCount
            val seasonsCount = plan.availableSeasons.count(plan::isSeasonSelected)
            val summaryText = if (seasonsCount > 1) {
                stringResource(Res.string.downloads_episodes_selected_multi_season, selectedCount, seasonsCount)
            } else {
                stringResource(Res.string.downloads_episodes_selected, selectedCount)
            }

            Text(
                text = summaryText,
                style = MaterialTheme.typography.bodySmall,
                color = tokens.colors.textSecondary,
            )
        }

        DialogButtons {
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismissRequest,
                style = DialogButtonStyle.Secondary,
            )
            DialogButton(
                text = stringResource(Res.string.downloads_action_continue_source_selection),
                onClick = { BatchDownloadCoordinator.continueToSourceSelection() },
                style = DialogButtonStyle.Primary,
                enabled = plan.totalSelectedCount > 0,
            )
        }
    }
}

@Composable
private fun SourceSelectionDialog(
    plan: BatchDownloadPlan,
    seasonIndex: Int,
    onDismissRequest: () -> Unit,
    onConfirm: () -> Unit,
    onOverrideClicked: (PlannedEpisodeItem) -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    val totalSeasons = plan.seasonsToSource.size
    val currentSeason = plan.seasonsToSource[seasonIndex]
    val currentSeasonPlan = plan.seasonPlans[currentSeason]
    val isPlanning = currentSeasonPlan?.isPlanning == true

    val dialogTitle = if (plan.isSingleTitle) {
        plan.meta.name
    } else {
        stringResource(
            Res.string.downloads_season_step_indicator,
            seasonIndex + 1,
            totalSeasons,
        )
    }

    val currentSeasonLabel = if (plan.isSingleTitle) {
        plan.meta.releaseInfo.orEmpty()
    } else {
        seasonLabel(currentSeason)
    }

    val episodes = currentSeasonPlan?.episodes.orEmpty()
    val allStreamsAcrossSeason = remember(episodes) {
        episodes.flatMap { it.allAvailableStreams }
    }
    val nuvioStreamCount = remember(allStreamsAcrossSeason) {
        allStreamsAcrossSeason.count { !it.isCloudStreamBatchSource() }
    }
    val cloudStreamCount = remember(allStreamsAcrossSeason) {
        allStreamsAcrossSeason.count { it.isCloudStreamBatchSource() }
    }

    DialogSurface(
        onDismissRequest = onDismissRequest,
        modifier = Modifier.fillMaxWidth(0.94f),
        title = dialogTitle,
        properties = WideBatchDialogProperties,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            val readyInSeason = remember(episodes) {
                episodes.count { it.status == EpisodePlanStatus.Ready && it.streamCandidate != null }
            }
            val totalKnownBytes = remember(episodes) {
                episodes.mapNotNull { ep ->
                    ep.sizeBytes?.takeIf { ep.status == EpisodePlanStatus.Ready && it > 0L }
                }.sum()
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    if (currentSeasonLabel.isNotBlank()) {
                        Text(
                            text = currentSeasonLabel,
                            style = MaterialTheme.typography.titleMedium,
                            color = tokens.colors.textPrimary,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                    if (episodes.isNotEmpty()) {
                        val sizePart = if (totalKnownBytes > 0L) " · ~${formatBytes(totalKnownBytes)}" else ""
                        Text(
                            text = "$readyInSeason/${episodes.size} ready$sizePart",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (readyInSeason > 0) tokens.colors.accent else tokens.colors.textMuted,
                        )
                    }
                }
                if (isPlanning) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        FindingSourceIndicator(compact = true)
                        Surface(
                            shape = RoundedCornerShape(NuvioTokens.Radius.full),
                            color = tokens.colors.surfaceCard,
                            border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                            modifier = Modifier.clickable { BatchDownloadCoordinator.stopActiveScan() },
                        ) {
                            Text(
                                text = "Stop scan",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = tokens.colors.textSecondary,
                                modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
                            )
                        }
                    }
                }
            }

            BatchSourceFilterBar(
                selected = plan.sourceFilter,
                nuvioCount = nuvioStreamCount,
                cloudStreamCount = cloudStreamCount,
                onSelect = BatchDownloadCoordinator::setSourceFilter,
            )

            BatchSearchAndQualityBar(
                query = plan.searchQuery,
                onQueryChange = BatchDownloadCoordinator::setSearchQuery,
                placeholder = "Search quality, provider, language (e.g. 1080p, HEVC, Hindi)...",
            )

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 300.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(
                    items = episodes,
                    key = { it.episode.id.ifBlank { "${it.episode.season}_${it.episode.episode}" } },
                ) { item ->
                    EpisodeSourcePlanRow(
                        item = item,
                        season = currentSeason,
                        defaultTitle = plan.meta.name,
                        activeFilter = plan.sourceFilter,
                        activeQuery = plan.searchQuery,
                        onChangeSource = { onOverrideClicked(item) },
                    )
                }
            }
        }

        val isLastSeason = seasonIndex >= totalSeasons - 1

        DialogButtons {
            DialogButton(
                text = if (plan.isSingleTitle) {
                    stringResource(Res.string.action_cancel)
                } else {
                    stringResource(Res.string.action_back)
                },
                onClick = {
                    if (plan.isSingleTitle) {
                        onDismissRequest()
                    } else if (seasonIndex > 0) {
                        BatchDownloadCoordinator.goToSeasonIndex(seasonIndex - 1)
                    } else {
                        BatchDownloadCoordinator.goToEpisodeSelection()
                    }
                },
                style = DialogButtonStyle.Secondary,
            )

            val totalReadyAcrossPlan = plan.seasonPlans.values.sumOf { it.readyToDownloadCount }
            if (!isLastSeason && !plan.isSingleTitle) {
                DialogButton(
                    text = stringResource(Res.string.downloads_next_season),
                    onClick = { BatchDownloadCoordinator.goToSeasonIndex(seasonIndex + 1) },
                    style = DialogButtonStyle.Primary,
                    enabled = !isPlanning || (currentSeasonPlan?.readyToDownloadCount ?: 0) > 0,
                    loading = isPlanning && (currentSeasonPlan?.readyToDownloadCount ?: 0) == 0,
                )
            } else {
                DialogButton(
                    text = if (totalReadyAcrossPlan > 0 && !plan.isSingleTitle) {
                        "${stringResource(Res.string.downloads_action_queue)} ($totalReadyAcrossPlan)"
                    } else {
                        stringResource(Res.string.downloads_action_queue)
                    },
                    onClick = onConfirm,
                    style = DialogButtonStyle.Primary,
                    enabled = totalReadyAcrossPlan > 0,
                    loading = isPlanning && totalReadyAcrossPlan == 0,
                )
            }
        }
    }
}

@Composable
private fun BatchSearchAndQualityBar(
    query: String,
    onQueryChange: (String) -> Unit,
    placeholder: String,
) {
    val tokens = MaterialTheme.nuvio
    val activeWords = remember(query) {
        query.trim().lowercase().split(' ').filter { it.isNotEmpty() }.toSet()
    }
    val quickTags = remember {
        listOf(
            "4K" to "4k",
            "1080p" to "1080p",
            "720p" to "720p",
            "HDR" to "hdr",
            "HEVC" to "hevc",
        )
    }

    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        NuvioInputField(
            value = query,
            onValueChange = onQueryChange,
            placeholder = placeholder,
            trailingContent = if (query.isNotEmpty()) {
                {
                    IconButton(onClick = { onQueryChange("") }) {
                        Icon(
                            imageVector = Icons.Rounded.Close,
                            contentDescription = "Clear search",
                            tint = tokens.colors.textMuted,
                        )
                    }
                }
            } else null,
        )
        LazyRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            items(quickTags) { (label, token) ->
                val selected = token in activeWords
                Surface(
                    shape = RoundedCornerShape(NuvioTokens.Radius.full),
                    color = if (selected) tokens.colors.accent.copy(alpha = 0.22f) else tokens.colors.surfaceCard,
                    border = BorderStroke(
                        width = 1.dp,
                        color = if (selected) tokens.colors.accent else tokens.colors.borderSubtle,
                    ),
                    modifier = Modifier.clickable {
                        val words = query.trim().split(' ').filter { it.isNotEmpty() }
                        val next = if (words.any { it.equals(token, ignoreCase = true) }) {
                            words.filterNot { it.equals(token, ignoreCase = true) }.joinToString(" ")
                        } else {
                            (words + token).joinToString(" ")
                        }
                        onQueryChange(next)
                    },
                ) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
                        color = if (selected) tokens.colors.accent else tokens.colors.textSecondary,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun BatchSourceFilterBar(
    selected: BatchSourceFilter,
    nuvioCount: Int,
    cloudStreamCount: Int,
    onSelect: (BatchSourceFilter) -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    val totalCount = nuvioCount + cloudStreamCount
    LazyRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        listOf(
            BatchSourceFilter.All to (if (totalCount > 0) "All ($totalCount)" else "All Sources"),
            BatchSourceFilter.Nuvio to (if (totalCount > 0) "Nuvio ($nuvioCount)" else "Nuvio"),
            BatchSourceFilter.CloudStream to (if (totalCount > 0) "CloudStream ($cloudStreamCount)" else "CloudStream"),
        ).forEach { (filter, label) ->
            item {
                val isSelected = selected == filter
                Surface(
                    shape = RoundedCornerShape(NuvioTokens.Radius.sm),
                    color = if (isSelected) tokens.colors.accent.copy(alpha = 0.2f) else tokens.colors.surfaceCard,
                    border = BorderStroke(
                        width = 1.dp,
                        color = if (isSelected) tokens.colors.accent else tokens.colors.borderSubtle,
                    ),
                    modifier = Modifier.clickable { onSelect(filter) },
                ) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
                        color = if (isSelected) tokens.colors.accent else tokens.colors.textSecondary,
                        maxLines = 1,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun SourceOriginBadge(isCloudStream: Boolean) {
    val tokens = MaterialTheme.nuvio
    val bgColor = if (isCloudStream) {
        tokens.colors.accent.copy(alpha = 0.2f)
    } else {
        tokens.colors.surfaceElevated
    }
    val fgColor = if (isCloudStream) {
        tokens.colors.accent
    } else {
        tokens.colors.textSecondary
    }
    Box(
        modifier = Modifier
            .background(bgColor, RoundedCornerShape(6.dp))
            .padding(horizontal = 7.dp, vertical = 2.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = if (isCloudStream) "CLOUDSTREAM" else "NUVIO",
            style = MaterialTheme.typography.labelSmall.copy(
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 0.4.sp,
            ),
            color = fgColor,
            maxLines = 1,
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EpisodeSourcePlanRow(
    item: PlannedEpisodeItem,
    season: Int,
    defaultTitle: String,
    activeFilter: BatchSourceFilter,
    activeQuery: String,
    onChangeSource: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    val episodeTitle = item.episode.title?.takeIf { it.isNotBlank() } ?: defaultTitle
    val displayText = item.episode.episode?.let { episodeNumber ->
        localizedEpisodeLabel(season, episodeNumber, episodeTitle)
    } ?: episodeTitle

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(NuvioTokens.Radius.md),
        color = tokens.colors.surfaceCard,
        border = BorderStroke(1.dp, tokens.colors.borderSubtle),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = displayText,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                    color = tokens.colors.textPrimary,
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )

                if (item.status == EpisodePlanStatus.Ready || item.allAvailableStreams.isNotEmpty()) {
                    OutlinedButton(
                        onClick = onChangeSource,
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                        modifier = Modifier
                            .padding(start = 8.dp)
                            .heightIn(min = 32.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Edit,
                            contentDescription = null,
                            tint = tokens.colors.accent,
                            modifier = Modifier.size(13.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = stringResource(Res.string.downloads_override_source),
                            style = MaterialTheme.typography.labelSmall,
                            color = tokens.colors.textPrimary,
                            maxLines = 1,
                        )
                    }
                }
            }

            when {
                item.status == EpisodePlanStatus.Loading -> {
                    FindingSourceIndicator(compact = true)
                }
                item.status == EpisodePlanStatus.AlreadyDownloaded -> {
                    Text(
                        text = stringResource(Res.string.season_download_already_downloaded),
                        style = MaterialTheme.typography.bodySmall,
                        color = tokens.colors.accent,
                    )
                }
                item.status == EpisodePlanStatus.AlreadyInProgress -> {
                    Text(
                        text = stringResource(Res.string.downloads_status_queued),
                        style = MaterialTheme.typography.bodySmall,
                        color = tokens.colors.textSecondary,
                    )
                }
                item.status == EpisodePlanStatus.Ready && item.streamCandidate != null -> {
                    val selected = item.streamCandidate
                    val isCs3 = selected.isCloudStreamBatchSource()
                    val badge = item.resolutionLabel
                    val provider = selected.addonName.takeIf { it.isNotBlank() }
                    val size = item.sizeBytes?.takeIf { it > 0 }?.let(::formatBytes)
                    val streamHeadline = selected.streamLabel
                        .ifBlank { selected.name ?: selected.title.orEmpty() }
                        .trim()

                    FlowRow(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        SourceOriginBadge(isCloudStream = isCs3)
                        val metaSummary = streamSourceSummary(badge, provider, size)
                        if (metaSummary.isNotBlank()) {
                            Text(
                                text = metaSummary,
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = tokens.colors.accent,
                            )
                        }
                        if (item.allAvailableStreams.size > 1) {
                            Text(
                                text = if (item.isScanningMore) {
                                    "· ${item.allAvailableStreams.size} sources (scanning…)"
                                } else {
                                    "· ${item.allAvailableStreams.size} sources"
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = tokens.colors.textMuted,
                            )
                        }
                    }

                    if (streamHeadline.isNotBlank()) {
                        Text(
                            text = streamHeadline,
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.textSecondary,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
                else -> {
                    val hint = when {
                        activeQuery.isNotBlank() && item.allAvailableStreams.isNotEmpty() ->
                            "No source matches \"$activeQuery\" (${item.allAvailableStreams.size} total available)"
                        activeFilter == BatchSourceFilter.CloudStream && item.allAvailableStreams.any { !it.isCloudStreamBatchSource() } ->
                            "No CloudStream source found (Nuvio sources available)"
                        activeFilter == BatchSourceFilter.Nuvio && item.allAvailableStreams.any { it.isCloudStreamBatchSource() } ->
                            "No Nuvio source found (CloudStream sources available)"
                        else -> stringResource(Res.string.season_download_no_source_found)
                    }
                    Text(
                        text = hint,
                        style = MaterialTheme.typography.bodySmall,
                        color = tokens.colors.danger,
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun StreamOverrideDialog(
    target: PlannedEpisodeItem,
    initialFilter: BatchSourceFilter,
    initialQuery: String = "",
    showSyncSeasonAction: Boolean = false,
    onSelectAndApplySeason: ((StreamItem) -> Unit)? = null,
    onSelect: (StreamItem) -> Unit,
    onDismiss: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    var filter by remember(initialFilter) { mutableStateOf(initialFilter) }
    var searchQuery by remember(initialQuery) { mutableStateOf(initialQuery) }
    var audioVariantFilter by remember { mutableStateOf("Both") }
    val episodeNumber = target.episode.episode
    val dialogTitle = if (episodeNumber != null) {
        stringResource(Res.string.downloads_select_source_dialog_title, episodeNumber)
    } else {
        stringResource(Res.string.downloads_select_source_dialog_title_single)
    }

    val allStreams = remember(target.allAvailableStreams) {
        target.allAvailableStreams.filter { stream ->
            isDownloadableDirectUrl(stream.playableDirectUrl) || stream.isResolverDependent()
        }.ifEmpty { target.allAvailableStreams }
    }
    val nuvioCount = remember(allStreams) { allStreams.count { !it.isCloudStreamBatchSource() } }
    val cloudStreamCount = remember(allStreams) { allStreams.count { it.isCloudStreamBatchSource() } }
    val filteredStreams = remember(allStreams, filter, searchQuery, audioVariantFilter) {
        allStreams.filter { stream ->
            stream.matchesBatchSourceFilter(filter) && stream.matchesBatchSearchQuery(searchQuery)
        }.filter { stream ->
            when (audioVariantFilter) {
                "SUB" -> when (StreamBadgePresentation.audioVariantOf(stream)) {
                    "SUB", "DUAL" -> true
                    "DUB" -> false
                    else -> true
                }
                "DUB" -> when (StreamBadgePresentation.audioVariantOf(stream)) {
                    "DUB", "DUAL" -> true
                    "SUB" -> false
                    else -> true
                }
                else -> true
            }
        }
    }

    DialogSurface(
        onDismissRequest = onDismiss,
        modifier = Modifier.fillMaxWidth(0.94f),
        title = dialogTitle,
        properties = WideBatchDialogProperties,
    ) {
        BatchSourceFilterBar(
            selected = filter,
            nuvioCount = nuvioCount,
            cloudStreamCount = cloudStreamCount,
            onSelect = { filter = it },
        )

        BatchSearchAndQualityBar(
            query = searchQuery,
            onQueryChange = { searchQuery = it },
            placeholder = "Search ${allStreams.size} streams (quality, scraper, language)...",
        )

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            listOf("Both", "SUB", "DUB").forEach { mode ->
                FilterChip(
                    selected = audioVariantFilter == mode,
                    onClick = { audioVariantFilter = mode },
                    label = {
                        Text(
                            text = mode,
                            style = MaterialTheme.typography.labelMedium,
                            maxLines = 1,
                        )
                    },
                )
            }
        }

        if (filteredStreams.isEmpty()) {
            Text(
                text = if (searchQuery.isNotBlank()) {
                    "No streams match \"$searchQuery\""
                } else {
                    stringResource(Res.string.season_download_no_source_found)
                },
                style = MaterialTheme.typography.bodyMedium,
                color = tokens.colors.textSecondary,
            )
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 330.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(filteredStreams) { stream ->
                    val facts = remember(stream) {
                        DebridStreamMetadata.facts(stream, DebridStreamPreferences())
                    }
                    val isCurrentSelection = stream == target.streamCandidate
                    val isCs3 = stream.isCloudStreamBatchSource()

                    val variantLabel = StreamBadgePresentation.audioVariantOf(stream)
                    val badge = listOfNotNull(facts.qualityBadge(), variantLabel)
                        .joinToString(" • ")
                        .takeIf { it.isNotEmpty() }
                    val size = StreamSourcePrefillSelector.sizeBytes(stream)?.let(::formatBytes)
                    val addon = stream.addonName

                    val titleText = stream.streamLabel.ifBlank {
                        stream.name ?: stringResource(Res.string.downloads_stream_fallback_title)
                    }
                    val subtitleText = streamSourceSummary(badge, addon, size)

                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelect(stream) },
                        shape = RoundedCornerShape(NuvioTokens.Radius.md),
                        color = if (isCurrentSelection) {
                            tokens.colors.accent.copy(alpha = 0.16f)
                        } else {
                            tokens.colors.surfaceCard
                        },
                        border = if (isCurrentSelection) {
                            BorderStroke(1.5.dp, tokens.colors.accent)
                        } else {
                            BorderStroke(1.dp, tokens.colors.borderSubtle)
                        },
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Column(
                                modifier = Modifier.weight(1f),
                                verticalArrangement = Arrangement.spacedBy(4.dp),
                            ) {
                                FlowRow(
                                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                                    verticalArrangement = Arrangement.spacedBy(4.dp),
                                ) {
                                    SourceOriginBadge(isCloudStream = isCs3)
                                    if (subtitleText.isNotBlank()) {
                                        Text(
                                            text = subtitleText,
                                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                            color = if (isCurrentSelection) {
                                                tokens.colors.accent
                                            } else {
                                                tokens.colors.textSecondary
                                            },
                                        )
                                    }
                                }
                                Text(
                                    text = titleText,
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                                    color = tokens.colors.textPrimary,
                                    maxLines = 3,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                val extraDesc = stream.description?.trim()?.takeIf {
                                    it.isNotBlank() && !titleText.contains(it, ignoreCase = true)
                                }
                                if (extraDesc != null) {
                                    Text(
                                        text = extraDesc,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = tokens.colors.textMuted,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                }
                            }
                            if (isCurrentSelection) {
                                Spacer(modifier = Modifier.width(8.dp))
                                Icon(
                                    imageVector = Icons.Rounded.Check,
                                    contentDescription = null,
                                    modifier = Modifier.size(20.dp),
                                    tint = tokens.colors.accent,
                                )
                            }
                        }
                    }
                }
            }
        }

        DialogButtons {
            if (showSyncSeasonAction && onSelectAndApplySeason != null && target.streamCandidate != null) {
                val activeCandidate = target.streamCandidate
                DialogButton(
                    text = "Use ${activeCandidate.addonName.ifBlank { "provider" }} for season",
                    onClick = { onSelectAndApplySeason(activeCandidate) },
                    style = DialogButtonStyle.Secondary,
                )
            }
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismiss,
                style = DialogButtonStyle.Secondary,
            )
        }
    }
}

@Composable
private fun SelectionTextButton(label: StringResource, onClick: () -> Unit) {
    TextButton(
        onClick = onClick,
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Text(
            text = stringResource(label),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.nuvio.colors.accent,
            maxLines = 1,
        )
    }
}

@Composable
private fun FindingSourceIndicator(compact: Boolean) {
    val tokens = MaterialTheme.nuvio
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(if (compact) 11.dp else 14.dp),
            strokeWidth = if (compact) 1.6.dp else 2.dp,
            color = tokens.colors.accent,
        )
        Text(
            text = stringResource(Res.string.season_download_finding_source),
            style = MaterialTheme.typography.bodySmall,
            color = if (compact) tokens.colors.textSecondary else tokens.colors.accent,
        )
    }
}

private fun streamSourceSummary(badge: String?, addon: String?, size: String?): String =
    listOfNotNull(badge, addon, size).joinToString(" • ")
