#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 1: Search Overhaul (Section 1).

Root-cause fixes:
  - `SearchRepository.search()` short-circuited to `NoActiveAddons` whenever no
    addon/server/CloudStream source was runnable, even though the app ships a
    built-in TMDB catalog. It now falls back to a built-in TMDB search section
    (`TmdbService.searchTitles`) so search always returns results.
  - Autocomplete suggestions were derived only from in-flight addon sections and
    history; they now also include live debounced TMDB title suggestions.
  - Tapping a suggestion row navigated straight to details; it now fills the
    query and runs the search (the existing arrow button still only fills).
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 search] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 search] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 1: TmdbService.searchTitles — built-in title search API
# ---------------------------------------------------------------------------

def _patch_tmdb_service(root: Path) -> None:
    tmdb = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/tmdb/TmdbService.kt"
    _replace_once(
        tmdb,
        """import com.nuvio.app.features.addons.httpGetText
import kotlinx.coroutines.sync.Mutex""",
        """import com.nuvio.app.features.addons.httpGetText
import com.nuvio.app.features.home.MetaPreview
import kotlinx.coroutines.sync.Mutex""",
        "TmdbService MetaPreview import",
    )

    _replace_once(
        tmdb,
        """        return fetch<TmdbPublicReviewsPage>(
            endpoint = endpoint,
            apiKey = apiKey,
            query = mapOf("page" to page.coerceAtLeast(1).toString()),
        )
    }

    internal fun normalizeMediaType(mediaType: String): String =""",
        """        return fetch<TmdbPublicReviewsPage>(
            endpoint = endpoint,
            apiKey = apiKey,
            query = mapOf("page" to page.coerceAtLeast(1).toString()),
        )
    }

    /**
     * Built-in title search (Nuvio Enhanced): powers Search autocomplete
     * suggestions and the no-addon fallback results section.
     */
    suspend fun searchTitles(query: String, limit: Int = 14): List<MetaPreview> {
        val apiKey = TmdbSettingsRepository.effectiveApiKey()
        val cleanQuery = query.trim()
        if (apiKey.isBlank() || cleanQuery.isBlank()) return emptyList()
        val body = fetch<TmdbMultiSearchResponse>(
            endpoint = "search/multi",
            apiKey = apiKey,
            query = mapOf(
                "query" to cleanQuery,
                "include_adult" to "false",
            ),
        ) ?: return emptyList()
        return body.results.asSequence()
            .filter { item -> item.id > 0 && (item.mediaType == "movie" || item.mediaType == "tv") }
            .distinctBy { item -> "${item.mediaType}:${item.id}" }
            .mapNotNull { item ->
                val title = (item.title ?: item.name)?.trim().orEmpty()
                if (title.isEmpty()) return@mapNotNull null
                val rawDate = item.releaseDate ?: item.firstAirDate
                val year = rawDate
                    ?.take(4)
                    ?.takeIf { it.length == 4 && it.all(Char::isDigit) }
                MetaPreview(
                    id = "tmdb:${item.id}",
                    type = if (item.mediaType == "tv") "series" else "movie",
                    name = title,
                    poster = item.posterPath?.takeIf { it.isNotBlank() }
                        ?.let { path -> "https://image.tmdb.org/t/p/w500$path" },
                    banner = item.backdropPath?.takeIf { it.isNotBlank() }
                        ?.let { path -> "https://image.tmdb.org/t/p/w780$path" },
                    description = item.overview,
                    releaseInfo = year,
                    rawReleaseDate = rawDate,
                    popularity = item.popularity,
                    voteCount = item.voteCount,
                    imdbRating = item.voteAverage
                        ?.takeIf { it > 0.0 }
                        ?.let { value -> if (value % 1.0 == 0.0) value.toInt().toString() else value.toString() },
                )
            }
            .take(limit)
            .toList()
    }

    internal fun normalizeMediaType(mediaType: String): String =""",
        "TmdbService.searchTitles()",
    )

    _replace_once(
        tmdb,
        """@Serializable
data class TmdbPublicReviewAuthorDto(
    val name: String? = null,
    val username: String? = null,
    val rating: Double? = null,
)
""",
        """@Serializable
data class TmdbPublicReviewAuthorDto(
    val name: String? = null,
    val username: String? = null,
    val rating: Double? = null,
)

@Serializable
private data class TmdbMultiSearchResponse(
    val results: List<TmdbMultiSearchItem> = emptyList(),
)

@Serializable
private data class TmdbMultiSearchItem(
    val id: Int = 0,
    @SerialName("media_type") val mediaType: String? = null,
    val title: String? = null,
    val name: String? = null,
    val overview: String? = null,
    @SerialName("poster_path") val posterPath: String? = null,
    @SerialName("backdrop_path") val backdropPath: String? = null,
    @SerialName("release_date") val releaseDate: String? = null,
    @SerialName("first_air_date") val firstAirDate: String? = null,
    @SerialName("vote_average") val voteAverage: Double? = null,
    @SerialName("vote_count") val voteCount: Int? = null,
    val popularity: Double? = null,
)
""",
        "TmdbService multi-search DTOs",
    )


