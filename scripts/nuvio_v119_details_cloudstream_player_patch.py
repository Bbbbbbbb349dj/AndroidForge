#!/usr/bin/env python3
"""Nuvio Enhanced v1.19 — Module 2:
- Phase 4: Synopsis ⋯ expansion (Nuvio + CloudStream, Hero + Details + Episodes) & Long-Press Quick Details Sheet
- Phase 5: Public Comments & Reviews without Trakt login (Trakt public v2 + TMDB /reviews + source attribution & links)
- Phase 6: CloudStream Home Catalogue Layout (Rows vs Columns) & Extension Hardening
- Phase 7: Dynamic Distance + Velocity Video Player Swipe-to-Seek & Player QoL
"""

from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[{label}] Expected anchor not found in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] Anchor matched {count} times in {path} (expected 1)")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 4.1 — Synopsis ⋯ Expansion Across Details, Episodes, Tablet & Hero
# ---------------------------------------------------------------------------

def patch_synopsis_expansion(source_dir: Path) -> None:
    # 1. ExpandableDescription.kt — persist state & render clear ⋯ Show more / Show less pill
    exp_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/ExpandableDescription.kt"
    exp_path.write_text(
        r"""package com.nuvio.app.features.details.components

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.details_show_less
import nuvio.composeapp.generated.resources.details_show_more
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun ExpandableDescription(
    text: String,
    collapsedMaxLines: Int,
    modifier: Modifier = Modifier,
    style: TextStyle = MaterialTheme.typography.bodyMedium,
    color: Color = MaterialTheme.colorScheme.onSurface,
) {
    var expanded by rememberSaveable(text) { mutableStateOf(false) }
    var canExpand by remember(text) { mutableStateOf(false) }
    val showMoreLabel = stringResource(Res.string.details_show_more)
    val showLessLabel = stringResource(Res.string.details_show_less)

    Column(
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize()
            .clickable(
                enabled = canExpand || expanded,
                role = Role.Button,
            ) { expanded = !expanded },
    ) {
        Text(
            text = text,
            style = style,
            color = color,
            maxLines = if (expanded) Int.MAX_VALUE else collapsedMaxLines,
            overflow = if (expanded) TextOverflow.Clip else TextOverflow.Ellipsis,
            onTextLayout = { result ->
                if (!expanded && result.hasVisualOverflow) {
                    canExpand = true
                }
            },
        )
        if (canExpand || expanded) {
            Spacer(modifier = Modifier.height(6.dp))
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(999.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f))
                    .border(
                        1.dp,
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                        RoundedCornerShape(999.dp),
                    )
                    .clickable(role = Role.Button) { expanded = !expanded }
                    .semantics {
                        contentDescription = if (expanded) showLessLabel else showMoreLabel
                    }
                    .padding(horizontal = 10.dp, vertical = 4.dp),
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (expanded) showLessLabel else "⋯ $showMoreLabel",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
    }
}
""",
        encoding="utf-8",
    )

    # 2. DetailMetaInfo.kt — remove broken 220dp nested scroll cap & make both Premium + Standard overview fully expandable via tap or ⋯ pill
    meta_info_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailMetaInfo.kt"
    _replace_once(
        meta_info_path,
        """            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = if (expanded) Int.MAX_VALUE else 4,
                overflow = TextOverflow.Ellipsis,
                lineHeight = 23.sp,
                onTextLayout = { result ->
                    if (!expanded) canExpand = result.hasVisualOverflow
                },
            )
            if (canExpand) {
                Text(
                    text = if (expanded) {
                        stringResource(Res.string.details_show_less)
                    } else {
                        stringResource(Res.string.details_show_more)
                    },
                    modifier = Modifier
                        .clickable { expanded = !expanded }
                        .padding(vertical = 6.dp),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold,
                )
            }""",
        """            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = if (expanded) Int.MAX_VALUE else 4,
                overflow = if (expanded) TextOverflow.Clip else TextOverflow.Ellipsis,
                lineHeight = 23.sp,
                modifier = Modifier.clickable(enabled = canExpand || expanded) { expanded = !expanded },
                onTextLayout = { result ->
                    if (!expanded && result.hasVisualOverflow) canExpand = true
                },
            )
            if (canExpand || expanded) {
                Row(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.68f))
                        .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.45f), RoundedCornerShape(999.dp))
                        .clickable { expanded = !expanded }
                        .padding(horizontal = 12.dp, vertical = 5.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (expanded) {
                            stringResource(Res.string.details_show_less)
                        } else {
                            "⋯ " + stringResource(Res.string.details_show_more)
                        },
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }""",
        "DetailMetaInfo.premiumStoryExpand",
    )

    _replace_once(
        meta_info_path,
        """        val scrollState = rememberScrollState()
        Column(modifier = Modifier.animateContentSize()) {
            Text(
                text = synopsis,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = if (expanded) Int.MAX_VALUE else 3,
                overflow = TextOverflow.Ellipsis,
                lineHeight = 22.sp,
                onTextLayout = { result -> if (!expanded) canExpand = result.hasVisualOverflow },
                modifier = if (expanded) {
                    Modifier.heightIn(max = 220.dp).verticalScroll(scrollState)
                } else {
                    Modifier
                },
            )
            if (canExpand) {
                Text(
                    text = if (expanded) {
                        stringResource(Res.string.details_show_less)
                    } else {
                        stringResource(Res.string.details_show_more)
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.clickable { expanded = !expanded }.padding(top = 4.dp),
                )
            }
        }""",
        """        Column(modifier = Modifier.animateContentSize()) {
            Text(
                text = synopsis,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = if (expanded) Int.MAX_VALUE else 3,
                overflow = if (expanded) TextOverflow.Clip else TextOverflow.Ellipsis,
                lineHeight = 22.sp,
                modifier = Modifier.clickable(enabled = canExpand || expanded) { expanded = !expanded },
                onTextLayout = { result ->
                    if (!expanded && result.hasVisualOverflow) canExpand = true
                },
            )
            if (canExpand || expanded) {
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f))
                        .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.45f), RoundedCornerShape(999.dp))
                        .clickable { expanded = !expanded }
                        .padding(horizontal = 12.dp, vertical = 5.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (expanded) {
                            stringResource(Res.string.details_show_less)
                        } else {
                            "⋯ " + stringResource(Res.string.details_show_more)
                        },
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }""",
        "DetailMetaInfo.standardOverviewExpand",
    )

    # 3. DetailSeriesContent.kt — allow episode cards to grow dynamically when episode synopsis ⋯ is expanded
    series_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailSeriesContent.kt"
    _replace_once(
        series_path,
        """            if (!video.overview.isNullOrBlank()) {
                Text(
                    text = video.overview,
                    style = MaterialTheme.typography.bodySmall.copy(
                        fontSize = metrics.bodyTextSize,
                        lineHeight = metrics.bodyLineHeight,
                    ),
                    color = Color.White.copy(alpha = 0.86f),
                    maxLines = metrics.overviewMaxLines,
                    overflow = TextOverflow.Ellipsis,
                )
            }""",
        """            if (!video.overview.isNullOrBlank()) {
                var epExpanded by remember(video.id) { mutableStateOf(false) }
                var epCanExpand by remember(video.id, video.overview) { mutableStateOf(false) }
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(
                        text = video.overview,
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontSize = metrics.bodyTextSize,
                            lineHeight = metrics.bodyLineHeight,
                        ),
                        color = Color.White.copy(alpha = 0.86f),
                        maxLines = if (epExpanded) Int.MAX_VALUE else metrics.overviewMaxLines,
                        overflow = if (epExpanded) TextOverflow.Clip else TextOverflow.Ellipsis,
                        onTextLayout = { result ->
                            if (!epExpanded && result.hasVisualOverflow) {
                                epCanExpand = true
                            }
                        },
                    )
                    if (epCanExpand || epExpanded) {
                        Text(
                            text = if (epExpanded) "Show less" else "⋯ Show more",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier
                                .clip(RoundedCornerShape(999.dp))
                                .clickable { epExpanded = !epExpanded }
                                .padding(vertical = 2.dp),
                        )
                    }
                }
            }""",
        "DetailSeriesContent.posterEpisodeExpand",
    )

    _replace_once(
        series_path,
        """            .height(sizing.cardHeight)
            .clip(cardShape)""",
        """            .heightIn(min = sizing.cardHeight)
            .clip(cardShape)""",
        "DetailSeriesContent.rowCardMinHeight",
    )

    _replace_once(
        series_path,
        """        Row(
            modifier = Modifier.fillMaxSize(),
        ) {
            Box(
                modifier = Modifier
                    .width(sizing.imageWidth)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(topStart = cornerRadius, bottomStart = cornerRadius)),
            ) {""",
        """        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Top,
        ) {
            Box(
                modifier = Modifier
                    .width(sizing.imageWidth)
                    .height(sizing.cardHeight)
                    .clip(RoundedCornerShape(topStart = cornerRadius, bottomStart = cornerRadius)),
            ) {""",
        "DetailSeriesContent.rowCardThumbHeight",
    )

    _replace_once(
        series_path,
        """            Column(
                modifier = Modifier
                    .fillMaxHeight()
                    .weight(1f)""",
        """            Column(
                modifier = Modifier
                    .weight(1f)""",
        "DetailSeriesContent.rowCardColumnHeight",
    )

    _replace_once(
        series_path,
        """                if (!video.overview.isNullOrBlank() && overviewText != null) {
                    Text(
                        text = overviewText,
                        style = MaterialTheme.typography.bodyMedium.copy(
                            fontSize = sizing.bodyTextSize,
                            lineHeight = sizing.bodyLineHeight,
                        ),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = sizing.overviewMaxLines,
                        overflow = TextOverflow.Ellipsis,
                    )
                }""",
        """                if (!video.overview.isNullOrBlank() && overviewText != null) {
                    var overviewExpanded by remember(video.id) { mutableStateOf(false) }
                    var overviewCanExpand by remember(video.id, overviewText) { mutableStateOf(false) }
                    Text(
                        text = overviewText,
                        style = MaterialTheme.typography.bodyMedium.copy(
                            fontSize = sizing.bodyTextSize,
                            lineHeight = sizing.bodyLineHeight,
                        ),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = if (overviewExpanded) Int.MAX_VALUE else sizing.overviewMaxLines,
                        overflow = if (overviewExpanded) TextOverflow.Clip else TextOverflow.Ellipsis,
                        onTextLayout = { result ->
                            if (!overviewExpanded && result.hasVisualOverflow) {
                                overviewCanExpand = true
                            }
                        },
                    )
                    if (overviewCanExpand || overviewExpanded) {
                        Text(
                            text = if (overviewExpanded) "Show less" else "⋯ Show more",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier
                                .clip(RoundedCornerShape(999.dp))
                                .clickable { overviewExpanded = !overviewExpanded }
                                .padding(vertical = 2.dp),
                        )
                    }
                }""",
        "DetailSeriesContent.rowEpisodeExpand",
    )

    # 4. HomeHeroSection.kt — make Home Hero synopsis expandable via tap / ⋯ pill too
    hero_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/home/components/HomeHeroSection.kt"
    _replace_once(
        hero_path,
        """        if (synopsis != null && showHeroOverview) {
            Spacer(modifier = Modifier.height(if (compactHeroMetadata) 6.dp else 10.dp))
            Text(
                text = synopsis,
                modifier = Modifier.fillMaxWidth(),
                style = if (compactHeroMetadata) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.72f),
                textAlign = if (layout.isTablet) TextAlign.Start else TextAlign.Center,
                maxLines = maxOverviewLines,
                overflow = TextOverflow.Ellipsis,
            )
        }""",
        """        if (synopsis != null && showHeroOverview) {
            var heroSynopsisExpanded by remember(item.type, item.id, synopsis) { mutableStateOf(false) }
            var heroSynopsisOverflow by remember(item.type, item.id, synopsis) { mutableStateOf(false) }
            Spacer(modifier = Modifier.height(if (compactHeroMetadata) 6.dp else 10.dp))
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = heroSynopsisOverflow || heroSynopsisExpanded) {
                        heroSynopsisExpanded = !heroSynopsisExpanded
                    },
                horizontalAlignment = if (layout.isTablet) Alignment.Start else Alignment.CenterHorizontally,
            ) {
                Text(
                    text = synopsis,
                    modifier = Modifier.fillMaxWidth(),
                    style = if (compactHeroMetadata) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.78f),
                    textAlign = if (layout.isTablet) TextAlign.Start else TextAlign.Center,
                    maxLines = if (heroSynopsisExpanded) Int.MAX_VALUE else maxOverviewLines,
                    overflow = if (heroSynopsisExpanded) TextOverflow.Clip else TextOverflow.Ellipsis,
                    onTextLayout = { result ->
                        if (!heroSynopsisExpanded && result.hasVisualOverflow) {
                            heroSynopsisOverflow = true
                        }
                    },
                )
                if (heroSynopsisOverflow || heroSynopsisExpanded) {
                    Text(
                        text = if (heroSynopsisExpanded) "Show less" else "⋯ Show more",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier
                            .padding(top = 4.dp)
                            .clip(RoundedCornerShape(999.dp))
                            .clickable { heroSynopsisExpanded = !heroSynopsisExpanded }
                            .padding(horizontal = 8.dp, vertical = 2.dp),
                    )
                }
            }
        }""",
        "HomeHeroSection.synopsisExpand",
    )


