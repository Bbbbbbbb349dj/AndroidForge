package com.nuvio.app.features.downloads

import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.nio.ByteBuffer
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import okhttp3.Call
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

internal val downloadHttpClient = OkHttpClient.Builder()
    .dns(com.nuvio.app.core.network.NuvioDns)
    .connectTimeout(60, TimeUnit.SECONDS)
    .readTimeout(60, TimeUnit.SECONDS)
    .writeTimeout(60, TimeUnit.SECONDS)
    .followRedirects(true)
    .followSslRedirects(true)
    .dispatcher(okhttp3.Dispatcher().apply {
        maxRequests = 64
        maxRequestsPerHost = 32
    })
    .build()

internal class DownloadHttpException(val statusCode: Int) : IOException("Download failed: HTTP $statusCode")

internal suspend fun transferAndroidDownload(
    item: DownloadItem,
    sink: DownloadSink,
    validator: String?,
    client: OkHttpClient = downloadHttpClient,
    onHeaders: (totalBytes: Long?, validator: String?) -> Unit,
    onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,
): Unit = coroutineScope {
    val activeCall = AtomicReference<Call?>()
    val transfer = async(Dispatchers.IO) {
        try {
            require(File(item.fileName).name == item.fileName && item.fileName.isNotBlank())
            if (looksLikeHlsUrl(item.sourceUrl)) {
                transferHlsPlaylistDownload(item, sink, client, activeCall, onHeaders, onProgress)
                return@async
            }

            var offset = sink.length()
            var restarted = false

            while (true) {
                ensureActive()
                val request = buildDownloadRequest(item.sourceUrl, item.sourceHeaders, offset, validator)
                val call = client.newCall(request)
                activeCall.set(call)
                ensureActive()
                var switchToHlsText: Pair<String, String>? = null
                call.execute().use { response ->
                    if (response.code == 416 && offset > 0L && !restarted) {
                        offset = 0L
                        restarted = true
                        return@use
                    }
                    if (!response.isSuccessful) throw DownloadHttpException(response.code)
                    val contentType = response.header("Content-Type").orEmpty().lowercase()
                    val body = response.body ?: throw IOException("Download response is empty")

                    if (offset == 0L && (contentType.contains("mpegurl") || contentType.contains("m3u"))) {
                        val playlistText = body.string()
                        if (playlistText.trimStart().startsWith("#EXTM3U")) {
                            switchToHlsText = response.request.url.toString() to playlistText
                            return@use
                        }
                    }

                    val range = response.header("Content-Range")?.let(::parseDownloadContentRange)
                    val resumed = response.code == 206
                    if (resumed && (range == null || range.first != offset)) {
                        throw IOException("Server returned an invalid download range")
                    }
                    val startingBytes = if (resumed) offset else 0L
                    val contentLength = body.contentLength().takeIf { it >= 0L }
                    val totalBytes = range?.second ?: contentLength?.let { startingBytes + it }
                    val responseValidator = response.header("ETag")?.takeUnless { it.startsWith("W/") }
                        ?: response.header("Last-Modified")

                    body.byteStream().use { input ->
                        // Sniff disguised HLS playlists served as text/plain or application/octet-stream
                        val headBuffer = ByteArray(16)
                        var headLen = 0
                        if (startingBytes == 0L) {
                            while (headLen < headBuffer.size) {
                                val r = input.read(headBuffer, headLen, headBuffer.size - headLen)
                                if (r <= 0) break
                                headLen += r
                            }
                            val prefix = String(headBuffer, 0, headLen, Charsets.UTF_8).trimStart()
                            if (prefix.startsWith("#EXTM3U")) {
                                val out = ByteArrayOutputStream()
                                out.write(headBuffer, 0, headLen)
                                val buf = ByteArray(16 * 1024)
                                while (true) {
                                    ensureActive()
                                    val r = input.read(buf)
                                    if (r == -1) break
                                    out.write(buf, 0, r)
                                }
                                switchToHlsText = response.request.url.toString() to out.toString("UTF-8")
                                return@use
                            }
                        }

                        onHeaders(totalBytes, responseValidator)
                        var downloaded = startingBytes
                        onProgress(downloaded, totalBytes)
                        sink.open(append = resumed && offset > 0L).use { output ->
                            if (headLen > 0) {
                                output.write(headBuffer, 0, headLen)
                                downloaded += headLen
                                onProgress(downloaded, totalBytes)
                            }
                            val buffer = ByteArray(64 * 1024)
                            while (true) {
                                ensureActive()
                                val size = input.read(buffer)
                                if (size == -1) break
                                output.write(buffer, 0, size)
                                downloaded += size
                                onProgress(downloaded, totalBytes)
                            }
                            output.fd.sync()
                        }
                        ensureActive()
                        if (totalBytes != null && downloaded != totalBytes) {
                            throw IOException("Download ended before all bytes were received")
                        }
                    }
                    return@async
                }

                val hlsDetected = switchToHlsText
                if (hlsDetected != null) {
                    transferHlsPlaylistDownload(
                        item = item,
                        sink = sink,
                        client = client,
                        activeCall = activeCall,
                        onHeaders = onHeaders,
                        onProgress = onProgress,
                        initialPlaylistUrl = hlsDetected.first,
                        initialPlaylistBody = hlsDetected.second,
                    )
                    return@async
                }
            }
        } catch (error: Exception) {
            ensureActive()
            throw error
        }
    }
    try {
        transfer.await()
    } finally {
        activeCall.get()?.cancel()
    }
}

