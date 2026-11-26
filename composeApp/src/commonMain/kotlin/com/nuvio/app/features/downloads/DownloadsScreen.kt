package com.nuvio.app.features.downloads

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Download
import androidx.compose.material.icons.rounded.Folder
import androidx.compose.material.icons.rounded.Movie
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material3.Surface
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import com.nuvio.app.core.ui.nuvio
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.app.core.ui.NuvioActionLabel
import com.nuvio.app.core.deeplink.AppDeepLinkRepository
import com.nuvio.app.core.ui.NuvioPosterCard
import com.nuvio.app.core.ui.NuvioScreen
import nuvio.composeapp.generated.resources.media_movie
import nuvio.composeapp.generated.resources.media_series
import com.nuvio.app.core.ui.NuvioScreenHeader
import com.nuvio.app.core.ui.NuvioSectionLabel
import com.nuvio.app.core.ui.NuvioStatusModal
import com.nuvio.app.core.ui.NuvioToastController
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.PlatformBackHandler
import com.nuvio.app.core.ui.nuvioTypeScale
import com.nuvio.app.features.watched.WatchedRepository
import com.nuvio.app.features.watchprogress.WatchProgressRepository
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.action_cancel
import nuvio.composeapp.generated.resources.action_delete
import nuvio.composeapp.generated.resources.action_delete_confirm_message
import nuvio.composeapp.generated.resources.compose_settings_page_root
import nuvio.composeapp.generated.resources.compose_settings_root_downloads_title
import nuvio.composeapp.generated.resources.downloads_delete_message
import nuvio.composeapp.generated.resources.downloads_delete_title
import nuvio.composeapp.generated.resources.downloads_empty_message
import nuvio.composeapp.generated.resources.downloads_empty_title
import nuvio.composeapp.generated.resources.downloads_episodes
import nuvio.composeapp.generated.resources.downloads_open_directory
import nuvio.composeapp.generated.resources.downloads_open_directory_failed
import nuvio.composeapp.generated.resources.downloads_pause_all
import nuvio.composeapp.generated.resources.downloads_resume_all
import nuvio.composeapp.generated.resources.downloads_section_active
import nuvio.composeapp.generated.resources.downloads_section_downloaded
import nuvio.composeapp.generated.resources.downloads_show_downloads
import nuvio.composeapp.generated.resources.downloads_titles
import nuvio.composeapp.generated.resources.downloads_watched_count
import nuvio.composeapp.generated.resources.episodes_season
import nuvio.composeapp.generated.resources.episodes_specials
import org.jetbrains.compose.resources.pluralStringResource
import org.jetbrains.compose.resources.stringResource

