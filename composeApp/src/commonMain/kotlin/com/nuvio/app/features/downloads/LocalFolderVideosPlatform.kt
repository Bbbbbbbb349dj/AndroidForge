package com.nuvio.app.features.downloads

import com.nuvio.app.core.deeplink.LocalSidecarSubtitleItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class LocalVideoFolder(
    val treeUri: String,
    val displayName: String,
)

data class LocalParsedMediaInfo(
    val cleanTitle: String,
    val year: Int? = null,
    val isSeries: Boolean = false,
    val seasonNumber: Int? = null,
    val episodeNumber: Int? = null,
    val episodeTitle: String? = null,
)

data class LocalVideoFileItem(
    val id: String,
    val uri: String,
    val title: String,
    val filename: String,
    val folderUri: String,
    val folderName: String,
    val sizeBytes: Long,
    val lastModifiedMs: Long,
    val mimeType: String?,
    val extensionLabel: String,
    val year: Int? = null,
    val isSeries: Boolean = false,
    val seriesKey: String? = null,
    val seasonNumber: Int? = null,
    val episodeNumber: Int? = null,
    val episodeTitle: String? = null,
    val posterUrl: String? = null,
    val backgroundUrl: String? = null,
    val episodeThumbnailUrl: String? = null,
    val resolvedMetaId: String? = null,
    val sidecarSubtitles: List<LocalSidecarSubtitleItem> = emptyList(),
) {
    val syntheticVideoId: String
        get() = "local:${uri.hashCode().toUInt().toString(16)}"

    val effectiveParentMetaId: String
        get() = resolvedMetaId?.takeIf { it.isNotBlank() }
            ?: seriesKey?.let { "local_series:$it" }
            ?: syntheticVideoId
}

data class LocalSeriesGroup(
    val key: String,
    val title: String,
    val year: Int?,
    val posterUrl: String?,
    val backgroundUrl: String?,
    val resolvedMetaId: String?,
    val episodes: List<LocalVideoFileItem>,
) {
    val seasonCount: Int
        get() = episodes.map { it.seasonNumber ?: 1 }.distinct().size

    val totalSizeBytes: Long
        get() = episodes.sumOf { it.sizeBytes }
}

data class LocalFolderVideosState(
    val isSupported: Boolean = false,
    val isScanning: Boolean = false,
    val folders: List<LocalVideoFolder> = emptyList(),
    val videos: List<LocalVideoFileItem> = emptyList(),
    val errorMessage: String? = null,
)

object LocalMediaParser {
    private val SXXEXX_REGEX = Regex(
        """(?i)(.*?)[\s._\-\[\(]*S(\d{1,2})[\s._\-]*E(\d{1,3})(?:[\s._\-]*E\d{1,3})?[\s._\-\]\)]*(.*)""",
    )
    private val X_EP_REGEX = Regex(
        """(?i)(.*?)[\s._\-\[\(]+(\d{1,2})x(\d{2,3})[\s._\-\]\)]*(.*)""",
    )
    private val SEASON_EP_WORDS_REGEX = Regex(
        """(?i)(.*?)[\s._\-]*Season[\s._\-]*(\d{1,2})[\s._\-]*(?:Episode|Ep)[\s._\-]*(\d{1,3})(.*)""",
    )
    private val EP_ONLY_REGEX = Regex(
        """(?i)(.*?)[\s._\-\[\(]*(?:Episode|Ep|Part|E)[\s._\-]*(\d{1,3})\b(.*)""",
    )
    private val LEADING_EP_IN_SEASON_REGEX = Regex(
        """^\s*(\d{1,3})(?:[\s._\-:]+(.*))?$""",
    )
    private val ANIME_DASH_EP_REGEX = Regex(
        """^(?:\[[^\]]+\][\s._]*)?(.+?)\s+-\s+(\d{2,3})(?:\s*v\d)?(?:\s*[\[\(].*)?$""",
    )
    private val FOLDER_SEASON_REGEX = Regex(
        """(?i)(?:^|[\s._\-])(?:Season|S)[\s._\-]*(\d{1,2})\b""",
    )
    private val YEAR_TOKEN_REGEX = Regex("""\b(19\d{2}|20\d{2})\b""")
    private val JUNK_TAG_REGEX = Regex(
        """(?i)\b(2160p|1080p|720p|480p|360p|4k|uhd|fhd|hdrip|web[\s.\-]?dl|webrip|web|bluray|blu[\s.\-]?ray|brrip|bdrip|dvdrip|hdtv|remux|proper|repack|extended|unrated|directors[\s.\-]?cut|x264|x265|h[\s.]?264|h[\s.]?265|hevc|avc|av1|10bit|8bit|hdr10\+?|hdr|dv|dolby[\s.\-]?vision|aac\d*(?:\.\d)?|ddp?\d*(?:\.\d)?|ac3|eac3|dts(?:\-hd)?|truehd|atmos|flac|mp3|dual[\s.\-]?audio|multi[\s.\-]?audio| multi|hindi|eng|english|esub|esubs|subs?|yts(?:\.[a-z]+)?|rarbg|psa|pahe|tigole|qxr|flux|ntb|etrg|evo|galaxy(?:rg|tv)?)\b.*$""",
    )
    private val LEADING_GROUP_BRACKET_REGEX = Regex("""^(?:\[[^\]]{1,32}\]|\([^\)]{1,24}\))[\s._\-]*""")