private fun looksLikeHlsUrl(url: String): Boolean {
    val lower = url.trim().lowercase()
    val path = lower.substringBefore('?').substringBefore('#')
    return path.endsWith(".m3u8") || ".m3u8/" in path || lower.contains(".m3u8?")
}

private fun buildDownloadRequest(
    url: String,
    headers: Map<String, String>,
    offset: Long = 0L,
    validator: String? = null,
    byteRange: Pair<Long, Long>? = null,
): Request = Request.Builder().url(url).apply {
    headers.forEach { (key, value) ->
        if (!key.equals("Range", true) && !key.equals("If-Range", true) &&
            !key.equals("Accept-Encoding", true)
        ) {
            header(key, value)
        }
    }
    header("Accept-Encoding", "identity")
    if (byteRange != null) {
        header("Range", "bytes=${byteRange.first}-${byteRange.second}")
    } else if (offset > 0L) {
        header("Range", "bytes=$offset-")
        validator?.let { header("If-Range", it) }
    }
}.build()

private data class HlsKeySpec(
    val method: String,
    val uri: String?,
    val iv: ByteArray?,
)

private data class HlsSegmentSpec(
    val url: String,
    val sequence: Long,
    val key: HlsKeySpec?,
    val byteRange: Pair<Long, Long>?,
)

