package com.nuvio.app.features.downloads

import java.io.IOException
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

private const val MAX_SEGMENT_BYTES = 32L * 1024L * 1024L

/** Each parallel call is independently cancelled when its coroutine is cancelled. */
internal suspend fun fetchHlsSegment(
    client: OkHttpClient,
    request: Request,
    byteRange: Pair<Long, Long>?,
): ByteArray = suspendCancellableCoroutine { continuation ->
    val call = client.newCall(request)
    continuation.invokeOnCancellation { call.cancel() }
    call.enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            if (continuation.isActive) continuation.resumeWithException(e)
        }

        override fun onResponse(call: Call, response: Response) {
            val result = runCatching {
                response.use {
                    if (!it.isSuccessful) throw DownloadHttpException(it.code)
                    if (byteRange != null) {
                        val expected = "bytes ${byteRange.first}-${byteRange.second}/"
                        if (it.code != 206 || it.header("Content-Range")?.startsWith(expected) != true) {
                            throw IOException("HLS server ignored the requested byte range")
                        }
                    }
                    val body = it.body ?: throw IOException("Empty HLS segment")
                    if (body.contentLength() > MAX_SEGMENT_BYTES) throw IOException("HLS segment exceeds the safe memory limit")
                    val source = body.source()
                    // Bounded read also covers chunked responses with unknown Content-Length.
                    source.request(MAX_SEGMENT_BYTES + 1)
                    if (source.buffer.size > MAX_SEGMENT_BYTES) throw IOException("HLS segment exceeds the safe memory limit")
                    source.readByteArray().also { bytes ->
                        if (byteRange != null && bytes.size.toLong() != byteRange.second - byteRange.first + 1) {
                            throw IOException("Incomplete HLS byte range")
                        }
                    }
                }
            }
            if (continuation.isActive) {
                result.fold(
                    onSuccess = { continuation.resume(it) },
                    onFailure = { continuation.resumeWithException(it) },
                )
            }
        }
    })
}
