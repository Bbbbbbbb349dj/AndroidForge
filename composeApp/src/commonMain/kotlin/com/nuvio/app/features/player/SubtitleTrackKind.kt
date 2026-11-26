package com.nuvio.app.features.player

import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.StringResource

internal enum class SubtitleTrackKind(val labelResource: StringResource) {
    All(Res.string.v121_subtitles_all),
    Sdh(Res.string.v121_subtitles_sdh),
    Forced(Res.string.v121_subtitles_forced),
    Srt(Res.string.v121_subtitles_srt),
}

private val sdhLabel = Regex("(?i)(?:^|[^a-z0-9])(?:sdh|cc|hearing[ ._-]?impaired)(?:$|[^a-z0-9])")
private val forcedLabel = Regex("(?i)(?:^|[^a-z0-9])forced(?:$|[^a-z0-9])")

internal fun SubtitleSelectionOption.matchesKind(kind: SubtitleTrackKind): Boolean {
    if (kind == SubtitleTrackKind.All) return true
    return when (this) {
        is SubtitleSelectionOption.BuiltIn -> when (kind) {
            SubtitleTrackKind.Forced -> track.isForced || forcedLabel.containsMatchIn(track.label)
            SubtitleTrackKind.Sdh -> sdhLabel.containsMatchIn(track.label)
            // An embedded track has no meaningful remote file extension.
            SubtitleTrackKind.Srt -> track.label.contains("srt", ignoreCase = true) || track.label.contains("subrip", ignoreCase = true)
            else -> true
        }
        is SubtitleSelectionOption.Addon -> {
            val label = listOfNotNull(subtitle.label, subtitle.display, subtitle.id).joinToString(" ")
            when (kind) {
                SubtitleTrackKind.Forced -> subtitle.isForced || forcedLabel.containsMatchIn(label)
                SubtitleTrackKind.Sdh -> subtitle.isSdh || sdhLabel.containsMatchIn(label)
                SubtitleTrackKind.Srt -> subtitle.format.equals("srt", true) ||
                    subtitle.url.substringBefore('?').substringBefore('#').endsWith(".srt", true) ||
                    label.contains("srt", true)
                else -> true
            }
        }
    }
}