@Composable
fun DownloadsScreen(
    onBack: (() -> Unit)? = null,
    onOpenDownload: (DownloadItem) -> Unit,
    onOpenDetails: (DownloadItem) -> Unit,
    initialShowId: String? = null,
    onNavigateToShow: ((showId: String, title: String) -> Unit)? = null,
    onBackFromShow: (() -> Unit)? = null,
    onOpenSettings: (() -> Unit)? = null,
) {
    val uiState by remember {
        DownloadsRepository.ensureLoaded()
        DownloadsRepository.uiState
    }.collectAsStateWithLifecycle()
    val watchProgressState by remember {
        WatchProgressRepository.ensureLoaded()
        WatchProgressRepository.uiState
    }.collectAsStateWithLifecycle()
    val watchedState by remember {
        WatchedRepository.ensureLoaded()
        WatchedRepository.uiState
    }.collectAsStateWithLifecycle()
    LaunchedEffect(uiState.completedItems.size) {
        DownloadsRepository.markCompletedSeen()
    }

    var selectedShowId by rememberSaveable(initialShowId) { mutableStateOf(initialShowId) }
    var selectedLocalSeriesKey by rememberSaveable { mutableStateOf<String?>(null) }
    var actionsItemId by rememberSaveable { mutableStateOf<String?>(null) }
    var deleteItemId by rememberSaveable { mutableStateOf<String?>(null) }
    val localState by LocalFolderVideosPlatform.state.collectAsStateWithLifecycle()
    var viewFilter by rememberSaveable { mutableStateOf("all") }
    var selectedLocalFolderUri by rememberSaveable { mutableStateOf<String?>(null) }
    val visibleLocalVideos = remember(localState.videos, selectedLocalFolderUri) {
        if (selectedLocalFolderUri == null) localState.videos
        else localState.videos.filter { it.folderUri == selectedLocalFolderUri }
    }
    val (localSeriesGroups, localMovies) = remember(visibleLocalVideos) {
        LocalMediaParser.groupVideos(visibleLocalVideos)
    }
    val activeLocalSeries = remember(selectedLocalSeriesKey, localSeriesGroups) {
        selectedLocalSeriesKey?.let { key -> localSeriesGroups.firstOrNull { it.key == key } }
    }
    val playLocalVideo: (LocalVideoFileItem) -> Unit = { video ->
        val matchingSeries = if (video.isSeries) {
            localSeriesGroups.firstOrNull { grp ->
                grp.key == (video.seriesKey ?: LocalMediaParser.canonicalSeriesKey(video.title)) ||
                    grp.episodes.any { it.uri == video.uri }
            }
        } else null
        if (matchingSeries != null) {
            LocalEpisodePlaylistRegistry.registerFromItems(video.effectiveParentMetaId, matchingSeries.episodes)
        }
        val resolvedEntry = matchingSeries?.let {
            LocalEpisodePlaylistRegistry.findEpisode(
                parentMetaId = video.effectiveParentMetaId,
                activeSourceUrl = video.uri,
                videoId = video.syntheticVideoId,
            )
        }
        AppDeepLinkRepository.openLocalVideo(
            uri = video.uri,
            title = video.title,
            filename = video.filename,
            subtitle = video.folderName,
            mimeType = video.mimeType,
            poster = video.posterUrl,
            background = video.backgroundUrl,
            seasonNumber = resolvedEntry?.seasonNumber ?: (if (video.isSeries) (video.seasonNumber ?: 1) else video.seasonNumber),
            episodeNumber = resolvedEntry?.episodeNumber ?: (if (video.isSeries) (video.episodeNumber ?: 1) else video.episodeNumber),
            episodeTitle = video.episodeTitle,
            episodeThumbnail = video.episodeThumbnailUrl,
            contentType = if (video.isSeries) "series" else "movie",
            parentMetaId = video.effectiveParentMetaId,
            parentMetaType = if (video.isSeries) "series" else "movie",
            sidecarSubtitles = video.sidecarSubtitles,
        )
    }
    val speeds = rememberDownloadSpeeds(uiState.items)
    val watchStatusOf = remember(watchProgressState, watchedState) {
        { item: DownloadItem -> item.watchStatus(watchProgressState) }
    }
    val selectedShowTitle = remember(selectedShowId, uiState.items) {
        selectedShowId?.let { showId ->
            uiState.items.firstOrNull { it.isEpisode && it.parentMetaId == showId }?.title
        }
    }
    val onOpenActions: (DownloadItem) -> Unit = { actionsItemId = it.id }

    PlatformBackHandler(enabled = selectedLocalSeriesKey != null || (selectedShowId != null && onBackFromShow == null)) {
        if (selectedLocalSeriesKey != null) {
            selectedLocalSeriesKey = null
        } else {
            selectedShowId = null
        }
    }

    NuvioScreen {
        stickyHeader {
            NuvioScreenHeader(
                title = when {
                    activeLocalSeries != null -> activeLocalSeries.title
                    selectedShowId != null -> selectedShowTitle ?: stringResource(Res.string.downloads_show_downloads)
                    else -> stringResource(Res.string.compose_settings_root_downloads_title)
                },
                onBack = when {
                    selectedLocalSeriesKey != null -> ({ selectedLocalSeriesKey = null })
                    selectedShowId != null -> ({ onBackFromShow?.invoke() ?: run { selectedShowId = null } })
                    else -> onBack
                },
                actions = {
                    OpenDownloadsFolderButton(tint = MaterialTheme.nuvio.colors.textPrimary)
                    if (selectedShowId == null && activeLocalSeries == null && onOpenSettings != null) {
                        IconButton(onClick = onOpenSettings) {
                            Icon(
                                imageVector = Icons.Rounded.Settings,
                                contentDescription = stringResource(Res.string.compose_settings_page_root),
                                tint = MaterialTheme.nuvio.colors.textPrimary,
                            )
                        }
                    }
                },
            )
        }

        val showId = selectedShowId
        if (activeLocalSeries != null) {
            localSeriesShowContent(
                series = activeLocalSeries,
                watchProgressState = watchProgressState,
                onPlayEpisode = playLocalVideo,
            )
        } else if (showId == null) {
            downloadsRootContent(
                items = uiState.items,
                localState = localState,
                localSeriesGroups = localSeriesGroups,
                localMovies = localMovies,
                watchProgressState = watchProgressState,
                viewFilter = viewFilter,
                onViewFilterChange = { viewFilter = it },
                selectedLocalFolderUri = selectedLocalFolderUri,
                onSelectLocalFolderUri = { selectedLocalFolderUri = it },
                onAddLocalFolder = { LocalFolderVideosPlatform.addFolder() },
                onRemoveLocalFolder = { uri ->
                    if (selectedLocalFolderUri == uri) selectedLocalFolderUri = null
                    LocalFolderVideosPlatform.removeFolder(uri)
                },
                onPickSingleVideo = { LocalFolderVideosPlatform.pickAndPlaySingleVideo() },
                onRefreshLocalFolders = { LocalFolderVideosPlatform.refresh() },
                onOpenLocalSeries = { series -> selectedLocalSeriesKey = series.key },
                onPlayLocalVideo = playLocalVideo,
                speeds = speeds,
                watchStatusOf = watchStatusOf,
                onPlay = onOpenDownload,
                onOpenShow = { item ->
                    onNavigateToShow?.invoke(item.parentMetaId, item.title) ?: run { selectedShowId = item.parentMetaId }
                },
                onOpenActions = onOpenActions,
            )
        } else {
            downloadsShowContent(
                episodes = uiState.items
                    .filter { it.isEpisode && it.parentMetaId == showId }
                    .sortedForSeriesDownloads(),
                speeds = speeds,
                watchStatusOf = watchStatusOf,
                onPlay = onOpenDownload,
                onOpenActions = onOpenActions,
            )
        }
    }

    val actionsItem = actionsItemId?.let { id -> uiState.items.firstOrNull { it.id == id } }
    DownloadActionSheet(
        item = actionsItem,
        watchStatus = actionsItem?.let(watchStatusOf) ?: DownloadWatchStatus(),
        onDismiss = { actionsItemId = null },
        onPlay = { actionsItem?.let(onOpenDownload) },
        onToggleTransfer = { actionsItem?.toggleTransfer() },
        onOpenDetails = { actionsItem?.let(onOpenDetails) },
        onDelete = { deleteItemId = actionsItem?.id },
    )

    val deleteItem = deleteItemId?.let { id -> uiState.items.firstOrNull { it.id == id } }
    if (deleteItem != null) {
        DeleteDownloadDialog(
            item = deleteItem,
            onConfirm = {
                DownloadsRepository.cancelDownload(deleteItem.id)
                deleteItemId = null
            },
            onDismiss = { deleteItemId = null },
        )
    }
}

