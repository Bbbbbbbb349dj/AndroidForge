#!/usr/bin/env python3
"""Nuvio Enhanced v1.17 Enhancements:
1. Progressive real-time CloudStream source display (`StreamPlay`, etc.) until playback starts.
2. Full CloudStream support inside `Player > Source` (and Episode Streams / Auto-Fallback / Next Episode).
3. Smart CloudStream speed optimizations without reducing link count (plugin pre-warming,
   smart `provider_concurrency = 24` default, fast non-blocking HLS variant handling,
   expanded route indexing, and tuned HTTP dead-mirror timeouts).
4. Next Episode button + seamless episode switching for Local Storage folder seasons
   (both in-app Local Media library and direct 'Open with Nuvio' sibling folder playback).
5. App version bump to `1.17` (`versionCode = 170`).
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")
    if new and new in content:
        return False
    if old not in content:
        raise RuntimeError(f"Patch anchor missing for {label} in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return True


def _write_text(root: Path, rel_path: str, content: str, patched: list[str]) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    patched.append(rel_path)


def apply_v117_enhancements_patch(root: Path) -> list[str]:
    patched: list[str] = []

    # -------------------------------------------------------------------------
    # 1. Version 1.17 (versionCode 170) across gradle.properties & Version.xcconfig
    # -------------------------------------------------------------------------
    gradle_props = root / "gradle.properties"
    if gradle_props.is_file():
        if _replace_once(
            gradle_props,
            "nuvio.app.versionName=1.1.2\n",
            "nuvio.app.versionName=1.17\n",
            "gradle.properties versionName 1.17",
        ):
            patched.append(str(gradle_props.relative_to(root)))

    xcconfig = root / "iosApp/Configuration/Version.xcconfig"
    if xcconfig.is_file():
        changed = False
        changed |= _replace_once(
            xcconfig,
            "CURRENT_PROJECT_VERSION=161\n",
            "CURRENT_PROJECT_VERSION=170\n",
            "Version.xcconfig CURRENT_PROJECT_VERSION=170",
        )
        changed |= _replace_once(
            xcconfig,
            "MARKETING_VERSION=1.1.2\n",
            "MARKETING_VERSION=1.17\n",
            "Version.xcconfig MARKETING_VERSION=1.17",
        )
        if changed:
            patched.append(str(xcconfig.relative_to(root)))

    local_android_kt = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.android.kt"
    if local_android_kt.is_file():
        if _replace_once(
            local_android_kt,
            '.header("User-Agent", "NuvioEnhanced/1.1.2")',
            '.header("User-Agent", "NuvioEnhanced/1.17")',
            "LocalFolderVideosPlatform User-Agent 1.17",
        ):
            patched.append(str(local_android_kt.relative_to(root)))

    # -------------------------------------------------------------------------
    # 2. CloudStreamLiveLinkHub in commonMain (lock-free KMP live callback bus)
    # -------------------------------------------------------------------------
    _write_text(
        root,
        "composeApp/src/commonMain/kotlin/com/nuvio/app/features/cloudstream/CloudStreamLiveLinkHub.kt",
        r'''package com.nuvio.app.features.cloudstream

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
''',
        patched,
    )

    # -------------------------------------------------------------------------
    # 3. CloudStreamPlatformRuntime.android.kt:
    #    - Real-time CloudStreamLiveLinkHub.publish inside loadLinks callbacks
    #    - Smart default provider_concurrency = 24 for multi-scraper plugins (StreamPlay, etc.)
    #    - Route index population from getMainPage & search
    #    - Faster dead-mirror HTTP & discovery timeouts + higher sub-API concurrency
    # -------------------------------------------------------------------------
    cs_runtime = root / "composeApp/src/androidFull/kotlin/com/nuvio/app/features/cloudstream/CloudStreamPlatformRuntime.android.kt"
    if cs_runtime.is_file():
        changed = False
        changed |= _replace_once(
            cs_runtime,
            "    private fun applyHostCompatibilityDefaults(pluginClassName: String) {\n"
            "        if (pluginClassName != CINESTREAM_PLUGIN_CLASS) return\n"
            "        val preferences = getContext()?.getSharedPreferences(\n"
            "            com.lagradost.cloudstream3.utils.PREFERENCES_NAME,\n"
            "            Context.MODE_PRIVATE,\n"
            "        ) ?: return\n"
            "        if (preferences.getString(CINESTREAM_SIMKL_PROVIDER_KEY, null) != \"false\") {\n"
            "            CloudStreamApp.setKey(CINESTREAM_SIMKL_PROVIDER_KEY, false)\n"
            "        }\n"
            "    }\n",
            "    private fun applyHostCompatibilityDefaults(pluginClassName: String) {\n"
            "        val ctx = getContext() ?: return\n"
            "        if (pluginClassName == CINESTREAM_PLUGIN_CLASS) {\n"
            "            val preferences = ctx.getSharedPreferences(\n"
            "                com.lagradost.cloudstream3.utils.PREFERENCES_NAME,\n"
            "                Context.MODE_PRIVATE,\n"
            "            )\n"
            "            if (preferences.getString(CINESTREAM_SIMKL_PROVIDER_KEY, null) != \"false\") {\n"
            "                CloudStreamApp.setKey(CINESTREAM_SIMKL_PROVIDER_KEY, false)\n"
            "            }\n"
            "        }\n"
            "        // Seed smart high-throughput scraper concurrency (24) for multi-scraper extensions\n"
            "        // such as StreamPlay when the user has not explicitly customized provider_concurrency.\n"
            "        // All scrapers still execute (zero link reduction), finishing in ~2-3x fewer waves.\n"
            "        val loadingName = PluginManager.currentlyLoading\n"
            "        val candidateNames = listOfNotNull(\n"
            "            loadingName?.removeSuffix(\"Plugin\"),\n"
            "            loadingName,\n"
            "            pluginClassName.substringAfterLast('.').removeSuffix(\"Plugin\"),\n"
            "        ).map { it.trim() }.filter { it.isNotBlank() }.distinct()\n"
            "        if (candidateNames.any { name ->\n"
            "                name.contains(\"StreamPlay\", ignoreCase = true) ||\n"
            "                    name.contains(\"SuperStream\", ignoreCase = true) ||\n"
            "                    name.contains(\"Sora\", ignoreCase = true) ||\n"
            "                    name.contains(\"Ultima\", ignoreCase = true) ||\n"
            "                    name.contains(\"CineStream\", ignoreCase = true) ||\n"
            "                    name.contains(\"Codex\", ignoreCase = true)\n"
            "            }\n"
            "        ) {\n"
            "            candidateNames.forEach { prefName ->\n"
            "                val sp = ctx.getSharedPreferences(prefName, Context.MODE_PRIVATE)\n"
            "                if (!sp.contains(\"provider_concurrency\")) {\n"
            "                    sp.edit().putInt(\"provider_concurrency\", 24).apply()\n"
            "                    CloudStreamApp.setKey(prefName, \"provider_concurrency\", 24)\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n",
            "CloudStreamPlatformRuntime smart provider_concurrency=24 default",
        )
        changed |= _replace_once(
            cs_runtime,
            "    private const val DEFAULT_HTTP_TIMEOUT_SECONDS = 20L\n",
            "    private const val DEFAULT_HTTP_TIMEOUT_SECONDS = 12L\n",
            "CloudStreamPlatformRuntime DEFAULT_HTTP_TIMEOUT_SECONDS 12s for dead-mirror fast fail",
        )
        changed |= _replace_once(
            cs_runtime,
            "                                    val items = section.list.map { it.toNuvioSearchItem(api) }\n"
            "                                    if (items.isNotEmpty()) apiSections += title to items\n",
            "                                    val items = section.list.map { it.toNuvioSearchItem(api) }\n"
            "                                    if (items.isNotEmpty()) {\n"
            "                                        CloudStreamSearchRouteIndex.remember(id, section.name, items)\n"
            "                                        apiSections += title to items\n"
            "                                    }\n",
            "CloudStreamPlatformRuntime remember mainPage routes in CloudStreamSearchRouteIndex",
        )
        changed |= _replace_once(
            cs_runtime,
            "                            orderedResults[index] = items.map { it.toNuvioSearchItem(api) }\n",
            "                            val mappedItems = items.map { it.toNuvioSearchItem(api) }\n"
            "                            CloudStreamSearchRouteIndex.remember(id, effectiveQuery, mappedItems)\n"
            "                            orderedResults[index] = mappedItems\n",
            "CloudStreamPlatformRuntime remember search routes in CloudStreamSearchRouteIndex",
        )
        changed |= _replace_once(
            cs_runtime,
            "    override suspend fun loadLinks(data: String): List<CloudStreamPlaybackSource> = withContext(Dispatchers.IO) {\n"
            "        val route = decodeAndroidDexRoute(data)\n"
            "        val api = findProvider(route.providerClassName)\n"
            "        val subtitles = Collections.synchronizedList(mutableListOf<CloudStreamSubtitle>())\n"
            "        val links = Collections.synchronizedList(mutableListOf<ExtractorLink>())\n"
            "        // Match the real CloudStream/Nuvio execution contract: loadLinks() is allowed\n"
            "        // to return false and/or finish after producing callbacks. The callback collection\n"
            "        // is the authoritative result. A timeout must not discard links already emitted.\n"
            "        val completed = withTimeoutOrNull(\n"
            "            stageTimeout(api.loadLinksTimeoutMs, DEFAULT_LINK_TIMEOUT_MS),\n"
            "        ) {\n"
            "            runCatching {\n"
            "                api.loadLinks(\n"
            "                    data = route.data,\n"
            "                    isCasting = false,\n"
            "                    subtitleCallback = { subtitle ->\n"
            "                        subtitles += CloudStreamSubtitle(\n"
            "                            url = subtitle.url,\n"
            "                            language = subtitle.lang,\n"
            "                            name = subtitle.lang,\n"
            "                            headers = subtitle.headers.orEmpty(),\n"
            "                        )\n"
            "                    },\n"
            "                    callback = links::add,\n"
            "                )\n"
            "            }.onFailure { error ->\n"
            "                log.w(error) {\n"
            "                    \"CloudStream loadLinks threw provider=${api.name} \" +\n"
            "                        \"links=${links.size} error=${error.javaClass.simpleName}: ${error.message}\"\n"
            "                }\n"
            "            }.getOrDefault(false)\n"
            "        }\n\n"
            "        val subtitleSnapshot = synchronized(subtitles) { subtitles.toList() }\n"
            "        val linkSnapshot = synchronized(links) { links.toList() }\n\n"
            "        RuntimeDiagnostics.recordLog(\n"
            "            \"cs-load-links-result provider=${api.name} completed=${completed != null} \" +\n"
            "                \"returned=${completed ?: \"timeout\"} links=${linkSnapshot.size} subtitles=${subtitleSnapshot.size}\",\n"
            "        )\n\n"
            "        if (completed == null) {\n"
            "            log.w {\n"
            "                \"CloudStream loadLinks timed out provider=${api.name} \" +\n"
            "                    \"links=${linkSnapshot.size}; returning partial callbacks\"\n"
            "            }\n"
            "        } else if (completed == false && linkSnapshot.isEmpty()) {\n"
            "            log.w {\n"
            "                \"CloudStream loadLinks returned false with no links provider=${api.name}\"\n"
            "            }\n"
            "        }\n\n"
            "        linkSnapshot.distinctBy { link ->\n"
            "            listOf(\n"
            "                link.url,\n"
            "                link.referer,\n"
            "                link.quality.toString(),\n"
            "                link.type.name,\n"
            "                link.headers.toString(),\n"
            "            )\n"
            "        }.map { link ->\n"
            "            CloudStreamPlaybackSource(\n"
            "                name = link.name.ifBlank { link.source },\n"
            "                url = link.url,\n"
            "                quality = link.quality.takeIf { it > 0 },\n"
            "                referer = link.referer.takeIf(String::isNotBlank),\n"
            "                headers = link.headers,\n"
            "                subtitles = subtitleSnapshot,\n"
            "                isHls = link.type == ExtractorLinkType.M3U8,\n"
            "                isDash = link.type == ExtractorLinkType.DASH,\n"
            "            )\n"
            "        }.also {\n"
            "            if (it.isEmpty()) {\n"
            "                error(\n"
            "                    \"CloudStream provider returned no playable links \" +\n"
            "                        \"(provider=${api.name}, completed=${completed ?: \"timeout\"})\",\n"
            "                )\n"
            "            }\n"
            "        }\n"
            "    }\n",
            "    override suspend fun loadLinks(data: String): List<CloudStreamPlaybackSource> = withContext(Dispatchers.IO) {\n"
            "        val route = decodeAndroidDexRoute(data)\n"
            "        val api = findProvider(route.providerClassName)\n"
            "        val subtitles = Collections.synchronizedList(mutableListOf<CloudStreamSubtitle>())\n"
            "        val links = Collections.synchronizedList(mutableListOf<ExtractorLink>())\n\n"
            "        fun snapshotSources(): List<CloudStreamPlaybackSource> {\n"
            "            val subSnap = synchronized(subtitles) { subtitles.toList() }\n"
            "            val linkSnap = synchronized(links) { links.toList() }\n"
            "            if (linkSnap.isEmpty()) return emptyList()\n"
            "            return linkSnap.distinctBy { link ->\n"
            "                listOf(\n"
            "                    link.url,\n"
            "                    link.referer,\n"
            "                    link.quality.toString(),\n"
            "                    link.type.name,\n"
            "                    link.headers.toString(),\n"
            "                )\n"
            "            }.map { link ->\n"
            "                CloudStreamPlaybackSource(\n"
            "                    name = link.name.ifBlank { link.source },\n"
            "                    url = link.url,\n"
            "                    quality = link.quality.takeIf { it > 0 },\n"
            "                    referer = link.referer.takeIf(String::isNotBlank),\n"
            "                    headers = link.headers,\n"
            "                    subtitles = subSnap,\n"
            "                    isHls = link.type == ExtractorLinkType.M3U8,\n"
            "                    isDash = link.type == ExtractorLinkType.DASH,\n"
            "                )\n"
            "            }\n"
            "        }\n\n"
            "        val completed = withTimeoutOrNull(\n"
            "            stageTimeout(api.loadLinksTimeoutMs, DEFAULT_LINK_TIMEOUT_MS),\n"
            "        ) {\n"
            "            runCatching {\n"
            "                api.loadLinks(\n"
            "                    data = route.data,\n"
            "                    isCasting = false,\n"
            "                    subtitleCallback = { subtitle ->\n"
            "                        subtitles += CloudStreamSubtitle(\n"
            "                            url = subtitle.url,\n"
            "                            language = subtitle.lang,\n"
            "                            name = subtitle.lang,\n"
            "                            headers = subtitle.headers.orEmpty(),\n"
            "                        )\n"
            "                        if (links.isNotEmpty()) {\n"
            "                            val partial = snapshotSources()\n"
            "                            if (partial.isNotEmpty()) {\n"
            "                                CloudStreamLiveLinkHub.publish(\n"
            "                                    providerId = id,\n"
            "                                    routeData = data,\n"
            "                                    sources = partial,\n"
            "                                    isComplete = false,\n"
            "                                )\n"
            "                            }\n"
            "                        }\n"
            "                    },\n"
            "                    callback = { link ->\n"
            "                        links.add(link)\n"
            "                        val partial = snapshotSources()\n"
            "                        if (partial.isNotEmpty()) {\n"
            "                            CloudStreamLiveLinkHub.publish(\n"
            "                                providerId = id,\n"
            "                                routeData = data,\n"
            "                                sources = partial,\n"
            "                                isComplete = false,\n"
            "                            )\n"
            "                        }\n"
            "                    },\n"
            "                )\n"
            "            }.onFailure { error ->\n"
            "                log.w(error) {\n"
            "                    \"CloudStream loadLinks threw provider=${api.name} \" +\n"
            "                        \"links=${links.size} error=${error.javaClass.simpleName}: ${error.message}\"\n"
            "                }\n"
            "            }.getOrDefault(false)\n"
            "        }\n\n"
            "        val finalSources = snapshotSources()\n"
            "        if (finalSources.isNotEmpty()) {\n"
            "            CloudStreamLiveLinkHub.publish(\n"
            "                providerId = id,\n"
            "                routeData = data,\n"
            "                sources = finalSources,\n"
            "                isComplete = true,\n"
            "            )\n"
            "        }\n\n"
            "        RuntimeDiagnostics.recordLog(\n"
            "            \"cs-load-links-result provider=${api.name} completed=${completed != null} \" +\n"
            "                \"returned=${completed ?: \"timeout\"} links=${finalSources.size} subtitles=${subtitles.size}\",\n"
            "        )\n\n"
            "        if (completed == null) {\n"
            "            log.w {\n"
            "                \"CloudStream loadLinks timed out provider=${api.name} \" +\n"
            "                    \"links=${finalSources.size}; returning partial callbacks\"\n"
            "            }\n"
            "        } else if (completed == false && finalSources.isEmpty()) {\n"
            "            log.w {\n"
            "                \"CloudStream loadLinks returned false with no links provider=${api.name}\"\n"
            "            }\n"
            "        }\n\n"
            "        finalSources.also {\n"
            "            if (it.isEmpty()) {\n"
            "                error(\n"
            "                    \"CloudStream provider returned no playable links \" +\n"
            "                        \"(provider=${api.name}, completed=${completed ?: \"timeout\"})\",\n"
            "                )\n"
            "            }\n"
            "        }\n"
            "    }\n",
            "CloudStreamPlatformRuntime live progressive callback streaming in loadLinks",
        )
        changed |= _replace_once(
            cs_runtime,
            "        private const val CLOUDSTREAM_API_CONCURRENCY = 4\n"
            "        private const val DEFAULT_MAIN_PAGE_SECTION_TIMEOUT_MS = 15_000L\n"
            "        private const val DEFAULT_DISCOVERY_TIMEOUT_MS = 25_000L\n"
            "        private const val DEFAULT_LOAD_TIMEOUT_MS = 45_000L\n"
            "        private const val DEFAULT_LINK_TIMEOUT_MS = 75_000L\n",
            "        private const val CLOUDSTREAM_API_CONCURRENCY = 8\n"
            "        private const val DEFAULT_MAIN_PAGE_SECTION_TIMEOUT_MS = 15_000L\n"
            "        private const val DEFAULT_DISCOVERY_TIMEOUT_MS = 14_000L\n"
            "        private const val DEFAULT_LOAD_TIMEOUT_MS = 45_000L\n"
            "        private const val DEFAULT_LINK_TIMEOUT_MS = 85_000L\n",
            "CloudStreamPlatformRuntime tuned sub-API concurrency & link timeout",
        )
        if changed:
            patched.append(str(cs_runtime.relative_to(root)))

    # -------------------------------------------------------------------------
    # 4. CloudStreamRepository.kt (fullCommonMain):
    #    - Pre-warm runnable .cs3 plugins on initialize() and setPluginEnabled(..., true)
    #    - Stop background link loads cleanly when playback starts (unless Player is loading)
    #    - Respect forceRefresh invalidation + preserve partial live links on timeout
    # -------------------------------------------------------------------------
    cs_repo = root / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/cloudstream/CloudStreamRepository.kt"
    if cs_repo.is_file():
        changed = False
        changed |= _replace_once(
            cs_repo,
            "    private const val LOAD_LINKS_CACHE_MAX_ENTRIES = 16\n"
            "    private const val LOAD_LINKS_CACHE_TTL_MS = 120_000L\n"
            "    private const val LOAD_RESULT_CACHE_MAX_ENTRIES = 16\n"
            "    private const val LOAD_RESULT_CACHE_TTL_MS = 600_000L\n"
            "    private const val REPOSITORY_DISCOVERY_CONCURRENCY = 6\n"
            "    private const val PROVIDER_REQUEST_CONCURRENCY = 4\n",
            "    private const val LOAD_LINKS_CACHE_MAX_ENTRIES = 32\n"
            "    private const val LOAD_LINKS_CACHE_TTL_MS = 600_000L\n"
            "    private const val LOAD_RESULT_CACHE_MAX_ENTRIES = 32\n"
            "    private const val LOAD_RESULT_CACHE_TTL_MS = 900_000L\n"
            "    private const val REPOSITORY_DISCOVERY_CONCURRENCY = 6\n"
            "    private const val PROVIDER_REQUEST_CONCURRENCY = 8\n"
            "    private var playbackStopObserverStarted = false\n",
            "CloudStreamRepository cache TTL & provider concurrency",
        )
        changed |= _replace_once(
            cs_repo,
            "        initialized = true\n"
            "        _uiState.value = restoreState(profileId)\n\n"
            "    }\n",
            "        initialized = true\n"
            "        val restored = restoreState(profileId)\n"
            "        _uiState.value = restored\n"
            "        if (!playbackStopObserverStarted) {\n"
            "            playbackStopObserverStarted = true\n"
            "            scope.launch {\n"
            "                var lastToken = CloudStreamLiveLinkHub.playbackStartedSignals.value\n"
            "                CloudStreamLiveLinkHub.playbackStartedSignals.collect { token ->\n"
            "                    if (token != lastToken) {\n"
            "                        lastToken = token\n"
            "                        if (!CloudStreamLiveLinkHub.isPlayerLoadingActive()) {\n"
            "                            cancelInFlightLoadLinksRequests()\n"
            "                        }\n"
            "                    }\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "        scope.launch {\n"
            "            restored.plugins\n"
            "                .filter(CloudStreamPluginItem::isRunnable)\n"
            "                .forEach { plugin ->\n"
            "                    runCatching { CloudStreamPlatformRuntime.provider(plugin) }\n"
            "                }\n"
            "        }\n"
            "    }\n",
            "CloudStreamRepository pre-warm runnable plugins & observe playback start",
        )
        changed |= _replace_once(
            cs_repo,
            "            val enabledPlugin = _uiState.value.plugins.firstOrNull { it.metadata.id.value == pluginId }\n"
            "            if (enabledPlugin?.isRunnable == true) {\n"
            "            }\n",
            "            val enabledPlugin = _uiState.value.plugins.firstOrNull { it.metadata.id.value == pluginId }\n"
            "            if (enabledPlugin?.isRunnable == true) {\n"
            "                scope.launch {\n"
            "                    runCatching { CloudStreamPlatformRuntime.provider(enabledPlugin) }\n"
            "                }\n"
            "            }\n",
            "CloudStreamRepository pre-warm newly enabled plugin",
        )
        changed |= _replace_once(
            cs_repo,
            "        CloudStreamPlatformRuntime.clear()\n"
            "        currentProfileId = profileId.coerceAtLeast(1)\n",
            "        CloudStreamLiveLinkHub.clearAll()\n"
            "        CloudStreamPlatformRuntime.clear()\n"
            "        currentProfileId = profileId.coerceAtLeast(1)\n",
            "CloudStreamRepository clear live link hub on profile change",
        )
        changed |= _replace_once(
            cs_repo,
            "        CloudStreamPlatformRuntime.clear()\n"
            "        CloudStreamPlatformStorage.clearPackages()\n",
            "        CloudStreamLiveLinkHub.clearAll()\n"
            "        CloudStreamPlatformRuntime.clear()\n"
            "        CloudStreamPlatformStorage.clearPackages()\n",
            "CloudStreamRepository clear live link hub on clearLocalState",
        )
        changed |= _replace_once(
            cs_repo,
            "    actual suspend fun loadLinks(providerId: String, data: String): Result<List<CloudStreamPlaybackSource>> {\n"
            "        initialize()\n"
            "        val requestKey = \"$providerId\\\\u0000$data\"\n"
            "        val now = currentEpochMillis()\n"
            "        loadLinksCacheMutex.withLock {\n",
            "    actual suspend fun loadLinks(providerId: String, data: String): Result<List<CloudStreamPlaybackSource>> {\n"
            "        initialize()\n"
            "        val requestKey = \"$providerId\\\\u0000$data\"\n"
            "        val bypassCache = CloudStreamLiveLinkHub.consumeForceRefresh(providerId, data)\n"
            "        if (bypassCache) {\n"
            "            loadLinksCacheMutex.withLock { loadLinksCache.remove(requestKey) }\n"
            "        }\n"
            "        val now = currentEpochMillis()\n"
            "        loadLinksCacheMutex.withLock {\n",
            "CloudStreamRepository honor forceRefresh in loadLinks",
        )
        changed |= _replace_once(
            cs_repo,
            "                entry.sources\n"
            "            } else {\n"
            "                null\n"
            "            }\n"
            "        }?.let { cached ->\n"
            "            RuntimeDiagnostics.recordLog(\"cs-load-links-cache-hit provider=$providerId links=${cached.size}\")\n"
            "            return Result.success(cached)\n"
            "        }\n",
            "                entry.sources\n"
            "            } else {\n"
            "                null\n"
            "            }\n"
            "        }?.let { cached ->\n"
            "            CloudStreamLiveLinkHub.publish(\n"
            "                providerId = providerId,\n"
            "                routeData = data,\n"
            "                sources = cached,\n"
            "                isComplete = true,\n"
            "            )\n"
            "            RuntimeDiagnostics.recordLog(\"cs-load-links-cache-hit provider=$providerId links=${cached.size}\")\n"
            "            return Result.success(cached)\n"
            "        }\n",
            "CloudStreamRepository publish cache hit to live link hub",
        )
        if changed:
            patched.append(str(cs_repo.relative_to(root)))

    # -------------------------------------------------------------------------
    # 5. StreamFetchSupport.kt:
    #    - Non-blocking instant StreamItem mapping + background parallel HLS variant cache
    #    - loadCloudStreamRouteProgressive(...) for live progressive source emission
    #    - Smart parentMetaId fallback from `videoId.substringBefore(':')`
    # -------------------------------------------------------------------------
    fetch_support = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamFetchSupport.kt"
    if fetch_support.is_file():
        changed = False
        changed |= _replace_once(
            fetch_support,
            "import com.nuvio.app.features.cloudstream.CloudStreamLoadItem\n",
            "import com.nuvio.app.features.cloudstream.CloudStreamLiveLinkHub\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamLoadItem\n",
            "StreamFetchSupport import CloudStreamLiveLinkHub",
        )
        changed |= _replace_once(
            fetch_support,
            "import kotlinx.coroutines.sync.Mutex\n"
            "import kotlinx.coroutines.sync.withLock\n"
            "import kotlin.math.abs\n",
            "import kotlinx.coroutines.launch\n"
            "import kotlinx.coroutines.sync.Mutex\n"
            "import kotlinx.coroutines.sync.Semaphore\n"
            "import kotlinx.coroutines.sync.withLock\n"
            "import kotlinx.coroutines.sync.withPermit\n"
            "import kotlin.math.abs\n"
            "import kotlin.time.TimeSource\n",
            "StreamFetchSupport progressive streaming imports",
        )
        changed |= _replace_once(
            fetch_support,
            "    if (fresh.isNotEmpty()) {\n"
            "        cloudStreamCacheMutex.withLock {\n",
            "    if (fresh.isNotEmpty()) {\n"
            "        CloudStreamSearchRouteIndex.remember(providerId, query, fresh)\n"
            "        cloudStreamCacheMutex.withLock {\n",
            "StreamFetchSupport populate CloudStreamSearchRouteIndex on search",
        )
        changed |= _replace_once(
            fetch_support,
            "internal suspend fun resolveCloudStreamProviderStreams(\n"
            "    providerGroup: CloudStreamProviderGroup,\n"
            "    request: CloudStreamSearchRequest?,\n"
            "): AddonStreamGroup {\n",
            "private val hlsVariantCacheMutex = Mutex()\n"
            "private val hlsVariantCache = LinkedHashMap<String, List<StreamItem>>()\n"
            "private val hlsExpandInFlight = HashSet<String>()\n"
            "private val hlsExpandSemaphore = Semaphore(10)\n\n"
            "private fun hlsCacheKeyForStream(stream: StreamItem): String? {\n"
            "    val sourceUrl = stream.playableDirectUrl?.takeIf { it.isNotBlank() } ?: return null\n"
            "    val normalizedType = normalizeStreamType(stream.streamType)\n"
            "    val shouldInspect = normalizedType == \"hls\" || sourceUrl.contains(\".m3u8\", ignoreCase = true)\n"
            "    if (!shouldInspect) return null\n"
            "    return \"${stream.addonId}::${stream.sourceName.orEmpty()}::${stream.streamLabel}::$sourceUrl\"\n"
            "}\n\n"
            "private fun deduplicateCloudStreamItems(items: List<StreamItem>): List<StreamItem> =\n"
            "    items.distinctBy { stream ->\n"
            "        listOf(\n"
            "            stream.addonId,\n"
            "            stream.sourceName.orEmpty(),\n"
            "            stream.streamLabel,\n"
            "            stream.playableDirectUrl.orEmpty(),\n"
            "        )\n"
            "    }\n\n"
            "internal fun fastCloudStreamSourcesToStreamItems(\n"
            "    providerId: String,\n"
            "    providerName: String,\n"
            "    sources: List<CloudStreamPlaybackSource>,\n"
            "): List<StreamItem> {\n"
            "    if (sources.isEmpty()) return emptyList()\n"
            "    val cachedSnapshot: Map<String, List<StreamItem>> = if (hlsVariantCacheMutex.tryLock()) {\n"
            "        try { HashMap(hlsVariantCache) } finally { hlsVariantCacheMutex.unlock() }\n"
            "    } else {\n"
            "        emptyMap()\n"
            "    }\n"
            "    val mapped = sources.flatMap { source ->\n"
            "        val base = source.toStreamItem(\n"
            "            providerId = providerId,\n"
            "            providerName = providerName,\n"
            "        )\n"
            "        val key = hlsCacheKeyForStream(base)\n"
            "        if (key != null) cachedSnapshot[key] ?: listOf(base) else listOf(base)\n"
            "    }\n"
            "    return deduplicateCloudStreamItems(mapped)\n"
            "}\n\n"
            "private fun scheduleBackgroundHlsExpansion(\n"
            "    providerId: String,\n"
            "    providerName: String,\n"
            "    sources: List<CloudStreamPlaybackSource>,\n"
            "    onVariantsExpanded: () -> Unit,\n"
            ") {\n"
            "    sources.forEach { source ->\n"
            "        val base = source.toStreamItem(providerId = providerId, providerName = providerName)\n"
            "        val key = hlsCacheKeyForStream(base) ?: return@forEach\n"
            "        cloudStreamProviderScope.launch {\n"
            "            val shouldStart = hlsVariantCacheMutex.withLock {\n"
            "                if (key in hlsVariantCache || key in hlsExpandInFlight) {\n"
            "                    false\n"
            "                } else {\n"
            "                    hlsExpandInFlight.add(key)\n"
            "                    true\n"
            "                }\n"
            "            }\n"
            "            if (!shouldStart) return@launch\n"
            "            val expanded = try {\n"
            "                hlsExpandSemaphore.withPermit {\n"
            "                    withTimeoutOrNull(3_000L) { base.expandCloudStreamHlsVariants() }\n"
            "                        ?: listOf(base)\n"
            "                }\n"
            "            } catch (_: Throwable) {\n"
            "                listOf(base)\n"
            "            }\n"
            "            var hadMultiVariants = false\n"
            "            hlsVariantCacheMutex.withLock {\n"
            "                hlsExpandInFlight.remove(key)\n"
            "                if (hlsVariantCache.size >= 512) {\n"
            "                    hlsVariantCache.keys.firstOrNull()?.let(hlsVariantCache::remove)\n"
            "                }\n"
            "                hlsVariantCache[key] = expanded\n"
            "                hadMultiVariants = expanded.size > 1\n"
            "            }\n"
            "            if (hadMultiVariants) {\n"
            "                onVariantsExpanded()\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n\n"
            "internal suspend fun loadCloudStreamRouteProgressive(\n"
            "    providerId: String,\n"
            "    providerName: String,\n"
            "    linkData: String,\n"
            "    timeoutMs: Long = CLOUDSTREAM_PROVIDER_STREAM_TIMEOUT_MS,\n"
            "    forceRefresh: Boolean = false,\n"
            "    onProgress: ((List<StreamItem>) -> Unit)? = null,\n"
            "): Result<List<StreamItem>> = coroutineScope {\n"
            "    if (forceRefresh) {\n"
            "        CloudStreamLiveLinkHub.invalidate(providerId, linkData)\n"
            "    } else {\n"
            "        CloudStreamLiveLinkHub.snapshot(providerId, linkData)?.let { snap ->\n"
            "            if (snap.sources.isNotEmpty()) {\n"
            "                val cachedItems = fastCloudStreamSourcesToStreamItems(\n"
            "                    providerId = providerId,\n"
            "                    providerName = providerName,\n"
            "                    sources = snap.sources,\n"
            "                )\n"
            "                if (cachedItems.isNotEmpty()) {\n"
            "                    onProgress?.invoke(cachedItems)\n"
            "                    if (snap.isComplete) {\n"
            "                        return@coroutineScope Result.success(cachedItems)\n"
            "                    }\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n\n"
            "    var lastEmittedCount = 0\n"
            "    var lastEmitMark: TimeSource.Monotonic.ValueTimeMark? = null\n\n"
            "    fun emitSources(sources: List<CloudStreamPlaybackSource>, force: Boolean = false) {\n"
            "        if (sources.isEmpty()) return\n"
            "        if (onProgress != null) {\n"
            "            val nowMark = TimeSource.Monotonic.markNow()\n"
            "            val elapsedMs = lastEmitMark?.elapsedNow()?.inWholeMilliseconds ?: Long.MAX_VALUE\n"
            "            val shouldEmit = force || lastEmittedCount == 0 ||\n"
            "                (sources.size != lastEmittedCount && elapsedMs >= 140L) ||\n"
            "                elapsedMs >= 500L\n"
            "            if (shouldEmit) {\n"
            "                val items = fastCloudStreamSourcesToStreamItems(\n"
            "                    providerId = providerId,\n"
            "                    providerName = providerName,\n"
            "                    sources = sources,\n"
            "                )\n"
            "                if (items.isNotEmpty()) {\n"
            "                    lastEmittedCount = sources.size\n"
            "                    lastEmitMark = nowMark\n"
            "                    onProgress.invoke(items)\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "        scheduleBackgroundHlsExpansion(providerId, providerName, sources) {\n"
            "            if (onProgress != null) {\n"
            "                val latest = CloudStreamLiveLinkHub.snapshot(providerId, linkData)?.sources ?: sources\n"
            "                val updated = fastCloudStreamSourcesToStreamItems(providerId, providerName, latest)\n"
            "                if (updated.isNotEmpty()) {\n"
            "                    onProgress.invoke(updated)\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    }\n\n"
            "    val liveJob = launch {\n"
            "        CloudStreamLiveLinkHub.observe(providerId, linkData).collect { snap ->\n"
            "            emitSources(snap.sources, force = lastEmittedCount == 0 || snap.isComplete)\n"
            "        }\n"
            "    }\n\n"
            "    val loadedSourcesResult = try {\n"
            "        val direct = withTimeoutOrNull(timeoutMs) {\n"
            "            CloudStreamRepository.loadLinks(providerId, linkData)\n"
            "        }\n"
            "        when {\n"
            "            direct != null && direct.isSuccess -> direct\n"
            "            else -> {\n"
            "                val partial = CloudStreamLiveLinkHub.snapshot(providerId, linkData)?.sources.orEmpty()\n"
            "                if (partial.isNotEmpty()) {\n"
            "                    Result.success(partial)\n"
            "                } else {\n"
            "                    direct ?: Result.failure(IllegalStateException(\"$providerName timed out\"))\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "    } finally {\n"
            "        liveJob.cancel()\n"
            "    }\n\n"
            "    loadedSourcesResult.map { finalSources ->\n"
            "        val fastFinal = fastCloudStreamSourcesToStreamItems(\n"
            "            providerId = providerId,\n"
            "            providerName = providerName,\n"
            "            sources = finalSources,\n"
            "        )\n"
            "        if (fastFinal.isNotEmpty()) {\n"
            "            onProgress?.invoke(fastFinal)\n"
            "        }\n"
            "        scheduleBackgroundHlsExpansion(providerId, providerName, finalSources) {}\n"
            "        fastFinal\n"
            "    }\n"
            "}\n\n"
            "internal suspend fun resolveCloudStreamProviderStreams(\n"
            "    providerGroup: CloudStreamProviderGroup,\n"
            "    request: CloudStreamSearchRequest?,\n"
            "    forceRefresh: Boolean = false,\n"
            "    onProgress: ((List<StreamItem>) -> Unit)? = null,\n"
            "): AddonStreamGroup {\n",
            "StreamFetchSupport progressive route loader & fast non-blocking HLS handling",
        )
        changed |= _replace_once(
            fetch_support,
            "                val sources = runCatchingUnlessCancelled {\n"
            "                    CloudStreamRepository.loadLinks(providerGroup.providerId, linkData).getOrThrow()\n"
            "                }.onFailure { error -> lastError = error }\n"
            "                    .getOrNull()\n"
            "                    ?: return null\n"
            "                return cloudStreamSourcesToStreamItems(\n"
            "                    providerId = providerGroup.providerId,\n"
            "                    providerName = providerGroup.addonName,\n"
            "                    sources = sources,\n"
            "                ).takeIf { streams -> streams.isNotEmpty() }\n"
            "                    ?: run {\n"
            "                        lastError = IllegalStateException(\"No links found\")\n"
            "                        null\n"
            "                    }\n",
            "                val progressiveStreams = runCatchingUnlessCancelled {\n"
            "                    loadCloudStreamRouteProgressive(\n"
            "                        providerId = providerGroup.providerId,\n"
            "                        providerName = providerGroup.addonName,\n"
            "                        linkData = linkData,\n"
            "                        forceRefresh = forceRefresh,\n"
            "                        onProgress = onProgress,\n"
            "                    ).getOrThrow()\n"
            "                }.onFailure { error -> lastError = error }\n"
            "                    .getOrNull()\n"
            "                    ?: return null\n"
            "                return progressiveStreams.takeIf { streams -> streams.isNotEmpty() }\n"
            "                    ?: run {\n"
            "                        lastError = IllegalStateException(\"No links found\")\n"
            "                        null\n"
            "                    }\n",
            "StreamFetchSupport resolveMatch use loadCloudStreamRouteProgressive",
        )
        changed |= _replace_once(
            fetch_support,
            "                    if (linkData != null) {\n"
            "                        val directSources = runCatchingUnlessCancelled {\n"
            "                            CloudStreamRepository.loadLinks(providerGroup.providerId, linkData).getOrThrow()\n"
            "                        }.onFailure { error -> lastError = error }\n"
            "                            .getOrNull()\n"
            "                        if (directSources != null) {\n"
            "                            val directStreams = cloudStreamSourcesToStreamItems(\n"
            "                                providerId = providerGroup.providerId,\n"
            "                                providerName = providerGroup.addonName,\n"
            "                                sources = directSources,\n"
            "                            )\n"
            "                            if (directStreams.isNotEmpty()) return@runCatchingUnlessCancelled directStreams\n"
            "                        }\n"
            "                    }\n",
            "                    if (linkData != null) {\n"
            "                        val directStreams = runCatchingUnlessCancelled {\n"
            "                            loadCloudStreamRouteProgressive(\n"
            "                                providerId = providerGroup.providerId,\n"
            "                                providerName = providerGroup.addonName,\n"
            "                                linkData = linkData,\n"
            "                                forceRefresh = forceRefresh,\n"
            "                                onProgress = onProgress,\n"
            "                            ).getOrThrow()\n"
            "                        }.onFailure { error -> lastError = error }\n"
            "                            .getOrNull()\n"
            "                        if (!directStreams.isNullOrEmpty()) {\n"
            "                            return@runCatchingUnlessCancelled directStreams\n"
            "                        }\n"
            "                    }\n",
            "StreamFetchSupport loadByExternalId use loadCloudStreamRouteProgressive",
        )
        changed |= _replace_once(
            fetch_support,
            "    val metaLookupType = parentMetaType?.takeIf { it.isNotBlank() } ?: type\n"
            "    val metaLookupId = parentMetaId?.takeIf { it.isNotBlank() } ?: videoId\n"
            "    val meta = MetaDetailsRepository.peek(metaLookupType, metaLookupId)\n",
            "    val metaLookupType = parentMetaType?.takeIf { it.isNotBlank() } ?: type\n"
            "    val inferredParentId = parentMetaId?.takeIf { it.isNotBlank() }\n"
            "        ?: videoId.substringBefore(':').takeIf { it.isNotBlank() && it != videoId }\n"
            "    val metaLookupId = inferredParentId ?: videoId\n"
            "    val meta = MetaDetailsRepository.peek(metaLookupType, metaLookupId)\n"
            "        ?: MetaDetailsRepository.peek(\"series\", metaLookupId)\n"
            "        ?: MetaDetailsRepository.peek(\"movie\", metaLookupId)\n",
            "StreamFetchSupport buildCloudStreamSearchRequest smart parentMetaId fallback",
        )
        changed |= _replace_once(
            fetch_support,
            "    val externalId = sequenceOf(videoId, parentMetaId, metaLookupId)\n",
            "    val externalId = sequenceOf(videoId, videoId.substringBefore(':'), parentMetaId, metaLookupId)\n",
            "StreamFetchSupport buildCloudStreamSearchRequest episode externalId extraction",
        )
        if changed:
            patched.append(str(fetch_support.relative_to(root)))

    # -------------------------------------------------------------------------
    # 6. StreamsRepository.kt:
    #    - Progressive live display on Source Selection screen until playback starts
    #    - Higher CloudStream concurrency (8)
    #    - Signal playbackStarted on cancelLoading() / clear()
    # -------------------------------------------------------------------------
    streams_repo = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamsRepository.kt"
    if streams_repo.is_file():
        changed = False
        changed |= _replace_once(
            streams_repo,
            "import com.nuvio.app.features.cloudstream.CloudStreamRepository\n",
            "import com.nuvio.app.features.cloudstream.CloudStreamLiveLinkHub\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamRepository\n",
            "StreamsRepository import CloudStreamLiveLinkHub",
        )
        changed |= _replace_once(
            streams_repo,
            "    private val cloudStreamSemaphore = Semaphore(4)\n",
            "    private val cloudStreamSemaphore = Semaphore(8)\n",
            "StreamsRepository cloudStreamSemaphore 8",
        )
        changed |= _replace_once(
            streams_repo,
            "            activeJob = scope.launch {\n"
            "                val result = runCatching {\n"
            "                    withTimeoutOrNull(STREAM_PROVIDER_TIMEOUT_MS) {\n"
            "                        CloudStreamRepository.loadLinks(cloudStreamRoute.providerId, cloudStreamRoute.data)\n"
            "                    } ?: error(\"$providerName timed out\")\n"
            "                }.fold(\n"
            "                    onSuccess = { it },\n"
            "                    onFailure = { Result.failure(it) },\n"
            "                )\n"
            "                if (activeRequestKey != requestKey) return@launch\n"
            "                result.fold(\n"
            "                    onSuccess = { sources ->\n"
            "                        val streams = cloudStreamSourcesToStreamItems(\n"
            "                            providerId = cloudStreamRoute.providerId,\n"
            "                            providerName = providerName,\n"
            "                            sources = sources,\n"
            "                        )\n",
            "            activeJob = scope.launch {\n"
            "                val result = loadCloudStreamRouteProgressive(\n"
            "                    providerId = cloudStreamRoute.providerId,\n"
            "                    providerName = providerName,\n"
            "                    linkData = cloudStreamRoute.data,\n"
            "                    timeoutMs = STREAM_PROVIDER_TIMEOUT_MS,\n"
            "                    forceRefresh = forceRefresh,\n"
            "                    onProgress = { partialStreams ->\n"
            "                        if (activeRequestKey != requestKey || partialStreams.isEmpty()) return@loadCloudStreamRouteProgressive\n"
            "                        val orderedPartial = partialStreams.sortedForGroupedDisplay()\n"
            "                        val presentedPartial = StreamBadgePresentation.apply(\n"
            "                            groups = listOf(\n"
            "                                AddonStreamGroup(\n"
            "                                    addonName = providerName,\n"
            "                                    addonId = providerAddonId,\n"
            "                                    streams = orderedPartial,\n"
            "                                    isLoading = true,\n"
            "                                ),\n"
            "                            ),\n"
            "                            rules = streamBadgeRules,\n"
            "                        )\n"
            "                        _uiState.update { current ->\n"
            "                            if (current.requestToken != requestToken) return@update current\n"
            "                            val existing = current.groups.firstOrNull { it.addonId == providerAddonId }\n"
            "                            if (existing != null && !existing.isLoading) return@update current\n"
            "                            current.copy(\n"
            "                                groups = presentedPartial,\n"
            "                                activeAddonIds = setOf(providerAddonId),\n"
            "                                isAnyLoading = true,\n"
            "                                emptyStateReason = null,\n"
            "                            )\n"
            "                        }\n"
            "                    },\n"
            "                )\n"
            "                if (activeRequestKey != requestKey) return@launch\n"
            "                result.fold(\n"
            "                    onSuccess = { rawStreams ->\n"
            "                        val streams = rawStreams.sortedForGroupedDisplay()\n",
            "StreamsRepository progressive streaming for direct CloudStream route",
        )
        changed |= _replace_once(
            streams_repo,
            "            fun publishAddonGroup(group: AddonStreamGroup) {\n",
            "            fun publishPartialCloudStreamGroup(partialGroup: AddonStreamGroup) {\n"
            "                if (partialGroup.streams.isEmpty()) return\n"
            "                val presented = presentStreamGroup(partialGroup)\n"
            "                _uiState.update { current ->\n"
            "                    val target = current.groups.firstOrNull { it.addonId == presented.addonId }\n"
            "                    if (target != null && !target.isLoading) return@update current\n"
            "                    val updated = StreamAutoPlaySelector.orderAddonStreams(\n"
            "                        groups = current.groups.map { g ->\n"
            "                            if (g.addonId == presented.addonId) {\n"
            "                                presented.copy(isLoading = true, error = null)\n"
            "                            } else {\n"
            "                                g\n"
            "                            }\n"
            "                        },\n"
            "                        installedOrder = installedAddonOrder,\n"
            "                        preferredGroupIds = preferredGroupIds,\n"
            "                    )\n"
            "                    val anyLoading = updated.any { it.isLoading }\n"
            "                    current.copy(\n"
            "                        groups = updated,\n"
            "                        isAnyLoading = anyLoading,\n"
            "                        emptyStateReason = updated.toEmptyStateReason(anyLoading),\n"
            "                    )\n"
            "                }\n"
            "                updateAutoPlayAfterStreamsChanged()\n"
            "            }\n\n"
            "            fun publishAddonGroup(group: AddonStreamGroup) {\n",
            "StreamsRepository publishPartialCloudStreamGroup helper",
        )
        changed |= _replace_once(
            streams_repo,
            "            cloudStreamProviderGroups.forEach { providerGroup ->\n"
            "                launch {\n"
            "                    val group = withTimeoutOrNull(STREAM_PROVIDER_TIMEOUT_MS) {\n"
            "                        cloudStreamSemaphore.withPermit {\n"
            "                            resolveCloudStreamProviderStreams(\n"
            "                                providerGroup = providerGroup,\n"
            "                                request = cloudStreamSearchRequest,\n"
            "                            )\n"
            "                        }\n"
            "                    } ?: AddonStreamGroup(\n",
            "            cloudStreamProviderGroups.forEach { providerGroup ->\n"
            "                launch {\n"
            "                    val group = withTimeoutOrNull(STREAM_PROVIDER_TIMEOUT_MS) {\n"
            "                        cloudStreamSemaphore.withPermit {\n"
            "                            resolveCloudStreamProviderStreams(\n"
            "                                providerGroup = providerGroup,\n"
            "                                request = cloudStreamSearchRequest,\n"
            "                                forceRefresh = forceRefresh,\n"
            "                                onProgress = { partialStreams ->\n"
            "                                    publishPartialCloudStreamGroup(\n"
            "                                        AddonStreamGroup(\n"
            "                                            addonName = providerGroup.addonName,\n"
            "                                            addonId = providerGroup.addonId,\n"
            "                                            streams = partialStreams.sortedForGroupedDisplay(),\n"
            "                                            isLoading = true,\n"
            "                                        ),\n"
            "                                    )\n"
            "                                },\n"
            "                            )\n"
            "                        }\n"
            "                    } ?: AddonStreamGroup(\n",
            "StreamsRepository pass onProgress to resolveCloudStreamProviderStreams",
        )
        changed |= _replace_once(
            streams_repo,
            "    fun cancelLoading() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        activeJob?.cancel()\n"
            "        activeJob = null\n",
            "    fun cancelLoading() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        activeJob?.cancel()\n"
            "        activeJob = null\n"
            "        CloudStreamLiveLinkHub.notifyPlaybackStarted()\n",
            "StreamsRepository stop background CloudStream scrapes when playback starts",
        )
        changed |= _replace_once(
            streams_repo,
            "    fun clear() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        activeJob?.cancel()\n"
            "        activeJob = null\n",
            "    fun clear() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        activeJob?.cancel()\n"
            "        activeJob = null\n"
            "        CloudStreamLiveLinkHub.notifyPlaybackStarted()\n",
            "StreamsRepository clear notifyPlaybackStarted",
        )
        if changed:
            patched.append(str(streams_repo.relative_to(root)))

    # -------------------------------------------------------------------------
    # 7. PlayerStreamsRepository.kt + All 11 Player Call Sites (`Player > Source`, etc.):
    #    - Pass parentMetaId, parentMetaType, and searchTitle at every call site
    #    - Progressive live CloudStream link display in `Player > Source` & Episode Streams
    #    - 90s timeout + 8 permits + async MetaDetailsRepository.fetch fallback
    # -------------------------------------------------------------------------
    player_streams_repo = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerStreamsRepository.kt"
    if player_streams_repo.is_file():
        changed = False
        changed |= _replace_once(
            player_streams_repo,
            "import com.nuvio.app.features.cloudstream.CloudStreamRepository\n"
            "import com.nuvio.app.features.cloudstream.parseCloudStreamRouteId\n"
            "import com.nuvio.app.features.streams.buildCloudStreamSearchRequest\n"
            "import com.nuvio.app.features.streams.cloudStreamProviderGroupsForRequest\n"
            "import com.nuvio.app.features.streams.resolveCloudStreamProviderStreams\n",
            "import com.nuvio.app.features.cloudstream.CloudStreamLiveLinkHub\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamRepository\n"
            "import com.nuvio.app.features.cloudstream.parseCloudStreamRouteId\n"
            "import com.nuvio.app.features.streams.buildCloudStreamSearchRequest\n"
            "import com.nuvio.app.features.streams.cloudStreamProviderGroupsForRequest\n"
            "import com.nuvio.app.features.streams.loadCloudStreamRouteProgressive\n"
            "import com.nuvio.app.features.streams.resolveCloudStreamProviderStreams\n",
            "PlayerStreamsRepository CloudStream live imports",
        )
        changed |= _replace_once(
            player_streams_repo,
            "    private val cloudStreamSemaphore = Semaphore(4)\n"
            "    private const val PLAYER_STREAM_PROVIDER_TIMEOUT_MS = 35_000L\n",
            "    private val cloudStreamSemaphore = Semaphore(8)\n"
            "    private const val PLAYER_STREAM_PROVIDER_TIMEOUT_MS = 90_000L\n",
            "PlayerStreamsRepository 90s timeout & 8 permits",
        )
        changed |= _replace_once(
            player_streams_repo,
            "    fun stopSourcesLoading() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        cancelSourceJob()\n"
            "    }\n\n"
            "    fun pauseSearchForPlayback() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        cancelSourceJob()\n"
            "        cancelEpisodeStreamsJob()\n"
            "    }\n",
            "    fun stopSourcesLoading() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        cancelSourceJob()\n"
            "        if (episodeStreamsJob?.isActive != true) {\n"
            "            CloudStreamLiveLinkHub.notifyPlaybackStarted()\n"
            "        }\n"
            "    }\n\n"
            "    fun pauseSearchForPlayback() {\n"
            "        PluginRepository.setLocalPluginSearchPaused(true)\n"
            "        cancelSourceJob()\n"
            "        cancelEpisodeStreamsJob()\n"
            "        CloudStreamLiveLinkHub.notifyPlaybackStarted()\n"
            "    }\n",
            "PlayerStreamsRepository notifyPlaybackStarted on stop/pause",
        )
        changed |= _replace_once(
            player_streams_repo,
            "        val cloudStreamSearchRequest = buildCloudStreamSearchRequest(\n"
            "            type = type,\n"
            "            videoId = videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            parentMetaType = parentMetaType,\n"
            "            season = season,\n"
            "            episode = episode,\n"
            "            searchTitle = searchTitle,\n"
            "        )\n",
            "        CloudStreamRepository.initialize()\n"
            "        val initialCloudStreamSearchRequest = buildCloudStreamSearchRequest(\n"
            "            type = type,\n"
            "            videoId = videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            parentMetaType = parentMetaType,\n"
            "            season = season,\n"
            "            episode = episode,\n"
            "            searchTitle = searchTitle,\n"
            "        )\n"
            "        val cloudStreamSearchRequest = initialCloudStreamSearchRequest\n",
            "PlayerStreamsRepository initialize CloudStreamRepository before provider group resolution",
        )
        changed |= _replace_once(
            player_streams_repo,
            "            val job = scope.launch {\n"
            "                val result = runCatching {\n"
            "                    withTimeoutOrNull(PLAYER_STREAM_PROVIDER_TIMEOUT_MS) {\n"
            "                        CloudStreamRepository.loadLinks(cloudStreamRoute.providerId, cloudStreamRoute.data)\n"
            "                    } ?: error(\"$providerName timed out\")\n"
            "                }.fold(\n"
            "                    onSuccess = { it },\n"
            "                    onFailure = { Result.failure(it) },\n"
            "                )\n"
            "                if (requestKeyHolder() != requestKey) return@launch\n"
            "                result.fold(\n"
            "                    onSuccess = { sources ->\n"
            "                        val streams = cloudStreamSourcesToStreamItems(\n"
            "                            providerId = cloudStreamRoute.providerId,\n"
            "                            providerName = providerName,\n"
            "                            sources = sources,\n"
            "                        )\n",
            "            val job = scope.launch {\n"
            "                CloudStreamLiveLinkHub.onPlayerLoadStarted()\n"
            "                val result = try {\n"
            "                    loadCloudStreamRouteProgressive(\n"
            "                        providerId = cloudStreamRoute.providerId,\n"
            "                        providerName = providerName,\n"
            "                        linkData = cloudStreamRoute.data,\n"
            "                        timeoutMs = PLAYER_STREAM_PROVIDER_TIMEOUT_MS,\n"
            "                        forceRefresh = forceRefresh,\n"
            "                        onProgress = { partialStreams ->\n"
            "                            if (requestKeyHolder() != requestKey || partialStreams.isEmpty()) return@loadCloudStreamRouteProgressive\n"
            "                            val presentedPartial = StreamBadgePresentation.apply(\n"
            "                                groups = listOf(\n"
            "                                    AddonStreamGroup(\n"
            "                                        addonName = providerName,\n"
            "                                        addonId = providerAddonId,\n"
            "                                        streams = partialStreams.sortedForGroupedDisplay(),\n"
            "                                        isLoading = true,\n"
            "                                    ),\n"
            "                                ),\n"
            "                                rules = streamBadgeRules,\n"
            "                            )\n"
            "                            stateFlow.update { current ->\n"
            "                                val existing = current.groups.firstOrNull { it.addonId == providerAddonId }\n"
            "                                if (existing != null && !existing.isLoading) return@update current\n"
            "                                current.copy(\n"
            "                                    groups = presentedPartial,\n"
            "                                    activeAddonIds = setOf(providerAddonId),\n"
            "                                    isAnyLoading = true,\n"
            "                                    emptyStateReason = null,\n"
            "                                )\n"
            "                            }\n"
            "                        },\n"
            "                    )\n"
            "                } finally {\n"
            "                    CloudStreamLiveLinkHub.onPlayerLoadFinished()\n"
            "                }\n"
            "                if (requestKeyHolder() != requestKey) return@launch\n"
            "                result.fold(\n"
            "                    onSuccess = { rawStreams ->\n"
            "                        val streams = rawStreams.sortedForGroupedDisplay()\n",
            "PlayerStreamsRepository progressive streaming for direct CloudStream route",
        )
        changed |= _replace_once(
            player_streams_repo,
            "            fun publishStreamGroup(group: AddonStreamGroup) {\n",
            "            fun publishPartialCloudStreamGroup(partialGroup: AddonStreamGroup) {\n"
            "                if (partialGroup.streams.isEmpty()) return\n"
            "                val presented = presentStreamGroup(partialGroup)\n"
            "                stateFlow.update { current ->\n"
            "                    val target = current.groups.firstOrNull { it.addonId == presented.addonId }\n"
            "                    if (target != null && !target.isLoading) return@update current\n"
            "                    val updated = StreamAutoPlaySelector.orderAddonStreams(\n"
            "                        groups = current.groups.map { g ->\n"
            "                            if (g.addonId == presented.addonId) {\n"
            "                                presented.copy(isLoading = true, error = null)\n"
            "                            } else {\n"
            "                                g\n"
            "                            }\n"
            "                        },\n"
            "                        installedOrder = installedAddonOrder,\n"
            "                        preferredGroupIds = preferredGroupIds,\n"
            "                    )\n"
            "                    val anyLoading = updated.any { it.isLoading }\n"
            "                    current.copy(\n"
            "                        groups = updated,\n"
            "                        isAnyLoading = anyLoading,\n"
            "                        emptyStateReason = updated.toEmptyStateReason(anyLoading),\n"
            "                    )\n"
            "                }\n"
            "            }\n\n"
            "            fun publishStreamGroup(group: AddonStreamGroup) {\n",
            "PlayerStreamsRepository publishPartialCloudStreamGroup helper",
        )
        changed |= _replace_once(
            player_streams_repo,
            "            cloudStreamProviderGroups.forEach { providerGroup ->\n"
            "                launch {\n"
            "                    val group = withTimeoutOrNull(PLAYER_STREAM_PROVIDER_TIMEOUT_MS) {\n"
            "                        cloudStreamSemaphore.withPermit {\n"
            "                            resolveCloudStreamProviderStreams(\n"
            "                                providerGroup = providerGroup,\n"
            "                                request = cloudStreamSearchRequest,\n"
            "                            )\n"
            "                        }\n"
            "                    } ?: AddonStreamGroup(\n",
            "            cloudStreamProviderGroups.forEach { providerGroup ->\n"
            "                launch {\n"
            "                    CloudStreamLiveLinkHub.onPlayerLoadStarted()\n"
            "                    val effectiveRequest = cloudStreamSearchRequest ?: run {\n"
            "                        val fallbackMetaId = parentMetaId?.takeIf { it.isNotBlank() }\n"
            "                            ?: videoId.substringBefore(':').takeIf { it.isNotBlank() } ?: videoId\n"
            "                        val fallbackMetaType = parentMetaType?.takeIf { it.isNotBlank() } ?: type\n"
            "                        runCatchingUnlessCancelled {\n"
            "                            MetaDetailsRepository.fetch(fallbackMetaType, fallbackMetaId)\n"
            "                        }\n"
            "                        buildCloudStreamSearchRequest(\n"
            "                            type = type,\n"
            "                            videoId = videoId,\n"
            "                            parentMetaId = fallbackMetaId,\n"
            "                            parentMetaType = fallbackMetaType,\n"
            "                            season = season,\n"
            "                            episode = episode,\n"
            "                            searchTitle = searchTitle,\n"
            "                        )\n"
            "                    }\n"
            "                    val group = try {\n"
            "                        withTimeoutOrNull(PLAYER_STREAM_PROVIDER_TIMEOUT_MS) {\n"
            "                            cloudStreamSemaphore.withPermit {\n"
            "                                resolveCloudStreamProviderStreams(\n"
            "                                    providerGroup = providerGroup,\n"
            "                                    request = effectiveRequest,\n"
            "                                    forceRefresh = forceRefresh,\n"
            "                                    onProgress = { partialStreams ->\n"
            "                                        publishPartialCloudStreamGroup(\n"
            "                                            AddonStreamGroup(\n"
            "                                                addonName = providerGroup.addonName,\n"
            "                                                addonId = providerGroup.addonId,\n"
            "                                                streams = partialStreams.sortedForGroupedDisplay(),\n"
            "                                                isLoading = true,\n"
            "                                            ),\n"
            "                                        )\n"
            "                                    },\n"
            "                                )\n"
            "                            }\n"
            "                        }\n"
            "                    } finally {\n"
            "                        CloudStreamLiveLinkHub.onPlayerLoadFinished()\n"
            "                    } ?: AddonStreamGroup(\n",
            "PlayerStreamsRepository progressive CloudStream execution & metadata fetch fallback",
        )
        if changed:
            patched.append(str(player_streams_repo.relative_to(root)))

    # Pass parentMetaId, parentMetaType, and searchTitle at all 11 PlayerStreamsRepository call sites
    src_actions = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeSourceActions.kt"
    if src_actions.is_file():
        changed = False
        changed |= _replace_once(
            src_actions,
            "                    PlayerStreamsRepository.loadSources(\n"
            "                        type = contentType ?: parentMetaType,\n"
            "                        videoId = vid,\n"
            "                        season = activeSeasonNumber,\n"
            "                        episode = activeEpisodeNumber,\n"
            "                        forceRefresh = true,\n"
            "                    )\n",
            "                    PlayerStreamsRepository.loadSources(\n"
            "                        type = contentType ?: parentMetaType,\n"
            "                        videoId = vid,\n"
            "                        parentMetaId = parentMetaId,\n"
            "                        parentMetaType = parentMetaType,\n"
            "                        season = activeSeasonNumber,\n"
            "                        episode = activeEpisodeNumber,\n"
            "                        searchTitle = playerMeta?.name ?: title,\n"
            "                        forceRefresh = true,\n"
            "                    )\n",
            "PlayerScreenRuntimeSourceActions switchToSource onStale pass CloudStream context",
        )
        changed |= _replace_once(
            src_actions,
            "                PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                    type = contentType ?: parentMetaType,\n"
            "                    videoId = episode.id,\n"
            "                    season = episode.season,\n"
            "                    episode = episode.episode,\n"
            "                    forceRefresh = true,\n"
            "                )\n",
            "                PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                    type = contentType ?: parentMetaType,\n"
            "                    videoId = episode.id,\n"
            "                    parentMetaId = parentMetaId,\n"
            "                    parentMetaType = parentMetaType,\n"
            "                    season = episode.season,\n"
            "                    episode = episode.episode,\n"
            "                    searchTitle = playerMeta?.name ?: title,\n"
            "                    forceRefresh = true,\n"
            "                )\n",
            "PlayerScreenRuntimeSourceActions switchToEpisodeStream onStale pass CloudStream context",
        )
        changed |= _replace_once(
            src_actions,
            "    PlayerStreamsRepository.loadSources(\n"
            "        type = contentType ?: parentMetaType,\n"
            "        videoId = vid,\n"
            "        season = activeSeasonNumber,\n"
            "        episode = activeEpisodeNumber,\n"
            "    )\n",
            "    PlayerStreamsRepository.loadSources(\n"
            "        type = contentType ?: parentMetaType,\n"
            "        videoId = vid,\n"
            "        parentMetaId = parentMetaId,\n"
            "        parentMetaType = parentMetaType,\n"
            "        season = activeSeasonNumber,\n"
            "        episode = activeEpisodeNumber,\n"
            "        searchTitle = playerMeta?.name ?: title,\n"
            "    )\n",
            "PlayerScreenRuntimeSourceActions openSourcesPanel pass CloudStream context",
        )
        changed |= _replace_once(
            src_actions,
            "    scope.launchPlayerNextEpisodeAutoPlay(\n"
            "        previousJob = nextEpisodeAutoPlayJob,\n"
            "        nextEpisodeInfo = nextEpisodeInfo,\n"
            "        allEpisodes = playerMetaVideos,\n"
            "        parentMetaId = parentMetaId,\n"
            "        parentMetaType = parentMetaType,\n"
            "        contentType = contentType,\n",
            "    scope.launchPlayerNextEpisodeAutoPlay(\n"
            "        previousJob = nextEpisodeAutoPlayJob,\n"
            "        nextEpisodeInfo = nextEpisodeInfo,\n"
            "        allEpisodes = playerMetaVideos,\n"
            "        parentMetaId = parentMetaId,\n"
            "        parentMetaType = parentMetaType,\n"
            "        contentType = contentType,\n"
            "        searchTitle = playerMeta?.name ?: title,\n",
            "PlayerScreenRuntimeSourceActions playNextEpisode pass searchTitle",
        )
        if changed:
            patched.append(str(src_actions.relative_to(root)))

    runtime_ui = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeUi.kt"
    if runtime_ui.is_file():
        changed = False
        changed |= _replace_once(
            runtime_ui,
            "                PlayerStreamsRepository.loadSources(\n"
            "                    type = contentType ?: parentMetaType,\n"
            "                    videoId = vid,\n"
            "                    season = activeSeasonNumber,\n"
            "                    episode = activeEpisodeNumber,\n"
            "                    forceRefresh = true,\n"
            "                )\n",
            "                PlayerStreamsRepository.loadSources(\n"
            "                    type = contentType ?: parentMetaType,\n"
            "                    videoId = vid,\n"
            "                    parentMetaId = parentMetaId,\n"
            "                    parentMetaType = parentMetaType,\n"
            "                    season = activeSeasonNumber,\n"
            "                    episode = activeEpisodeNumber,\n"
            "                    searchTitle = playerMeta?.name ?: title,\n"
            "                    forceRefresh = true,\n"
            "                )\n",
            "PlayerScreenRuntimeUi onReloadSources pass CloudStream context",
        )
        changed |= _replace_once(
            runtime_ui,
            "            PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                type = contentType ?: parentMetaType,\n"
            "                videoId = episode.id,\n"
            "                season = episode.season,\n"
            "                episode = episode.episode,\n"
            "            )\n",
            "            PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                type = contentType ?: parentMetaType,\n"
            "                videoId = episode.id,\n"
            "                parentMetaId = parentMetaId,\n"
            "                parentMetaType = parentMetaType,\n"
            "                season = episode.season,\n"
            "                episode = episode.episode,\n"
            "                searchTitle = playerMeta?.name ?: title,\n"
            "            )\n",
            "PlayerScreenRuntimeUi onEpisodeStreamsRequested pass CloudStream context",
        )
        changed |= _replace_once(
            runtime_ui,
            "                PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                    type = contentType ?: parentMetaType,\n"
            "                    videoId = episode.id,\n"
            "                    season = episode.season,\n"
            "                    episode = episode.episode,\n"
            "                    forceRefresh = true,\n"
            "                )\n",
            "                PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                    type = contentType ?: parentMetaType,\n"
            "                    videoId = episode.id,\n"
            "                    parentMetaId = parentMetaId,\n"
            "                    parentMetaType = parentMetaType,\n"
            "                    season = episode.season,\n"
            "                    episode = episode.episode,\n"
            "                    searchTitle = playerMeta?.name ?: title,\n"
            "                    forceRefresh = true,\n"
            "                )\n",
            "PlayerScreenRuntimeUi onReloadEpisodeStreams pass CloudStream context",
        )
        if changed:
            patched.append(str(runtime_ui.relative_to(root)))

    src_fallback = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeSourceFallback.kt"
    if src_fallback.is_file():
        if _replace_once(
            src_fallback,
            "            PlayerStreamsRepository.loadSources(\n"
            "                type = contentType ?: parentMetaType,\n"
            "                videoId = videoId,\n"
            "                season = season,\n"
            "                episode = episode,\n"
            "            )\n",
            "            PlayerStreamsRepository.loadSources(\n"
            "                type = contentType ?: parentMetaType,\n"
            "                videoId = videoId,\n"
            "                parentMetaId = parentMetaId,\n"
            "                parentMetaType = parentMetaType,\n"
            "                season = season,\n"
            "                episode = episode,\n"
            "                searchTitle = playerMeta?.name ?: title,\n"
            "            )\n",
            "PlayerScreenRuntimeSourceFallback loadSources pass CloudStream context",
        ):
            patched.append(str(src_fallback.relative_to(root)))

    next_auto = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerNextEpisodeAutoPlay.kt"
    if next_auto.is_file():
        changed = False
        changed |= _replace_once(
            next_auto,
            "import com.nuvio.app.features.downloads.DownloadsRepository\n",
            "import com.nuvio.app.features.downloads.DownloadsRepository\n"
            "import com.nuvio.app.features.downloads.LocalEpisodePlaylistRegistry\n",
            "PlayerNextEpisodeAutoPlay import LocalEpisodePlaylistRegistry",
        )
        changed |= _replace_once(
            next_auto,
            "    parentMetaId: String,\n"
            "    parentMetaType: String,\n"
            "    contentType: String?,\n",
            "    parentMetaId: String,\n"
            "    parentMetaType: String,\n"
            "    contentType: String?,\n"
            "    searchTitle: String? = null,\n",
            "PlayerNextEpisodeAutoPlay add searchTitle param",
        )
        changed |= _replace_once(
            next_auto,
            "        PlayerStreamsRepository.loadEpisodeStreams(\n"
            "            type = type,\n"
            "            videoId = nextVideo.id,\n"
            "            season = nextVideo.season,\n"
            "            episode = nextVideo.episode,\n"
            "        )\n",
            "        PlayerStreamsRepository.loadEpisodeStreams(\n"
            "            type = type,\n"
            "            videoId = nextVideo.id,\n"
            "            parentMetaId = parentMetaId,\n"
            "            parentMetaType = parentMetaType,\n"
            "            season = nextVideo.season,\n"
            "            episode = nextVideo.episode,\n"
            "            searchTitle = searchTitle,\n"
            "        )\n",
            "PlayerNextEpisodeAutoPlay loadEpisodeStreams pass CloudStream context",
        )
        changed |= _replace_once(
            next_auto,
            "            PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                type = type,\n"
            "                videoId = nextVideo.id,\n"
            "                season = nextVideo.season,\n"
            "                episode = nextVideo.episode,\n"
            "                forceRefresh = true,\n"
            "            )\n",
            "            PlayerStreamsRepository.loadEpisodeStreams(\n"
            "                type = type,\n"
            "                videoId = nextVideo.id,\n"
            "                parentMetaId = parentMetaId,\n"
            "                parentMetaType = parentMetaType,\n"
            "                season = nextVideo.season,\n"
            "                episode = nextVideo.episode,\n"
            "                searchTitle = searchTitle,\n"
            "                forceRefresh = true,\n"
            "            )\n",
            "PlayerNextEpisodeAutoPlay retry loadEpisodeStreams pass CloudStream context",
        )
        changed |= _replace_once(
            next_auto,
            "        PlayerStreamsRepository.loadEpisodeStreams(\n"
            "            type = type,\n"
            "            videoId = nextEp.videoId,\n"
            "            season = nextEp.season,\n"
            "            episode = nextEp.episode\n"
            "        )\n",
            "        if (\n"
            "            parentMetaId.startsWith(\"local_series:\") ||\n"
            "            parentMetaId.startsWith(\"local:\") ||\n"
            "            LocalEpisodePlaylistRegistry.findEpisode(\n"
            "                parentMetaId = parentMetaId,\n"
            "                activeSourceUrl = activeSourceUrl,\n"
            "                videoId = nextEp.videoId,\n"
            "                season = nextEp.season,\n"
            "                episode = nextEp.episode,\n"
            "            ) != null\n"
            "        ) {\n"
            "            return@launch\n"
            "        }\n"
            "        PlayerStreamsRepository.loadEpisodeStreams(\n"
            "            type = type,\n"
            "            videoId = nextEp.videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            parentMetaType = parentMetaType,\n"
            "            season = nextEp.season,\n"
            "            episode = nextEp.episode,\n"
            "            searchTitle = playerMeta?.name ?: title,\n"
            "        )\n",
            "PlayerNextEpisodeAutoPlay preloadNextEpisodeSources pass CloudStream context & skip local",
        )
        if changed:
            patched.append(str(next_auto.relative_to(root)))

    # -------------------------------------------------------------------------
    # 8. Next Episode Button & Episode Switching for Local Storage Folder Seasons:
    #    - Enhanced LocalMediaParser (leading episode numbers in season folders + show folders)
    #    - LocalPlaylistEpisode + LocalEpisodePlaylistRegistry in LocalFolderVideosPlatform.kt
    #    - DownloadsScreen & LocalVideoPlayerActivity local season playlist registration
    #    - PlayerScreenRuntimeEffects, PlayerScreenRuntimeSourceActions, PlayerScreenRuntimeUi,
    #      and PlayerControls (including Legacy Layout pill button)
    # -------------------------------------------------------------------------
    local_platform_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.kt"
    if local_platform_kt.is_file():
        changed = False
        changed |= _replace_once(
            local_platform_kt,
            "import com.nuvio.app.core.deeplink.LocalSidecarSubtitleItem\n"
            "import kotlinx.coroutines.flow.StateFlow\n",
            "import com.nuvio.app.core.deeplink.LocalSidecarSubtitleItem\n"
            "import kotlinx.coroutines.flow.MutableStateFlow\n"
            "import kotlinx.coroutines.flow.StateFlow\n"
            "import kotlinx.coroutines.flow.asStateFlow\n"
            "import kotlinx.coroutines.flow.update\n",
            "LocalFolderVideosPlatform MutableStateFlow imports",
        )
        changed |= _replace_once(
            local_platform_kt,
            "    private val EP_ONLY_REGEX = Regex(\n"
            "        \"\"\"(?i)(.*?)[\\s._\\-\\[\\(]*(?:Episode|Ep|E)[\\s._\\-]*(\\d{1,3})\\b(.*)\"\"\",\n"
            "    )\n",
            "    private val EP_ONLY_REGEX = Regex(\n"
            "        \"\"\"(?i)(.*?)[\\s._\\-\\[\\(]*(?:Episode|Ep|Part|E)[\\s._\\-]*(\\d{1,3})\\b(.*)\"\"\",\n"
            "    )\n"
            "    private val LEADING_EP_IN_SEASON_REGEX = Regex(\n"
            "        \"\"\"^\\s*(\\d{1,3})(?:[\\s._\\-:]+(.*))?$\"\"\",\n"
            "    )\n",
            "LocalMediaParser LEADING_EP_IN_SEASON_REGEX",
        )
        changed |= _replace_once(
            local_platform_kt,
            "        if (folderSeason != null) {\n"
            "            EP_ONLY_REGEX.matchEntire(rawStem)?.let { m ->\n"
            "                val rawShow = m.groupValues[1]\n"
            "                val ep = m.groupValues[2].toIntOrNull()\n"
            "                val tail = m.groupValues[3]\n"
            "                val (showTitle, year) = extractTitleAndYear(\n"
            "                    rawShow.ifBlank { inferredSeriesFolderTitle.orEmpty() },\n"
            "                    fallback = inferredSeriesFolderTitle,\n"
            "                )\n"
            "                return LocalParsedMediaInfo(\n"
            "                    cleanTitle = showTitle,\n"
            "                    year = year,\n"
            "                    isSeries = true,\n"
            "                    seasonNumber = folderSeason,\n"
            "                    episodeNumber = ep,\n"
            "                    episodeTitle = cleanEpisodeSubtitle(tail),\n"
            "                )\n"
            "            }\n"
            "        }\n",
            "        val nonGenericParent = parentFolderName?.let(::cleanName)?.takeIf { it.isNotBlank() && !isGenericFolderName(it) }\n"
            "        if (folderSeason != null || nonGenericParent != null) {\n"
            "            EP_ONLY_REGEX.matchEntire(rawStem)?.let { m ->\n"
            "                val rawShow = m.groupValues[1]\n"
            "                val ep = m.groupValues[2].toIntOrNull()\n"
            "                val tail = m.groupValues[3]\n"
            "                if (ep != null && ep in 1..999) {\n"
            "                    val fallbackSeries = inferredSeriesFolderTitle ?: nonGenericParent\n"
            "                    val (showTitle, year) = extractTitleAndYear(\n"
            "                        rawShow.ifBlank { fallbackSeries.orEmpty() },\n"
            "                        fallback = fallbackSeries,\n"
            "                    )\n"
            "                    return LocalParsedMediaInfo(\n"
            "                        cleanTitle = showTitle,\n"
            "                        year = year,\n"
            "                        isSeries = true,\n"
            "                        seasonNumber = folderSeason ?: 1,\n"
            "                        episodeNumber = ep,\n"
            "                        episodeTitle = cleanEpisodeSubtitle(tail),\n"
            "                    )\n"
            "                }\n"
            "            }\n"
            "        }\n\n"
            "        if (folderSeason != null) {\n"
            "            LEADING_EP_IN_SEASON_REGEX.matchEntire(rawStem)?.let { m ->\n"
            "                val ep = m.groupValues[1].toIntOrNull()\n"
            "                val tail = m.groupValues[2]\n"
            "                if (ep != null && ep in 1..999) {\n"
            "                    val fallbackSeries = inferredSeriesFolderTitle ?: nonGenericParent\n"
            "                    val (showTitle, year) = extractTitleAndYear(\n"
            "                        fallbackSeries.orEmpty(),\n"
            "                        fallback = fallbackSeries,\n"
            "                    )\n"
            "                    return LocalParsedMediaInfo(\n"
            "                        cleanTitle = showTitle,\n"
            "                        year = year,\n"
            "                        isSeries = true,\n"
            "                        seasonNumber = folderSeason,\n"
            "                        episodeNumber = ep,\n"
            "                        episodeTitle = cleanEpisodeSubtitle(tail),\n"
            "                    )\n"
            "                }\n"
            "            }\n"
            "        }\n",
            "LocalMediaParser folder season & show folder episode patterns",
        )
        changed |= _replace_once(
            local_platform_kt,
            "internal expect object LocalFolderVideosPlatform {\n",
            "data class LocalPlaylistEpisode(\n"
            "    val videoId: String,\n"
            "    val uri: String,\n"
            "    val title: String,\n"
            "    val filename: String,\n"
            "    val mimeType: String? = null,\n"
            "    val seasonNumber: Int,\n"
            "    val episodeNumber: Int,\n"
            "    val episodeTitle: String? = null,\n"
            "    val thumbnailUrl: String? = null,\n"
            "    val sidecarSubtitles: List<LocalSidecarSubtitleItem> = emptyList(),\n"
            ")\n\n"
            "object LocalEpisodePlaylistRegistry {\n"
            "    private val _playlistsByKey = MutableStateFlow<Map<String, List<LocalPlaylistEpisode>>>(emptyMap())\n"
            "    val playlistsByKey: StateFlow<Map<String, List<LocalPlaylistEpisode>>> = _playlistsByKey.asStateFlow()\n\n"
            "    fun registerFromItems(parentMetaId: String, items: List<LocalVideoFileItem>) {\n"
            "        if (items.isEmpty()) return\n"
            "        val sorted = items.sortedWith(\n"
            "            compareBy<LocalVideoFileItem> { it.seasonNumber ?: 1 }\n"
            "                .thenBy { it.episodeNumber ?: Int.MAX_VALUE }\n"
            "                .thenBy { it.filename.lowercase() },\n"
            "        )\n"
            "        val perSeasonCounter = HashMap<Int, Int>()\n"
            "        val mapped = sorted.map { item ->\n"
            "            val s = (item.seasonNumber ?: 1).coerceAtLeast(1)\n"
            "            val nextFallback = (perSeasonCounter[s] ?: 0) + 1\n"
            "            val e = (item.episodeNumber ?: nextFallback).coerceAtLeast(1)\n"
            "            perSeasonCounter[s] = maxOf(nextFallback, e)\n"
            "            LocalPlaylistEpisode(\n"
            "                videoId = item.syntheticVideoId,\n"
            "                uri = item.uri,\n"
            "                title = item.title,\n"
            "                filename = item.filename,\n"
            "                mimeType = item.mimeType,\n"
            "                seasonNumber = s,\n"
            "                episodeNumber = e,\n"
            "                episodeTitle = item.episodeTitle,\n"
            "                thumbnailUrl = item.episodeThumbnailUrl ?: item.backgroundUrl ?: item.posterUrl,\n"
            "                sidecarSubtitles = item.sidecarSubtitles,\n"
            "            )\n"
            "        }\n"
            "        registerPlaylist(parentMetaId, mapped)\n"
            "    }\n\n"
            "    fun registerPlaylist(parentMetaId: String, episodes: List<LocalPlaylistEpisode>) {\n"
            "        if (parentMetaId.isBlank() || episodes.isEmpty()) return\n"
            "        val deduped = episodes\n"
            "            .distinctBy { it.uri }\n"
            "            .sortedWith(compareBy<LocalPlaylistEpisode> { it.seasonNumber }.thenBy { it.episodeNumber })\n"
            "        _playlistsByKey.update { current -> current + (parentMetaId to deduped) }\n"
            "    }\n\n"
            "    fun episodesForPlayback(\n"
            "        parentMetaId: String,\n"
            "        activeSourceUrl: String,\n"
            "    ): List<LocalPlaylistEpisode> {\n"
            "        val isLocalSource = activeSourceUrl.startsWith(\"content://\", ignoreCase = true) ||\n"
            "            activeSourceUrl.startsWith(\"file://\", ignoreCase = true)\n"
            "        if (!isLocalSource && !parentMetaId.startsWith(\"local_series:\") && !parentMetaId.startsWith(\"local:\")) {\n"
            "            return emptyList()\n"
            "        }\n"
            "        _playlistsByKey.value[parentMetaId]?.takeIf { it.size > 1 }?.let { return it }\n"
            "        _playlistsByKey.value.values.firstOrNull { list ->\n"
            "            list.size > 1 && list.any { it.uri == activeSourceUrl }\n"
            "        }?.let { return it }\n\n"
            "        val scanned = LocalFolderVideosPlatform.state.value.videos\n"
            "        if (scanned.isEmpty()) return emptyList()\n"
            "        val (seriesGroups, _) = LocalMediaParser.groupVideos(scanned)\n"
            "        val matchingGroup = seriesGroups.firstOrNull { grp ->\n"
            "            grp.episodes.any { ep ->\n"
            "                ep.uri == activeSourceUrl || ep.effectiveParentMetaId == parentMetaId\n"
            "            } || \"local_series:${grp.key}\" == parentMetaId\n"
            "        }\n"
            "        if (matchingGroup != null && matchingGroup.episodes.isNotEmpty()) {\n"
            "            registerFromItems(parentMetaId.ifBlank { \"local_series:${matchingGroup.key}\" }, matchingGroup.episodes)\n"
            "            return _playlistsByKey.value[parentMetaId.ifBlank { \"local_series:${matchingGroup.key}\" }].orEmpty()\n"
            "        }\n"
            "        return emptyList()\n"
            "    }\n\n"
            "    fun findEpisode(\n"
            "        parentMetaId: String,\n"
            "        activeSourceUrl: String,\n"
            "        videoId: String? = null,\n"
            "        season: Int? = null,\n"
            "        episode: Int? = null,\n"
            "    ): LocalPlaylistEpisode? {\n"
            "        val list = episodesForPlayback(parentMetaId, activeSourceUrl)\n"
            "        if (list.isEmpty()) return null\n"
            "        if (!videoId.isNullOrBlank()) {\n"
            "            list.firstOrNull { it.videoId == videoId }?.let { return it }\n"
            "        }\n"
            "        if (season != null && episode != null) {\n"
            "            list.firstOrNull { it.seasonNumber == season && it.episodeNumber == episode }?.let { return it }\n"
            "        }\n"
            "        return null\n"
            "    }\n"
            "}\n\n"
            "internal expect object LocalFolderVideosPlatform {\n",
            "LocalFolderVideosPlatform LocalEpisodePlaylistRegistry",
        )
        if changed:
            patched.append(str(local_platform_kt.relative_to(root)))

    # Register LocalSeriesGroup playlist when tapping an episode in DownloadsScreen.kt
    dl_screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsScreen.kt"
    if dl_screen.is_file():
        if _replace_once(
            dl_screen,
            "    val playLocalVideo: (LocalVideoFileItem) -> Unit = { video ->\n"
            "        AppDeepLinkRepository.openLocalVideo(\n"
            "            uri = video.uri,\n"
            "            title = video.title,\n"
            "            filename = video.filename,\n"
            "            subtitle = video.folderName,\n"
            "            mimeType = video.mimeType,\n"
            "            poster = video.posterUrl,\n"
            "            background = video.backgroundUrl,\n"
            "            seasonNumber = video.seasonNumber,\n"
            "            episodeNumber = video.episodeNumber,\n",
            "    val playLocalVideo: (LocalVideoFileItem) -> Unit = { video ->\n"
            "        val matchingSeries = if (video.isSeries) {\n"
            "            localSeriesGroups.firstOrNull { grp ->\n"
            "                grp.key == (video.seriesKey ?: LocalMediaParser.canonicalSeriesKey(video.title)) ||\n"
            "                    grp.episodes.any { it.uri == video.uri }\n"
            "            }\n"
            "        } else null\n"
            "        if (matchingSeries != null) {\n"
            "            LocalEpisodePlaylistRegistry.registerFromItems(video.effectiveParentMetaId, matchingSeries.episodes)\n"
            "        }\n"
            "        val resolvedEntry = matchingSeries?.let {\n"
            "            LocalEpisodePlaylistRegistry.findEpisode(\n"
            "                parentMetaId = video.effectiveParentMetaId,\n"
            "                activeSourceUrl = video.uri,\n"
            "                videoId = video.syntheticVideoId,\n"
            "            )\n"
            "        }\n"
            "        AppDeepLinkRepository.openLocalVideo(\n"
            "            uri = video.uri,\n"
            "            title = video.title,\n"
            "            filename = video.filename,\n"
            "            subtitle = video.folderName,\n"
            "            mimeType = video.mimeType,\n"
            "            poster = video.posterUrl,\n"
            "            background = video.backgroundUrl,\n"
            "            seasonNumber = resolvedEntry?.seasonNumber ?: (if (video.isSeries) (video.seasonNumber ?: 1) else video.seasonNumber),\n"
            "            episodeNumber = resolvedEntry?.episodeNumber ?: (if (video.isSeries) (video.episodeNumber ?: 1) else video.episodeNumber),\n",
            "DownloadsScreen register LocalEpisodePlaylistRegistry on playLocalVideo",
        ):
            patched.append(str(dl_screen.relative_to(root)))

    # Enhance LocalVideoPlayerActivity.kt so 'Open with Nuvio' discovers sibling season files too
    local_player_act = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/LocalVideoPlayerActivity.kt"
    if local_player_act.is_file():
        _write_text(
            root,
            "composeApp/src/androidMain/kotlin/com/nuvio/app/LocalVideoPlayerActivity.kt",
            r'''package com.nuvio.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.nuvio.app.core.ui.NuvioSheetBackdrop
import com.nuvio.app.core.ui.NuvioSheetBackdropHost
import com.nuvio.app.core.ui.NuvioToastController
import com.nuvio.app.core.ui.glass.rememberNuvioBackdrop
import com.nuvio.app.features.downloads.DownloadSubtitles
import com.nuvio.app.features.downloads.LocalEpisodePlaylistRegistry
import com.nuvio.app.features.downloads.LocalFolderVideosPlatform
import com.nuvio.app.features.downloads.LocalMediaParser
import com.nuvio.app.features.downloads.LocalPlaylistEpisode
import com.nuvio.app.features.player.ExternalPlayerPlatform
import com.nuvio.app.features.player.PlayerScreen
import com.nuvio.app.features.profiles.ProfileRepository
import com.nuvio.app.features.watchprogress.WatchProgressRepository
import java.io.File

class LocalVideoPlayerActivity : MainActivity() {
    private var activeIntent by mutableStateOf<Intent?>(null)
    private var intentNonce by mutableLongStateOf(0L)

    override fun onCreate(savedInstanceState: Bundle?) {
        LocalFolderVideosPlatform.initialize(applicationContext)
        activeIntent = intent
        intentNonce += 1L
        super.onCreate(savedInstanceState)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        activeIntent = intent
        intentNonce += 1L
    }

    override fun showContent() {
        setContent {
            val currentIntent = activeIntent
            val currentNonce = intentNonce
            val resolved = remember(currentIntent, currentNonce) {
                extractPlayableVideo(currentIntent)
            }
            if (resolved == null) {
                NuvioToastController.show("Unable to open selected video file")
                finish()
                return@setContent
            }

            val sheetBackdropSource = rememberNuvioBackdrop()
            val sheetBackdrop = remember(sheetBackdropSource) { NuvioSheetBackdrop(sheetBackdropSource) }

            NuvioSheetBackdropHost(sheetBackdrop = sheetBackdrop) {
                AppEnvironment(drawAppBackground = false) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color.Black),
                    ) {
                        key(currentNonce, resolved.uriString) {
                            PlayerScreen(
                                profileId = ProfileRepository.activeProfileId,
                                title = resolved.title,
                                sourceUrl = resolved.uriString,
                                externalSubtitles = DownloadSubtitles.localSubtitles(resolved.uriString),
                                streamType = resolved.cleanMimeType,
                                providerName = "Local Storage",
                                streamTitle = resolved.displayName,
                                streamSubtitle = "Local Storage",
                                onBack = { finish() },
                                onOpenInExternalPlayer = { request ->
                                    ExternalPlayerPlatform.open(request, null)
                                },
                                seasonNumber = resolved.seasonNumber,
                                episodeNumber = resolved.episodeNumber,
                                episodeTitle = resolved.episodeTitle,
                                contentType = resolved.contentType,
                                videoId = resolved.syntheticId,
                                parentMetaId = resolved.parentMetaId,
                                parentMetaType = resolved.contentType,
                                initialPositionMs = resolved.resumePositionMs,
                                initialProgressFraction = resolved.resumeFraction,
                                sourceFilename = resolved.displayName,
                            )
                        }
                    }
                }
            }
        }
        contentReady = true
    }

    private data class ResolvedExternalVideo(
        val uriString: String,
        val displayName: String,
        val title: String,
        val cleanMimeType: String?,
        val contentType: String,
        val seasonNumber: Int?,
        val episodeNumber: Int?,
        val episodeTitle: String?,
        val syntheticId: String,
        val parentMetaId: String,
        val resumePositionMs: Long,
        val resumeFraction: Float?,
    )

    private fun extractPlayableVideo(intent: Intent?): ResolvedExternalVideo? {
        if (intent == null) return null
        val uri: Uri = when (intent.action) {
            Intent.ACTION_SEND -> {
                @Suppress("DEPRECATION")
                (intent.getParcelableExtra(Intent.EXTRA_STREAM) as? Uri)
                    ?: intent.clipData?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.uri
                    ?: intent.data
            }
            else -> {
                intent.data
                    ?: intent.clipData?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.uri
            }
        } ?: return null

        val scheme = uri.scheme?.lowercase() ?: return null
        if (scheme != "content" && scheme != "file") return null

        if (scheme == "content" && (intent.flags and Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION) != 0) {
            runCatching {
                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
        }

        val displayName = LocalFolderVideosPlatform.resolveDisplayName(applicationContext, uri)
        val rawMime = intent.type?.trim()?.takeIf { it.isNotEmpty() && !it.endsWith("/*") }
            ?: runCatching { contentResolver.getType(uri)?.trim() }.getOrNull()
                ?.takeIf { it.isNotEmpty() && !it.endsWith("/*") && it != "application/octet-stream" }

        val uriString = uri.toString()
        val parentDirFile = if (scheme == "file") uri.path?.let(::File)?.parentFile else null
        val parsed = LocalMediaParser.parse(
            filename = displayName,
            parentFolderName = parentDirFile?.name,
            grandParentFolderName = parentDirFile?.parentFile?.name,
        )
        val syntheticId = "local:${uriString.hashCode().toUInt().toString(16)}"

        // Check scanned Local Storage Folders first, or scan sibling files when opened via file://
        val scannedVideos = LocalFolderVideosPlatform.state.value.videos
        val matchedScanned = scannedVideos.firstOrNull { it.uri == uriString || it.filename.equals(displayName, ignoreCase = true) }
        val seriesParentMetaId = when {
            matchedScanned != null && matchedScanned.isSeries -> {
                val (groups, _) = LocalMediaParser.groupVideos(scannedVideos)
                val grp = groups.firstOrNull { g -> g.episodes.any { it.uri == matchedScanned.uri } }
                if (grp != null) {
                    LocalEpisodePlaylistRegistry.registerFromItems(matchedScanned.effectiveParentMetaId, grp.episodes)
                }
                matchedScanned.effectiveParentMetaId
            }
            parsed.isSeries && parentDirFile != null && parentDirFile.isDirectory -> {
                val pId = "local_series:${LocalMediaParser.canonicalSeriesKey(parsed.cleanTitle)}"
                val videoExts = setOf("mp4", "mkv", "avi", "webm", "mov", "m4v", "ts", "m2ts", "flv", "wmv", "mpg", "mpeg")
                val siblings = parentDirFile.listFiles()
                    .orEmpty()
                    .filter { f -> f.isFile && f.extension.lowercase() in videoExts }
                    .mapNotNull { f ->
                        val p = LocalMediaParser.parse(f.name, parentDirFile.name, parentDirFile.parentFile?.name)
                        if (!p.isSeries || p.episodeNumber == null) return@mapNotNull null
                        val fUri = Uri.fromFile(f).toString()
                        LocalPlaylistEpisode(
                            videoId = "local:${fUri.hashCode().toUInt().toString(16)}",
                            uri = fUri,
                            title = p.cleanTitle,
                            filename = f.name,
                            seasonNumber = (p.seasonNumber ?: 1).coerceAtLeast(1),
                            episodeNumber = p.episodeNumber.coerceAtLeast(1),
                            episodeTitle = p.episodeTitle,
                        )
                    }
                if (siblings.size > 1) {
                    LocalEpisodePlaylistRegistry.registerPlaylist(pId, siblings)
                }
                pId
            }
            parsed.isSeries -> "local_series:${LocalMediaParser.canonicalSeriesKey(parsed.cleanTitle)}"
            else -> syntheticId
        }

        val isSeries = parsed.isSeries || (matchedScanned?.isSeries == true)
        val effectiveSeason = matchedScanned?.seasonNumber ?: parsed.seasonNumber ?: (if (isSeries) 1 else null)
        val effectiveEpisode = matchedScanned?.episodeNumber ?: parsed.episodeNumber ?: (if (isSeries) 1 else null)

        WatchProgressRepository.ensureLoaded()
        val resumeEntry = runCatching {
            WatchProgressRepository.progressForVideo(
                videoId = syntheticId,
                parentMetaId = seriesParentMetaId,
                seasonNumber = effectiveSeason,
                episodeNumber = effectiveEpisode,
            )?.takeIf { it.isResumable }
        }.getOrNull()

        return ResolvedExternalVideo(
            uriString = uriString,
            displayName = displayName,
            title = matchedScanned?.title ?: parsed.cleanTitle,
            cleanMimeType = rawMime,
            contentType = if (isSeries) "series" else "movie",
            seasonNumber = effectiveSeason,
            episodeNumber = effectiveEpisode,
            episodeTitle = matchedScanned?.episodeTitle ?: parsed.episodeTitle,
            syntheticId = matchedScanned?.syntheticVideoId ?: syntheticId,
            parentMetaId = seriesParentMetaId,
            resumePositionMs = resumeEntry?.lastPositionMs?.takeIf { it > 0L } ?: 0L,
            resumeFraction = resumeEntry?.progressFraction?.takeIf { it > 0f },
        )
    }
}
''',
            patched,
        )

    # Wire LocalEpisodePlaylistRegistry into PlayerScreenRuntimeEffects.kt
    runtime_effects = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeEffects.kt"
    if runtime_effects.is_file():
        changed = False
        changed |= _replace_once(
            runtime_effects,
            "import com.nuvio.app.features.details.MetaDetailsRepository\n",
            "import com.nuvio.app.features.details.MetaDetailsRepository\n"
            "import com.nuvio.app.features.details.MetaVideo\n"
            "import com.nuvio.app.features.downloads.LocalEpisodePlaylistRegistry\n"
            "import com.nuvio.app.features.downloads.LocalFolderVideosPlatform\n",
            "PlayerScreenRuntimeEffects local playlist imports",
        )
        changed |= _replace_once(
            runtime_effects,
            "    LaunchedEffect(parentMetaType, parentMetaId) {\n"
            "        playerMeta = MetaDetailsRepository.peek(parentMetaType, parentMetaId)\n"
            "        playerMetaVideos = playerMeta?.videos.orEmpty()\n"
            "        if (playerMetaVideos.isEmpty()) {\n"
            "            MetaDetailsRepository.fetch(parentMetaType, parentMetaId)?.let { meta ->\n"
            "                playerMeta = meta\n"
            "                playerMetaVideos = meta.videos\n"
            "            }\n"
            "        }\n"
            "    }\n\n"
            "    LaunchedEffect(metaUiState.meta, parentMetaType, parentMetaId) {\n"
            "        val currentMeta = metaUiState.meta ?: return@LaunchedEffect\n"
            "        if (currentMeta.type == parentMetaType && currentMeta.id == parentMetaId) {\n"
            "            playerMeta = currentMeta\n"
            "            playerMetaVideos = currentMeta.videos\n"
            "        }\n"
            "    }\n",
            "    val localFolderState by LocalFolderVideosPlatform.state.collectAsStateWithLifecycle()\n"
            "    val localPlaylistsState by LocalEpisodePlaylistRegistry.playlistsByKey.collectAsStateWithLifecycle()\n\n"
            "    fun mergeLocalPlaylistVideos(remoteVideos: List<MetaVideo>): List<MetaVideo> {\n"
            "        val localEps = LocalEpisodePlaylistRegistry.episodesForPlayback(parentMetaId, activeSourceUrl)\n"
            "        if (localEps.isEmpty()) return remoteVideos\n"
            "        return localEps.map { localEp ->\n"
            "            val remoteMatch = remoteVideos.firstOrNull {\n"
            "                it.season == localEp.seasonNumber && it.episode == localEp.episodeNumber\n"
            "            }\n"
            "            MetaVideo(\n"
            "                id = localEp.videoId,\n"
            "                title = localEp.episodeTitle?.takeIf { it.isNotBlank() }\n"
            "                    ?: remoteMatch?.title?.takeIf { it.isNotBlank() }\n"
            "                    ?: \"Episode ${localEp.episodeNumber}\",\n"
            "                released = remoteMatch?.released?.takeIf { PlayerNextEpisodeRules.hasEpisodeAired(it) }\n"
            "                    ?: \"2000-01-01T00:00:00.000Z\",\n"
            "                thumbnail = localEp.thumbnailUrl ?: remoteMatch?.thumbnail,\n"
            "                season = localEp.seasonNumber,\n"
            "                episode = localEp.episodeNumber,\n"
            "                overview = remoteMatch?.overview,\n"
            "            )\n"
            "        }\n"
            "    }\n\n"
            "    LaunchedEffect(parentMetaType, parentMetaId, activeSourceUrl, localFolderState.videos, localPlaylistsState) {\n"
            "        val peeked = if (parentMetaId.startsWith(\"local_series:\") || parentMetaId.startsWith(\"local:\")) {\n"
            "            null\n"
            "        } else {\n"
            "            MetaDetailsRepository.peek(parentMetaType, parentMetaId)\n"
            "        }\n"
            "        if (peeked != null) playerMeta = peeked\n"
            "        val initialMerged = mergeLocalPlaylistVideos(playerMeta?.videos.orEmpty())\n"
            "        playerMetaVideos = initialMerged\n"
            "        if (playerMeta == null && !parentMetaId.startsWith(\"local_series:\") && !parentMetaId.startsWith(\"local:\")) {\n"
            "            MetaDetailsRepository.fetch(parentMetaType, parentMetaId)?.let { meta ->\n"
            "                playerMeta = meta\n"
            "                playerMetaVideos = mergeLocalPlaylistVideos(meta.videos)\n"
            "            }\n"
            "        }\n"
            "    }\n\n"
            "    LaunchedEffect(metaUiState.meta, parentMetaType, parentMetaId, activeSourceUrl) {\n"
            "        val currentMeta = metaUiState.meta ?: return@LaunchedEffect\n"
            "        if (currentMeta.type == parentMetaType && currentMeta.id == parentMetaId) {\n"
            "            playerMeta = currentMeta\n"
            "            playerMetaVideos = mergeLocalPlaylistVideos(currentMeta.videos)\n"
            "        }\n"
            "    }\n",
            "PlayerScreenRuntimeEffects populate playerMetaVideos from local folder season",
        )
        changed |= _replace_once(
            runtime_effects,
            "            PlayerStreamsRepository.loadSources(\n"
            "                type = type,\n"
            "                videoId = currentVideoId,\n"
            "                season = season,\n"
            "                episode = episode,\n"
            "                forceRefresh = true,\n"
            "            )\n",
            "            PlayerStreamsRepository.loadSources(\n"
            "                type = type,\n"
            "                videoId = currentVideoId,\n"
            "                parentMetaId = parentMetaId,\n"
            "                parentMetaType = parentMetaType,\n"
            "                season = season,\n"
            "                episode = episode,\n"
            "                searchTitle = playerMeta?.name ?: title,\n"
            "                forceRefresh = true,\n"
            "            )\n",
            "PlayerScreenRuntimeEffects credentialRefresh loadSources pass CloudStream context",
        )
        if changed:
            patched.append(str(runtime_effects.relative_to(root)))

    # Wire switchToLocalPlaylistEpisode into PlayerScreenRuntimeSourceActions.kt & PlayerScreenRuntimeUi.kt
    if src_actions.is_file():
        changed = False
        changed |= _replace_once(
            src_actions,
            "import com.nuvio.app.features.downloads.DownloadItem\n"
            "import com.nuvio.app.features.downloads.DownloadSubtitles\n"
            "import com.nuvio.app.features.downloads.DownloadsRepository\n",
            "import com.nuvio.app.features.downloads.DownloadItem\n"
            "import com.nuvio.app.features.downloads.DownloadSubtitles\n"
            "import com.nuvio.app.features.downloads.DownloadsRepository\n"
            "import com.nuvio.app.features.downloads.LocalEpisodePlaylistRegistry\n"
            "import com.nuvio.app.features.downloads.LocalPlaylistEpisode\n"
            "import com.nuvio.app.features.streams.StreamSubtitle\n"
            "import kotlinx.coroutines.delay\n",
            "PlayerScreenRuntimeSourceActions local playlist imports",
        )
        changed |= _replace_once(
            src_actions,
            "internal fun PlayerScreenRuntime.playNextEpisode(automatic: Boolean = false) {\n"
            "    if (nextEpisodeAutoPlaySearching || nextEpisodeAutoPlayCountdown != null) return\n"
            "    nextEpisodePreloadTriggered = false\n"
            "    val playbackKey = activePlaybackKey\n"
            "    val nextVideoId = nextEpisodeInfo?.takeIf { it.hasAired }?.videoId ?: return\n",
            "internal fun PlayerScreenRuntime.switchToLocalPlaylistEpisode(\n"
            "    localEpisode: LocalPlaylistEpisode,\n"
            "    episode: MetaVideo,\n"
            ") {\n"
            "    resetEpisodePanelAndNextEpisodeState()\n"
            "    flushWatchProgress()\n"
            "    stopActiveP2pStream()\n\n"
            "    val resolvedVideoId = localEpisode.videoId\n"
            "    val epEntry = WatchProgressRepository.progressForVideo(\n"
            "        videoId = resolvedVideoId,\n"
            "        parentMetaId = parentMetaId,\n"
            "        seasonNumber = localEpisode.seasonNumber,\n"
            "        episodeNumber = localEpisode.episodeNumber,\n"
            "    )?.takeIf { !it.isCompleted }\n"
            "    val epResumeFraction = epEntry?.progressPercent\n"
            "        ?.takeIf { it > 0f }\n"
            "        ?.let { (it / 100f).coerceIn(0f, 1f) }\n"
            "    val epResumePositionMs = epEntry?.lastPositionMs?.takeIf { it > 0L } ?: 0L\n\n"
            "    val sidecars = localEpisode.sidecarSubtitles.map { sub ->\n"
            "        StreamSubtitle(url = sub.uri, language = sub.language, name = sub.label)\n"
            "    }\n"
            "    externalSubtitles = DownloadSubtitles.localSubtitles(localEpisode.uri) + sidecars\n"
            "    activeSourceUrl = localEpisode.uri\n"
            "    restartSourceFallback(activeSourceUrl, autoSelection = null)\n"
            "    activeSourceAudioUrl = null\n"
            "    activeSourceHeaders = emptyMap()\n"
            "    activeSourceResponseHeaders = emptyMap()\n"
            "    activeStreamType = localEpisode.mimeType\n"
            "    activeSourceIdentityKey = null\n"
            "    activeSourceFilename = localEpisode.filename\n"
            "    activeStreamTitle = localEpisode.filename.ifBlank { episode.title.ifBlank { title } }\n"
            "    activeStreamSubtitle = \"Local Storage\"\n"
            "    activeStreamFilename = localEpisode.filename\n"
            "    activeProviderName = \"Local Storage\"\n"
            "    activeProviderAddonId = null\n"
            "    activeStream = null\n"
            "    currentStreamBingeGroup = null\n"
            "    activeSubtitleExtras = null\n"
            "    currentStreamFilename = localEpisode.filename\n"
            "    currentStreamInfoHash = null\n"
            "    activeSeasonNumber = localEpisode.seasonNumber\n"
            "    activeEpisodeNumber = localEpisode.episodeNumber\n"
            "    activeEpisodeTitle = episode.title\n"
            "    activeEpisodeThumbnail = episode.thumbnail ?: localEpisode.thumbnailUrl\n"
            "    activePauseDescription = episode.overview\n"
            "    activeVideoId = resolvedVideoId\n"
            "    activeInitialPositionMs = epResumePositionMs\n"
            "    activeInitialProgressFraction = epResumeFraction\n"
            "    controlsVisible = true\n"
            "    InAppLogger.info(\n"
            "        \"Player/Source\",\n"
            "        \"switch local folder episode videoId=$resolvedVideoId s=${localEpisode.seasonNumber} e=${localEpisode.episodeNumber} resumeMs=$epResumePositionMs\",\n"
            "    )\n"
            "}\n\n"
            "internal fun PlayerScreenRuntime.playNextEpisode(automatic: Boolean = false) {\n"
            "    val nextInfo = nextEpisodeInfo?.takeIf { it.hasAired }\n"
            "    val localNext = if (nextInfo != null) {\n"
            "        LocalEpisodePlaylistRegistry.findEpisode(\n"
            "            parentMetaId = parentMetaId,\n"
            "            activeSourceUrl = activeSourceUrl,\n"
            "            videoId = nextInfo.videoId,\n"
            "            season = nextInfo.season,\n"
            "            episode = nextInfo.episode,\n"
            "        )\n"
            "    } else null\n"
            "    if (localNext != null && nextInfo != null) {\n"
            "        val nextMetaVideo = playerMetaVideos.firstOrNull { it.id == nextInfo.videoId }\n"
            "            ?: MetaVideo(\n"
            "                id = localNext.videoId,\n"
            "                title = localNext.episodeTitle?.takeIf { it.isNotBlank() } ?: nextInfo.title,\n"
            "                released = \"2000-01-01T00:00:00.000Z\",\n"
            "                thumbnail = localNext.thumbnailUrl ?: nextInfo.thumbnail,\n"
            "                season = localNext.seasonNumber,\n"
            "                episode = localNext.episodeNumber,\n"
            "                overview = nextInfo.overview,\n"
            "            )\n"
            "        if (!automatic) {\n"
            "            nextEpisodeAutoPlayJob?.cancel()\n"
            "            nextEpisodeAutoPlayJob = null\n"
            "            switchToLocalPlaylistEpisode(localNext, nextMetaVideo)\n"
            "            return\n"
            "        }\n"
            "        if (nextEpisodeAutoPlaySearching || nextEpisodeAutoPlayCountdown != null) return\n"
            "        val playbackKey = activePlaybackKey\n"
            "        nextEpisodeAutoPlayAutomatic = true\n"
            "        nextEpisodeAutoPlaySearching = false\n"
            "        nextEpisodeAutoPlaySourceName = \"Local Storage\"\n"
            "        showNextEpisodeCard = true\n"
            "        nextEpisodeAutoPlayJob?.cancel()\n"
            "        nextEpisodeAutoPlayJob = scope.launch {\n"
            "            for (sec in 5 downTo 1) {\n"
            "                if (activePlaybackKey != playbackKey) return@launch\n"
            "                nextEpisodeAutoPlayCountdown = sec\n"
            "                delay(1000L)\n"
            "            }\n"
            "            if (activePlaybackKey != playbackKey) return@launch\n"
            "            nextEpisodeAutoPlayCountdown = null\n"
            "            switchToLocalPlaylistEpisode(localNext, nextMetaVideo)\n"
            "        }\n"
            "        return\n"
            "    }\n"
            "    if (nextEpisodeAutoPlaySearching || nextEpisodeAutoPlayCountdown != null) return\n"
            "    nextEpisodePreloadTriggered = false\n"
            "    val playbackKey = activePlaybackKey\n"
            "    val nextVideoId = nextInfo?.videoId ?: return\n",
            "PlayerScreenRuntimeSourceActions switchToLocalPlaylistEpisode & instant local Next Episode",
        )
        changed |= _replace_once(
            src_actions,
            "    if (playerMetaVideos.isEmpty()) {\n"
            "        scope.launch {\n"
            "            playerMetaVideos = MetaDetailsRepository.fetch(parentMetaType, parentMetaId)?.videos ?: emptyList()\n",
            "    if (playerMetaVideos.isEmpty()) {\n"
            "        val localEps = LocalEpisodePlaylistRegistry.episodesForPlayback(parentMetaId, activeSourceUrl)\n"
            "        if (localEps.isNotEmpty()) {\n"
            "            playerMetaVideos = localEps.map { ep ->\n"
            "                MetaVideo(\n"
            "                    id = ep.videoId,\n"
            "                    title = ep.episodeTitle?.takeIf { it.isNotBlank() } ?: \"Episode ${ep.episodeNumber}\",\n"
            "                    released = \"2000-01-01T00:00:00.000Z\",\n"
            "                    thumbnail = ep.thumbnailUrl,\n"
            "                    season = ep.seasonNumber,\n"
            "                    episode = ep.episodeNumber,\n"
            "                )\n"
            "            }\n"
            "        } else scope.launch {\n"
            "            playerMetaVideos = MetaDetailsRepository.fetch(parentMetaType, parentMetaId)?.videos ?: emptyList()\n",
            "PlayerScreenRuntimeSourceActions openEpisodesPanel local folder fallback",
        )
        if changed:
            patched.append(str(src_actions.relative_to(root)))

    if runtime_ui.is_file():
        changed = False
        changed |= _replace_once(
            runtime_ui,
            "import com.nuvio.app.features.party.PartyRepository\n",
            "import com.nuvio.app.features.downloads.LocalEpisodePlaylistRegistry\n"
            "import com.nuvio.app.features.party.PartyRepository\n",
            "PlayerScreenRuntimeUi import LocalEpisodePlaylistRegistry",
        )
        changed |= _replace_once(
            runtime_ui,
            "        onEpisodeSelectedForDownload = { episode ->\n"
            "            selectDownloadedEpisodeForPlayback(\n"
            "                parentMetaId = parentMetaId,\n"
            "                episode = episode,\n"
            "                onDownloadedEpisodeSelected = { item, video -> switchToDownloadedEpisode(item, video) },\n"
            "            )\n"
            "        },\n",
            "        onEpisodeSelectedForDownload = { episode ->\n"
            "            val localEp = LocalEpisodePlaylistRegistry.findEpisode(\n"
            "                parentMetaId = parentMetaId,\n"
            "                activeSourceUrl = activeSourceUrl,\n"
            "                videoId = episode.id,\n"
            "                season = episode.season,\n"
            "                episode = episode.episode,\n"
            "            )\n"
            "            if (localEp != null) {\n"
            "                switchToLocalPlaylistEpisode(localEp, episode)\n"
            "                true\n"
            "            } else {\n"
            "                selectDownloadedEpisodeForPlayback(\n"
            "                    parentMetaId = parentMetaId,\n"
            "                    episode = episode,\n"
            "                    onDownloadedEpisodeSelected = { item, video -> switchToDownloadedEpisode(item, video) },\n"
            "                )\n"
            "            }\n"
            "        },\n",
            "PlayerScreenRuntimeUi Episodes panel switch local folder episode",
        )
        if changed:
            patched.append(str(runtime_ui.relative_to(root)))

    # Add Next Episode button to Legacy Player Layout (ProgressControls) in PlayerControls.kt too
    player_controls = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerControls.kt"
    if player_controls.is_file():
        changed = False
        changed |= _replace_once(
            player_controls,
            "import androidx.compose.material.icons.rounded.VideoLibrary\n",
            "import androidx.compose.material.icons.rounded.SkipNext\n"
            "import androidx.compose.material.icons.rounded.VideoLibrary\n",
            "PlayerControls import Icons.Rounded.SkipNext",
        )
        changed |= _replace_once(
            player_controls,
            "                    onEpisodesClick = onEpisodesClick,\n"
            "                    onChaptersClick = onChaptersClick,\n",
            "                    onEpisodesClick = onEpisodesClick,\n"
            "                    onNextEpisodeClick = onNextEpisodeClick,\n"
            "                    onChaptersClick = onChaptersClick,\n",
            "PlayerControls pass onNextEpisodeClick to ProgressControls",
        )
        changed |= _replace_once(
            player_controls,
            "    onEpisodesClick: (() -> Unit)? = null,\n"
            "    onChaptersClick: (() -> Unit)? = null,\n"
            "    onLiveChannelsClick: (() -> Unit)? = null,\n"
            "    qualityLabel: String? = null,\n"
            "    onQualityClick: (() -> Unit)? = null,\n"
            "    seekPreview: SeekPreviewController? = null,\n"
            "    onTimelineTouchChange: (Boolean) -> Unit = {},\n"
            "    onPictureInPictureClick: (() -> Unit)? = null,\n"
            "    modifier: Modifier = Modifier,\n"
            ") {\n",
            "    onEpisodesClick: (() -> Unit)? = null,\n"
            "    onNextEpisodeClick: (() -> Unit)? = null,\n"
            "    onChaptersClick: (() -> Unit)? = null,\n"
            "    onLiveChannelsClick: (() -> Unit)? = null,\n"
            "    qualityLabel: String? = null,\n"
            "    onQualityClick: (() -> Unit)? = null,\n"
            "    seekPreview: SeekPreviewController? = null,\n"
            "    onTimelineTouchChange: (Boolean) -> Unit = {},\n"
            "    onPictureInPictureClick: (() -> Unit)? = null,\n"
            "    modifier: Modifier = Modifier,\n"
            ") {\n",
            "ProgressControls add onNextEpisodeClick parameter",
        )
        changed |= _replace_once(
            player_controls,
            "                    if (onEpisodesClick != null) {\n"
            "                        PlayerActionPillButton(\n"
            "                            label = stringResource(Res.string.compose_player_episodes),\n"
            "                            icon = Icons.Rounded.VideoLibrary,\n"
            "                            onClick = onEpisodesClick,\n"
            "                        )\n"
            "                    }\n",
            "                    if (onNextEpisodeClick != null) {\n"
            "                        PlayerActionPillButton(\n"
            "                            label = stringResource(Res.string.player_next_episode),\n"
            "                            icon = Icons.Rounded.SkipNext,\n"
            "                            onClick = onNextEpisodeClick,\n"
            "                        )\n"
            "                    }\n"
            "                    if (onEpisodesClick != null) {\n"
            "                        PlayerActionPillButton(\n"
            "                            label = stringResource(Res.string.compose_player_episodes),\n"
            "                            icon = Icons.Rounded.VideoLibrary,\n"
            "                            onClick = onEpisodesClick,\n"
            "                        )\n"
            "                    }\n",
            "ProgressControls render Next Episode pill button in Legacy Layout",
        )
        if changed:
            patched.append(str(player_controls.relative_to(root)))

    return patched
