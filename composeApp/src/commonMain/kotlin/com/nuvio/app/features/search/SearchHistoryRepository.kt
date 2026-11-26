package com.nuvio.app.features.search

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
