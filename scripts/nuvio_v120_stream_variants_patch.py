#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 10: SUB/DUB/DUAL stream badges & batch downloads (Sec 7/8).

  - `StreamBadgePresentation.audioVariantOf()` detects SUB/DUB/DUAL from badges/name/filename.
  - Text-only `SUB`/`DUB`/`DUAL` pill rendered on `StreamCard` badge rows.
  - `BatchDownloadCoordinator` presents badge rules via `applyToStreams()` and its
    "episode downloaded" lookup matches variant-suffixed keys.
  - `DownloadItem.audioVariant` participates in `logicalContentKey` (and `buildLogicalKey`),
    so a DUAL/Both download never overwrites a SUB download (and vice versa).
  - `StreamOverrideDialog` gains SUB/DUB/Both filter chips and shows the variant in the
    stream summary line (badge • addon • size).
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return  # already applied
        raise RuntimeError(f"[v1.20 variants] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 variants] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _replace_exact_count(path: Path, old: str, new: str, expected: int, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) >= expected:
            return  # already applied
        raise RuntimeError(f"[v1.20 variants] Expected {expected} matches for {label}, found none in {path}")
    if count != expected:
        raise RuntimeError(f"[v1.20 variants] Expected {expected} matches for {label}, found {count} in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def _patch_presentation_helper(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamBadgePresentation.kt"
    _replace_once(
        path,
        """    // Each addon group is presented on its own with the same rules, so their regexes are""",
        """    /**
     * Detects the audio-variant label ("SUB", "DUB" or "DUAL") for a stream from its badge
     * names, title, description and filename. Nuvio Enhanced: drives the stream/batch variant
     * pills and keeps SUB/DUB downloads from overwriting each other.
     */
    fun audioVariantOf(stream: StreamItem): String? {
        val texts = buildList {
            stream.badges.forEach { badge -> add(badge.name) }
            stream.name?.let { add(it) }
            stream.description?.let { add(it) }
            stream.behaviorHints.filename?.let { add(it) }
        }.filter { it.isNotBlank() }
        fun mentions(word: String): Boolean = texts.any { text ->
            Regex("\\\\b$word\\\\b", RegexOption.IGNORE_CASE).containsMatchIn(text)
        }
        val hasSub = mentions("sub")
        val hasDub = mentions("dub")
        return when {
            mentions("dual") || (hasSub && hasDub) -> "DUAL"
            hasDub -> "DUB"
            hasSub -> "SUB"
            else -> null
        }
    }

    // Each addon group is presented on its own with the same rules, so their regexes are""",
        "audioVariantOf helper",
    )


def _patch_models(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsModels.kt"
    _replace_once(
        path,
        """    val sourceSubtitles: List<StreamSubtitle> = emptyList(),
    val localFileUri: String? = null,""",
        """    val sourceSubtitles: List<StreamSubtitle> = emptyList(),
    /** "SUB", "DUB" or "DUAL" when known — part of the logical content identity. */
    val audioVariant: String? = null,
    val localFileUri: String? = null,""",
        "audioVariant field",
    )
    _replace_once(
        path,
        """    val logicalContentKey: String
        get() = if (isEpisode) {
            "${parentMetaId.trim()}|${seasonNumber ?: -1}|${episodeNumber ?: -1}"
        } else {
            "${parentMetaId.trim()}|movie"
        }""",
        """    val logicalContentKey: String
        get() {
            val base = if (isEpisode) {
                "${parentMetaId.trim()}|${seasonNumber ?: -1}|${episodeNumber ?: -1}"
            } else {
                "${parentMetaId.trim()}|movie"
            }
            return audioVariant?.takeIf { it.isNotBlank() }?.let { "$base|$it" } ?: base
        }""",
        "logicalContentKey variant suffix",
    )


def _patch_repository(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsRepository.kt"
    _replace_once(
        path,
        """internal fun buildLogicalKey(
    parentMetaId: String,
    seasonNumber: Int?,
    episodeNumber: Int?,
): String = if (seasonNumber != null && episodeNumber != null) {
    "${parentMetaId.trim()}|$seasonNumber|$episodeNumber"
} else {
    "${parentMetaId.trim()}|movie"
}""",
        """internal fun buildLogicalKey(
    parentMetaId: String,
    seasonNumber: Int?,
    episodeNumber: Int?,
    audioVariant: String? = null,
): String {
    val base = if (seasonNumber != null && episodeNumber != null) {
        "${parentMetaId.trim()}|$seasonNumber|$episodeNumber"
    } else {
        "${parentMetaId.trim()}|movie"
    }
    return audioVariant?.takeIf { it.isNotBlank() }?.let { "$base|$it" } ?: base
}""",
        "buildLogicalKey variant param",
    )
    _replace_once(
        path,
        """        val now = DownloadsClock.nowEpochMs()
        val logicalKey = buildLogicalKey(
            parentMetaId = parentMetaId,
            seasonNumber = seasonNumber,
            episodeNumber = episodeNumber,
        )""",
        """        val audioVariant = com.nuvio.app.features.streams.StreamBadgePresentation.audioVariantOf(stream)
        val now = DownloadsClock.nowEpochMs()
        val logicalKey = buildLogicalKey(
            parentMetaId = parentMetaId,
            seasonNumber = seasonNumber,
            episodeNumber = episodeNumber,
            audioVariant = audioVariant,
        )""",
        "enqueue variant key",
    )
    _replace_once(
        path,
        """            sourceSubtitles = stream.externalSubtitles,
            localFileUri = null,""",
        """            sourceSubtitles = stream.externalSubtitles,
            audioVariant = audioVariant,
            localFileUri = null,""",
        "queued item audioVariant",
    )


def _patch_coordinator(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/BatchDownloadCoordinator.kt"
    _replace_once(
        path,
        """import com.nuvio.app.features.streams.StreamItem""",
        """import com.nuvio.app.features.streams.StreamBadgePresentation
import com.nuvio.app.features.streams.StreamBadgeSettingsRepository
import com.nuvio.app.features.streams.StreamItem""",
        "coordinator imports",
    )
    _replace_once(
        path,
        """private fun List<DownloadItem>.downloadFor(logicalKey: String): DownloadItem? =
    firstOrNull { it.logicalContentKey == logicalKey && it.status != DownloadStatus.Failed }""",
        """private fun List<DownloadItem>.downloadFor(logicalKey: String): DownloadItem? =
    firstOrNull { item ->
        // Matches the base key plus any audio-variant suffix (SUB/DUB/DUAL).
        (item.logicalContentKey == logicalKey || item.logicalContentKey.startsWith("$logicalKey|")) &&
            item.status != DownloadStatus.Failed
    }""",
        "variant-aware downloadFor",
    )
    _replace_once(
        path,
        """        val currentPlan = _activePlan.value
        val activeFilter = currentPlan?.sourceFilter ?: BatchSourceFilter.All
        val activeQuery = currentPlan?.searchQuery.orEmpty()
        val filteredStreams = streams.filter {
            it.matchesBatchSourceFilter(activeFilter) && it.matchesBatchSearchQuery(activeQuery)
        }""",
        """        val presentedStreams = StreamBadgePresentation.applyToStreams(
            streams,
            StreamBadgeSettingsRepository.snapshot(),
        )
        val currentPlan = _activePlan.value
        val activeFilter = currentPlan?.sourceFilter ?: BatchSourceFilter.All
        val activeQuery = currentPlan?.searchQuery.orEmpty()
        val filteredStreams = presentedStreams.filter {
            it.matchesBatchSourceFilter(activeFilter) && it.matchesBatchSearchQuery(activeQuery)
        }""",
        "applyToStreams in batch",
    )
    _replace_exact_count(
        path,
        """                            allAvailableStreams = streams,""",
        """                            allAvailableStreams = presentedStreams,""",
        1,
        "presented streams stored (deep)",
    )
    _replace_exact_count(
        path,
        """                        allAvailableStreams = streams,""",
        """                        allAvailableStreams = presentedStreams,""",
        3,
        "presented streams stored",
    )


def _patch_stream_card(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamCard.kt"
    _replace_once(
        path,
        """    val badgeImages = stream.badges.filter { it.imageURL.isNotBlank() }
    val hasBadges = badgeImages.isNotEmpty() || (showFileSizeBadges && stream.behaviorHints.videoSize != null)""",
        """    val badgeImages = stream.badges.filter { it.imageURL.isNotBlank() }
    val audioVariantLabel = remember(stream) { StreamBadgePresentation.audioVariantOf(stream) }
    val hasBadges = badgeImages.isNotEmpty() || audioVariantLabel != null ||
        (showFileSizeBadges && stream.behaviorHints.videoSize != null)""",
        "variant label state",
    )
    _replace_exact_count(
        path,
        """                StreamCardBadgeRow(
                    badgeImages = badgeImages,
                    stream = stream,
                    showFileSizeBadges = showFileSizeBadges,""",
        """                StreamCardBadgeRow(
                    badgeImages = badgeImages,
                    audioVariantLabel = audioVariantLabel,
                    stream = stream,
                    showFileSizeBadges = showFileSizeBadges,""",
        2,
        "badge row calls",
    )
    _replace_once(
        path,
        """private fun StreamCardBadgeRow(
    badgeImages: List<StreamBadge>,
    stream: StreamItem,
    showFileSizeBadges: Boolean,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        badgeImages.forEach { badge ->
            StreamBadgeImage(badge = badge)
        }""",
        """private fun StreamCardBadgeRow(
    badgeImages: List<StreamBadge>,
    audioVariantLabel: String?,
    stream: StreamItem,
    showFileSizeBadges: Boolean,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        if (audioVariantLabel != null) {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .background(Color.White.copy(alpha = 0.16f))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
            ) {
                Text(
                    text = audioVariantLabel,
                    color = Color.White,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
        badgeImages.forEach { badge ->
            StreamBadgeImage(badge = badge)
        }""",
        "variant text pill",
    )


def _patch_batch_dialog(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/BatchDownloadDialog.kt"
    _replace_once(
        path,
        """import com.nuvio.app.features.streams.StreamItem""",
        """import com.nuvio.app.features.streams.StreamBadgePresentation
import com.nuvio.app.features.streams.StreamItem""",
        "dialog import",
    )
    _replace_once(
        path,
        """    var filter by remember(initialFilter) { mutableStateOf(initialFilter) }
    var searchQuery by remember(initialQuery) { mutableStateOf(initialQuery) }""",
        """    var filter by remember(initialFilter) { mutableStateOf(initialFilter) }
    var searchQuery by remember(initialQuery) { mutableStateOf(initialQuery) }
    var audioVariantFilter by remember { mutableStateOf("Both") }""",
        "variant filter state",
    )
    _replace_once(
        path,
        """    val filteredStreams = remember(allStreams, filter, searchQuery) {
        allStreams.filter { stream ->
            stream.matchesBatchSourceFilter(filter) && stream.matchesBatchSearchQuery(searchQuery)
        }
    }""",
        """    val filteredStreams = remember(allStreams, filter, searchQuery, audioVariantFilter) {
        allStreams.filter { stream ->
            stream.matchesBatchSourceFilter(filter) && stream.matchesBatchSearchQuery(searchQuery)
        }.filter { stream ->
            when (audioVariantFilter) {
                "SUB" -> when (StreamBadgePresentation.audioVariantOf(stream)) {
                    "SUB", "DUAL" -> true
                    "DUB" -> false
                    else -> true
                }
                "DUB" -> when (StreamBadgePresentation.audioVariantOf(stream)) {
                    "DUB", "DUAL" -> true
                    "SUB" -> false
                    else -> true
                }
                else -> true
            }
        }
    }""",
        "variant filtering",
    )
    _replace_once(
        path,
        """        BatchSearchAndQualityBar(
            query = searchQuery,
            onQueryChange = { searchQuery = it },
            placeholder = "Search ${allStreams.size} streams (quality, scraper, language)...",
        )
""",
        """        BatchSearchAndQualityBar(
            query = searchQuery,
            onQueryChange = { searchQuery = it },
            placeholder = "Search ${allStreams.size} streams (quality, scraper, language)...",
        )

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            listOf("Both", "SUB", "DUB").forEach { mode ->
                FilterChip(
                    selected = audioVariantFilter == mode,
                    onClick = { audioVariantFilter = mode },
                    label = {
                        Text(
                            text = mode,
                            style = MaterialTheme.typography.labelMedium,
                            maxLines = 1,
                        )
                    },
                )
            }
        }
""",
        "variant chips row",
    )
    _replace_once(
        path,
        """                    val badge = facts.qualityBadge()
                    val size = StreamSourcePrefillSelector.sizeBytes(stream)?.let(::formatBytes)""",
        """                    val variantLabel = StreamBadgePresentation.audioVariantOf(stream)
                    val badge = listOfNotNull(facts.qualityBadge(), variantLabel)
                        .joinToString(" • ")
                        .takeIf { it.isNotEmpty() }
                    val size = StreamSourcePrefillSelector.sizeBytes(stream)?.let(::formatBytes)""",
        "variant in summary",
    )


def apply_v120_stream_variants_patch(source_dir: Path) -> None:
    _patch_presentation_helper(source_dir)
    _patch_models(source_dir)
    _patch_repository(source_dir)
    _patch_coordinator(source_dir)
    _patch_stream_card(source_dir)
    _patch_batch_dialog(source_dir)
    print("[v1.20-module-11] SUB/DUB/DUAL pills, batch badge presentation & variant keys applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_stream_variants_patch.py <source_dir>")
    apply_v120_stream_variants_patch(Path(sys.argv[1]).resolve())
