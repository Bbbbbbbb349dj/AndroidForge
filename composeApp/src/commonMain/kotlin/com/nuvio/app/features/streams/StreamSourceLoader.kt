package com.nuvio.app.features.streams

import co.touchlab.kermit.Logger
import com.nuvio.app.core.build.AppFeaturePolicy
import com.nuvio.app.core.logging.InAppLogger
import com.nuvio.app.features.addons.AddonRepository
import com.nuvio.app.features.addons.buildAddonResourceUrl
import com.nuvio.app.features.addons.enabledAddons
import com.nuvio.app.features.addons.fetchAddonResponseText
import com.nuvio.app.features.cloudstream.CloudStreamRepository
import com.nuvio.app.features.cloudstream.parseCloudStreamRouteId
import com.nuvio.app.features.details.MetaDetails
import com.nuvio.app.features.debrid.DebridSettings
import com.nuvio.app.features.debrid.DebridSettingsRepository
import com.nuvio.app.features.debrid.DebridStreamPresentation
import com.nuvio.app.features.debrid.LocalDebridAvailabilityService
import com.nuvio.app.features.plugins.PluginRepository
import com.nuvio.app.features.plugins.PluginScraper
import com.nuvio.app.features.plugins.PluginsUiState
import com.nuvio.app.features.plugins.pluginContentId
import com.nuvio.app.features.servers.ServerStreamSource
import com.nuvio.app.features.servers.ServerStreams
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch
import kotlinx.coroutines.supervisorScope
import kotlinx.coroutines.withTimeoutOrNull
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.streams_failed_to_load_scraper
import org.jetbrains.compose.resources.getString

internal data class StreamSourceTargets(
    val serverSources: List<ServerStreamSource>,
    val streamAddons: List<InstalledStreamAddonTarget>,
    val pluginProviderGroups: List<PluginProviderGroup>,
    val preferredGroupIds: Set<String>,
    val installedAddonOrder: List<String>,
    val streamAddonIds: Set<String>,
    /** Enabled addons before filtering by stream support; zero means none are installed. */
    val enabledAddonCount: Int,
    val pluginScraperCount: Int,
)

/** One place streams can come from, and how to load its group. */
private class StreamSource(
    val addonName: String,
    val addonId: String,
    val load: suspend () -> AddonStreamGroup,
)

internal object StreamSourceLoader {
    const val EMBEDDED_ADDON_ID = "embedded"

    /** Wraps a title's embedded streams as one group; [streams] must not be empty. */
    fun embeddedStreamGroup(streams: List<StreamItem>): AddonStreamGroup =
        AddonStreamGroup(addonName = streams.first().addonName, addonId = EMBEDDED_ADDON_ID, streams = streams, isLoading = false)

    private val log = Logger.withTag("StreamSourceLoader")

    fun resolveTargets(
        type: String,
        videoId: String,
        season: Int?,
        episode: Int?,
        forceRefresh: Boolean = false,
        pluginUiState: PluginsUiState = if (AppFeaturePolicy.pluginsEnabled) {
            PluginRepository.initialize()
            PluginRepository.uiState.value
        } else {
            PluginsUiState(pluginsEnabled = false)
        },
    ): StreamSourceTargets {
        val isNativeServerRequest = ServerStreams.isNativeRequest(videoId)
        val serverSources = ServerStreams.sources(type, videoId, season, episode, forceRefresh)
        val preferredGroupIds = serverSources.filter { it.preferred }.mapTo(mutableSetOf()) { it.addonId }
        val installedAddons = if (isNativeServerRequest) emptyList() else AddonRepository.uiState.value.addons.enabledAddons()
        val pluginScrapers = if (AppFeaturePolicy.pluginsEnabled && !isNativeServerRequest) {
            PluginRepository.getEnabledScrapersForType(type)
        } else {
            emptyList()
        }
        val pluginProviderGroups = pluginScrapers.toPluginProviderGroups(
            repositories = pluginUiState.repositories,
            groupByRepository = pluginUiState.groupStreamsByRepository,
        )

        val streamAddons = installedAddons.mapNotNull { addon ->
            val manifest = addon.manifest ?: return@mapNotNull null
            if (!manifest.supportsStream(type, videoId)) return@mapNotNull null

            InstalledStreamAddonTarget(
                addonName = addon.displayTitle.ifBlank { manifest.name },
                addonId = addon.streamAddonInstanceId(manifest.id),
                manifest = manifest,
            )
        }

        val installedAddonOrder = streamAddons.map { it.addonName }
        val installedAddonIds = streamAddons.map { it.addonId }.toSet()

        return StreamSourceTargets(
            serverSources = serverSources,
            streamAddons = streamAddons,
            pluginProviderGroups = pluginProviderGroups,
            preferredGroupIds = preferredGroupIds,
            installedAddonOrder = installedAddonOrder,
            streamAddonIds = installedAddonIds,
            enabledAddonCount = installedAddons.size,
            pluginScraperCount = pluginScrapers.size,
        )
    }

