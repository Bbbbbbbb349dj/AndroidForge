package com.nuvio.app.features.player

import com.nuvio.app.features.streams.SmartStreamRanking
import com.nuvio.app.features.streams.SmartStreamSettingsRepository
import com.nuvio.app.features.streams.currentSmartDeviceProfile
import co.touchlab.kermit.Logger
import com.nuvio.app.features.addons.AddonRepository
import com.nuvio.app.features.addons.enabledAddons
import com.nuvio.app.features.debrid.DebridSettingsRepository
import com.nuvio.app.features.debrid.DirectDebridPlayableResult
import com.nuvio.app.features.debrid.DirectDebridPlaybackResolver
import com.nuvio.app.features.streams.StreamAutoPlaySelector
import com.nuvio.app.features.streams.StreamItem
import com.nuvio.app.isIos
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.time.Duration.Companion.seconds
import kotlin.time.TimeSource
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect

private const val SOURCE_FALLBACK_POLL_COUNT = 30
private const val SOURCE_FALLBACK_POLL_INTERVAL_MS = 500L

private val log = Logger.withTag("PlayerSourceFallback")

/**
 * Plays [stream] at [url] in place of the current source. Before playback has started the
 * pending resume position is kept, otherwise playback continues from the current position.
 */
internal fun PlayerScreenRuntime.playReplacementSource(stream: StreamItem, url: String, videoId: String) {
    if (playerSettingsUiState.streamReuseLastLinkEnabled) {
        saveDirectStreamForReuse(stream, url, videoId, activeSeasonNumber, activeEpisodeNumber)
    }
    if (activeSourceUrl == autoSelectedSourceUrl) autoSelectedSourceUrl = url
    if (initialLoadCompleted) {
        activeInitialPositionMs = playbackSnapshot.positionMs.coerceAtLeast(0L)
        activeInitialProgressFraction = null
    }
    flushWatchProgress()
    stopActiveP2pStream()
    externalSubtitles = stream.externalSubtitles
    activeSourceUrl = url
    activeSourceAudioUrl = null
    activeSourceHeaders = sanitizePlaybackHeaders(stream.behaviorHints.proxyHeaders?.request)
    activeSourceResponseHeaders = sanitizePlaybackResponseHeaders(stream.behaviorHints.proxyHeaders?.response)
    activeStreamType = stream.streamType
    activeSourceIdentityKey = stream.playerSourceIdentityKey() ?: activeSourceIdentityKey
    activeSourceFilename = stream.behaviorHints.filename
    activeStreamTitle = stream.streamLabel
    activeStreamSubtitle = stream.streamSubtitle
    activeStreamFilename = streamPlaybackFilename(stream, url)
    activeProviderName = stream.addonName
    activeProviderAddonId = stream.addonId
    activeStream = stream
    currentStreamBingeGroup = stream.behaviorHints.bingeGroup
    activeSubtitleExtras = SubtitleRequestExtras.from(stream.behaviorHints, url)
    currentStreamFilename = stream.behaviorHints.filename
    currentStreamInfoHash = stream.infoHash
    showSourcesPanel = false
    controlsVisible = true
}

/** Shows [message] as the playback error unless the next matching source is tried instead. */
internal fun PlayerScreenRuntime.showErrorUnlessSourceFallback(message: String?) {
    if (tryFallbackToNextSourceAfterError(message)) return
    errorMessage = message
    controlsVisible = !playerControlsLocked
}

/**
 * When the current source fails (before playback starts or mid-playback) or playback stalls,
 * quietly plays the next source that auto source selection would pick — with the configured
 * quality/language preferences applied by the rankings — up to the configured number of further
 * sources. Mid-playback fallbacks continue from the current position, and the failing source may
 * be auto-selected or manually picked. The engine switch on error is excluded.
 *
 * Returns `true` when a fallback was started and the error must not be shown yet.
 */
