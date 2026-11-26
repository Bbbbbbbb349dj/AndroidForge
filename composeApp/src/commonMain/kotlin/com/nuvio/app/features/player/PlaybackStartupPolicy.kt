package com.nuvio.app.features.player

/** Bounded startup buffering: avoid repeatedly entering playback with an empty queue. */
internal object PlaybackStartupPolicy {
    const val startBufferMs = 1_500
    // Initial startup and recovery are separate: don't repeatedly resume into an empty buffer.
    const val networkRebufferMs = 2_500
    const val localRebufferMs = 250
}
