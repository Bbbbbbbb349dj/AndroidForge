package com.nuvio.app.features.player

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