internal fun PlayerScreenRuntime.tryFallbackToNextSourceAfterError(message: String?): Boolean {
    if (sourceFallbackJob?.isActive == true) return true
    val settings = playerSettingsUiState
    // v1.20 Section 13: error/stall fallback engages on default installs — auto AND manual
    // streams — instead of requiring three opt-in settings (fallback toggle off by default,
    // engine-switch exclusion, MANUAL mode) to be flipped first.
    if (settings.externalPlayerEnabled) return false
    val failedUrl = activeSourceUrl
    // Nuvio Enhanced: never replace local/offline sources (file://, content://) — there is
    // nothing to fall back to, and slow local seeks must not trigger network source search.
    if (failedUrl.startsWith("file:") || failedUrl.startsWith("content:")) return false
    if (failedUrl.isBlank()) return false
    if (sourceFallbackAttempts >= settings.streamAutoPlayFallbackMaxSources) return false
    val videoId = activeVideoId ?: return false

    activeStream?.playerSourceIdentityKey()?.let(sourceFallbackTriedKeys::add)
    val failedInfoHash = activeStream?.p2pInfoHash ?: currentStreamInfoHash
    val failedAddonId = activeProviderAddonId
    val season = activeSeasonNumber
    val episode = activeEpisodeNumber
    errorMessage = null
    sourceFallbackStatus = "Switching to backup stream…"

    sourceFallbackJob = scope.launch {
        try {
            // Joins the shared source search, so results the stream screen already found are reused.
            PlayerStreamsRepository.loadSources(
                type = contentType ?: parentMetaType,
                videoId = videoId,
                parentMetaId = parentMetaId,
                parentMetaType = parentMetaType,
                season = season,
                episode = episode,
                searchTitle = playerMeta?.name ?: title,
            )
            var polls = 0
            while (sourceFallbackAttempts < playerSettingsUiState.streamAutoPlayFallbackMaxSources) {
                val state = PlayerStreamsRepository.sourceState.value
                val next = nextSourceFallbackCandidate(
                    streams = state.groups.flatMap { it.streams },
                    settings = playerSettingsUiState,
                    triedKeys = sourceFallbackTriedKeys,
                    failedAddonId = failedAddonId,
                    failedInfoHash = failedInfoHash,
                    isEpisode = season != null,
                )
                if (next == null) {
                    // Bail quickly when the shared search finished or produced nothing (~3s),
                    // so errors surface promptly instead of hiding behind 15s of polling.
                    val searchDone = state.emptyStateReason != null ||
                        (!state.isAnyLoading && state.groups.isNotEmpty()) ||
                        (!state.isAnyLoading && state.groups.isEmpty() && polls >= 6)
                    if (searchDone || polls >= SOURCE_FALLBACK_POLL_COUNT) break
                    delay(SOURCE_FALLBACK_POLL_INTERVAL_MS)
                    polls++
                    continue
                }
                next.playerSourceIdentityKey()?.let(sourceFallbackTriedKeys::add)
                sourceFallbackAttempts++

                val playable = when (
                    val resolved = DirectDebridPlaybackResolver.resolveToPlayableStream(next, season, episode)
                ) {
                    is DirectDebridPlayableResult.Success -> resolved.stream
                    else -> null
                }
                val url = playable?.playableDirectUrl
                if (playable == null || url.isNullOrBlank() || url == failedUrl) {
                    log.d { "Fallback source from ${next.addonName} has no playable link, trying the next one" }
                    continue
                }
                log.i { "Source failed to start, falling back to ${playable.streamLabel} from ${playable.addonName}" }
                playReplacementSource(playable, url, videoId)
                return@launch
            }
        } catch (cancelled: kotlinx.coroutines.CancellationException) {
            throw cancelled
        } catch (e: Exception) {
            log.w { "Source fallback recovery failed: ${e.message}" }
            // Fall through to the error display below instead of dying silently.
        } finally {
            PlayerStreamsRepository.stopSourcesLoading()
            sourceFallbackStatus = null
        }
        // The last source that failed may have been saved for reuse.
        removeFailedStreamFromCache()
        errorMessage = message
        controlsVisible = !playerControlsLocked
    }
    return true
}

/**
 * The best stream auto source selection would pick from [streams], leaving out the sources
 * already tried and other copies of the torrent that failed.
 */
