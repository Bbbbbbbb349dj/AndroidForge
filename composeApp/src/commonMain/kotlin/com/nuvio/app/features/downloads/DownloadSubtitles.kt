package com.nuvio.app.features.downloads

import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.player.PlayerSubtitleCueParser
import com.nuvio.app.features.player.loadAddonSubtitles
import com.nuvio.app.features.streams.StreamSubtitle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

internal object DownloadSubtitles {
    private val json = Json { ignoreUnknownKeys = true }

    suspend fun prepare(item: DownloadItem, localVideoUri: String): Unit = withContext(Dispatchers.Default) {
        val storage = DownloadSubtitleStorage(localVideoUri)
        val manifest = readManifest(storage)
        val saved = manifest.tracks.filter { storage.localFileUri(it.fileName) != null }.toMutableList()
        if (manifest.complete && saved.size == manifest.tracks.size) return@withContext
        var nextFileIndex = (saved.maxOfOrNull { it.fileName.substringBefore('.').toIntOrNull() ?: -1 } ?: -1) + 1
        val addonSubtitles = loadAddonSubtitles(item.subtitleRequests).map {
            StreamSubtitle(url = it.url, language = it.language, name = it.display)
        }
        val pending = (item.sourceSubtitles + addonSubtitles)
            .distinctBy { it.url }
            .filter { subtitle ->
                (subtitle.url.startsWith("https://", true) || subtitle.url.startsWith("http://", true)) &&
                    saved.none { it.sourceUrl == subtitle.url }
            }
        var failedCount = 0
        for (batch in pending.chunked(4)) {
            val fetched = coroutineScope {
                batch.map { subtitle ->
                    async {
                        val body = try {
                            withTimeoutOrNull(15_000L) {
                                httpGetTextWithHeaders(subtitle.url, subtitle.headers.orEmpty())
                            }?.takeIf { it.isNotBlank() && PlayerSubtitleCueParser.parse(it, subtitle.url).isNotEmpty() }
                        } catch (error: Exception) {
                            if (error is CancellationException) throw error
                            null
                        }
                        subtitle to body
                    }
                }.awaitAll()
            }
            for ((subtitle, body) in fetched) {
                currentCoroutineContext().ensureActive()
                if (body == null) {
                    failedCount++
                    continue
                }
                val extension = PlayerSubtitleCueParser.fileExtension(body, subtitle.url)
                val fileName = "${nextFileIndex++}.$extension"
                try {
                    storage.write(fileName, body)
                    saved += DownloadedSubtitle(subtitle.url, fileName, subtitle.language, subtitle.name)
                    storage.write("manifest.json", json.encodeToString(SubtitleManifest(tracks = saved.toList())))
                } catch (error: Exception) {
                    if (error is CancellationException) throw error
                }
            }
        }
        currentCoroutineContext().ensureActive()
        // Nuvio Enhanced: only seal the manifest when nothing failed, so later runs
        // retry tracks that could not be fetched (e.g. a transient English-track failure).
        val allFetched = failedCount == 0
        runCatching {
            storage.write(
                "manifest.json",
                json.encodeToString(
                    SubtitleManifest(
                        complete = allFetched,
                        contentKey = item.videoId?.takeIf { it.isNotBlank() } ?: item.fileName,
                        tracks = saved,
                    ),
                ),
            )
        }
        Unit
    }

    private val selectedTrackMutex = kotlinx.coroutines.sync.Mutex()

    /** Save the user-selected track once; later playback reads it with no network. */
    suspend fun cacheSelected(localVideoUri: String, subtitle: com.nuvio.app.features.player.AddonSubtitle): String =
        withContext(Dispatchers.IO) {
            selectedTrackMutex.lock()
            try {
                val storage = DownloadSubtitleStorage(localVideoUri)
                val manifest = readManifest(storage)
                val existing = manifest.tracks.firstOrNull { it.sourceUrl == subtitle.url }
                existing?.let { track -> storage.localFileUri(track.fileName)?.let { return@withContext it } }
                val body = kotlinx.coroutines.withTimeout(15_000L) { httpGetTextWithHeaders(subtitle.url, emptyMap()) }
                require(PlayerSubtitleCueParser.parse(body, subtitle.url).isNotEmpty()) { "Invalid subtitle response" }
                val extension = PlayerSubtitleCueParser.fileExtension(body, subtitle.url)
                val index = (manifest.tracks.maxOfOrNull { it.fileName.substringBefore('.').toIntOrNull() ?: -1 } ?: -1) + 1
                val fileName = "$index.$extension"
                storage.write(fileName, body)
                val saved = DownloadedSubtitle(subtitle.url, fileName, subtitle.language, subtitle.label ?: subtitle.display)
                storage.write("manifest.json", json.encodeToString(manifest.copy(
                    tracks = manifest.tracks.filterNot { it.sourceUrl == subtitle.url } + saved,
                )))
                requireNotNull(storage.localFileUri(fileName)) { "Subtitle could not be saved" }
            } finally {
                selectedTrackMutex.unlock()
            }
        }

    fun localSubtitles(localVideoUri: String): List<StreamSubtitle> {
        // Nuvio Enhanced: content:// SAF URIs are supported by DownloadSubtitleStorage too.
        if (!localVideoUri.startsWith("file:") && !localVideoUri.startsWith("content:")) return emptyList()
        val storage = DownloadSubtitleStorage(localVideoUri)
        return readManifest(storage).tracks.mapNotNull { track ->
            val uri = storage.localFileUri(track.fileName) ?: return@mapNotNull null
            StreamSubtitle(url = uri, language = track.language, name = track.name)
        }
    }

    private fun readManifest(storage: DownloadSubtitleStorage): SubtitleManifest =
        runCatching {
            storage.read("manifest.json")?.let { json.decodeFromString<SubtitleManifest>(it) }
        }.getOrNull() ?: SubtitleManifest()
}

@Serializable
private data class SubtitleManifest(
    val complete: Boolean = false,
    /** Logical content identity (videoId, falling back to the download file name). */
    val contentKey: String? = null,
    val tracks: List<DownloadedSubtitle> = emptyList(),
)

@Serializable
private data class DownloadedSubtitle(
    val sourceUrl: String,
    val fileName: String,
    val language: String,
    val name: String? = null,
)

internal expect class DownloadSubtitleStorage(localVideoUri: String) {
    fun read(fileName: String): String?
    fun write(fileName: String, text: String)
    fun localFileUri(fileName: String): String?
    fun remove()
}
