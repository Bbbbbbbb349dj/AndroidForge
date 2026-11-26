package com.nuvio.app.features.player

import kotlin.test.*

class SubtitleTrackKindV121Test {
    private fun addon(label: String = "English", forced: Boolean = false, sdh: Boolean = false, url: String = "https://example.test/sub.vtt") =
        SubtitleSelectionOption.Addon(AddonSubtitle("en", url, "en", "English", label = label, isForced = forced, isSdh = sdh))

    @Test fun filtersUseProviderFlagsAndReleaseLabels() {
        assertTrue(addon(forced = true).matchesKind(SubtitleTrackKind.Forced))
        assertTrue(addon("English [forced]").matchesKind(SubtitleTrackKind.Forced))
        assertFalse(addon("Unforced dialogue").matchesKind(SubtitleTrackKind.Forced))
        assertTrue(addon(sdh = true).matchesKind(SubtitleTrackKind.Sdh))
        assertTrue(addon("English (SDH)").matchesKind(SubtitleTrackKind.Sdh))
        assertTrue(addon("English.CC").matchesKind(SubtitleTrackKind.Sdh))
        assertFalse(addon("Access").matchesKind(SubtitleTrackKind.Sdh))
    }

    @Test fun srtIgnoresSignedUrlQueryAndEmbeddedForcedFlagsArePreserved() {
        assertTrue(addon(url = "https://example.test/sub.SRT?token=123").matchesKind(SubtitleTrackKind.Srt))
        assertFalse(addon().matchesKind(SubtitleTrackKind.Srt))
        assertTrue(SubtitleSelectionOption.BuiltIn(SubtitleTrack(0, "0", "English", isForced = true)).matchesKind(SubtitleTrackKind.Forced))
        assertTrue(addon().matchesKind(SubtitleTrackKind.All))
    }
}
