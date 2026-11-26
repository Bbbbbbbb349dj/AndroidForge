"""Nuvio Enhanced v1.20 — automatic library categorisation.

When playback of a title finishes (movie ended / episode finished, per the same
watched threshold the rest of the app uses), the title is filed into its library
category automatically:

- Movie finished            -> Completed
- Episode finished           -> Watching (created if the title isn't saved yet)
- Fully-watched series      -> Completed (driven from fullyWatchedSeriesKeys)

Existing user-chosen categories are preserved; watch-status categories follow the
same single-status rule the poster quick-actions sheet uses.
"""

from __future__ import annotations

from pathlib import Path

_ACTIONS = "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimePlaybackActions.kt"
_MAIN = "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"

_NEW_FILE = """package com.nuvio.app.features.player

import com.nuvio.app.features.library.LibraryItem
import com.nuvio.app.features.library.LibraryRepository
import com.nuvio.app.features.library.LocalLibraryCategory
import com.nuvio.app.features.library.normalizeLocalCategoryKeys
import com.nuvio.app.features.watchprogress.WatchProgressPlaybackSession
import com.nuvio.app.features.watching.domain.isProgressComplete
import com.nuvio.app.isIos

/**
 * Nuvio Enhanced: files finished titles into their library category automatically.
 * Called from the progress flush path; silent, idempotent, and never downgrades a
 * title that is already marked Completed.
 */
internal fun autoCategorizeFromPlayback(
    session: WatchProgressPlaybackSession,
    snapshot: PlayerPlaybackSnapshot,
) {
    if (!isProgressComplete(snapshot.positionMs, snapshot.durationMs, snapshot.isEnded)) return
    val metaId = session.parentMetaId.trim()
    if (metaId.isEmpty()) return
    val isEpisode = session.seasonNumber != null && session.episodeNumber != null
    runCatching {
        val existing = LibraryRepository.savedItem(metaId, session.parentMetaType)
        val currentKeys = if (existing != null) {
            normalizeLocalCategoryKeys(existing.listKeys).toList()
        } else {
            emptyList()
        }
        if (isEpisode) {
            // Mid-series completion keeps the title in Watching; never downgrade Completed.
            if (LocalLibraryCategory.COMPLETED.key in currentKeys) return
            if (LocalLibraryCategory.WATCHING.key in currentKeys) return
            val base = existing ?: LibraryItem(
                id = metaId,
                type = session.parentMetaType,
                name = session.title,
                poster = session.poster,
                banner = session.background,
                logo = session.logo,
                savedAtEpochMs = 0L,
            )
            val nextKeys = currentKeys
                .filterNot { key -> LocalLibraryCategory.fromKey(key)?.isWatchStatus == true } +
                LocalLibraryCategory.WATCHING.key
            LibraryRepository.save(base.copy(listKeys = normalizeLocalCategoryKeys(nextKeys)))
        } else {
            if (LocalLibraryCategory.COMPLETED.key in currentKeys) return
            val base = existing ?: LibraryItem(
                id = metaId,
                type = session.parentMetaType,
                name = session.title,
                poster = session.poster,
                banner = session.background,
                logo = session.logo,
                savedAtEpochMs = 0L,
            )
            val nextKeys = currentKeys
                .filterNot { key -> LocalLibraryCategory.fromKey(key)?.isWatchStatus == true } +
                LocalLibraryCategory.COMPLETED.key
            LibraryRepository.save(base.copy(listKeys = normalizeLocalCategoryKeys(nextKeys)))
        }
    }
}

/**
 * Marks fully-watched series as Completed. [fullyWatchedKeys] uses the app's
 * watched-key format (type:id:season:episode with aliases), so the series id is
 * recovered by splitting on ':' the same way the poster badges do.
 */
internal fun autoCompleteFullyWatchedSeries(fullyWatchedKeys: Set<String>) {
    if (fullyWatchedKeys.isEmpty() || isIos) return
    runCatching {
        val seriesIdTypePairs = fullyWatchedKeys.mapNotNull { key ->
            val parts = key.split(':')
            if (parts.size < 4) return@mapNotNull null
            val id = parts[1].trim()
            if (id.isEmpty()) return@mapNotNull null
            val type = parts[0].trim().ifEmpty { return@mapNotNull null }
            type to id
        }.distinct()
        for ((type, id) in seriesIdTypePairs) {
            val existing = LibraryRepository.savedItem(id, type) ?: continue
            val currentKeys = normalizeLocalCategoryKeys(existing.listKeys).toList()
            if (LocalLibraryCategory.COMPLETED.key in currentKeys) continue
            val nextKeys = currentKeys
                .filterNot { key -> LocalLibraryCategory.fromKey(key)?.isWatchStatus == true } +
                LocalLibraryCategory.COMPLETED.key
            LibraryRepository.save(existing.copy(listKeys = normalizeLocalCategoryKeys(nextKeys)))
        }
    }
}
"""


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 library-auto] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 library-auto] Ambiguous anchor ({count} matches) for {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _write_helper(source_dir: Path) -> None:
    path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/LibraryAutoCategorize.kt"
    if path.exists():
        raise RuntimeError(f"[v1.20 library-auto] Refusing to overwrite existing {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_NEW_FILE, encoding="utf-8")


def _patch_flush_hook(source_dir: Path) -> None:
    path = source_dir / _ACTIONS
    _replace_once(
        path,
        """    WatchProgressRepository.flushPlaybackProgress(
        session = playbackSession,
        snapshot = playbackSnapshot,
    )
}""",
        """    WatchProgressRepository.flushPlaybackProgress(
        session = playbackSession,
        snapshot = playbackSnapshot,
    )
    autoCategorizeFromPlayback(playbackSession, playbackSnapshot)
}""",
        "flush -> auto categorize",
    )


def _patch_fully_watched_hook(source_dir: Path) -> None:
    path = source_dir / _MAIN
    _replace_once(
        path,
        """import com.nuvio.app.features.player.externalPlaybackSession""",
        """import com.nuvio.app.features.player.autoCompleteFullyWatchedSeries
import com.nuvio.app.features.player.externalPlaybackSession""",
        "auto-complete import",
    )
    _replace_once(
        path,
        """    val fullyWatchedSeriesKeys by WatchedRepository.fullyWatchedSeriesKeys.collectAsStateWithLifecycle()""",
        """    val fullyWatchedSeriesKeys by WatchedRepository.fullyWatchedSeriesKeys.collectAsStateWithLifecycle()
    LaunchedEffect(fullyWatchedSeriesKeys) {
        autoCompleteFullyWatchedSeries(fullyWatchedSeriesKeys)
    }""",
        "fully-watched series -> Completed",
    )


def apply_v120_library_auto_patch(source_dir: Path) -> None:
    _write_helper(source_dir)
    _patch_flush_hook(source_dir)
    _patch_fully_watched_hook(source_dir)
    print(
        "[v1.20-module-15] Library auto-categorisation: finished movies -> Completed, "
        "episodes -> Watching, fully-watched series -> Completed applied cleanly."
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: nuvio_v120_library_auto_patch.py <source-root>")
    apply_v120_library_auto_patch(Path(sys.argv[1]))