# ---------------------------------------------------------------------------
# Step 2: SearchRepository — TMDB fallback section when no other sources exist
# ---------------------------------------------------------------------------

def _patch_search_repository(root: Path) -> None:
    repo = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchRepository.kt"
    _replace_once(
        repo,
        """import com.nuvio.app.features.watchprogress.CurrentDateProvider
import kotlinx.coroutines.CancellationException""",
        """import com.nuvio.app.features.watchprogress.CurrentDateProvider
import com.nuvio.app.features.tmdb.TmdbService
import kotlinx.coroutines.CancellationException""",
        "SearchRepository TmdbService import",
    )

    # A: only short-circuit while manifests are pending or an error must surface;
    # otherwise fall through to the built-in TMDB catalog below.
    _replace_once(
        repo,
        """        if (activeAddons.isEmpty() && serverSearches.isEmpty() && runnableCloudPlugins.isEmpty()) {
            activeJob?.cancel()
            lastRequestKey = null
            _uiState.value = SearchUiState(
                isLoading = hasPendingAddonManifests,
                emptyStateReason = when {
                    hasPendingAddonManifests -> null
                    addonManifestErrorMessage != null -> SearchEmptyStateReason.RequestFailed
                    else -> SearchEmptyStateReason.NoActiveAddons
                },
                errorMessage = addonManifestErrorMessage,
            )
            return
        }""",
        """        val noExternalSearchSources =
            activeAddons.isEmpty() && serverSearches.isEmpty() && runnableCloudPlugins.isEmpty()
        if (noExternalSearchSources && (hasPendingAddonManifests || addonManifestErrorMessage != null)) {
            activeJob?.cancel()
            lastRequestKey = null
            _uiState.value = SearchUiState(
                isLoading = hasPendingAddonManifests,
                emptyStateReason = if (hasPendingAddonManifests) {
                    null
                } else {
                    SearchEmptyStateReason.RequestFailed
                },
                errorMessage = addonManifestErrorMessage,
            )
            return
        }""",
        "SearchRepository no-source early return",
    )

    # B: with zero runnable loaders, use the TMDB fallback instead of giving up.
    _replace_once(
        repo,
        """        if (requests.isEmpty() && serverSearches.isEmpty() && runnableCloudPlugins.isEmpty()) {
            activeJob?.cancel()
            lastRequestKey = null
            _uiState.value = SearchUiState(
                isLoading = hasPendingAddonManifests,
                emptyStateReason = if (hasPendingAddonManifests) null else SearchEmptyStateReason.NoSearchCatalogs,
            )
            return
        }""",
        """        val useTmdbFallback =
            requests.isEmpty() && serverSearches.isEmpty() && runnableCloudPlugins.isEmpty()
        if (useTmdbFallback && hasPendingAddonManifests) {
            activeJob?.cancel()
            lastRequestKey = null
            _uiState.value = SearchUiState(isLoading = true)
            return
        }""",
        "SearchRepository empty-loader early return",
    )

    _replace_once(
        repo,
        """            append("|csExt=$includeCloudStreamExtensions:")
            append(runnableCloudPlugins.joinToString(",") { it.metadata.id.value })
        }""",
        """            append("|csExt=$includeCloudStreamExtensions:")
            append(runnableCloudPlugins.joinToString(",") { it.metadata.id.value })
            if (useTmdbFallback) append("|tmdbFallback")
        }""",
        "SearchRepository request key tmdb flag",
    )

    _replace_once(
        repo,
        """        val loaders: List<suspend () -> HomeCatalogSection> =
            requests.map { request -> suspend { request.toSection(forceRefresh = forceRefresh) } } +""",
        """        val tmdbFallbackLoader: (suspend () -> HomeCatalogSection)? =
            if (useTmdbFallback) {
                suspend { tmdbFallbackSection(normalizedQuery) }
            } else {
                null
            }
        val loaders: List<suspend () -> HomeCatalogSection> =
            requests.map { request -> suspend { request.toSection(forceRefresh = forceRefresh) } } +""",
        "SearchRepository tmdb loader declaration",
    )

    _replace_once(
        repo,
        """                        requireNotNull(section) {
                            "No CloudStream matches in ${plugin.metadata.name}"
                        }
                    }
                }
        if (canReuseRequestState(forceRefresh, requestKey, lastRequestKey)) return""",
        """                        requireNotNull(section) {
                            "No CloudStream matches in ${plugin.metadata.name}"
                        }
                    }
                } +
                listOfNotNull(tmdbFallbackLoader)
        if (canReuseRequestState(forceRefresh, requestKey, lastRequestKey)) return""",
        "SearchRepository loaders tmdb append",
    )

    _replace_once(
        repo,
        """    private fun buildDiscoverSources(addons: List<ManagedAddon>): List<DiscoverCatalogOption> =""",
        """    private suspend fun tmdbFallbackSection(query: String): HomeCatalogSection {
        val items = TmdbService.searchTitles(query)
        require(items.isNotEmpty()) {
            getString(Res.string.search_error_no_results_for_catalog, "TMDB")
        }
        return HomeCatalogSection(
            key = "tmdb:search:${query.lowercase()}",
            title = "TMDB",
            subtitle = "Built-in catalog",
            addonName = "TMDB",
            target = CatalogTarget.Addon(
                manifestUrl = "tmdb://builtin",
                contentType = if (items.first().type == "series") "series" else "movie",
                catalogId = "search",
            ),
            items = items,
        )
    }

    private fun buildDiscoverSources(addons: List<ManagedAddon>): List<DiscoverCatalogOption> =""",
        "SearchRepository tmdbFallbackSection()",
    )