internal fun nextSourceFallbackCandidate(
    streams: List<StreamItem>,
    settings: PlayerSettingsUiState,
    triedKeys: Set<String>,
    failedAddonId: String?,
    failedInfoHash: String?,
    installedAddonNames: Set<String> = AddonRepository.uiState.value.addons.enabledAddons().map { it.displayTitle }.toSet(),
    debridEnabled: Boolean = DebridSettingsRepository.snapshot().canResolvePlayableLinks,
    activeResolverProviderId: String? = DebridSettingsRepository.snapshot().activeResolverProviderId,
    isEpisode: Boolean = false,
): StreamItem? {
    val untried = streams.filterNot { stream ->
        val key = stream.playerSourceIdentityKey()
        (key != null && key in triedKeys) ||
            (failedInfoHash != null && stream.addonId == failedAddonId &&
                stream.p2pInfoHash.equals(failedInfoHash, ignoreCase = true))
    }
    val smartSettings = SmartStreamSettingsRepository.state.value
    if (smartSettings.autoPlay) {
        return SmartStreamRanking.rankForAutoPlay(
            streams = untried,
            settings = smartSettings,
            device = currentSmartDeviceProfile(),
            debridEnabled = debridEnabled,
            isEpisode = isEpisode,
        ).ranked.firstOrNull()?.stream
    }
    StreamAutoPlaySelector.evaluateAutoPlayStream(
        streams = untried,
        mode = settings.streamAutoPlayMode,
        regexPattern = settings.streamAutoPlayRegex,
        source = settings.streamAutoPlaySource,
        installedAddonNames = installedAddonNames,
        selectedAddons = settings.streamAutoPlaySelectedAddons,
        selectedPlugins = settings.streamAutoPlaySelectedPlugins,
        debridEnabled = debridEnabled,
        activeResolverProviderId = activeResolverProviderId,
    ).readyStreams.firstOrNull()?.let { return it }
    // v1.20: MANUAL mode yields no auto-selection candidates; still pick the best-ranked
    // backup (quality/language/device aware) so error fallback works on default installs.
    return SmartStreamRanking.rankForAutoPlay(
        streams = untried,
        settings = smartSettings,
        device = currentSmartDeviceProfile(),
        debridEnabled = debridEnabled,
        isEpisode = isEpisode,
    ).ranked.firstOrNull()?.stream
}

/**
 * Nuvio Enhanced (v1.20): sustained-stall watchdog. When playback should be running but the
 * position makes no progress for [STALL_THRESHOLD], quietly fall back to the next source.
 */
@Composable
internal fun PlayerScreenRuntime.BindSourceFallbackStallWatchdog() {
    LaunchedEffect(Unit) {
        val timeSource = TimeSource.Monotonic
        var lastPositionMs = playbackSnapshot.positionMs
        var lastBufferedMs = playbackSnapshot.bufferedPositionMs
        var lastProgressAt = timeSource.markNow()
        while (true) {
            delay(STALL_POLL_INTERVAL)
            val snapshot = playbackSnapshot
            // Buffering progress (e.g. slow CloudStream HLS start) is NOT a stall — only a
            // frozen position with a frozen buffer counts, so working streams are never swapped.
            val bufferAdvanced = snapshot.bufferedPositionMs > lastBufferedMs
            lastBufferedMs = snapshot.bufferedPositionMs
            if (snapshot.positionMs != lastPositionMs || bufferAdvanced) {
                lastPositionMs = snapshot.positionMs
                lastProgressAt = timeSource.markNow()
                continue
            }
            val shouldCurrentlyPlay = shouldPlay &&
                !snapshot.isEnded &&
                !snapshot.isLoading &&
                !snapshot.isOpening
            if (!shouldCurrentlyPlay || errorMessage != null || sourceFallbackStatus != null) {
                lastProgressAt = timeSource.markNow()
                continue
            }
            if (lastProgressAt.elapsedNow() >= STALL_THRESHOLD) {
                // One probe per interval; the fallback's own gates decide applicability.
                tryFallbackToNextSourceAfterError("Playback stalled — trying a backup stream")
                lastProgressAt = timeSource.markNow()
                lastPositionMs = playbackSnapshot.positionMs
            }
        }
    }
}

private val STALL_POLL_INTERVAL = 2_000L
private val STALL_THRESHOLD = 12.seconds
