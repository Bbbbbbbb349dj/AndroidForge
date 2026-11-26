package com.nuvio.app.features.downloads

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
            .header("User-Agent", "NuvioEnhanced/1.21")
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