private fun LazyListScope.downloadsRootContent(
    items: List<DownloadItem>,
    localState: LocalFolderVideosState,
    localSeriesGroups: List<LocalSeriesGroup>,
    localMovies: List<LocalVideoFileItem>,
    watchProgressState: com.nuvio.app.features.watchprogress.WatchProgressUiState,
    viewFilter: String,
    onViewFilterChange: (String) -> Unit,
    selectedLocalFolderUri: String?,
    onSelectLocalFolderUri: (String?) -> Unit,
    onAddLocalFolder: () -> Unit,
    onRemoveLocalFolder: (String) -> Unit,
    onPickSingleVideo: () -> Unit,
    onRefreshLocalFolders: () -> Unit,
    onOpenLocalSeries: (LocalSeriesGroup) -> Unit,
    onPlayLocalVideo: (LocalVideoFileItem) -> Unit,
    speeds: Map<String, Long>,
    watchStatusOf: (DownloadItem) -> DownloadWatchStatus,
    onPlay: (DownloadItem) -> Unit,
    onOpenShow: (DownloadItem) -> Unit,
    onOpenActions: (DownloadItem) -> Unit,
) {
    val localTitlesCount = localSeriesGroups.size + localMovies.size
    if (localState.isSupported) {
        item(key = "local-folders-toolbar") {
            LocalFoldersToolbar(
                viewFilter = viewFilter,
                appDownloadsCount = items.size,
                localTitlesCount = localTitlesCount,
                folders = localState.folders,
                selectedFolderUri = selectedLocalFolderUri,
                isScanning = localState.isScanning,
                onViewFilterChange = onViewFilterChange,
                onSelectFolderUri = onSelectLocalFolderUri,
                onAddFolder = onAddLocalFolder,
                onRemoveFolder = onRemoveLocalFolder,
                onPickSingleVideo = onPickSingleVideo,
                onRefresh = onRefreshLocalFolders,
            )
        }
    }

    val showAppDownloads = !localState.isSupported || viewFilter == "all" || viewFilter == "app"
    val showLocalFolders = localState.isSupported && (viewFilter == "all" || viewFilter == "local")

    if (showLocalFolders && (localSeriesGroups.isNotEmpty() || localMovies.isNotEmpty())) {
        if (localSeriesGroups.isNotEmpty()) {
            item(key = "header-local-series") {
                SectionHeader(
                    title = "Local Series",
                    detail = "${localSeriesGroups.size} ${if (localSeriesGroups.size == 1) "show" else "shows"}",
                )
            }
            items(localSeriesGroups, key = { "local_series:${it.key}" }) { series ->
                LocalSeriesRow(
                    series = series,
                    onOpen = { onOpenLocalSeries(series) },
                )
            }
        }

        if (localMovies.isNotEmpty()) {
            item(key = "header-local-movies") {
                SectionHeader(
                    title = "Local Movies",
                    detail = "${localMovies.size} ${if (localMovies.size == 1) "movie" else "movies"}",
                )
            }
            items(localMovies, key = { "local_movie:${it.id}" }) { movie ->
                val progress = watchProgressState.progressForVideo(
                    videoId = movie.syntheticVideoId,
                    parentMetaId = movie.effectiveParentMetaId,
                )
                LocalMovieRow(
                    movie = movie,
                    progressFraction = progress?.progressFraction ?: 0f,
                    isCompleted = progress?.isEffectivelyCompleted == true,
                    onPlay = { onPlayLocalVideo(movie) },
                )
            }
        }
    } else if (localState.isSupported && viewFilter == "local" && !localState.isScanning) {
        item(key = "local-empty") {
            DownloadsEmptyState(
                title = if (localState.folders.isEmpty()) "No Android folders added yet" else "No video files found",
                message = if (localState.folders.isEmpty()) {
                    "Tap '+ Add Folder' above to automatically organize phone videos into Movies & Series with posters, or 'Open Video' for a single file."
                } else {
                    "No playable video files (.mp4, .mkv, .avi, .webm, .mov, .ts) were found in the selected folder."
                },
            )
        }
    }

    if (!showAppDownloads) return

    if (items.isEmpty()) {
        if (!showLocalFolders || (localSeriesGroups.isEmpty() && localMovies.isEmpty())) {
            item(key = "empty") {
                DownloadsEmptyState(
                    title = stringResource(Res.string.downloads_empty_title),
                    message = stringResource(Res.string.downloads_empty_message),
                )
            }
        }
        return
    }

    val activeItems = items.filter { it.status != DownloadStatus.Completed }
    val entries = items.downloadedEntries()

    item(key = "summary") {
        val titleCount = items.distinctBy { it.parentMetaId }.size
        SummaryText(
            listOf(
                pluralStringResource(Res.plurals.downloads_titles, titleCount, titleCount),
                formatBytes(items.sumOf { it.sizeOnDiskBytes }),
            ),
        )
    }

    if (activeItems.isNotEmpty()) {
        item(key = "active_header") {
            val hasDownloading = activeItems.any { it.status == DownloadStatus.Downloading }
            val hasPaused = activeItems.any { it.status == DownloadStatus.Paused }
            SectionHeader(
                title = stringResource(Res.string.downloads_section_active),
                actionText = when {
                    activeItems.size < 2 -> null
                    hasDownloading -> stringResource(Res.string.downloads_pause_all)
                    hasPaused -> stringResource(Res.string.downloads_resume_all)
                    else -> null
                },
                onAction = {
                    if (hasDownloading) {
                        DownloadsRepository.pauseActiveDownloads()
                    } else {
                        DownloadsRepository.resumePausedDownloads()
                    }
                },
            )
        }
        items(items = activeItems, key = { it.id }) { item ->
            ActiveDownloadRow(
                item = item,
                speedBytesPerSecond = speeds[item.id],
                inShowPage = false,
                onToggle = item::toggleTransfer,
                onOpenActions = { onOpenActions(item) },
            )
        }
    }

    if (entries.isNotEmpty()) {
        item(key = "downloaded_header") {
            SectionHeader(title = stringResource(Res.string.downloads_section_downloaded))
        }
        items(items = entries, key = { it.key }) { entry ->
            when (entry) {
                is DownloadedEntry.Movie -> DownloadedMovieRow(
                    item = entry.item,
                    watchStatus = watchStatusOf(entry.item),
                    onPlay = { onPlay(entry.item) },
                    onOpenActions = { onOpenActions(entry.item) },
                )
                is DownloadedEntry.Show -> DownloadedShowRow(
                    cover = entry.episodes.first(),
                    episodeCount = entry.episodes.size,
                    sizeBytes = entry.episodes.sumOf { it.sizeOnDiskBytes },
                    downloadingCount = entry.downloadingCount,
                    onOpen = { onOpenShow(entry.episodes.first()) },
                )
            }
        }
    }

    item(key = "downloads_device_storage_bar") {
        DeviceStorageBar(
            appDownloadsBytes = items.sumOf { it.downloadedBytes },
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 12.dp),
        )
    }
}