    fun parse(filename: String, parentFolderName: String? = null, grandParentFolderName: String? = null): LocalParsedMediaInfo {
        val rawStem = filename.substringBeforeLast('.', filename)
            .replace(LEADING_GROUP_BRACKET_REGEX, "")
            .trim()

        val folderSeason = parentFolderName?.let { folder ->
            FOLDER_SEASON_REGEX.find(folder)?.groupValues?.getOrNull(1)?.toIntOrNull()
        }
        val inferredSeriesFolderTitle = when {
            folderSeason != null && !grandParentFolderName.isNullOrBlank() -> cleanName(grandParentFolderName)
            parentFolderName != null && FOLDER_SEASON_REGEX.containsMatchIn(parentFolderName) -> {
                cleanName(parentFolderName.replace(FOLDER_SEASON_REGEX, ""))
            }
            else -> null
        }?.takeIf { it.isNotBlank() && !isGenericFolderName(it) }

        SXXEXX_REGEX.matchEntire(rawStem)?.let { m ->
            val rawShow = m.groupValues[1]
            val season = m.groupValues[2].toIntOrNull() ?: folderSeason ?: 1
            val ep = m.groupValues[3].toIntOrNull()
            val tail = m.groupValues[4]
            val (showTitle, year) = extractTitleAndYear(rawShow, fallback = inferredSeriesFolderTitle ?: parentFolderName)
            return LocalParsedMediaInfo(
                cleanTitle = showTitle,
                year = year,
                isSeries = true,
                seasonNumber = season,
                episodeNumber = ep,
                episodeTitle = cleanEpisodeSubtitle(tail),
            )
        }

        SEASON_EP_WORDS_REGEX.matchEntire(rawStem)?.let { m ->
            val rawShow = m.groupValues[1]
            val season = m.groupValues[2].toIntOrNull() ?: folderSeason ?: 1
            val ep = m.groupValues[3].toIntOrNull()
            val tail = m.groupValues[4]
            val (showTitle, year) = extractTitleAndYear(rawShow, fallback = inferredSeriesFolderTitle ?: parentFolderName)
            return LocalParsedMediaInfo(
                cleanTitle = showTitle,
                year = year,
                isSeries = true,
                seasonNumber = season,
                episodeNumber = ep,
                episodeTitle = cleanEpisodeSubtitle(tail),
            )
        }

        X_EP_REGEX.matchEntire(rawStem)?.let { m ->
            val rawShow = m.groupValues[1]
            val season = m.groupValues[2].toIntOrNull() ?: folderSeason ?: 1
            val ep = m.groupValues[3].toIntOrNull()
            val tail = m.groupValues[4]
            val (showTitle, year) = extractTitleAndYear(rawShow, fallback = inferredSeriesFolderTitle ?: parentFolderName)
            return LocalParsedMediaInfo(
                cleanTitle = showTitle,
                year = year,
                isSeries = true,
                seasonNumber = season,
                episodeNumber = ep,
                episodeTitle = cleanEpisodeSubtitle(tail),
            )
        }

        ANIME_DASH_EP_REGEX.matchEntire(filename.substringBeforeLast('.', filename).trim())?.let { m ->
            val rawShow = m.groupValues[1]
            val ep = m.groupValues[2].toIntOrNull()
            if (ep != null && ep in 1..999 && rawShow.length >= 2) {
                val (showTitle, year) = extractTitleAndYear(rawShow, fallback = inferredSeriesFolderTitle)
                return LocalParsedMediaInfo(
                    cleanTitle = showTitle,
                    year = year,
                    isSeries = true,
                    seasonNumber = folderSeason ?: 1,
                    episodeNumber = ep,
                    episodeTitle = null,
                )
            }
        }

        val nonGenericParent = parentFolderName?.let(::cleanName)?.takeIf { it.isNotBlank() && !isGenericFolderName(it) }
        if (folderSeason != null || nonGenericParent != null) {
            EP_ONLY_REGEX.matchEntire(rawStem)?.let { m ->
                val rawShow = m.groupValues[1]
                val ep = m.groupValues[2].toIntOrNull()
                val tail = m.groupValues[3]
                if (ep != null && ep in 1..999) {
                    val fallbackSeries = inferredSeriesFolderTitle ?: nonGenericParent
                    val (showTitle, year) = extractTitleAndYear(
                        rawShow.ifBlank { fallbackSeries.orEmpty() },
                        fallback = fallbackSeries,
                    )
                    return LocalParsedMediaInfo(
                        cleanTitle = showTitle,
                        year = year,
                        isSeries = true,
                        seasonNumber = folderSeason ?: 1,
                        episodeNumber = ep,
                        episodeTitle = cleanEpisodeSubtitle(tail),
                    )
                }
            }
        }

        if (folderSeason != null) {
            LEADING_EP_IN_SEASON_REGEX.matchEntire(rawStem)?.let { m ->
                val ep = m.groupValues[1].toIntOrNull()
                val tail = m.groupValues[2]
                if (ep != null && ep in 1..999) {
                    val fallbackSeries = inferredSeriesFolderTitle ?: nonGenericParent
                    val (showTitle, year) = extractTitleAndYear(
                        fallbackSeries.orEmpty(),
                        fallback = fallbackSeries,
                    )
                    return LocalParsedMediaInfo(
                        cleanTitle = showTitle,
                        year = year,
                        isSeries = true,
                        seasonNumber = folderSeason,
                        episodeNumber = ep,
                        episodeTitle = cleanEpisodeSubtitle(tail),
                    )
                }
            }
        }

        val (movieTitle, movieYear) = extractTitleAndYear(rawStem, fallback = null)
        return LocalParsedMediaInfo(
            cleanTitle = movieTitle.ifBlank { rawStem.replace('_', ' ').trim().ifBlank { "Local Video" } },
            year = movieYear,
            isSeries = false,
        )
    }

