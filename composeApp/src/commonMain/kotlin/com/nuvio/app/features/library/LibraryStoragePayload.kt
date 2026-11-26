package com.nuvio.app.features.library

import com.nuvio.app.features.library.sync.LibrarySyncKey
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
internal data class StoredLibraryPayload(
    val items: List<LibraryItem> = emptyList(),
    val deltaCursorEventId: Long = 0L,
    val deltaInitialized: Boolean = false,
    val pendingUpsertKeys: List<LibrarySyncKey> = emptyList(),
    val pendingDeleteKeys: List<LibrarySyncKey> = emptyList(),
    val localCategoryOverridesByKey: Map<String, List<String>> = emptyMap(),
)

internal object LibraryStoragePayloadCodec {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun decode(payload: String): StoredLibraryPayload {
        val raw = runCatching {
            json.decodeFromString<StoredLibraryPayload>(payload)
        }.getOrDefault(StoredLibraryPayload())
        if (raw.items.isEmpty()) return raw
        val restoredItems = raw.items.map { item ->
            val key = libraryItemKey(item.id, item.type)
            val sidecar = raw.localCategoryOverridesByKey[key]
            mergeLibraryItemPreservingLocalMetadata(
                existing = null,
                incoming = item,
                fallbackCategoryKeys = sidecar,
            )
        }
        return raw.copy(items = restoredItems)
    }

    fun encode(snapshot: LibraryLocalSnapshot): String {
        val overrides = buildMap<String, List<String>> {
            putAll(snapshot.localCategoryOverridesByKey)
            snapshot.items.forEach { item ->
                val key = libraryItemKey(item.id, item.type)
                val normalized = normalizeLocalCategoryKeys(item.listKeys).toList()
                if (normalized.isNotEmpty()) {
                    put(key, normalized)
                }
            }
        }
        return json.encodeToString(
            StoredLibraryPayload(
                items = snapshot.items
                    .map { item -> item.copy(listKeys = normalizeLocalCategoryKeys(item.listKeys)) }
                    .sortedByDescending(LibraryItem::savedAtEpochMs),
                deltaCursorEventId = snapshot.deltaCursorEventId,
                deltaInitialized = snapshot.deltaInitialized,
                pendingUpsertKeys = snapshot.pendingUpsertKeys,
                pendingDeleteKeys = snapshot.pendingDeleteKeys,
                localCategoryOverridesByKey = overrides,
            ),
        )
    }
}
