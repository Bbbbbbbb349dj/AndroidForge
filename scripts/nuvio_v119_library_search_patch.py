#!/usr/bin/env python3
"""Nuvio Enhanced v1.19 — Module 1: Signing, Library Fixes & Controls, and Unified Search.

Implements Execution Priority Steps 2–9:
  - Step 2 (Phase 8): APK release signing hardening (V1+V2+V3, `keystore.properties` +
    `NUVIO_RELEASE_*` env support), `applicationId = "com.nuvio.enhanced"` preserved,
    `versionCode = 190`, `versionName = "1.19"`, plus `keystore.properties.example`.
  - Step 3 (Phase 2.1 & 2.2):
      * Fixes Library categories (`Watching`, `Completed`, `On hold`, `Dropped`,
        `Plan to watch`) reverting to `Plan to watch` after sync/refresh/restart by
        preserving local `listKeys` + metadata in `LibrarySyncReconciler`, persisting a
        `localCategoryOverrides` sidecar in `StoredLibraryPayload`, enforcing single
        watch-status key replacement, and merging metadata in `LibraryLocalState.upsert`.
      * Fixes false-positive Duplicate Title dialog when moving an existing Library item
        between categories (`TrackingListPickerDialog` + `LibraryRepository.findOtherDuplicateCandidates`).
  - Step 4 (Phase 2.5): Removes ONLY the top-right Download button on `LibraryScreen`,
    keeping Downloads tab, Details downloads, CloudStream downloads, and Player intact.
  - Step 5 (Phase 2.3 & 2.4):
      * Adds persisted `LibraryCategoryNavPosition` (`TOP` / `BOTTOM`) applied immediately.
      * Replaces on-screen `LibrarySavedControls` sticky bar with a Library-only
        bottom-right Sort & Filter FAB + `LibrarySortFilterBottomSheet`.
  - Steps 6–9 (Phase 3.1–3.4):
      * Debounced live Search Autocomplete with loading, empty, and error states.
      * Persistent deduplicated Search History with single-entry delete & `Clear all`.
      * Persisted `"Include CloudStream Extensions"` search toggle with concurrent
        attributed extension search, deduplication, isolated provider failure handling,
        and zero overhead when disabled.
      * Home Screen top-right Search entry point reusing the exact same `SearchScreen`.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.19 mod1] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.19 mod1] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 2 (Phase 8): Signing, Package Identity & Version Bump (v1.19 / 190)
# ---------------------------------------------------------------------------

def _patch_signing_and_version(root: Path) -> None:
    app_gradle = root / "androidApp/build.gradle.kts"
    _replace_once(
        app_gradle,
        r"""val defaultKeystore = rootProject.file("keystore/nuvio-enhanced.jks")
val hasDefaultKeystore = defaultKeystore.exists()

val releaseStoreFile = envOrLocalProperty("NUVIO_RELEASE_STORE_FILE")
val releaseStorePassword = envOrLocalProperty("NUVIO_RELEASE_STORE_PASSWORD")
val releaseKeyAlias = envOrLocalProperty("NUVIO_RELEASE_KEY_ALIAS")
val releaseKeyPassword = envOrLocalProperty("NUVIO_RELEASE_KEY_PASSWORD")
val releaseKeystore = releaseStoreFile?.let(rootProject::file)
    ?: if (hasDefaultKeystore) defaultKeystore else null""",
        r"""val keystoreProps = Properties().apply {
    val ksFile = rootProject.file("keystore.properties")
    if (ksFile.exists()) ksFile.inputStream().use { load(it) }
}
fun signingProperty(envKey: String, propKey: String): String? =
    envOrLocalProperty(envKey)
        ?: keystoreProps.getProperty(propKey)?.trim()?.takeIf { it.isNotBlank() }

val defaultKeystore = rootProject.file("keystore/nuvio-enhanced.jks")
val hasDefaultKeystore = defaultKeystore.exists()

