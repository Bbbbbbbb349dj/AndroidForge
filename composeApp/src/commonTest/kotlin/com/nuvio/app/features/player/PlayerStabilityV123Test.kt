package com.nuvio.app.features.player

import kotlin.test.*

class PlayerStabilityV123Test {
    @Test fun embeddedVlcIsSelectableAndEngineCycleReachesEveryEngine() {
        assertEquals(AndroidPlaybackEngine.Vlc, AndroidPlaybackEngine.entries.first { it.name == "Vlc" })
        assertEquals(AndroidPlaybackEngine.Vlc, AndroidPlaybackEngine.Libmpv.switchTarget)
        assertEquals(AndroidPlaybackEngine.ExoPlayer, AndroidPlaybackEngine.Vlc.switchTarget)
        assertEquals(AndroidPlaybackEngine.Libmpv, AndroidPlaybackEngine.ExoPlayer.switchTarget)
    }
    @Test fun vlcPreservesSupportedHttpOptions() {
        assertNull(vlcSourceFallbackReason(mapOf("user-agent" to "Nuvio", "REFERER" to "https://example.test"), emptyMap(), false, false))
    }
    @Test fun protectedAndSplitSourcesKeepWorkingThroughExo() {
        for (header in listOf("Authorization", "Cookie", "Origin", "X-Token")) {
            assertNotNull(vlcSourceFallbackReason(mapOf(header to "value"), emptyMap(), false, false))
        }
        assertNotNull(vlcSourceFallbackReason(emptyMap(), mapOf("Content-Type" to "video/mp4"), false, false))
        assertNotNull(vlcSourceFallbackReason(emptyMap(), emptyMap(), true, false))
        assertNotNull(vlcSourceFallbackReason(emptyMap(), emptyMap(), false, true))
    }
    @Test fun startupAndRecoveryRetainSafetyMargins() {
        assertEquals(1500, PlaybackStartupPolicy.startBufferMs)
        assertTrue(PlaybackStartupPolicy.networkRebufferMs >= PlaybackStartupPolicy.startBufferMs)
    }
}
