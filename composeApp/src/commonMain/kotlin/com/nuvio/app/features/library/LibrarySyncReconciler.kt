package com.nuvio.app.features.library

import com.nuvio.app.features.library.sync.LibraryDeltaEvent
import com.nuvio.app.features.library.sync.LibrarySyncKey

internal data class LibrarySnapshotReconciliation(
    val itemsByKey: MutableMap<String, LibraryItem>,
    val pendingUpsertKeysByKey: MutableMap<String, LibrarySyncKey>,
    val pendingDeleteKeysByKey: MutableMap<String, LibrarySyncKey>,
    val preservedLocalItems: Boolean,
)

internal data class LibraryDeltaReconciliation(
    val itemsByKey: MutableMap<String, LibraryItem>,
    val changed: Boolean,
    val cursorEventId: Long,
)

internal fun reconcileLibrarySnapshot(
    serverItems: Collection<LibraryItem>,
    localItemsByKey: Map<String, LibraryItem>,
    pendingUpsertKeysByKey: Map<String, LibrarySyncKey>,
    pendingDeleteKeysByKey: Map<String, LibrarySyncKey>,
    localCategoryOverridesByKey: Map<String, List<String>> = emptyMap(),
): LibrarySnapshotReconciliation {
    val serverItemsByKey = LinkedHashMap<String, LibraryItem>()
    serverItems.forEach { serverItem ->
        val key = libraryItemKey(serverItem.id, serverItem.type)
        val localExisting = localItemsByKey[key]
        serverItemsByKey[key] = mergeLibraryItemPreservingLocalMetadata(
            existing = localExisting,
            incoming = serverItem,
            fallbackCategoryKeys = localCategoryOverridesByKey[key],
        )
    }
    val pendingUpserts = pendingUpsertKeysByKey.toMutableMap()
    val pendingDeletes = pendingDeleteKeysByKey.toMutableMap()
    pendingDeletes.keys.forEach(serverItemsByKey::remove)
    pendingUpserts.keys.forEach { key ->
        localItemsByKey[key]?.let { item ->
            serverItemsByKey[key] = mergeLibraryItemPreservingLocalMetadata(
                existing = serverItemsByKey[key],
                incoming = item,
                explicitListKeys = item.listKeys,
                fallbackCategoryKeys = localCategoryOverridesByKey[key],
            )
        }
    }

    return LibrarySnapshotReconciliation(
        itemsByKey = serverItemsByKey,
        pendingUpsertKeysByKey = pendingUpserts,
        pendingDeleteKeysByKey = pendingDeletes,
        preservedLocalItems = pendingUpserts.isNotEmpty() || pendingDeletes.isNotEmpty(),
    )
}

internal fun reconcileLibraryDelta(
    events: Collection<LibraryDeltaEvent>,
    currentItemsByKey: Map<String, LibraryItem>,
    pendingUpsertKeysByKey: Map<String, LibrarySyncKey>,
    pendingDeleteKeysByKey: Map<String, LibrarySyncKey>,
    currentCursorEventId: Long,
    localCategoryOverridesByKey: Map<String, List<String>> = emptyMap(),
): LibraryDeltaReconciliation {
    val items = currentItemsByKey.toMutableMap()

    events.sortedBy(LibraryDeltaEvent::eventId).forEach { event ->
        val key = libraryItemKey(event.item.id, event.item.type)
        if (key in pendingUpsertKeysByKey || key in pendingDeleteKeysByKey) return@forEach

        when (event.operation.trim().lowercase()) {
            "upsert" -> items[key] = mergeLibraryItemPreservingLocalMetadata(
                existing = items[key],
                incoming = event.item,
                fallbackCategoryKeys = localCategoryOverridesByKey[key],
            )
            "delete" -> items.remove(key)
        }
    }

    return LibraryDeltaReconciliation(
        itemsByKey = items,
        changed = items != currentItemsByKey,
        cursorEventId = maxOf(
            currentCursorEventId,
            events.maxOfOrNull(LibraryDeltaEvent::eventId) ?: currentCursorEventId,
        ),
    )
}
