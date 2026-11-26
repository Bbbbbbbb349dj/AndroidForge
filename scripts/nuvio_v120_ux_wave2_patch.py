"""Nuvio Enhanced v1.20 — UX wave 2.

- Search: suggestions close on search commit (IME Search action + focus clearing),
  CloudStream-style type chip visible after searching, results filtered by type.
- Watched/unwatched purged from the poster quick-actions sheet and the episode /
  season long-press sheets (library categories remain the single source of truth).
- Player: theme-accent tint for the liquid-glass sheen (settings switch for the
  glass itself already exists at Settings -> Playback -> Interface).
"""

from __future__ import annotations

from pathlib import Path

_SEARCH = "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchScreen.kt"
_DISCOVER = "composeApp/src/commonMain/kotlin/com/nuvio/app/features/search/SearchDiscoverContent.kt"
_INPUT = "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/Components.kt"
_QUICK = "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/TitleQuickDetailsSheet.kt"
_DETAILS = "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/MetaDetailsScreen.kt"
_GLASS = "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerLiquidGlass.kt"
_PC = "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenContent.kt"


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 ux-wave2] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 ux-wave2] Ambiguous anchor ({count} matches) for {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_input_field_keyboard(source_dir: Path) -> None:
    path = source_dir / _INPUT
    _replace_once(
        path,
        """import androidx.compose.foundation.text.TextAutoSize""",
        """import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.TextAutoSize""",
        "keyboard imports",
    )
    _replace_once(
        path,
        """    trailingContent: (@Composable (() -> Unit))? = null,
    containerColor: Color = MaterialTheme.nuvio.colors.surfaceCard,
) {""",
        """    trailingContent: (@Composable (() -> Unit))? = null,
    containerColor: Color = MaterialTheme.nuvio.colors.surfaceCard,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    keyboardActions: KeyboardActions = KeyboardActions.Default,
) {""",
        "input field keyboard params",
    )
    _replace_once(
        path,
        """        modifier = modifier.fillMaxWidth(),
        singleLine = true,""",
        """        modifier = modifier.fillMaxWidth(),
        keyboardOptions = keyboardOptions,
        keyboardActions = keyboardActions,
        singleLine = true,""",
        "input field keyboard pass-through",
    )


def _patch_search_commit(source_dir: Path) -> None:
    path = source_dir / _SEARCH
    _replace_once(
        path,
        """    val focusRequester = remember { FocusRequester() }""",
        """    val focusRequester = remember { FocusRequester() }
    val commitFocusManager = androidx.compose.ui.platform.LocalFocusManager.current""",
        "focus manager",
    )
    _replace_once(
        path,
        """                            onValueChange = { query = it },
                            placeholder = stringResource(Res.string.compose_search_placeholder),""",
        """                            onValueChange = { query = it },
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                                imeAction = androidx.compose.ui.text.input.ImeAction.Search,
                            ),
                            keyboardActions = androidx.compose.foundation.text.KeyboardActions(
                                onSearch = {
                                    if (query.isNotBlank()) {
                                        SearchHistoryRepository.recordSearch(query.trim())
                                    }
                                    isSearchFocused = false
                                    commitFocusManager.clearFocus(force = true)
                                },
                            ),
                            placeholder = stringResource(Res.string.compose_search_placeholder),""",
        "IME search commits and closes suggestions",
    )
    _replace_once(
        path,
        """                                onSearchPress = { recentQuery ->
                                    query = recentQuery
                                    SearchHistoryRepository.recordSearch(recentQuery)
                                },""",
        """                                onSearchPress = { recentQuery ->
                                    query = recentQuery
                                    SearchHistoryRepository.recordSearch(recentQuery)
                                    isSearchFocused = false
                                    commitFocusManager.clearFocus(force = true)
                                },""",
        "recent search closes suggestions",
    )
    _replace_once(
        path,
        """                            query = suggestion.text
                            SearchHistoryRepository.recordSearch(suggestion.text)
                            isSearchFocused = false
                        },""",
        """                            query = suggestion.text
                            SearchHistoryRepository.recordSearch(suggestion.text)
                            isSearchFocused = false
                            commitFocusManager.clearFocus(force = true)
                        },""",
        "suggestion tap closes suggestions",
    )


def _patch_search_type_filter(source_dir: Path) -> None:
    path = source_dir / _DISCOVER
    _replace_once(
        path,
        """@Composable
private fun CatalogLoadingFooter(modifier: Modifier = Modifier) {""",
        """@Composable
internal fun SearchTypeFilterRow(
    state: DiscoverUiState,
    onTypeSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    // CloudStream-style type chip: visible after a search so results can be narrowed
    // to Movies / Series without losing the query.
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        NuvioDropdownChip(
            title = stringResource(Res.string.discover_select_type),
            label = state.selectedType?.displayTypeLabel() ?: stringResource(Res.string.discover_type),
            selectedKey = state.selectedType,
            options = state.typeOptions.map { NuvioDropdownOption(key = it, label = it.displayTypeLabel()) },
            enabled = state.typeOptions.isNotEmpty(),
            onSelected = { onTypeSelected(it.key) },
        )
    }
}

@Composable
private fun CatalogLoadingFooter(modifier: Modifier = Modifier) {""",
        "SearchTypeFilterRow",
    )

    screen = source_dir / _SEARCH
    _replace_once(
        screen,
        """                    if (query.isBlank()) {
                        DiscoverFilterRow(
                            state = discoverUiState,
                            modifier = Modifier
                                .padding(horizontal = 16.dp)
                                .padding(top = 8.dp, bottom = 14.dp),
                            onTypeSelected = SearchRepository::selectDiscoverType,
                            onCatalogSelected = SearchRepository::selectDiscoverCatalog,
                            onGenreSelected = SearchRepository::selectDiscoverGenre,
                        )
                    }""",
        """                    if (query.isBlank()) {
                        DiscoverFilterRow(
                            state = discoverUiState,
                            modifier = Modifier
                                .padding(horizontal = 16.dp)
                                .padding(top = 8.dp, bottom = 14.dp),
                            onTypeSelected = SearchRepository::selectDiscoverType,
                            onCatalogSelected = SearchRepository::selectDiscoverCatalog,
                            onGenreSelected = SearchRepository::selectDiscoverGenre,
                        )
                    } else {
                        SearchTypeFilterRow(
                            state = discoverUiState,
                            modifier = Modifier
                                .padding(horizontal = 16.dp)
                                .padding(top = 8.dp, bottom = 14.dp),
                            onTypeSelected = SearchRepository::selectDiscoverType,
                        )
                    }""",
        "type chip stays visible after search",
    )
    _replace_once(
        screen,
        """            NuvioScreen(
                horizontalPadding = 0.dp,""",
        """            val searchResultSections = remember(uiState.sections, discoverUiState.selectedType) {
                val selected = discoverUiState.selectedType
                if (selected.isNullOrBlank()) {
                    uiState.sections
                } else {
                    uiState.sections.mapNotNull { section ->
                        val filtered = section.items.filter { item ->
                            item.type.equals(selected, ignoreCase = true) ||
                                (selected.equals("series", ignoreCase = true) && item.type.equals("tv", ignoreCase = true)) ||
                                (selected.equals("tv", ignoreCase = true) && item.type.equals("series", ignoreCase = true))
                        }
                        if (filtered.isEmpty()) null else section.copy(items = filtered)
                    }
                }
            }
            NuvioScreen(
                horizontalPadding = 0.dp,""",
        "filtered search sections",
    )
    _replace_once(
        screen,
        """                        uiState.sections.isEmpty() -> {
                            item {
                                SearchEmptyStateCard(""",
        """                        searchResultSections.isEmpty() -> {
                            item {
                                SearchEmptyStateCard(""",
        "empty state honours type filter",
    )
    _replace_once(
        screen,
        """                            items(
                                items = uiState.sections.withDuplicateSafeLazyKeys { section -> section.key },""",
        """                            items(
                                items = searchResultSections.withDuplicateSafeLazyKeys { section -> section.key },""",
        "render filtered sections",
    )


def _patch_watched_purge(source_dir: Path) -> None:
    quick = source_dir / _QUICK
    _replace_once(
        quick,
        """                Row(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .border(
                            1.dp,
                            MaterialTheme.colorScheme.outline.copy(alpha = 0.5f),
                            RoundedCornerShape(14.dp),
                        )
                        .clickable(onClick = onToggleWatched)
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Icon(
                        imageVector = if (isWatched) Icons.Rounded.VisibilityOff else Icons.Rounded.Visibility,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.size(18.dp),
                    )
                    Text(
                        text = if (isWatched) "Unwatched" else "Watched",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }""",
        """            }""",
        "quick sheet watched button removed",
    )
    details = source_dir / _DETAILS
    _replace_once(
        details,
        """                                        onEpisodeLongPress = { video ->
                                            selectedEpisodeZoomAnchor = PosterZoomAnchorHolder.consume()
                                            selectedEpisodeForActions = video
                                        },
                                        onSeasonLongPress = { season -> selectedSeasonForActions = season },""",
        """                                        onEpisodeLongPress = { _ -> },
                                        onSeasonLongPress = { _ -> },""",
        "episode/season watched sheets no longer open",
    )


def _patch_theme_glass(source_dir: Path) -> None:
    glass = source_dir / _GLASS
    _replace_once(
        glass,
        """internal val LocalPlayerControlGlassEnabled = staticCompositionLocalOf { true }""",
        """internal val LocalPlayerControlGlassEnabled = staticCompositionLocalOf { true }

/** Theme accent tint for the glass sheen so player chrome follows the active theme. */
internal val LocalPlayerThemeGlassTint = staticCompositionLocalOf { Color.White.copy(alpha = 0.05f) }""",
        "theme glass tint local",
    )
    _replace_once(
        glass,
        """    tint: Color = PlayerGlassSurfaceTint,
    fallback: Color = PlayerGlassFallback,""",
        """    tint: Color = LocalPlayerThemeGlassTint.current,
    fallback: Color = PlayerGlassFallback,""",
        "glass default tint from theme",
    )
    pc = source_dir / _PC
    _replace_once(
        pc,
        """            LocalPlayerControlGlassEnabled provides playerSettingsUiState.playerControlGlassEnabled,
        ) {""",
        """            LocalPlayerControlGlassEnabled provides playerSettingsUiState.playerControlGlassEnabled,
            LocalPlayerThemeGlassTint provides androidx.compose.material3.MaterialTheme.colorScheme.primary.copy(alpha = 0.07f),
        ) {""",
        "provide theme glass tint",
    )


def apply_v120_ux_wave2_patch(source_dir: Path) -> None:
    _patch_input_field_keyboard(source_dir)
    _patch_search_commit(source_dir)
    _patch_search_type_filter(source_dir)
    _patch_watched_purge(source_dir)
    _patch_theme_glass(source_dir)
    print(
        "[v1.20-module-14] UX wave 2: search commit + type filter, watched purge, "
        "theme glass tint applied cleanly."
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: nuvio_v120_ux_wave2_patch.py <source-root>")
    apply_v120_ux_wave2_patch(Path(sys.argv[1]))