    fun canonicalSeriesKey(title: String): String =
        title.lowercase()
            .replace(Regex("[^a-z0-9]+"), "_")
            .trim('_')
            .ifBlank { "series" }

    fun groupVideos(videos: List<LocalVideoFileItem>): Pair<List<LocalSeriesGroup>, List<LocalVideoFileItem>> {
        val seriesItems = videos.filter { it.isSeries }
        val movieItems = videos.filterNot { it.isSeries }
            .sortedWith(compareByDescending<LocalVideoFileItem> { it.lastModifiedMs }.thenBy { it.title.lowercase() })

        val seriesGroups = seriesItems
            .groupBy { it.seriesKey ?: canonicalSeriesKey(it.title) }
            .map { (key, eps) ->
                val sortedEps = eps.sortedWith(
                    compareBy<LocalVideoFileItem> { it.seasonNumber ?: 1 }
                        .thenBy { it.episodeNumber ?: Int.MAX_VALUE }
                        .thenBy { it.filename.lowercase() },
                )
                val primary = sortedEps.firstOrNull { !it.posterUrl.isNullOrBlank() } ?: sortedEps.first()
                LocalSeriesGroup(
                    key = key,
                    title = primary.title,
                    year = sortedEps.firstNotNullOfOrNull { it.year },
                    posterUrl = sortedEps.firstNotNullOfOrNull { it.posterUrl },
                    backgroundUrl = sortedEps.firstNotNullOfOrNull { it.backgroundUrl },
                    resolvedMetaId = sortedEps.firstNotNullOfOrNull { it.resolvedMetaId },
                    episodes = sortedEps,
                )
            }
            .sortedWith(
                compareByDescending<LocalSeriesGroup> { grp -> grp.episodes.maxOfOrNull { it.lastModifiedMs } ?: 0L }
                    .thenBy { it.title.lowercase() },
            )

        return seriesGroups to movieItems
    }

