package com.nuvio.app.features.cloudstream

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.mapNotNull
import kotlinx.coroutines.flow.update
import kotlin.time.TimeSource

internal data class CloudStreamLiveSnapshot(
    val providerId: String,
    val routeData: String,
    val sources: List<CloudStreamPlaybackSource>,
    val isComplete: Boolean,
    val revision: Long,
    val capturedMark: TimeSource.Monotonic.ValueTimeMark = TimeSource.Monotonic.markNow(),
) {
    fun isFresh(maxAgeMs: Long = 600_000L): Boolean =
        capturedMark.elapsedNow().inWholeMilliseconds <= maxAgeMs
}

/**
 * Lock-free, KMP-safe live stream hub bridging callback-based CloudStream `loadLinks`
 * scrapers (e.g. `StreamPlay` with 60+ internal extractors) to `StreamsRepository`
 * and `PlayerStreamsRepository` in real time.
 */
internal object CloudStreamLiveLinkHub {
    private const val MAX_SESSIONS = 48

    private val sessions = MutableStateFlow<Map<String, CloudStreamLiveSnapshot>>(emptyMap())
    private val forceRefreshKeys = MutableStateFlow<Set<String>>(emptySet())
    private val activePlayerLoads = MutableStateFlow(0)
    private val _playbackStartedSignals = MutableStateFlow(0L)
    val playbackStartedSignals: StateFlow<Long> = _playbackStartedSignals.asStateFlow()

    private fun sessionKey(providerId: String, routeData: String): String =
        "$providerId\u0000$routeData"

    fun publish(
        providerId: String,
        routeData: String,
        sources: List<CloudStreamPlaybackSource>,
        isComplete: Boolean,
    ) {
        if (sources.isEmpty() && !isComplete) return
        val key = sessionKey(providerId, routeData)
        sessions.update { current ->
            val previous = current[key]
            val mergedSources = if (sources.isNotEmpty()) {
                sources
            } else {
                previous?.sources.orEmpty()
            }
            if (mergedSources.isEmpty()) return@update current
            if (
                previous != null &&
                previous.sources.size == mergedSources.size &&
                previous.isComplete == isComplete &&
                previous.sources.lastOrNull()?.subtitles?.size == mergedSources.lastOrNull()?.subtitles?.size
            ) {
                return@update current
            }
            val next = LinkedHashMap<String, CloudStreamLiveSnapshot>(current.size + 1)
            next.putAll(current)
            next.remove(key)
            next[key] = CloudStreamLiveSnapshot(
                providerId = providerId,
                routeData = routeData,
                sources = mergedSources,
                isComplete = isComplete,
                revision = (previous?.revision ?: 0L) + 1L,
            )
            while (next.size > MAX_SESSIONS) {
                val eldest = next.keys.firstOrNull() ?: break
                next.remove(eldest)
            }
            next
        }
    }

    fun snapshot(providerId: String, routeData: String): CloudStreamLiveSnapshot? {
        val snap = sessions.value[sessionKey(providerId, routeData)] ?: return null
        return snap.takeIf { it.isFresh() }
    }

    fun observe(providerId: String, routeData: String): Flow<CloudStreamLiveSnapshot> {
        val key = sessionKey(providerId, routeData)
        return sessions
            .mapNotNull { map -> map[key]?.takeIf { it.isFresh() } }
            .distinctUntilChanged { a, b -> a.revision == b.revision }
    }

    fun invalidate(providerId: String, routeData: String) {
        val key = sessionKey(providerId, routeData)
        sessions.update { current ->
            if (key !in current) current else current - key
        }
        forceRefreshKeys.update { it + key }
    }

    fun consumeForceRefresh(providerId: String, routeData: String): Boolean {
        val key = sessionKey(providerId, routeData)
        var wasPresent = false
        forceRefreshKeys.update { current ->
            if (key in current) {
                wasPresent = true
                current - key
            } else {
                current
            }
        }
        return wasPresent
    }

    fun onPlayerLoadStarted() {
        activePlayerLoads.update { it + 1 }
    }

    fun onPlayerLoadFinished() {
        activePlayerLoads.update { (it - 1).coerceAtLeast(0) }
    }

    fun isPlayerLoadingActive(): Boolean = activePlayerLoads.value > 0

    fun notifyPlaybackStarted() {
        _playbackStartedSignals.update { it + 1L }
    }

    fun clearAll() {
        sessions.value = emptyMap()
        forceRefreshKeys.value = emptySet()
    }
}