val releaseStoreFile = signingProperty("NUVIO_RELEASE_STORE_FILE", "storeFile")
val releaseStorePassword = signingProperty("NUVIO_RELEASE_STORE_PASSWORD", "storePassword")
val releaseKeyAlias = signingProperty("NUVIO_RELEASE_KEY_ALIAS", "keyAlias")
val releaseKeyPassword = signingProperty("NUVIO_RELEASE_KEY_PASSWORD", "keyPassword") ?: releaseStorePassword
val releaseKeystore = releaseStoreFile
    ?.let { path -> File(path).let { if (it.isAbsolute) it else rootProject.file(path) } }
    ?.takeIf { it.isFile }
    ?: if (hasDefaultKeystore) defaultKeystore else null""",
        "androidApp keystore.properties + env signing support",
    )

    _replace_once(
        app_gradle,
        r"""    signingConfigs {
        create("release") {
            if (releaseKeystore != null && releaseStorePassword != null && releaseKeyAlias != null && releaseKeyPassword != null) {
                storeFile = releaseKeystore
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }""",
        r"""    signingConfigs {
        create("release") {
            if (releaseKeystore != null && releaseStorePassword != null && releaseKeyAlias != null && releaseKeyPassword != null) {
                storeFile = releaseKeystore
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
                enableV1Signing = true
                enableV2Signing = true
                enableV3Signing = true
            }
        }
    }""",
        "androidApp enable V1/V2/V3 signing schemes",
    )

    xcconfig = root / "iosApp/Configuration/Version.xcconfig"
    _replace_once(
        xcconfig,
        "MARKETING_VERSION=1.18\n",
        "MARKETING_VERSION=1.19\n",
        "Version.xcconfig MARKETING_VERSION=1.19",
    )
    _replace_once(
        xcconfig,
        "CURRENT_PROJECT_VERSION=180\n",
        "CURRENT_PROJECT_VERSION=190\n",
        "Version.xcconfig CURRENT_PROJECT_VERSION=190",
    )

    gradle_props = root / "gradle.properties"
    _replace_once(
        gradle_props,
        "nuvio.app.versionName=1.18\n",
        "nuvio.app.versionName=1.19\n",
        "gradle.properties nuvio.app.versionName=1.19",
    )

    local_folder_android = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.android.kt"
    if local_folder_android.is_file():
        _replace_once(
            local_folder_android,
            '"NuvioEnhanced/1.18"',
            '"NuvioEnhanced/1.19"',
            "LocalFolderVideosPlatform User-Agent NuvioEnhanced/1.19",
        )

    example_props = root / "keystore.properties.example"
    example_props.write_text(
        "# Copy to keystore.properties (gitignored) or supply NUVIO_RELEASE_* environment variables\n"
        "# so every release APK shares the exact same signing certificate across upgrades.\n"
        "storeFile=keystore/nuvio-enhanced.jks\n"
        "storePassword=CHANGE_ME\n"
        "keyAlias=nuvioenhanced\n"
        "keyPassword=CHANGE_ME\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Step 3 (Phase 2.1 & 2.2): Library Category Persistence & Duplicate Detection
# ---------------------------------------------------------------------------

def _patch_library_persistence_and_duplicates(root: Path) -> None:
    categories_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryCategories.kt"
    _replace_once(
        categories_kt,
        r"""fun LibraryItem.effectiveLocalCategoryKeys(): Set<String> {
    val explicit = listKeys.filterTo(linkedSetOf()) { it in LocalLibraryCategory.allKeys }
    return if (explicit.isNotEmpty()) {
        explicit
    } else {
        setOf(LocalLibraryCategory.PLAN_TO_WATCH.key)
    }
}""",
        r"""/**
 * Normalizes a set of local category keys so at most ONE watch-status category
 * (`Watching`, `Completed`, `Plan to watch`, `On hold`, `Dropped`) is active at a time,
 * while preserving collection/alert tags (`Favourites`, `Subscribed`) and duplicate markers.
 *
 * When multiple watch-status keys are present, the LAST watch-status key in iteration order
 * wins so newly selected statuses (e.g. `On hold` or `Dropped`) never lose to an older
 * `Plan to watch` entry due to enum declaration order.
 */
fun normalizeLocalCategoryKeys(
    rawKeys: Collection<String>,
    defaultToPlanToWatch: Boolean = true,
): Set<String> {
    var chosenWatchStatus: String? = null
    val extras = linkedSetOf<String>()
    for (raw in rawKeys) {
        val key = raw.trim()
        when {
            key in LocalLibraryCategory.watchStatusKeys -> chosenWatchStatus = key
            key in LocalLibraryCategory.allKeys -> extras += key
            key == LOCAL_ALLOW_DUPLICATE_MARKER -> extras += key
        }
    }
    return buildSet {
        if (chosenWatchStatus != null) {
            add(chosenWatchStatus)
        } else if (defaultToPlanToWatch && extras.none { it in LocalLibraryCategory.allKeys }) {
            add(LocalLibraryCategory.PLAN_TO_WATCH.key)
        }
        addAll(extras)
    }
}

fun toggleLocalCategoryMembership(
    current: Map<String, Boolean>,
    toggledKey: String,
): Map<String, Boolean> {
    val category = LocalLibraryCategory.fromKey(toggledKey)
    val next = current.toMutableMap()
    if (category?.isWatchStatus == true) {
        LocalLibraryCategory.watchStatusKeys.forEach { statusKey ->
            next[statusKey] = (statusKey == toggledKey)
        }
    } else {
        next[toggledKey] = !(current[toggledKey] ?: false)
    }
    return next
}

fun mergeLibraryItemPreservingLocalMetadata(
    existing: LibraryItem?,
    incoming: LibraryItem,
    explicitListKeys: Collection<String>? = null,
    fallbackCategoryKeys: Collection<String>? = null,
): LibraryItem {
    val resolvedKeys: Set<String> = when {
        explicitListKeys != null -> {
            val allowDup = if (
                LOCAL_ALLOW_DUPLICATE_MARKER in explicitListKeys ||
                (existing != null && LOCAL_ALLOW_DUPLICATE_MARKER in existing.listKeys)
            ) {
                listOf(LOCAL_ALLOW_DUPLICATE_MARKER)
            } else {
                emptyList()
            }
            normalizeLocalCategoryKeys(explicitListKeys + allowDup)
        }
        incoming.listKeys.any { it in LocalLibraryCategory.allKeys } ->
            normalizeLocalCategoryKeys(incoming.listKeys)
        existing != null && existing.listKeys.any { it in LocalLibraryCategory.allKeys } ->
            normalizeLocalCategoryKeys(existing.listKeys)
        !fallbackCategoryKeys.isNullOrEmpty() ->
            normalizeLocalCategoryKeys(fallbackCategoryKeys)
        else -> setOf(LocalLibraryCategory.PLAN_TO_WATCH.key)
    }
    if (existing == null) {
        return incoming.copy(listKeys = resolvedKeys)
    }
    return incoming.copy(
        name = incoming.name.ifBlank { existing.name },
        poster = incoming.poster?.takeIf { it.isNotBlank() } ?: existing.poster,
        posterShape = incoming.posterShape,
        banner = incoming.banner?.takeIf { it.isNotBlank() } ?: existing.banner,
        logo = incoming.logo?.takeIf { it.isNotBlank() } ?: existing.logo,
        description = incoming.description?.takeIf { it.isNotBlank() } ?: existing.description,
        releaseInfo = incoming.releaseInfo?.takeIf { it.isNotBlank() } ?: existing.releaseInfo,
        imdbRating = incoming.imdbRating?.takeIf { it.isNotBlank() } ?: existing.imdbRating,
        genres = incoming.genres.ifEmpty { existing.genres },
        addonBaseUrl = incoming.addonBaseUrl?.takeIf { it.isNotBlank() } ?: existing.addonBaseUrl,
        savedAtEpochMs = when {
            existing.savedAtEpochMs > 0L -> existing.savedAtEpochMs
            incoming.savedAtEpochMs > 0L -> incoming.savedAtEpochMs
            else -> 0L
        },
        listKeys = resolvedKeys,
        imdbId = incoming.imdbId?.takeIf { it.isNotBlank() } ?: existing.imdbId,
        tmdbId = incoming.tmdbId ?: existing.tmdbId,
        traktId = incoming.traktId ?: existing.traktId,
        mediaCategory = incoming.mediaCategory?.takeIf { it.isNotBlank() } ?: existing.mediaCategory,
    )
}

fun LibraryItem.effectiveLocalCategoryKeys(): Set<String> {
    val explicit = listKeys.filter { it in LocalLibraryCategory.allKeys }
    return if (explicit.isNotEmpty()) {
        normalizeLocalCategoryKeys(explicit)
    } else {
        setOf(LocalLibraryCategory.PLAN_TO_WATCH.key)
    }
}""",
        "LibraryCategories normalization + metadata-preserving merge",
    )

    # Patch StoredLibraryPayload to persist category overrides sidecar
    payload_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryStoragePayload.kt"
    _replace_once(
        payload_kt,
        r"""@Serializable
internal data class StoredLibraryPayload(
    val items: List<LibraryItem> = emptyList(),
    val deltaCursorEventId: Long = 0L,
    val deltaInitialized: Boolean = false,
    val pendingUpsertKeys: List<LibrarySyncKey> = emptyList(),
    val pendingDeleteKeys: List<LibrarySyncKey> = emptyList(),
)

internal object LibraryStoragePayloadCodec {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun decode(payload: String): StoredLibraryPayload =
        runCatching {
            json.decodeFromString<StoredLibraryPayload>(payload)
        }.getOrDefault(StoredLibraryPayload())

    fun encode(snapshot: LibraryLocalSnapshot): String =
        json.encodeToString(
            StoredLibraryPayload(
                items = snapshot.items.sortedByDescending(LibraryItem::savedAtEpochMs),
                deltaCursorEventId = snapshot.deltaCursorEventId,
                deltaInitialized = snapshot.deltaInitialized,
                pendingUpsertKeys = snapshot.pendingUpsertKeys,
                pendingDeleteKeys = snapshot.pendingDeleteKeys,
            ),
        )
}""",
        r"""@Serializable
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
}""",
        "LibraryStoragePayload category sidecar persistence",
    )

    # Patch LibrarySyncReconciler so server snapshots & deltas never wipe local categories/metadata
    reconciler_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibrarySyncReconciler.kt"
    _replace_once(
        reconciler_kt,
        r"""internal fun reconcileLibrarySnapshot(
    serverItems: Collection<LibraryItem>,
    localItemsByKey: Map<String, LibraryItem>,
    pendingUpsertKeysByKey: Map<String, LibrarySyncKey>,
    pendingDeleteKeysByKey: Map<String, LibrarySyncKey>,
): LibrarySnapshotReconciliation {
    val serverItemsByKey = serverItems.associateByTo(mutableMapOf()) {
        libraryItemKey(it.id, it.type)
    }
    val pendingUpserts = pendingUpsertKeysByKey.toMutableMap()
    val pendingDeletes = pendingDeleteKeysByKey.toMutableMap()
    pendingDeletes.keys.forEach(serverItemsByKey::remove)
    pendingUpserts.keys.forEach { key ->
        localItemsByKey[key]?.let { item -> serverItemsByKey[key] = item }
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
): LibraryDeltaReconciliation {
    val items = currentItemsByKey.toMutableMap()

    events.sortedBy(LibraryDeltaEvent::eventId).forEach { event ->
        val key = libraryItemKey(event.item.id, event.item.type)
        if (key in pendingUpsertKeysByKey || key in pendingDeleteKeysByKey) return@forEach

        when (event.operation.trim().lowercase()) {
            "upsert" -> items[key] = event.item
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
}""",
        r"""internal fun reconcileLibrarySnapshot(
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
}""",
        "LibrarySyncReconciler preserve local categories & metadata",
    )

    # Patch LibraryLocalState to track localCategoryOverridesByKey & merge on upsert
    local_state_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryLocalState.kt"
    _replace_once(
        local_state_kt,
        r"""    val pendingUpsertKeys: List<LibrarySyncKey>,
    val pendingDeleteKeys: List<LibrarySyncKey>,
) {""",
        r"""    val pendingUpsertKeys: List<LibrarySyncKey>,
    val pendingDeleteKeys: List<LibrarySyncKey>,
    val localCategoryOverridesByKey: Map<String, List<String>> = emptyMap(),
) {""",
        "LibraryLocalSnapshot localCategoryOverridesByKey field",
    )
    _replace_once(
        local_state_kt,
        r"""    private var pendingUpsertKeysByKey: MutableMap<String, LibrarySyncKey> = mutableMapOf()
    private var pendingDeleteKeysByKey: MutableMap<String, LibrarySyncKey> = mutableMapOf()""",
        r"""    private var pendingUpsertKeysByKey: MutableMap<String, LibrarySyncKey> = mutableMapOf()
    private var pendingDeleteKeysByKey: MutableMap<String, LibrarySyncKey> = mutableMapOf()
    private var localCategoryOverridesByKey: MutableMap<String, List<String>> = mutableMapOf()""",
        "LibraryLocalState localCategoryOverridesByKey state",
    )
    _replace_once(
        local_state_kt,
        r"""        isLoading = true
        itemsById = mutableMapOf()
        deltaCursorEventId = 0L
        deltaInitialized = false
        pendingUpsertKeysByKey = mutableMapOf()
        pendingDeleteKeysByKey = mutableMapOf()
        LibraryStateTransition(""",
        r"""        isLoading = true
        itemsById = mutableMapOf()
        deltaCursorEventId = 0L
        deltaInitialized = false
        pendingUpsertKeysByKey = mutableMapOf()
        pendingDeleteKeysByKey = mutableMapOf()
        localCategoryOverridesByKey = mutableMapOf()
        LibraryStateTransition(""",
        "LibraryLocalState.beginProfileLoad clear overrides",
    )
    _replace_once(
        local_state_kt,
        r"""        isLoading = false
        itemsById = mutableMapOf()
        deltaCursorEventId = 0L
        deltaInitialized = false
        pendingUpsertKeysByKey = mutableMapOf()
        pendingDeleteKeysByKey = mutableMapOf()
        LibraryStateTransition(""",
        r"""        isLoading = false
        itemsById = mutableMapOf()
        deltaCursorEventId = 0L
        deltaInitialized = false
        pendingUpsertKeysByKey = mutableMapOf()
        pendingDeleteKeysByKey = mutableMapOf()
        localCategoryOverridesByKey = mutableMapOf()
        LibraryStateTransition(""",
        "LibraryLocalState.reset clear overrides",
    )
    _replace_once(
        local_state_kt,
        r"""    fun completeProfileLoad(
        token: LibraryProfileToken,
        activeProfileId: Int,
        items: Collection<LibraryItem>,
        deltaCursorEventId: Long = 0L,
        deltaInitialized: Boolean = false,
        pendingUpsertKeys: Collection<LibrarySyncKey> = emptyList(),
        pendingDeleteKeys: Collection<LibrarySyncKey> = emptyList(),
    ): LibraryLocalSnapshot? = synchronized(lock) {
        if (activeProfileId != token.profileId || !isCurrentLocked(token)) {
            return@synchronized null
        }
        itemsById = items.associateByTo(mutableMapOf()) { libraryItemKey(it.id, it.type) }""",
        r"""    fun completeProfileLoad(
        token: LibraryProfileToken,
        activeProfileId: Int,
        items: Collection<LibraryItem>,
        deltaCursorEventId: Long = 0L,
        deltaInitialized: Boolean = false,
        pendingUpsertKeys: Collection<LibrarySyncKey> = emptyList(),
        pendingDeleteKeys: Collection<LibrarySyncKey> = emptyList(),
        categoryOverridesByKey: Map<String, List<String>> = emptyMap(),
    ): LibraryLocalSnapshot? = synchronized(lock) {
        if (activeProfileId != token.profileId || !isCurrentLocked(token)) {
            return@synchronized null
        }
        localCategoryOverridesByKey = categoryOverridesByKey.toMutableMap()
        itemsById = LinkedHashMap<String, LibraryItem>().apply {
            items.forEach { raw ->
                val key = libraryItemKey(raw.id, raw.type)
                val merged = mergeLibraryItemPreservingLocalMetadata(
                    existing = null,
                    incoming = raw,
                    fallbackCategoryKeys = localCategoryOverridesByKey[key],
                )
                put(key, merged)
                localCategoryOverridesByKey[key] = normalizeLocalCategoryKeys(merged.listKeys).toList()
            }
        }""",
        "LibraryLocalState.completeProfileLoad restore category overrides",
    )
    _replace_once(
        local_state_kt,
        r"""        val reconciliation = reconcileLibrarySnapshot(
            serverItems = serverItems,
            localItemsByKey = itemsById,
            pendingUpsertKeysByKey = pendingUpsertKeysByKey,
            pendingDeleteKeysByKey = pendingDeleteKeysByKey,
        )""",
        r"""        val reconciliation = reconcileLibrarySnapshot(
            serverItems = serverItems,
            localItemsByKey = itemsById,
            pendingUpsertKeysByKey = pendingUpsertKeysByKey,
            pendingDeleteKeysByKey = pendingDeleteKeysByKey,
            localCategoryOverridesByKey = localCategoryOverridesByKey,
        )""",
        "LibraryLocalState.applyServerItems pass localCategoryOverridesByKey",
    )
    _replace_once(
        local_state_kt,
        r"""        val reconciliation = reconcileLibraryDelta(
            events = events,
            currentItemsByKey = itemsById,
            pendingUpsertKeysByKey = pendingUpsertKeysByKey,
            pendingDeleteKeysByKey = pendingDeleteKeysByKey,
            currentCursorEventId = deltaCursorEventId,
        )""",
        r"""        val reconciliation = reconcileLibraryDelta(
            events = events,
            currentItemsByKey = itemsById,
            pendingUpsertKeysByKey = pendingUpsertKeysByKey,
            pendingDeleteKeysByKey = pendingDeleteKeysByKey,
            currentCursorEventId = deltaCursorEventId,
            localCategoryOverridesByKey = localCategoryOverridesByKey,
        )""",
        "LibraryLocalState.applyDeltaEvents pass localCategoryOverridesByKey",
    )
    _replace_once(
        local_state_kt,
        r"""    fun upsert(item: LibraryItem): LibraryLocalSnapshot = synchronized(lock) {
        val key = libraryItemKey(item.id, item.type)
        itemsById[key] = item
        pendingUpsertKeysByKey[key] = item.toLibrarySyncKey()
        pendingDeleteKeysByKey.remove(key)
        revision += 1L
        contentRevision += 1L
        snapshotLocked()
    }""",
        r"""    fun upsert(item: LibraryItem): LibraryLocalSnapshot = synchronized(lock) {
        val key = libraryItemKey(item.id, item.type)
        val existing = itemsById[key]
        val merged = mergeLibraryItemPreservingLocalMetadata(
            existing = existing,
            incoming = item,
            explicitListKeys = item.listKeys.takeIf { it.isNotEmpty() },
            fallbackCategoryKeys = localCategoryOverridesByKey[key],
        )
        itemsById[key] = merged
        localCategoryOverridesByKey[key] = normalizeLocalCategoryKeys(merged.listKeys).toList()
        pendingUpsertKeysByKey[key] = merged.toLibrarySyncKey()
        pendingDeleteKeysByKey.remove(key)
        revision += 1L
        contentRevision += 1L
        snapshotLocked()
    }""",
        "LibraryLocalState.upsert preserve metadata + record category sidecar",
    )
    _replace_once(
        local_state_kt,
        r"""            itemsById.remove(key)
            pendingUpsertKeysByKey.remove(key)
            pendingDeleteKeysByKey[key] = item.toLibrarySyncKey()""",
        r"""            itemsById.remove(key)
            localCategoryOverridesByKey.remove(key)
            pendingUpsertKeysByKey.remove(key)
            pendingDeleteKeysByKey[key] = item.toLibrarySyncKey()""",
        "LibraryLocalState.removeById clear category override",
    )
    _replace_once(
        local_state_kt,
        r"""        if (removedItem != null) {
            pendingUpsertKeysByKey.remove(key)
            pendingDeleteKeysByKey[key] = removedItem.toLibrarySyncKey()""",
        r"""        if (removedItem != null) {
            localCategoryOverridesByKey.remove(key)
            pendingUpsertKeysByKey.remove(key)
            pendingDeleteKeysByKey[key] = removedItem.toLibrarySyncKey()""",
        "LibraryLocalState.remove clear category override",
    )
    _replace_once(
        local_state_kt,
        r"""            pendingUpsertKeys = pendingUpsertKeysByKey.values.toList(),
            pendingDeleteKeys = pendingDeleteKeysByKey.values.toList(),
        )""",
        r"""            pendingUpsertKeys = pendingUpsertKeysByKey.values.toList(),
            pendingDeleteKeys = pendingDeleteKeysByKey.values.toList(),
            localCategoryOverridesByKey = localCategoryOverridesByKey.toMap(),
        )""",
        "LibraryLocalState.snapshotLocked include localCategoryOverridesByKey",
    )

    # Patch LibraryRepository loadFromDisk + duplicate candidate helpers + applyMembershipChanges
    repo_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryRepository.kt"
    repo_text = repo_kt.read_text(encoding="utf-8")
    if "categoryOverridesByKey = storedPayload.localCategoryOverridesByKey" not in repo_text:
        _replace_once(
            repo_kt,
            "pendingDeleteKeys = storedPayload.pendingDeleteKeys,",
            "pendingDeleteKeys = storedPayload.pendingDeleteKeys,\n            categoryOverridesByKey = storedPayload.localCategoryOverridesByKey,",
            "LibraryRepository.completeLoadFromDisk pass localCategoryOverridesByKey",
        )

    _replace_once(
        repo_kt,
        r"""        if (updateLocal) {
            if (localDesired) {
                val existingSameItem = localState.find(item.id, item.type)
                val otherDuplicates = findDuplicateCandidates(item).filterNot {
                    it.id == item.id && it.type.equals(item.type, ignoreCase = true)
                }
                when (duplicateResolution) {
                    DuplicateLibraryResolution.REPLACE -> {
                        otherDuplicates.forEach { dup -> remove(dup.id, dup.type) }
                        save(item.copy(listKeys = effectiveLocalKeys))
                    }
                    DuplicateLibraryResolution.ADD -> {
                        if (existingSameItem != null) {
                            val mergedKeys = existingSameItem.effectiveLocalCategoryKeys() + effectiveLocalKeys
                            val preservedAllowDup = if (LOCAL_ALLOW_DUPLICATE_MARKER in existingSameItem.listKeys) {
                                setOf(LOCAL_ALLOW_DUPLICATE_MARKER)
                            } else {
                                emptySet()
                            }
                            save(item.copy(listKeys = mergedKeys + preservedAllowDup))
                        } else {
                            val allowDupFlag = if (otherDuplicates.isNotEmpty()) {
                                setOf(LOCAL_ALLOW_DUPLICATE_MARKER)
                            } else {
                                emptySet()
                            }
                            save(item.copy(listKeys = effectiveLocalKeys + allowDupFlag))
                        }
                    }
                    null -> {
                        // Prevent silent duplicate titles unless explicitly added via DuplicateLibraryResolution.ADD
                        otherDuplicates
                            .filterNot { LOCAL_ALLOW_DUPLICATE_MARKER in it.listKeys }
                            .forEach { dup -> remove(dup.id, dup.type) }
                        val preservedAllowDup = if (existingSameItem != null && LOCAL_ALLOW_DUPLICATE_MARKER in existingSameItem.listKeys) {
                            setOf(LOCAL_ALLOW_DUPLICATE_MARKER)
                        } else {
                            emptySet()
                        }
                        save(item.copy(listKeys = effectiveLocalKeys + preservedAllowDup))
                    }
                }
            } else if (currentlyInLocal) {
                remove(item.id, item.type)
            }
        }""",
        r"""        if (updateLocal) {
            if (localDesired) {
                val existingSameItem = localState.find(item.id, item.type)
                val otherDuplicates = findOtherDuplicateCandidates(item)
                val normalizedRequestedKeys = normalizeLocalCategoryKeys(effectiveLocalKeys)
                when (duplicateResolution) {
                    DuplicateLibraryResolution.REPLACE -> {
                        otherDuplicates.forEach { dup -> remove(dup.id, dup.type) }
                        save(
                            mergeLibraryItemPreservingLocalMetadata(
                                existing = existingSameItem,
                                incoming = item,
                                explicitListKeys = normalizedRequestedKeys,
                            ),
                        )
                    }
                    DuplicateLibraryResolution.ADD -> {
                        if (existingSameItem != null) {
                            // Updating an existing item's category replaces its watch status cleanly
                            // rather than unioning stale `local:plan_to_watch` back in.
                            save(
                                mergeLibraryItemPreservingLocalMetadata(
                                    existing = existingSameItem,
                                    incoming = item,
                                    explicitListKeys = normalizedRequestedKeys,
                                ),
                            )
                        } else {
                            val allowDupFlag = if (otherDuplicates.isNotEmpty()) {
                                setOf(LOCAL_ALLOW_DUPLICATE_MARKER)
                            } else {
                                emptySet()
                            }
                            save(
                                mergeLibraryItemPreservingLocalMetadata(
                                    existing = null,
                                    incoming = item,
                                    explicitListKeys = normalizedRequestedKeys + allowDupFlag,
                                ),
                            )
                        }
                    }
                    null -> {
                        if (existingSameItem == null) {
                            otherDuplicates
                                .filterNot { LOCAL_ALLOW_DUPLICATE_MARKER in it.listKeys }
                                .forEach { dup -> remove(dup.id, dup.type) }
                        }
                        save(
                            mergeLibraryItemPreservingLocalMetadata(
                                existing = existingSameItem,
                                incoming = item,
                                explicitListKeys = normalizedRequestedKeys,
                            ),
                        )
                    }
                }
            } else if (currentlyInLocal) {
                remove(item.id, item.type)
            }
        }""",
        "LibraryRepository.applyMembershipChanges single-status + metadata-safe category move",
    )

    _replace_once(
        repo_kt,
        "    fun findDuplicateCandidates(candidate: LibraryItem): List<LibraryItem> {",
        r"""    fun findSavedItem(id: String, type: String): LibraryItem? {
        ensureLoaded()
        return localState.find(id, type)
    }

    fun findOtherDuplicateCandidates(candidate: LibraryItem): List<LibraryItem> =
        findDuplicateCandidates(candidate).filterNot { existing ->
            existing.id.trim() == candidate.id.trim() &&
                existing.type.trim().equals(candidate.type.trim(), ignoreCase = true)
        }

    fun findDuplicateCandidates(candidate: LibraryItem): List<LibraryItem> {""",
        "LibraryRepository.findSavedItem & findOtherDuplicateCandidates",
    )

    # Patch TrackingListPickerDialog so moving an existing Library item between categories NEVER triggers false duplicate dialog
    picker_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/TrackingListPickerDialog.kt"
    _replace_once(
        picker_kt,
        r"""    val existingDuplicates = remember(targetItem, visible) {
        targetItem?.let(LibraryRepository::findDuplicateCandidates).orEmpty()
    }
    val existingExact = remember(targetItem, existingDuplicates) {
        targetItem?.let { candidate ->
            existingDuplicates.firstOrNull {
                it.id == candidate.id && it.type.equals(candidate.type, ignoreCase = true)
            }
        }
    }""",
        r"""    val existingExact = remember(targetItem, visible) {
        targetItem?.let { candidate -> LibraryRepository.findSavedItem(candidate.id, candidate.type) }
    }
    val otherDuplicates = remember(targetItem, visible) {
        targetItem?.let(LibraryRepository::findOtherDuplicateCandidates).orEmpty()
    }
    val existingDuplicates = remember(existingExact, otherDuplicates) {
        buildList {
            if (existingExact != null) add(existingExact)
            addAll(otherDuplicates)
        }
    }""",
        "TrackingListPickerDialog separate existingExact from otherDuplicates",
    )
    _replace_once(
        picker_kt,
        r"""                    val hasAnyLocalSelected = LocalLibraryCategory.allKeys.any { membership[it] == true }
                    if (onSaveWithResolution != null && hasAnyLocalSelected && existingDuplicates.isNotEmpty()) {
                        showDuplicateConfirm = true
                    } else if (onSaveWithResolution != null) {
                        onSaveWithResolution(null)
                    } else {
                        onSave()
                    }""",
        r"""                    val hasAnyLocalSelected = LocalLibraryCategory.allKeys.any { membership[it] == true }
                    if (
                        onSaveWithResolution != null &&
                        hasAnyLocalSelected &&
                        existingExact == null &&
                        otherDuplicates.isNotEmpty()
                    ) {
                        showDuplicateConfirm = true
                    } else if (onSaveWithResolution != null) {
                        onSaveWithResolution(null)
                    } else {
                        onSave()
                    }""",
        "TrackingListPickerDialog skip duplicate dialog when moving existing item",
    )
    _replace_once(
        picker_kt,
        r"""    LibraryDuplicateAlertDialog(
        visible = showDuplicateConfirm,
        candidateTitle = title,
        existingItems = existingDuplicates,""",
        r"""    LibraryDuplicateAlertDialog(
        visible = showDuplicateConfirm,
        candidateTitle = title,
        existingItems = otherDuplicates,""",
        "TrackingListPickerDialog pass only genuine otherDuplicates",
    )


# ---------------------------------------------------------------------------
# Steps 4 & 5 (Phase 2.3, 2.4, 2.5):
# - Remove ONLY Library Top-Right Download Button
# - Library Navigation Position (Top / Bottom)
# - Library-Only Bottom-Right Sort & Filter FAB + Bottom Sheet
# ---------------------------------------------------------------------------

LIBRARY_SORT_FILTER_SHEET_KT = r"""package com.nuvio.app.features.library

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.FilterList
import androidx.compose.material.icons.rounded.GridView
import androidx.compose.material.icons.rounded.RestartAlt
import androidx.compose.material.icons.rounded.ViewAgenda
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.i18n.localizedMediaTypeLabel
import com.nuvio.app.core.ui.NuvioModalBottomSheet
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.nuvio
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.library_filter_all_types
import nuvio.composeapp.generated.resources.library_filter_genre
import nuvio.composeapp.generated.resources.library_filter_list
import nuvio.composeapp.generated.resources.library_filter_sort
import nuvio.composeapp.generated.resources.library_filter_type
import nuvio.composeapp.generated.resources.library_filter_watched
import nuvio.composeapp.generated.resources.library_filter_year
import nuvio.composeapp.generated.resources.library_sort_added_asc
import nuvio.composeapp.generated.resources.library_sort_added_desc
import nuvio.composeapp.generated.resources.library_sort_provider_order
import nuvio.composeapp.generated.resources.library_sort_released_asc
import nuvio.composeapp.generated.resources.library_sort_released_desc
import nuvio.composeapp.generated.resources.library_sort_title_asc
import nuvio.composeapp.generated.resources.library_sort_title_desc
import nuvio.composeapp.generated.resources.library_type_all
import nuvio.composeapp.generated.resources.library_watched_filter_all
import nuvio.composeapp.generated.resources.library_watched_filter_unwatched
import nuvio.composeapp.generated.resources.library_watched_filter_watched
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun LibrarySortFilterFab(
    activeFilterCount: Int,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    Box(modifier = modifier) {
        FloatingActionButton(
            onClick = onClick,
            shape = CircleShape,
            containerColor = tokens.colors.accent,
            contentColor = tokens.colors.onAccent,
            elevation = FloatingActionButtonDefaults.elevation(
                defaultElevation = 6.dp,
                pressedElevation = 10.dp,
            ),
            modifier = Modifier
                .size(54.dp)
                .semantics { contentDescription = "Sort and filter Library" },
        ) {
            Icon(
                imageVector = Icons.Rounded.FilterList,
                contentDescription = null,
                modifier = Modifier.size(24.dp),
            )
        }
        if (activeFilterCount > 0) {
            Surface(
                shape = CircleShape,
                color = tokens.colors.surfaceCard,
                border = BorderStroke(1.5.dp, tokens.colors.accent),
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .size(20.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = activeFilterCount.coerceAtMost(9).toString(),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = tokens.colors.textPrimary,
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
internal fun LibrarySortFilterBottomSheet(
    visible: Boolean,
    layoutMode: LibraryLayoutMode,
    categoryNavPosition: LibraryCategoryNavPosition,
    sourceMode: LibrarySourceMode,
    sortOption: LibrarySortOption,
    verticalProjection: LibraryVerticalProjection,
    watchedFilter: LibraryWatchedFilter,
    onLayoutModeSelected: (LibraryLayoutMode) -> Unit,
    onCategoryNavPositionSelected: (LibraryCategoryNavPosition) -> Unit,
    onSectionSelected: (String) -> Unit,
    onTypeSelected: (String?) -> Unit,
    onGenreSelected: (String?) -> Unit,
    onYearSelected: (String?) -> Unit,
    onWatchedFilterSelected: (LibraryWatchedFilter) -> Unit,
    onSortSelected: (LibrarySortOption) -> Unit,
    onClearFilters: () -> Unit,
    onDismiss: () -> Unit,
) {
    if (!visible) return
    val tokens = MaterialTheme.nuvio
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val sortOptions = availableLibrarySortOptions(sourceMode)
    val allLabel = stringResource(Res.string.library_type_all)
    val allTypesLabel = stringResource(Res.string.library_filter_all_types)

    NuvioModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        contentColor = tokens.colors.textPrimary,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 620.dp)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Sort & Filter Library",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = tokens.colors.textPrimary,
                    )
                    Text(
                        text = "Customize sorting, filters, layout, and category bar position",
                        style = MaterialTheme.typography.bodySmall,
                        color = tokens.colors.textMuted,
                    )
                }
                OutlinedButton(
                    onClick = onClearFilters,
                    border = BorderStroke(1.dp, tokens.colors.borderDefault),
                ) {
                    Icon(
                        imageVector = Icons.Rounded.RestartAlt,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = tokens.colors.textSecondary,
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Reset", color = tokens.colors.textPrimary)
                }
            }

            HorizontalDivider(color = tokens.colors.borderSubtle)

            // 1. Sort Order
            SheetSectionTitle(stringResource(Res.string.library_filter_sort))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                sortOptions.forEach { option ->
                    SheetFilterPill(
                        label = sheetSortLabel(option),
                        selected = option == sortOption,
                        onClick = { onSortSelected(option) },
                    )
                }
            }

            // 2. Display Layout & Category Bar Position
            HorizontalDivider(color = tokens.colors.borderSubtle)
            SheetSectionTitle("DISPLAY & NAVIGATION")
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                SheetFilterPill(
                    label = "Horizontal Rows",
                    selected = layoutMode == LibraryLayoutMode.HORIZONTAL,
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Rounded.ViewAgenda,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                        )
                    },
                    onClick = { onLayoutModeSelected(LibraryLayoutMode.HORIZONTAL) },
                    modifier = Modifier.weight(1f),
                )
                SheetFilterPill(
                    label = "Vertical Grid",
                    selected = layoutMode == LibraryLayoutMode.VERTICAL,
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Rounded.GridView,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                        )
                    },
                    onClick = { onLayoutModeSelected(LibraryLayoutMode.VERTICAL) },
                    modifier = Modifier.weight(1f),
                )
            }

            if (sourceMode == LibrarySourceMode.LOCAL) {
                Text(
                    text = "Category Navigation Bar Position",
                    style = MaterialTheme.typography.labelMedium,
                    color = tokens.colors.textSecondary,
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    SheetFilterPill(
                        label = "Top",
                        selected = categoryNavPosition == LibraryCategoryNavPosition.TOP,
                        onClick = { onCategoryNavPositionSelected(LibraryCategoryNavPosition.TOP) },
                        modifier = Modifier.weight(1f),
                    )
                    SheetFilterPill(
                        label = "Bottom",
                        selected = categoryNavPosition == LibraryCategoryNavPosition.BOTTOM,
                        onClick = { onCategoryNavPositionSelected(LibraryCategoryNavPosition.BOTTOM) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }

            // 3. Remote Tracker Section selector (when in remote tracking source mode)
            if (sourceMode.isRemoteTrackingSource && verticalProjection.availableSections.size > 1) {
                HorizontalDivider(color = tokens.colors.borderSubtle)
                SheetSectionTitle(stringResource(Res.string.library_filter_list))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    verticalProjection.availableSections.forEach { section ->
                        SheetFilterPill(
                            label = localizedLibrarySectionTitle(section.type, section.displayTitle),
                            selected = section.type == verticalProjection.selectedSectionKey,
                            onClick = { onSectionSelected(section.type) },
                        )
                    }
                }
            }

            // 4. Watched Filter
            HorizontalDivider(color = tokens.colors.borderSubtle)
            SheetSectionTitle(stringResource(Res.string.library_filter_watched))
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                LibraryWatchedFilter.entries.forEach { filter ->
                    SheetFilterPill(
                        label = sheetWatchedLabel(filter),
                        selected = watchedFilter == filter,
                        onClick = { onWatchedFilterSelected(filter) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }

            // 5. Media Type Filter
            if (verticalProjection.availableTypes.isNotEmpty()) {
                HorizontalDivider(color = tokens.colors.borderSubtle)
                SheetSectionTitle(stringResource(Res.string.library_filter_type))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    SheetFilterPill(
                        label = "$allTypesLabel (${verticalProjection.allTypesCount})",
                        selected = verticalProjection.selectedType == null,
                        onClick = { onTypeSelected(null) },
                    )
                    verticalProjection.availableTypes.forEach { type ->
                        val count = verticalProjection.typeCounts[type] ?: 0
                        SheetFilterPill(
                            label = "${localizedMediaTypeLabel(type)} ($count)",
                            selected = verticalProjection.selectedType == type,
                            onClick = { onTypeSelected(type) },
                        )
                    }
                }
            }

            // 6. Genre Filter
            if (verticalProjection.availableGenres.isNotEmpty()) {
                HorizontalDivider(color = tokens.colors.borderSubtle)
                SheetSectionTitle(stringResource(Res.string.library_filter_genre))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                ) {
                    SheetFilterPill(
                        label = allLabel,
                        selected = verticalProjection.selectedGenre == null,
                        onClick = { onGenreSelected(null) },
                    )
                    verticalProjection.availableGenres.forEach { option ->
                        SheetFilterPill(
                            label = "${option.key} (${option.count})",
                            selected = verticalProjection.selectedGenre == option.key,
                            onClick = { onGenreSelected(option.key) },
                        )
                    }
                }
            }

            // 7. Release Year Filter
            if (verticalProjection.availableYears.isNotEmpty()) {
                HorizontalDivider(color = tokens.colors.borderSubtle)
                SheetSectionTitle(stringResource(Res.string.library_filter_year))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                ) {
                    SheetFilterPill(
                        label = allLabel,
                        selected = verticalProjection.selectedYear == null,
                        onClick = { onYearSelected(null) },
                    )
                    verticalProjection.availableYears.forEach { option ->
                        SheetFilterPill(
                            label = "${option.key} (${option.count})",
                            selected = verticalProjection.selectedYear == option.key,
                            onClick = { onYearSelected(option.key) },
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(4.dp))
            Button(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(NuvioTokens.Radius.lg),
                colors = ButtonDefaults.buttonColors(
                    containerColor = tokens.colors.accent,
                    contentColor = tokens.colors.onAccent,
                ),
            ) {
                Icon(Icons.Rounded.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Apply & Close", fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
private fun SheetSectionTitle(title: String) {
    val tokens = MaterialTheme.nuvio
    Text(
        text = title.uppercase(),
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.Bold,
        color = tokens.colors.textMuted,
    )
}

@Composable
private fun SheetFilterPill(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    leadingIcon: (@Composable () -> Unit)? = null,
) {
    val tokens = MaterialTheme.nuvio
    val shape = RoundedCornerShape(NuvioTokens.Radius.full)
    Surface(
        shape = shape,
        color = if (selected) tokens.colors.accent.copy(alpha = 0.20f) else tokens.colors.surfaceCard,
        border = BorderStroke(
            width = if (selected) 1.5.dp else 1.dp,
            color = if (selected) tokens.colors.accent else tokens.colors.borderSubtle,
        ),
        modifier = modifier
            .clip(shape)
            .clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leadingIcon != null) {
                leadingIcon()
                Spacer(modifier = Modifier.width(6.dp))
            }
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                color = if (selected) tokens.colors.accent else tokens.colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun sheetSortLabel(option: LibrarySortOption): String =
    when (option) {
        LibrarySortOption.DEFAULT -> stringResource(Res.string.library_sort_provider_order)
        LibrarySortOption.ADDED_DESC -> stringResource(Res.string.library_sort_added_desc)
        LibrarySortOption.ADDED_ASC -> stringResource(Res.string.library_sort_added_asc)
        LibrarySortOption.RELEASED_DESC -> stringResource(Res.string.library_sort_released_desc)
        LibrarySortOption.RELEASED_ASC -> stringResource(Res.string.library_sort_released_asc)
        LibrarySortOption.TITLE_ASC -> stringResource(Res.string.library_sort_title_asc)
        LibrarySortOption.TITLE_DESC -> stringResource(Res.string.library_sort_title_desc)
    }

@Composable
private fun sheetWatchedLabel(filter: LibraryWatchedFilter): String =
    when (filter) {
        LibraryWatchedFilter.ALL -> stringResource(Res.string.library_watched_filter_all)
        LibraryWatchedFilter.WATCHED -> stringResource(Res.string.library_watched_filter_watched)
        LibraryWatchedFilter.UNWATCHED -> stringResource(Res.string.library_watched_filter_unwatched)
    }
"""


def _patch_library_ui_controls(root: Path) -> None:
    # 1. Add LibraryCategoryNavPosition to LibraryDisplaySettings.kt
    display_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryDisplaySettings.kt"
    _replace_once(
        display_kt,
        r"""enum class LibraryLayoutMode {
    HORIZONTAL,
    VERTICAL,
}""",
        r"""enum class LibraryLayoutMode {
    HORIZONTAL,
    VERTICAL,
}

enum class LibraryCategoryNavPosition {
    TOP,
    BOTTOM,
}""",
        "LibraryCategoryNavPosition enum",
    )
    _replace_once(
        display_kt,
        r"""data class LibraryDisplaySettingsUiState(
    val layoutMode: LibraryLayoutMode = LibraryLayoutMode.HORIZONTAL,
    val sortOption: LibrarySortOption = LibrarySortOption.DEFAULT,
    val viewMode: LibraryViewMode = LibraryViewMode.Saved,
    val selectedSectionKey: String? = null,
    val selectedType: String? = null,
)""",
        r"""data class LibraryDisplaySettingsUiState(
    val layoutMode: LibraryLayoutMode = LibraryLayoutMode.HORIZONTAL,
    val categoryNavPosition: LibraryCategoryNavPosition = LibraryCategoryNavPosition.TOP,
    val sortOption: LibrarySortOption = LibrarySortOption.DEFAULT,
    val viewMode: LibraryViewMode = LibraryViewMode.Saved,
    val selectedSectionKey: String? = null,
    val selectedType: String? = null,
)""",
        "LibraryDisplaySettingsUiState categoryNavPosition",
    )
    _replace_once(
        display_kt,
        r"""    fun setLayoutMode(layoutMode: LibraryLayoutMode) {
        ensureLoaded()
        if (_uiState.value.layoutMode == layoutMode) return
        _uiState.value = _uiState.value.copy(layoutMode = layoutMode)
        persist()
    }""",
        r"""    fun setLayoutMode(layoutMode: LibraryLayoutMode) {
        ensureLoaded()
        if (_uiState.value.layoutMode == layoutMode) return
        _uiState.value = _uiState.value.copy(layoutMode = layoutMode)
        persist()
    }

    fun setCategoryNavPosition(position: LibraryCategoryNavPosition) {
        ensureLoaded()
        if (_uiState.value.categoryNavPosition == position) return
        _uiState.value = _uiState.value.copy(categoryNavPosition = position)
        persist()
    }""",
        "LibraryDisplaySettingsRepository.setCategoryNavPosition",
    )
    _replace_once(
        display_kt,
        r"""internal fun encodeLibraryDisplaySettings(state: LibraryDisplaySettingsUiState): String =
    LibraryDisplaySettingsJson.encodeToString(
        StoredLibraryDisplaySettings(
            layoutMode = state.layoutMode.name,
            sortOption = state.sortOption.name,
            viewMode = state.viewMode.name,
            selectedSectionKey = state.selectedSectionKey,
            selectedType = state.selectedType,
        ),
    )

internal fun decodeLibraryDisplaySettings(payload: String?): LibraryDisplaySettingsUiState {
    val stored = payload
        ?.takeIf { it.isNotBlank() }
        ?.let { value ->
            runCatching {
                LibraryDisplaySettingsJson.decodeFromString<StoredLibraryDisplaySettings>(value)
            }.getOrNull()
        }
    return LibraryDisplaySettingsUiState(
        layoutMode = stored?.layoutMode
            ?.let { value -> LibraryLayoutMode.entries.firstOrNull { it.name == value } }
            ?: LibraryLayoutMode.HORIZONTAL,
        sortOption = stored?.sortOption""",
        r"""internal fun encodeLibraryDisplaySettings(state: LibraryDisplaySettingsUiState): String =
    LibraryDisplaySettingsJson.encodeToString(
        StoredLibraryDisplaySettings(
            layoutMode = state.layoutMode.name,
            categoryNavPosition = state.categoryNavPosition.name,
            sortOption = state.sortOption.name,
            viewMode = state.viewMode.name,
            selectedSectionKey = state.selectedSectionKey,
            selectedType = state.selectedType,
        ),
    )

internal fun decodeLibraryDisplaySettings(payload: String?): LibraryDisplaySettingsUiState {
    val stored = payload
        ?.takeIf { it.isNotBlank() }
        ?.let { value ->
            runCatching {
                LibraryDisplaySettingsJson.decodeFromString<StoredLibraryDisplaySettings>(value)
            }.getOrNull()
        }
    return LibraryDisplaySettingsUiState(
        layoutMode = stored?.layoutMode
            ?.let { value -> LibraryLayoutMode.entries.firstOrNull { it.name == value } }
            ?: LibraryLayoutMode.HORIZONTAL,
        categoryNavPosition = stored?.categoryNavPosition
            ?.let { value -> LibraryCategoryNavPosition.entries.firstOrNull { it.name == value } }
            ?: LibraryCategoryNavPosition.TOP,
        sortOption = stored?.sortOption""",
        "encode/decode categoryNavPosition",
    )
    _replace_once(
        display_kt,
        r"""@Serializable
private data class StoredLibraryDisplaySettings(
    @SerialName("layout_mode") val layoutMode: String = LibraryLayoutMode.HORIZONTAL.name,""",
        r"""@Serializable
private data class StoredLibraryDisplaySettings(
    @SerialName("layout_mode") val layoutMode: String = LibraryLayoutMode.HORIZONTAL.name,
    @SerialName("category_nav_position") val categoryNavPosition: String = LibraryCategoryNavPosition.TOP.name,""",
        "StoredLibraryDisplaySettings category_nav_position field",
    )

    # 2. Write LibrarySortFilterSheet.kt
    sheet_path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibrarySortFilterSheet.kt"
    sheet_path.write_text(LIBRARY_SORT_FILTER_SHEET_KT, encoding="utf-8")

    # 3. Patch LibraryScreen.kt:
    #    - Remove ONLY top-right LibraryDownloadsButton
    #    - Render LibraryCategoryNavBar at TOP or BOTTOM based on displaySettings.categoryNavPosition
    #    - Remove on-screen stickyHeader { LibrarySavedControls(...) }
    #    - Add Library-only bottom-right LibrarySortFilterFab + LibrarySortFilterBottomSheet
    screen_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryScreen.kt"
    _replace_once(
        screen_kt,
        r"""                    if (onDownloadsClick != null) {
                        LibraryDownloadsButton(onClick = onDownloadsClick)
                    }
                }
                if (sourceMode == LibraryViewMode.Saved && uiState.sourceMode == LibrarySourceMode.LOCAL) {
                    Spacer(modifier = Modifier.height(6.dp))
                    LibraryCategoryNavBar(
                        selectedTabKey = selectedLocalCategoryKey,
                        categoryCounts = localCategoryCounts,
                        totalUniqueCount = uiState.items.size,
                        onTabSelected = { nextKey ->
                            selectedLocalCategoryKey = nextKey
                            selectedLibraryType = null
                        },
                    )
                }""",
        r"""                }
                if (
                    sourceMode == LibraryViewMode.Saved &&
                    uiState.sourceMode == LibrarySourceMode.LOCAL &&
                    displaySettings.categoryNavPosition == LibraryCategoryNavPosition.TOP
                ) {
                    Spacer(modifier = Modifier.height(6.dp))
                    LibraryCategoryNavBar(
                        selectedTabKey = selectedLocalCategoryKey,
                        categoryCounts = localCategoryCounts,
                        totalUniqueCount = uiState.items.size,
                        onTabSelected = { nextKey ->
                            selectedLocalCategoryKey = nextKey
                            selectedLibraryType = null
                        },
                    )
                }""",
        "LibraryScreen remove top-right LibraryDownloadsButton + conditional TOP category bar",
    )

    _replace_once(
        screen_kt,
        r"""                        stickyHeader(
                            key = "library-saved-controls:${uiState.sourceMode}:" +
                                "$effectiveLayoutForSaved:$effectiveSortOption:$selectedLocalCategoryKey",
                        ) {
                            Box(modifier = Modifier.fillMaxWidth()) {
                                Box(
                                    modifier = Modifier
                                        .matchParentSize()
                                        .appBackgroundCover(MaterialTheme.colorScheme.background)
                                        .nuvioConsumePointerEvents(),
                                )
                                LibrarySavedControls(
                                    layoutMode = effectiveLayoutForSaved,
                                    sourceMode = uiState.sourceMode,
                                    sortOption = effectiveSortOption,
                                    verticalProjection = verticalProjection,
                                    watchedFilter = libraryWatchedFilter,
                                    onSectionSelected = { sectionKey ->
                                        if (uiState.sourceMode == LibrarySourceMode.LOCAL) {
                                            selectedLocalCategoryKey = sectionKey
                                        } else {
                                            selectedLibrarySectionKey = sectionKey
                                        }
                                        selectedLibraryType = null
                                    },
                                    onTypeSelected = { type -> selectedLibraryType = type },
                                    onGenreSelected = { genre -> libraryGenre = genre },
                                    onYearSelected = { year -> libraryYear = year },
                                    onWatchedFilterSelected = { filter -> libraryWatchedFilterName = filter.name },
                                    onSortSelected = LibraryDisplaySettingsRepository::setSortOption,
                                    modifier = libraryContentTransitionModifier()
                                        .padding(horizontal = 16.dp)
                                        .padding(top = 8.dp, bottom = 14.dp),
                                )
                            }
                        }""",
        r"""                        // On-screen LibrarySavedControls replaced by the Library-only Sort & Filter FAB.""",
        "LibraryScreen remove on-screen LibrarySavedControls stickyHeader",
    )

    _replace_once(
        screen_kt,
        r"""    var showReleaseCalendar by rememberSaveable { mutableStateOf(false) }""",
        r"""    var showReleaseCalendar by rememberSaveable { mutableStateOf(false) }
    var showSortFilterSheet by rememberSaveable { mutableStateOf(false) }""",
        "LibraryScreen showSortFilterSheet state",
    )

    _replace_once(
        screen_kt,
        r"""                            LibraryLayoutMode.VERTICAL -> {
                                if (verticalProjection.entries.isEmpty()) {
                                    val selectedCategory = LocalLibraryCategory.fromKey(selectedLocalCategoryKey)
                                    item(key = "library_category_or_filter_empty") {
                                        HomeEmptyStateCard(
                                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                            title = when {
                                                savedSearchQuery.isNotBlank() -> "No matching titles"
                                                selectedCategory != null -> selectedCategory.emptyTitle
                                                else -> stringResource(Res.string.library_empty_title)
                                            },
                                            message = when {
                                                savedSearchQuery.isNotBlank() ->
                                                    "No titles matched “${savedSearchQuery.trim()}” in this view."
                                                selectedCategory != null -> selectedCategory.emptyMessage
                                                else -> stringResource(Res.string.library_empty_message)
                                            },
                                            actionLabel = if (savedSearchQuery.isNotBlank()) "Clear search" else null,
                                            onActionClick = if (savedSearchQuery.isNotBlank()) {
                                                { savedSearchQuery = "" }
                                            } else null,
                                        )
                                    }
                                } else {
                                    libraryVerticalContent(
                                        projection = verticalProjection,
                                        columns = gridColumns,
                                        releaseInfoFor = releaseInfoFor,
                                        watchedKeys = watchedUiState.watchedKeys,
                                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                        posterPattern = effectivePosterPattern,
                                        onPosterClick = onPosterClick,
                                        onPosterLongClick = onPosterLongClick,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    }""",
        r"""                            LibraryLayoutMode.VERTICAL -> {
                                if (verticalProjection.entries.isEmpty()) {
                                    val selectedCategory = LocalLibraryCategory.fromKey(selectedLocalCategoryKey)
                                    item(key = "library_category_or_filter_empty") {
                                        HomeEmptyStateCard(
                                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                            title = when {
                                                savedSearchQuery.isNotBlank() -> "No matching titles"
                                                selectedCategory != null -> selectedCategory.emptyTitle
                                                else -> stringResource(Res.string.library_empty_title)
                                            },
                                            message = when {
                                                savedSearchQuery.isNotBlank() ->
                                                    "No titles matched “${savedSearchQuery.trim()}” in this view."
                                                selectedCategory != null -> selectedCategory.emptyMessage
                                                else -> stringResource(Res.string.library_empty_message)
                                            },
                                            actionLabel = if (savedSearchQuery.isNotBlank()) "Clear search" else null,
                                            onActionClick = if (savedSearchQuery.isNotBlank()) {
                                                { savedSearchQuery = "" }
                                            } else null,
                                        )
                                    }
                                } else {
                                    libraryVerticalContent(
                                        projection = verticalProjection,
                                        columns = gridColumns,
                                        releaseInfoFor = releaseInfoFor,
                                        watchedKeys = watchedUiState.watchedKeys,
                                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                        posterPattern = effectivePosterPattern,
                                        onPosterClick = onPosterClick,
                                        onPosterLongClick = onPosterLongClick,
                                    )
                                }
                            }
                        }
                        item(key = "library_bottom_fab_clearance") {
                            Spacer(
                                modifier = Modifier.height(
                                    if (
                                        uiState.sourceMode == LibrarySourceMode.LOCAL &&
                                        displaySettings.categoryNavPosition == LibraryCategoryNavPosition.BOTTOM
                                    ) {
                                        124.dp
                                    } else {
                                        76.dp
                                    },
                                ),
                            )
                        }
                    }
                }
            }
            }

            val bottomNavOverlayPadding = if (LocalNuvioBottomNavigationOverlayPadding.current > 0.dp) {
                nuvioSafeBottomPadding()
            } else {
                0.dp
            }
            val showBottomCategoryNav = sourceMode == LibraryViewMode.Saved &&
                uiState.sourceMode == LibrarySourceMode.LOCAL &&
                displaySettings.categoryNavPosition == LibraryCategoryNavPosition.BOTTOM

            if (showBottomCategoryNav) {
                Box(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                        .appBackgroundCover(MaterialTheme.colorScheme.background, coverAbove = false)
                        .padding(top = 6.dp, bottom = bottomNavOverlayPadding + 6.dp),
                ) {
                    LibraryCategoryNavBar(
                        selectedTabKey = selectedLocalCategoryKey,
                        categoryCounts = localCategoryCounts,
                        totalUniqueCount = uiState.items.size,
                        onTabSelected = { nextKey ->
                            selectedLocalCategoryKey = nextKey
                            selectedLibraryType = null
                        },
                    )
                }
            }

            if (sourceMode == LibraryViewMode.Saved && uiState.sections.isNotEmpty()) {
                val activeFilterCount = listOf(
                    effectiveSortOption != LibrarySortOption.DEFAULT,
                    selectedLibraryType != null,
                    libraryGenre != null,
                    libraryYear != null,
                    libraryWatchedFilter != LibraryWatchedFilter.ALL,
                ).count { it }
                LibrarySortFilterFab(
                    activeFilterCount = activeFilterCount,
                    onClick = { showSortFilterSheet = true },
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(
                            end = 18.dp,
                            bottom = bottomNavOverlayPadding + (if (showBottomCategoryNav) 62.dp else 16.dp),
                        ),
                )
            }
        }
    }

    LibrarySortFilterBottomSheet(
        visible = showSortFilterSheet,
        layoutMode = effectiveLayoutForSaved,
        categoryNavPosition = displaySettings.categoryNavPosition,
        sourceMode = uiState.sourceMode,
        sortOption = effectiveSortOption,
        verticalProjection = verticalProjection,
        watchedFilter = libraryWatchedFilter,
        onLayoutModeSelected = LibraryDisplaySettingsRepository::setLayoutMode,
        onCategoryNavPositionSelected = LibraryDisplaySettingsRepository::setCategoryNavPosition,
        onSectionSelected = { sectionKey ->
            if (uiState.sourceMode == LibrarySourceMode.LOCAL) {
                selectedLocalCategoryKey = sectionKey
            } else {
                selectedLibrarySectionKey = sectionKey
            }
            selectedLibraryType = null
        },
        onTypeSelected = { type ->
            selectedLibraryType = type
            if (type != null && displaySettings.layoutMode != LibraryLayoutMode.VERTICAL) {
                LibraryDisplaySettingsRepository.setLayoutMode(LibraryLayoutMode.VERTICAL)
            }
        },
        onGenreSelected = { genre ->
            libraryGenre = genre
            if (genre != null && displaySettings.layoutMode != LibraryLayoutMode.VERTICAL) {
                LibraryDisplaySettingsRepository.setLayoutMode(LibraryLayoutMode.VERTICAL)
            }
        },
        onYearSelected = { year ->
            libraryYear = year
            if (year != null && displaySettings.layoutMode != LibraryLayoutMode.VERTICAL) {
                LibraryDisplaySettingsRepository.setLayoutMode(LibraryLayoutMode.VERTICAL)
            }
        },
        onWatchedFilterSelected = { filter ->
            libraryWatchedFilterName = filter.name
            if (filter != LibraryWatchedFilter.ALL && displaySettings.layoutMode != LibraryLayoutMode.VERTICAL) {
                LibraryDisplaySettingsRepository.setLayoutMode(LibraryLayoutMode.VERTICAL)
            }
        },
        onSortSelected = LibraryDisplaySettingsRepository::setSortOption,
        onClearFilters = {
            selectedLibraryType = null
            libraryGenre = null
            libraryYear = null
            libraryWatchedFilterName = LibraryWatchedFilter.ALL.name
            LibraryDisplaySettingsRepository.setSortOption(LibrarySortOption.DEFAULT)
        },
        onDismiss = { showSortFilterSheet = false },
    )""",
        "LibraryScreen bottom category bar + Library-only Sort & Filter FAB + Sheet",
    )


# ---------------------------------------------------------------------------
# Steps 6–9 (Phase 3.1–3.4):
# - Search History clearAll + case-insensitive dedup + cap=15
# - Search Autocomplete + CloudStream Extension Search Toggle
# - Home Screen Search entry point reusing SearchScreen
# ---------------------------------------------------------------------------

SEARCH_ENHANCEMENTS_KT = r"""package com.nuvio.app.features.search

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Extension
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.NorthWest
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioLoadingIndicator
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.nuvio
import com.nuvio.app.features.cloudstream.CloudStreamPluginItem
import com.nuvio.app.features.cloudstream.CloudStreamRepository
import com.nuvio.app.features.cloudstream.CloudStreamSearchItem
import com.nuvio.app.features.cloudstream.toMetaPreview
import com.nuvio.app.features.home.HomeCatalogSection
import com.nuvio.app.features.home.MetaPreview
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withTimeoutOrNull

data class SearchSuggestionItem(
    val text: String,
    val subtitle: String? = null,
    val isHistory: Boolean = false,
    val preview: MetaPreview? = null,
)

data class CloudStreamProviderSearchOutcome(
    val plugin: CloudStreamPluginItem,
    val items: List<CloudStreamSearchItem>,
    val errorMessage: String? = null,
)

suspend fun searchRunnableCloudStreamProviders(
    query: String,
    timeoutPerProviderMs: Long = 14_000L,
): List<CloudStreamProviderSearchOutcome> {
    val trimmed = query.trim()
    if (trimmed.isBlank()) return emptyList()
    CloudStreamRepository.initialize()
    val runnablePlugins = CloudStreamRepository.uiState.value.plugins
        .filter(CloudStreamPluginItem::isRunnable)
    if (runnablePlugins.isEmpty()) return emptyList()

    return coroutineScope {
        runnablePlugins.map { plugin ->
            async {
                val outcome = runCatching {
                    withTimeoutOrNull(timeoutPerProviderMs) {
                        CloudStreamRepository.search(
                            query = trimmed,
                            providerId = plugin.metadata.id.value,
                        ).firstOrNull()
                    }
                }.getOrElse { error ->
                    Result.failure(error)
                }
                when {
                    outcome == null -> CloudStreamProviderSearchOutcome(
                        plugin = plugin,
                        items = emptyList(),
                        errorMessage = "${plugin.metadata.name} timed out",
                    )
                    outcome.isSuccess -> {
                        val deduped = outcome.getOrDefault(emptyList())
                            .filter { it.name.isNotBlank() && it.data.isNotBlank() }
                            .distinctBy { "${it.type}:${it.data.trim().lowercase()}" }
                        CloudStreamProviderSearchOutcome(
                            plugin = plugin,
                            items = deduped,
                            errorMessage = null,
                        )
                    }
                    else -> CloudStreamProviderSearchOutcome(
                        plugin = plugin,
                        items = emptyList(),
                        errorMessage = outcome.exceptionOrNull()?.message ?: "${plugin.metadata.name} search failed",
                    )
                }
            }
        }.awaitAll()
    }
}

fun buildCloudStreamSearchSections(
    outcomes: List<CloudStreamProviderSearchOutcome>,
): List<HomeCatalogSection> {
    val seenGlobalKeys = HashSet<String>()
    return outcomes.mapNotNull { outcome ->
        if (outcome.items.isEmpty()) return@mapNotNull null
        val previews = outcome.items.mapNotNull { item ->
            val preview = item.toMetaPreview()
            val dedupKey = "${outcome.plugin.metadata.id.value}:${preview.id}"
            if (!seenGlobalKeys.add(dedupKey)) null else preview
        }
        if (previews.isEmpty()) return@mapNotNull null
        HomeCatalogSection(
            key = "cloudstream_search:${outcome.plugin.metadata.id.value}",
            title = outcome.plugin.metadata.name,
            subtitle = "CloudStream Extension",
            addonName = "${outcome.plugin.metadata.name} · CloudStream",
            type = previews.first().type,
            items = previews,
        )
    }
}

fun buildSearchAutocompleteSuggestions(
    rawQuery: String,
    recentSearches: List<String>,
    sections: List<HomeCatalogSection>,
    limit: Int = 8,
): List<SearchSuggestionItem> {
    val trimmed = rawQuery.trim()
    if (trimmed.isBlank()) return emptyList()
    val queryLower = trimmed.lowercase()
    val seen = LinkedHashSet<String>()
    val result = ArrayList<SearchSuggestionItem>(limit)

    recentSearches
        .filter { it.lowercase().contains(queryLower) && !it.equals(trimmed, ignoreCase = true) }
        .take(3)
        .forEach { historyEntry ->
            if (seen.add(historyEntry.lowercase())) {
                result += SearchSuggestionItem(
                    text = historyEntry,
                    subtitle = "Recent search",
                    isHistory = true,
                )
            }
        }

    sections.asSequence()
        .flatMap { section ->
            section.items.asSequence().map { item -> section to item }
        }
        .forEach { (section, item) ->
            if (result.size >= limit) return@forEach
            val cleanName = item.name.trim()
            if (cleanName.isBlank()) return@forEach
            if (!seen.add(cleanName.lowercase())) return@forEach
            val yearLabel = item.releaseInfo?.take(4)?.takeIf { it.all(Char::isDigit) }
            val sourceLabel = section.addonName.takeIf { it.isNotBlank() } ?: section.title
            val metaParts = listOfNotNull(
                item.type.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() },
                yearLabel,
                sourceLabel,
            )
            result += SearchSuggestionItem(
                text = cleanName,
                subtitle = metaParts.joinToString(" · "),
                isHistory = false,
                preview = item,
            )
        }

    return result
}

@Composable
internal fun SearchCloudStreamExtensionToggleRow(
    enabled: Boolean,
    runnableExtensionCount: Int,
    onToggle: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    val shape = RoundedCornerShape(NuvioTokens.Radius.lg)
    Surface(
        shape = shape,
        color = if (enabled) tokens.colors.accent.copy(alpha = 0.12f) else tokens.colors.surfaceCard,
        border = BorderStroke(
            width = 1.dp,
            color = if (enabled) tokens.colors.accent.copy(alpha = 0.5f) else tokens.colors.borderSubtle,
        ),
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .clickable { onToggle(!enabled) },
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.weight(1f),
            ) {
                Icon(
                    imageVector = Icons.Rounded.Extension,
                    contentDescription = null,
                    tint = if (enabled) tokens.colors.accent else tokens.colors.textMuted,
                    modifier = Modifier.size(18.dp),
                )
                Column {
                    Text(
                        text = "Include CloudStream Extensions",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.textPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = when {
                            !enabled -> "Off · Searching Nuvio catalogs only"
                            runnableExtensionCount == 0 -> "On · No runnable CloudStream extensions enabled"
                            runnableExtensionCount == 1 -> "On · Searching 1 enabled extension concurrently"
                            else -> "On · Searching $runnableExtensionCount enabled extensions concurrently"
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = tokens.colors.textMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Switch(
                checked = enabled,
                onCheckedChange = onToggle,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = tokens.colors.onAccent,
                    checkedTrackColor = tokens.colors.accent,
                ),
            )
        }
    }
}

@Composable
internal fun SearchAutocompleteSuggestionsCard(
    visible: Boolean,
    isLoading: Boolean,
    suggestions: List<SearchSuggestionItem>,
    errorMessage: String?,
    onSelectSuggestion: (SearchSuggestionItem) -> Unit,
    onFillQuery: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    AnimatedVisibility(
        visible = visible,
        enter = expandVertically() + fadeIn(),
        exit = shrinkVertically() + fadeOut(),
        modifier = modifier,
    ) {
        Surface(
            shape = RoundedCornerShape(NuvioTokens.Radius.lg),
            color = tokens.colors.surfaceCard,
            border = BorderStroke(1.dp, tokens.colors.borderSubtle),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "SUGGESTIONS",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = tokens.colors.textMuted,
                    )
                    if (isLoading) {
                        NuvioLoadingIndicator(modifier = Modifier.size(14.dp))
                    }
                }
                HorizontalDivider(color = tokens.colors.borderSubtle)
                when {
                    suggestions.isNotEmpty() -> {
                        suggestions.forEachIndexed { index, item ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onSelectSuggestion(item) }
                                    .padding(horizontal = 14.dp, vertical = 9.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                            ) {
                                Icon(
                                    imageVector = if (item.isHistory) Icons.Rounded.History else Icons.Rounded.Search,
                                    contentDescription = null,
                                    tint = tokens.colors.textMuted,
                                    modifier = Modifier.size(17.dp),
                                )
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = item.text,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.Medium,
                                        color = tokens.colors.textPrimary,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    item.subtitle?.takeIf { it.isNotBlank() }?.let { sub ->
                                        Text(
                                            text = sub,
                                            style = MaterialTheme.typography.labelSmall,
                                            color = tokens.colors.textMuted,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                        )
                                    }
                                }
                                IconButton(
                                    onClick = { onFillQuery(item.text) },
                                    modifier = Modifier.size(28.dp),
                                ) {
                                    Icon(
                                        imageVector = Icons.Rounded.NorthWest,
                                        contentDescription = "Fill search query",
                                        tint = tokens.colors.textMuted,
                                        modifier = Modifier.size(15.dp),
                                    )
                                }
                            }
                            if (index < suggestions.lastIndex) {
                                HorizontalDivider(color = tokens.colors.borderSubtle.copy(alpha = 0.5f))
                            }
                        }
                    }
                    isLoading -> {
                        Text(
                            text = "Finding matching titles…",
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        )
                    }
                    !errorMessage.isNullOrBlank() -> {
                        Text(
                            text = errorMessage,
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.warning,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        )
                    }
                    else -> {
                        Text(
                            text = "No instant suggestions — results appear below",
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                        )
                    }
                }
            }
        }
    }
}
"""


def _patch_search_and_home_entry(root: Path) -> None:
    # 1. Upgrade SearchHistoryRepository with clearAll(), MAX=15, case-insensitive dedup, and persisted includeCloudStreamExtensions
    history_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchHistoryRepository.kt"
    history_kt.write_text(
        r"""package com.nuvio.app.features.search

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
private data class StoredSearchPreferencesPayload(
    val recentSearches: List<String> = emptyList(),
    val includeCloudStreamExtensions: Boolean = false,
)

object SearchHistoryRepository {
    const val MAX_RECENT_SEARCHES = 15

    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    private val _uiState = MutableStateFlow<List<String>>(emptyList())
    val uiState: StateFlow<List<String>> = _uiState.asStateFlow()

    private val _enabled = MutableStateFlow(true)
    val enabled: StateFlow<Boolean> = _enabled.asStateFlow()

    private val _includeCloudStreamExtensions = MutableStateFlow(false)
    val includeCloudStreamExtensions: StateFlow<Boolean> = _includeCloudStreamExtensions.asStateFlow()

    private var hasLoaded = false
    private var recentSearches: List<String> = emptyList()

    fun ensureLoaded() {
        if (hasLoaded) return
        loadFromDisk()
    }

    fun onProfileChanged() {
        loadFromDisk()
    }

    fun setEnabled(enabled: Boolean) {
        ensureLoaded()
        if (_enabled.value == enabled) return
        _enabled.value = enabled
        SearchHistoryStorage.saveEnabled(enabled)
        publish()
    }

    fun setIncludeCloudStreamExtensions(include: Boolean) {
        ensureLoaded()
        if (_includeCloudStreamExtensions.value == include) return
        _includeCloudStreamExtensions.value = include
        persist()
    }

    fun recordSearch(query: String) {
        ensureLoaded()
        if (!_enabled.value) return
        val normalizedQuery = query.trim()
        if (normalizedQuery.length < 2) return

        val updatedSearches = applySearchHistoryEntry(
            current = recentSearches,
            query = normalizedQuery,
            limit = MAX_RECENT_SEARCHES,
        )
        if (updatedSearches == recentSearches) return

        recentSearches = updatedSearches
        publish()
        persist()
    }

    fun removeSearch(query: String) {
        ensureLoaded()
        val updatedSearches = recentSearches.filterNot { it.equals(query.trim(), ignoreCase = true) }
        if (updatedSearches == recentSearches) return

        recentSearches = updatedSearches
        publish()
        persist()
    }

    fun clearAll() {
        ensureLoaded()
        if (recentSearches.isEmpty()) return
        recentSearches = emptyList()
        publish()
        persist()
    }

    private fun loadFromDisk() {
        hasLoaded = true
        _enabled.value = SearchHistoryStorage.loadEnabled() ?: true
        val payload = SearchHistoryStorage.loadPayload().orEmpty().trim()
        if (payload.isEmpty()) {
            recentSearches = emptyList()
            _includeCloudStreamExtensions.value = false
        } else if (payload.startsWith("{")) {
            val decoded = runCatching {
                json.decodeFromString<StoredSearchPreferencesPayload>(payload)
            }.getOrDefault(StoredSearchPreferencesPayload())
            recentSearches = sanitizeSearchHistoryList(decoded.recentSearches, MAX_RECENT_SEARCHES)
            _includeCloudStreamExtensions.value = decoded.includeCloudStreamExtensions
        } else {
            // Backward-compatible migration from legacy JSON array format
            val legacyList = runCatching {
                json.decodeFromString<List<String>>(payload)
            }.getOrDefault(emptyList())
            recentSearches = sanitizeSearchHistoryList(legacyList, MAX_RECENT_SEARCHES)
            _includeCloudStreamExtensions.value = false
        }
        publish()
    }

    private fun publish() {
        _uiState.value = if (_enabled.value) recentSearches else emptyList()
    }

    private fun persist() {
        SearchHistoryStorage.savePayload(
            json.encodeToString(
                StoredSearchPreferencesPayload(
                    recentSearches = recentSearches,
                    includeCloudStreamExtensions = _includeCloudStreamExtensions.value,
                ),
            ),
        )
    }
}

internal fun sanitizeSearchHistoryList(
    entries: List<String>,
    limit: Int = SearchHistoryRepository.MAX_RECENT_SEARCHES,
): List<String> {
    val seen = HashSet<String>()
    val out = ArrayList<String>(limit)
    for (raw in entries) {
        val trimmed = raw.trim()
        if (trimmed.length < 2) continue
        if (seen.add(trimmed.lowercase())) {
            out += trimmed
            if (out.size >= limit) break
        }
    }
    return out
}

internal fun applySearchHistoryEntry(
    current: List<String>,
    query: String,
    limit: Int,
): List<String> {
    val trimmed = query.trim()
    if (trimmed.length < 2) return sanitizeSearchHistoryList(current, limit)
    return buildList {
        add(trimmed)
        current.forEach { existing ->
            val clean = existing.trim()
            if (clean.length >= 2 && !clean.equals(trimmed, ignoreCase = true) && size < limit) {
                add(clean)
            }
        }
    }
}
""",
        encoding="utf-8",
    )

    # 2. Write SearchEnhancements.kt
    (root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchEnhancements.kt").write_text(
        SEARCH_ENHANCEMENTS_KT,
        encoding="utf-8",
    )

    # 3. Patch SearchRepository.kt to support includeCloudStreamExtensions concurrently & non-blockingly
    search_repo_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchRepository.kt"
    _replace_once(
        search_repo_kt,
        "import com.nuvio.app.features.home.MetaPreview",
        "import com.nuvio.app.features.home.MetaPreview\nimport com.nuvio.app.features.cloudstream.CloudStreamPluginItem\nimport com.nuvio.app.features.cloudstream.CloudStreamRepository",
        "SearchRepository CloudStream imports",
    )
    _replace_once(
        search_repo_kt,
        r"""    fun search(
        query: String,
        addons: List<ManagedAddon>,
        forceRefresh: Boolean = false,
    ) {""",
        r"""    fun search(
        query: String,
        addons: List<ManagedAddon>,
        forceRefresh: Boolean = false,
        includeCloudStreamExtensions: Boolean = SearchHistoryRepository.includeCloudStreamExtensions.value,
    ) {""",
        "SearchRepository.search includeCloudStreamExtensions param",
    )
    _replace_once(
        search_repo_kt,
        r"""        val activeAddons = enabledAddons.filter { it.manifest != null }
        val serverSearches = ServerCatalog.searchTargets()
        if (activeAddons.isEmpty() && serverSearches.isEmpty()) {""",
        r"""        val activeAddons = enabledAddons.filter { it.manifest != null }
        val serverSearches = ServerCatalog.searchTargets()
        val runnableCloudPlugins = if (includeCloudStreamExtensions) {
            CloudStreamRepository.initialize()
            CloudStreamRepository.uiState.value.plugins.filter(CloudStreamPluginItem::isRunnable)
        } else {
            emptyList()
        }
        if (activeAddons.isEmpty() && serverSearches.isEmpty() && runnableCloudPlugins.isEmpty()) {""",
        "SearchRepository allow CloudStream-only search when enabled",
    )
    _replace_once(
        search_repo_kt,
        r"""        val requests = buildSearchRequests(
            addons = activeAddons,
            query = normalizedQuery,
        )
        if (requests.isEmpty() && serverSearches.isEmpty()) {""",
        r"""        val requests = buildSearchRequests(
            addons = activeAddons,
            query = normalizedQuery,
        )
        if (requests.isEmpty() && serverSearches.isEmpty() && runnableCloudPlugins.isEmpty()) {""",
        "SearchRepository allow CloudStream-only catalog list",
    )
    _replace_once(
        search_repo_kt,
        r"""            serverSearches.forEach { ref ->
                append("|server:${ref.connection.id}:${ref.kind.contentType}:")
                append(ref.connection.selectedLibraries(ref.kind).joinToString(",") { it.id })
            }
        }
        val loaders: List<suspend () -> HomeCatalogSection> =
            requests.map { request -> suspend { request.toSection(forceRefresh = forceRefresh) } } +
                serverSearches.map { ref ->
                    suspend {
                        ServerCatalog.searchSection(ref, normalizedQuery).also { section ->
                            require(section.items.isNotEmpty()) {
                                getString(Res.string.search_error_no_results_for_catalog, section.title)
                            }
                        }
                    }
                }""",
        r"""            serverSearches.forEach { ref ->
                append("|server:${ref.connection.id}:${ref.kind.contentType}:")
                append(ref.connection.selectedLibraries(ref.kind).joinToString(",") { it.id })
            }
            append("|csExt=$includeCloudStreamExtensions:")
            append(runnableCloudPlugins.joinToString(",") { it.metadata.id.value })
        }
        val loaders: List<suspend () -> HomeCatalogSection> =
            requests.map { request -> suspend { request.toSection(forceRefresh = forceRefresh) } } +
                serverSearches.map { ref ->
                    suspend {
                        ServerCatalog.searchSection(ref, normalizedQuery).also { section ->
                            require(section.items.isNotEmpty()) {
                                getString(Res.string.search_error_no_results_for_catalog, section.title)
                            }
                        }
                    }
                } +
                runnableCloudPlugins.map { plugin ->
                    suspend {
                        val outcomes = searchRunnableCloudStreamProviders(
                            query = normalizedQuery,
                        ).filter { it.plugin.metadata.id.value == plugin.metadata.id.value }
                        val section = buildCloudStreamSearchSections(outcomes).firstOrNull()
                        requireNotNull(section) {
                            outcomes.firstOrNull()?.errorMessage ?: "No CloudStream matches in ${plugin.metadata.name}"
                        }
                    }
                }""",
        "SearchRepository concurrent CloudStream loaders when toggle enabled",
    )

    #Wait: notice above `runnableCloudPlugins.map { plugin -> searchRunnableCloudStreamProviders(...) }` would call all providers N times!
    # Let's make each plugin loader call ONLY `CloudStreamRepository.search(query = normalizedQuery, providerId = plugin.metadata.id.value)` directly!
    search_repo_text = search_repo_kt.read_text(encoding="utf-8")
    search_repo_text = search_repo_text.replace(
        r"""                runnableCloudPlugins.map { plugin ->
                    suspend {
                        val outcomes = searchRunnableCloudStreamProviders(
                            query = normalizedQuery,
                        ).filter { it.plugin.metadata.id.value == plugin.metadata.id.value }
                        val section = buildCloudStreamSearchSections(outcomes).firstOrNull()
                        requireNotNull(section) {
                            outcomes.firstOrNull()?.errorMessage ?: "No CloudStream matches in ${plugin.metadata.name}"
                        }
                    }
                }""",
        r"""                runnableCloudPlugins.map { plugin ->
                    suspend {
                        val singleResult = kotlinx.coroutines.withTimeoutOrNull(14_000L) {
                            CloudStreamRepository.search(
                                query = normalizedQuery,
                                providerId = plugin.metadata.id.value,
                            ).firstOrNull()
                        } ?: Result.failure(IllegalStateException("${plugin.metadata.name} timed out"))
                        val items = singleResult.getOrThrow()
                            .filter { it.name.isNotBlank() && it.data.isNotBlank() }
                            .distinctBy { "${it.type}:${it.data.trim().lowercase()}" }
                        val section = buildCloudStreamSearchSections(
                            listOf(
                                CloudStreamProviderSearchOutcome(
                                    plugin = plugin,
                                    items = items,
                                ),
                            ),
                        ).firstOrNull()
                        requireNotNull(section) {
                            "No CloudStream matches in ${plugin.metadata.name}"
                        }
                    }
                }""",
    )
    search_repo_kt.write_text(search_repo_text, encoding="utf-8")

    # 4. Patch SearchScreen.kt:
    #    - Observe includeCloudStreamExtensions + runnable CloudStream plugin count
    #    - Faster 240ms debounce + live autocomplete panel while focused & typing
    #    - CloudStream Extension Search Toggle row
    #    - Clear all button in SearchRecentSection
    search_screen_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchScreen.kt"
    _replace_once(
        search_screen_kt,
        "import com.nuvio.app.features.home.MetaPreview",
        "import com.nuvio.app.features.home.MetaPreview\nimport com.nuvio.app.features.cloudstream.CloudStreamPluginItem\nimport com.nuvio.app.features.cloudstream.CloudStreamRepository",
        "SearchScreen CloudStream imports",
    )
    _replace_once(
        search_screen_kt,
        r"""    LaunchedEffect(Unit) {
        AddonRepository.initialize()
        WatchedRepository.ensureLoaded()
        SearchHistoryRepository.ensureLoaded()
    }

    val addonsUiState by AddonRepository.uiState.collectAsStateWithLifecycle()
    val uiState by SearchRepository.uiState.collectAsStateWithLifecycle()
    val discoverUiState by SearchRepository.discoverUiState.collectAsStateWithLifecycle()
    val homeCatalogSettingsUiState by remember {
        HomeCatalogSettingsRepository.snapshot()
        HomeCatalogSettingsRepository.uiState
    }.collectAsStateWithLifecycle()
    val recentSearches by SearchHistoryRepository.uiState.collectAsStateWithLifecycle()""",
        r"""    LaunchedEffect(Unit) {
        AddonRepository.initialize()
        WatchedRepository.ensureLoaded()
        SearchHistoryRepository.ensureLoaded()
        CloudStreamRepository.initialize()
    }

    val addonsUiState by AddonRepository.uiState.collectAsStateWithLifecycle()
    val uiState by SearchRepository.uiState.collectAsStateWithLifecycle()
    val discoverUiState by SearchRepository.discoverUiState.collectAsStateWithLifecycle()
    val homeCatalogSettingsUiState by remember {
        HomeCatalogSettingsRepository.snapshot()
        HomeCatalogSettingsRepository.uiState
    }.collectAsStateWithLifecycle()
    val recentSearches by SearchHistoryRepository.uiState.collectAsStateWithLifecycle()
    val includeCloudStreamExtensions by SearchHistoryRepository.includeCloudStreamExtensions.collectAsStateWithLifecycle()
    val cloudStreamUiState by CloudStreamRepository.uiState.collectAsStateWithLifecycle()
    val runnableCloudStreamCount = remember(cloudStreamUiState.plugins) {
        cloudStreamUiState.plugins.count(CloudStreamPluginItem::isRunnable)
    }""",
        "SearchScreen state flows for CloudStream search toggle",
    )
    _replace_once(
        search_screen_kt,
        r"""    ScreenActivityEffect(query, addonRefreshKey, homeCatalogSettingsUiState.hideUnreleasedContent) { screenActive ->
        if (!screenActive) return@ScreenActivityEffect
        val normalizedQuery = query.trim()
        if (normalizedQuery.isBlank()) {
            lastRequestedQuery = null
            SearchRepository.clear()
        } else {
            delay(350)
            lastRequestedQuery = normalizedQuery
            SearchRepository.search(
                query = normalizedQuery,
                addons = addonsUiState.addons,
            )
        }
    }""",
        r"""    ScreenActivityEffect(
        query,
        addonRefreshKey,
        homeCatalogSettingsUiState.hideUnreleasedContent,
        includeCloudStreamExtensions,
        cloudStreamUiState.registryRevision,
    ) { screenActive ->
        if (!screenActive) return@ScreenActivityEffect
        val normalizedQuery = query.trim()
        if (normalizedQuery.isBlank()) {
            lastRequestedQuery = null
            SearchRepository.clear()
        } else {
            delay(240)
            lastRequestedQuery = normalizedQuery
            SearchRepository.search(
                query = normalizedQuery,
                addons = addonsUiState.addons,
                includeCloudStreamExtensions = includeCloudStreamExtensions,
            )
        }
    }""",
        "SearchScreen debounced search with includeCloudStreamExtensions",
    )
    _replace_once(
        search_screen_kt,
        r"""                            trailingContent = if (query.isNotBlank()) {
                                {
                                    IconButton(onClick = { query = "" }) {
                                        Icon(
                                            imageVector = Icons.Rounded.Close,
                                            contentDescription = stringResource(Res.string.compose_search_clear),
                                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                            } else {
                                null
                            },
                        )
                    }
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(14.dp))""",
        r"""                            trailingContent = if (query.isNotBlank()) {
                                {
                                    IconButton(onClick = { query = "" }) {
                                        Icon(
                                            imageVector = Icons.Rounded.Close,
                                            contentDescription = stringResource(Res.string.compose_search_clear),
                                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                            } else {
                                null
                            },
                        )
                    }
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
                    SearchCloudStreamExtensionToggleRow(
                        enabled = includeCloudStreamExtensions,
                        runnableExtensionCount = runnableCloudStreamCount,
                        onToggle = SearchHistoryRepository::setIncludeCloudStreamExtensions,
                        modifier = Modifier.padding(horizontal = 16.dp),
                    )
                    val autocompleteSuggestions = remember(query, recentSearches, uiState.sections) {
                        buildSearchAutocompleteSuggestions(
                            rawQuery = query,
                            recentSearches = recentSearches,
                            sections = uiState.sections,
                        )
                    }
                    val trimmedForAutocomplete = query.trim()
                    val autocompleteLoading = trimmedForAutocomplete.length >= 2 &&
                        (lastRequestedQuery != trimmedForAutocomplete || uiState.isLoading)
                    SearchAutocompleteSuggestionsCard(
                        visible = isSearchFocused && trimmedForAutocomplete.length >= 2,
                        isLoading = autocompleteLoading,
                        suggestions = autocompleteSuggestions,
                        errorMessage = if (uiState.emptyStateReason == SearchEmptyStateReason.RequestFailed) {
                            uiState.errorMessage ?: "Network unavailable — check connection"
                        } else null,
                        onSelectSuggestion = { suggestion ->
                            query = suggestion.text
                            SearchHistoryRepository.recordSearch(suggestion.text)
                            isSearchFocused = false
                            suggestion.preview?.let { preview -> onPosterClick?.invoke(preview) }
                        },
                        onFillQuery = { text ->
                            query = text
                        },
                        modifier = Modifier
                            .padding(horizontal = 16.dp)
                            .padding(top = 8.dp),
                    )
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(10.dp))""",
        "SearchScreen CloudStream toggle + live Autocomplete panel",
    )
    _replace_once(
        search_screen_kt,
        r"""                    if (isSearchFocused && recentSearches.isNotEmpty()) {
                        item(key = "recent_searches") {
                            SearchRecentSection(
                                recentSearches = recentSearches,
                                onSearchPress = { recentQuery -> query = recentQuery },
                                onRemoveSearch = SearchHistoryRepository::removeSearch,
                            )
                        }
                    }""",
        r"""                    if ((isSearchFocused || isSearchVisible) && recentSearches.isNotEmpty()) {
                        item(key = "recent_searches") {
                            SearchRecentSection(
                                recentSearches = recentSearches,
                                onSearchPress = { recentQuery ->
                                    query = recentQuery
                                    SearchHistoryRepository.recordSearch(recentQuery)
                                },
                                onRemoveSearch = SearchHistoryRepository::removeSearch,
                                onClearAll = SearchHistoryRepository::clearAll,
                            )
                        }
                    }""",
        "SearchScreen pass onClearAll to SearchRecentSection",
    )
    _replace_once(
        search_screen_kt,
        r"""                                            } else {
                                                SearchRepository.search(
                                                    query = normalizedQuery,
                                                    addons = addonsUiState.addons,
                                                    forceRefresh = true,
                                                )
                                            }""",
        r"""                                            } else {
                                                SearchRepository.search(
                                                    query = normalizedQuery,
                                                    addons = addonsUiState.addons,
                                                    forceRefresh = true,
                                                    includeCloudStreamExtensions = includeCloudStreamExtensions,
                                                )
                                            }""",
        "SearchScreen retry preserve includeCloudStreamExtensions",
    )
    _replace_once(
        search_screen_kt,
        r"""@Composable
private fun SearchRecentSection(
    recentSearches: List<String>,
    onSearchPress: (String) -> Unit,
    onRemoveSearch: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(
            text = stringResource(Res.string.compose_search_recent_searches),
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
            color = MaterialTheme.colorScheme.onBackground,
        )
        Spacer(modifier = Modifier.height(4.dp))""",
        r"""@Composable
private fun SearchRecentSection(
    recentSearches: List<String>,
    onSearchPress: (String) -> Unit,
    onRemoveSearch: (String) -> Unit,
    onClearAll: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(Res.string.compose_search_recent_searches),
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onBackground,
            )
            if (onClearAll != null && recentSearches.isNotEmpty()) {
                Text(
                    text = "Clear all",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable(onClick = onClearAll)
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                )
            }
        }
        Spacer(modifier = Modifier.height(4.dp))""",
        "SearchRecentSection Clear all button",
    )

    # 5. Wire Home Screen Search entry point (Phase 3.4) -> switches to Search tab & auto-focuses Search input!
    shell_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/AppShellComponents.kt"
    _replace_once(
        shell_kt,
        "    val onCatalogClick: ((HomeCatalogSection) -> Unit)? = null,",
        "    val onHomeSearchClick: (() -> Unit)? = null,\n    val onCatalogClick: ((HomeCatalogSection) -> Unit)? = null,",
        "AppTabActions onHomeSearchClick",
    )
    _replace_once(
        shell_kt,
        r"""                        HomeScreen(
                            modifier = Modifier.fillMaxSize(),
                            animateCollectionGifs = state.animateHomeCollectionGifs,
                            scrollToTopRequests = requests.homeScrollToTopRequests,
                            onCatalogClick = actions.onCatalogClick,""",
        r"""                        HomeScreen(
                            modifier = Modifier.fillMaxSize(),
                            animateCollectionGifs = state.animateHomeCollectionGifs,
                            scrollToTopRequests = requests.homeScrollToTopRequests,
                            onSearchClick = actions.onHomeSearchClick,
                            onCatalogClick = actions.onCatalogClick,""",
        "AppShellComponents pass onHomeSearchClick to HomeScreen",
    )

    main_content_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"
    _replace_once(
        main_content_kt,
        r"""                            AppTabActions(
                                onCatalogClick = onCatalogClick,""",
        r"""                            AppTabActions(
                                onHomeSearchClick = {
                                    selectedTab = AppScreenTab.Search
                                    searchFocusRequestCount++
                                },
                                onCatalogClick = onCatalogClick,""",
        "MainAppContent wire onHomeSearchClick to shared SearchScreen",
    )

    home_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/home/HomeScreen.kt"
    _replace_once(
        home_kt,
        "import androidx.compose.material.icons.rounded.PlayArrow",
        "import androidx.compose.material.icons.rounded.PlayArrow\nimport androidx.compose.material.icons.rounded.Search\nimport androidx.compose.foundation.layout.statusBarsPadding",
        "HomeScreen Search icon import",
    )
    _replace_once(
        home_kt,
        r"""fun HomeScreen(
    modifier: Modifier = Modifier,
    animateCollectionGifs: Boolean = true,
    scrollToTopRequests: Flow<Unit> = emptyFlow(),
    onCatalogClick: ((HomeCatalogSection) -> Unit)? = null,""",
        r"""fun HomeScreen(
    modifier: Modifier = Modifier,
    animateCollectionGifs: Boolean = true,
    scrollToTopRequests: Flow<Unit> = emptyFlow(),
    onSearchClick: (() -> Unit)? = null,
    onCatalogClick: ((HomeCatalogSection) -> Unit)? = null,""",
        "HomeScreen onSearchClick parameter",
    )
    _replace_once(
        home_kt,
        r"""        val hasDiscoveryProviders = runnableCloudStreamProviders.isNotEmpty()""",
        r"""        if (onSearchClick != null) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .statusBarsPadding()
                    .padding(top = 10.dp, end = 16.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.84f))
                        .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.55f), CircleShape)
                        .clickable(onClick = onSearchClick),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Search,
                        contentDescription = "Search movies, series, and extensions",
                        tint = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.size(21.dp),
                    )
                }
            }
        }

        val hasDiscoveryProviders = runnableCloudStreamProviders.isNotEmpty()""",
        "HomeScreen top-right Search button reusing shared SearchScreen",
    )


def apply_v119_library_search_patch(root: Path) -> None:
    print("  -> [v1.19 mod1] Applying signing, Library fixes/FAB/nav, and unified Search...")
    _patch_signing_and_version(root)
    _patch_library_persistence_and_duplicates(root)
    _patch_library_ui_controls(root)
    _patch_search_and_home_entry(root)
    print("  -> [v1.19 mod1] Completed successfully.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v119_library_search_patch.py <source_dir>")
    apply_v119_library_search_patch(Path(sys.argv[1]).resolve())
