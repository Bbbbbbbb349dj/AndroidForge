#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 2: Details Mark-Watched Removal & Rating Map (Sections 4 & 5).

  - Section 4: removes the hero `watchedAction` (Mark watched/unwatched) button from
    `DetailActionButtons.kt` (phone secondary row + tablet icon row). Progress,
    episode watched state, and Library tracking remain untouched.
  - Section 5: single source of truth for the episode Rating Map:
      * keeps ONE `showRatingMap` toggle in `RatingsSettings.kt`,
      * adds `RatingMapPosition` (TOP/BOTTOM) for non-tab layouts (TOP renders right
        after Overview, BOTTOM after all sections),
      * adds `MetaScreenSectionKey.RATING_MAP` (enable/reorder/Grouped/None) for the
        tab layout path,
      * removes the inline duplicate rating-map row from `DetailPremiumOverviewCard`.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 details] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 details] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _replace_each(path: Path, old: str, new: str, label: str, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"[v1.20 details] Expected {expected} matches for {label}, found {count} in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


# ---------------------------------------------------------------------------
# Section 4: remove Mark watched / Mark unwatched action from details buttons
# ---------------------------------------------------------------------------

def _patch_remove_watched_action(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailActionButtons.kt"
    text = path.read_text(encoding="utf-8")

    # Drop the now-unused string imports (only referenced by the removed action).
    text = text.replace(
        "import nuvio.composeapp.generated.resources.hero_mark_unwatched\n"
        "import nuvio.composeapp.generated.resources.hero_mark_watched\n",
        "",
        1,
    )
    # Drop the now-unused visibility icons (only referenced by the removed action).
    text = text.replace(
        "import androidx.compose.material.icons.filled.Visibility\n"
        "import androidx.compose.material.icons.filled.VisibilityOff\n",
        "",
        1,
    )
    path.write_text(text, encoding="utf-8")

    _replace_once(
        path,
        """    val shuffleAction = actionSet.shuffle
    val watchedAction = actionSet.watched
    val saveAction = actionSet.save""",
        """    val shuffleAction = actionSet.shuffle
    val saveAction = actionSet.save""",
        "DetailActions drop watchedAction",
    )

    _replace_once(
        path,
        """        secondaryActions = buildList {
            if (!shuffleEnabled) shuffleAction?.let(::add)
            add(watchedAction)
            add(saveAction)
        },""",
        """        secondaryActions = buildList {
            if (!shuffleEnabled) shuffleAction?.let(::add)
            add(saveAction)
        },""",
        "DetailActions secondary list",
    )

    _replace_once(
        path,
        """private class DetailActionSet(
    val shuffle: DetailSecondaryAction?,
    val watched: DetailSecondaryAction,
    val save: DetailSecondaryAction,
    val icons: List<DetailSecondaryAction>,
)""",
        """private class DetailActionSet(
    val shuffle: DetailSecondaryAction?,
    val save: DetailSecondaryAction,
    val icons: List<DetailSecondaryAction>,
)""",
        "DetailActionSet drop watched",
    )

    _replace_once(
        path,
        """    val watchedAction = DetailSecondaryAction(
        label = stringResource(if (isWatched) Res.string.hero_mark_unwatched else Res.string.hero_mark_watched),
        icon = if (isWatched) Icons.Default.Visibility else Icons.Default.VisibilityOff,
        isActive = isWatched,
        onClick = onWatchedClick,
    )
    val saveAction = DetailSecondaryAction(""",
        """    val saveAction = DetailSecondaryAction(""",
        "detailActionSet drop watchedAction build",
    )

    _replace_once(
        path,
        """        add(watchedAction)
        add(saveAction)
    }
    return DetailActionSet(shuffleAction, watchedAction, saveAction, iconActions)""",
        """        add(saveAction)
    }
    return DetailActionSet(shuffleAction, saveAction, iconActions)""",
        "detailActionSet icon row + return",
    )


# ---------------------------------------------------------------------------
# Section 5: rating map — repository (RatingMapPosition + RATING_MAP section key)
# ---------------------------------------------------------------------------

def _patch_settings_repository(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/MetaScreenSettingsRepository.kt"

    _replace_once(
        path,
        """    EPISODES,
    DETAILS,
    COLLECTION,
    MORE_LIKE_THIS,
    ;

    
    val canBeTabbed: Boolean
        get() = this != ACTIONS && this != OVERVIEW
}
""",
        """    EPISODES,
    RATING_MAP,
    DETAILS,
    COLLECTION,
    MORE_LIKE_THIS,
    ;

    
    val canBeTabbed: Boolean
        get() = this != ACTIONS && this != OVERVIEW
}

enum class RatingMapPosition {
    TOP,
    BOTTOM,
    ;

    companion object {
        fun parse(raw: String?): RatingMapPosition? = when (raw?.lowercase()) {
            "top" -> TOP
            "bottom" -> BOTTOM
            else -> null
        }

        fun persist(position: RatingMapPosition): String = when (position) {
            TOP -> "top"
            BOTTOM -> "bottom"
        }
    }
}
""",
        "MetaScreenSectionKey.RATING_MAP + RatingMapPosition",
    )

    _replace_once(
        path,
        """    val showRatingMap: Boolean = true,
    val showDownloadAction: Boolean = false,
)""",
        """    val showRatingMap: Boolean = true,
    val ratingMapPosition: RatingMapPosition = RatingMapPosition.BOTTOM,
    val showDownloadAction: Boolean = false,
)""",
        "UiState ratingMapPosition",
    )

    _replace_once(
        path,
        """    @SerialName("show_rating_map")
    val showRatingMap: Boolean = true,
    @SerialName("show_download_action")
    val showDownloadAction: Boolean = false,
)""",
        """    @SerialName("show_rating_map")
    val showRatingMap: Boolean = true,
    @SerialName("rating_map_position")
    val ratingMapPosition: String? = null,
    @SerialName("show_download_action")
    val showDownloadAction: Boolean = false,
)""",
        "payload ratingMapPosition",
    )

    _replace_once(
        path,
        """        MetaScreenSectionDefinition(
            key = MetaScreenSectionKey.EPISODES,
            titleRes = Res.string.settings_meta_episodes,
            descriptionRes = Res.string.meta_section_episodes_description,
        ),
        MetaScreenSectionDefinition(
            key = MetaScreenSectionKey.DETAILS,""",
        """        MetaScreenSectionDefinition(
            key = MetaScreenSectionKey.EPISODES,
            titleRes = Res.string.settings_meta_episodes,
            descriptionRes = Res.string.meta_section_episodes_description,
        ),
        MetaScreenSectionDefinition(
            key = MetaScreenSectionKey.RATING_MAP,
            titleRes = Res.string.layout_rating_map,
            descriptionRes = Res.string.layout_rating_map_sub,
        ),
        MetaScreenSectionDefinition(
            key = MetaScreenSectionKey.DETAILS,""",
        "definitions RATING_MAP",
    )

    _replace_once(
        path,
        """    private var showRatingMap: Boolean = true
    private var posterTransitionEnabled: Boolean = false""",
        """    private var showRatingMap: Boolean = true
    private var ratingMapPosition: RatingMapPosition = RatingMapPosition.BOTTOM
    private var posterTransitionEnabled: Boolean = false""",
        "private ratingMapPosition var",
    )

    _replace_once(
        path,
        """                showRatingMap = parsed.showRatingMap
                showDownloadAction = parsed.showDownloadAction""",
        """                showRatingMap = parsed.showRatingMap
                ratingMapPosition = RatingMapPosition.parse(parsed.ratingMapPosition)
                    ?: RatingMapPosition.BOTTOM
                showDownloadAction = parsed.showDownloadAction""",
        "ensureLoaded parse position",
    )

    _replace_each(
        path,
        """        showRatingMap = true
        showDownloadAction = false""",
        """        showRatingMap = true
        ratingMapPosition = RatingMapPosition.BOTTOM
        showDownloadAction = false""",
        "reset defaults (profile/clear/reset)",
        expected=3,
    )

    _replace_once(
        path,
        """    fun setShowRatingMap(enabled: Boolean) {
        ensureLoaded()
        if (showRatingMap == enabled) return
        showRatingMap = enabled
        publish()
        persist()
    }
""",
        """    fun setShowRatingMap(enabled: Boolean) {
        ensureLoaded()
        if (showRatingMap == enabled) return
        showRatingMap = enabled
        publish()
        persist()
    }

    fun setRatingMapPosition(position: RatingMapPosition) {
        ensureLoaded()
        if (ratingMapPosition == position) return
        ratingMapPosition = position
        publish()
        persist()
    }
""",
        "setRatingMapPosition setter",
    )

    _replace_once(
        path,
        """            showRatingMap = showRatingMap,
            showDownloadAction = showDownloadAction,
        )
    }""",
        """            showRatingMap = showRatingMap,
            ratingMapPosition = ratingMapPosition,
            showDownloadAction = showDownloadAction,
        )
    }""",
        "publish ratingMapPosition",
    )

    _replace_once(
        path,
        """                    showRatingMap = showRatingMap,
                    showDownloadAction = showDownloadAction,
                ),""",
        """                    showRatingMap = showRatingMap,
                    ratingMapPosition = RatingMapPosition.persist(ratingMapPosition),
                    showDownloadAction = showDownloadAction,
                ),""",
        "persist ratingMapPosition",
    )

    _replace_once(
        path,
        """        orderedKeys.forEachIndexed { newIndex, sectionKey ->
            val current = preferences[sectionKey] ?: return@forEachIndexed
            preferences[sectionKey] = current.copy(order = newIndex)
        }
        publish()
        persist()
    }
""",
        """        orderedKeys.forEachIndexed { newIndex, sectionKey ->
            val current = preferences[sectionKey] ?: return@forEachIndexed
            preferences[sectionKey] = current.copy(order = newIndex)
        }
        publish()
        persist()
    }

    /** Reorder by section key so filtered editor lists map back to definition order. */
    fun moveByKey(fromKey: MetaScreenSectionKey, toKey: MetaScreenSectionKey) {
        ensureLoaded()
        if (fromKey == toKey) return
        val orderedKeys = definitions
            .sortedBy { definition -> preferences[definition.key]?.order ?: Int.MAX_VALUE }
            .map { it.key }
            .toMutableList()
        val fromIndex = orderedKeys.indexOf(fromKey)
        val toIndex = orderedKeys.indexOf(toKey)
        if (fromIndex < 0 || toIndex < 0) return
        orderedKeys.add(toIndex, orderedKeys.removeAt(fromIndex))
        orderedKeys.forEachIndexed { newIndex, sectionKey ->
            val current = preferences[sectionKey] ?: return@forEachIndexed
            preferences[sectionKey] = current.copy(order = newIndex)
        }
        publish()
        persist()
    }
""",
        "moveByKey",
    )


# ---------------------------------------------------------------------------
# Section 5: settings UI — strings, position chips, section editor mapping
# ---------------------------------------------------------------------------

def _patch_strings(root: Path) -> None:
    path = root / "composeApp/src/commonMain/composeResources/values/strings.xml"
    _replace_once(
        path,
        """    <string name="layout_rating_map">Rating Map</string>
    <string name="layout_rating_map_sub">Show a color-coded map of episode ratings at the bottom of show and anime pages.</string>""",
        """    <string name="layout_rating_map">Rating Map</string>
    <string name="layout_rating_map_sub">Show a color-coded map of episode ratings at the bottom of show and anime pages.</string>
    <string name="layout_rating_map_position">Rating Map Position</string>
    <string name="layout_rating_map_position_sub">Choose whether the rating map appears at the top or bottom of the details page.</string>""",
        "strings rating map position",
    )


def _patch_ratings_settings(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/RatingsSettings.kt"
    _replace_once(
        path,
        """import com.nuvio.app.core.ui.Chip
import com.nuvio.app.features.details.EpisodeRatingsVisibility
import com.nuvio.app.features.details.MetaScreenSettingsRepository
import com.nuvio.app.features.details.MetaScreenSettingsUiState""",
        """import com.nuvio.app.core.ui.Chip
import com.nuvio.app.features.details.EpisodeRatingsVisibility
import com.nuvio.app.features.details.MetaScreenSettingsRepository
import com.nuvio.app.features.details.MetaScreenSettingsUiState
import com.nuvio.app.features.details.RatingMapPosition""",
        "RatingsSettings import RatingMapPosition",
    )
    _replace_once(
        path,
        """import nuvio.composeapp.generated.resources.layout_rating_map
import nuvio.composeapp.generated.resources.layout_rating_map_sub""",
        """import nuvio.composeapp.generated.resources.layout_rating_map
import nuvio.composeapp.generated.resources.layout_rating_map_position
import nuvio.composeapp.generated.resources.layout_rating_map_position_sub
import nuvio.composeapp.generated.resources.layout_rating_map_sub
import nuvio.composeapp.generated.resources.settings_nav_bar_position_bottom
import nuvio.composeapp.generated.resources.settings_nav_bar_position_top""",
        "RatingsSettings string imports",
    )
    _replace_once(
        path,
        """    SettingsGroupDivider(isTablet = isTablet)
    SettingsSwitchRow(
        title = stringResource(Res.string.layout_rating_map),
        description = stringResource(Res.string.layout_rating_map_sub),
        checked = uiState.showRatingMap,
        isTablet = isTablet,
        onCheckedChange = MetaScreenSettingsRepository::setShowRatingMap,
    )
}""",
        """    SettingsGroupDivider(isTablet = isTablet)
    SettingsSwitchRow(
        title = stringResource(Res.string.layout_rating_map),
        description = stringResource(Res.string.layout_rating_map_sub),
        checked = uiState.showRatingMap,
        isTablet = isTablet,
        onCheckedChange = MetaScreenSettingsRepository::setShowRatingMap,
    )
    if (!uiState.tabLayout) {
        // Non-tab layouts position the map explicitly; tab layouts use the
        // RATING_MAP section row (reorder + Grouped/None) instead.
        SettingsGroupDivider(isTablet = isTablet)
        SettingsChipRow(
            title = stringResource(Res.string.layout_rating_map_position),
            description = stringResource(Res.string.layout_rating_map_position_sub),
            isTablet = isTablet,
        ) {
            RatingMapPosition.entries.forEach { position ->
                Chip(
                    label = stringResource(
                        when (position) {
                            RatingMapPosition.TOP -> Res.string.settings_nav_bar_position_top
                            RatingMapPosition.BOTTOM -> Res.string.settings_nav_bar_position_bottom
                        },
                    ),
                    selected = uiState.ratingMapPosition == position,
                    onClick = { MetaScreenSettingsRepository.setRatingMapPosition(position) },
                )
            }
        }
    }
}""",
        "RatingsSettings position chips",
    )


def _patch_settings_page(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/MetaScreenSettingsPage.kt"
    _replace_once(
        path,
        """        MetaScreenSectionKey.EPISODES -> Res.string.settings_meta_episodes
        MetaScreenSectionKey.DETAILS -> Res.string.settings_meta_details""",
        """        MetaScreenSectionKey.EPISODES -> Res.string.settings_meta_episodes
        MetaScreenSectionKey.RATING_MAP -> Res.string.layout_rating_map
        MetaScreenSectionKey.DETAILS -> Res.string.settings_meta_details""",
        "titleRes RATING_MAP",
    )
    _replace_once(
        path,
        """        MetaScreenSectionKey.EPISODES -> Res.string.settings_meta_episodes_description
        MetaScreenSectionKey.DETAILS -> Res.string.settings_meta_details_description""",
        """        MetaScreenSectionKey.EPISODES -> Res.string.settings_meta_episodes_description
        MetaScreenSectionKey.RATING_MAP -> Res.string.layout_rating_map_sub
        MetaScreenSectionKey.DETAILS -> Res.string.settings_meta_details_description""",
        "descriptionRes RATING_MAP",
    )
    _replace_once(
        path,
        """                MetaSectionReorderableList(
                    items = uiState.items,
                    isTablet = isTablet,
                    tabLayout = uiState.tabLayout,
                )""",
        """                MetaSectionReorderableList(
                    items = uiState.items.filter { item ->
                        uiState.tabLayout || item.key != MetaScreenSectionKey.RATING_MAP
                    },
                    isTablet = isTablet,
                    tabLayout = uiState.tabLayout,
                )""",
        "editor hides RATING_MAP outside tab mode",
    )
    _replace_once(
        path,
        """    ) { from, to ->
        MetaScreenSettingsRepository.moveByIndex(from.index, to.index)
        hapticFeedback.performHapticFeedback(HapticFeedbackType.TextHandleMove)
    }""",
        """    ) { from, to ->
        val fromKey = items.getOrNull(from.index)?.key
        val toKey = items.getOrNull(to.index)?.key
        if (fromKey != null && toKey != null) {
            MetaScreenSettingsRepository.moveByKey(fromKey, toKey)
        }
        hapticFeedback.performHapticFeedback(HapticFeedbackType.TextHandleMove)
    }""",
        "reorder uses moveByKey",
    )


# ---------------------------------------------------------------------------
# Section 5: DetailMetaInfo — remove inline rating-map duplicate
# ---------------------------------------------------------------------------

def _patch_detail_meta_info(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailMetaInfo.kt"
    _replace_once(
        path,
        """    showOverallRatings: Boolean = true,
    isMdbListActive: Boolean = false,
    showNuvioRead: Boolean? = null,
    showRatingMap: Boolean = true,
    episodeImdbRatings: Map<Pair<Int, Int>, Double> = emptyMap(),
    episodeTmdbRatings: Map<Pair<Int, Int>, Double> = emptyMap(),
    episodeRatingsVisibility: EpisodeRatingsVisibility? = null,
    isEpisodeWatched: ((MetaVideo) -> Boolean)? = null,
    onEpisodeClick: ((MetaVideo) -> Unit)? = null,
    onEpisodeLongPress: ((MetaVideo) -> Unit)? = null,
) {""",
        """    showOverallRatings: Boolean = true,
    isMdbListActive: Boolean = false,
    showNuvioRead: Boolean? = null,
    episodeImdbRatings: Map<Pair<Int, Int>, Double> = emptyMap(),
    episodeTmdbRatings: Map<Pair<Int, Int>, Double> = emptyMap(),
) {""",
        "DetailMetaInfo signature",
    )
    _replace_once(
        path,
        """            DetailPremiumOverviewCard(
                meta = meta,
                pills = overviewPills,
                ratings = meta.externalRatings,
                description = meta.description,
                showRatingMap = showRatingMap,
                episodeRatingsVisibility = episodeRatingsVisibility,
                isEpisodeWatched = isEpisodeWatched,
                onEpisodeClick = onEpisodeClick,
                onEpisodeLongPress = onEpisodeLongPress,
                onRatingsClick = { showRatings = true },
            )""",
        """            DetailPremiumOverviewCard(
                meta = meta,
                pills = overviewPills,
                ratings = meta.externalRatings,
                description = meta.description,
                onRatingsClick = { showRatings = true },
            )""",
        "premium card call args",
    )
    _replace_once(
        path,
        """private fun DetailPremiumOverviewCard(
    meta: MetaDetails,
    pills: List<String>,
    ratings: List<MetaExternalRating>,
    description: String?,
    showRatingMap: Boolean = true,
    episodeRatingsVisibility: EpisodeRatingsVisibility? = null,
    isEpisodeWatched: ((MetaVideo) -> Boolean)? = null,
    onEpisodeClick: ((MetaVideo) -> Unit)? = null,
    onEpisodeLongPress: ((MetaVideo) -> Unit)? = null,
    onRatingsClick: () -> Unit,
) {
    var ratingMapExpanded by remember { mutableStateOf(false) }
    // On-demand map: show the arrow row only when the global Rating Map
    // setting is on, a map actually exists, and episode ratings are not
    // hidden. The map content itself still only composes when expanded.
    val showRatingMapRow = showRatingMap &&
        episodeRatingsVisibility != null &&
        episodeRatingsVisibility.showRatings &&
        isEpisodeWatched != null && onEpisodeClick != null && onEpisodeLongPress != null &&
        meta.hasEpisodeRatingMap()
    Surface(""",
        """private fun DetailPremiumOverviewCard(
    meta: MetaDetails,
    pills: List<String>,
    ratings: List<MetaExternalRating>,
    description: String?,
    onRatingsClick: () -> Unit,
) {
    Surface(""",
        "premium card signature + row guard",
    )
    _replace_once(
        path,
        """            if (showRatingMapRow) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { ratingMapExpanded = !ratingMapExpanded }
                        .padding(vertical = 2.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = stringResource(Res.string.nuvio_read_rating_map),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Icon(
                        imageVector = if (ratingMapExpanded) Icons.Rounded.KeyboardArrowUp else Icons.Rounded.KeyboardArrowDown,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                AnimatedVisibility(visible = ratingMapExpanded) {
                    DetailEpisodeRatingMap(
                        meta = meta,
                        episodeRatingsVisibility = episodeRatingsVisibility!!,
                        isEpisodeWatched = isEpisodeWatched!!,
                        onEpisodeClick = onEpisodeClick!!,
                        onEpisodeLongPress = onEpisodeLongPress!!,
                    )
                }
            }

            description?.trim()?""",
        """            description?.trim()?""",
        "premium card inline rating map removal",
    )


# ---------------------------------------------------------------------------
# Section 5: MetaDetailsScreen — RATING_MAP section + positioned standalone map
# ---------------------------------------------------------------------------

def _patch_meta_details_screen(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/MetaDetailsScreen.kt"

    # 1. DetailMetaInfo call drops rating-map plumbing.
    _replace_once(
        path,
        """                DetailMetaInfo(
                    meta = meta,
                    showOverallRatings = settings.showOverallRatings,
                    isMdbListActive = isMdbListActive,
                    showRatingMap = settings.showRatingMap,
                    horizontalScrollPadding = horizontalScrollPadding,
                    episodeRatingsVisibility = settings.episodeRatingsVisibility,
                    isEpisodeWatched = { episode ->
                        isEpisodeWatchedForActions(
                            meta = meta,
                            episode = episode,
                            watchedKeys = watchedKeys,
                            progressByVideoId = progressByVideoId,
                        )
                    },
                    onEpisodeClick = onEpisodeClick,
                    onEpisodeLongPress = onEpisodeLongPress,
                )""",
        """                DetailMetaInfo(
                    meta = meta,
                    showOverallRatings = settings.showOverallRatings,
                    isMdbListActive = isMdbListActive,
                    horizontalScrollPadding = horizontalScrollPadding,
                )""",
        "DetailMetaInfo caller",
    )

    # 2. Standalone map after the section call is replaced by positioned emission
    #    inside `configuredMetaSectionItems` (TOP after Overview / BOTTOM at end).
    _replace_once(
        path,
        """                                    if (
                                        !enhancedSettingsUiState.nuvioReadEnabled &&
                                        metaScreenSettingsUiState.showRatingMap &&
                                        metaScreenSettingsUiState.episodeRatingsVisibility.showRatings &&
                                        hasEpisodes &&
                                        meta.hasEpisodeRatingMap()
                                    ) {
                                        item(key = "detail-rating-map") {
                                            val ratingMapWatchedKeys = watchedUiState.watchedKeys
                                            val isRatingMapEpisodeWatched = remember(meta, ratingMapWatchedKeys, progressByVideoId) {
                                                { episode: MetaVideo ->
                                                    isEpisodeWatchedForActions(
                                                        meta = meta,
                                                        episode = episode,
                                                        watchedKeys = ratingMapWatchedKeys,
                                                        progressByVideoId = progressByVideoId,
                                                    )
                                                }
                                            }
                                            DetailSectionContainer(
                                                horizontalPadding = contentHorizontalPadding,
                                                contentMaxWidth = if (isTablet && !useTabletLayout) contentMaxWidth else Dp.Unspecified,
                                            ) {
                                                DetailEpisodeRatingMap(
                                                    meta = meta,
                                                    episodeRatingsVisibility = metaScreenSettingsUiState.episodeRatingsVisibility,
                                                    isEpisodeWatched = isRatingMapEpisodeWatched,
                                                    onEpisodeClick = onEpisodePlayClick,
                                                    onEpisodeLongPress = { video ->
                                                        selectedEpisodeZoomAnchor = null
                                                        selectedEpisodeForActions = video
                                                    },
                                                )
                                            }
                                        }
                                    }

                                    item(key = "detail-bottom-spacer") {""",
        """                                    item(key = "detail-bottom-spacer") {""",
        "remove legacy standalone rating map item",
    )

    # 3. `metaSectionHasContent` exhaustive when.
    _replace_once(
        path,
        """        MetaScreenSectionKey.EPISODES -> hasEpisodes
        MetaScreenSectionKey.DETAILS -> hasAdditionalInfoSection
        MetaScreenSectionKey.COLLECTION -> !hasEpisodes && hasCollectionSection
        MetaScreenSectionKey.MORE_LIKE_THIS -> hasMoreLikeThisSection
    }

@Composable
@OptIn(ExperimentalSharedTransitionApi::class)""",
        """        MetaScreenSectionKey.EPISODES -> hasEpisodes
        MetaScreenSectionKey.RATING_MAP -> hasEpisodes && meta.hasEpisodeRatingMap()
        MetaScreenSectionKey.DETAILS -> hasAdditionalInfoSection
        MetaScreenSectionKey.COLLECTION -> !hasEpisodes && hasCollectionSection
        MetaScreenSectionKey.MORE_LIKE_THIS -> hasMoreLikeThisSection
    }

@Composable
@OptIn(ExperimentalSharedTransitionApi::class)""",
        "metaSectionHasContent RATING_MAP",
    )

    # 4. ConfiguredMetaSections.sectionHasContent (12-space indent).
    _replace_once(
        path,
        """            MetaScreenSectionKey.EPISODES -> hasEpisodes
            MetaScreenSectionKey.DETAILS -> hasAdditionalInfoSection""",
        """            MetaScreenSectionKey.EPISODES -> hasEpisodes
            MetaScreenSectionKey.RATING_MAP -> settings.showRatingMap &&
                settings.episodeRatingsVisibility.showRatings &&
                hasEpisodes &&
                meta.hasEpisodeRatingMap()
            MetaScreenSectionKey.DETAILS -> hasAdditionalInfoSection""",
        "sectionHasContent RATING_MAP",
    )

    # 5. RenderSection RATING_MAP case.
    _replace_once(
        path,
        """            MetaScreenSectionKey.EPISODES -> {
                if (hasEpisodes) {
                    DetailSeriesContent(""",
        """            MetaScreenSectionKey.RATING_MAP -> {
                if (
                    settings.showRatingMap &&
                    settings.episodeRatingsVisibility.showRatings &&
                    hasEpisodes &&
                    meta.hasEpisodeRatingMap()
                ) {
                    val ratingMapWatchedKeys = watchedKeys
                    DetailEpisodeRatingMap(
                        meta = meta,
                        episodeRatingsVisibility = settings.episodeRatingsVisibility,
                        isEpisodeWatched = { episode ->
                            isEpisodeWatchedForActions(
                                meta = meta,
                                episode = episode,
                                watchedKeys = ratingMapWatchedKeys,
                                progressByVideoId = progressByVideoId,
                            )
                        },
                        onEpisodeClick = onEpisodeClick,
                        onEpisodeLongPress = onEpisodeLongPress,
                    )
                }
            }
            MetaScreenSectionKey.EPISODES -> {
                if (hasEpisodes) {
                    DetailSeriesContent(""",
        "RenderSection RATING_MAP",
    )

    # 6. Non-tab emission: skip RATING_MAP as a plain section; emit positioned map.
    _replace_once(
        path,
        """    if (!settings.tabLayout) {
        enabledItems
            .filter { sectionHasContent(it.key) }
            .forEach { section ->
                if (section.key == MetaScreenSectionKey.EPISODES && addLazyEpisodeItems()) return@forEach
                addSectionItem(
                    key = "detail-section-${section.key.name}",
                    sectionItems = listOf(section),
                    forceTabLayout = false,
                )
            }
        return
    }
""",
        """    fun ratingMapAvailable(): Boolean =
        settings.showRatingMap &&
            settings.episodeRatingsVisibility.showRatings &&
            hasEpisodes &&
            meta.hasEpisodeRatingMap()

    fun addRatingMapItem() {
        item(key = "detail-rating-map") {
            val ratingMapWatchedKeys = watchedKeys
            val isRatingMapEpisodeWatched = remember(meta, ratingMapWatchedKeys, progressByVideoId) {
                { episode: MetaVideo ->
                    isEpisodeWatchedForActions(
                        meta = meta,
                        episode = episode,
                        watchedKeys = ratingMapWatchedKeys,
                        progressByVideoId = progressByVideoId,
                    )
                }
            }
            DetailSectionContainer(
                horizontalPadding = contentHorizontalPadding,
                contentMaxWidth = contentMaxWidth,
            ) {
                DetailEpisodeRatingMap(
                    meta = meta,
                    episodeRatingsVisibility = settings.episodeRatingsVisibility,
                    isEpisodeWatched = isRatingMapEpisodeWatched,
                    onEpisodeClick = onEpisodeClick,
                    onEpisodeLongPress = onEpisodeLongPress,
                )
            }
        }
    }

    if (!settings.tabLayout) {
        var ratingMapTopEmitted = false
        enabledItems
            .filter { it.key != MetaScreenSectionKey.RATING_MAP && sectionHasContent(it.key) }
            .forEach { section ->
                if (section.key == MetaScreenSectionKey.EPISODES && addLazyEpisodeItems()) return@forEach
                addSectionItem(
                    key = "detail-section-${section.key.name}",
                    sectionItems = listOf(section),
                    forceTabLayout = false,
                )
                if (
                    section.key == MetaScreenSectionKey.OVERVIEW &&
                    settings.ratingMapPosition == RatingMapPosition.TOP &&
                    ratingMapAvailable()
                ) {
                    ratingMapTopEmitted = true
                    addRatingMapItem()
                }
            }
        when (settings.ratingMapPosition) {
            RatingMapPosition.TOP -> if (!ratingMapTopEmitted && ratingMapAvailable()) addRatingMapItem()
            RatingMapPosition.BOTTOM -> if (ratingMapAvailable()) addRatingMapItem()
        }
        return
    }
""",
        "configuredMetaSectionItems positioned map",
    )


def apply_v120_details_layout_patch(source_dir: Path) -> None:
    _patch_remove_watched_action(source_dir)
    _patch_settings_repository(source_dir)
    _patch_strings(source_dir)
    _patch_ratings_settings(source_dir)
    _patch_settings_page(source_dir)
    _patch_detail_meta_info(source_dir)
    _patch_meta_details_screen(source_dir)
    print("[v1.20-module-2] Mark-watched removal & Rating Map overhaul applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_details_layout_patch.py <source_dir>")
    apply_v120_details_layout_patch(Path(sys.argv[1]).resolve())
