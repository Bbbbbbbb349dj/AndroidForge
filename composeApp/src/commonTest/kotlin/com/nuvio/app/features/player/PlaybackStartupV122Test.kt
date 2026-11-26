package com.nuvio.app.features.player

import kotlin.test.*

class PlaybackStartupV122Test {
    @Test fun defaultStartupUsesABoundedNonzeroSafetyBuffer() {
        assertTrue(PlaybackStartupPolicy.startBufferMs in 500..2_000)
    }

    @Test fun recoveryStillHasBufferProtection() {
        assertTrue(PlaybackStartupPolicy.networkRebufferMs > 0)
        assertTrue(PlaybackStartupPolicy.localRebufferMs > 0)
    }
}