    suspend fun fetchAddonGroup(
        addon: InstalledStreamAddonTarget,
        type: String,
        videoId: String,
        forceRefresh: Boolean,
    ): AddonStreamGroup {
        val url = buildAddonResourceUrl(
            manifestUrl = addon.manifest.transportUrl,
            resource = "stream",
            type = type,
            id = videoId,
        )
        val displayName = addon.addonName
        InAppLogger.info(
            "Streams/AddonFetch",
            "Fetching streams addon=$displayName addonId=${addon.addonId} url=${InAppLogger.redactUrl(url)}",
        )
        return runCatchingUnlessCancelled {
            val payload = fetchAddonResponseText(
                url = url,
                forceRefresh = forceRefresh,
            )
            StreamParser.parse(
                payload = payload,
                addonName = displayName,
                addonId = addon.addonId,
                addonLogo = addon.manifest.logoUrl,
            )
        }.fold(
            onSuccess = { streams ->
                InAppLogger.info("Streams/AddonFetch", "Loaded streams addon=$displayName count=${streams.size}")
                AddonStreamGroup(
                    addonName = displayName,
                    addonId = addon.addonId,
                    streams = streams,
                    isLoading = false,
                )
            },
            onFailure = { err ->
                InAppLogger.warn("Streams/AddonFetch", "Failed addon=$displayName error=${InAppLogger.throwableSummary(err)}")
                AddonStreamGroup(
                    addonName = displayName,
                    addonId = addon.addonId,
                    streams = emptyList(),
                    isLoading = false,
                    error = err.message,
                )
            },
        )
    }

    suspend fun executePluginScraper(
        scraper: PluginScraper,
        providerGroup: PluginProviderGroup,
        type: String,
        videoId: String,
        season: Int?,
        episode: Int?,
        includeScraperNameInSubtitle: Boolean = false,
    ): StreamLoadCompletion.PluginScraper {
        InAppLogger.info(
            "Streams/PluginFetch",
            "Executing scraper=${scraper.name} provider=${providerGroup.addonName} type=$type id=$videoId season=${season ?: -1} episode=${episode ?: -1}",
        )
        return PluginRepository.executeScraper(
            scraper = scraper,
            tmdbId = pluginContentId(
                videoId = videoId,
                season = season,
                episode = episode,
            ),
            mediaType = type,
            season = season,
            episode = episode,
        ).fold(
            onSuccess = { results ->
                InAppLogger.info("Streams/PluginFetch", "Scraper loaded scraper=${scraper.name} provider=${providerGroup.addonName} count=${results.size}")
                StreamLoadCompletion.PluginScraper(
                    addonId = providerGroup.addonId,
                    streams = results.map { result ->
                        result.toStreamItem(
                            scraper = scraper,
                            addonName = providerGroup.addonName,
                            addonId = providerGroup.addonId,
                            includeScraperNameInSubtitle = includeScraperNameInSubtitle,
                        )
                    },
                    error = null,
                )
            },
            onFailure = { error ->
                InAppLogger.warn("Streams/PluginFetch", "Scraper failed scraper=${scraper.name} provider=${providerGroup.addonName} error=${InAppLogger.throwableSummary(error)}")
                StreamLoadCompletion.PluginScraper(
                    addonId = providerGroup.addonId,
                    streams = emptyList(),
                    error = error.message ?: getString(Res.string.streams_failed_to_load_scraper, scraper.name),
                )
            },
        )
    }

    fun presentStreamGroup(
        group: AddonStreamGroup,
        streamBadgeRules: StreamBadgeRules,
        debridSettings: DebridSettings,
    ): AddonStreamGroup {
        val badgeGroup = StreamBadgePresentation.apply(
            groups = listOf(group),
            rules = streamBadgeRules,
        ).firstOrNull() ?: group
        return DebridStreamPresentation.apply(
            groups = listOf(badgeGroup),
            settings = debridSettings,
        ).firstOrNull() ?: badgeGroup
    }

    suspend fun checkDebridCache(
        group: AddonStreamGroup,
        eligibleGroupIds: Set<String>,
    ): AddonStreamGroup {
        if (group.addonId !in eligibleGroupIds || group.streams.isEmpty()) {
            return group
        }

        return LocalDebridAvailabilityService.checkCachedAvailability(group, eligibleGroupIds)
    }