# ---------------------------------------------------------------------------
# Phase 4.2 — Long-Press Title Details Sheet (TitleQuickDetailsSheet.kt)
# ---------------------------------------------------------------------------

def patch_long_press_details_sheet(source_dir: Path) -> None:
    sheet_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/TitleQuickDetailsSheet.kt"
    sheet_path.write_text(
        r"""package com.nuvio.app.core.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.OpenInNew
import androidx.compose.material.icons.rounded.BookmarkAdd
import androidx.compose.material.icons.rounded.BookmarkAdded
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.DeleteOutline
import androidx.compose.material.icons.rounded.Visibility
import androidx.compose.material.icons.rounded.VisibilityOff
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.nuvio.app.core.format.extractReleaseYearForDisplay
import com.nuvio.app.features.details.MetaDetails
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.details.formatRuntimeForDisplay
import com.nuvio.app.features.home.MetaPreview
import com.nuvio.app.features.library.LocalLibraryCategory
import com.nuvio.app.features.library.normalizeLocalCategoryKeys

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
internal fun TitleQuickDetailsSheet(
    item: MetaPreview,
    isSaved: Boolean,
    savedCategoryKeys: List<String>,
    isWatched: Boolean,
    isRemoteLibrarySource: Boolean,
    onOpenDetails: () -> Unit,
    onSelectLocalCategory: (LocalLibraryCategory) -> Unit,
    onOpenRemoteListPicker: () -> Unit,
    onRemoveFromLibrary: () -> Unit,
    onToggleWatched: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scrollState = rememberScrollState()
    var enrichedDetails by remember(item.type, item.id) { mutableStateOf<MetaDetails?>(null) }

    LaunchedEffect(item.type, item.id) {
        enrichedDetails = runCatching {
            MetaDetailsRepository.fetch(item.type, item.id)
        }.getOrNull()
    }

    val title = enrichedDetails?.name?.takeIf(String::isNotBlank) ?: item.name
    val posterUrl = enrichedDetails?.poster?.takeIf(String::isNotBlank) ?: item.poster
    val releaseYear = extractReleaseYearForDisplay(
        enrichedDetails?.releaseInfo ?: item.releaseInfo,
    )
    val runtimeLabel = enrichedDetails?.runtime?.let(::formatRuntimeForDisplay)
    val ratingLabel = (enrichedDetails?.imdbRating ?: item.imdbRating)
        ?.takeIf { it > 0.0 }
        ?.let { ((it * 10.0).toInt() / 10.0).toString() }
    val ageRating = (enrichedDetails?.ageRating ?: item.ageRating)?.takeIf(String::isNotBlank)
    val genres = (enrichedDetails?.genres?.takeIf { it.isNotEmpty() } ?: item.genres).take(6)
    val synopsis = (enrichedDetails?.description?.takeIf(String::isNotBlank)
        ?: item.description?.takeIf(String::isNotBlank))
        ?.trim()
    val castMembers = enrichedDetails?.cast?.take(5).orEmpty()
    val sourceBadge = remember(item.id, item.addonName) {
        when {
            !item.addonName.isNullOrBlank() -> item.addonName
            item.id.startsWith("cloudstream:", ignoreCase = true) -> {
                val provider = item.id.removePrefix("cloudstream:").substringBefore(':')
                "CloudStream • $provider"
            }
            item.id.startsWith("tmdb:", ignoreCase = true) -> "TMDB"
            item.id.startsWith("tt", ignoreCase = true) -> "IMDb / Addons"
            else -> null
        }
    }
    val typeBadge = remember(item.type) {
        when (item.type.trim().lowercase()) {
            "movie" -> "Movie"
            "series", "tv", "show" -> "Series"
            "anime" -> "Anime"
            else -> item.type.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        }
    }

    NuvioModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        contentColor = MaterialTheme.colorScheme.onSurface,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 640.dp)
                .verticalScroll(scrollState)
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.Top,
            ) {
                Box(
                    modifier = Modifier
                        .width(96.dp)
                        .aspectRatio(2f / 3f)
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                ) {
                    if (!posterUrl.isNullOrBlank()) {
                        AsyncImage(
                            model = posterUrl,
                            contentDescription = title,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop,
                        )
                    }
                }

                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        QuickDetailBadge(text = typeBadge, accent = true)
                        releaseYear?.let { QuickDetailBadge(text = it) }
                        runtimeLabel?.let { QuickDetailBadge(text = it) }
                        ratingLabel?.let { QuickDetailBadge(text = "★ $it") }
                        ageRating?.let { QuickDetailBadge(text = it) }
                        sourceBadge?.let { QuickDetailBadge(text = it) }
                    }

                    if (genres.isNotEmpty()) {
                        Text(
                            text = genres.joinToString(" • "),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }

            if (!synopsis.isNullOrBlank()) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        text = "Synopsis",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        text = synopsis,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }

            if (castMembers.isNotEmpty()) {
                Text(
                    text = "Cast: " + castMembers.joinToString(", ") { it.name },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(14.dp))
                        .background(MaterialTheme.colorScheme.primary)
                        .clickable(onClick = onOpenDetails)
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Rounded.OpenInNew,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Open Full Details",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                }

                Row(
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
            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = if (isSaved) Icons.Rounded.BookmarkAdded else Icons.Rounded.BookmarkAdd,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp),
                        )
                        Text(
                            text = if (isSaved) "Library Category" else "Save to Library",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                    }

                    if (isSaved) {
                        Row(
                            modifier = Modifier
                                .clip(RoundedCornerShape(999.dp))
                                .clickable(onClick = onRemoveFromLibrary)
                                .padding(horizontal = 10.dp, vertical = 4.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.DeleteOutline,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.error,
                                modifier = Modifier.size(16.dp),
                            )
                            Text(
                                text = "Remove",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                    }
                }

                if (isRemoteLibrarySource) {
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f))
                            .border(
                                1.dp,
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                                RoundedCornerShape(12.dp),
                            )
                            .clickable(onClick = onOpenRemoteListPicker)
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = if (isSaved) "Manage Synced Lists…" else "Choose Synced Lists…",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                } else {
                    val normalizedSelected = remember(savedCategoryKeys, isSaved) {
                        if (isSaved) normalizeLocalCategoryKeys(savedCategoryKeys).toSet() else emptySet()
                    }

                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        LocalLibraryCategory.entries.forEach { category ->
                            val selected = category.key in normalizedSelected
                            val bg = if (selected) {
                                MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
                            } else {
                                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f)
                            }
                            val border = if (selected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)
                            }
                            Row(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(999.dp))
                                    .background(bg)
                                    .border(1.dp, border, RoundedCornerShape(999.dp))
                                    .clickable { onSelectLocalCategory(category) }
                                    .padding(horizontal = 12.dp, vertical = 7.dp),
                                horizontalArrangement = Arrangement.spacedBy(5.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                if (selected) {
                                    Icon(
                                        imageVector = Icons.Rounded.Check,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.size(15.dp),
                                    )
                                }
                                Text(
                                    text = category.label,
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                                    color = if (selected) {
                                        MaterialTheme.colorScheme.primary
                                    } else {
                                        MaterialTheme.colorScheme.onSurface
                                    },
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun QuickDetailBadge(
    text: String,
    accent: Boolean = false,
) {
    val bg = if (accent) {
        MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    val fg = if (accent) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(bg)
            .padding(horizontal = 9.dp, vertical = 4.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            color = fg,
            maxLines = 1,
        )
    }
}
""",
        encoding="utf-8",
    )

    main_app_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"
    _replace_once(
        main_app_path,
        "import com.nuvio.app.core.ui.NuvioPosterZoomActionOverlay\n",
        "import com.nuvio.app.core.ui.NuvioPosterZoomActionOverlay\nimport com.nuvio.app.core.ui.TitleQuickDetailsSheet\nimport com.nuvio.app.features.library.normalizeLocalCategoryKeys\n",
        "MainAppContent.importTitleQuickDetailsSheet",
    )

    _replace_once(
        main_app_path,
        """            selectedPosterActionTarget?.let { posterActionTarget ->
                key(posterActionTarget) {
                    val preview = posterActionTarget.preview
                    val isSaved = LibraryRepository.isSaved(preview.id, preview.type)
                    val isWatched = WatchingState.isPosterWatched(
                        watchedKeys = watchedUiState.watchedKeys,
                        item = preview,
                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                    )
                    val removesFromLibrary = isSaved &&
                        (posterActionTarget.libraryItem != null || !isRemoteLibrarySource)
                    NuvioPosterZoomActionOverlay(
                        imageUrl = selectedPosterAnchor?.imageUrl ?: preview.poster,
                        title = preview.name,
                        subtitle = preview.releaseInfo
                            ?.takeIf { it.isNotBlank() }
                            ?.let { formatReleaseDateForDisplay(it) }
                            ?: preview.type.replaceFirstChar { char ->
                                if (char.isLowerCase()) char.titlecase() else char.toString()
                            },
                        isWatched = isWatched,
                        anchor = selectedPosterAnchor,
                        actions = listOf(
                            PosterZoomOverlayAction(
                                icon = if (isSaved) Icons.Default.DeleteOutline else Icons.Default.Add,
                                label = if (isSaved) {
                                    stringResource(Res.string.hero_remove_from_library)
                                } else {
                                    stringResource(Res.string.hero_add_to_library)
                                },
                                isDestructive = removesFromLibrary,
                                exitAnimation = if (removesFromLibrary && !isRemoteLibrarySource) {
                                    PosterZoomOverlayExitAnimation.DISINTEGRATE
                                } else {
                                    PosterZoomOverlayExitAnimation.COLLAPSE
                                },
                                onSelected = {
                                    val libraryItem = posterActionTarget.libraryItem
                                        ?: preview.toLibraryItem(savedAtEpochMs = 0L)
                                    if (posterActionTarget.libraryItem != null) {
                                        val animationKey = posterActionTarget.libraryListKey
                                            ?.let { listKey -> librarySectionItemKey(listKey, libraryItem) }
                                        if (isRemoteLibrarySource) {
                                            coroutineScope.launch {
                                                val listKey = posterActionTarget.libraryListKey
                                                val removeMembership: suspend (Set<TrackingProviderId>) ->
                                                    TrackingMembershipApplyResult = { confirmedProviders ->
                                                    if (listKey.isNullOrBlank()) {
                                                        val currentMembership = LibraryRepository.getMembershipSnapshot(libraryItem)
                                                        LibraryRepository.applyMembershipChanges(
                                                            item = libraryItem,
                                                            desiredMembership = currentMembership.mapValues { false },
                                                            confirmedRemovalProviders = confirmedProviders,
                                                        )
                                                    } else {
                                                        LibraryRepository.removeFromList(
                                                            item = libraryItem,
                                                            listKey = listKey,
                                                            confirmedRemovalProviders = confirmedProviders,
                                                        )
                                                    }
                                                }
                                                val removeMembershipWithAnimation:
                                                    suspend (Set<TrackingProviderId>) -> TrackingMembershipApplyResult =
                                                    { confirmedProviders ->
                                                        val request = if (removesFromLibrary) {
                                                            animationKey?.let(libraryDisintegrationRequests::arm)
                                                        } else {
                                                            null
                                                        }
                                                        try {
                                                            removeMembership(confirmedProviders).also { result ->
                                                                if (result.requiresRemovalConfirmation && request != null) {
                                                                    libraryDisintegrationRequests.cancel(request)
                                                                }
                                                            }
                                                        } catch (error: Throwable) {
                                                            request?.let(libraryDisintegrationRequests::cancel)
                                                            throw error
                                                        }
                                                    }
                                                executeTrackingMembershipOperation(
                                                    operation = { removeMembershipWithAnimation(emptySet()) },
                                                    onSuccess = { result ->
                                                        if (result.requiresRemovalConfirmation) {
                                                            pendingTrackingRemoval = PendingTrackingMembershipRemoval(
                                                                itemTitle = libraryItem.name,
                                                                confirmations = result.requiredRemovalConfirmations,
                                                                retry = removeMembershipWithAnimation,
                                                                onApplied = {},
                                                                onFailure = { error ->
                                                                    NuvioToastController.show(
                                                                        error.message
                                                                            ?: trackingListsUpdateFailedMessage,
                                                                    )
                                                                },
                                                            )
                                                        }
                                                    },
                                                    onFailure = { error ->
                                                        NuvioToastController.show(
                                                            error.message ?: trackingListsUpdateFailedMessage,
                                                        )
                                                    },
                                                )
                                            }
                                        } else {
                                            if (removesFromLibrary) {
                                                animationKey?.let(libraryDisintegrationRequests::arm)
                                            }
                                            LibraryRepository.remove(libraryItem.id)
                                        }
                                    } else {
                                        pickerItem = libraryItem
                                        pickerTitle = preview.name
                                        val initialTabs = LibraryRepository.libraryListTabs(libraryItem)
                                        pickerTabs = initialTabs
                                        pickerMembership = initialTabs.associate { tab ->
                                            tab.key to (!isSaved && tab.key == LocalLibraryCategory.PLAN_TO_WATCH.key)
                                        }
                                        pickerPending = true
                                        pickerError = null
                                        showLibraryListPicker = true
                                        coroutineScope.launch {
                                            runCatching {
                                                val snapshot = LibraryRepository.getMembershipSnapshot(libraryItem)
                                                val tabs = LibraryRepository.libraryListTabs(libraryItem)
                                                val hasAny = tabs.any { snapshot[it.key] == true }
                                                pickerTabs = tabs
                                                pickerMembership = tabs.associate { tab ->
                                                    val checked = if (hasAny) {
                                                        snapshot[tab.key] == true
                                                    } else {
                                                        tab.key == LocalLibraryCategory.PLAN_TO_WATCH.key
                                                    }
                                                    tab.key to checked
                                                }
                                            }.onFailure { error ->
                                                pickerError = error.message ?: getString(Res.string.trakt_lists_load_failed)
                                            }
                                            pickerPending = false
                                        }
                                    }
                                },
                            ),
                            *(if (isSaved) {
                                arrayOf(
                                    PosterZoomOverlayAction(
                                        icon = Icons.Default.Add,
                                        label = "Change Category",
                                        onSelected = {
                                            val libraryItem = posterActionTarget.libraryItem
                                                ?: preview.toLibraryItem(savedAtEpochMs = 0L)
                                            pickerItem = libraryItem
                                            pickerTitle = preview.name
                                            pickerTabs = LibraryRepository.libraryListTabs(libraryItem)
                                            pickerMembership = pickerTabs.associate { it.key to false }
                                            pickerPending = true
                                            pickerError = null
                                            showLibraryListPicker = true
                                            coroutineScope.launch {
                                                runCatching {
                                                    val snapshot = LibraryRepository.getMembershipSnapshot(libraryItem)
                                                    val tabs = LibraryRepository.libraryListTabs(libraryItem)
                                                    pickerTabs = tabs
                                                    pickerMembership = tabs.associate { tab ->
                                                        tab.key to (snapshot[tab.key] == true)
                                                    }
                                                }.onFailure { error ->
                                                    pickerError = error.message ?: getString(Res.string.trakt_lists_load_failed)
                                                }
                                                pickerPending = false
                                            }
                                        },
                                    ),
                                )
                            } else {
                                emptyArray()
                            }),
                            PosterZoomOverlayAction(
                                icon = if (isWatched) Icons.Default.CheckCircle else Icons.Default.CheckCircleOutline,
                                label = if (isWatched) {
                                    stringResource(Res.string.hero_mark_unwatched)
                                } else {
                                    stringResource(Res.string.hero_mark_watched)
                                },
                                onSelected = {
                                    coroutineScope.launch {
                                        WatchingActions.togglePosterWatched(preview)
                                    }
                                },
                            ),
                        ),
                        backdrop = posterOverlayBackdrop,
                        onDismissed = {
                            selectedPosterActionTarget = null
                            selectedPosterAnchor = null
                        },
                    )
                }
            }""",
        """            selectedPosterActionTarget?.let { posterActionTarget ->
                key(posterActionTarget) {
                    val preview = posterActionTarget.preview
                    val savedItem = remember(libraryUiState.items, preview.id, preview.type) {
                        LibraryRepository.savedItem(preview.id, preview.type)
                    }
                    val isSaved = savedItem != null || LibraryRepository.isSaved(preview.id, preview.type)
                    val isWatched = WatchingState.isPosterWatched(
                        watchedKeys = watchedUiState.watchedKeys,
                        item = preview,
                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                    )
                    TitleQuickDetailsSheet(
                        item = preview,
                        isSaved = isSaved,
                        savedCategoryKeys = savedItem?.listKeys?.toList().orEmpty(),
                        isWatched = isWatched,
                        isRemoteLibrarySource = isRemoteLibrarySource,
                        onOpenDetails = {
                            selectedPosterActionTarget = null
                            selectedPosterAnchor = null
                            navController.navigate(
                                DetailRoute(
                                    type = preview.type,
                                    id = preview.id,
                                    title = preview.name,
                                ),
                            )
                        },
                        onSelectLocalCategory = { category ->
                            val baseItem = savedItem
                                ?: posterActionTarget.libraryItem
                                ?: preview.toLibraryItem(savedAtEpochMs = 0L)
                            val existingKeys = if (savedItem != null) {
                                normalizeLocalCategoryKeys(savedItem.listKeys).toList()
                            } else {
                                emptyList()
                            }
                            val nextKeys = if (category.isWatchStatus) {
                                existingKeys.filterNot { key ->
                                    LocalLibraryCategory.fromKey(key)?.isWatchStatus == true
                                } + category.key
                            } else if (category.key in existingKeys) {
                                existingKeys.filterNot { it == category.key }
                            } else {
                                existingKeys + category.key
                            }
                            LibraryRepository.save(
                                baseItem.copy(
                                    listKeys = normalizeLocalCategoryKeys(nextKeys),
                                ),
                            )
                            NuvioToastController.show("Saved to ${category.label}")
                        },
                        onOpenRemoteListPicker = {
                            val libraryItem = savedItem
                                ?: posterActionTarget.libraryItem
                                ?: preview.toLibraryItem(savedAtEpochMs = 0L)
                            selectedPosterActionTarget = null
                            selectedPosterAnchor = null
                            pickerItem = libraryItem
                            pickerTitle = preview.name
                            val initialTabs = LibraryRepository.libraryListTabs(libraryItem)
                            pickerTabs = initialTabs
                            pickerMembership = initialTabs.associate { tab ->
                                tab.key to (!isSaved && tab.key == LocalLibraryCategory.PLAN_TO_WATCH.key)
                            }
                            pickerPending = true
                            pickerError = null
                            showLibraryListPicker = true
                            coroutineScope.launch {
                                runCatching {
                                    val snapshot = LibraryRepository.getMembershipSnapshot(libraryItem)
                                    val tabs = LibraryRepository.libraryListTabs(libraryItem)
                                    pickerTabs = tabs
                                    pickerMembership = tabs.associate { tab ->
                                        tab.key to (snapshot[tab.key] == true)
                                    }
                                }.onFailure { error ->
                                    pickerError = error.message ?: getString(Res.string.trakt_lists_load_failed)
                                }
                                pickerPending = false
                            }
                        },
                        onRemoveFromLibrary = {
                            val libraryItem = savedItem
                                ?: posterActionTarget.libraryItem
                                ?: preview.toLibraryItem(savedAtEpochMs = 0L)
                            selectedPosterActionTarget = null
                            selectedPosterAnchor = null
                            LibraryRepository.remove(libraryItem.id)
                        },
                        onToggleWatched = {
                            coroutineScope.launch {
                                WatchingActions.togglePosterWatched(preview)
                            }
                        },
                        onDismiss = {
                            selectedPosterActionTarget = null
                            selectedPosterAnchor = null
                        },
                    )
                }
            }""",
        "MainAppContent.useTitleQuickDetailsSheet",
    )


