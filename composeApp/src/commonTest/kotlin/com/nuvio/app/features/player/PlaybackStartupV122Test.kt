package com.nuvio.app.features.player

import kotlin.test.*

class PlaybackStartupV122Test {
    @Test fun defaultStartupDoesNotWaitForAnExtraTimeBuffer() {
        assertEquals(0, PlaybackStartupPolicy.startBufferMs)
    }

    @Test fun recoveryStillHasBufferProtection() {
        assertTrue(PlaybackStartupPolicy.networkRebufferMs > 0)
        assertTrue(PlaybackStartupPolicy.localRebufferMs > 0)
    }
}
