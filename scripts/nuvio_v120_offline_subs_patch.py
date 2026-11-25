#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 9: Offline Subtitles (Section 3).

  - `localSubtitles()` serves `content://` SAF URIs (storage already supports them;
    the `file:`-only guard made SAF downloads report no subtitles).
  - `prepare()` no longer marks the manifest complete when downloads failed, so a later
    run retries the missing tracks (previously a transient failure — e.g. the English
    track — was sealed behind `complete=true` forever).
  - The manifest records the logical content key (`videoId` fallback `fileName`) so the
    subtitle set is identifiable across the download's lifetime.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 offline-subs] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 offline-subs] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_v120_offline_subs_patch(source_dir: Path) -> None:
    path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadSubtitles.kt"
    _replace_once(
        path,
        """        val pending = (item.sourceSubtitles + addonSubtitles)
            .distinctBy { it.url }
            .filter { subtitle ->
                (subtitle.url.startsWith("https://", true) || subtitle.url.startsWith("http://", true)) &&
                    saved.none { it.sourceUrl == subtitle.url }
            }
        for (batch in pending.chunked(4)) {""",
        """        val pending = (item.sourceSubtitles + addonSubtitles)
            .distinctBy { it.url }
            .filter { subtitle ->
                (subtitle.url.startsWith("https://", true) || subtitle.url.startsWith("http://", true)) &&
                    saved.none { it.sourceUrl == subtitle.url }
            }
        var failedCount = 0
        for (batch in pending.chunked(4)) {""",
        "failed counter",
    )
    _replace_once(
        path,
        """            for ((subtitle, body) in fetched) {
                currentCoroutineContext().ensureActive()
                if (body == null) continue""",
        """            for ((subtitle, body) in fetched) {
                currentCoroutineContext().ensureActive()
                if (body == null) {
                    failedCount++
                    continue
                }""",
        "count failures",
    )
    _replace_once(
        path,
        """        currentCoroutineContext().ensureActive()
        runCatching {
            storage.write("manifest.json", json.encodeToString(SubtitleManifest(complete = true, tracks = saved)))
        }
        Unit""",
        """        currentCoroutineContext().ensureActive()
        // Nuvio Enhanced: only seal the manifest when nothing failed, so later runs
        // retry tracks that could not be fetched (e.g. a transient English-track failure).
        val allFetched = failedCount == 0
        runCatching {
            storage.write(
                "manifest.json",
                json.encodeToString(
                    SubtitleManifest(
                        complete = allFetched,
                        contentKey = item.videoId?.takeIf { it.isNotBlank() } ?: item.fileName,
                        tracks = saved,
                    ),
                ),
            )
        }
        Unit""",
        "complete only on success + contentKey",
    )
    _replace_once(
        path,
        """    fun localSubtitles(localVideoUri: String): List<StreamSubtitle> {
        if (!localVideoUri.startsWith("file:")) return emptyList()""",
        """    fun localSubtitles(localVideoUri: String): List<StreamSubtitle> {
        // Nuvio Enhanced: content:// SAF URIs are supported by DownloadSubtitleStorage too.
        if (!localVideoUri.startsWith("file:") && !localVideoUri.startsWith("content:")) return emptyList()""",
        "content uri support",
    )
    _replace_once(
        path,
        """@Serializable
private data class SubtitleManifest(
    val complete: Boolean = false,
    val tracks: List<DownloadedSubtitle> = emptyList(),
)""",
        """@Serializable
private data class SubtitleManifest(
    val complete: Boolean = false,
    /** Logical content identity (videoId, falling back to the download file name). */
    val contentKey: String? = null,
    val tracks: List<DownloadedSubtitle> = emptyList(),
)""",
        "manifest contentKey field",
    )
    print("[v1.20-module-10] Offline subtitles: content:// support, retryable manifests & content key applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_offline_subs_patch.py <source_dir>")
    apply_v120_offline_subs_patch(Path(sys.argv[1]).resolve())