# ---------------------------------------------------------------------------
# Step 3: SearchEnhancements — merge TMDB titles into autocomplete suggestions
# ---------------------------------------------------------------------------

def _patch_search_enhancements(root: Path) -> None:
    enhancements = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchEnhancements.kt"
    _replace_once(
        enhancements,
        """fun buildSearchAutocompleteSuggestions(
    rawQuery: String,
    recentSearches: List<String>,
    sections: List<HomeCatalogSection>,
    limit: Int = 8,
): List<SearchSuggestionItem> {""",
        """fun buildSearchAutocompleteSuggestions(
    rawQuery: String,
    recentSearches: List<String>,
    sections: List<HomeCatalogSection>,
    tmdbTitles: List<MetaPreview> = emptyList(),
    limit: Int = 8,
): List<SearchSuggestionItem> {""",
        "buildSearchAutocompleteSuggestions signature",
    )

    _replace_once(
        enhancements,
        """    sections.asSequence()
        .flatMap { section ->
            section.items.asSequence().map { item -> section to item }
        }""",
        """    tmdbTitles.forEach { title ->
        if (result.size >= limit) return@forEach
        val cleanName = title.name.trim()
        if (cleanName.isBlank()) return@forEach
        if (!seen.add(cleanName.lowercase())) return@forEach
        val yearLabel = title.releaseInfo?.take(4)?.takeIf { it.all(Char::isDigit) }
        val typeLabel = title.type.replaceFirstChar { char ->
            if (char.isLowerCase()) char.titlecase() else char.toString()
        }
        result += SearchSuggestionItem(
            text = cleanName,
            subtitle = listOfNotNull(typeLabel, yearLabel, "TMDB").joinToString(" · "),
            isHistory = false,
            preview = title,
        )
    }

    sections.asSequence()
        .flatMap { section ->
            section.items.asSequence().map { item -> section to item }
        }""",
        "buildSearchAutocompleteSuggestions tmdb merge",
    )


