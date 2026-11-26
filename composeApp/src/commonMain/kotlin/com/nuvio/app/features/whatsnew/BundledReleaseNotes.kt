package com.nuvio.app.features.whatsnew

/** Shipped with the APK: About → What's New also works before publication and offline. */
internal object BundledReleaseNotes {
    val v121 = WhatsNewRelease(
        version = "1.21",
        title = "Nuvio Enhanced 1.21 — Search, playback & your watching space",
        publishedAt = null,
        releaseUrl = "https://github.com/Bbbbbbbb349dj/AndroidForge/releases/tag/nuvio-enhanced-v1.21-apk",
        notes = listOf(
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Removed the eye overlay from poster artwork without changing watched history or Library categories.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Removed the Movie/Series chip and its spacing from text search. Results no longer inherit Discover's last selected content type.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Search includes every installed, enabled add-on catalog declaring search support, including legacy extraSupported manifests. CloudStream remains separately opt-in.", null),
            WhatsNewNote(WhatsNewNoteCategory.FEATURES, "Added a More like this player action so movie recommendations can be opened at any time, not only near the credits. Existing end-of-movie recommendations remain.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Movie recommendations fall back to TMDB when the configured tracking provider has no results. Empty results are explained rather than hidden.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "The player Back button now minimizes when Mini Player is enabled. The minimize action no longer depends on a second hidden PiP preference, and disabling Mini Player dismisses its hosted video.", null),
            WhatsNewNote(WhatsNewNoteCategory.FEATURES, "Added a visible Night Mode audio-compression control for both player layouts, with Android 9+ ExoPlayer dynamic-range compression and the existing MPV compressor. Unsupported devices are indicated.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Restored Glass Backgrounds on Controls to the main Playback settings page. Turning it off also stops unnecessary video-frame capture.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Removed the Buy Me a Coffee card and its unused implementation from Settings.", null),
            WhatsNewNote(WhatsNewNoteCategory.PERFORMANCE, "HLS playback starts immediately instead of waiting for quality inspection. Background inspection is time-bounded and no longer restarts an already playing master playlist.", null),
            WhatsNewNote(WhatsNewNoteCategory.PERFORMANCE, "Reduced default startup buffering while retaining explicit custom buffer values and separate rebuffer protection. Provider throughput still determines sustained playback speed.", null),
            WhatsNewNote(WhatsNewNoteCategory.PERFORMANCE, "HLS downloads fetch up to four segments concurrently, write and decrypt them in playlist order, validate byte ranges, cancel in-flight requests, and checkpoint completed batches. Segment memory is bounded.", null),
            WhatsNewNote(WhatsNewNoteCategory.FEATURES, "Subtitles now have an always-accessible Fetch / refresh action plus All, SDH/CC, Forced and SRT filters. Provider flags and release labels are retained.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Downloaded videos can request additional subtitles even when local subtitles already exist. A selected online result is saved once beside the download for later offline playback.", null),
            WhatsNewNote(WhatsNewNoteCategory.FEATURES, "Redesigned the personal profile as a responsive watching dashboard with live collection counts, seven-day activity, watch time, taste analysis, edit/switch actions and useful empty states. No invented profile statistics.", null),
            WhatsNewNote(WhatsNewNoteCategory.FIXES, "Update and release history now use this fork rather than the unavailable upstream. These release notes are bundled for offline access.", null),
            WhatsNewNote(WhatsNewNoteCategory.OTHER, "Retained v1.20 Downloads navigation, Unlimited concurrency, rating-map positioning, CloudStream integration, local media and Library category persistence.", null),
            WhatsNewNote(WhatsNewNoteCategory.OTHER, "Provider-dependent limits: SDH/forced subtitles cannot be created when providers do not supply them. Subtitle fetch needs installed subtitle add-ons and internet access; truly unidentified local files need recognizable title metadata.", null),
        ),
    )

    fun merge(content: WhatsNewContent?, currentVersion: String): WhatsNewContent {
        val releases = listOf(v121) + content?.snapshot?.releases.orEmpty()
        return WhatsNewContent(
            snapshot = WhatsNewSnapshotBuilder.build(releases, currentVersion),
            fromCache = content?.fromCache ?: true,
            isStale = content?.isStale ?: false,
            fetchedAtMillis = content?.fetchedAtMillis ?: 0L,
        )
    }
}
