package com.nuvio.app.features.search

import co.touchlab.kermit.Logger
import com.nuvio.app.features.addons.httpGetText
import com.nuvio.app.features.tmdb.TmdbSettingsRepository
import com.nuvio.app.features.tmdb.buildTmdbUrl
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * CloudStream-style live search suggestions: debounced TMDB multi-search titles shown while
 * typing, cleared the moment a search is executed, a suggestion is picked, or focus is lost.
 */
object SearchSuggestionRepository {
    private val log = Logger.withTag("SearchSuggestionRepository")
    private val json = Json { ignoreUnknownKeys = true }
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val _suggestions = MutableStateFlow<List<String>>(emptyList())
    val suggestions: StateFlow<List<String>> = _suggestions.asStateFlow()

    private var fetchJob: Job? = null
    private var lastQuery: String = ""

    fun fetchSuggestions(query: String) {
        val normalized = query.trim()
        if (normalized.length < 2) {
            clear()
            return
        }
        if (normalized.equals(lastQuery, ignoreCase = true) && _suggestions.value.isNotEmpty()) return
        lastQuery = normalized
        fetchJob?.cancel()
        fetchJob = scope.launch {
            delay(300) // debounce while the user is still typing
            val results = runCatching { fetchTmdbSuggestions(normalized) }
                .onFailure { error ->
                    log.w { "Suggestion fetch failed: ${error.message}" }
                }
                .getOrDefault(emptyList())
            if (normalized != lastQuery) return@launch
            _suggestions.value = results
        }
    }

    fun clear() {
        fetchJob?.cancel()
        fetchJob = null
        lastQuery = ""
        _suggestions.value = emptyList()
    }

    private suspend fun fetchTmdbSuggestions(query: String): List<String> {
        val apiKey = TmdbSettingsRepository.effectiveApiKey()
        if (apiKey.isBlank()) return emptyList()
        val url = buildTmdbUrl(
            endpoint = "search/multi",
            apiKey = apiKey,
            query = mapOf("query" to query, "language" to "en-US", "include_adult" to "false"),
        )
        val payload = httpGetText(url)
        val parsed = json.decodeFromString<TmdbMultiSearchResponse>(payload)
        return parsed.results
            .asSequence()
            .filter { it.mediaType == "movie" || it.mediaType == "tv" }
            .mapNotNull { it.title ?: it.name }
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
            .take(8)
            .toList()
    }
}

@Serializable
private data class TmdbMultiSearchResponse(
    val results: List<TmdbMultiSearchItem> = emptyList(),
)

@Serializable
private data class TmdbMultiSearchItem(
    @SerialName("media_type") val mediaType: String? = null,
    val title: String? = null,
    val name: String? = null,
)