private fun LazyListScope.downloadsShowContent(
    episodes: List<DownloadItem>,
    speeds: Map<String, Long>,
    watchStatusOf: (DownloadItem) -> DownloadWatchStatus,
    onPlay: (DownloadItem) -> Unit,
    onOpenActions: (DownloadItem) -> Unit,
) {
    if (episodes.isEmpty()) {
        item(key = "empty") {
            DownloadsEmptyState(title = stringResource(Res.string.downloads_empty_title))
        }
        return
    }

    item(key = "summary") {
        val watchedCount = episodes.count { watchStatusOf(it).isWatched }
        SummaryText(
            listOfNotNull(
                pluralStringResource(Res.plurals.downloads_episodes, episodes.size, episodes.size),
                formatBytes(episodes.sumOf { it.sizeOnDiskBytes }),
                stringResource(Res.string.downloads_watched_count, watchedCount).takeIf { watchedCount > 0 },
            ),
        )
    }

    episodes
        .groupBy { it.seasonNumber ?: 0 }
        .toList()
        .sortedBy { (season, _) -> season }
        .forEach { (season, seasonEpisodes) ->
            item(key = "season_$season") {
                SectionHeader(
                    title = if (season == 0) {
                        stringResource(Res.string.episodes_specials)
                    } else {
                        stringResource(Res.string.episodes_season, season)
                    },
                    detail = listOf(
                        pluralStringResource(Res.plurals.downloads_episodes, seasonEpisodes.size, seasonEpisodes.size),
                        formatBytes(seasonEpisodes.sumOf { it.sizeOnDiskBytes }),
                    ).joinToString(DownloadTextSeparator),
                )
            }
            items(items = seasonEpisodes, key = { it.id }) { item ->
                if (item.status == DownloadStatus.Completed) {
                    DownloadedEpisodeRow(
                        item = item,
                        watchStatus = watchStatusOf(item),
                        onPlay = { onPlay(item) },
                        onOpenActions = { onOpenActions(item) },
                    )
                } else {
                    ActiveDownloadRow(
                        item = item,
                        speedBytesPerSecond = speeds[item.id],
                        inShowPage = true,
                        onToggle = item::toggleTransfer,
                        onOpenActions = { onOpenActions(item) },
                    )
                }
            }
        }
}