    private fun extractTitleAndYear(raw: String, fallback: String?): Pair<String, Int?> {
        val spaced = raw
            .replace('.', ' ')
            .replace('_', ' ')
            .replace(LEADING_GROUP_BRACKET_REGEX, "")
            .replace(JUNK_TAG_REGEX, "")
            .trim()

        val yearMatches = YEAR_TOKEN_REGEX.findAll(spaced).toList()
        val yearMatch = yearMatches.lastOrNull { m ->
            m.range.first > 1
        }
        val year = yearMatch?.groupValues?.getOrNull(1)?.toIntOrNull()
        val beforeYear = if (yearMatch != null) {
            spaced.substring(0, yearMatch.range.first)
        } else {
            spaced
        }
        val cleaned = cleanName(beforeYear)
        if (cleaned.isNotBlank()) return cleaned to year
        val fb = fallback?.let(::cleanName)?.takeIf { !isGenericFolderName(it) }.orEmpty()
        return fb.ifBlank { cleanName(spaced).ifBlank { "Local Video" } } to year
    }

    private fun cleanEpisodeSubtitle(rawTail: String): String? {
        val cleaned = rawTail
            .replace('.', ' ')
            .replace('_', ' ')
            .replace(JUNK_TAG_REGEX, "")
            .replace(Regex("""\[[^\]]*\]|\([^\)]*\)"""), " ")
            .trim(' ', '-', ':', '.', '_')
            .replace(Regex("\\s+"), " ")
            .trim()
        return cleaned.takeIf { it.length in 2..80 && !it.all { ch -> ch.isDigit() } }
    }

    private fun cleanName(value: String): String =
        value
            .replace('.', ' ')
            .replace('_', ' ')
            .replace(JUNK_TAG_REGEX, "")
            .replace(Regex("""\[[^\]]*\]|\([^\)]*\)"""), " ")
            .trim(' ', '-', ':', '.', '_')
            .replace(Regex("\\s+"), " ")
            .trim()

    private fun isGenericFolderName(name: String): Boolean {
        val lower = name.trim().lowercase()
        return lower in setOf(
            "download", "downloads", "movies", "movie", "video", "videos",
            "tv", "tv shows", "series", "shows", "anime", "media",
            "internal storage", "sdcard", "dcim", "camera", "telegram", "whatsapp video",
        )
    }
}

data class LocalPlaylistEpisode(
    val videoId: String,
    val uri: String,
    val title: String,
    val filename: String,
    val mimeType: String? = null,
    val seasonNumber: Int,
    val episodeNumber: Int,
    val episodeTitle: String? = null,
    val thumbnailUrl: String? = null,
    val sidecarSubtitles: List<LocalSidecarSubtitleItem> = emptyList(),
)

object LocalEpisodePlaylistRegistry {
    private val _playlistsByKey = MutableStateFlow<Map<String, List<LocalPlaylistEpisode>>>(emptyMap())
    val playlistsByKey: StateFlow<Map<String, List<LocalPlaylistEpisode>>> = _playlistsByKey.asStateFlow()

