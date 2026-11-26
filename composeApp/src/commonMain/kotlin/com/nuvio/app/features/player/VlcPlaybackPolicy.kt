package com.nuvio.app.features.player

/** LibVLC 3.x exposes UA/referrer options, not ExoPlayer's arbitrary request/response overrides. */
internal fun vlcSourceFallbackReason(
    headers: Map<String, String>,
    responseHeaders: Map<String, String>,
    separateAudio: Boolean,
    youtubeChunked: Boolean,
): String? = when {
    separateAudio || youtubeChunked -> "This source needs split/chunked playback. Using ExoPlayer for this source."
    responseHeaders.isNotEmpty() -> "This source needs response-header overrides. Using ExoPlayer for this source."
    headers.keys.any { !it.equals("User-Agent", true) && !it.equals("Referer", true) && !it.equals("Referrer", true) } ->
        "This source needs protected request headers. Using ExoPlayer to preserve them."
    else -> null
}