private suspend fun transferHlsPlaylistDownload(
    item: DownloadItem,
    sink: DownloadSink,
    client: OkHttpClient,
    activeCall: AtomicReference<Call?>,
    onHeaders: (totalBytes: Long?, validator: String?) -> Unit,
    onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,
    initialPlaylistUrl: String? = null,
    initialPlaylistBody: String? = null,
) {
    suspend fun fetchText(url: String): Pair<String, String> {
        val call = client.newCall(buildDownloadRequest(url, item.sourceHeaders))
        activeCall.set(call)
        call.execute().use { response ->
            if (!response.isSuccessful) throw DownloadHttpException(response.code)
            val body = response.body?.string() ?: throw IOException("Empty HLS playlist")
            return response.request.url.toString() to body
        }
    }

    suspend fun fetchBytesWithRetry(url: String, byteRange: Pair<Long, Long>? = null): ByteArray {
        var attempt = 0
        while (true) {
            kotlinx.coroutines.currentCoroutineContext().ensureActive()
            try {
                return fetchHlsSegment(client, buildDownloadRequest(url, item.sourceHeaders, byteRange = byteRange), byteRange)
            } catch (err: Exception) {
                kotlinx.coroutines.currentCoroutineContext().ensureActive()
                attempt++
                if (attempt >= 3) throw err
                delay(600L * attempt)
            }
        }
    }

    var (playlistUrl, playlistText) = if (initialPlaylistUrl != null && initialPlaylistBody != null) {
        initialPlaylistUrl to initialPlaylistBody
    } else {
        fetchText(item.sourceUrl)
    }

    // Resolve master playlist (#EXT-X-STREAM-INF) to best variant media playlist
    if (playlistText.contains("#EXT-X-STREAM-INF")) {
        val variantUrl = selectBestHlsVariant(playlistUrl, playlistText)
            ?: throw IOException("No playable variant found in HLS master playlist")
        val resolved = fetchText(variantUrl)
        playlistUrl = resolved.first
        playlistText = resolved.second
    }

    val (initSegment, segments) = parseHlsMediaPlaylist(playlistUrl, playlistText)
    if (segments.isEmpty()) {
        throw IOException("HLS media playlist contained no segments")
    }

    val keyCache = HashMap<String, ByteArray>()
    suspend fun decryptIfNeeded(raw: ByteArray, segment: HlsSegmentSpec): ByteArray {
        val keySpec = segment.key ?: return raw
        if (keySpec.method.equals("NONE", ignoreCase = true) || keySpec.uri.isNullOrBlank()) {
            return raw
        }
        if (!keySpec.method.equals("AES-128", ignoreCase = true)) {
            throw IOException("Unsupported HLS encryption: ${keySpec.method}")
        }
        val keyBytes = keyCache.getOrPut(keySpec.uri) {
            fetchBytesWithRetry(keySpec.uri)
        }
        val ivBytes = keySpec.iv ?: ByteBuffer.allocate(16).putLong(8, segment.sequence).array()
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(keyBytes, "AES"), IvParameterSpec(ivBytes))
        return cipher.doFinal(raw)
    }

    // Nuvio Enhanced: segment checkpoint so an interrupted HLS transfer resumes
    // instead of restarting from byte zero.
    val checkpointFile = DownloadsLiveStatusPlatform.checkpointFile("${item.fileName}.hls")
    var checkpointBytes = 0L
    var startSegmentIndex = 0
    val savedCheckpoint = checkpointFile?.takeIf { it.isFile }?.readText()?.split('\n')
    if (savedCheckpoint != null && savedCheckpoint.size == 3 && savedCheckpoint[0] == playlistUrl) {
        startSegmentIndex = savedCheckpoint[1].toIntOrNull()?.coerceIn(0, segments.size) ?: 0
        checkpointBytes = savedCheckpoint[2].toLongOrNull() ?: 0L
    }
    val canResume = checkpointBytes > 0 && startSegmentIndex > 0 && sink.length() == checkpointBytes
    if (!canResume) {
        checkpointBytes = 0L
        startSegmentIndex = 0
        checkpointFile?.delete()
    }

    onHeaders(null, null)
    var downloadedBytes = checkpointBytes
    onProgress(downloadedBytes, null)

    sink.open(append = canResume).use { output ->
        if (initSegment != null && !canResume) {
            val initRaw = fetchBytesWithRetry(initSegment.url, initSegment.byteRange)
            val initPlain = decryptIfNeeded(initRaw, initSegment)
            output.write(initPlain)
            downloadedBytes += initPlain.size
            onProgress(downloadedBytes, null)
        }

        val totalCount = segments.size
        // Four in-flight segments hide per-request latency, without unbounded memory or
        // out-of-order writes. Decryption and durable checkpoints stay on the writer.
        segments.withIndex().drop(startSegmentIndex).chunked(4).forEach { batch ->
            val fetched = coroutineScope {
                batch.map { indexed ->
                    async(Dispatchers.IO) {
                        indexed to fetchBytesWithRetry(indexed.value.url, indexed.value.byteRange)
                    }
                }.map { it.await() }
            }
            for ((indexed, rawBytes) in fetched) {
                kotlinx.coroutines.currentCoroutineContext().ensureActive()
                val clearBytes = decryptIfNeeded(rawBytes, indexed.value)
                output.write(clearBytes)
                downloadedBytes += clearBytes.size
                val completed = indexed.index + 1
                val estimatedTotal = if (completed >= totalCount) downloadedBytes else {
                    ((downloadedBytes.toDouble() * totalCount) / completed).toLong()
                        .coerceAtLeast(downloadedBytes + 1L)
                }
                onHeaders(estimatedTotal, null)
                onProgress(downloadedBytes, estimatedTotal)
            }
            output.fd.sync()
            val completed = batch.last().index + 1
            runCatching { checkpointFile?.writeText("$playlistUrl\n$completed\n$downloadedBytes") }
        }
        output.fd.sync()
    }
    checkpointFile?.delete()
    onHeaders(downloadedBytes, null)
    onProgress(downloadedBytes, downloadedBytes)
}

private fun resolveRelativeHlsUrl(baseUrl: String, ref: String): String {
    val trimmed = ref.trim()
    if (trimmed.startsWith("http://", true) || trimmed.startsWith("https://", true)) return trimmed
    return baseUrl.toHttpUrlOrNull()?.resolve(trimmed)?.toString()
        ?: runCatching { java.net.URI(baseUrl).resolve(trimmed).toString() }.getOrDefault(trimmed)
}