    fun registerFromItems(parentMetaId: String, items: List<LocalVideoFileItem>) {
        if (items.isEmpty()) return
        val sorted = items.sortedWith(
            compareBy<LocalVideoFileItem> { it.seasonNumber ?: 1 }
                .thenBy { it.episodeNumber ?: Int.MAX_VALUE }
                .thenBy { it.filename.lowercase() },
        )
        val perSeasonCounter = HashMap<Int, Int>()
        val mapped = sorted.map { item ->
            val s = (item.seasonNumber ?: 1).coerceAtLeast(1)
            val nextFallback = (perSeasonCounter[s] ?: 0) + 1
            val e = (item.episodeNumber ?: nextFallback).coerceAtLeast(1)
            perSeasonCounter[s] = maxOf(nextFallback, e)
            LocalPlaylistEpisode(
                videoId = item.syntheticVideoId,
                uri = item.uri,
                title = item.title,
                filename = item.filename,
                mimeType = item.mimeType,
                seasonNumber = s,
                episodeNumber = e,
                episodeTitle = item.episodeTitle,
                thumbnailUrl = item.episodeThumbnailUrl ?: item.backgroundUrl ?: item.posterUrl,
                sidecarSubtitles = item.sidecarSubtitles,
            )
        }
        registerPlaylist(parentMetaId, mapped)
    }

    fun registerPlaylist(parentMetaId: String, episodes: List<LocalPlaylistEpisode>) {
        if (parentMetaId.isBlank() || episodes.isEmpty()) return
        val deduped = episodes
            .distinctBy { it.uri }
            .sortedWith(compareBy<LocalPlaylistEpisode> { it.seasonNumber }.thenBy { it.episodeNumber })
        _playlistsByKey.update { current -> current + (parentMetaId to deduped) }
    }

    fun episodesForPlayback(
        parentMetaId: String,
        activeSourceUrl: String,
    ): List<LocalPlaylistEpisode> {
        val isLocalSource = activeSourceUrl.startsWith("content://", ignoreCase = true) ||
            activeSourceUrl.startsWith("file://", ignoreCase = true)
        if (!isLocalSource && !parentMetaId.startsWith("local_series:") && !parentMetaId.startsWith("local:")) {
            return emptyList()
        }
        _playlistsByKey.value[parentMetaId]?.takeIf { it.size > 1 }?.let { return it }
        _playlistsByKey.value.values.firstOrNull { list ->
            list.size > 1 && list.any { it.uri == activeSourceUrl }
        }?.let { return it }

        val scanned = LocalFolderVideosPlatform.state.value.videos
        if (scanned.isEmpty()) return emptyList()
        val (seriesGroups, _) = LocalMediaParser.groupVideos(scanned)
        val matchingGroup = seriesGroups.firstOrNull { grp ->
            grp.episodes.any { ep ->
                ep.uri == activeSourceUrl || ep.effectiveParentMetaId == parentMetaId
            } || "local_series:${grp.key}" == parentMetaId
        }
        if (matchingGroup != null && matchingGroup.episodes.isNotEmpty()) {
            registerFromItems(parentMetaId.ifBlank { "local_series:${matchingGroup.key}" }, matchingGroup.episodes)
            return _playlistsByKey.value[parentMetaId.ifBlank { "local_series:${matchingGroup.key}" }].orEmpty()
        }
        return emptyList()
    }

    fun findEpisode(
        parentMetaId: String,
        activeSourceUrl: String,
        videoId: String? = null,
        season: Int? = null,
        episode: Int? = null,
    ): LocalPlaylistEpisode? {
        val list = episodesForPlayback(parentMetaId, activeSourceUrl)
        if (list.isEmpty()) return null
        if (!videoId.isNullOrBlank()) {
            list.firstOrNull { it.videoId == videoId }?.let { return it }
        }
        if (season != null && episode != null) {
            list.firstOrNull { it.seasonNumber == season && it.episodeNumber == episode }?.let { return it }
        }
        return null
    }
}

internal expect object LocalFolderVideosPlatform {
    val state: StateFlow<LocalFolderVideosState>

    fun addFolder()
    fun removeFolder(treeUri: String)
    fun refresh()
    fun pickAndPlaySingleVideo()
}
