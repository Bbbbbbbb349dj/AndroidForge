package com.nuvio.app.features.settings

import androidx.compose.runtime.Composable
import com.nuvio.app.core.ui.Chip
import com.nuvio.app.features.details.EpisodeRatingsVisibility
import com.nuvio.app.features.details.MetaScreenSettingsRepository
import com.nuvio.app.features.details.MetaScreenSettingsUiState
import com.nuvio.app.features.details.RatingMapPosition
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.layout_episode_ratings
import nuvio.composeapp.generated.resources.layout_episode_ratings_sub
import nuvio.composeapp.generated.resources.layout_overall_ratings
import nuvio.composeapp.generated.resources.layout_overall_ratings_sub_off
import nuvio.composeapp.generated.resources.layout_overall_ratings_sub_on
import nuvio.composeapp.generated.resources.layout_rating_map
import nuvio.composeapp.generated.resources.layout_rating_map_position
import nuvio.composeapp.generated.resources.layout_rating_map_position_sub
import nuvio.composeapp.generated.resources.layout_rating_map_sub
import nuvio.composeapp.generated.resources.settings_nav_bar_position_bottom
import nuvio.composeapp.generated.resources.settings_nav_bar_position_top
import nuvio.composeapp.generated.resources.layout_ratings_hide
import nuvio.composeapp.generated.resources.layout_ratings_hide_unwatched
import nuvio.composeapp.generated.resources.layout_ratings_show
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun RatingsSettings(
    isTablet: Boolean,
    uiState: MetaScreenSettingsUiState,
) {
    SettingsSwitchRow(
        title = stringResource(Res.string.layout_overall_ratings),
        description = stringResource(
            if (uiState.showOverallRatings) Res.string.layout_overall_ratings_sub_on
            else Res.string.layout_overall_ratings_sub_off,
        ),
        checked = uiState.showOverallRatings,
        isTablet = isTablet,
        onCheckedChange = MetaScreenSettingsRepository::setShowOverallRatings,
    )
    SettingsGroupDivider(isTablet = isTablet)
    SettingsChipRow(
        title = stringResource(Res.string.layout_episode_ratings),
        description = stringResource(Res.string.layout_episode_ratings_sub),
        isTablet = isTablet,
    ) {
        EpisodeRatingsVisibility.entries.forEach { visibility ->
            Chip(
                label = stringResource(
                    when (visibility) {
                        EpisodeRatingsVisibility.SHOW_ALL -> Res.string.layout_ratings_show
                        EpisodeRatingsVisibility.HIDE_EPISODES -> Res.string.layout_ratings_hide
                        EpisodeRatingsVisibility.HIDE_UNWATCHED_EPISODES -> Res.string.layout_ratings_hide_unwatched
                    },
                ),
                selected = uiState.episodeRatingsVisibility == visibility,
                onClick = { MetaScreenSettingsRepository.setEpisodeRatingsVisibility(visibility) },
            )
        }
    }
    SettingsGroupDivider(isTablet = isTablet)
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
}