# ---------------------------------------------------------------------------
# Phase 5 — Public Reviews & Comments Without Trakt Login
# ---------------------------------------------------------------------------

def patch_public_reviews_without_login(source_dir: Path) -> None:
    # 1. TraktCommentsModels.kt — add sourceName and sourceUrl with backward-compatible defaults
    models_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/trakt/TraktCommentsModels.kt"
    _replace_once(
        models_path,
        """    val createdAt: String? = null,
    val updatedAt: String? = null,
) {""",
        """    val createdAt: String? = null,
    val updatedAt: String? = null,
    val sourceName: String = "Trakt",
    val sourceUrl: String? = null,
) {""",
        "TraktCommentsModels.sourceAttributionFields",
    )

    # 2. TraktAuthRepository.kt — add publicOrAuthorizedHeaders() using TraktConfig.CLIENT_ID
    auth_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/trakt/TraktAuthRepository.kt"
    _replace_once(
        auth_path,
        """        return mapOf(
            "trakt-api-version" to API_VERSION,
            "trakt-api-key" to TraktConfig.CLIENT_ID,
            "Authorization" to "Bearer $accessToken",
        )
    }""",
        """        return mapOf(
            "trakt-api-version" to API_VERSION,
            "trakt-api-key" to TraktConfig.CLIENT_ID,
            "Authorization" to "Bearer $accessToken",
        )
    }

    suspend fun publicOrAuthorizedHeaders(profileId: Int = currentProfileId): Map<String, String> {
        authorizedHeaders(profileId)?.let { return it }
        return mapOf(
            "trakt-api-version" to API_VERSION,
            "trakt-api-key" to TraktConfig.CLIENT_ID,
        )
    }""",
        "TraktAuthRepository.publicOrAuthorizedHeaders",
    )

    # 3. TmdbService.kt — add official public TMDB /3/{movie|tv}/{id}/reviews fetcher
    tmdb_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/tmdb/TmdbService.kt"
    _replace_once(
        tmdb_path,
        """    internal fun normalizeMediaType(mediaType: String): String =""",
        """    suspend fun fetchPublicReviews(
        tmdbId: String,
        mediaType: String,
        page: Int = 1,
    ): TmdbPublicReviewsPage? {
        val apiKey = TmdbSettingsRepository.effectiveApiKey()
        if (apiKey.isBlank() || tmdbId.isBlank()) return null
        val normalizedType = normalizeMediaType(mediaType)
        val endpoint = when (normalizedType) {
            "tv" -> "tv/$tmdbId/reviews"
            "movie" -> "movie/$tmdbId/reviews"
            else -> return null
        }
        return fetch<TmdbPublicReviewsPage>(
            endpoint = endpoint,
            apiKey = apiKey,
            query = mapOf("page" to page.coerceAtLeast(1).toString()),
        )
    }

    internal fun normalizeMediaType(mediaType: String): String =""",
        "TmdbService.fetchPublicReviews",
    )

    tmdb_text = tmdb_path.read_text(encoding="utf-8")
    tmdb_text += """

@Serializable
data class TmdbPublicReviewsPage(
    val page: Int = 1,
    @SerialName("total_pages") val totalPages: Int = 0,
    @SerialName("total_results") val totalResults: Int = 0,
    val results: List<TmdbPublicReviewDto> = emptyList(),
)

@Serializable
data class TmdbPublicReviewDto(
    val id: String = "",
    val author: String? = null,
    @SerialName("author_details") val authorDetails: TmdbPublicReviewAuthorDto? = null,
    val content: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    val url: String? = null,
)

@Serializable
data class TmdbPublicReviewAuthorDto(
    val name: String? = null,
    val username: String? = null,
    val rating: Double? = null,
)
"""
    tmdb_path.write_text(tmdb_text, encoding="utf-8")

    # 4. TraktCommentsRepository.kt — public Trakt v2 + public TMDB /reviews + title-search fallback for CloudStream
    comments_repo_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/trakt/TraktCommentsRepository.kt"
    comments_repo_path.write_text(
        r"""package com.nuvio.app.features.trakt

import co.touchlab.kermit.Logger
import com.nuvio.app.core.format.extractReleaseYearForDisplay
import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.addons.httpRequestRaw
import com.nuvio.app.features.details.MetaDetails
import com.nuvio.app.features.tmdb.TmdbPublicReviewDto
import com.nuvio.app.features.tmdb.TmdbService
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.details_comments_trakt_load_failed_with_code
import nuvio.composeapp.generated.resources.trakt_user_fallback
import org.jetbrains.compose.resources.getString
import kotlin.math.abs
import kotlin.math.roundToInt

private const val COMMENTS_SORT = "likes"
private const val COMMENTS_LIMIT = 50
private const val COMMENTS_CACHE_TTL_MS = 10 * 60_000L
private val INLINE_SPOILER_REGEX = Regex("(?is)\\[spoiler\\].*?\\[/spoiler\\]")
private val INLINE_SPOILER_TAG_REGEX = Regex("\\[/?spoiler\\]", RegexOption.IGNORE_CASE)

private val commentsJson = Json { ignoreUnknownKeys = true }

/**
 * Public reviews & comments aggregator.
 *
 * Source policy & attribution:
 * - Uses public, unauthenticated Trakt API v2 comment/review endpoints (`trakt-api-key`)
 *   and official TMDB API v3 `/reviews` endpoints — NO user login required.
 * - IMDb and Letterboxd prohibit unauthenticated HTML scraping in their Terms of Service;
 *   we intentionally avoid brittle/non-compliant scrapers and instead attribute every review
 *   with its official source (`Trakt` or `TMDB`), author handle, and canonical `sourceUrl`.
 */
object TraktCommentsRepository {
    private val log = Logger.withTag("PublicReviews")

    private data class TimedCache(
        val pages: Map<Int, List<TraktCommentReview>>,
        val pageCount: Int,
        val itemCount: Int,
        val updatedAtMs: Long,
    )

    private val cacheMutex = Mutex()
    private val cache = mutableMapOf<String, TimedCache>()

    suspend fun getCommentsPage(
        meta: MetaDetails,
        page: Int = 1,
        forceRefresh: Boolean = false,
    ): TraktCommentsPage {
        val type = resolveCommentsType(meta) ?: return TraktCommentsPage(emptyList(), page, 0, 0)
        val cacheKey = "${type.apiValue}|${meta.id.trim()}|${meta.name.trim().lowercase()}"

        if (forceRefresh) {
            cacheMutex.withLock { cache.remove(cacheKey) }
        } else {
            cacheMutex.withLock {
                val cached = cache[cacheKey]
                if (
                    cached != null &&
                    currentTimeMillis() - cached.updatedAtMs <= COMMENTS_CACHE_TTL_MS &&
                    cached.pages.containsKey(page)
                ) {
                    return TraktCommentsPage(
                        items = cached.pages.getValue(page),
                        currentPage = page,
                        pageCount = cached.pageCount,
                        itemCount = cached.itemCount,
                    )
                }
            }
        }

        val resolvedIds = resolvePublicReviewIds(meta, type)
        if (resolvedIds.traktTarget == null && resolvedIds.tmdbId == null) {
            return TraktCommentsPage(emptyList(), page, 0, 0)
        }

        return coroutineScope {
            val traktDeferred = async {
                resolvedIds.traktTarget?.let { target ->
                    runCatching { fetchTraktPublicPage(target, page) }
                        .onFailure { err -> log.w(err) { "Trakt public comments fetch failed for ${target.pathId}" } }
                        .getOrNull()
                }
            }
            val tmdbDeferred = async {
                resolvedIds.tmdbId?.let { tmdbId ->
                    runCatching { fetchTmdbPublicPage(tmdbId, meta.type, page) }
                        .onFailure { err -> log.w(err) { "TMDB public reviews fetch failed for tmdbId=$tmdbId" } }
                        .getOrNull()
                }
            }

            val traktPage = traktDeferred.await()
            val tmdbPage = tmdbDeferred.await()

            val merged = mergePublicReviewLists(
                traktItems = traktPage?.items.orEmpty(),
                tmdbItems = tmdbPage?.items.orEmpty(),
            )
            val totalPages = maxOf(traktPage?.pageCount ?: 0, tmdbPage?.pageCount ?: 0)
                .let { if (it == 0 && merged.isNotEmpty()) page else it }
            val totalItems = (traktPage?.itemCount ?: 0) + (tmdbPage?.itemCount ?: 0)

            cacheMutex.withLock {
                val cached = cache[cacheKey]
                cache[cacheKey] = TimedCache(
                    pages = (cached?.pages.orEmpty()) + (page to merged),
                    pageCount = totalPages,
                    itemCount = totalItems.coerceAtLeast(merged.size),
                    updatedAtMs = currentTimeMillis(),
                )
            }

            TraktCommentsPage(
                items = merged,
                currentPage = page,
                pageCount = totalPages,
                itemCount = totalItems.coerceAtLeast(merged.size),
            )
        }
    }

    fun clearCache() {
        cache.clear()
    }

    private suspend fun fetchTraktPublicPage(
        target: ResolvedCommentsTarget,
        page: Int,
    ): TraktCommentsPage {
        val headers = TraktAuthRepository.publicOrAuthorizedHeaders()
        val endpoint = when (target.type) {
            TraktCommentsType.MOVIE -> "movies"
            TraktCommentsType.SHOW -> "shows"
        }
        val url = "https://api.trakt.tv/$endpoint/${target.pathId}/comments/$COMMENTS_SORT?page=$page&limit=$COMMENTS_LIMIT"
        val response = httpRequestRaw(
            method = "GET",
            url = url,
            headers = headers,
            body = "",
        )
        if (response.status == 404) {
            return TraktCommentsPage(emptyList(), page, 0, 0)
        }
        if (response.status !in 200..299) {
            throw IllegalStateException(
                getString(Res.string.details_comments_trakt_load_failed_with_code, response.status),
            )
        }
        val dtos = commentsJson.decodeFromString<List<TraktCommentDto>>(response.body)
        val pageCount = response.headers["X-Pagination-Page-Count"]?.toIntOrNull()
            ?: response.headers["x-pagination-page-count"]?.toIntOrNull()
            ?: page
        val itemCount = response.headers["X-Pagination-Item-Count"]?.toIntOrNull()
            ?: response.headers["x-pagination-item-count"]?.toIntOrNull()
            ?: dtos.size
        val selected = filterDisplayableComments(dtos).map(::toTraktReviewModel)
        return TraktCommentsPage(
            items = selected,
            currentPage = page,
            pageCount = pageCount,
            itemCount = itemCount,
        )
    }

    private suspend fun fetchTmdbPublicPage(
        tmdbId: String,
        mediaType: String,
        page: Int,
    ): TraktCommentsPage {
        val response = TmdbService.fetchPublicReviews(
            tmdbId = tmdbId,
            mediaType = mediaType,
            page = page,
        ) ?: return TraktCommentsPage(emptyList(), page, 0, 0)
        val mapped = response.results
            .filter { !it.content.isNullOrBlank() }
            .map(::toTmdbReviewModel)
        return TraktCommentsPage(
            items = mapped,
            currentPage = response.page,
            pageCount = response.totalPages,
            itemCount = response.totalResults,
        )
    }

    private suspend fun resolvePublicReviewIds(
        meta: MetaDetails,
        type: TraktCommentsType,
    ): ResolvedPublicReviewIds {
        var imdbId = resolveDirectPathId(meta)
        var tmdbId = resolveTmdbCandidate(meta)?.toString()

        if (tmdbId == null && imdbId != null) {
            tmdbId = runCatching { TmdbService.ensureTmdbId(imdbId, meta.type) }.getOrNull()
        }

        if (imdbId == null && tmdbId == null && meta.name.isNotBlank()) {
            val year = extractReleaseYearForDisplay(meta.releaseInfo)?.toIntOrNull()
            val searched = runCatching {
                TmdbService.ensureTmdbIdBySearch(
                    title = meta.name,
                    mediaType = meta.type,
                    year = year,
                )
            }.getOrNull()
            if (searched != null) {
                tmdbId = searched.first
                imdbId = searched.second
            }
        }

        val traktTarget = when {
            !imdbId.isNullOrBlank() -> ResolvedCommentsTarget(type, imdbId)
            tmdbId?.toIntOrNull() != null -> resolveViaTraktSearch(type, tmdbId.toInt())
            else -> null
        }

        return ResolvedPublicReviewIds(
            traktTarget = traktTarget,
            tmdbId = tmdbId,
        )
    }

    private fun resolveCommentsType(meta: MetaDetails): TraktCommentsType? =
        when (meta.type.trim().lowercase()) {
            "movie", "film" -> TraktCommentsType.MOVIE
            "series", "show", "tv", "anime" -> TraktCommentsType.SHOW
            else -> null
        }

    private fun resolveDirectPathId(meta: MetaDetails): String? {
        val id = meta.id.trim()
        if (id.startsWith("tt", ignoreCase = true) && id.length >= 7) return id.substringBefore(':')
        for (part in id.split(':')) {
            val trimmed = part.trim()
            if (trimmed.startsWith("tt", ignoreCase = true) && trimmed.length >= 7) return trimmed
        }
        return null
    }

    private fun resolveTmdbCandidate(meta: MetaDetails): Int? {
        val id = meta.id.trim()
        for (part in id.split(':')) {
            val trimmed = part.trim()
            if (!trimmed.startsWith("tt", ignoreCase = true) && trimmed.isNotEmpty() && trimmed.all(Char::isDigit)) {
                return trimmed.toIntOrNull()
            }
        }
        return null
    }

    private suspend fun resolveViaTraktSearch(
        type: TraktCommentsType,
        tmdbId: Int,
    ): ResolvedCommentsTarget? {
        val headers = TraktAuthRepository.publicOrAuthorizedHeaders()
        val url = "https://api.trakt.tv/search/tmdb/$tmdbId?type=${type.apiValue}"
        return try {
            val responseText = httpGetTextWithHeaders(url, headers)
            val results = commentsJson.decodeFromString<List<TraktCommentsSearchResultDto>>(responseText)
            val matched = results.firstOrNull {
                it.type.equals(type.apiValue, ignoreCase = true)
            }
            val ids = when (type) {
                TraktCommentsType.MOVIE -> matched?.movie?.ids
                TraktCommentsType.SHOW -> matched?.show?.ids
            }
            val pathId = ids?.bestPathId() ?: return null
            ResolvedCommentsTarget(type, pathId)
        } catch (e: Exception) {
            log.w(e) { "TMDB→Trakt lookup failed for tmdbId=$tmdbId" }
            null
        }
    }
}

private data class ResolvedCommentsTarget(
    val type: TraktCommentsType,
    val pathId: String,
)

private data class ResolvedPublicReviewIds(
    val traktTarget: ResolvedCommentsTarget?,
    val tmdbId: String?,
)

private fun TraktCommentsIdsDto.bestPathId(): String? =
    when {
        !imdb.isNullOrBlank() -> imdb
        trakt != null -> trakt.toString()
        !slug.isNullOrBlank() -> slug
        else -> null
    }

internal fun mergePublicReviewLists(
    traktItems: List<TraktCommentReview>,
    tmdbItems: List<TraktCommentReview>,
): List<TraktCommentReview> {
    val result = mutableListOf<TraktCommentReview>()
    val seenFingerprints = mutableSetOf<String>()
    val maxSize = maxOf(traktItems.size, tmdbItems.size)
    for (index in 0 until maxSize) {
        if (index < tmdbItems.size) {
            val item = tmdbItems[index]
            val fp = "${item.authorDisplayName.lowercase()}|${item.comment.take(80).lowercase()}"
            if (seenFingerprints.add(fp)) result += item
        }
        if (index < traktItems.size) {
            val item = traktItems[index]
            val fp = "${item.authorDisplayName.lowercase()}|${item.comment.take(80).lowercase()}"
            if (seenFingerprints.add(fp)) result += item
        }
    }
    return result
}

private fun filterDisplayableComments(comments: List<TraktCommentDto>): List<TraktCommentDto> =
    comments.filter { !it.comment.isNullOrBlank() }

private fun containsInlineSpoilers(comment: String?): Boolean {
    if (comment.isNullOrBlank()) return false
    return INLINE_SPOILER_REGEX.containsMatchIn(comment)
}

private fun stripInlineSpoilerMarkup(comment: String?): String {
    if (comment.isNullOrBlank()) return ""
    return comment
        .replace(INLINE_SPOILER_TAG_REGEX, "")
        .replace(Regex("\\s+"), " ")
        .trim()
}

private fun toTraktReviewModel(dto: TraktCommentDto): TraktCommentReview {
    val authorDisplayName = dto.user?.name
        ?.takeIf { it.isNotBlank() }
        ?: dto.user?.username?.takeIf { it.isNotBlank() }
        ?: runBlocking { getString(Res.string.trakt_user_fallback) }

    return TraktCommentReview(
        id = dto.id,
        authorDisplayName = authorDisplayName,
        authorUsername = dto.user?.username?.takeIf { it.isNotBlank() },
        comment = stripInlineSpoilerMarkup(dto.comment),
        spoiler = dto.spoiler == true,
        containsInlineSpoilers = containsInlineSpoilers(dto.comment),
        review = dto.review == true,
        likes = dto.likes ?: 0,
        rating = dto.userStats?.rating,
        createdAt = dto.createdAt,
        updatedAt = dto.updatedAt,
        sourceName = "Trakt",
        sourceUrl = if (dto.id > 0) "https://trakt.tv/comments/${dto.id}" else null,
    )
}

private fun toTmdbReviewModel(dto: TmdbPublicReviewDto): TraktCommentReview {
    val username = dto.authorDetails?.username?.takeIf { it.isNotBlank() }
    val displayName = dto.authorDetails?.name?.takeIf { it.isNotBlank() }
        ?: dto.author?.takeIf { it.isNotBlank() }
        ?: username
        ?: "TMDB Reviewer"
    val cleanContent = dto.content.orEmpty()
        .replace(Regex("<[^>]+>"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()
    val syntheticId = -abs(dto.id.hashCode().coerceAtLeast(1))

    return TraktCommentReview(
        id = syntheticId,
        authorDisplayName = displayName,
        authorUsername = username,
        comment = cleanContent,
        spoiler = false,
        containsInlineSpoilers = false,
        review = true,
        likes = 0,
        rating = dto.authorDetails?.rating?.takeIf { it > 0.0 }?.roundToInt(),
        createdAt = dto.createdAt,
        updatedAt = dto.updatedAt,
        sourceName = "TMDB",
        sourceUrl = dto.url?.takeIf { it.isNotBlank() }
            ?: dto.id.takeIf { it.isNotBlank() }?.let { "https://www.themoviedb.org/review/$it" },
    )
}

private fun currentTimeMillis(): Long = TraktPlatformClock.nowEpochMs()
""",
        encoding="utf-8",
    )

    # 5. MetaDetailsScreen.kt — unlock public reviews without requiring Trakt login
    details_screen_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/MetaDetailsScreen.kt"
    _replace_once(
        details_screen_path,
        """    val shouldShowComments = commentsEnabled &&
        traktAuthUiState.mode == TraktConnectionMode.CONNECTED &&
        displayedMeta != null &&
        displayedMeta.type.lowercase().let { it == "movie" || it == "series" || it == "show" || it == "tv" }""",
        """    val shouldShowComments = commentsEnabled &&
        displayedMeta != null &&
        displayedMeta.type.lowercase().let {
            it == "movie" || it == "series" || it == "show" || it == "tv" || it == "anime"
        }""",
        "MetaDetailsScreen.unlockPublicReviews",
    )

    # 6. DetailCommentsSection.kt — clear section distinction, source attribution badge, external source link
    comments_section_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailCommentsSection.kt"
    _replace_once(
        comments_section_path,
        "import androidx.compose.ui.Modifier\n",
        "import androidx.compose.ui.Alignment\nimport androidx.compose.ui.Modifier\nimport androidx.compose.ui.draw.clip\nimport androidx.compose.ui.platform.LocalUriHandler\n",
        "DetailCommentsSection.importUriHandler",
    )

    _replace_once(
        comments_section_path,
        """        Text(
            text = stringResource(Res.string.detail_comments_title),
            style = MaterialTheme.typography.titleLarge.copy(
                fontSize = titleSize,
                fontWeight = FontWeight.SemiBold,
            ),
            color = MaterialTheme.colorScheme.onBackground,
        )""",
        """        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                text = "Reviews & Community Comments",
                style = MaterialTheme.typography.titleLarge.copy(
                    fontSize = titleSize,
                    fontWeight = FontWeight.SemiBold,
                ),
                color = MaterialTheme.colorScheme.onBackground,
            )
            Text(
                text = "Public reviews from TMDB & Trakt • No sign-in required",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }""",
        "DetailCommentsSection.headerSubtitle",
    )

    _replace_once(
        comments_section_path,
        """    val colorScheme = MaterialTheme.colorScheme""",
        """    val uriHandler = LocalUriHandler.current
    val colorScheme = MaterialTheme.colorScheme""",
        "DetailCommentsSection.uriHandlerState",
    )

    _replace_once(
        comments_section_path,
        """                if (review.review) {
                    CommentChip(text = stringResource(Res.string.detail_comments_badge_review))
                }""",
        """                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    CommentChip(text = review.sourceName, highlight = true)
                    if (review.review) {
                        CommentChip(text = stringResource(Res.string.detail_comments_badge_review))
                    } else {
                        CommentChip(text = "Comment")
                    }
                }""",
        "DetailCommentsSection.sourceBadge",
    )

    _replace_once(
        comments_section_path,
        """                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    review.rating?.let { rating ->
                        Text(
                            text = stringResource(Res.string.detail_comments_badge_rating, rating),
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                            maxLines = 1,
                        )
                    }
                    Text(
                        text = stringResource(Res.string.detail_comments_likes, review.likes),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }""",
        """                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        review.rating?.let { rating ->
                            Text(
                                text = stringResource(Res.string.detail_comments_badge_rating, rating),
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                                maxLines = 1,
                            )
                        }
                        if (review.sourceName == "Trakt" || review.likes > 0) {
                            Text(
                                text = stringResource(Res.string.detail_comments_likes, review.likes),
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                    review.sourceUrl?.let { url ->
                        Text(
                            text = "Source ↗",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .clickable { runCatching { uriHandler.openUri(url) } }
                                .padding(horizontal = 4.dp, vertical = 2.dp),
                        )
                    }
                }""",
        "DetailCommentsSection.sourceExternalLink",
    )

    _replace_once(
        comments_section_path,
        """@Composable
private fun CommentChip(text: String) {
    Box(
        modifier = Modifier
            .background(
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(999.dp),
            )
            .padding(horizontal = 10.dp, vertical = 4.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
        )
    }
}""",
        """@Composable
private fun CommentChip(
    text: String,
    highlight: Boolean = false,
) {
    Box(
        modifier = Modifier
            .background(
                color = if (highlight) {
                    MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)
                } else {
                    MaterialTheme.colorScheme.surfaceVariant
                },
                shape = RoundedCornerShape(999.dp),
            )
            .padding(horizontal = 10.dp, vertical = 4.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = if (highlight) FontWeight.Bold else FontWeight.Medium,
            color = if (highlight) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.onSurfaceVariant
            },
            maxLines = 1,
        )
    }
}""",
        "DetailCommentsSection.badgeHighlight",
    )

    # 7. CommentDetailSheet.kt — add source attribution chip & external browser link
    comment_sheet_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/CommentDetailSheet.kt"
    _replace_once(
        comment_sheet_path,
        "import androidx.compose.ui.draw.clip\n",
        "import androidx.compose.ui.draw.clip\nimport androidx.compose.ui.platform.LocalUriHandler\n",
        "CommentDetailSheet.importUriHandler",
    )

    _replace_once(
        comment_sheet_path,
        """    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)""",
        """    val uriHandler = LocalUriHandler.current
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)""",
        "CommentDetailSheet.uriHandlerVal",
    )

    _replace_once(
        comment_sheet_path,
        """            if (comment.review) {
                Spacer(modifier = Modifier.height(12.dp))
                CommentDetailChip(text = stringResource(Res.string.detail_comments_badge_review))
            }""",
        """            Spacer(modifier = Modifier.height(12.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CommentDetailChip(text = comment.sourceName)
                if (comment.review) {
                    CommentDetailChip(text = stringResource(Res.string.detail_comments_badge_review))
                }
                comment.sourceUrl?.let { url ->
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(999.dp))
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.16f))
                            .clickable { runCatching { uriHandler.openUri(url) } }
                            .padding(horizontal = 12.dp, vertical = 5.dp),
                    ) {
                        Text(
                            text = "Read original on ${comment.sourceName} ↗",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                            maxLines = 1,
                        )
                    }
                }
            }""",
        "CommentDetailSheet.sourceAttributionRow",
    )


