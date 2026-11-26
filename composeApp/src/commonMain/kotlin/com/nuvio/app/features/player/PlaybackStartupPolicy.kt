package com.nuvio.app.features.player

/** Start at the first decodable sample, without waiting to accumulate extra playback time. */
internal object PlaybackStartupPolicy {
    const val startBufferMs = 0
    // Initial startup and recovery are separate: don't repeatedly resume into an empty buffer.
    const val networkRebufferMs = 2_500
    const val localRebufferMs = 250
}