private fun selectBestHlsVariant(baseUrl: String, masterText: String): String? {
    data class Variant(val url: String, val height: Int, val bandwidth: Long)
    val lines = masterText.lines().map(String::trim)
    val variants = mutableListOf<Variant>()
    var pendingInfo: String? = null
    for (line in lines) {
        if (line.isEmpty()) continue
        if (line.startsWith("#EXT-X-STREAM-INF:", ignoreCase = true)) {
            pendingInfo = line.substringAfter(':')
        } else if (!line.startsWith("#") && pendingInfo != null) {
            val attrs = pendingInfo
            pendingInfo = null
            val height = Regex("RESOLUTION=\\d+x(\\d+)", RegexOption.IGNORE_CASE)
                .find(attrs)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: 0
            val bw = Regex("BANDWIDTH=(\\d+)", RegexOption.IGNORE_CASE)
                .find(attrs)?.groupValues?.getOrNull(1)?.toLongOrNull() ?: 0L
            variants += Variant(resolveRelativeHlsUrl(baseUrl, line), height, bw)
        }
    }
    val preferredMax = DownloadsSettingsRepository.preferredResolution.value.resolution
    val underCap = variants.filter { it.height in 1..preferredMax }
    val chosen = underCap.maxWithOrNull(compareBy<Variant> { it.height }.thenBy { it.bandwidth })
        ?: variants.maxWithOrNull(compareBy<Variant> { it.height }.thenBy { it.bandwidth })
    return chosen?.url
}

private fun parseHlsMediaPlaylist(
    baseUrl: String,
    mediaText: String,
): Pair<HlsSegmentSpec?, List<HlsSegmentSpec>> {
    var mediaSequence = 0L
    var currentKey: HlsKeySpec? = null
    var initSegment: HlsSegmentSpec? = null
    var pendingByteRange: Pair<Long, Long>? = null
    var lastRangeEnd = 0L
    val segments = mutableListOf<HlsSegmentSpec>()

    fun parseAttr(line: String, name: String): String? {
        val quoted = Regex("$name=\"([^\"]*)\"", RegexOption.IGNORE_CASE).find(line)?.groupValues?.getOrNull(1)
        if (quoted != null) return quoted
        return Regex("$name=([^,\\s]+)", RegexOption.IGNORE_CASE).find(line)?.groupValues?.getOrNull(1)
    }

    fun parseByteRangeSpec(spec: String?): Pair<Long, Long>? {
        if (spec.isNullOrBlank()) return null
        val len = spec.substringBefore('@').toLongOrNull() ?: return null
        val start = if ('@' in spec) {
            spec.substringAfter('@').toLongOrNull() ?: lastRangeEnd
        } else {
            lastRangeEnd
        }
        val end = start + len - 1L
        lastRangeEnd = end + 1L
        return start to end
    }

    for (rawLine in mediaText.lines()) {
        val line = rawLine.trim()
        if (line.isEmpty()) continue
        when {
            line.startsWith("#EXT-X-MEDIA-SEQUENCE:", true) -> {
                mediaSequence = line.substringAfter(':').trim().toLongOrNull() ?: 0L
            }
            line.startsWith("#EXT-X-KEY:", true) -> {
                val method = parseAttr(line, "METHOD") ?: "NONE"
                val uri = parseAttr(line, "URI")?.let { resolveRelativeHlsUrl(baseUrl, it) }
                val ivHex = parseAttr(line, "IV")?.removePrefix("0x")?.removePrefix("0X")
                val iv = ivHex?.takeIf { it.length == 32 }?.chunked(2)
                    ?.mapNotNull { it.toIntOrNull(16)?.toByte() }
                    ?.takeIf { it.size == 16 }
                    ?.toByteArray()
                currentKey = HlsKeySpec(method = method, uri = uri, iv = iv)
            }
            line.startsWith("#EXT-X-MAP:", true) -> {
                val mapUri = parseAttr(line, "URI")?.let { resolveRelativeHlsUrl(baseUrl, it) }
                val mapRange = parseByteRangeSpec(parseAttr(line, "BYTERANGE"))
                if (mapUri != null) {
                    initSegment = HlsSegmentSpec(
                        url = mapUri,
                        sequence = mediaSequence,
                        key = currentKey,
                        byteRange = mapRange,
                    )
                }
            }
            line.startsWith("#EXT-X-BYTERANGE:", true) -> {
                pendingByteRange = parseByteRangeSpec(line.substringAfter(':').trim())
            }
            !line.startsWith("#") -> {
                val segIndex = mediaSequence + segments.size
                segments += HlsSegmentSpec(
                    url = resolveRelativeHlsUrl(baseUrl, line),
                    sequence = segIndex,
                    key = currentKey,
                    byteRange = pendingByteRange,
                )
                pendingByteRange = null
            }
        }
    }
    return initSegment to segments
}

internal fun parseDownloadContentRange(value: String): Pair<Long, Long?>? {
    val match = Regex("bytes (\\d+)-(\\d+)/(\\d+|\\*)").matchEntire(value.trim()) ?: return null
    val start = match.groupValues[1].toLongOrNull() ?: return null
    val end = match.groupValues[2].toLongOrNull() ?: return null
    val total = match.groupValues[3].toLongOrNull()
    if (end < start || (total != null && end >= total)) return null
    return start to total
}