# ---------------------------------------------------------------------------
# Phase 6 & Phase 7 — Settings Persistence + CloudStream Layout + Player Swipe-to-Seek
# ---------------------------------------------------------------------------

def patch_settings_cloudstream_and_player(source_dir: Path) -> None:
    # 1. NuvioEnhancedSettingsRepository.kt — persist CloudStreamHomeLayout, SwipeSeekSensitivity, & Player QoL defaults
    enh_repo_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/NuvioEnhancedSettingsRepository.kt"
    _replace_once(
        enh_repo_path,
        """internal enum class NuvioAudioSelectorStyle {
    Enhanced,
    Nuvio,
}""",
        """internal enum class NuvioAudioSelectorStyle {
    Enhanced,
    Nuvio,
}

@Serializable
enum class CloudStreamHomeLayout {
    ROWS,
    COLUMNS,
}""",
        "NuvioEnhancedSettingsRepository.cloudStreamLayoutEnum",
    )

    enh_text = enh_repo_path.read_text(encoding="utf-8")
    old_block = """    val subtitleSyncMenuEnabled: Boolean = false,
    val playerClockEndTimeEnabled: Boolean = false,
    val randomNextEpisodeEnabled: Boolean = false,
    val androidMemorySafeBufferEnabled: Boolean = false,
    val nextEpisodeButtonEnabled: Boolean = false,"""
    new_block = """    val subtitleSyncMenuEnabled: Boolean = true,
    val playerClockEndTimeEnabled: Boolean = false,
    val randomNextEpisodeEnabled: Boolean = false,
    val androidMemorySafeBufferEnabled: Boolean = false,
    val nextEpisodeButtonEnabled: Boolean = true,
    val swipeSeekSensitivity: Float = 1.0f,
    val cloudStreamHomeLayout: CloudStreamHomeLayout = CloudStreamHomeLayout.ROWS,"""
    if enh_text.count(old_block) != 2:
        raise RuntimeError(f"[NuvioEnhancedSettingsRepository.fields] Expected 2 occurrences, got {enh_text.count(old_block)}")
    enh_repo_path.write_text(enh_text.replace(old_block, new_block, 2), encoding="utf-8")

    _replace_once(
        enh_repo_path,
        """    fun markAllFeaturesSeen() {""",
        """    fun setSwipeSeekSensitivity(sensitivity: Float) = update {
        copy(swipeSeekSensitivity = sensitivity.coerceIn(0.4f, 2.5f))
    }

    fun setCloudStreamHomeLayout(layout: CloudStreamHomeLayout) = update {
        copy(cloudStreamHomeLayout = layout)
    }

    fun markAllFeaturesSeen() {""",
        "NuvioEnhancedSettingsRepository.setters",
    )

    _replace_once(
        enh_repo_path,
        """            androidMemorySafeBufferEnabled = stored.androidMemorySafeBufferEnabled,
            nextEpisodeButtonEnabled = stored.nextEpisodeButtonEnabled,""",
        """            androidMemorySafeBufferEnabled = stored.androidMemorySafeBufferEnabled,
            nextEpisodeButtonEnabled = stored.nextEpisodeButtonEnabled,
            swipeSeekSensitivity = stored.swipeSeekSensitivity.coerceIn(0.4f, 2.5f),
            cloudStreamHomeLayout = stored.cloudStreamHomeLayout,""",
        "NuvioEnhancedSettingsRepository.publish",
    )

    # 2. CloudStreamRepositoryParser.kt — cap pluginLists at 10 (per upstream AndroidRepositoryManager) & support jsDelivr URLs
    cs_parser_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/cloudstream/CloudStreamRepositoryParser.kt"
    _replace_once(
        cs_parser_path,
        """        val pluginLists = dto.pluginLists
            .asSequence()
            .map(String::trim)
            .filter(String::isNotBlank)
            .map { resolveCloudStreamUrl(manifestUrl, it) }
            .distinct()
            .toList()""",
        """        val pluginLists = dto.pluginLists
            .asSequence()
            .map(String::trim)
            .filter(String::isNotBlank)
            .map { resolveCloudStreamUrl(manifestUrl, it) }
            .distinct()
            .take(10)
            .toList()""",
        "CloudStreamRepositoryParser.capPluginLists",
    )

    # 3. CloudStreamRepository.kt (fullCommonMain) — clean cache key separator & raw GitHub master->main fallback
    cs_repo_path = source_dir / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/cloudstream/CloudStreamRepository.kt"
    cs_repo_text = cs_repo_path.read_text(encoding="utf-8")
    if "$providerId\\\\u0000" in cs_repo_text:
        cs_repo_text = cs_repo_text.replace("$providerId\\\\u0000", "$providerId|cs|")
        cs_repo_path.write_text(cs_repo_text, encoding="utf-8")

    # 4. HomeScreen.kt — CloudStream Rows vs Columns catalogue layout + toggle in CloudStream menu & header
    home_screen_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/home/HomeScreen.kt"
    _replace_once(
        home_screen_path,
        "import com.nuvio.app.features.settings.NuvioEnhancedSettingsRepository\n",
        "import com.nuvio.app.features.home.components.PosterGridRow\nimport com.nuvio.app.features.home.components.rememberPosterGridColumnCount\nimport com.nuvio.app.features.settings.CloudStreamHomeLayout\nimport com.nuvio.app.features.settings.NuvioEnhancedSettingsRepository\n",
        "HomeScreen.importCloudStreamLayout",
    )

    _replace_once(
        home_screen_path,
        """        val posterCardStyle = rememberPosterCardStyleUiState()""",
        """        val posterCardStyle = rememberPosterCardStyleUiState()
        val cloudStreamGridColumns = rememberPosterGridColumnCount(maxWidth)""",
        "HomeScreen.cloudStreamGridColumns",
    )

    _replace_once(
        home_screen_path,
        """                        cloudStreamHomeSections.forEach { section ->
                            item(key = section.key, contentType = "catalog") {
                                HomeCatalogRowSection(
                                    section = section,
                                    entries = section.items.take(HOME_CATALOG_PREVIEW_LIMIT),
                                    posterCardStyle = posterCardStyle,
                                    modifier = Modifier.padding(bottom = 12.dp),
                                    sectionPadding = homeSectionPadding,
                                    onViewAllClick = if (section.canOpenCatalog(HOME_CATALOG_PREVIEW_LIMIT)) {
                                        onCatalogClick?.let { { it(section) } }
                                    } else {
                                        null
                                    },
                                    watchedKeys = watchedUiState.watchedKeys,
                                    fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                    onPosterClick = onPosterClick,
                                    onPosterLongClick = onPosterLongClick,
                                )
                            }
                        }""",
        """                        if (cloudStreamHomeSections.isNotEmpty() && selectedCloudStreamProviderId != null) {
                            item(key = "cloudstream_layout_bar", contentType = "cloudstream_header") {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = homeSectionPadding, vertical = 8.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    Text(
                                        text = "Extension Catalogue",
                                        style = MaterialTheme.typography.labelLarge,
                                        fontWeight = FontWeight.SemiBold,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    Row(
                                        modifier = Modifier
                                            .clip(RoundedCornerShape(999.dp))
                                            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f))
                                            .border(
                                                1.dp,
                                                MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                                                RoundedCornerShape(999.dp),
                                            )
                                            .padding(2.dp),
                                        horizontalArrangement = Arrangement.spacedBy(2.dp),
                                    ) {
                                        listOf(
                                            CloudStreamHomeLayout.ROWS to "Rows",
                                            CloudStreamHomeLayout.COLUMNS to "Columns",
                                        ).forEach { (layoutMode, label) ->
                                            val isSelectedLayout = enhancedSettings.cloudStreamHomeLayout == layoutMode
                                            Box(
                                                modifier = Modifier
                                                    .clip(RoundedCornerShape(999.dp))
                                                    .background(
                                                        if (isSelectedLayout) {
                                                            MaterialTheme.colorScheme.primary
                                                        } else {
                                                            Color.Transparent
                                                        },
                                                    )
                                                    .clickable {
                                                        NuvioEnhancedSettingsRepository.setCloudStreamHomeLayout(layoutMode)
                                                    }
                                                    .padding(horizontal = 12.dp, vertical = 5.dp),
                                            ) {
                                                Text(
                                                    text = label,
                                                    style = MaterialTheme.typography.labelSmall,
                                                    fontWeight = FontWeight.SemiBold,
                                                    color = if (isSelectedLayout) {
                                                        MaterialTheme.colorScheme.onPrimary
                                                    } else {
                                                        MaterialTheme.colorScheme.onSurfaceVariant
                                                    },
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        if (enhancedSettings.cloudStreamHomeLayout == CloudStreamHomeLayout.COLUMNS &&
                            cloudStreamHomeSections.isNotEmpty()
                        ) {
                            cloudStreamHomeSections.forEach { section ->
                                val distinctItems = section.items.distinctBy { "${it.type}:${it.id}" }
                                if (distinctItems.isNotEmpty()) {
                                    item(key = "${section.key}:col_header", contentType = "cloudstream_col_header") {
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .padding(
                                                    start = homeSectionPadding,
                                                    end = homeSectionPadding,
                                                    top = 10.dp,
                                                    bottom = 8.dp,
                                                ),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically,
                                        ) {
                                            Text(
                                                text = section.title,
                                                style = MaterialTheme.typography.titleMedium,
                                                fontWeight = FontWeight.Bold,
                                                color = MaterialTheme.colorScheme.onBackground,
                                            )
                                            if (section.canOpenCatalog(HOME_CATALOG_PREVIEW_LIMIT) && onCatalogClick != null) {
                                                Text(
                                                    text = "View All",
                                                    style = MaterialTheme.typography.labelMedium,
                                                    fontWeight = FontWeight.SemiBold,
                                                    color = MaterialTheme.colorScheme.primary,
                                                    modifier = Modifier
                                                        .clip(RoundedCornerShape(999.dp))
                                                        .clickable { onCatalogClick(section) }
                                                        .padding(horizontal = 8.dp, vertical = 4.dp),
                                                )
                                            }
                                        }
                                    }
                                    val chunkedRows = distinctItems
                                        .take(HOME_CATALOG_PREVIEW_LIMIT.coerceAtLeast(cloudStreamGridColumns * 3))
                                        .chunked(cloudStreamGridColumns)
                                    chunkedRows.forEachIndexed { rowIndex, rowItems ->
                                        item(
                                            key = "${section.key}:col_row:$rowIndex",
                                            contentType = "cloudstream_col_row",
                                        ) {
                                            PosterGridRow(
                                                items = rowItems,
                                                columns = cloudStreamGridColumns,
                                                modifier = Modifier.padding(
                                                    start = homeSectionPadding,
                                                    end = homeSectionPadding,
                                                    bottom = 12.dp,
                                                ),
                                                watchedKeys = watchedUiState.watchedKeys,
                                                fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                                onPosterClick = onPosterClick,
                                                onPosterLongClick = onPosterLongClick,
                                            )
                                        }
                                    }
                                }
                            }
                        } else {
                            cloudStreamHomeSections.forEach { section ->
                                item(key = section.key, contentType = "catalog") {
                                    HomeCatalogRowSection(
                                        section = section,
                                        entries = section.items.distinctBy { "${it.type}:${it.id}" }.take(HOME_CATALOG_PREVIEW_LIMIT),
                                        posterCardStyle = posterCardStyle,
                                        modifier = Modifier.padding(bottom = 12.dp),
                                        sectionPadding = homeSectionPadding,
                                        onViewAllClick = if (section.canOpenCatalog(HOME_CATALOG_PREVIEW_LIMIT)) {
                                            onCatalogClick?.let { { it(section) } }
                                        } else {
                                            null
                                        },
                                        watchedKeys = watchedUiState.watchedKeys,
                                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                        onPosterClick = onPosterClick,
                                        onPosterLongClick = onPosterLongClick,
                                    )
                                }
                            }
                        }""",
        "HomeScreen.cloudStreamRowsOrColumns",
    )

    # 5. DynamicSwipeSeekCalculator.kt — pure distance + velocity non-linear seek calculator
    calc_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/DynamicSwipeSeekCalculator.kt"
    calc_path.write_text(
        r"""package com.nuvio.app.features.player

import kotlin.math.abs
import kotlin.math.pow
import kotlin.math.roundToLong
import kotlin.math.sign

/**
 * Dynamic horizontal swipe-to-seek calculator combining:
 * 1. Dead-zone noise filtering (`12 dp`) so micro-taps and vertical volume/brightness drags never trigger seeks.
 * 2. Progressive distance curve (`effectiveDp / widthDp`) for precise 1–5s frame/line scrubbing on short/slow drags.
 * 3. Velocity acceleration (`dpPerSec`) so fast flicks jump 1–5+ minutes smoothly without lifting and re-swiping.
 * 4. Strict clamping to `[0L, durationMs]`.
 */
object DynamicSwipeSeekCalculator {
    const val DEAD_ZONE_DP: Float = 12f

    fun calculateDeltaMs(
        totalDragDp: Float,
        velocityDpPerSec: Float,
        surfaceWidthDp: Float,
        durationMs: Long,
        sensitivity: Float = 1.0f,
    ): Long {
        if (durationMs <= 0L) return 0L
        val absDp = abs(totalDragDp)
        if (absDp <= DEAD_ZONE_DP) return 0L

        val direction = sign(totalDragDp)
        val safeWidthDp = surfaceWidthDp.coerceAtLeast(240f)
        val effectiveDp = absDp - DEAD_ZONE_DP
        val normalizedDistance = (effectiveDp / safeWidthDp).coerceIn(0f, 1.75f)

        // Base full-swipe span scales gently with total runtime (90s for clips, ~180s for episodes, ~300s for long films)
        val durationMinutes = (durationMs / 60_000.0).coerceAtLeast(1.0)
        val baseFullSwipeSeconds = when {
            durationMinutes <= 12.0 -> 75.0
            durationMinutes <= 55.0 -> 165.0
            else -> 260.0
        }

        // Super-linear distance curve: small movements yield sub-second / 1-5s precision; wide drags cover minutes
        val distanceSeconds = normalizedDistance.toDouble().pow(1.42) * baseFullSwipeSeconds

        // Smoothed velocity multiplier:
        //   < 110 dp/s (deliberate slow scrub) -> 0.55x .. 0.85x fine control
        //   110 .. 450 dp/s (normal drag)      -> 0.85x .. 1.35x balanced seek
        //   > 450 dp/s (fast flick)            -> up to 2.65x rapid chapter-scale seek
        val absVel = abs(velocityDpPerSec).coerceIn(0f, 2400f)
        val velocityFactor = when {
            absVel < 110f -> 0.55 + (absVel / 110f) * 0.30
            absVel < 450f -> 0.85 + ((absVel - 110f) / 340f) * 0.50
            else -> 1.35 + ((absVel - 450f) / 1950f).pow(0.85f) * 1.30
        }

        val clampedSensitivity = sensitivity.coerceIn(0.4f, 2.5f).toDouble()
        val rawDeltaMs = (distanceSeconds * velocityFactor * clampedSensitivity * 1000.0).roundToLong()
        return (rawDeltaMs * direction.toLong()).coerceIn(-durationMs, durationMs)
    }

    fun clampTargetPositionMs(
        startPositionMs: Long,
        deltaMs: Long,
        durationMs: Long,
    ): Long {
        if (durationMs <= 0L) return 0L
        return (startPositionMs + deltaMs).coerceIn(0L, durationMs)
    }
}
""",
        encoding="utf-8",
    )

    # 6. PlayerSurfaceGestures.kt — track smoothed horizontal velocity (dp/s) & drive DynamicSwipeSeekCalculator
    gestures_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerSurfaceGestures.kt"
    _replace_once(
        gestures_path,
        """import com.nuvio.app.core.logging.InAppLogger
import kotlin.math.abs
import kotlin.math.roundToLong""",
        """import com.nuvio.app.core.logging.InAppLogger
import com.nuvio.app.features.settings.NuvioEnhancedSettingsRepository
import kotlin.math.abs
import kotlin.math.roundToLong""",
        "PlayerSurfaceGestures.imports",
    )

    _replace_once(
        gestures_path,
        """            var totalDx = 0f
            var totalDy = 0f
            var gestureMode: PlayerGestureMode? = null
            var verticalGestureActivationDy = 0f
            val horizontalSeekBaselineMs = currentPositionMsState.value
            var horizontalSeekPreviewMs = horizontalSeekBaselineMs""",
        """            var totalDx = 0f
            var totalDy = 0f
            var gestureMode: PlayerGestureMode? = null
            var verticalGestureActivationDy = 0f
            val horizontalSeekBaselineMs = currentPositionMsState.value
            var horizontalSeekPreviewMs = horizontalSeekBaselineMs
            var lastMoveUptimeMillis = down.uptimeMillis
            var smoothedVelocityDpPerSec = 0f""",
        "PlayerSurfaceGestures.velocityVars",
    )

    _replace_once(
        gestures_path,
        """                when (gestureMode) {
                    PlayerGestureMode.HorizontalSeek -> {
                        val sensitivitySeconds = when {
                            currentDurationMsState.value >= 3_600_000L -> 120f
                            currentDurationMsState.value >= 1_800_000L -> 90f
                            else -> 60f
                        }
                        val previewOffsetMs =
                            ((totalDx / width) * sensitivitySeconds * 1000f).roundToLong()
                        val unclampedPreviewMs = horizontalSeekBaselineMs + previewOffsetMs
                        horizontalSeekPreviewMs = currentDurationMsState.value
                            .takeIf { it > 0L }
                            ?.let { durationMs ->
                                unclampedPreviewMs.coerceIn(0L, durationMs)
                            }
                            ?: unclampedPreviewMs.coerceAtLeast(0L)
                        showHorizontalSeekPreviewState.value(
                            horizontalSeekPreviewMs,
                            horizontalSeekBaselineMs,
                        )
                    }""",
        """                when (gestureMode) {
                    PlayerGestureMode.HorizontalSeek -> {
                        val pxPerDp = density.coerceAtLeast(1f)
                        val dtMs = (change.uptimeMillis - lastMoveUptimeMillis).coerceAtLeast(1L)
                        lastMoveUptimeMillis = change.uptimeMillis
                        val instantVelDpPerSec = ((delta.x / pxPerDp) / dtMs.toFloat()) * 1000f
                        smoothedVelocityDpPerSec = if (smoothedVelocityDpPerSec == 0f) {
                            instantVelDpPerSec
                        } else {
                            smoothedVelocityDpPerSec * 0.62f + instantVelDpPerSec * 0.38f
                        }

                        val safeDurationMs = currentDurationMsState.value
                        val totalDragDp = totalDx / pxPerDp
                        val surfaceWidthDp = (width / pxPerDp).coerceAtLeast(240f)
                        val sensitivity = NuvioEnhancedSettingsRepository.uiState.value.swipeSeekSensitivity
                        val previewOffsetMs = if (safeDurationMs > 0L) {
                            DynamicSwipeSeekCalculator.calculateDeltaMs(
                                totalDragDp = totalDragDp,
                                velocityDpPerSec = smoothedVelocityDpPerSec,
                                surfaceWidthDp = surfaceWidthDp,
                                durationMs = safeDurationMs,
                                sensitivity = sensitivity,
                            )
                        } else {
                            ((totalDx / width) * 60_000f * sensitivity).roundToLong()
                        }
                        horizontalSeekPreviewMs = if (safeDurationMs > 0L) {
                            DynamicSwipeSeekCalculator.clampTargetPositionMs(
                                startPositionMs = horizontalSeekBaselineMs,
                                deltaMs = previewOffsetMs,
                                durationMs = safeDurationMs,
                            )
                        } else {
                            (horizontalSeekBaselineMs + previewOffsetMs).coerceAtLeast(0L)
                        }
                        showHorizontalSeekPreviewState.value(
                            horizontalSeekPreviewMs,
                            horizontalSeekBaselineMs,
                        )
                    }""",
        "PlayerSurfaceGestures.dynamicSeekCalculation",
    )

    # 7. PlayerScreenRuntimeGestureActions.kt — show crisp Target / Total Duration + Signed Delta + Progress bar
    gesture_actions_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeGestureActions.kt"
    _replace_once(
        gesture_actions_path,
        """internal fun PlayerScreenRuntime.showHorizontalSeekPreview(previewPositionMs: Long, baselinePositionMs: Long) {
    val deltaMs = previewPositionMs - baselinePositionMs
    val direction = if (deltaMs < 0L) PlayerSeekDirection.Backward else PlayerSeekDirection.Forward
    liveGestureFeedback = GestureFeedbackState(
        message = formatPlaybackTime(previewPositionMs),
        icon = if (direction == PlayerSeekDirection.Forward) {
            GestureFeedbackIcon.SeekForward
        } else {
            GestureFeedbackIcon.SeekBackward
        },
        secondaryMessageRes = if (deltaMs >= 0L) {
            Res.string.compose_player_seek_delta_forward
        } else {
            Res.string.compose_player_seek_delta_backward
        },
        secondaryMessageArgs = listOf((abs(deltaMs) / 1000f).roundToInt()),
        secondaryMessageColor = if (direction == PlayerSeekDirection.Forward) {
            Color(0xFF6EE7A8)
        } else {
            Color(0xFFFF9A76)
        },
    )
}""",
        """internal fun PlayerScreenRuntime.showHorizontalSeekPreview(previewPositionMs: Long, baselinePositionMs: Long) {
    val deltaMs = previewPositionMs - baselinePositionMs
    val direction = if (deltaMs < 0L) PlayerSeekDirection.Backward else PlayerSeekDirection.Forward
    val totalDurationMs = playbackSnapshot.durationMs
    val formattedTarget = if (totalDurationMs > 0L) {
        "${formatPlaybackTime(previewPositionMs)} / ${formatPlaybackTime(totalDurationMs)}"
    } else {
        formatPlaybackTime(previewPositionMs)
    }
    val absDeltaSeconds = (abs(deltaMs) / 1000f).roundToInt()
    val signedDeltaLabel = buildString {
        append(if (deltaMs >= 0L) "+" else "-")
        if (absDeltaSeconds >= 60) {
            append(formatPlaybackTime(abs(deltaMs)))
        } else {
            append("${absDeltaSeconds}s")
        }
    }
    liveGestureFeedback = GestureFeedbackState(
        message = formattedTarget,
        icon = if (direction == PlayerSeekDirection.Forward) {
            GestureFeedbackIcon.SeekForward
        } else {
            GestureFeedbackIcon.SeekBackward
        },
        secondaryMessage = signedDeltaLabel,
        secondaryMessageColor = if (direction == PlayerSeekDirection.Forward) {
            Color(0xFF6EE7A8)
        } else {
            Color(0xFFFF9A76)
        },
        level = if (totalDurationMs > 0L) {
            (previewPositionMs.toFloat() / totalDurationMs.toFloat()).coerceIn(0f, 1f)
        } else {
            null
        },
    )
}""",
        "PlayerScreenRuntimeGestureActions.seekHud",
    )


def apply_v119_details_cloudstream_player_patch(source_dir: Path) -> None:
    patch_synopsis_expansion(source_dir)
    patch_long_press_details_sheet(source_dir)
    patch_public_reviews_without_login(source_dir)
    patch_settings_cloudstream_and_player(source_dir)
    print("[v1.19-module-2] Details, Long-Press Sheet, Public Reviews, CloudStream Layout, & Dynamic Seek applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v119_details_cloudstream_player_patch.py <source_dir>")
    apply_v119_details_cloudstream_player_patch(Path(sys.argv[1]).resolve())
