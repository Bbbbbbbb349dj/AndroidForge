#!/usr/bin/env python3
"""Local Android Folder Videos (Movies & Series with Posters) + Direct 'Open with Nuvio' Player."""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")
    if new:
        if new in content:
            return False
    elif old not in content:
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


def apply_local_media_patch(root: Path) -> list[str]:
    patched: list[str] = []

    # 1. Rich LocalVideoLaunchRequest in AppUrlBridge.kt
    bridge_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/deeplink/AppUrlBridge.kt"
    if bridge_kt.is_file():
        changed = False
        changed |= _replace_once(
            bridge_kt,
            "sealed interface AppDeepLink {\n",
            "data class LocalSidecarSubtitleItem(\n"
            "    val uri: String,\n"
            "    val language: String,\n"
            "    val label: String,\n"
            ")\n\n"
            "data class LocalVideoLaunchRequest(\n"
            "    val uri: String,\n"
            "    val title: String,\n"
            "    val filename: String? = null,\n"
            "    val subtitle: String? = null,\n"
            "    val mimeType: String? = null,\n"
            "    val poster: String? = null,\n"
            "    val background: String? = null,\n"
            "    val seasonNumber: Int? = null,\n"
            "    val episodeNumber: Int? = null,\n"
            "    val episodeTitle: String? = null,\n"
            "    val episodeThumbnail: String? = null,\n"
            "    val contentType: String = \"movie\",\n"
            "    val parentMetaId: String? = null,\n"
            "    val parentMetaType: String = \"movie\",\n"
            "    val sidecarSubtitles: List<LocalSidecarSubtitleItem> = emptyList(),\n"
            "    val nonce: Long = 0L,\n"
            ")\n\n"
            "sealed interface AppDeepLink {\n",
            "AppUrlBridge LocalVideoLaunchRequest",
        )
        changed |= _replace_once(
            bridge_kt,
            "object AppDeepLinkRepository {\n"
            "    private val _pendingDeepLink = MutableStateFlow<AppDeepLink?>(null)\n"
            "    val pendingDeepLink: StateFlow<AppDeepLink?> = _pendingDeepLink.asStateFlow()\n",
            "object AppDeepLinkRepository {\n"
            "    private val _pendingDeepLink = MutableStateFlow<AppDeepLink?>(null)\n"
            "    val pendingDeepLink: StateFlow<AppDeepLink?> = _pendingDeepLink.asStateFlow()\n\n"
            "    private var localVideoSeq = 0L\n"
            "    private val _pendingLocalVideo = MutableStateFlow<LocalVideoLaunchRequest?>(null)\n"
            "    val pendingLocalVideo: StateFlow<LocalVideoLaunchRequest?> = _pendingLocalVideo.asStateFlow()\n\n"
            "    fun openLocalVideo(\n"
            "        uri: String,\n"
            "        title: String,\n"
            "        filename: String? = null,\n"
            "        subtitle: String? = null,\n"
            "        mimeType: String? = null,\n"
            "        poster: String? = null,\n"
            "        background: String? = null,\n"
            "        seasonNumber: Int? = null,\n"
            "        episodeNumber: Int? = null,\n"
            "        episodeTitle: String? = null,\n"
            "        episodeThumbnail: String? = null,\n"
            "        contentType: String = \"movie\",\n"
            "        parentMetaId: String? = null,\n"
            "        parentMetaType: String = \"movie\",\n"
            "        sidecarSubtitles: List<LocalSidecarSubtitleItem> = emptyList(),\n"
            "    ) {\n"
            "        val trimmed = uri.trim()\n"
            "        if (trimmed.isEmpty()) return\n"
            "        localVideoSeq += 1L\n"
            "        _pendingLocalVideo.value = LocalVideoLaunchRequest(\n"
            "            uri = trimmed,\n"
            "            title = title.trim().ifEmpty { \"Local Video\" },\n"
            "            filename = filename?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            subtitle = subtitle?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            mimeType = mimeType?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            poster = poster?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            background = background?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            seasonNumber = seasonNumber,\n"
            "            episodeNumber = episodeNumber,\n"
            "            episodeTitle = episodeTitle?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            episodeThumbnail = episodeThumbnail?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            contentType = contentType,\n"
            "            parentMetaId = parentMetaId?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            parentMetaType = parentMetaType,\n"
            "            sidecarSubtitles = sidecarSubtitles,\n"
            "            nonce = localVideoSeq,\n"
            "        )\n"
            "    }\n\n"
            "    fun markLocalVideoConsumed(request: LocalVideoLaunchRequest) {\n"
            "        if (_pendingLocalVideo.value?.nonce == request.nonce) {\n"
            "            _pendingLocalVideo.value = null\n"
            "        }\n"
            "    }\n",
            "AppDeepLinkRepository pendingLocalVideo",
        )
        if changed:
            patched.append(str(bridge_kt.relative_to(root)))

    # 2. LocalFolderVideosPlatform + LocalMediaParser (commonMain + iosMain + androidMain)
    _write_text(
        root,
        "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.kt",
        r'''package com.nuvio.app.features.downloads

import com.nuvio.app.core.deeplink.LocalSidecarSubtitleItem
import kotlinx.coroutines.flow.StateFlow

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
        """(?i)(.*?)[\s._\-\[\(]*(?:Episode|Ep|E)[\s._\-]*(\d{1,3})\b(.*)""",
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

        if (folderSeason != null) {
            EP_ONLY_REGEX.matchEntire(rawStem)?.let { m ->
                val rawShow = m.groupValues[1]
                val ep = m.groupValues[2].toIntOrNull()
                val tail = m.groupValues[3]
                val (showTitle, year) = extractTitleAndYear(
                    rawShow.ifBlank { inferredSeriesFolderTitle.orEmpty() },
                    fallback = inferredSeriesFolderTitle,
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

internal expect object LocalFolderVideosPlatform {
    val state: StateFlow<LocalFolderVideosState>

    fun addFolder()
    fun removeFolder(treeUri: String)
    fun refresh()
    fun pickAndPlaySingleVideo()
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/iosMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.ios.kt",
        r'''package com.nuvio.app.features.downloads

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

internal actual object LocalFolderVideosPlatform {
    private val _state = MutableStateFlow(LocalFolderVideosState(isSupported = false))
    actual val state: StateFlow<LocalFolderVideosState> = _state.asStateFlow()

    actual fun addFolder() = Unit
    actual fun removeFolder(treeUri: String) = Unit
    actual fun refresh() = Unit
    actual fun pickAndPlaySingleVideo() = Unit
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.android.kt",
        r'''package com.nuvio.app.features.downloads

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import androidx.appcompat.app.AppCompatActivity
import com.nuvio.app.core.deeplink.AppDeepLinkRepository
import com.nuvio.app.core.deeplink.LocalSidecarSubtitleItem
import com.nuvio.app.core.ui.NuvioToastController
import java.lang.ref.WeakReference
import java.net.URLEncoder
import java.util.Locale
import java.util.concurrent.TimeUnit
import kotlin.math.abs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

internal actual object LocalFolderVideosPlatform {
    private const val PREFS_NAME = "nuvio_local_video_folders"
    private const val META_CACHE_PREFS = "nuvio_local_media_meta_v1"
    private const val KEY_TREE_URIS = "folder_tree_uris"
    private const val REQUEST_ADD_LOCAL_FOLDER = 51044
    private const val REQUEST_PICK_SINGLE_VIDEO = 51045
    private const val MAX_SCAN_DEPTH = 5
    private const val MAX_FILES_PER_SCAN = 1500

    private val VIDEO_EXTENSIONS = setOf(
        "mp4", "mkv", "avi", "webm", "mov", "m4v", "ts", "m2ts",
        "mts", "flv", "wmv", "3gp", "3g2", "mpg", "mpeg", "ogv", "vob", "m3u8",
    )
    private val SUBTITLE_EXTENSIONS = setOf("srt", "vtt", "ass", "ssa", "sub")
    private val IMAGE_EXTENSIONS = setOf("jpg", "jpeg", "png", "webp")

    private val httpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(8, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build()
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var scanJob: Job? = null
    private var appContext: Context? = null
    private var activityRef: WeakReference<AppCompatActivity>? = null

    private val _state = MutableStateFlow(LocalFolderVideosState(isSupported = true))
    actual val state: StateFlow<LocalFolderVideosState> = _state.asStateFlow()

    fun initialize(context: Context) {
        val app = context.applicationContext
        val firstInit = appContext == null
        appContext = app
        if (firstInit) {
            refresh()
        }
    }

    fun bindActivity(activity: AppCompatActivity) {
        activityRef = WeakReference(activity)
        if (appContext == null) {
            initialize(activity.applicationContext)
        }
    }

    fun unbindActivity(activity: AppCompatActivity) {
        if (activityRef?.get() === activity) {
            activityRef = null
        }
    }

    actual fun addFolder() {
        val activity = activityRef?.get()
        if (activity == null) {
            NuvioToastController.show("Unable to open folder picker right now")
            return
        }
        runCatching {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
                addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or
                        Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION or
                        Intent.FLAG_GRANT_PREFIX_URI_PERMISSION,
                )
            }
            @Suppress("DEPRECATION")
            activity.startActivityForResult(intent, REQUEST_ADD_LOCAL_FOLDER)
        }.onFailure { err ->
            NuvioToastController.show(err.message ?: "Android folder picker is unavailable on this device")
        }
    }

    actual fun pickAndPlaySingleVideo() {
        val activity = activityRef?.get()
        if (activity == null) {
            NuvioToastController.show("Unable to open file picker right now")
            return
        }
        runCatching {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "video/*"
                putExtra(
                    Intent.EXTRA_MIME_TYPES,
                    arrayOf(
                        "video/*",
                        "application/mp4",
                        "application/x-matroska",
                        "application/vnd.apple.mpegurl",
                        "application/x-mpegurl",
                    ),
                )
                addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or
                        Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION,
                )
            }
            @Suppress("DEPRECATION")
            activity.startActivityForResult(intent, REQUEST_PICK_SINGLE_VIDEO)
        }.onFailure { err ->
            NuvioToastController.show(err.message ?: "Unable to open video file picker")
        }
    }

    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != REQUEST_ADD_LOCAL_FOLDER && requestCode != REQUEST_PICK_SINGLE_VIDEO) {
            return false
        }
        if (resultCode != Activity.RESULT_OK) return true
        val uri = data?.data ?: return true
        val ctx = appContext ?: activityRef?.get()?.applicationContext ?: return true

        when (requestCode) {
            REQUEST_ADD_LOCAL_FOLDER -> {
                runCatching {
                    ctx.contentResolver.takePersistableUriPermission(
                        uri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION,
                    )
                }
                val saved = getSavedTreeUris(ctx).toMutableSet()
                saved.add(uri.toString())
                saveTreeUris(ctx, saved)
                NuvioToastController.show("Added folder: ${friendlyTreeName(uri)}")
                refresh()
            }

            REQUEST_PICK_SINGLE_VIDEO -> {
                runCatching {
                    ctx.contentResolver.takePersistableUriPermission(
                        uri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION,
                    )
                }
                val name = resolveDisplayName(ctx, uri)
                val mime = runCatching { ctx.contentResolver.getType(uri) }.getOrNull()
                val parsed = LocalMediaParser.parse(name)
                AppDeepLinkRepository.openLocalVideo(
                    uri = uri.toString(),
                    title = parsed.cleanTitle,
                    filename = name,
                    subtitle = "Local Storage",
                    mimeType = mime,
                    seasonNumber = parsed.seasonNumber,
                    episodeNumber = parsed.episodeNumber,
                    episodeTitle = parsed.episodeTitle,
                    contentType = if (parsed.isSeries) "series" else "movie",
                    parentMetaType = if (parsed.isSeries) "series" else "movie",
                )
            }
        }
        return true
    }

    actual fun removeFolder(treeUri: String) {
        val ctx = appContext ?: return
        val saved = getSavedTreeUris(ctx).toMutableSet()
        if (saved.remove(treeUri)) {
            saveTreeUris(ctx, saved)
            runCatching {
                ctx.contentResolver.releasePersistableUriPermission(
                    Uri.parse(treeUri),
                    Intent.FLAG_GRANT_READ_URI_PERMISSION,
                )
            }
            refresh()
        }
    }

    actual fun refresh() {
        val ctx = appContext ?: return
        scanJob?.cancel()
        scanJob = scope.launch {
            val savedUris = getSavedTreeUris(ctx)
            val folderItems = savedUris.map { raw ->
                LocalVideoFolder(
                    treeUri = raw,
                    displayName = friendlyTreeName(Uri.parse(raw)),
                )
            }
            _state.value = _state.value.copy(
                isSupported = true,
                isScanning = savedUris.isNotEmpty(),
                folders = folderItems,
                errorMessage = null,
            )
            if (savedUris.isEmpty()) {
                _state.value = LocalFolderVideosState(
                    isSupported = true,
                    isScanning = false,
                    folders = emptyList(),
                    videos = emptyList(),
                )
                return@launch
            }

            val discovered = mutableListOf<LocalVideoFileItem>()
            val seenUris = HashSet<String>()
            for (folder in folderItems) {
                if (discovered.size >= MAX_FILES_PER_SCAN) break
                runCatching {
                    val treeUri = Uri.parse(folder.treeUri)
                    val rootDocId = DocumentsContract.getTreeDocumentId(treeUri)
                    scanDocumentFolder(
                        ctx = ctx,
                        treeUri = treeUri,
                        parentDocId = rootDocId,
                        rootFolderUri = folder.treeUri,
                        folderLabel = folder.displayName,
                        parentFolderLabel = null,
                        depth = 0,
                        seenUris = seenUris,
                        out = discovered,
                    )
                }
            }

            // Publish immediately so local files appear right away, then enrich posters/metadata
            _state.value = LocalFolderVideosState(
                isSupported = true,
                isScanning = discovered.isNotEmpty(),
                folders = folderItems,
                videos = discovered,
            )

            if (discovered.isNotEmpty()) {
                val enriched = runCatching { enrichWithCinemetaPosters(ctx, discovered) }
                    .getOrDefault(discovered)
                _state.value = LocalFolderVideosState(
                    isSupported = true,
                    isScanning = false,
                    folders = folderItems,
                    videos = enriched,
                )
            }
        }
    }

    private data class FolderEntryRow(
        val docId: String,
        val name: String,
        val mime: String,
        val sizeBytes: Long,
        val lastMod: Long,
    )

    private fun scanDocumentFolder(
        ctx: Context,
        treeUri: Uri,
        parentDocId: String,
        rootFolderUri: String,
        folderLabel: String,
        parentFolderLabel: String?,
        depth: Int,
        seenUris: MutableSet<String>,
        out: MutableList<LocalVideoFileItem>,
    ) {
        if (depth > MAX_SCAN_DEPTH || out.size >= MAX_FILES_PER_SCAN) return
        val childrenUri = DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, parentDocId)
        val projection = arrayOf(
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED,
        )

        val subDirs = mutableListOf<Pair<String, String>>()
        val rows = mutableListOf<FolderEntryRow>()

        runCatching {
            ctx.contentResolver.query(childrenUri, projection, null, null, null)?.use { cursor ->
                val idIdx = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DOCUMENT_ID)
                val nameIdx = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DISPLAY_NAME)
                val mimeIdx = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_MIME_TYPE)
                val sizeIdx = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_SIZE)
                val modIdx = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_LAST_MODIFIED)

                while (cursor.moveToNext()) {
                    val docId = if (idIdx >= 0) cursor.getString(idIdx) else null
                    if (docId.isNullOrBlank()) continue
                    val name = (if (nameIdx >= 0) cursor.getString(nameIdx) else null)?.trim().orEmpty()
                    if (name.isEmpty() || name.startsWith(".")) continue
                    val mime = (if (mimeIdx >= 0) cursor.getString(mimeIdx) else null)?.trim().orEmpty()

                    if (mime == DocumentsContract.Document.MIME_TYPE_DIR) {
                        subDirs += docId to name
                    } else {
                        val sizeBytes = if (sizeIdx >= 0 && !cursor.isNull(sizeIdx)) cursor.getLong(sizeIdx) else 0L
                        val lastMod = if (modIdx >= 0 && !cursor.isNull(modIdx)) cursor.getLong(modIdx) else 0L
                        rows += FolderEntryRow(docId, name, mime, sizeBytes, lastMod)
                    }
                }
            }
        }

        // Detect local folder artwork (poster.jpg, folder.jpg, cover.png, backdrop.jpg, etc.)
        var folderPosterUri: String? = null
        var folderBackdropUri: String? = null
        val subtitleFiles = mutableListOf<Pair<String, String>>() // (name, uri)

        for (row in rows) {
            val ext = row.name.substringAfterLast('.', "").lowercase(Locale.US)
            if (ext in IMAGE_EXTENSIONS) {
                val stem = row.name.substringBeforeLast('.').lowercase(Locale.US)
                val imgUri = DocumentsContract.buildDocumentUriUsingTree(treeUri, row.docId).toString()
                if (stem in setOf("poster", "folder", "cover", "thumb")) {
                    folderPosterUri = imgUri
                } else if (stem in setOf("backdrop", "fanart", "background", "banner")) {
                    folderBackdropUri = imgUri
                }
            } else if (ext in SUBTITLE_EXTENSIONS) {
                val subUri = DocumentsContract.buildDocumentUriUsingTree(treeUri, row.docId).toString()
                subtitleFiles += row.name to subUri
            }
        }

        for (row in rows) {
            if (out.size >= MAX_FILES_PER_SCAN) break
            val ext = row.name.substringAfterLast('.', "").lowercase(Locale.US)
            val isVideo = row.mime.startsWith("video/", ignoreCase = true) ||
                row.mime.equals("application/x-matroska", ignoreCase = true) ||
                row.mime.equals("application/mp4", ignoreCase = true) ||
                ext in VIDEO_EXTENSIONS
            if (!isVideo) continue

            val fileUri = DocumentsContract.buildDocumentUriUsingTree(treeUri, row.docId)
            val uriStr = fileUri.toString()
            if (!seenUris.add(uriStr)) continue

            val videoStem = row.name.substringBeforeLast('.', row.name)
            val sidecars = subtitleFiles.mapNotNull { (subName, subUri) ->
                val subNoExt = subName.substringBeforeLast('.')
                if (subNoExt.equals(videoStem, ignoreCase = true) ||
                    subNoExt.startsWith("$videoStem.", ignoreCase = true)
                ) {
                    val langSuffix = subNoExt.removePrefix(videoStem).trim('.').ifBlank { "External" }
                    LocalSidecarSubtitleItem(
                        uri = subUri,
                        language = langSuffix.take(8).lowercase(Locale.US),
                        label = langSuffix,
                    )
                } else {
                    null
                }
            }

            // Also check same-stem image e.g. MovieName.jpg
            val stemPosterUri = rows.firstOrNull { r ->
                val rExt = r.name.substringAfterLast('.', "").lowercase(Locale.US)
                rExt in IMAGE_EXTENSIONS && r.name.substringBeforeLast('.').equals(videoStem, ignoreCase = true)
            }?.let { r -> DocumentsContract.buildDocumentUriUsingTree(treeUri, r.docId).toString() }

            val parsed = LocalMediaParser.parse(
                filename = row.name,
                parentFolderName = folderLabel,
                grandParentFolderName = parentFolderLabel,
            )

            out += LocalVideoFileItem(
                id = uriStr,
                uri = uriStr,
                title = parsed.cleanTitle,
                filename = row.name,
                folderUri = rootFolderUri,
                folderName = folderLabel,
                sizeBytes = row.sizeBytes.coerceAtLeast(0L),
                lastModifiedMs = row.lastMod.coerceAtLeast(0L),
                mimeType = row.mime.ifEmpty { null },
                extensionLabel = ext.uppercase(Locale.US).ifBlank { "VIDEO" },
                year = parsed.year,
                isSeries = parsed.isSeries,
                seriesKey = if (parsed.isSeries) LocalMediaParser.canonicalSeriesKey(parsed.cleanTitle) else null,
                seasonNumber = parsed.seasonNumber,
                episodeNumber = parsed.episodeNumber,
                episodeTitle = parsed.episodeTitle,
                posterUrl = stemPosterUri ?: folderPosterUri,
                backgroundUrl = folderBackdropUri,
                episodeThumbnailUrl = stemPosterUri,
                sidecarSubtitles = sidecars,
            )
        }

        for ((subDocId, subLabel) in subDirs) {
            if (out.size >= MAX_FILES_PER_SCAN) break
            scanDocumentFolder(
                ctx = ctx,
                treeUri = treeUri,
                parentDocId = subDocId,
                rootFolderUri = rootFolderUri,
                folderLabel = subLabel,
                parentFolderLabel = folderLabel,
                depth = depth + 1,
                seenUris = seenUris,
                out = out,
            )
        }
    }

    private data class CachedCinemetaEntry(
        val imdbId: String,
        val name: String,
        val year: Int?,
        val poster: String?,
        val background: String?,
        val episodes: Map<String, Pair<String?, String?>> = emptyMap(), // "s:e" -> (title, thumb)
    )

    private suspend fun enrichWithCinemetaPosters(
        ctx: Context,
        items: List<LocalVideoFileItem>,
    ): List<LocalVideoFileItem> = coroutineScope {
        val prefs = ctx.getSharedPreferences(META_CACHE_PREFS, Context.MODE_PRIVATE)
        val gate = Semaphore(4)

        val uniqueQueries = items.map { item ->
            Triple(
                if (item.isSeries) "series" else "movie",
                item.seriesKey ?: LocalMediaParser.canonicalSeriesKey(item.title),
                item.title to item.year,
            )
        }.distinctBy { "${it.first}::${it.second}" }

        val resolvedMap = uniqueQueries.map { (mediaType, keySlug, titleAndYear) ->
            async {
                val mapKey = "$mediaType::$keySlug"
                val meta = gate.withPermit {
                    lookupCinemeta(prefs, mediaType, keySlug, titleAndYear.first, titleAndYear.second)
                }
                mapKey to meta
            }
        }.awaitAll().toMap()

        items.map { item ->
            val mediaType = if (item.isSeries) "series" else "movie"
            val keySlug = item.seriesKey ?: LocalMediaParser.canonicalSeriesKey(item.title)
            val meta = resolvedMap["$mediaType::$keySlug"] ?: return@map item
            val epInfo = if (item.isSeries && item.seasonNumber != null && item.episodeNumber != null) {
                meta.episodes["${item.seasonNumber}:${item.episodeNumber}"]
            } else {
                null
            }
            item.copy(
                title = meta.name.ifBlank { item.title },
                year = item.year ?: meta.year,
                posterUrl = item.posterUrl ?: meta.poster,
                backgroundUrl = item.backgroundUrl ?: meta.background,
                episodeTitle = item.episodeTitle ?: epInfo?.first,
                episodeThumbnailUrl = item.episodeThumbnailUrl ?: epInfo?.second ?: meta.background,
                resolvedMetaId = meta.imdbId.takeIf { it.isNotBlank() },
            )
        }
    }

    private fun lookupCinemeta(
        prefs: android.content.SharedPreferences,
        mediaType: String,
        keySlug: String,
        queryTitle: String,
        queryYear: Int?,
    ): CachedCinemetaEntry? {
        if (queryTitle.length < 2) return null
        val cacheKey = "v1::$mediaType::$keySlug::${queryYear ?: 0}"
        val cachedJson = prefs.getString(cacheKey, null)
        if (cachedJson != null) {
            if (cachedJson == "NONE") return null
            return runCatching { parseCachedEntry(JSONObject(cachedJson)) }.getOrNull()
        }

        return runCatching {
            val encoded = URLEncoder.encode(queryTitle, "UTF-8").replace("+", "%20")
            val searchUrl = "https://v3-cinemeta.strem.io/catalog/$mediaType/top/search=$encoded.json"
            val body = httpGetString(searchUrl) ?: return@runCatching null
            val metas = JSONObject(body).optJSONArray("metas") ?: return@runCatching null
            if (metas.length() == 0) {
                prefs.edit().putString(cacheKey, "NONE").apply()
                return@runCatching null
            }

            var bestObj: JSONObject? = null
            var bestScore = Int.MIN_VALUE
            val targetCanon = LocalMediaParser.canonicalSeriesKey(queryTitle)

            for (i in 0 until metas.length().coerceAtMost(10)) {
                val obj = metas.optJSONObject(i) ?: continue
                val candName = obj.optString("name").trim()
                if (candName.isEmpty()) continue
                val candCanon = LocalMediaParser.canonicalSeriesKey(candName)
                val releaseInfo = obj.optString("releaseInfo")
                val candYear = Regex("""\b(19\d{2}|20\d{2})\b""").find(releaseInfo)?.value?.toIntOrNull()

                var score = 0
                if (candCanon == targetCanon) score += 100
                else if (candCanon.startsWith(targetCanon) || targetCanon.startsWith(candCanon)) score += 60
                else if (i == 0) score += 25

                if (queryYear != null && candYear != null) {
                    val diff = abs(queryYear - candYear)
                    score += when {
                        diff == 0 -> 40
                        diff == 1 -> 20
                        else -> -35
                    }
                }
                score -= i * 3
                if (score > bestScore) {
                    bestScore = score
                    bestObj = obj
                }
            }

            val chosen = bestObj?.takeIf { bestScore >= 20 }
            if (chosen == null) {
                prefs.edit().putString(cacheKey, "NONE").apply()
                return@runCatching null
            }

            val imdbId = chosen.optString("id").trim()
            val officialName = chosen.optString("name").trim().ifBlank { queryTitle }
            val poster = chosen.optString("poster").trim().takeIf { it.startsWith("http") }
                ?: imdbId.takeIf { it.startsWith("tt") }?.let { "https://images.metahub.space/poster/medium/$it/img" }
            val background = chosen.optString("background").trim().takeIf { it.startsWith("http") }
                ?: imdbId.takeIf { it.startsWith("tt") }?.let { "https://images.metahub.space/background/medium/$it/img" }
            val releaseYear = Regex("""\b(19\d{2}|20\d{2})\b""")
                .find(chosen.optString("releaseInfo"))?.value?.toIntOrNull()

            val episodeMap = HashMap<String, Pair<String?, String?>>()
            if (mediaType == "series" && imdbId.startsWith("tt")) {
                runCatching {
                    val detailBody = httpGetString("https://v3-cinemeta.strem.io/meta/series/$imdbId.json")
                    val videos = detailBody?.let { JSONObject(it).optJSONObject("meta")?.optJSONArray("videos") }
                    if (videos != null) {
                        for (j in 0 until videos.length()) {
                            val v = videos.optJSONObject(j) ?: continue
                            val s = v.optInt("season", -1)
                            val e = v.optInt("episode", v.optInt("number", -1))
                            if (s >= 0 && e >= 0) {
                                val epName = v.optString("name").ifBlank { v.optString("title") }.trim().ifBlank { null }
                                val epThumb = v.optString("thumbnail").trim().takeIf { it.startsWith("http") }
                                episodeMap["$s:$e"] = epName to epThumb
                            }
                        }
                    }
                }
            }

            val entry = CachedCinemetaEntry(
                imdbId = imdbId,
                name = officialName,
                year = releaseYear,
                poster = poster,
                background = background,
                episodes = episodeMap,
            )
            prefs.edit().putString(cacheKey, serializeCachedEntry(entry).toString()).apply()
            entry
        }.getOrNull()
    }

    private fun serializeCachedEntry(entry: CachedCinemetaEntry): JSONObject {
        val obj = JSONObject()
        obj.put("imdbId", entry.imdbId)
        obj.put("name", entry.name)
        entry.year?.let { obj.put("year", it) }
        entry.poster?.let { obj.put("poster", it) }
        entry.background?.let { obj.put("background", it) }
        val epsObj = JSONObject()
        entry.episodes.forEach { (k, pair) ->
            val eo = JSONObject()
            pair.first?.let { eo.put("t", it) }
            pair.second?.let { eo.put("u", it) }
            epsObj.put(k, eo)
        }
        obj.put("eps", epsObj)
        return obj
    }

    private fun parseCachedEntry(obj: JSONObject): CachedCinemetaEntry {
        val eps = HashMap<String, Pair<String?, String?>>()
        val epsObj = obj.optJSONObject("eps")
        if (epsObj != null) {
            val keys = epsObj.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val eo = epsObj.optJSONObject(k) ?: continue
                eps[k] = eo.optString("t").ifBlank { null } to eo.optString("u").ifBlank { null }
            }
        }
        return CachedCinemetaEntry(
            imdbId = obj.optString("imdbId"),
            name = obj.optString("name"),
            year = if (obj.has("year")) obj.optInt("year") else null,
            poster = obj.optString("poster").ifBlank { null },
            background = obj.optString("background").ifBlank { null },
            episodes = eps,
        )
    }

    private fun httpGetString(url: String): String? {
        val req = Request.Builder()
            .url(url)
            .header("User-Agent", "NuvioEnhanced/1.1.2")
            .build()
        httpClient.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            return resp.body?.string()
        }
    }

    internal fun resolveDisplayName(ctx: Context, uri: Uri): String {
        if (uri.scheme.equals("content", ignoreCase = true)) {
            runCatching {
                ctx.contentResolver.query(
                    uri,
                    arrayOf(OpenableColumns.DISPLAY_NAME),
                    null,
                    null,
                    null,
                )?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (idx >= 0) {
                            val name = cursor.getString(idx)?.trim()
                            if (!name.isNullOrEmpty()) return name
                        }
                    }
                }
            }
        }
        return uri.lastPathSegment
            ?.substringAfterLast('/')
            ?.substringAfterLast(':')
            ?.trim()
            ?.takeIf { it.isNotEmpty() }
            ?: "Local Video"
    }

    internal fun cleanVideoTitle(filename: String): String =
        LocalMediaParser.parse(filename).cleanTitle

    private fun friendlyTreeName(uri: Uri): String {
        val docId = runCatching { DocumentsContract.getTreeDocumentId(uri) }.getOrNull()
            ?: uri.lastPathSegment
            ?: return "Local Folder"
        val cleaned = docId.substringAfter(':', docId).trim('/')
        return if (cleaned.isEmpty()) "Internal Storage" else cleaned.substringAfterLast('/')
    }

    private fun getSavedTreeUris(ctx: Context): List<String> {
        val raw = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getStringSet(KEY_TREE_URIS, emptySet())
            .orEmpty()
        return raw.filter { it.isNotBlank() }.sorted()
    }

    private fun saveTreeUris(ctx: Context, uris: Set<String>) {
        ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putStringSet(KEY_TREE_URIS, uris)
            .apply()
    }
}
''',
        patched,
    )

    # 3. DownloadsScreen.kt: Native Nuvio Posters + Movies & Series (Season -> Episode) drilldown
    dl_screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsScreen.kt"
    if dl_screen.is_file():
        changed = False
        changed |= _replace_once(
            dl_screen,
            "import androidx.compose.material.icons.Icons\n"
            "import androidx.compose.material.icons.rounded.Download\n"
            "import androidx.compose.material.icons.rounded.Settings\n",
            "import androidx.compose.foundation.BorderStroke\n"
            "import androidx.compose.foundation.clickable\n"
            "import androidx.compose.foundation.horizontalScroll\n"
            "import androidx.compose.foundation.layout.Spacer\n"
            "import androidx.compose.foundation.layout.width\n"
            "import androidx.compose.foundation.rememberScrollState\n"
            "import androidx.compose.foundation.shape.RoundedCornerShape\n"
            "import androidx.compose.material.icons.Icons\n"
            "import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight\n"
            "import androidx.compose.material.icons.rounded.Add\n"
            "import androidx.compose.material.icons.rounded.Close\n"
            "import androidx.compose.material.icons.rounded.Download\n"
            "import androidx.compose.material.icons.rounded.Folder\n"
            "import androidx.compose.material.icons.rounded.Movie\n"
            "import androidx.compose.material.icons.rounded.PlayArrow\n"
            "import androidx.compose.material.icons.rounded.Refresh\n"
            "import androidx.compose.material.icons.rounded.Settings\n"
            "import androidx.compose.material3.Surface\n"
            "import androidx.compose.ui.text.font.FontWeight\n"
            "import androidx.compose.ui.text.style.TextOverflow\n",
            "DownloadsScreen local media & poster imports",
        )
        changed |= _replace_once(
            dl_screen,
            "import com.nuvio.app.core.ui.NuvioScreen\n",
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n"
            "import com.nuvio.app.core.ui.NuvioPosterCard\n"
            "import com.nuvio.app.core.ui.NuvioScreen\n"
            "import nuvio.composeapp.generated.resources.media_movie\n"
            "import nuvio.composeapp.generated.resources.media_series\n",
            "DownloadsScreen AppDeepLinkRepository & NuvioPosterCard imports",
        )
        changed |= _replace_once(
            dl_screen,
            "    var selectedShowId by rememberSaveable(initialShowId) { mutableStateOf(initialShowId) }\n"
            "    var actionsItemId by rememberSaveable { mutableStateOf<String?>(null) }\n"
            "    var deleteItemId by rememberSaveable { mutableStateOf<String?>(null) }\n",
            "    var selectedShowId by rememberSaveable(initialShowId) { mutableStateOf(initialShowId) }\n"
            "    var selectedLocalSeriesKey by rememberSaveable { mutableStateOf<String?>(null) }\n"
            "    var actionsItemId by rememberSaveable { mutableStateOf<String?>(null) }\n"
            "    var deleteItemId by rememberSaveable { mutableStateOf<String?>(null) }\n"
            "    val localState by LocalFolderVideosPlatform.state.collectAsStateWithLifecycle()\n"
            "    var viewFilter by rememberSaveable { mutableStateOf(\"all\") }\n"
            "    var selectedLocalFolderUri by rememberSaveable { mutableStateOf<String?>(null) }\n"
            "    val visibleLocalVideos = remember(localState.videos, selectedLocalFolderUri) {\n"
            "        if (selectedLocalFolderUri == null) localState.videos\n"
            "        else localState.videos.filter { it.folderUri == selectedLocalFolderUri }\n"
            "    }\n"
            "    val (localSeriesGroups, localMovies) = remember(visibleLocalVideos) {\n"
            "        LocalMediaParser.groupVideos(visibleLocalVideos)\n"
            "    }\n"
            "    val activeLocalSeries = remember(selectedLocalSeriesKey, localSeriesGroups) {\n"
            "        selectedLocalSeriesKey?.let { key -> localSeriesGroups.firstOrNull { it.key == key } }\n"
            "    }\n"
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
            "            episodeNumber = video.episodeNumber,\n"
            "            episodeTitle = video.episodeTitle,\n"
            "            episodeThumbnail = video.episodeThumbnailUrl,\n"
            "            contentType = if (video.isSeries) \"series\" else \"movie\",\n"
            "            parentMetaId = video.effectiveParentMetaId,\n"
            "            parentMetaType = if (video.isSeries) \"series\" else \"movie\",\n"
            "            sidecarSubtitles = video.sidecarSubtitles,\n"
            "        )\n"
            "    }\n",
            "DownloadsScreen local series/movies state & playLocalVideo",
        )
        changed |= _replace_once(
            dl_screen,
            "    PlatformBackHandler(enabled = selectedShowId != null && onBackFromShow == null) {\n"
            "        selectedShowId = null\n"
            "    }\n",
            "    PlatformBackHandler(enabled = selectedLocalSeriesKey != null || (selectedShowId != null && onBackFromShow == null)) {\n"
            "        if (selectedLocalSeriesKey != null) {\n"
            "            selectedLocalSeriesKey = null\n"
            "        } else {\n"
            "            selectedShowId = null\n"
            "        }\n"
            "    }\n",
            "DownloadsScreen PlatformBackHandler for local series",
        )
        changed |= _replace_once(
            dl_screen,
            "            NuvioScreenHeader(\n"
            "                title = if (selectedShowId == null) {\n"
            "                    stringResource(Res.string.compose_settings_root_downloads_title)\n"
            "                } else {\n"
            "                    selectedShowTitle ?: stringResource(Res.string.downloads_show_downloads)\n"
            "                },\n"
            "                onBack = if (selectedShowId != null) {\n"
            "                    { onBackFromShow?.invoke() ?: run { selectedShowId = null } }\n"
            "                } else {\n"
            "                    onBack\n"
            "                },\n"
            "                actions = {\n"
            "                    OpenDownloadsFolderButton(tint = MaterialTheme.nuvio.colors.textPrimary)\n"
            "                    if (selectedShowId == null && onOpenSettings != null) {\n",
            "            NuvioScreenHeader(\n"
            "                title = when {\n"
            "                    activeLocalSeries != null -> activeLocalSeries.title\n"
            "                    selectedShowId != null -> selectedShowTitle ?: stringResource(Res.string.downloads_show_downloads)\n"
            "                    else -> stringResource(Res.string.compose_settings_root_downloads_title)\n"
            "                },\n"
            "                onBack = when {\n"
            "                    selectedLocalSeriesKey != null -> ({ selectedLocalSeriesKey = null })\n"
            "                    selectedShowId != null -> ({ onBackFromShow?.invoke() ?: run { selectedShowId = null } })\n"
            "                    else -> onBack\n"
            "                },\n"
            "                actions = {\n"
            "                    OpenDownloadsFolderButton(tint = MaterialTheme.nuvio.colors.textPrimary)\n"
            "                    if (selectedShowId == null && activeLocalSeries == null && onOpenSettings != null) {\n",
            "DownloadsScreen header support activeLocalSeries",
        )
        changed |= _replace_once(
            dl_screen,
            "        val showId = selectedShowId\n"
            "        if (showId == null) {\n"
            "            downloadsRootContent(\n"
            "                items = uiState.items,\n"
            "                speeds = speeds,\n"
            "                watchStatusOf = watchStatusOf,\n"
            "                onPlay = onOpenDownload,\n"
            "                onOpenShow = { item ->\n"
            "                    onNavigateToShow?.invoke(item.parentMetaId, item.title) ?: run { selectedShowId = item.parentMetaId }\n"
            "                },\n"
            "                onOpenActions = onOpenActions,\n"
            "            )\n"
            "        } else {\n",
            "        val showId = selectedShowId\n"
            "        if (activeLocalSeries != null) {\n"
            "            localSeriesShowContent(\n"
            "                series = activeLocalSeries,\n"
            "                watchProgressState = watchProgressState,\n"
            "                onPlayEpisode = playLocalVideo,\n"
            "            )\n"
            "        } else if (showId == null) {\n"
            "            downloadsRootContent(\n"
            "                items = uiState.items,\n"
            "                localState = localState,\n"
            "                localSeriesGroups = localSeriesGroups,\n"
            "                localMovies = localMovies,\n"
            "                watchProgressState = watchProgressState,\n"
            "                viewFilter = viewFilter,\n"
            "                onViewFilterChange = { viewFilter = it },\n"
            "                selectedLocalFolderUri = selectedLocalFolderUri,\n"
            "                onSelectLocalFolderUri = { selectedLocalFolderUri = it },\n"
            "                onAddLocalFolder = { LocalFolderVideosPlatform.addFolder() },\n"
            "                onRemoveLocalFolder = { uri ->\n"
            "                    if (selectedLocalFolderUri == uri) selectedLocalFolderUri = null\n"
            "                    LocalFolderVideosPlatform.removeFolder(uri)\n"
            "                },\n"
            "                onPickSingleVideo = { LocalFolderVideosPlatform.pickAndPlaySingleVideo() },\n"
            "                onRefreshLocalFolders = { LocalFolderVideosPlatform.refresh() },\n"
            "                onOpenLocalSeries = { series -> selectedLocalSeriesKey = series.key },\n"
            "                onPlayLocalVideo = playLocalVideo,\n"
            "                speeds = speeds,\n"
            "                watchStatusOf = watchStatusOf,\n"
            "                onPlay = onOpenDownload,\n"
            "                onOpenShow = { item ->\n"
            "                    onNavigateToShow?.invoke(item.parentMetaId, item.title) ?: run { selectedShowId = item.parentMetaId }\n"
            "                },\n"
            "                onOpenActions = onOpenActions,\n"
            "            )\n"
            "        } else {\n",
            "DownloadsScreen branch activeLocalSeries & pass localSeriesGroups/localMovies",
        )
        changed |= _replace_once(
            dl_screen,
            "private fun LazyListScope.downloadsRootContent(\n"
            "    items: List<DownloadItem>,\n"
            "    speeds: Map<String, Long>,\n"
            "    watchStatusOf: (DownloadItem) -> DownloadWatchStatus,\n"
            "    onPlay: (DownloadItem) -> Unit,\n"
            "    onOpenShow: (DownloadItem) -> Unit,\n"
            "    onOpenActions: (DownloadItem) -> Unit,\n"
            ") {\n"
            "    if (items.isEmpty()) {\n"
            "        item(key = \"empty\") {\n"
            "            DownloadsEmptyState(\n"
            "                title = stringResource(Res.string.downloads_empty_title),\n"
            "                message = stringResource(Res.string.downloads_empty_message),\n"
            "            )\n"
            "        }\n"
            "        return\n"
            "    }\n",
            "private fun LazyListScope.downloadsRootContent(\n"
            "    items: List<DownloadItem>,\n"
            "    localState: LocalFolderVideosState,\n"
            "    localSeriesGroups: List<LocalSeriesGroup>,\n"
            "    localMovies: List<LocalVideoFileItem>,\n"
            "    watchProgressState: com.nuvio.app.features.watchprogress.WatchProgressUiState,\n"
            "    viewFilter: String,\n"
            "    onViewFilterChange: (String) -> Unit,\n"
            "    selectedLocalFolderUri: String?,\n"
            "    onSelectLocalFolderUri: (String?) -> Unit,\n"
            "    onAddLocalFolder: () -> Unit,\n"
            "    onRemoveLocalFolder: (String) -> Unit,\n"
            "    onPickSingleVideo: () -> Unit,\n"
            "    onRefreshLocalFolders: () -> Unit,\n"
            "    onOpenLocalSeries: (LocalSeriesGroup) -> Unit,\n"
            "    onPlayLocalVideo: (LocalVideoFileItem) -> Unit,\n"
            "    speeds: Map<String, Long>,\n"
            "    watchStatusOf: (DownloadItem) -> DownloadWatchStatus,\n"
            "    onPlay: (DownloadItem) -> Unit,\n"
            "    onOpenShow: (DownloadItem) -> Unit,\n"
            "    onOpenActions: (DownloadItem) -> Unit,\n"
            ") {\n"
            "    val localTitlesCount = localSeriesGroups.size + localMovies.size\n"
            "    if (localState.isSupported) {\n"
            "        item(key = \"local-folders-toolbar\") {\n"
            "            LocalFoldersToolbar(\n"
            "                viewFilter = viewFilter,\n"
            "                appDownloadsCount = items.size,\n"
            "                localTitlesCount = localTitlesCount,\n"
            "                folders = localState.folders,\n"
            "                selectedFolderUri = selectedLocalFolderUri,\n"
            "                isScanning = localState.isScanning,\n"
            "                onViewFilterChange = onViewFilterChange,\n"
            "                onSelectFolderUri = onSelectLocalFolderUri,\n"
            "                onAddFolder = onAddLocalFolder,\n"
            "                onRemoveFolder = onRemoveLocalFolder,\n"
            "                onPickSingleVideo = onPickSingleVideo,\n"
            "                onRefresh = onRefreshLocalFolders,\n"
            "            )\n"
            "        }\n"
            "    }\n\n"
            "    val showAppDownloads = !localState.isSupported || viewFilter == \"all\" || viewFilter == \"app\"\n"
            "    val showLocalFolders = localState.isSupported && (viewFilter == \"all\" || viewFilter == \"local\")\n\n"
            "    if (showLocalFolders && (localSeriesGroups.isNotEmpty() || localMovies.isNotEmpty())) {\n"
            "        if (localSeriesGroups.isNotEmpty()) {\n"
            "            item(key = \"header-local-series\") {\n"
            "                SectionHeader(\n"
            "                    title = \"Local Series\",\n"
            "                    detail = \"${localSeriesGroups.size} ${if (localSeriesGroups.size == 1) \"show\" else \"shows\"}\",\n"
            "                )\n"
            "            }\n"
            "            items(localSeriesGroups, key = { \"local_series:${it.key}\" }) { series ->\n"
            "                LocalSeriesRow(\n"
            "                    series = series,\n"
            "                    onOpen = { onOpenLocalSeries(series) },\n"
            "                )\n"
            "            }\n"
            "        }\n\n"
            "        if (localMovies.isNotEmpty()) {\n"
            "            item(key = \"header-local-movies\") {\n"
            "                SectionHeader(\n"
            "                    title = \"Local Movies\",\n"
            "                    detail = \"${localMovies.size} ${if (localMovies.size == 1) \"movie\" else \"movies\"}\",\n"
            "                )\n"
            "            }\n"
            "            items(localMovies, key = { \"local_movie:${it.id}\" }) { movie ->\n"
            "                val progress = watchProgressState.items[movie.syntheticVideoId]\n"
            "                LocalMovieRow(\n"
            "                    movie = movie,\n"
            "                    progressFraction = progress?.progressFraction ?: 0f,\n"
            "                    isCompleted = progress?.isEffectivelyCompleted == true,\n"
            "                    onPlay = { onPlayLocalVideo(movie) },\n"
            "                )\n"
            "            }\n"
            "        }\n"
            "    } else if (localState.isSupported && viewFilter == \"local\" && !localState.isScanning) {\n"
            "        item(key = \"local-empty\") {\n"
            "            DownloadsEmptyState(\n"
            "                title = if (localState.folders.isEmpty()) \"No Android folders added yet\" else \"No video files found\",\n"
            "                message = if (localState.folders.isEmpty()) {\n"
            "                    \"Tap '+ Add Folder' above to automatically organize phone videos into Movies & Series with posters, or 'Open Video' for a single file.\"\n"
            "                } else {\n"
            "                    \"No playable video files (.mp4, .mkv, .avi, .webm, .mov, .ts) were found in the selected folder.\"\n"
            "                },\n"
            "            )\n"
            "        }\n"
            "    }\n\n"
            "    if (!showAppDownloads) return\n\n"
            "    if (items.isEmpty()) {\n"
            "        if (!showLocalFolders || (localSeriesGroups.isEmpty() && localMovies.isEmpty())) {\n"
            "            item(key = \"empty\") {\n"
            "                DownloadsEmptyState(\n"
            "                    title = stringResource(Res.string.downloads_empty_title),\n"
            "                    message = stringResource(Res.string.downloads_empty_message),\n"
            "                )\n"
            "            }\n"
            "        }\n"
            "        return\n"
            "    }\n",
            "DownloadsScreen movies & series sections in downloadsRootContent",
        )

        local_composables = r'''

private fun LazyListScope.localSeriesShowContent(
    series: LocalSeriesGroup,
    watchProgressState: com.nuvio.app.features.watchprogress.WatchProgressUiState,
    onPlayEpisode: (LocalVideoFileItem) -> Unit,
) {
    val episodes = series.episodes
    val watchedCount = episodes.count { ep ->
        watchProgressState.items[ep.syntheticVideoId]?.isEffectivelyCompleted == true
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
                val progress = watchProgressState.items[episode.syntheticVideoId]
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
'''
        current_dl = dl_screen.read_text(encoding="utf-8", errors="replace")
        if "fun LocalFoldersToolbar(" not in current_dl:
            dl_screen.write_text(current_dl + local_composables, encoding="utf-8")
            changed = True
        if changed:
            patched.append(str(dl_screen.relative_to(root)))

    # 4. Dedicated LocalVideoPlayerActivity.kt for direct, zero-gate 'Open with Nuvio' playback
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
import com.nuvio.app.features.downloads.LocalFolderVideosPlatform
import com.nuvio.app.features.downloads.LocalMediaParser
import com.nuvio.app.features.player.ExternalPlayerPlatform
import com.nuvio.app.features.player.PlayerScreen
import com.nuvio.app.features.profiles.ProfileRepository
import com.nuvio.app.features.watchprogress.WatchProgressRepository

class LocalVideoPlayerActivity : MainActivity() {
    private var activeIntent by mutableStateOf<Intent?>(null)
    private var intentNonce by mutableLongStateOf(0L)

    override fun onCreate(savedInstanceState: Bundle?) {
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
                                parentMetaId = resolved.syntheticId,
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

        val parsed = LocalMediaParser.parse(displayName)
        val uriString = uri.toString()
        val syntheticId = "local:${uriString.hashCode().toUInt().toString(16)}"

        WatchProgressRepository.ensureLoaded()
        val resumeEntry = runCatching {
            WatchProgressRepository.progressForVideo(syntheticId)?.takeIf { it.isResumable }
        }.getOrNull()

        return ResolvedExternalVideo(
            uriString = uriString,
            displayName = displayName,
            title = parsed.cleanTitle,
            cleanMimeType = rawMime,
            contentType = if (parsed.isSeries) "series" else "movie",
            seasonNumber = parsed.seasonNumber,
            episodeNumber = parsed.episodeNumber,
            episodeTitle = parsed.episodeTitle,
            syntheticId = syntheticId,
            resumePositionMs = resumeEntry?.lastPositionMs?.takeIf { it > 0L } ?: 0L,
            resumeFraction = resumeEntry?.progressFraction?.takeIf { it > 0f },
        )
    }
}
''',
        patched,
    )

    # 5. AndroidManifest.xml: Register LocalVideoPlayerActivity for "Open with Nuvio" from Files/Gallery/Storage
    manifest_xml = root / "androidApp/src/main/AndroidManifest.xml"
    if manifest_xml.is_file():
        changed = _replace_once(
            manifest_xml,
            '        <activity\n'
            '            android:exported="true"\n'
            '            android:name="com.nuvio.app.MainActivity"\n'
            '            android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"\n'
            '            android:supportsPictureInPicture="true"\n'
            '            android:theme="@style/Theme.Nuvio.Splash" />\n',
            '        <activity\n'
            '            android:exported="true"\n'
            '            android:name="com.nuvio.app.MainActivity"\n'
            '            android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"\n'
            '            android:supportsPictureInPicture="true"\n'
            '            android:theme="@style/Theme.Nuvio.Splash" />\n\n'
            '        <activity\n'
            '            android:name="com.nuvio.app.LocalVideoPlayerActivity"\n'
            '            android:exported="true"\n'
            '            android:label="@string/app_name"\n'
            '            android:icon="@mipmap/ic_launcher"\n'
            '            android:roundIcon="@mipmap/ic_launcher_round"\n'
            '            android:launchMode="singleTask"\n'
            '            android:taskAffinity="com.nuvio.app.localplayer"\n'
            '            android:screenOrientation="sensorLandscape"\n'
            '            android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation|keyboard|keyboardHidden|uiMode"\n'
            '            android:supportsPictureInPicture="true"\n'
            '            android:theme="@style/Theme.Nuvio">\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.VIEW" />\n'
            '                <category android:name="android.intent.category.DEFAULT" />\n'
            '                <category android:name="android.intent.category.BROWSABLE" />\n'
            '                <data android:scheme="content" />\n'
            '                <data android:scheme="file" />\n'
            '                <data android:mimeType="video/*" />\n'
            '                <data android:mimeType="application/mp4" />\n'
            '                <data android:mimeType="application/x-matroska" />\n'
            '                <data android:mimeType="video/x-matroska" />\n'
            '                <data android:mimeType="video/mp2t" />\n'
            '                <data android:mimeType="application/vnd.apple.mpegurl" />\n'
            '                <data android:mimeType="application/x-mpegurl" />\n'
            '                <data android:mimeType="application/ogg" />\n'
            '            </intent-filter>\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.VIEW" />\n'
            '                <category android:name="android.intent.category.DEFAULT" />\n'
            '                <data android:scheme="file" />\n'
            '                <data android:scheme="content" />\n'
            '                <data android:host="*" />\n'
            '                <data android:mimeType="application/octet-stream" />\n'
            '                <data android:pathPattern=".*\\\\.mkv" />\n'
            '                <data android:pathPattern=".*\\\\.mp4" />\n'
            '                <data android:pathPattern=".*\\\\.avi" />\n'
            '                <data android:pathPattern=".*\\\\.webm" />\n'
            '                <data android:pathPattern=".*\\\\.mov" />\n'
            '                <data android:pathPattern=".*\\\\.ts" />\n'
            '                <data android:pathPattern=".*\\\\.m4v" />\n'
            '            </intent-filter>\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.SEND" />\n'
            '                <category android:name="android.intent.category.DEFAULT" />\n'
            '                <data android:mimeType="video/*" />\n'
            '            </intent-filter>\n'
            '        </activity>\n',
            "AndroidManifest LocalVideoPlayerActivity Open with Nuvio intent-filters",
        )
        if changed:
            patched.append(str(manifest_xml.relative_to(root)))

    # 6. MainActivity.kt: Wire LocalFolderVideosPlatform lifecycle + SAF picker result callback
    main_act = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/MainActivity.kt"
    if main_act.is_file():
        changed = False
        changed |= _replace_once(
            main_act,
            "import com.nuvio.app.features.downloads.DownloadsExternalFolderPlatform\n",
            "import com.nuvio.app.features.downloads.DownloadsExternalFolderPlatform\n"
            "import com.nuvio.app.features.downloads.LocalFolderVideosPlatform\n",
            "MainActivity LocalFolderVideosPlatform import",
        )
        changed |= _replace_once(
            main_act,
            "        DownloadsExternalFolderPlatform.initialize(applicationContext)\n"
            "        DownloadsExternalFolderPlatform.bindActivity(this)\n",
            "        DownloadsExternalFolderPlatform.initialize(applicationContext)\n"
            "        DownloadsExternalFolderPlatform.bindActivity(this)\n"
            "        LocalFolderVideosPlatform.initialize(applicationContext)\n"
            "        LocalFolderVideosPlatform.bindActivity(this)\n",
            "MainActivity initialize & bind LocalFolderVideosPlatform",
        )
        changed |= _replace_once(
            main_act,
            "        DownloadsExternalFolderPlatform.unbindActivity(this)\n",
            "        DownloadsExternalFolderPlatform.unbindActivity(this)\n"
            "        LocalFolderVideosPlatform.unbindActivity(this)\n",
            "MainActivity unbind LocalFolderVideosPlatform",
        )
        changed |= _replace_once(
            main_act,
            "        if (DownloadsExternalFolderPlatform.handleActivityResult(requestCode, resultCode, data)) {\n"
            "            return\n"
            "        }\n",
            "        if (DownloadsExternalFolderPlatform.handleActivityResult(requestCode, resultCode, data)) {\n"
            "            return\n"
            "        }\n"
            "        if (LocalFolderVideosPlatform.onActivityResult(requestCode, resultCode, data)) {\n"
            "            return\n"
            "        }\n",
            "MainActivity LocalFolderVideosPlatform onActivityResult",
        )
        if changed:
            patched.append(str(main_act.relative_to(root)))

    # 7. MainAppContent.kt: Observe pendingLocalVideo for in-app Local Media playback with full posters/subtitles
    main_app = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"
    if main_app.is_file():
        changed = False
        changed |= _replace_once(
            main_app,
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n",
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n"
            "import com.nuvio.app.core.deeplink.LocalVideoLaunchRequest\n"
            "import com.nuvio.app.features.streams.StreamSubtitle\n",
            "MainAppContent LocalVideoLaunchRequest & StreamSubtitle imports",
        )
        changed |= _replace_once(
            main_app,
            "            val launchId = PlayerLaunchStore.put(playerLaunch)\n"
            "            navController.navigate(PlayerRoute(launchId = launchId, title = playerLaunch.title))\n"
            "        }\n",
            "            val launchId = PlayerLaunchStore.put(playerLaunch)\n"
            "            navController.navigate(PlayerRoute(launchId = launchId, title = playerLaunch.title))\n"
            "        }\n\n"
            "        fun openLocalVideo(req: LocalVideoLaunchRequest) {\n"
            "            val syntheticId = \"local:${req.uri.hashCode().toUInt().toString(16)}\"\n"
            "            val resumeEntry = WatchProgressRepository.progressForVideo(syntheticId)\n"
            "                ?.takeIf { it.isResumable }\n"
            "            val cleanMime = req.mimeType\n"
            "                ?.trim()\n"
            "                ?.takeIf { it.isNotEmpty() && !it.endsWith(\"/*\") && it != \"application/octet-stream\" }\n"
            "            val sidecars = req.sidecarSubtitles.map { sub ->\n"
            "                StreamSubtitle(url = sub.uri, language = sub.language, name = sub.label)\n"
            "            }\n"
            "            val playerLaunch = PlayerLaunch(\n"
            "                profileId = activePlaybackProfileId,\n"
            "                title = req.title,\n"
            "                sourceUrl = req.uri,\n"
            "                externalSubtitles = DownloadSubtitles.localSubtitles(req.uri) + sidecars,\n"
            "                streamType = cleanMime,\n"
            "                streamTitle = req.filename ?: req.title,\n"
            "                streamSubtitle = req.subtitle ?: \"Local Storage\",\n"
            "                providerName = \"Local Storage\",\n"
            "                poster = req.poster,\n"
            "                background = req.background,\n"
            "                seasonNumber = req.seasonNumber,\n"
            "                episodeNumber = req.episodeNumber,\n"
            "                episodeTitle = req.episodeTitle,\n"
            "                episodeThumbnail = req.episodeThumbnail,\n"
            "                contentType = req.contentType,\n"
            "                videoId = syntheticId,\n"
            "                parentMetaId = req.parentMetaId ?: syntheticId,\n"
            "                parentMetaType = req.parentMetaType,\n"
            "                sourceFilename = req.filename,\n"
            "                initialPositionMs = resumeEntry?.lastPositionMs?.takeIf { it > 0L } ?: 0L,\n"
            "                initialProgressFraction = resumeEntry?.progressFraction?.takeIf { it > 0f },\n"
            "            )\n"
            "            val launchId = PlayerLaunchStore.put(playerLaunch)\n"
            "            navController.navigate(PlayerRoute(launchId = launchId, title = playerLaunch.title))\n"
            "        }\n\n"
            "        LaunchedEffect(navController, ownsAppRuntime) {\n"
            "            if (!ownsAppRuntime) return@LaunchedEffect\n"
            "            AppDeepLinkRepository.pendingLocalVideo.collect { req ->\n"
            "                if (req == null) return@collect\n"
            "                AppDeepLinkRepository.markLocalVideoConsumed(req)\n"
            "                openLocalVideo(req)\n"
            "            }\n"
            "        }\n",
            "MainAppContent openLocalVideo & pendingLocalVideo collector",
        )
        if changed:
            patched.append(str(main_app.relative_to(root)))

    # 8. PlaybackMediaItems.android.kt: Support explicit MIME in inferMimeTypeFromStreamType + contentResolver & displayName fallback
    media_items = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlaybackMediaItems.android.kt"
    if media_items.is_file():
        changed = False
        changed |= _replace_once(
            media_items,
            "    return when (normalized) {\n"
            "        \"hls\", \"m3u8\" -> MimeTypes.APPLICATION_M3U8\n"
            "        \"dash\", \"mpd\" -> MimeTypes.APPLICATION_MPD\n"
            "        \"smoothstreaming\", \"ss\" -> MimeTypes.APPLICATION_SS\n"
            "        else -> null\n"
            "    }\n",
            "    return when (normalized) {\n"
            "        \"hls\", \"m3u8\" -> MimeTypes.APPLICATION_M3U8\n"
            "        \"dash\", \"mpd\" -> MimeTypes.APPLICATION_MPD\n"
            "        \"smoothstreaming\", \"ss\" -> MimeTypes.APPLICATION_SS\n"
            "        else -> normalizeMimeType(normalized)\n"
            "    }\n",
            "PlaybackMediaItems inferMimeTypeFromStreamType delegate normalizeMimeType",
        )
        changed |= _replace_once(
            media_items,
            "        \"video/x-matroska\",\n"
            "        \"audio/x-matroska\",\n"
            "        \"video/mkv\",\n"
            "        \"audio/mkv\" -> MimeTypes.VIDEO_MATROSKA\n\n"
            "        else -> null\n",
            "        \"video/x-matroska\",\n"
            "        \"audio/x-matroska\",\n"
            "        \"application/x-matroska\",\n"
            "        \"video/mkv\",\n"
            "        \"audio/mkv\" -> MimeTypes.VIDEO_MATROSKA\n\n"
            "        \"video/quicktime\" -> MIME_VIDEO_QUICK_TIME\n"
            "        \"video/x-msvideo\",\n"
            "        \"video/avi\" -> MimeTypes.VIDEO_AVI\n"
            "        \"video/mpeg\" -> MimeTypes.VIDEO_MPEG\n\n"
            "        else -> null\n",
            "PlaybackMediaItems normalizeMimeType extra local container formats",
        )
        changed |= _replace_once(
            media_items,
            "private fun sniffLocalMimeType(url: String): String? {\n"
            "    val header = readLocalHeaderBytes(url) ?: return null\n"
            "    return mimeTypeFromHeader(header)\n"
            "}\n",
            "private fun sniffLocalMimeType(url: String): String? {\n"
            "    val header = readLocalHeaderBytes(url)\n"
            "    if (header != null) {\n"
            "        mimeTypeFromHeader(header)?.let { return it }\n"
            "    }\n"
            "    return runCatching {\n"
            "        val uri = Uri.parse(url)\n"
            "        if (uri.scheme?.equals(\"content\", ignoreCase = true) == true) {\n"
            "            val context = PlayerSettingsStorage.applicationContext() ?: return@runCatching null\n"
            "            val resolverType = context.contentResolver.getType(uri)?.trim()\n"
            "            normalizeMimeType(resolverType)\n"
            "                ?: com.nuvio.app.features.downloads.LocalFolderVideosPlatform\n"
            "                    .resolveDisplayName(context, uri)\n"
            "                    .let(::inferMimeTypeFromPath)\n"
            "                ?: resolverType?.takeIf {\n"
            "                    it.startsWith(\"video/\", ignoreCase = true) && !it.endsWith(\"/*\")\n"
            "                }\n"
            "        } else {\n"
            "            null\n"
            "        }\n"
            "    }.getOrNull()\n"
            "}\n",
            "PlaybackMediaItems sniffLocalMimeType contentResolver + displayName fallback",
        )
        if changed:
            patched.append(str(media_items.relative_to(root)))

    return patched