# ---------------------------------------------------------------------------
# Step 4: SearchScreen — debounced TMDB suggestions + fill-and-search selection
# ---------------------------------------------------------------------------

def _patch_search_screen(root: Path) -> None:
    screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchScreen.kt"
    _replace_once(
        screen,
        """import com.nuvio.app.features.home.buildAddonCatalogRefreshSignature""",
        """import com.nuvio.app.features.home.buildAddonCatalogRefreshSignature
import com.nuvio.app.features.tmdb.TmdbService""",
        "SearchScreen TmdbService import",
    )

    _replace_once(
        screen,
        """    var query by rememberSaveable { mutableStateOf("") }
    var lastRequestedQuery by rememberSaveable { mutableStateOf<String?>(null) }""",
        """    var query by rememberSaveable { mutableStateOf("") }
    var lastRequestedQuery by rememberSaveable { mutableStateOf<String?>(null) }
    var tmdbSuggestions by remember { mutableStateOf<List<MetaPreview>>(emptyList()) }""",
        "SearchScreen tmdbSuggestions state",
    )

    _replace_once(
        screen,
        """            SearchRepository.search(
                query = normalizedQuery,
                addons = addonsUiState.addons,
                includeCloudStreamExtensions = includeCloudStreamExtensions,
            )
        }
    }""",
        """            SearchRepository.search(
                query = normalizedQuery,
                addons = addonsUiState.addons,
                includeCloudStreamExtensions = includeCloudStreamExtensions,
            )
        }
    }

    // Nuvio Enhanced: debounced TMDB title suggestions for the autocomplete card.
    LaunchedEffect(query) {
        val trimmed = query.trim()
        if (trimmed.length < 2) {
            tmdbSuggestions = emptyList()
            return@LaunchedEffect
        }
        delay(350)
        if (query.trim() != trimmed) return@LaunchedEffect
        tmdbSuggestions = runCatching {
            TmdbService.searchTitles(trimmed, limit = 8)
        }.getOrDefault(emptyList())
    }""",
        "SearchScreen tmdb suggestion effect",
    )

    _replace_once(
        screen,
        """                    val autocompleteSuggestions = remember(query, recentSearches, uiState.sections) {
                        buildSearchAutocompleteSuggestions(
                            rawQuery = query,
                            recentSearches = recentSearches,
                            sections = uiState.sections,
                        )
                    }""",
        """                    val autocompleteSuggestions =
                        remember(query, recentSearches, uiState.sections, tmdbSuggestions) {
                            buildSearchAutocompleteSuggestions(
                                rawQuery = query,
                                recentSearches = recentSearches,
                                sections = uiState.sections,
                                tmdbTitles = tmdbSuggestions,
                            )
                        }""",
        "SearchScreen autocomplete remember",
    )

    _replace_once(
        screen,
        """                        onSelectSuggestion = { suggestion ->
                            query = suggestion.text
                            SearchHistoryRepository.recordSearch(suggestion.text)
                            isSearchFocused = false
                            suggestion.preview?.let { preview -> onPosterClick?.invoke(preview) }
                        },""",
        """                        onSelectSuggestion = { suggestion ->
                            // Nuvio Enhanced: fill the query and run the search instead of
                            // navigating straight to the details screen.
                            query = suggestion.text
                            SearchHistoryRepository.recordSearch(suggestion.text)
                            isSearchFocused = false
                        },""",
        "SearchScreen onSelectSuggestion fill-and-search",
    )


def apply_v120_search_patch(source_dir: Path) -> None:
    _patch_tmdb_service(source_dir)
    _patch_search_repository(source_dir)
    _patch_search_enhancements(source_dir)
    _patch_search_screen(source_dir)
    print("[v1.20-module-1] Search TMDB fallback, suggestions, and fill-and-search applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_search_patch.py <source_dir>")
    apply_v120_search_patch(Path(sys.argv[1]).resolve())