@Composable
private fun SummaryText(parts: List<String>) {
    Text(
        text = parts.joinToString(DownloadTextSeparator),
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.nuvio.colors.textSecondary,
    )
}

@Composable
private fun SectionHeader(
    title: String,
    detail: String? = null,
    actionText: String? = null,
    onAction: () -> Unit = {},
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = NuvioTokens.Space.s8),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        NuvioSectionLabel(text = title)
        when {
            actionText != null -> NuvioActionLabel(text = actionText, onClick = onAction)
            detail != null -> Text(
                text = detail,
                style = MaterialTheme.nuvioTypeScale.bodySm,
                color = MaterialTheme.nuvio.colors.textMuted,
            )
        }
    }
}

@Composable
private fun DownloadsEmptyState(
    title: String,
    message: String? = null,
) {
    val tokens = MaterialTheme.nuvio
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = NuvioTokens.Space.s24, vertical = NuvioTokens.Space.s64),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s8),
    ) {
        Box(
            modifier = Modifier
                .padding(bottom = NuvioTokens.Space.s8)
                .size(NuvioTokens.Space.s64)
                .clip(tokens.shapes.avatar)
                .background(tokens.colors.surfaceCard),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Rounded.Download,
                contentDescription = null,
                tint = tokens.colors.textMuted,
                modifier = Modifier.size(NuvioTokens.Icon.xl),
            )
        }
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            color = tokens.colors.textPrimary,
            textAlign = TextAlign.Center,
        )
        if (message != null) {
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = tokens.colors.textMuted,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun DeleteDownloadDialog(
    item: DownloadItem,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    val name = listOfNotNull(item.title, item.episodeCode()).joinToString(" ")
    val sizeBytes = item.sizeOnDiskBytes
    NuvioStatusModal(
        title = stringResource(Res.string.downloads_delete_title, name),
        message = if (sizeBytes > 0L) {
            stringResource(Res.string.downloads_delete_message, formatBytes(sizeBytes))
        } else {
            stringResource(Res.string.action_delete_confirm_message)
        },
        isVisible = true,
        destructive = true,
        confirmText = stringResource(Res.string.action_delete),
        dismissText = stringResource(Res.string.action_cancel),
        onConfirm = onConfirm,
        onDismiss = onDismiss,
    )
}

private sealed interface DownloadedEntry {
    val key: String
    val addedAtEpochMs: Long

    data class Movie(val item: DownloadItem) : DownloadedEntry {
        override val key: String get() = item.id
        override val addedAtEpochMs: Long get() = item.createdAtEpochMs
    }

    data class Show(
        val episodes: List<DownloadItem>,
        val downloadingCount: Int,
    ) : DownloadedEntry {
        override val key: String get() = "show:${episodes.first().parentMetaId}"
        override val addedAtEpochMs: Long get() = episodes.maxOf { it.createdAtEpochMs }
    }
}

private fun List<DownloadItem>.downloadedEntries(): List<DownloadedEntry> {
    val completed = filter { it.status == DownloadStatus.Completed }
    val downloadingByShow = filter { it.isEpisode && it.status != DownloadStatus.Completed }
        .groupingBy { it.parentMetaId }
        .eachCount()
    val movies = completed
        .filterNot { it.isEpisode }
        .map { DownloadedEntry.Movie(it) }
    val shows = completed
        .filter { it.isEpisode }
        .groupBy { it.parentMetaId }
        .map { (showId, episodes) ->
            DownloadedEntry.Show(
                episodes = episodes.sortedForSeriesDownloads(),
                downloadingCount = downloadingByShow[showId] ?: 0,
            )
        }
    return (movies + shows).sortedByDescending { it.addedAtEpochMs }
}

private fun DownloadItem.toggleTransfer() {
    when (status) {
        DownloadStatus.Downloading, DownloadStatus.Queued -> DownloadsRepository.pauseDownload(id)
        DownloadStatus.Paused, DownloadStatus.Failed -> DownloadsRepository.resumeDownload(id)
        DownloadStatus.Completed -> Unit
    }
}


private fun LazyListScope.localSeriesShowContent(
    series: LocalSeriesGroup,
    watchProgressState: com.nuvio.app.features.watchprogress.WatchProgressUiState,
    onPlayEpisode: (LocalVideoFileItem) -> Unit,
) {
    val episodes = series.episodes
    val watchedCount = episodes.count { ep ->
        watchProgressState.progressForVideo(
            videoId = ep.syntheticVideoId,
            parentMetaId = ep.effectiveParentMetaId,
            seasonNumber = ep.seasonNumber,
            episodeNumber = ep.episodeNumber,
        )?.isEffectivelyCompleted == true
    }

    item(key = "local_series_summary") {
        SummaryText(
            listOfNotNull(
                series.year?.toString(),
                pluralStringResource(Res.plurals.downloads_episodes, episodes.size, episodes.size),
                formatBytes(series.totalSizeBytes).takeIf { series.totalSizeBytes > 0L },
                stringResource(Res.string.downloads_watched_count, watchedCount).takeIf { watchedCount > 0 },
            ),
        )
    }

    episodes
        .groupBy { it.seasonNumber ?: 1 }
        .toList()
        .sortedBy { (season, _) -> season }
        .forEach { (season, seasonEpisodes) ->
            item(key = "local_season_$season") {
                SectionHeader(
                    title = if (season == 0) {
                        stringResource(Res.string.episodes_specials)
                    } else {
                        stringResource(Res.string.episodes_season, season)
                    },
                    detail = listOfNotNull(
                        pluralStringResource(Res.plurals.downloads_episodes, seasonEpisodes.size, seasonEpisodes.size),
                        seasonEpisodes.sumOf { it.sizeBytes }.takeIf { it > 0L }?.let(::formatBytes),
                    ).joinToString(DownloadTextSeparator),
                )
            }
            items(
                items = seasonEpisodes,
                key = { "local_ep:${it.id}" },
            ) { episode ->
                val progress = watchProgressState.progressForVideo(
                    videoId = episode.syntheticVideoId,
                    parentMetaId = episode.effectiveParentMetaId,
                    seasonNumber = episode.seasonNumber,
                    episodeNumber = episode.episodeNumber,
                )
                LocalSeriesEpisodeRow(
                    episode = episode,
                    fallbackLandscapeUrl = series.backgroundUrl ?: series.posterUrl,
                    progressFraction = progress?.progressFraction ?: 0f,
                    isCompleted = progress?.isEffectivelyCompleted == true,
                    onPlay = { onPlayEpisode(episode) },
                )
            }
        }
}

@Composable
private fun LocalFoldersToolbar(
    viewFilter: String,
    appDownloadsCount: Int,
    localTitlesCount: Int,
    folders: List<LocalVideoFolder>,
    selectedFolderUri: String?,
    isScanning: Boolean,
    onViewFilterChange: (String) -> Unit,
    onSelectFolderUri: (String?) -> Unit,
    onAddFolder: () -> Unit,
    onRemoveFolder: (String) -> Unit,
    onPickSingleVideo: () -> Unit,
    onRefresh: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            listOf(
                "all" to "All (${appDownloadsCount + localTitlesCount})",
                "app" to "App Downloads ($appDownloadsCount)",
                "local" to "Local Media ($localTitlesCount)",
            ).forEach { (key, label) ->
                val selected = viewFilter == key
                Surface(
                    shape = RoundedCornerShape(NuvioTokens.Radius.full),
                    color = if (selected) tokens.colors.accent.copy(alpha = 0.2f) else tokens.colors.surfaceCard,
                    border = BorderStroke(
                        width = 1.dp,
                        color = if (selected) tokens.colors.accent else tokens.colors.borderSubtle,
                    ),
                    modifier = Modifier.clickable { onViewFilterChange(key) },
                ) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
                        color = if (selected) tokens.colors.accent else tokens.colors.textSecondary,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                    )
                }
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                shape = RoundedCornerShape(NuvioTokens.Radius.md),
                color = tokens.colors.surfaceCard,
                border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                modifier = Modifier.clickable(onClick = onAddFolder),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Add,
                        contentDescription = null,
                        tint = tokens.colors.accent,
                        modifier = Modifier.size(16.dp),
                    )
                    Spacer(Modifier.width(5.dp))
                    Icon(
                        imageVector = Icons.Rounded.Folder,
                        contentDescription = null,
                        tint = tokens.colors.textPrimary,
                        modifier = Modifier.size(15.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = "Add Folder",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.textPrimary,
                    )
                }
            }

            Surface(
                shape = RoundedCornerShape(NuvioTokens.Radius.md),
                color = tokens.colors.surfaceCard,
                border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                modifier = Modifier.clickable(onClick = onPickSingleVideo),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Movie,
                        contentDescription = null,
                        tint = tokens.colors.accent,
                        modifier = Modifier.size(15.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = "Open Video",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.textPrimary,
                    )
                }
            }

            if (folders.isNotEmpty() || isScanning) {
                Surface(
                    shape = RoundedCornerShape(NuvioTokens.Radius.md),
                    color = tokens.colors.surfaceCard,
                    border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                    modifier = Modifier.clickable(onClick = onRefresh),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Refresh,
                            contentDescription = "Refresh local folders",
                            tint = tokens.colors.textSecondary,
                            modifier = Modifier.size(15.dp),
                        )
                        Spacer(Modifier.width(5.dp))
                        Text(
                            text = if (isScanning) "Syncing Posters..." else "Refresh",
                            style = MaterialTheme.typography.labelMedium,
                            color = tokens.colors.textSecondary,
                        )
                    }
                }
            }
        }

        if (folders.isNotEmpty()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (folders.size > 1) {
                    val allSelected = selectedFolderUri == null
                    Surface(
                        shape = RoundedCornerShape(NuvioTokens.Radius.sm),
                        color = if (allSelected) tokens.colors.accent.copy(alpha = 0.18f) else tokens.colors.surfaceCard,
                        border = BorderStroke(1.dp, if (allSelected) tokens.colors.accent else tokens.colors.borderSubtle),
                        modifier = Modifier.clickable { onSelectFolderUri(null) },
                    ) {
                        Text(
                            text = "All Folders",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (allSelected) tokens.colors.accent else tokens.colors.textPrimary,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
                        )
                    }
                }
                folders.forEach { folder ->
                    val selected = selectedFolderUri == folder.treeUri
                    Surface(
                        shape = RoundedCornerShape(NuvioTokens.Radius.sm),
                        color = if (selected) tokens.colors.accent.copy(alpha = 0.18f) else tokens.colors.surfaceCard,
                        border = BorderStroke(1.dp, if (selected) tokens.colors.accent else tokens.colors.borderSubtle),
                        modifier = Modifier.clickable {
                            onSelectFolderUri(if (selected) null else folder.treeUri)
                        },
                    ) {
                        Row(
                            modifier = Modifier.padding(start = 9.dp, end = 6.dp, top = 5.dp, bottom = 5.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.Folder,
                                contentDescription = null,
                                tint = tokens.colors.textSecondary,
                                modifier = Modifier.size(13.dp),
                            )
                            Spacer(Modifier.width(5.dp))
                            Text(
                                text = folder.displayName,
                                style = MaterialTheme.typography.labelSmall,
                                color = tokens.colors.textPrimary,
                            )
                            Spacer(Modifier.width(4.dp))
                            Icon(
                                imageVector = Icons.Rounded.Close,
                                contentDescription = "Remove ${folder.displayName}",
                                tint = tokens.colors.textMuted,
                                modifier = Modifier
                                    .size(14.dp)
                                    .clickable { onRemoveFolder(folder.treeUri) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LocalMovieRow(
    movie: LocalVideoFileItem,
    progressFraction: Float,
    isCompleted: Boolean,
    onPlay: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    val subtitle = listOfNotNull(
        stringResource(Res.string.media_movie),
        movie.year?.toString(),
        movie.extensionLabel,
        movie.sizeBytes.takeIf { it > 0L }?.let(::formatBytes),
    ).joinToString(DownloadTextSeparator)

    val statusLabel = when {
        isCompleted -> "Watched"
        progressFraction > 0.02f -> "${(progressFraction * 100).toInt()}% watched • ${movie.folderName}"
        else -> movie.folderName
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onPlay),
        horizontalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s12),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        NuvioPosterCard(
            title = movie.title,
            imageUrl = movie.posterUrl,
            fallbackImageUrl = movie.posterUrl,
            modifier = Modifier.width(NuvioTokens.Space.s48),
            showTitleBelow = false,
        )
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s2),
        ) {
            Text(
                text = movie.title,
                style = MaterialTheme.typography.titleMedium,
                color = tokens.colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.nuvioTypeScale.bodySm,
                color = tokens.colors.textSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = statusLabel,
                style = MaterialTheme.nuvioTypeScale.bodySm,
                color = if (isCompleted || progressFraction > 0.02f) tokens.colors.accent else tokens.colors.textMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        IconButton(onClick = onPlay) {
            Icon(
                imageVector = Icons.Rounded.PlayArrow,
                contentDescription = "Play ${movie.title}",
                tint = tokens.colors.accent,
            )
        }
    }
}

@Composable
private fun LocalSeriesRow(
    series: LocalSeriesGroup,
    onOpen: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    val seasonsLabel = "${series.seasonCount} ${if (series.seasonCount == 1) "Season" else "Seasons"}"
    val subtitle = listOfNotNull(
        stringResource(Res.string.media_series),
        series.year?.toString(),
        seasonsLabel,
        pluralStringResource(Res.plurals.downloads_episodes, series.episodes.size, series.episodes.size),
        series.totalSizeBytes.takeIf { it > 0L }?.let(::formatBytes),
    ).joinToString(DownloadTextSeparator)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen),
        horizontalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s12),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        NuvioPosterCard(
            title = series.title,
            imageUrl = series.posterUrl,
            fallbackImageUrl = series.posterUrl,
            modifier = Modifier.width(NuvioTokens.Space.s48),
            showTitleBelow = false,
        )
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s2),
        ) {
            Text(
                text = series.title,
                style = MaterialTheme.typography.titleMedium,
                color = tokens.colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.nuvioTypeScale.bodySm,
                color = tokens.colors.textSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Icon(
            imageVector = Icons.AutoMirrored.Rounded.KeyboardArrowRight,
            contentDescription = null,
            tint = tokens.colors.textMuted,
            modifier = Modifier.padding(horizontal = NuvioTokens.Space.s12),
        )
    }
}

@Composable
private fun LocalSeriesEpisodeRow(
    episode: LocalVideoFileItem,
    fallbackLandscapeUrl: String?,
    progressFraction: Float,
    isCompleted: Boolean,
    onPlay: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    val epCode = buildString {
        if (episode.seasonNumber != null && episode.episodeNumber != null) {
            append("S").append(episode.seasonNumber).append(":E").append(episode.episodeNumber)
        } else if (episode.episodeNumber != null) {
            append("E").append(episode.episodeNumber)
        }
    }
    val rowTitle = when {
        epCode.isNotBlank() && !episode.episodeTitle.isNullOrBlank() -> "$epCode • ${episode.episodeTitle}"
        epCode.isNotBlank() -> "$epCode • Episode ${episode.episodeNumber}"
        else -> episode.filename
    }
    val subtitle = listOfNotNull(
        episode.extensionLabel,
        episode.sizeBytes.takeIf { it > 0L }?.let(::formatBytes),
        when {
            isCompleted -> "Watched"
            progressFraction > 0.02f -> "${(progressFraction * 100).toInt()}%"
            else -> null
        },
        if (episode.sidecarSubtitles.isNotEmpty()) "CC" else null,
    ).joinToString(DownloadTextSeparator)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onPlay),
        horizontalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s12),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        DownloadThumbnail(
            imageUrl = episode.episodeThumbnailUrl ?: fallbackLandscapeUrl,
            watchProgress = if (isCompleted) 1f else progressFraction,
        )
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(NuvioTokens.Space.s2),
        ) {
            Text(
                text = rowTitle,
                style = MaterialTheme.typography.titleMedium,
                color = tokens.colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.nuvioTypeScale.bodySm,
                color = tokens.colors.textSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        IconButton(onClick = onPlay) {
            Icon(
                imageVector = Icons.Rounded.PlayArrow,
                contentDescription = "Play $rowTitle",
                tint = tokens.colors.accent,
            )
        }
    }
}