    private fun failedGroup(addonName: String, addonId: String, error: Throwable) = AddonStreamGroup(
        addonName = addonName,
        addonId = addonId,
        streams = emptyList(),
        isLoading = false,
        error = error.message,
    )

    /**
     * Loads every source's streams for one title and returns them in display order. Sources that
     * haven't answered within [timeoutMs] are left out.
     */
    private data class SourceEmission(
        val index: Int,
        val group: AddonStreamGroup,
        val isFinal: Boolean,
    )

    suspend fun loadStreams(
        type: String,
        videoId: String,
        season: Int?,
        episode: Int?,
        embeddedStreams: List<StreamItem>,
        timeoutMs: Long,
        meta: MetaDetails? = null,
        onProgress: ((List<StreamItem>) -> Unit)? = null,
    ): List<StreamItem> {
        val streamBadgeRules = StreamBadgeSettingsRepository.snapshot()
        val debridSettings = DebridSettingsRepository.snapshot()
        fun present(group: AddonStreamGroup) = presentStreamGroup(group, streamBadgeRules, debridSettings)

        if (embeddedStreams.isNotEmpty()) {
            val group = embeddedStreamGroup(embeddedStreams)
            return present(group).streams
        }

        val targets = resolveTargets(type = type, videoId = videoId, season = season, episode = episode)
        val directCloudRoute = parseCloudStreamRouteId(videoId)
            ?: meta?.id?.takeIf { type.equals("movie", ignoreCase = true) }?.let(::parseCloudStreamRouteId)
        val cloudStreamSearchRequest = if (AppFeaturePolicy.pluginsEnabled) {
            val fallbackReq = buildCloudStreamSearchRequest(
                type = type,
                videoId = videoId,
                parentMetaId = meta?.id,
                parentMetaType = meta?.type ?: type,
                season = season,
                episode = episode,
                searchTitle = meta?.name,
            )
            if (fallbackReq != null) {
                fallbackReq.copy(
                    year = fallbackReq.year ?: meta?.releaseInfo.cloudStreamReleaseYear(),
                    genres = fallbackReq.genres.ifEmpty { meta?.genres.orEmpty() },
                )
            } else if (meta != null && meta.name.isNotBlank()) {
                CloudStreamSearchRequest(
                    title = meta.name,
                    type = type,
                    year = meta.releaseInfo.cloudStreamReleaseYear(),
                    season = season,
                    episode = episode,
                    episodeTitle = meta.videos.firstOrNull {
                        (season == null || it.season == season) && (episode == null || it.episode == episode)
                    }?.title,
                    externalId = sequenceOf(videoId, meta.id)
                        .map(String::trim)
                        .firstOrNull { it.matches(Regex("^tt\\d{5,12}$", RegexOption.IGNORE_CASE)) },
                    genres = meta.genres,
                )
            } else {
                null
            }
        } else {
            null
        }
        val cloudStreamGroups = if (AppFeaturePolicy.pluginsEnabled) {
            cloudStreamProviderGroupsForRequest(type = type, request = cloudStreamSearchRequest)
        } else {
            emptyList()
        }
        // Fast 0ms seed if StreamsRepository already resolved this exact episode/movie in session
        val tokenPrefix = "$type::$videoId::$season::$episode::"
        val cachedState = StreamsRepository.uiState.value
        if (onProgress != null && cachedState.requestToken?.startsWith(tokenPrefix) == true) {
            val preloaded = cachedState.groups.flatMap { it.streams }
            if (preloaded.isNotEmpty()) {
                onProgress(preloaded)
                if (!cachedState.isAnyLoading) {
                    return preloaded
                }
            }
        }

        val emissions = Channel<SourceEmission>(Channel.UNLIMITED)
        var nextSourceIndex = 0

        val directCloudSources = if (directCloudRoute != null && AppFeaturePolicy.pluginsEnabled) {
            CloudStreamRepository.initialize()
            val pluginItem = CloudStreamRepository.uiState.value.plugins
                .firstOrNull { it.metadata.id.value == directCloudRoute.providerId }
            val directName = pluginItem?.metadata?.name ?: "CloudStream"
            val directAddonId = cloudStreamAddonId(directCloudRoute.providerId)
            val myIndex = nextSourceIndex++
            listOf(
                StreamSource(directName, directAddonId) {
                    val items = loadCloudStreamRouteProgressive(
                        providerId = directCloudRoute.providerId,
                        providerName = directName,
                        linkData = directCloudRoute.data,
                        onProgress = { partialItems ->
                            if (partialItems.isNotEmpty()) {
                                emissions.trySend(
                                    SourceEmission(
                                        index = myIndex,
                                        group = present(
                                            AddonStreamGroup(
                                                addonName = directName,
                                                addonId = directAddonId,
                                                streams = partialItems.sortedForGroupedDisplay(),
                                                isLoading = true,
                                            ),
                                        ),
                                        isFinal = false,
                                    ),
                                )
                            }
                        },
                    ).getOrThrow()
                    AddonStreamGroup(
                        addonName = directName,
                        addonId = directAddonId,
                        streams = items.sortedForGroupedDisplay(),
                        isLoading = false,
                    )
                },
            )
        } else {
            emptyList()
        }
        val addonSources = targets.streamAddons.map { addon ->
            nextSourceIndex++
            StreamSource(addon.addonName, addon.addonId) {
                val group = fetchAddonGroup(addon, type, videoId, forceRefresh = false)
                checkDebridCache(group, targets.streamAddonIds)
            }
        }
        val pluginSources = targets.pluginProviderGroups.map { providerGroup ->
            nextSourceIndex++
            StreamSource(providerGroup.addonName, providerGroup.addonId) {
                loadPluginProviderGroup(providerGroup, type, videoId, season, episode)
            }
        }
        val csSources = cloudStreamGroups
            .filterNot { it.providerId == directCloudRoute?.providerId }
            .map { csGroup ->
                val myIndex = nextSourceIndex++
                StreamSource(csGroup.addonName, csGroup.addonId) {
                    resolveCloudStreamProviderStreams(
                        providerGroup = csGroup,
                        request = cloudStreamSearchRequest,
                        onProgress = { partialItems ->
                            if (partialItems.isNotEmpty()) {
                                emissions.trySend(
                                    SourceEmission(
                                        index = myIndex,
                                        group = present(
                                            AddonStreamGroup(
                                                addonName = csGroup.addonName,
                                                addonId = csGroup.addonId,
                                                streams = partialItems.sortedForGroupedDisplay(),
                                                isLoading = true,
                                            ),
                                        ),
                                        isFinal = false,
                                    ),
                                )
                            }
                        },
                    )
                }
            }
        val serverSources = targets.serverSources.map { source ->
            nextSourceIndex++
            StreamSource(source.addonName, source.addonId) { source.load() }
        }
        val sources = directCloudSources + addonSources + pluginSources + csSources + serverSources
        if (sources.isEmpty()) return emptyList()

        val arrivedByIndex = mutableMapOf<Int, AddonStreamGroup>()
        var lastEmittedCount = 0

        fun buildOrderedStreams(): List<StreamItem> {
            val arrivedGroups = sources.indices.mapNotNull { arrivedByIndex[it] }
            return StreamAutoPlaySelector.orderAddonStreams(
                groups = arrivedGroups,
                installedOrder = targets.installedAddonOrder,
                preferredGroupIds = targets.preferredGroupIds,
            ).flatMap { it.streams }
        }

        val loadScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        try {
            sources.forEachIndexed { index, source ->
                loadScope.launch {
                    val group = try {
                        present(source.load())
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Throwable) {
                        failedGroup(source.addonName, source.addonId, e)
                    }
                    emissions.send(SourceEmission(index = index, group = group, isFinal = true))
                }
            }
            var completedFinals = 0
            withTimeoutOrNull(timeoutMs) {
                while (completedFinals < sources.size) {
                    val emission = emissions.receive()
                    val existing = arrivedByIndex[emission.index]
                    // Never overwrite a non-empty partial group with a timed-out empty group
                    if (emission.group.streams.isNotEmpty() || existing == null) {
                        arrivedByIndex[emission.index] = emission.group
                    }
                    if (emission.isFinal) {
                        completedFinals += 1
                    }
                    if (onProgress != null && emission.group.streams.isNotEmpty()) {
                        val orderedNow = buildOrderedStreams()
                        if (orderedNow.isNotEmpty() && orderedNow.size != lastEmittedCount) {
                            lastEmittedCount = orderedNow.size
                            onProgress(orderedNow)
                        }
                    }
                }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            log.w(e) { "Stream loading error: ${e.message}" }
        } finally {
            loadScope.cancel()
        }

        return buildOrderedStreams()
    }

    /** Runs every scraper of [providerGroup] and merges their streams into one group. */
    private suspend fun loadPluginProviderGroup(
        providerGroup: PluginProviderGroup,
        type: String,
        videoId: String,
        season: Int?,
        episode: Int?,
    ): AddonStreamGroup = supervisorScope {
        val streams = providerGroup.scrapers
            .map { scraper ->
                async { executePluginScraper(scraper, providerGroup, type, videoId, season, episode) }
            }
            .awaitAll()
            .flatMap { it.streams }
        AddonStreamGroup(
            addonName = providerGroup.addonName,
            addonId = providerGroup.addonId,
            streams = streams.sortedForGroupedDisplay(),
            isLoading = false,
        )
    }
}
