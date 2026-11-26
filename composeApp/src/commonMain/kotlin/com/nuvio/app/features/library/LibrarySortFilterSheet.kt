package com.nuvio.app.features.library

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
