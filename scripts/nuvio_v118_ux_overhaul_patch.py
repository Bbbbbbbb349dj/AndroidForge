#!/usr/bin/env python3
"""Nuvio Enhanced v1.18 — Library Categories, CloudStream Filter/Sort, Fast Batch Sources & UX Overhaul.

Applies on top of v1.17:
  1. Version bump to `1.18` (`versionCode = 180`).
  2. Content & Discovery > CloudStream:
     - Status filters (`All`, `Installed`, `Enabled`, `Updates`, `Pinned`, `Available`)
     - Clickable top summary badges (`installed` / `enabled providers`) for 1-tap filtering
     - Sort options (`Smart Order`, `Enabled First`, `Installed First`, `Name A-Z`, `Name Z-A`, `Newest Version`)
     - One-tap `Update all installed (N)` batch updater & active filter reset bar
  3. Library Navigation Tabs:
     - Dedicated top navigation tabs for `Watching`, `Completed`, `Plan to watch`,
       `On hold`, `Dropped`, `Favourites`, and `Subscribed` (plus `All` overview)
     - Instant Library Search bar (by title, genre, or release year) in Saved Library
  4. Details Screen & Poster Overlay Library Category Picker + Duplicate Title Guard:
     - Tapping Library on Details opens a structured Category Picker (`Watching`,
       `Completed`, `Plan to watch`, `On hold`, `Dropped`, `Favourites`, `Subscribed`,
       plus 1-tap `Remove from Library` and connected remote trackers)
     - Details Hero Library button shows the active category badge (e.g. `Watching · ★`)
     - Long-pressing any poster on Home/Search/Catalog/Library includes quick category management
     - Duplicate Title Guard: prevents accidental duplicate titles across providers/categories
       and shows an alert popup asking whether to `Replace`, `Cancel`, or `Add`
  5. Fast Batch Download Source Loading & Offline Commuter UX:
     - Progressive live stream emission in `StreamSourceLoader` + `0ms` `StreamsRepository` seed
     - Non-blocking `loadCloudStreamRouteProgressive` (`fastCloudStreamSourcesToStreamItems`)
       instead of sequential `.m3u8` HTTP probes
     - Parallelism increased from 2 -> 5 episodes; episodes become `Ready` in ~1-2s on first stream
     - `Queue` button unlocks immediately as soon as any episode is ready (no 90s lock!)
     - `Stop Scan` control, live `Ready + Total Estimated Size` summary, `Next 3 / 5 / 10`
       unwatched episode quick-select chips, and 1-tap `Apply provider to season` sync
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.18 patch] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"[v1.18 patch] Ambiguous anchor ({count} matches) for {label} in {path}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


LIBRARY_CATEGORIES_KT = """\
package com.nuvio.app.features.library

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nuvio.app.core.ui.DialogButton
import com.nuvio.app.core.ui.DialogButtonStyle
import com.nuvio.app.core.ui.DialogButtons
import com.nuvio.app.core.ui.DialogSurface
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.nuvio
import com.nuvio.app.features.tracking.TrackingLibraryTab
import com.nuvio.app.features.tracking.TrackingLibraryTabKind
import kotlin.math.abs

const val LOCAL_LIBRARY_ALL_TAB_KEY = "all"
const val LOCAL_WATCH_STATUS_SELECTION_GROUP = "local:watch_status"
const val LOCAL_ALLOW_DUPLICATE_MARKER = "local:allow_duplicate"

enum class LocalLibraryCategory(
    val key: String,
    val label: String,
    val pickerSubtitle: String,
    val emptyTitle: String,
    val emptyMessage: String,
    val isWatchStatus: Boolean,
) {
    WATCHING(
        key = "local:watching",
        label = "Watching",
        pickerSubtitle = "Currently watching right now",
        emptyTitle = "Nothing in Watching yet",
        emptyMessage = "Open any Movie or Series and tap Library -> Watching to track what you're actively watching.",
        isWatchStatus = true,
    ),
    COMPLETED(
        key = "local:completed",
        label = "Completed",
        pickerSubtitle = "Finished watching",
        emptyTitle = "Nothing in Completed yet",
        emptyMessage = "Move finished Movies and Series to Completed from Details or by long-pressing any poster.",
        isWatchStatus = true,
    ),
    PLAN_TO_WATCH(
        key = "local:plan_to_watch",
        label = "Plan to watch",
        pickerSubtitle = "Saved on your watchlist for later",
        emptyTitle = "Your Plan to watch list is empty",
        emptyMessage = "Save upcoming or queued Movies and Series to Plan to watch so they're ready when you are.",
        isWatchStatus = true,
    ),
    ON_HOLD(
        key = "local:on_hold",
        label = "On hold",
        pickerSubtitle = "Paused for now — pick back up later",
        emptyTitle = "No titles On hold",
        emptyMessage = "Park paused Series or Movies here so Watching stays focused without losing your place.",
        isWatchStatus = true,
    ),
    DROPPED(
        key = "local:dropped",
        label = "Dropped",
        pickerSubtitle = "Stopped watching",
        emptyTitle = "No Dropped titles",
        emptyMessage = "Keep a record of titles you stopped watching so you don't accidentally start them again.",
        isWatchStatus = true,
    ),
    FAVOURITES(
        key = "local:favourites",
        label = "Favourites",
        pickerSubtitle = "All-time favourites (can combine with any status)",
        emptyTitle = "No Favourites yet",
        emptyMessage = "Tag your all-time favourite Movies and Series — Favourites can combine with any watch status.",
        isWatchStatus = false,
    ),
    SUBSCRIBED(
        key = "local:subscribed",
        label = "Subscribed",
        pickerSubtitle = "Follow airing episodes & Release Radar updates",
        emptyTitle = "No Subscribed titles yet",
        emptyMessage = "Subscribe to ongoing Series or upcoming Movies to highlight new releases in Release Radar and Calendar.",
        isWatchStatus = false,
    );

    companion object {
        val allKeys: Set<String> = entries.mapTo(linkedSetOf()) { it.key }
        val watchStatusKeys: Set<String> = entries.filter { it.isWatchStatus }.mapTo(linkedSetOf()) { it.key }
        private val byKey: Map<String, LocalLibraryCategory> = entries.associateBy { it.key }

        fun fromKey(key: String?): LocalLibraryCategory? = key?.let(byKey::get)
    }
}

enum class DuplicateLibraryResolution {
    REPLACE,
    ADD,
}

fun localLibraryCategoryTabs(): List<TrackingLibraryTab> =
    LocalLibraryCategory.entries.map { category ->
        TrackingLibraryTab(
            key = category.key,
            title = category.label,
            providerId = null,
            kind = if (category.isWatchStatus) TrackingLibraryTabKind.STATUS else TrackingLibraryTabKind.PERSONAL,
            selectionGroup = if (category.isWatchStatus) LOCAL_WATCH_STATUS_SELECTION_GROUP else null,
            description = category.pickerSubtitle,
        )
    }

fun LibraryItem.effectiveLocalCategoryKeys(): Set<String> {
    val explicit = listKeys.filterTo(linkedSetOf()) { it in LocalLibraryCategory.allKeys }
    return if (explicit.isNotEmpty()) {
        explicit
    } else {
        setOf(LocalLibraryCategory.PLAN_TO_WATCH.key)
    }
}

fun LibraryItem.localCategoriesInOrder(): List<LocalLibraryCategory> {
    val active = effectiveLocalCategoryKeys()
    return LocalLibraryCategory.entries.filter { it.key in active }
}

fun LibraryItem.localCategorySummaryLabel(): String {
    val active = localCategoriesInOrder()
    if (active.isEmpty()) return LocalLibraryCategory.PLAN_TO_WATCH.label
    val primary = active.firstOrNull { it.isWatchStatus } ?: active.first()
    val hasFav = LocalLibraryCategory.FAVOURITES in active && primary != LocalLibraryCategory.FAVOURITES
    val hasSub = LocalLibraryCategory.SUBSCRIBED in active && primary != LocalLibraryCategory.SUBSCRIBED
    return buildString {
        append(primary.label)
        if (hasFav) append(" · ★")
        if (hasSub) append(" · 🔔")
    }
}

fun LibraryItem.localCategoriesReadableList(): String =
    localCategoriesInOrder().joinToString(", ") { it.label }.ifBlank { LocalLibraryCategory.PLAN_TO_WATCH.label }

private val RELEASE_YEAR_REGEX = Regex(\"\"\"\\b(19\\d{2}|20\\d{2})\\b\"\"\")

fun normalizeLibraryTitleForDedup(rawTitle: String): String {
    if (rawTitle.isBlank()) return ""
    val sb = StringBuilder(rawTitle.length)
    var prevSpace = true
    for (ch in rawTitle.trim().lowercase()) {
        if (ch.isLetterOrDigit()) {
            sb.append(ch)
            prevSpace = false
        } else if (!prevSpace) {
            sb.append(' ')
            prevSpace = true
        }
    }
    return sb.toString().trim()
}

private fun extractPrimaryReleaseYear(releaseInfo: String?): Int? =
    releaseInfo?.let { RELEASE_YEAR_REGEX.find(it)?.groupValues?.getOrNull(1)?.toIntOrNull() }

private fun canonicalMediaBucket(type: String): String {
    return when (type.trim().lowercase()) {
        "movie", "film" -> "movie"
        "series", "tv", "show", "tvshow", "anime", "anime-series", "ova" -> "episodic"
        else -> "other"
    }
}

fun isPotentialDuplicateLibraryTitle(existing: LibraryItem, candidate: LibraryItem): Boolean {
    if (existing.id == candidate.id && existing.type.equals(candidate.type, ignoreCase = true)) {
        return true
    }
    if (existing.imdbId != null && existing.imdbId == candidate.imdbId) {
        return true
    }
    if (existing.tmdbId != null && existing.tmdbId == candidate.tmdbId &&
        canonicalMediaBucket(existing.type) == canonicalMediaBucket(candidate.type)
    ) {
        return true
    }
    val normExisting = normalizeLibraryTitleForDedup(existing.name)
    val normCandidate = normalizeLibraryTitleForDedup(candidate.name)
    if (normExisting.isBlank() || normExisting != normCandidate) return false

    val bucketA = canonicalMediaBucket(existing.type)
    val bucketB = canonicalMediaBucket(candidate.type)
    if (bucketA != "other" && bucketB != "other" && bucketA != bucketB) {
        return false
    }
    val yearA = extractPrimaryReleaseYear(existing.releaseInfo)
    val yearB = extractPrimaryReleaseYear(candidate.releaseInfo)
    if (yearA != null && yearB != null && abs(yearA - yearB) > 1) {
        return false
    }
    return true
}

@Composable
internal fun LibraryCategoryNavBar(
    selectedTabKey: String,
    categoryCounts: Map<String, Int>,
    totalUniqueCount: Int,
    onTabSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    val tabs = buildList {
        add(LOCAL_LIBRARY_ALL_TAB_KEY to ("All" to totalUniqueCount))
        LocalLibraryCategory.entries.forEach { category ->
            add(category.key to (category.label to (categoryCounts[category.key] ?: 0)))
        }
    }

    LazyRow(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        items(items = tabs, key = { it.first }) { (key, labelAndCount) ->
            val (label, count) = labelAndCount
            val isSelected = selectedTabKey == key
            val bgColor by animateColorAsState(
                targetValue = if (isSelected) {
                    tokens.colors.accent.copy(alpha = 0.20f)
                } else {
                    tokens.colors.surfaceCard.copy(alpha = 0.85f)
                },
                animationSpec = tween(durationMillis = 150),
                label = "libCatBg",
            )
            val borderColor by animateColorAsState(
                targetValue = if (isSelected) tokens.colors.accent else tokens.colors.borderSubtle,
                animationSpec = tween(durationMillis = 150),
                label = "libCatBorder",
            )
            Surface(
                shape = RoundedCornerShape(NuvioTokens.Radius.full),
                color = bgColor,
                border = BorderStroke(1.dp, borderColor),
                modifier = Modifier
                    .clip(RoundedCornerShape(NuvioTokens.Radius.full))
                    .clickable { onTabSelected(key) },
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (isSelected) tokens.colors.accent else tokens.colors.textPrimary,
                        maxLines = 1,
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Box(
                        modifier = Modifier
                            .background(
                                color = if (isSelected) {
                                    tokens.colors.accent.copy(alpha = 0.25f)
                                } else {
                                    tokens.colors.surfaceElevated
                                },
                                shape = RoundedCornerShape(999.dp),
                            )
                            .padding(horizontal = 6.dp, vertical = 1.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = count.toString(),
                            style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp),
                            fontWeight = FontWeight.SemiBold,
                            color = if (isSelected) tokens.colors.accent else tokens.colors.textMuted,
                            maxLines = 1,
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun LibraryDuplicateAlertDialog(
    visible: Boolean,
    candidateTitle: String,
    existingItems: List<LibraryItem>,
    targetCategoriesLabel: String,
    onReplace: () -> Unit,
    onAdd: () -> Unit,
    onCancel: () -> Unit,
) {
    if (!visible || existingItems.isEmpty()) return
    val tokens = MaterialTheme.nuvio
    val existingSummary = existingItems.joinToString(" • ") { existing ->
        val yearPart = existing.releaseInfo?.takeIf { it.isNotBlank() }?.let { " ($it)" }.orEmpty()
        "${existing.name}$yearPart in ${existing.localCategoriesReadableList()}"
    }

    DialogSurface(
        onDismissRequest = onCancel,
        title = "Duplicate Title in Library",
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "“$candidateTitle” is already in your Library.",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = tokens.colors.textPrimary,
            )
            Surface(
                shape = RoundedCornerShape(NuvioTokens.Radius.md),
                color = tokens.colors.surfaceCard,
                border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        text = "Existing: $existingSummary",
                        style = MaterialTheme.typography.bodySmall,
                        color = tokens.colors.textSecondary,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (targetCategoriesLabel.isNotBlank()) {
                        Text(
                            text = "Selected: $targetCategoriesLabel",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Medium,
                            color = tokens.colors.accent,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
            Text(
                text = "Choose Replace to update and keep a single entry, Add to keep existing and add this selection too, or Cancel.",
                style = MaterialTheme.typography.bodySmall,
                color = tokens.colors.textMuted,
            )
        }

        DialogButtons {
            DialogButton(
                text = "Cancel",
                onClick = onCancel,
                style = DialogButtonStyle.Secondary,
            )
            DialogButton(
                text = "Add",
                onClick = onAdd,
                style = DialogButtonStyle.Secondary,
            )
            DialogButton(
                text = "Replace",
                onClick = onReplace,
                style = DialogButtonStyle.Primary,
            )
        }
    }
}
"""


TRACKING_LIST_PICKER_DIALOG_KT = """\
package com.nuvio.app.core.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.DeleteOutline
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nuvio.app.features.library.DuplicateLibraryResolution
import com.nuvio.app.features.library.LibraryDuplicateAlertDialog
import com.nuvio.app.features.library.LibraryItem
import com.nuvio.app.features.library.LibraryRepository
import com.nuvio.app.features.library.LocalLibraryCategory
import com.nuvio.app.features.library.localCategoriesReadableList
import com.nuvio.app.features.tracking.TrackingLibraryTab
import com.nuvio.app.features.tracking.membershipTitle
import com.nuvio.app.features.tracking.trackingMembershipDestinations
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.action_cancel
import nuvio.composeapp.generated.resources.action_save
import nuvio.composeapp.generated.resources.compose_tracking_list_picker_loading
import nuvio.composeapp.generated.resources.hero_remove_from_library
import org.jetbrains.compose.resources.stringResource

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrackingListPickerDialog(
    visible: Boolean,
    title: String,
    tabs: List<TrackingLibraryTab>,
    membership: Map<String, Boolean>,
    isPending: Boolean,
    errorMessage: String?,
    onToggle: (String) -> Unit,
    onSave: () -> Unit,
    onDismiss: () -> Unit,
    targetItem: LibraryItem? = null,
    onSaveWithResolution: ((DuplicateLibraryResolution?) -> Unit)? = null,
    onRemoveFromLibrary: (() -> Unit)? = null,
) {
    if (!visible) return
    val tokens = MaterialTheme.nuvio
    val destinations = trackingMembershipDestinations(tabs)
    val localWatchStatusTabs = remember(destinations) {
        destinations.filter { it.providerId == null && LocalLibraryCategory.fromKey(it.key)?.isWatchStatus == true }
    }
    val localCollectionTabs = remember(destinations) {
        destinations.filter { it.providerId == null && LocalLibraryCategory.fromKey(it.key)?.isWatchStatus == false }
    }
    val otherTabs = remember(destinations) {
        destinations.filter { it.providerId != null || LocalLibraryCategory.fromKey(it.key) == null }
    }

    val existingDuplicates = remember(targetItem, visible) {
        targetItem?.let(LibraryRepository::findDuplicateCandidates).orEmpty()
    }
    val existingExact = remember(targetItem, existingDuplicates) {
        targetItem?.let { candidate ->
            existingDuplicates.firstOrNull {
                it.id == candidate.id && it.type.equals(candidate.type, ignoreCase = true)
            }
        }
    }
    var showDuplicateConfirm by remember(visible, targetItem) { mutableStateOf(false) }

    val selectedLocalLabels = remember(membership) {
        LocalLibraryCategory.entries
            .filter { membership[it.key] == true }
            .joinToString(", ") { it.label }
    }

    DialogSurface(
        onDismissRequest = onDismiss,
        title = title,
    ) {
        Text(
            text = "Choose which Library category to save this title under",
            style = MaterialTheme.typography.bodyMedium,
            color = tokens.colors.textMuted,
        )

        if (existingDuplicates.isNotEmpty()) {
            val statusBannerText = existingExact?.let {
                "Currently in Library: ${it.localCategoriesReadableList()}"
            } ?: "Matching title in Library: ${existingDuplicates.first().localCategoriesReadableList()}"
            Surface(
                shape = RoundedCornerShape(NuvioTokens.Radius.md),
                color = tokens.colors.accent.copy(alpha = 0.12f),
                border = BorderStroke(1.dp, tokens.colors.accent.copy(alpha = 0.45f)),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        text = statusBannerText,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.accent,
                        modifier = Modifier.weight(1f),
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (existingExact != null && onRemoveFromLibrary != null) {
                        Spacer(modifier = Modifier.width(8.dp))
                        OutlinedButton(
                            enabled = !isPending,
                            onClick = onRemoveFromLibrary,
                            border = BorderStroke(1.dp, tokens.colors.danger.copy(alpha = 0.6f)),
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.DeleteOutline,
                                contentDescription = null,
                                tint = tokens.colors.danger,
                                modifier = Modifier.size(16.dp),
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "Remove",
                                style = MaterialTheme.typography.labelSmall,
                                color = tokens.colors.danger,
                            )
                        }
                    }
                }
            }
        }

        if (!errorMessage.isNullOrBlank()) {
            Text(
                text = errorMessage,
                style = MaterialTheme.typography.bodySmall,
                color = tokens.colors.danger,
            )
        }

        if (isPending && destinations.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(240.dp),
                contentAlignment = Alignment.Center,
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(tokens.spacing.listGap),
                ) {
                    NuvioLoadingIndicator(
                        modifier = Modifier.size(tokens.icons.lg),
                    )
                    Text(
                        text = stringResource(Res.string.compose_tracking_list_picker_loading),
                        style = MaterialTheme.typography.bodyMedium,
                        color = tokens.colors.textMuted,
                    )
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 340.dp),
                verticalArrangement = Arrangement.spacedBy(tokens.spacing.controlGap),
            ) {
                if (localWatchStatusTabs.isNotEmpty()) {
                    item(key = "header_watch_status") {
                        Text(
                            text = "WATCH STATUS",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(top = 2.dp, bottom = 2.dp),
                        )
                    }
                    items(items = localWatchStatusTabs, key = { it.key }) { tab ->
                        DialogOption(
                            text = tab.title,
                            description = tab.description,
                            selected = membership[tab.key] == true,
                            enabled = !isPending,
                            role = Role.RadioButton,
                            onClick = { onToggle(tab.key) },
                        )
                    }
                }
                if (localCollectionTabs.isNotEmpty()) {
                    item(key = "header_collections") {
                        Text(
                            text = "COLLECTIONS & ALERTS",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(top = 8.dp, bottom = 2.dp),
                        )
                    }
                    items(items = localCollectionTabs, key = { it.key }) { tab ->
                        DialogOption(
                            text = tab.title,
                            description = tab.description,
                            selected = membership[tab.key] == true,
                            enabled = !isPending,
                            role = Role.Checkbox,
                            onClick = { onToggle(tab.key) },
                        )
                    }
                }
                if (otherTabs.isNotEmpty()) {
                    item(key = "header_remote_lists") {
                        Text(
                            text = "CONNECTED TRACKERS",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = tokens.colors.textMuted,
                            modifier = Modifier.padding(top = 8.dp, bottom = 2.dp),
                        )
                    }
                    items(items = otherTabs, key = { it.key }) { tab ->
                        DialogOption(
                            text = tab.membershipTitle(),
                            description = tab.description,
                            selected = membership[tab.key] == true,
                            enabled = !isPending,
                            role = if (tab.selectionGroup != null) Role.RadioButton else Role.Checkbox,
                            onClick = { onToggle(tab.key) },
                        )
                    }
                }
            }
        }

        DialogButtons {
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismiss,
                enabled = !isPending,
            )
            DialogButton(
                text = if (existingExact != null && membership.none { it.value }) {
                    stringResource(Res.string.hero_remove_from_library)
                } else {
                    stringResource(Res.string.action_save)
                },
                onClick = {
                    val hasAnyLocalSelected = LocalLibraryCategory.allKeys.any { membership[it] == true }
                    if (onSaveWithResolution != null && hasAnyLocalSelected && existingDuplicates.isNotEmpty()) {
                        showDuplicateConfirm = true
                    } else if (onSaveWithResolution != null) {
                        onSaveWithResolution(null)
                    } else {
                        onSave()
                    }
                },
                style = DialogButtonStyle.Primary,
                loading = isPending,
            )
        }
    }

    LibraryDuplicateAlertDialog(
        visible = showDuplicateConfirm,
        candidateTitle = title,
        existingItems = existingDuplicates,
        targetCategoriesLabel = selectedLocalLabels,
        onReplace = {
            showDuplicateConfirm = false
            onSaveWithResolution?.invoke(DuplicateLibraryResolution.REPLACE)
        },
        onAdd = {
            showDuplicateConfirm = false
            onSaveWithResolution?.invoke(DuplicateLibraryResolution.ADD)
        },
        onCancel = {
            showDuplicateConfirm = false
        },
    )
}
"""


def _patch_version_118(root: Path, changed: list[str]) -> None:
    gradle_props = root / "gradle.properties"
    if gradle_props.is_file():
        _replace_once(
            gradle_props,
            "nuvio.app.versionName=1.17\n",
            "nuvio.app.versionName=1.18\n",
            "gradle.properties versionName 1.18",
        )
        changed.append("gradle.properties")

    xcconfig = root / "iosApp/Configuration/Version.xcconfig"
    if xcconfig.is_file():
        _replace_once(
            xcconfig,
            "CURRENT_PROJECT_VERSION=170\n",
            "CURRENT_PROJECT_VERSION=180\n",
            "Version.xcconfig CURRENT_PROJECT_VERSION=180",
        )
        _replace_once(
            xcconfig,
            "MARKETING_VERSION=1.17\n",
            "MARKETING_VERSION=1.18\n",
            "Version.xcconfig MARKETING_VERSION=1.18",
        )
        changed.append("iosApp/Configuration/Version.xcconfig")

    local_media_plat = (
        root
        / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.android.kt"
    )
    if local_media_plat.is_file():
        _replace_once(
            local_media_plat,
            '.header("User-Agent", "NuvioEnhanced/1.17")',
            '.header("User-Agent", "NuvioEnhanced/1.18")',
            "LocalFolderVideosPlatform User-Agent 1.18",
        )
        changed.append(str(local_media_plat.relative_to(root)))


def _patch_library_categories_and_dedup(root: Path, changed: list[str]) -> None:
    cat_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryCategories.kt"
    )
    cat_path.write_text(LIBRARY_CATEGORIES_KT, encoding="utf-8")
    changed.append(str(cat_path.relative_to(root)))

    picker_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/TrackingListPickerDialog.kt"
    )
    picker_path.write_text(TRACKING_LIST_PICKER_DIALOG_KT, encoding="utf-8")
    changed.append(str(picker_path.relative_to(root)))

    # Patch LibraryLocalState.kt to expose exact (id, type) lookup
    local_state_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryLocalState.kt"
    )
    _replace_once(
        local_state_path,
        """    fun findById(id: String): LibraryItem? = synchronized(lock) {
        itemsById.values.firstOrNull { it.id == id }
    }""",
        """    fun find(id: String, type: String): LibraryItem? = synchronized(lock) {
        itemsById[libraryItemKey(id, type)]
    }

    fun findById(id: String): LibraryItem? = synchronized(lock) {
        itemsById.values.firstOrNull { it.id == id }
    }""",
        "LibraryLocalState.find(id, type)",
    )
    changed.append(str(local_state_path.relative_to(root)))

    # Patch LibrarySectionTitles.kt to recognize local category keys cleanly
    titles_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibrarySectionTitles.kt"
    )
    _replace_once(
        titles_path,
        """private val librarySectionTitleResources: Map<String, StringResource> = mapOf(
    "simkl:status:watching" to Res.string.library_status_watching,
    "simkl:status:plantowatch" to Res.string.library_status_plan_to_watch,
    "simkl:status:hold" to Res.string.library_status_on_hold,
    "simkl:status:completed" to Res.string.library_status_completed,
    "simkl:status:dropped" to Res.string.library_status_dropped,
)""",
        """private val librarySectionTitleResources: Map<String, StringResource> = mapOf(
    "simkl:status:watching" to Res.string.library_status_watching,
    "simkl:status:plantowatch" to Res.string.library_status_plan_to_watch,
    "simkl:status:hold" to Res.string.library_status_on_hold,
    "simkl:status:completed" to Res.string.library_status_completed,
    "simkl:status:dropped" to Res.string.library_status_dropped,
    "local:watching" to Res.string.library_status_watching,
    "local:plan_to_watch" to Res.string.library_status_plan_to_watch,
    "local:on_hold" to Res.string.library_status_on_hold,
    "local:completed" to Res.string.library_status_completed,
    "local:dropped" to Res.string.library_status_dropped,
)""",
        "LibrarySectionTitles local status mapping",
    )
    changed.append(str(titles_path.relative_to(root)))

    # Patch LibraryRepository.kt for 7 local categories, duplicate detection,Replace/Add resolution, and section publishing
    repo_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryRepository.kt"
    )
    _replace_once(
        repo_path,
        """    private fun toggleLocalSavedInternal(item: LibraryItem): TrackingMembershipApplyResult {
        val result = localState.toggle(
            item.copy(savedAtEpochMs = LibraryClock.nowEpochMs()),
        )""",
        """    private fun toggleLocalSavedInternal(item: LibraryItem): TrackingMembershipApplyResult {
        val defaultKeys = item.listKeys.takeIf { it.any(LocalLibraryCategory.allKeys::contains) }
            ?: setOf(LocalLibraryCategory.PLAN_TO_WATCH.key)
        val result = localState.toggle(
            item.copy(
                listKeys = defaultKeys,
                savedAtEpochMs = LibraryClock.nowEpochMs(),
            ),
        )""",
        "LibraryRepository.toggleLocalSavedInternal default category",
    )

    _replace_once(
        repo_path,
        """    fun savedItem(id: String): LibraryItem? {
        ensureLoaded()

        activeLibraryProvider()?.let { provider -> return provider.find(id) }

        return localState.findById(id)
    }

    fun libraryListTabs(item: LibraryItem? = null): List<TrackingLibraryTab> =
        libraryTabsWithLocal(
            TrackingProviderRegistry.connectedLibraryProviders()
                .flatMap { provider -> provider.snapshot().tabs },
        ).filter { tab ->
            item == null || (tab.supportsContentType(item.type) && (!item.isServerItem || tab.key == LOCAL_LIBRARY_LIST_KEY))
        }""",
        """    fun savedItem(id: String, type: String? = null): LibraryItem? {
        ensureLoaded()

        activeLibraryProvider()?.let { provider -> return provider.find(id) }

        return if (type != null) {
            localState.find(id, type) ?: localState.findById(id)
        } else {
            localState.findById(id)
        }
    }

    fun findDuplicateCandidates(candidate: LibraryItem): List<LibraryItem> {
        ensureLoaded()
        return localState.snapshot().items.filter { existing ->
            isPotentialDuplicateLibraryTitle(existing, candidate)
        }
    }

    fun libraryListTabs(item: LibraryItem? = null): List<TrackingLibraryTab> =
        (localLibraryCategoryTabs() +
            TrackingProviderRegistry.connectedLibraryProviders()
                .flatMap { provider -> provider.snapshot().tabs }
            ).filter { tab ->
            item == null || (
                tab.supportsContentType(item.type) &&
                    (!item.isServerItem || tab.providerId == null)
                )
        }""",
        "LibraryRepository.libraryListTabs & findDuplicateCandidates",
    )

    _replace_once(
        repo_path,
        """    suspend fun getMembershipSnapshot(item: LibraryItem): Map<String, Boolean> {
        ensureLoaded()
        val inLocal = localState.contains(item.id, item.type)
        val memberships = linkedMapOf<String, Boolean>()
        if (!item.isServerItem) {
            TrackingProviderRegistry.connectedLibraryProviders().forEach { provider ->
                memberships += provider.membership(item)
            }
        }
        return libraryMembershipWithLocal(inLocal = inLocal, providerMembership = memberships)
    }

    suspend fun applyMembershipChanges(
        item: LibraryItem,
        desiredMembership: Map<String, Boolean>,
        confirmedRemovalProviders: Set<TrackingProviderId> = emptySet(),
    ): TrackingMembershipApplyResult = withAddonLibraryEvent(item.id, item.type) {
        applyMembershipChanges(
            item = item,
            desiredMembership = desiredMembership,
            confirmedRemovalProviders = confirmedRemovalProviders,
            targetProviderIds = null,
            updateLocal = true,
        )
    }""",
        """    suspend fun getMembershipSnapshot(item: LibraryItem): Map<String, Boolean> {
        ensureLoaded()
        val existingLocal = localState.find(item.id, item.type)
        val activeLocalKeys = existingLocal?.effectiveLocalCategoryKeys().orEmpty()
        val memberships = linkedMapOf<String, Boolean>()
        LocalLibraryCategory.entries.forEach { category ->
            memberships[category.key] = category.key in activeLocalKeys
        }
        memberships[LOCAL_LIBRARY_LIST_KEY] = existingLocal != null
        if (!item.isServerItem) {
            TrackingProviderRegistry.connectedLibraryProviders().forEach { provider ->
                memberships += provider.membership(item)
            }
        }
        return memberships
    }

    suspend fun applyMembershipChanges(
        item: LibraryItem,
        desiredMembership: Map<String, Boolean>,
        confirmedRemovalProviders: Set<TrackingProviderId> = emptySet(),
        duplicateResolution: DuplicateLibraryResolution? = null,
    ): TrackingMembershipApplyResult = withAddonLibraryEvent(item.id, item.type) {
        applyMembershipChanges(
            item = item,
            desiredMembership = desiredMembership,
            confirmedRemovalProviders = confirmedRemovalProviders,
            targetProviderIds = null,
            updateLocal = true,
            duplicateResolution = duplicateResolution,
        )
    }""",
        "LibraryRepository.getMembershipSnapshot & applyMembershipChanges overload",
    )

    _replace_once(
        repo_path,
        """    private suspend fun applyMembershipChanges(
        item: LibraryItem,
        desiredMembership: Map<String, Boolean>,
        confirmedRemovalProviders: Set<TrackingProviderId>,
        targetProviderIds: Set<TrackingProviderId>?,
        updateLocal: Boolean,
    ): TrackingMembershipApplyResult {
        ensureLoaded()
        val localDesired = desiredMembership[LOCAL_LIBRARY_LIST_KEY] == true
        val currentlyInLocal = localState.contains(item.id, item.type)""",
        """    private suspend fun applyMembershipChanges(
        item: LibraryItem,
        desiredMembership: Map<String, Boolean>,
        confirmedRemovalProviders: Set<TrackingProviderId>,
        targetProviderIds: Set<TrackingProviderId>?,
        updateLocal: Boolean,
        duplicateResolution: DuplicateLibraryResolution? = null,
    ): TrackingMembershipApplyResult {
        ensureLoaded()
        val requestedCategoryKeys = LocalLibraryCategory.entries
            .filter { desiredMembership[it.key] == true }
            .mapTo(linkedSetOf()) { it.key }
        val legacyLocalDesired = desiredMembership[LOCAL_LIBRARY_LIST_KEY] == true &&
            desiredMembership.keys.none(LocalLibraryCategory.allKeys::contains)
        val effectiveLocalKeys = when {
            requestedCategoryKeys.isNotEmpty() -> requestedCategoryKeys
            legacyLocalDesired -> setOf(LocalLibraryCategory.PLAN_TO_WATCH.key)
            else -> emptySet()
        }
        val localDesired = effectiveLocalKeys.isNotEmpty()
        val currentlyInLocal = localState.contains(item.id, item.type)""",
        "LibraryRepository.applyMembershipChanges local keys resolution",
    )

    _replace_once(
        repo_path,
        """        if (updateLocal && localDesired != currentlyInLocal) {
            if (localDesired) {
                save(item)
            } else {
                remove(item.id, item.type)
            }
        }""",
        """        if (updateLocal) {
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
        "LibraryRepository.applyMembershipChanges duplicate resolution & save",
    )

    _replace_once(
        repo_path,
        """    private suspend fun removeFromListInternal(
        item: LibraryItem,
        listKey: String,
        confirmedRemovalProviders: Set<TrackingProviderId>,
    ): TrackingMembershipApplyResult {
        ensureLoaded()
        val targetProvider = TrackingProviderRegistry.connectedLibraryProviders()
            .firstOrNull { provider -> provider.snapshot().tabs.any { tab -> tab.key == listKey } }
        val currentMembership = if (listKey == LOCAL_LIBRARY_LIST_KEY) {
            mapOf(LOCAL_LIBRARY_LIST_KEY to localState.contains(item.id, item.type))
        } else {
            targetProvider?.membership(item).orEmpty()
        }
        val desiredMembership = libraryMembershipWithRemovedList(
            currentMembership = currentMembership,
            listKey = listKey,
        )
        return applyMembershipChanges(
            item = item,
            desiredMembership = desiredMembership,
            confirmedRemovalProviders = confirmedRemovalProviders,
            targetProviderIds = targetProvider?.let { provider -> setOf(provider.providerId) }.orEmpty(),
            updateLocal = listKey == LOCAL_LIBRARY_LIST_KEY,
        )
    }""",
        """    private suspend fun removeFromListInternal(
        item: LibraryItem,
        listKey: String,
        confirmedRemovalProviders: Set<TrackingProviderId>,
    ): TrackingMembershipApplyResult {
        ensureLoaded()
        val isLocalKey = listKey == LOCAL_LIBRARY_LIST_KEY || listKey in LocalLibraryCategory.allKeys
        val targetProvider = TrackingProviderRegistry.connectedLibraryProviders()
            .firstOrNull { provider -> provider.snapshot().tabs.any { tab -> tab.key == listKey } }
        val currentMembership = if (isLocalKey) {
            if (listKey == LOCAL_LIBRARY_LIST_KEY) {
                LocalLibraryCategory.allKeys.associateWith { false }
            } else {
                val activeKeys = localState.find(item.id, item.type)?.effectiveLocalCategoryKeys().orEmpty()
                LocalLibraryCategory.allKeys.associateWith { it in activeKeys }
            }
        } else {
            targetProvider?.membership(item).orEmpty()
        }
        val desiredMembership = libraryMembershipWithRemovedList(
            currentMembership = currentMembership,
            listKey = listKey,
        )
        return applyMembershipChanges(
            item = item,
            desiredMembership = desiredMembership,
            confirmedRemovalProviders = confirmedRemovalProviders,
            targetProviderIds = targetProvider?.let { provider -> setOf(provider.providerId) }.orEmpty(),
            updateLocal = isLocalKey,
        )
    }""",
        "LibraryRepository.removeFromListInternal local category support",
    )

    _replace_once(
        repo_path,
        """        val items = localSnapshot.items
            .sortedByDescending { it.savedAtEpochMs }
        val sections = items
            .groupBy { it.type }
            .map { (type, typeItems) ->
                LibrarySection(
                    type = type,
                    displayTitle = type.toLibraryDisplayTitle(),
                    items = typeItems.sortedByDescending { it.savedAtEpochMs },
                )
            }
            .sortedBy { it.displayTitle }""",
        """        val sortedRawItems = localSnapshot.items
            .sortedByDescending { it.savedAtEpochMs }
        val seenTitleBuckets = HashSet<String>()
        val items = buildList {
            for (entry in sortedRawItems) {
                if (LOCAL_ALLOW_DUPLICATE_MARKER in entry.listKeys) {
                    add(entry)
                    continue
                }
                val normTitle = normalizeLibraryTitleForDedup(entry.name)
                val dedupBucket = if (normTitle.isNotBlank()) {
                    "${entry.type.trim().lowercase().let { if (it == "movie" || it == "film") "movie" else "ep" }}::$normTitle"
                } else {
                    "id::${entry.type.lowercase()}::${entry.id}"
                }
                if (seenTitleBuckets.add(dedupBucket)) {
                    add(entry)
                }
            }
        }
        val sections = LocalLibraryCategory.entries.mapNotNull { category ->
            val categoryItems = items.filter { category.key in it.effectiveLocalCategoryKeys() }
            if (categoryItems.isEmpty()) {
                null
            } else {
                LibrarySection(
                    type = category.key,
                    displayTitle = category.label,
                    items = categoryItems,
                )
            }
        }""",
        "LibraryRepository.publish local category sections & dedup",
    )
    changed.append(str(repo_path.relative_to(root)))


def _patch_library_screen_tabs_and_search(root: Path, changed: list[str]) -> None:
    display_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryDisplaySettings.kt"
    )
    _replace_once(
        display_path,
        """internal fun buildLibraryVerticalProjection(
    sections: List<LibrarySection>,
    sourceMode: LibrarySourceMode,
    selectedSectionKey: String?,
    selectedType: String?,
    sortOption: LibrarySortOption,
    providerOrders: Map<String, Map<String, Int>> = emptyMap(),
    selectedGenre: String? = null,
    selectedYear: String? = null,
    watchedFilter: LibraryWatchedFilter = LibraryWatchedFilter.ALL,
    isWatched: (LibraryItem) -> Boolean = { false },
): LibraryVerticalProjection {
    val availableSections = if (sourceMode.isRemoteTrackingSource) sections else emptyList()
    val selectedSection = if (sourceMode.isRemoteTrackingSource) {
        sections.firstOrNull { it.type == selectedSectionKey } ?: sections.firstOrNull()
    } else {
        null
    }
    val baseEntries = if (selectedSection != null) {
        selectedSection.items.map { item -> LibraryVerticalEntry(item, selectedSection) }
    } else {
        sections.flatMap { section ->
            section.items.map { item -> LibraryVerticalEntry(item, section) }
        }
    }""",
        """internal fun buildLibraryVerticalProjection(
    sections: List<LibrarySection>,
    sourceMode: LibrarySourceMode,
    selectedSectionKey: String?,
    selectedType: String?,
    sortOption: LibrarySortOption,
    providerOrders: Map<String, Map<String, Int>> = emptyMap(),
    selectedGenre: String? = null,
    selectedYear: String? = null,
    watchedFilter: LibraryWatchedFilter = LibraryWatchedFilter.ALL,
    searchQuery: String = "",
    isWatched: (LibraryItem) -> Boolean = { false },
): LibraryVerticalProjection {
    val isFilteredLocalTab = !sourceMode.isRemoteTrackingSource &&
        !selectedSectionKey.isNullOrBlank() &&
        selectedSectionKey != LOCAL_LIBRARY_ALL_TAB_KEY
    val availableSections = if (sourceMode.isRemoteTrackingSource) sections else emptyList()
    val selectedSection = when {
        sourceMode.isRemoteTrackingSource -> {
            sections.firstOrNull { it.type == selectedSectionKey } ?: sections.firstOrNull()
        }
        isFilteredLocalTab -> {
            val category = LocalLibraryCategory.fromKey(selectedSectionKey)
            sections.firstOrNull { it.type == selectedSectionKey }
                ?: LibrarySection(
                    type = selectedSectionKey.orEmpty(),
                    displayTitle = category?.label ?: selectedSectionKey.orEmpty(),
                    items = emptyList(),
                )
        }
        else -> null
    }
    val trimmedQuery = searchQuery.trim()
    val rawEntries = if (selectedSection != null) {
        selectedSection.items.map { item -> LibraryVerticalEntry(item, selectedSection) }
    } else {
        sections.flatMap { section ->
            section.items.map { item -> LibraryVerticalEntry(item, section) }
        }
    }
    val baseEntries = if (trimmedQuery.isEmpty()) {
        rawEntries
    } else {
        rawEntries.filter { entry ->
            entry.item.name.contains(trimmedQuery, ignoreCase = true) ||
                entry.item.genres.any { it.contains(trimmedQuery, ignoreCase = true) } ||
                entry.item.releaseInfo?.contains(trimmedQuery, ignoreCase = true) == true
        }
    }""",
        "buildLibraryVerticalProjection local category tab & searchQuery",
    )
    changed.append(str(display_path.relative_to(root)))

    screen_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/library/LibraryScreen.kt"
    )
    _replace_once(
        screen_path,
        """    var selectedLibrarySectionKey by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedLibraryType by rememberSaveable { mutableStateOf<String?>(null) }
    var libraryGenre by rememberSaveable { mutableStateOf<String?>(null) }
    var libraryYear by rememberSaveable { mutableStateOf<String?>(null) }""",
        """    var selectedLibrarySectionKey by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedLocalCategoryKey by rememberSaveable { mutableStateOf(LOCAL_LIBRARY_ALL_TAB_KEY) }
    var savedSearchVisible by rememberSaveable { mutableStateOf(false) }
    var savedSearchQuery by rememberSaveable { mutableStateOf("") }
    var selectedLibraryType by rememberSaveable { mutableStateOf<String?>(null) }
    var libraryGenre by rememberSaveable { mutableStateOf<String?>(null) }
    var libraryYear by rememberSaveable { mutableStateOf<String?>(null) }
    val localCategoryCounts = remember(uiState.items) {
        val counts = linkedMapOf<String, Int>()
        LocalLibraryCategory.entries.forEach { category ->
            counts[category.key] = uiState.items.count { category.key in it.effectiveLocalCategoryKeys() }
        }
        counts
    }""",
        "LibraryScreen local category tab & search states",
    )

    _replace_once(
        screen_path,
        """    val sortedSections = remember(uiState.sections, displaySettings, uiState.sourceMode, sourceMode, providerOrders) {
        if (sourceMode == LibraryViewMode.Saved && displaySettings.layoutMode == LibraryLayoutMode.HORIZONTAL) {
            sortLibrarySections(
                sections = uiState.sections,
                selected = visibleSortOption,
                sourceMode = uiState.sourceMode,
                providerOrders = providerOrders.ranks,
            )
        } else {
            emptyList()
        }
    }
    val verticalProjection = remember(
        uiState.sections,
        uiState.sourceMode,
        selectedLibrarySectionKey,
        selectedLibraryType,
        libraryGenre,
        libraryYear,
        libraryWatchedFilter,
        watchedUiState.watchedKeys,
        fullyWatchedSeriesKeys,
        displaySettings,
        sourceMode,
        providerOrders,
    ) {
        if (sourceMode == LibraryViewMode.Saved && displaySettings.layoutMode == LibraryLayoutMode.VERTICAL) {
            buildLibraryVerticalProjection(
                sections = uiState.sections,
                sourceMode = uiState.sourceMode,
                selectedSectionKey = selectedLibrarySectionKey,
                selectedType = selectedLibraryType,
                sortOption = visibleSortOption,
                providerOrders = providerOrders.ranks,
                selectedGenre = libraryGenre,
                selectedYear = libraryYear,
                watchedFilter = libraryWatchedFilter,
                isWatched = { item ->
                    WatchingState.isPosterWatched(
                        watchedKeys = watchedUiState.watchedKeys,
                        item = item.toMetaPreview(),
                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                    )
                },
            )
        } else {
            LibraryVerticalProjection(
                availableSections = emptyList(),
                selectedSectionKey = null,
                availableTypes = emptyList(),
                selectedType = null,
                entries = emptyList(),
            )
        }
    }""",
        """    val isFocusedLocalCategoryTab = uiState.sourceMode == LibrarySourceMode.LOCAL &&
        selectedLocalCategoryKey != LOCAL_LIBRARY_ALL_TAB_KEY
    val effectiveLayoutForSaved = if (isFocusedLocalCategoryTab) {
        LibraryLayoutMode.VERTICAL
    } else {
        displaySettings.layoutMode
    }
    val filteredSectionsBySearch = remember(uiState.sections, savedSearchQuery) {
        val trimmed = savedSearchQuery.trim()
        if (trimmed.isEmpty()) {
            uiState.sections
        } else {
            uiState.sections.mapNotNull { section ->
                val matching = section.items.filter { item ->
                    item.name.contains(trimmed, ignoreCase = true) ||
                        item.genres.any { it.contains(trimmed, ignoreCase = true) } ||
                        item.releaseInfo?.contains(trimmed, ignoreCase = true) == true
                }
                if (matching.isEmpty()) null else section.copy(items = matching)
            }
        }
    }
    val sortedSections = remember(filteredSectionsBySearch, effectiveLayoutForSaved, uiState.sourceMode, sourceMode, providerOrders, visibleSortOption) {
        if (sourceMode == LibraryViewMode.Saved && effectiveLayoutForSaved == LibraryLayoutMode.HORIZONTAL) {
            sortLibrarySections(
                sections = filteredSectionsBySearch,
                selected = visibleSortOption,
                sourceMode = uiState.sourceMode,
                providerOrders = providerOrders.ranks,
            )
        } else {
            emptyList()
        }
    }
    val effectiveSectionKeyForProjection = if (uiState.sourceMode == LibrarySourceMode.LOCAL) {
        selectedLocalCategoryKey
    } else {
        selectedLibrarySectionKey
    }
    val verticalProjection = remember(
        uiState.sections,
        uiState.sourceMode,
        effectiveSectionKeyForProjection,
        selectedLibraryType,
        libraryGenre,
        libraryYear,
        libraryWatchedFilter,
        savedSearchQuery,
        watchedUiState.watchedKeys,
        fullyWatchedSeriesKeys,
        effectiveLayoutForSaved,
        sourceMode,
        providerOrders,
        visibleSortOption,
    ) {
        if (sourceMode == LibraryViewMode.Saved && effectiveLayoutForSaved == LibraryLayoutMode.VERTICAL) {
            buildLibraryVerticalProjection(
                sections = uiState.sections,
                sourceMode = uiState.sourceMode,
                selectedSectionKey = effectiveSectionKeyForProjection,
                selectedType = selectedLibraryType,
                sortOption = visibleSortOption,
                providerOrders = providerOrders.ranks,
                selectedGenre = libraryGenre,
                selectedYear = libraryYear,
                watchedFilter = libraryWatchedFilter,
                searchQuery = savedSearchQuery,
                isWatched = { item ->
                    WatchingState.isPosterWatched(
                        watchedKeys = watchedUiState.watchedKeys,
                        item = item.toMetaPreview(),
                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                    )
                },
            )
        } else {
            LibraryVerticalProjection(
                availableSections = emptyList(),
                selectedSectionKey = null,
                availableTypes = emptyList(),
                selectedType = null,
                entries = emptyList(),
            )
        }
    }""",
        "LibraryScreen verticalProjection & sortedSections with category tabs",
    )

    _replace_once(
        screen_path,
        """    val librarySectionsDisplay = if (
        sourceMode == LibraryViewMode.Saved &&
        displaySettings.layoutMode == LibraryLayoutMode.HORIZONTAL &&
        uiState.isLoaded &&
        sortedSections.isNotEmpty()
    ) {""",
        """    val librarySectionsDisplay = if (
        sourceMode == LibraryViewMode.Saved &&
        effectiveLayoutForSaved == LibraryLayoutMode.HORIZONTAL &&
        uiState.isLoaded &&
        sortedSections.isNotEmpty()
    ) {""",
        "LibraryScreen librarySectionsDisplay effectiveLayoutForSaved",
    )

    _replace_once(
        screen_path,
        """                    if (sourceMode == LibraryViewMode.Saved) {
                        val openCalendarLabel = stringResource(Res.string.library_calendar_open)
                        IconButton(
                            onClick = { showReleaseCalendar = true },
                            modifier = Modifier
                                .size(40.dp)
                                .semantics { contentDescription = openCalendarLabel },
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.CalendarMonth,
                                contentDescription = null,
                                modifier = Modifier.size(22.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }""",
        """                    if (sourceMode == LibraryViewMode.Saved) {
                        IconButton(
                            onClick = {
                                if (savedSearchVisible) savedSearchQuery = ""
                                savedSearchVisible = !savedSearchVisible
                            },
                            modifier = Modifier
                                .size(40.dp)
                                .semantics { contentDescription = "Search Library" },
                        ) {
                            Icon(
                                imageVector = if (savedSearchVisible) Icons.Rounded.Close else Icons.Rounded.Search,
                                contentDescription = null,
                                modifier = Modifier.size(22.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        val openCalendarLabel = stringResource(Res.string.library_calendar_open)
                        IconButton(
                            onClick = { showReleaseCalendar = true },
                            modifier = Modifier
                                .size(40.dp)
                                .semantics { contentDescription = openCalendarLabel },
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.CalendarMonth,
                                contentDescription = null,
                                modifier = Modifier.size(22.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }""",
        "LibraryScreen Saved search icon button",
    )

    _replace_once(
        screen_path,
        """                Spacer(modifier = Modifier.height(6.dp))
            }
        }""",
        """                if (sourceMode == LibraryViewMode.Saved && uiState.sourceMode == LibrarySourceMode.LOCAL) {
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
                }
                AnimatedVisibility(
                    visible = sourceMode == LibraryViewMode.Saved && savedSearchVisible,
                    enter = expandVertically() + fadeIn(),
                    exit = shrinkVertically() + fadeOut(),
                ) {
                    OutlinedTextField(
                        value = savedSearchQuery,
                        onValueChange = { savedSearchQuery = it },
                        singleLine = true,
                        placeholder = { Text("Search saved titles, genres, or release year...") },
                        leadingIcon = {
                            Icon(
                                imageVector = Icons.Rounded.Search,
                                contentDescription = null,
                            )
                        },
                        trailingIcon = if (savedSearchQuery.isNotEmpty()) {
                            {
                                IconButton(onClick = { savedSearchQuery = "" }) {
                                    Icon(
                                        imageVector = Icons.Rounded.Close,
                                        contentDescription = "Clear search",
                                    )
                                }
                            }
                        } else null,
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 6.dp),
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
            }
        }""",
        "LibraryScreen top CategoryNavBar & collapsible search field",
    )

    _replace_once(
        screen_path,
        """                    uiState.sections.isEmpty() -> {
                        item {
                            HomeEmptyStateCard(
                                modifier = Modifier.padding(horizontal = 16.dp),
                                title = when (uiState.sourceMode) {
                                    LibrarySourceMode.LOCAL -> stringResource(Res.string.library_empty_title)
                                    LibrarySourceMode.TRAKT -> stringResource(Res.string.library_trakt_empty_title)
                                    LibrarySourceMode.SIMKL -> stringResource(Res.string.library_simkl_empty_title)
                                    LibrarySourceMode.MDBLIST -> stringResource(Res.string.library_mdblist_empty_title)
                                    LibrarySourceMode.ANILIST -> stringResource(Res.string.library_anilist_empty_title)
                                    LibrarySourceMode.WETRAKR -> stringResource(Res.string.library_wetrakr_empty_title)
                                },
                                message = when (uiState.sourceMode) {
                                    LibrarySourceMode.LOCAL -> stringResource(Res.string.library_empty_message)
                                    LibrarySourceMode.TRAKT -> stringResource(Res.string.library_trakt_empty_message)
                                    LibrarySourceMode.SIMKL -> stringResource(Res.string.library_simkl_empty_message)
                                    LibrarySourceMode.MDBLIST -> stringResource(Res.string.library_mdblist_empty_message)
                                    LibrarySourceMode.ANILIST -> stringResource(Res.string.library_anilist_empty_message)
                                    LibrarySourceMode.WETRAKR -> stringResource(Res.string.library_wetrakr_empty_message)
                                },
                            )
                        }
                    }

                    else -> {
                        stickyHeader(
                            key = "library-saved-controls:${uiState.sourceMode}:" +
                                "${displaySettings.layoutMode}:$effectiveSortOption",
                        ) {
                            Box(modifier = Modifier.fillMaxWidth()) {
                                Box(
                                    modifier = Modifier
                                        .matchParentSize()
                                        .appBackgroundCover(MaterialTheme.colorScheme.background)
                                        .nuvioConsumePointerEvents(),
                                )
                                LibrarySavedControls(
                                    layoutMode = displaySettings.layoutMode,
                                    sourceMode = uiState.sourceMode,
                                    sortOption = effectiveSortOption,
                                    verticalProjection = verticalProjection,
                                    watchedFilter = libraryWatchedFilter,
                                    onSectionSelected = { sectionKey ->
                                        selectedLibrarySectionKey = sectionKey
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
                        }
                        when (displaySettings.layoutMode) {
                            LibraryLayoutMode.HORIZONTAL -> {
                                libraryEnhancedSections(
                                    content = enhancedLibraryContent,
                                    onPosterClick = onPosterClick,
                                )
                                librarySections(
                                    displaySections = librarySectionsDisplay,
                                    releaseInfoFor = releaseInfoFor,
                                    watchedKeys = watchedUiState.watchedKeys,
                                    fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                    sortOption = effectiveSortOption,
                                    posterPattern = effectivePosterPattern,
                                    onPosterClick = onPosterClick,
                                    onSectionViewAllClick = onSectionViewAllClick,
                                    onPosterLongClick = onPosterLongClick,
                                    onDisintegrated = disintegration::onExited,
                                )
                            }
                            LibraryLayoutMode.VERTICAL -> libraryVerticalContent(
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
                    }""",
        """                    uiState.sections.isEmpty() -> {
                        val selectedCategory = LocalLibraryCategory.fromKey(selectedLocalCategoryKey)
                        item {
                            HomeEmptyStateCard(
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                title = if (uiState.sourceMode == LibrarySourceMode.LOCAL && selectedCategory != null) {
                                    selectedCategory.emptyTitle
                                } else {
                                    when (uiState.sourceMode) {
                                        LibrarySourceMode.LOCAL -> stringResource(Res.string.library_empty_title)
                                        LibrarySourceMode.TRAKT -> stringResource(Res.string.library_trakt_empty_title)
                                        LibrarySourceMode.SIMKL -> stringResource(Res.string.library_simkl_empty_title)
                                        LibrarySourceMode.MDBLIST -> stringResource(Res.string.library_mdblist_empty_title)
                                        LibrarySourceMode.ANILIST -> stringResource(Res.string.library_anilist_empty_title)
                                        LibrarySourceMode.WETRAKR -> stringResource(Res.string.library_wetrakr_empty_title)
                                    }
                                },
                                message = if (uiState.sourceMode == LibrarySourceMode.LOCAL && selectedCategory != null) {
                                    selectedCategory.emptyMessage
                                } else {
                                    when (uiState.sourceMode) {
                                        LibrarySourceMode.LOCAL -> stringResource(Res.string.library_empty_message)
                                        LibrarySourceMode.TRAKT -> stringResource(Res.string.library_trakt_empty_message)
                                        LibrarySourceMode.SIMKL -> stringResource(Res.string.library_simkl_empty_message)
                                        LibrarySourceMode.MDBLIST -> stringResource(Res.string.library_mdblist_empty_message)
                                        LibrarySourceMode.ANILIST -> stringResource(Res.string.library_anilist_empty_message)
                                        LibrarySourceMode.WETRAKR -> stringResource(Res.string.library_wetrakr_empty_message)
                                    }
                                },
                            )
                        }
                    }

                    else -> {
                        stickyHeader(
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
                        }
                        when (effectiveLayoutForSaved) {
                            LibraryLayoutMode.HORIZONTAL -> {
                                libraryEnhancedSections(
                                    content = enhancedLibraryContent,
                                    onPosterClick = onPosterClick,
                                )
                                if (librarySectionsDisplay.isEmpty() && savedSearchQuery.isNotBlank()) {
                                    item(key = "library_search_empty_horizontal") {
                                        HomeEmptyStateCard(
                                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                            title = "No matching titles",
                                            message = "Nothing in your Library matched “${savedSearchQuery.trim()}”.",
                                            actionLabel = "Clear search",
                                            onActionClick = { savedSearchQuery = "" },
                                        )
                                    }
                                } else {
                                    librarySections(
                                        displaySections = librarySectionsDisplay,
                                        releaseInfoFor = releaseInfoFor,
                                        watchedKeys = watchedUiState.watchedKeys,
                                        fullyWatchedSeriesKeys = fullyWatchedSeriesKeys,
                                        sortOption = effectiveSortOption,
                                        posterPattern = effectivePosterPattern,
                                        onPosterClick = onPosterClick,
                                        onSectionViewAllClick = { section, sort ->
                                            if (uiState.sourceMode == LibrarySourceMode.LOCAL &&
                                                LocalLibraryCategory.fromKey(section.type) != null
                                            ) {
                                                selectedLocalCategoryKey = section.type
                                            } else {
                                                onSectionViewAllClick?.invoke(section, sort)
                                            }
                                        },
                                        onPosterLongClick = onPosterLongClick,
                                        onDisintegrated = disintegration::onExited,
                                    )
                                }
                            }
                            LibraryLayoutMode.VERTICAL -> {
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
                    }""",
        "LibraryScreen empty states & focused category rendering",
    )
    changed.append(str(screen_path.relative_to(root)))


def _patch_details_and_poster_picker(root: Path, changed: list[str]) -> None:
    # 1. DetailActionButtons.kt: show active category label on Details hero button
    buttons_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/DetailActionButtons.kt"
    )
    _replace_once(
        buttons_path,
        """    iconActionRow: Boolean = false,
    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,
) {
    val actionSet = detailActionSet(
        isSaved = isSaved,
        isWatched = isWatched,""",
        """    iconActionRow: Boolean = false,
    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,
    savedCategoryLabel: String? = null,
) {
    val actionSet = detailActionSet(
        isSaved = isSaved,
        savedCategoryLabel = savedCategoryLabel,
        isWatched = isWatched,""",
        "DetailActionButtons savedCategoryLabel param",
    )
    _replace_once(
        buttons_path,
        """private fun detailActionSet(
    isSaved: Boolean,
    isWatched: Boolean,""",
        """private fun detailActionSet(
    isSaved: Boolean,
    savedCategoryLabel: String? = null,
    isWatched: Boolean,""",
        "detailActionSet savedCategoryLabel signature",
    )
    _replace_once(
        buttons_path,
        """    val saveAction = DetailSecondaryAction(
        label = stringResource(if (isSaved) Res.string.hero_remove_from_library else Res.string.hero_add_to_library),
        icon = Icons.Default.Add,
        drawable = Res.drawable.sidebar_library.takeIf { isSaved },
        isActive = isSaved,
        onClick = onSaveClick,
        onLongClick = onSaveLongClick,
    )""",
        """    val saveAction = DetailSecondaryAction(
        label = if (isSaved && !savedCategoryLabel.isNullOrBlank()) {
            savedCategoryLabel
        } else {
            stringResource(if (isSaved) Res.string.hero_remove_from_library else Res.string.hero_add_to_library)
        },
        icon = Icons.Default.Add,
        drawable = Res.drawable.sidebar_library.takeIf { isSaved },
        isActive = isSaved,
        onClick = onSaveClick,
        onLongClick = onSaveLongClick,
    )""",
        "detailActionSet active category label",
    )
    _replace_once(
        buttons_path,
        """    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,
) {
    val actionSet = detailActionSet(
        isSaved = isSaved,
        isWatched = isWatched,
        shuffleEnabled = shuffleEnabled,""",
        """    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,
    savedCategoryLabel: String? = null,
) {
    val actionSet = detailActionSet(
        isSaved = isSaved,
        savedCategoryLabel = savedCategoryLabel,
        isWatched = isWatched,
        shuffleEnabled = shuffleEnabled,""",
        "TabletDetailHeroActions savedCategoryLabel param",
    )
    changed.append(str(buttons_path.relative_to(root)))

    # 2. MetaDetailsScreen.kt: wire Library button to Category Picker + Duplicate Title Guard + Category label
    details_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/MetaDetailsScreen.kt"
    )
    _replace_once(
        details_path,
        "import com.nuvio.app.features.library.LibraryRepository\n",
        "import com.nuvio.app.features.library.DuplicateLibraryResolution\n"
        "import com.nuvio.app.features.library.LibraryRepository\n"
        "import com.nuvio.app.features.library.LocalLibraryCategory\n"
        "import com.nuvio.app.features.library.localCategorySummaryLabel\n",
        "MetaDetailsScreen library category imports",
    )
    _replace_once(
        details_path,
        """                val isSaved = remember(
                    libraryUiState.items,
                    libraryUiState.sections,
                    libraryUiState.sourceMode,
                    meta.id,
                    meta.type,
                ) {
                    LibraryRepository.isSaved(meta.id, meta.type)
                }""",
        """                val isSaved = remember(
                    libraryUiState.items,
                    libraryUiState.sections,
                    libraryUiState.sourceMode,
                    meta.id,
                    meta.type,
                ) {
                    LibraryRepository.isSaved(meta.id, meta.type)
                }
                val savedCategoryLabel = remember(
                    libraryUiState.items,
                    libraryUiState.sections,
                    libraryUiState.sourceMode,
                    meta.id,
                    meta.type,
                ) {
                    LibraryRepository.savedItem(meta.id, meta.type)?.localCategorySummaryLabel()
                }""",
        "MetaDetailsScreen savedCategoryLabel",
    )
    _replace_once(
        details_path,
        """                val openLibraryListPicker = remember(meta) {
                    {
                        val libraryItem = meta.toLibraryItem(savedAtEpochMs = 0L)
                        pickerTabs = LibraryRepository.libraryListTabs(libraryItem)
                        pickerMembership = pickerTabs.associate { it.key to false }
                        pickerPending = true
                        pickerError = null
                        showLibraryListPicker = true
                        detailsScope.launch {
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
                        Unit
                    }
                }""",
        """                val openLibraryListPicker = remember(meta) {
                    {
                        val libraryItem = meta.toLibraryItem(savedAtEpochMs = 0L)
                        val initialTabs = LibraryRepository.libraryListTabs(libraryItem)
                        pickerTabs = initialTabs
                        val alreadyInLocal = LibraryRepository.isSaved(meta.id, meta.type)
                        pickerMembership = initialTabs.associate { tab ->
                            tab.key to (!alreadyInLocal && tab.key == LocalLibraryCategory.PLAN_TO_WATCH.key)
                        }
                        pickerPending = true
                        pickerError = null
                        showLibraryListPicker = true
                        detailsScope.launch {
                            runCatching {
                                val snapshot = LibraryRepository.getMembershipSnapshot(libraryItem)
                                val tabs = LibraryRepository.libraryListTabs(libraryItem)
                                val hasAnyExisting = tabs.any { snapshot[it.key] == true }
                                pickerTabs = tabs
                                pickerMembership = tabs.associate { tab ->
                                    val checked = if (hasAnyExisting) {
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
                        Unit
                    }
                }""",
        "MetaDetailsScreen openLibraryListPicker preselection",
    )
    _replace_once(
        details_path,
        """                                                        TabletDetailHeroActions(
                                                            playLabel = playButtonLabel,
                                                            playEnabled = isPrimaryPlayEnabled,
                                                            isSaved = isSaved,
                                                            isWatched = isWatched,
                                                            shuffleEnabled = shuffleSettings.enabled,
                                                            landscape = isTabletLandscape,
                                                            onPlayClick = onPrimaryPlayClick,
                                                            onPlayLongClick = if (showManualPlayOption) onPrimaryPlayLongClick else null,
                                                            onShuffleClick = onShuffleClick,
                                                            onWatchedClick = toggleWatched,
                                                            onSaveClick = toggleSaved,
                                                            onSaveLongClick = openLibraryListPicker,""",
        """                                                        TabletDetailHeroActions(
                                                            playLabel = playButtonLabel,
                                                            playEnabled = isPrimaryPlayEnabled,
                                                            isSaved = isSaved,
                                                            savedCategoryLabel = savedCategoryLabel,
                                                            isWatched = isWatched,
                                                            shuffleEnabled = shuffleSettings.enabled,
                                                            landscape = isTabletLandscape,
                                                            onPlayClick = onPrimaryPlayClick,
                                                            onPlayLongClick = if (showManualPlayOption) onPrimaryPlayLongClick else null,
                                                            onShuffleClick = onShuffleClick,
                                                            onWatchedClick = toggleWatched,
                                                            onSaveClick = openLibraryListPicker,
                                                            onSaveLongClick = openLibraryListPicker,""",
        "MetaDetailsScreen TabletDetailHeroActions openLibraryListPicker",
    )
    _replace_once(
        details_path,
        """                                        onPrimaryPlayLongClick = onPrimaryPlayLongClick,
                                        onSaveClick = toggleSaved,
                                        onSaveLongClick = openLibraryListPicker,
                                        onWatchedClick = toggleWatched,
                                        userRating = titleUserRating,
                                        onRateClick = openTitleRating,""",
        """                                        onPrimaryPlayLongClick = onPrimaryPlayLongClick,
                                        onSaveClick = openLibraryListPicker,
                                        onSaveLongClick = openLibraryListPicker,
                                        savedCategoryLabel = savedCategoryLabel,
                                        onWatchedClick = toggleWatched,
                                        userRating = titleUserRating,
                                        onRateClick = openTitleRating,""",
        "MetaDetailsScreen phone DetailContentSections openLibraryListPicker",
    )
    _replace_once(
        details_path,
        """                        DetailHeaderOverlay(
                            meta = meta,
                            isSaved = isSaved,
                            isHeroCollapsed = isHeroCollapsed,
                            backgroundColor = dominantBackdropColor.takeIf { dominantColorEnabled },
                            onBack = onBackFromDetails,
                            onToggleSaved = toggleSaved,
                            glassBackdrop = cinematicContentBackdrop.takeIf { cinematicGlassEnabled && it.isReady },
                        )""",
        """                        DetailHeaderOverlay(
                            meta = meta,
                            isSaved = isSaved,
                            isHeroCollapsed = isHeroCollapsed,
                            backgroundColor = dominantBackdropColor.takeIf { dominantColorEnabled },
                            onBack = onBackFromDetails,
                            onToggleSaved = openLibraryListPicker,
                            glassBackdrop = cinematicContentBackdrop.takeIf { cinematicGlassEnabled && it.isReady },
                        )""",
        "MetaDetailsScreen DetailHeaderOverlay openLibraryListPicker",
    )
    _replace_once(
        details_path,
        """                        TrackingListPickerDialog(
                            visible = showLibraryListPicker,
                            title = meta.name,
                            tabs = pickerTabs,
                            membership = pickerMembership,
                            isPending = pickerPending,
                            errorMessage = pickerError,
                            onToggle = { listKey ->
                                pickerMembership = toggleTrackingLibraryMembership(
                                    tabs = pickerTabs,
                                    membership = pickerMembership,
                                    key = listKey,
                                )
                            },
                            onDismiss = {
                                if (!pickerPending) {
                                    showLibraryListPicker = false
                                }
                            },
                            onSave = {
                                detailsScope.launch {
                                    pickerPending = true
                                    pickerError = null
                                    val item = meta.toLibraryItem(savedAtEpochMs = 0L)
                                    val desiredMembership = pickerMembership.toMap()
                                    val applyMembership: suspend (Set<TrackingProviderId>) ->
                                        TrackingMembershipApplyResult = { confirmedProviders ->
                                        LibraryRepository.applyMembershipChanges(
                                            item = item,
                                            desiredMembership = desiredMembership,
                                            confirmedRemovalProviders = confirmedProviders,
                                        )
                                    }
                                    val completeMembershipUpdate: suspend (TrackingMembershipApplyResult) -> Unit = { result ->
                                        showTrackingMembershipRewriteFeedback(result)
                                        showLibraryListPicker = false
                                    }
                                    executeTrackingMembershipOperation(
                                        operation = { applyMembership(emptySet()) },
                                        onSuccess = { result ->
                                            if (result.requiresRemovalConfirmation) {
                                                pendingTrackingRemoval = PendingTrackingMembershipRemoval(
                                                    itemTitle = item.name,
                                                    confirmations = result.requiredRemovalConfirmations,
                                                    retry = applyMembership,
                                                    onApplied = completeMembershipUpdate,
                                                    onFailure = { error ->
                                                        pickerError = error.message
                                                            ?: trackingListsUpdateFailedMessage
                                                    },
                                                )
                                            } else {
                                                completeMembershipUpdate(result)
                                            }
                                        },
                                        onFailure = { error ->
                                            pickerError = error.message ?: trackingListsUpdateFailedMessage
                                        },
                                    )
                                    pickerPending = false
                                }
                            },
                        )""",
        """                        val pickerTargetItem = remember(meta) { meta.toLibraryItem(savedAtEpochMs = 0L) }
                        val submitDetailsMembership: (DuplicateLibraryResolution?) -> Unit = { resolution ->
                            detailsScope.launch {
                                pickerPending = true
                                pickerError = null
                                val item = meta.toLibraryItem(savedAtEpochMs = 0L)
                                val desiredMembership = pickerMembership.toMap()
                                val applyMembership: suspend (Set<TrackingProviderId>) ->
                                    TrackingMembershipApplyResult = { confirmedProviders ->
                                    LibraryRepository.applyMembershipChanges(
                                        item = item,
                                        desiredMembership = desiredMembership,
                                        confirmedRemovalProviders = confirmedProviders,
                                        duplicateResolution = resolution,
                                    )
                                }
                                val completeMembershipUpdate: suspend (TrackingMembershipApplyResult) -> Unit = { result ->
                                    showTrackingMembershipRewriteFeedback(result)
                                    val chosen = LocalLibraryCategory.entries
                                        .filter { desiredMembership[it.key] == true }
                                        .joinToString(", ") { it.label }
                                    if (chosen.isNotBlank()) {
                                        NuvioToastController.show("Saved to $chosen")
                                    } else {
                                        NuvioToastController.show("Removed from Library")
                                    }
                                    showLibraryListPicker = false
                                }
                                executeTrackingMembershipOperation(
                                    operation = { applyMembership(emptySet()) },
                                    onSuccess = { result ->
                                        if (result.requiresRemovalConfirmation) {
                                            pendingTrackingRemoval = PendingTrackingMembershipRemoval(
                                                itemTitle = item.name,
                                                confirmations = result.requiredRemovalConfirmations,
                                                retry = applyMembership,
                                                onApplied = completeMembershipUpdate,
                                                onFailure = { error ->
                                                    pickerError = error.message
                                                        ?: trackingListsUpdateFailedMessage
                                                },
                                            )
                                        } else {
                                            completeMembershipUpdate(result)
                                        }
                                    },
                                    onFailure = { error ->
                                        pickerError = error.message ?: trackingListsUpdateFailedMessage
                                    },
                                )
                                pickerPending = false
                            }
                        }
                        TrackingListPickerDialog(
                            visible = showLibraryListPicker,
                            title = meta.name,
                            tabs = pickerTabs,
                            membership = pickerMembership,
                            isPending = pickerPending,
                            errorMessage = pickerError,
                            targetItem = pickerTargetItem,
                            onToggle = { listKey ->
                                pickerMembership = toggleTrackingLibraryMembership(
                                    tabs = pickerTabs,
                                    membership = pickerMembership,
                                    key = listKey,
                                )
                            },
                            onDismiss = {
                                if (!pickerPending) {
                                    showLibraryListPicker = false
                                }
                            },
                            onSave = { submitDetailsMembership(null) },
                            onSaveWithResolution = submitDetailsMembership,
                            onRemoveFromLibrary = {
                                pickerMembership = pickerMembership.mapValues { false }
                                submitDetailsMembership(null)
                            },
                        )""",
        "MetaDetailsScreen TrackingListPickerDialog duplicate resolution & remove",
    )
    _replace_once(
        details_path,
        """    contentHorizontalPadding: Dp,
    contentMaxWidth: Dp,
    playButtonLabel: String,
    isPrimaryPlayEnabled: Boolean,
    isSaved: Boolean,
    isWatched: Boolean,
    onPrimaryPlayClick: () -> Unit,
    onDownloadClick: (() -> Unit)?,
    onPlayFromStartClick: (() -> Unit)?,
    onPlayExternallyClick: (() -> Unit)?,
    onShuffleClick: (() -> Unit)?,
    shuffleEnabled: Boolean,
    onPrimaryPlayLongClick: (() -> Unit)?,
    onSaveClick: () -> Unit,
    onSaveLongClick: (() -> Unit)?,
    onWatchedClick: () -> Unit,
    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,""",
        """    contentHorizontalPadding: Dp,
    contentMaxWidth: Dp,
    playButtonLabel: String,
    isPrimaryPlayEnabled: Boolean,
    isSaved: Boolean,
    isWatched: Boolean,
    onPrimaryPlayClick: () -> Unit,
    onDownloadClick: (() -> Unit)?,
    onPlayFromStartClick: (() -> Unit)?,
    onPlayExternallyClick: (() -> Unit)?,
    onShuffleClick: (() -> Unit)?,
    shuffleEnabled: Boolean,
    onPrimaryPlayLongClick: (() -> Unit)?,
    onSaveClick: () -> Unit,
    onSaveLongClick: (() -> Unit)?,
    savedCategoryLabel: String? = null,
    onWatchedClick: () -> Unit,
    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,""",
        "configuredMetaSectionItems savedCategoryLabel param",
    )
    _replace_once(
        details_path,
        """                    onSaveClick = onSaveClick,
                    onSaveLongClick = onSaveLongClick,
                    onWatchedClick = onWatchedClick,
                    userRating = userRating,
                    onRateClick = onRateClick,""",
        """                    onSaveClick = onSaveClick,
                    onSaveLongClick = onSaveLongClick,
                    savedCategoryLabel = savedCategoryLabel,
                    onWatchedClick = onWatchedClick,
                    userRating = userRating,
                    onRateClick = onRateClick,""",
        "configuredMetaSectionItems forward savedCategoryLabel",
    )
    _replace_once(
        details_path,
        """    horizontalScrollPadding: Dp,
    playButtonLabel: String,
    isPrimaryPlayEnabled: Boolean,
    isSaved: Boolean,
    isWatched: Boolean,
    onPrimaryPlayClick: () -> Unit,
    onDownloadClick: (() -> Unit)?,
    onPlayFromStartClick: (() -> Unit)?,
    onPlayExternallyClick: (() -> Unit)?,
    onShuffleClick: (() -> Unit)?,
    shuffleEnabled: Boolean,
    onPrimaryPlayLongClick: (() -> Unit)?,
    onSaveClick: () -> Unit,
    onSaveLongClick: (() -> Unit)?,
    onWatchedClick: () -> Unit,
    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,
    showManualPlayOption: Boolean,""",
        """    horizontalScrollPadding: Dp,
    playButtonLabel: String,
    isPrimaryPlayEnabled: Boolean,
    isSaved: Boolean,
    isWatched: Boolean,
    onPrimaryPlayClick: () -> Unit,
    onDownloadClick: (() -> Unit)?,
    onPlayFromStartClick: (() -> Unit)?,
    onPlayExternallyClick: (() -> Unit)?,
    onShuffleClick: (() -> Unit)?,
    shuffleEnabled: Boolean,
    onPrimaryPlayLongClick: (() -> Unit)?,
    onSaveClick: () -> Unit,
    onSaveLongClick: (() -> Unit)?,
    savedCategoryLabel: String? = null,
    onWatchedClick: () -> Unit,
    userRating: Int? = null,
    onRateClick: (() -> Unit)? = null,
    showManualPlayOption: Boolean,""",
        "ConfiguredMetaSections savedCategoryLabel param",
    )
    _replace_once(
        details_path,
        """                    iconActionRow = settings.iconActionRow,
                    userRating = userRating,
                    onRateClick = onRateClick,
                )""",
        """                    iconActionRow = settings.iconActionRow,
                    userRating = userRating,
                    onRateClick = onRateClick,
                    savedCategoryLabel = savedCategoryLabel,
                )""",
        "PhoneHeroSection forward savedCategoryLabel to DetailActionButtons",
    )
    changed.append(str(details_path.relative_to(root)))

    # 3. MainAppContent.kt: upgrade Poster Zoom Overlay + TrackingListPickerDialog
    main_app_path = (
        root / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"
    )
    _replace_once(
        main_app_path,
        "import com.nuvio.app.features.library.LibraryRepository\n",
        "import com.nuvio.app.features.library.DuplicateLibraryResolution\n"
        "import com.nuvio.app.features.library.LibraryRepository\n"
        "import com.nuvio.app.features.library.LocalLibraryCategory\n",
        "MainAppContent library category imports",
    )
    _replace_once(
        main_app_path,
        """                                    } else {
                                        if (!isRemoteLibrarySource) {
                                            LibraryRepository.toggleLocalSaved(libraryItem)
                                        } else {
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
                                        }
                                    }
                                },
                            ),
                            PosterZoomOverlayAction(""",
        """                                    } else {
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
                            PosterZoomOverlayAction(""",
        "MainAppContent PosterZoomOverlay category picker & Change Category action",
    )
    _replace_once(
        main_app_path,
        """            TrackingListPickerDialog(
                visible = showLibraryListPicker,
                title = pickerTitle,
                tabs = pickerTabs,
                membership = pickerMembership,
                isPending = pickerPending,
                errorMessage = pickerError,
                onToggle = { listKey ->
                    pickerMembership = toggleTrackingLibraryMembership(
                        tabs = pickerTabs,
                        membership = pickerMembership,
                        key = listKey,
                    )
                },
                onDismiss = {
                    if (!pickerPending) {
                        showLibraryListPicker = false
                        pickerItem = null
                        pickerError = null
                    }
                },
                onSave = {
                    val item = pickerItem ?: return@TrackingListPickerDialog
                    coroutineScope.launch {
                        pickerPending = true
                        pickerError = null
                        val desiredMembership = pickerMembership.toMap()
                        val applyMembership: suspend (Set<TrackingProviderId>) ->
                            TrackingMembershipApplyResult = { confirmedProviders ->
                            LibraryRepository.applyMembershipChanges(
                                item = item,
                                desiredMembership = desiredMembership,
                                confirmedRemovalProviders = confirmedProviders,
                            )
                        }""",
        """            val submitGlobalMembership: (DuplicateLibraryResolution?) -> Unit = submit@{ resolution ->
                val item = pickerItem ?: return@submit
                coroutineScope.launch {
                    pickerPending = true
                    pickerError = null
                    val desiredMembership = pickerMembership.toMap()
                    val applyMembership: suspend (Set<TrackingProviderId>) ->
                        TrackingMembershipApplyResult = { confirmedProviders ->
                        LibraryRepository.applyMembershipChanges(
                            item = item,
                            desiredMembership = desiredMembership,
                            confirmedRemovalProviders = confirmedProviders,
                            duplicateResolution = resolution,
                        )
                    }
                    val completeMembershipUpdate: suspend (TrackingMembershipApplyResult) -> Unit = { result ->
                        showTrackingMembershipRewriteFeedback(result)
                        val chosen = LocalLibraryCategory.entries
                            .filter { desiredMembership[it.key] == true }
                            .joinToString(", ") { it.label }
                        if (chosen.isNotBlank()) {
                            NuvioToastController.show("Saved to $chosen")
                        }
                        showLibraryListPicker = false
                        pickerItem = null
                        pickerError = null
                    }
                    executeTrackingMembershipOperation(
                        operation = { applyMembership(emptySet()) },
                        onSuccess = { result ->
                            if (result.requiresRemovalConfirmation) {
                                pendingTrackingRemoval = PendingTrackingMembershipRemoval(
                                    itemTitle = item.name,
                                    confirmations = result.requiredRemovalConfirmations,
                                    retry = applyMembership,
                                    onApplied = completeMembershipUpdate,
                                    onFailure = { error ->
                                        pickerError = error.message ?: trackingListsUpdateFailedMessage
                                    },
                                )
                            } else {
                                completeMembershipUpdate(result)
                            }
                        },
                        onFailure = { error ->
                            pickerError = error.message ?: trackingListsUpdateFailedMessage
                        },
                    )
                    pickerPending = false
                }
            }
            TrackingListPickerDialog(
                visible = showLibraryListPicker,
                title = pickerTitle,
                tabs = pickerTabs,
                membership = pickerMembership,
                isPending = pickerPending,
                errorMessage = pickerError,
                targetItem = pickerItem,
                onToggle = { listKey ->
                    pickerMembership = toggleTrackingLibraryMembership(
                        tabs = pickerTabs,
                        membership = pickerMembership,
                        key = listKey,
                    )
                },
                onDismiss = {
                    if (!pickerPending) {
                        showLibraryListPicker = false
                        pickerItem = null
                        pickerError = null
                    }
                },
                onSaveWithResolution = submitGlobalMembership,
                onRemoveFromLibrary = {
                    pickerMembership = pickerMembership.mapValues { false }
                    submitGlobalMembership(null)
                },
                onSave = {
                    val item = pickerItem ?: return@TrackingListPickerDialog
                    coroutineScope.launch {
                        pickerPending = true
                        pickerError = null
                        val desiredMembership = pickerMembership.toMap()
                        val applyMembership: suspend (Set<TrackingProviderId>) ->
                            TrackingMembershipApplyResult = { confirmedProviders ->
                            LibraryRepository.applyMembershipChanges(
                                item = item,
                                desiredMembership = desiredMembership,
                                confirmedRemovalProviders = confirmedProviders,
                            )
                        }""",
        "MainAppContent TrackingListPickerDialog duplicate guard",
    )
    changed.append(str(main_app_path.relative_to(root)))


def _patch_cloudstream_filter_and_sort(root: Path, changed: list[str]) -> None:
    cs_path = (
        root
        / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/plugins/CloudStreamSettingsSection.kt"
    )
    _replace_once(
        cs_path,
        "@OptIn(ExperimentalLayoutApi::class)\n@Composable\ninternal fun CloudStreamSettingsSection() {",
        """private enum class CloudStreamStatusFilter(val key: String) {
    ALL("all"),
    INSTALLED("installed"),
    ENABLED("enabled"),
    UPDATES("updates"),
    PINNED("pinned"),
    AVAILABLE("available"),
}

private enum class CloudStreamSortOrder(val key: String) {
    SMART("smart"),
    ENABLED_FIRST("enabled_first"),
    INSTALLED_FIRST("installed_first"),
    NAME_ASC("name_asc"),
    NAME_DESC("name_desc"),
    VERSION_DESC("version_desc"),
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun CloudStreamSettingsSection() {""",
        "CloudStreamSettingsSection filter & sort enums",
    )

    _replace_once(
        cs_path,
        """    var query by rememberSaveable { mutableStateOf("") }
    var selectedLanguage by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedType by rememberSaveable { mutableStateOf<String?>(null) }""",
        """    var query by rememberSaveable { mutableStateOf("") }
    var selectedLanguage by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedType by rememberSaveable { mutableStateOf<String?>(null) }
    var statusFilterKey by rememberSaveable { mutableStateOf(CloudStreamStatusFilter.ALL.key) }
    var sortOrderKey by rememberSaveable { mutableStateOf(CloudStreamSortOrder.SMART.key) }
    val selectedStatusFilter = remember(statusFilterKey) {
        CloudStreamStatusFilter.entries.firstOrNull { it.key == statusFilterKey } ?: CloudStreamStatusFilter.ALL
    }
    val selectedSortOrder = remember(sortOrderKey) {
        CloudStreamSortOrder.entries.firstOrNull { it.key == sortOrderKey } ?: CloudStreamSortOrder.SMART
    }""",
        "CloudStreamSettingsSection status & sort state",
    )

    _replace_once(
        cs_path,
        """    val visiblePlugins = remember(state.plugins, query, selectedLanguage, selectedType) {
        val normalizedQuery = query.trim().lowercase()
        state.plugins.filter { item ->
            (normalizedQuery.isBlank() || listOf(
                item.metadata.name,
                item.metadata.internalName,
                item.metadata.description.orEmpty(),
                item.metadata.authors.joinToString(" "),
            ).any { it.lowercase().contains(normalizedQuery) }) &&
                (selectedLanguage == null || item.metadata.language == selectedLanguage) &&
                (selectedType == null || selectedType in item.metadata.rawTvTypes)
        }
    }
    val bulkActionPlugins = remember(visiblePlugins) {
        visiblePlugins.filter { item ->
            !item.isInstalling &&
                item.metadata.status.canInstall &&
                item.compatibility.isRunnable &&
                (!item.isRunnable || item.hasUpdate || !item.isInstalled || !item.verified)
        }
    }
    val pinnedSourceIds = remember(sourcePreferences.pinnedSources) {
        sourcePreferences.pinnedSources.map { it.id }.toSet()
    }

    NuvioSectionLabel(copy.sectionTitle)
    NuvioSurfaceCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            NuvioInfoBadge(text = copy.repositoryCount(state.repositories.size))
            NuvioInfoBadge(text = copy.installedCount(state.plugins.count { it.isInstalled }))
            NuvioInfoBadge(text = copy.enabledProviderCount(state.plugins.count { it.isRunnable }))
        }""",
        """    val pinnedSourceIds = remember(sourcePreferences.pinnedSources) {
        sourcePreferences.pinnedSources.map { it.id }.toSet()
    }
    val installedTotalCount = remember(state.plugins) { state.plugins.count { it.isInstalled } }
    val enabledTotalCount = remember(state.plugins) { state.plugins.count { it.isInstalled && it.enabled } }
    val updatesTotalCount = remember(state.plugins) { state.plugins.count { it.isInstalled && it.hasUpdate } }
    val pinnedTotalCount = remember(state.plugins, pinnedSourceIds) {
        state.plugins.count { cloudStreamAddonId(it.metadata.id.value) in pinnedSourceIds }
    }
    val availableNotInstalledCount = remember(state.plugins) { state.plugins.count { !it.isInstalled } }
    val updatableInstalledPlugins = remember(state.plugins) {
        state.plugins.filter { it.isInstalled && it.hasUpdate && !it.isInstalling }
    }
    val visiblePlugins = remember(
        state.plugins,
        query,
        selectedLanguage,
        selectedType,
        selectedStatusFilter,
        selectedSortOrder,
        pinnedSourceIds,
    ) {
        val normalizedQuery = query.trim().lowercase()
        val filtered = state.plugins.filter { item ->
            val matchesStatus = when (selectedStatusFilter) {
                CloudStreamStatusFilter.ALL -> true
                CloudStreamStatusFilter.INSTALLED -> item.isInstalled
                CloudStreamStatusFilter.ENABLED -> item.isInstalled && item.enabled
                CloudStreamStatusFilter.UPDATES -> item.isInstalled && item.hasUpdate
                CloudStreamStatusFilter.PINNED -> cloudStreamAddonId(item.metadata.id.value) in pinnedSourceIds
                CloudStreamStatusFilter.AVAILABLE -> !item.isInstalled
            }
            matchesStatus &&
                (normalizedQuery.isBlank() || listOf(
                    item.metadata.name,
                    item.metadata.internalName,
                    item.metadata.description.orEmpty(),
                    item.metadata.authors.joinToString(" "),
                ).any { it.lowercase().contains(normalizedQuery) }) &&
                (selectedLanguage == null || item.metadata.language == selectedLanguage) &&
                (selectedType == null || selectedType in item.metadata.rawTvTypes)
        }
        val comparator = when (selectedSortOrder) {
            CloudStreamSortOrder.SMART -> compareByDescending<CloudStreamPluginItem> {
                cloudStreamAddonId(it.metadata.id.value) in pinnedSourceIds
            }.thenByDescending { it.isInstalled && it.hasUpdate }
                .thenByDescending { it.isInstalled && it.enabled }
                .thenByDescending { it.isInstalled }
                .thenBy { it.metadata.name.lowercase() }
            CloudStreamSortOrder.ENABLED_FIRST -> compareByDescending<CloudStreamPluginItem> {
                it.isInstalled && it.enabled
            }.thenByDescending { it.isInstalled }
                .thenBy { it.metadata.name.lowercase() }
            CloudStreamSortOrder.INSTALLED_FIRST -> compareByDescending<CloudStreamPluginItem> {
                it.isInstalled
            }.thenByDescending { it.enabled }
                .thenBy { it.metadata.name.lowercase() }
            CloudStreamSortOrder.NAME_ASC -> compareBy<CloudStreamPluginItem> {
                it.metadata.name.lowercase()
            }
            CloudStreamSortOrder.NAME_DESC -> compareByDescending<CloudStreamPluginItem> {
                it.metadata.name.lowercase()
            }
            CloudStreamSortOrder.VERSION_DESC -> compareByDescending<CloudStreamPluginItem> {
                it.metadata.version
            }.thenBy { it.metadata.name.lowercase() }
        }
        filtered.sortedWith(comparator)
    }
    val bulkActionPlugins = remember(visiblePlugins) {
        visiblePlugins.filter { item ->
            !item.isInstalling &&
                item.metadata.status.canInstall &&
                item.compatibility.isRunnable &&
                (!item.isRunnable || item.hasUpdate || !item.isInstalled || !item.verified)
        }
    }

    NuvioSectionLabel(copy.sectionTitle)
    NuvioSurfaceCard {
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            NuvioInfoBadge(text = copy.repositoryCount(state.repositories.size))
            CloudStreamFilterChip(
                label = copy.installedCount(installedTotalCount),
                selected = selectedStatusFilter == CloudStreamStatusFilter.INSTALLED,
                onClick = {
                    statusFilterKey = if (selectedStatusFilter == CloudStreamStatusFilter.INSTALLED) {
                        CloudStreamStatusFilter.ALL.key
                    } else {
                        CloudStreamStatusFilter.INSTALLED.key
                    }
                },
            )
            CloudStreamFilterChip(
                label = copy.enabledProviderCount(enabledTotalCount),
                selected = selectedStatusFilter == CloudStreamStatusFilter.ENABLED,
                onClick = {
                    statusFilterKey = if (selectedStatusFilter == CloudStreamStatusFilter.ENABLED) {
                        CloudStreamStatusFilter.ALL.key
                    } else {
                        CloudStreamStatusFilter.ENABLED.key
                    }
                },
            )
        }""",
        "CloudStreamSettingsSection status/sort filtering & clickable top summary badges",
    )

    _replace_once(
        cs_path,
        """            NuvioInputField(
                value = query,
                onValueChange = { query = it },
                placeholder = copy.searchPlaceholder,
            )
            Spacer(Modifier.height(10.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                CloudStreamFilterChip(copy.allLanguages, selectedLanguage == null) { selectedLanguage = null }""",
        """            NuvioInputField(
                value = query,
                onValueChange = { query = it },
                placeholder = copy.searchPlaceholder,
                trailingContent = if (query.isNotEmpty()) {
                    {
                        IconButton(onClick = { query = "" }) {
                            Icon(Icons.Rounded.Close, contentDescription = "Clear search")
                        }
                    }
                } else null,
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = "Extension Status",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(6.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                CloudStreamFilterChip(
                    label = "All (${state.plugins.size})",
                    selected = selectedStatusFilter == CloudStreamStatusFilter.ALL,
                ) { statusFilterKey = CloudStreamStatusFilter.ALL.key }
                CloudStreamFilterChip(
                    label = "Installed ($installedTotalCount)",
                    selected = selectedStatusFilter == CloudStreamStatusFilter.INSTALLED,
                ) { statusFilterKey = CloudStreamStatusFilter.INSTALLED.key }
                CloudStreamFilterChip(
                    label = "Enabled ($enabledTotalCount)",
                    selected = selectedStatusFilter == CloudStreamStatusFilter.ENABLED,
                ) { statusFilterKey = CloudStreamStatusFilter.ENABLED.key }
                if (updatesTotalCount > 0 || selectedStatusFilter == CloudStreamStatusFilter.UPDATES) {
                    CloudStreamFilterChip(
                        label = "Updates ($updatesTotalCount)",
                        selected = selectedStatusFilter == CloudStreamStatusFilter.UPDATES,
                    ) { statusFilterKey = CloudStreamStatusFilter.UPDATES.key }
                }
                if (pinnedTotalCount > 0 || selectedStatusFilter == CloudStreamStatusFilter.PINNED) {
                    CloudStreamFilterChip(
                        label = "Pinned ($pinnedTotalCount)",
                        selected = selectedStatusFilter == CloudStreamStatusFilter.PINNED,
                    ) { statusFilterKey = CloudStreamStatusFilter.PINNED.key }
                }
                CloudStreamFilterChip(
                    label = "Not Installed ($availableNotInstalledCount)",
                    selected = selectedStatusFilter == CloudStreamStatusFilter.AVAILABLE,
                ) { statusFilterKey = CloudStreamStatusFilter.AVAILABLE.key }
            }
            Spacer(Modifier.height(10.dp))
            Text(
                text = "Sort Extensions",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(6.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                listOf(
                    CloudStreamSortOrder.SMART to "Smart Order",
                    CloudStreamSortOrder.ENABLED_FIRST to "Enabled First",
                    CloudStreamSortOrder.INSTALLED_FIRST to "Installed First",
                    CloudStreamSortOrder.NAME_ASC to "Name (A-Z)",
                    CloudStreamSortOrder.NAME_DESC to "Name (Z-A)",
                    CloudStreamSortOrder.VERSION_DESC to "Newest Version",
                ).forEach { (order, label) ->
                    CloudStreamFilterChip(
                        label = label,
                        selected = selectedSortOrder == order,
                    ) { sortOrderKey = order.key }
                }
            }
            Spacer(Modifier.height(10.dp))
            Text(
                text = "Languages & Types",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(6.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                CloudStreamFilterChip(copy.allLanguages, selectedLanguage == null) { selectedLanguage = null }""",
        "CloudStreamSettingsSection status & sort chip rows",
    )

    _replace_once(
        cs_path,
        """            bulkInstallMessage?.let {
                Spacer(Modifier.height(10.dp))
                Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }""",
        """            if (updatableInstalledPlugins.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                OutlinedButton(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(46.dp),
                    enabled = state.securityWarningAccepted && !isBulkInstalling,
                    onClick = {
                        val updateIds = updatableInstalledPlugins.map { it.metadata.id.value }
                        isBulkInstalling = true
                        bulkInstallMessage = null
                        scope.launch {
                            bulkInstallMessage = runCatching {
                                CloudStreamRepository.installAndEnablePlugins(updateIds).toUserMessage(copy)
                            }.getOrElse { err ->
                                err.message ?: copy.bulkInstallFailed
                            }
                            isBulkInstalling = false
                        }
                    },
                ) {
                    Icon(Icons.Rounded.Refresh, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "Update all installed (${updatableInstalledPlugins.size})",
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
            val hasActiveFilters = query.isNotBlank() ||
                selectedLanguage != null ||
                selectedType != null ||
                selectedStatusFilter != CloudStreamStatusFilter.ALL ||
                selectedSortOrder != CloudStreamSortOrder.SMART
            Spacer(Modifier.height(10.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "Showing ${visiblePlugins.size} of ${state.plugins.size} extensions",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (hasActiveFilters) {
                    Text(
                        text = "Reset filters",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.clickable {
                            query = ""
                            selectedLanguage = null
                            selectedType = null
                            statusFilterKey = CloudStreamStatusFilter.ALL.key
                            sortOrderKey = CloudStreamSortOrder.SMART.key
                        },
                    )
                }
            }
            bulkInstallMessage?.let {
                Spacer(Modifier.height(10.dp))
                Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }""",
        "CloudStreamSettingsSection Update All & active filter summary",
    )
    changed.append(str(cs_path.relative_to(root)))


def _patch_fast_batch_downloads(root: Path, changed: list[str]) -> None:
    # 1. StreamSourceLoader.kt: progressive live stream emission + 0ms StreamsRepository seed + non-blocking CS3
    loader_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamSourceLoader.kt"
    )
    _replace_once(
        loader_path,
        """    suspend fun loadStreams(
        type: String,
        videoId: String,
        season: Int?,
        episode: Int?,
        embeddedStreams: List<StreamItem>,
        timeoutMs: Long,
        meta: MetaDetails? = null,
    ): List<StreamItem> {""",
        """    private data class SourceEmission(
        val index: Int,
        val group: AddonStreamGroup,
        val isFinal: Boolean,
    )

    suspend fun loadStreams(
        type: String,
        videoId: String,
        season: Int?,
        episode: Int?,
        embeddedStreams: List<StreamItem>,
        timeoutMs: Long,
        meta: MetaDetails? = null,
        onProgress: ((List<StreamItem>) -> Unit)? = null,
    ): List<StreamItem> {""",
        "StreamSourceLoader.loadStreams onProgress signature",
    )

    _replace_once(
        loader_path,
        """        val directCloudSources = if (directCloudRoute != null && AppFeaturePolicy.pluginsEnabled) {
            CloudStreamRepository.initialize()
            val pluginItem = CloudStreamRepository.uiState.value.plugins
                .firstOrNull { it.metadata.id.value == directCloudRoute.providerId }
            val directName = pluginItem?.metadata?.name ?: "CloudStream"
            val directAddonId = cloudStreamAddonId(directCloudRoute.providerId)
            listOf(
                StreamSource(directName, directAddonId) {
                    val rawSources = CloudStreamRepository.loadLinks(directCloudRoute.providerId, directCloudRoute.data)
                        .getOrThrow()
                    val items = cloudStreamSourcesToStreamItems(
                        providerId = directCloudRoute.providerId,
                        providerName = directName,
                        sources = rawSources,
                    )
                    AddonStreamGroup(
                        addonName = directName,
                        addonId = directAddonId,
                        streams = items.sortedForGroupedDisplay(),
                        isLoading = false,
                    )
                },
            )
        } else {
            emptyList()
        }
        val sources = directCloudSources +
            targets.streamAddons.map { addon ->
                StreamSource(addon.addonName, addon.addonId) {
                    val group = fetchAddonGroup(addon, type, videoId, forceRefresh = false)
                    checkDebridCache(group, targets.streamAddonIds)
                }
            } + targets.pluginProviderGroups.map { providerGroup ->
                StreamSource(providerGroup.addonName, providerGroup.addonId) {
                    loadPluginProviderGroup(providerGroup, type, videoId, season, episode)
                }
            } + cloudStreamGroups
                .filterNot { it.providerId == directCloudRoute?.providerId }
                .map { csGroup ->
                    StreamSource(csGroup.addonName, csGroup.addonId) {
                        resolveCloudStreamProviderStreams(csGroup, cloudStreamSearchRequest)
                    }
                } + targets.serverSources.map { source ->
                StreamSource(source.addonName, source.addonId) { source.load() }
            }
        if (sources.isEmpty()) return emptyList()

        val results = Channel<Pair<Int, AddonStreamGroup>>(Channel.UNLIMITED)
        val arrivedByIndex = mutableMapOf<Int, AddonStreamGroup>()
        val loadScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        try {
            sources.forEachIndexed { index, source ->
                loadScope.launch {
                    val group = try {
                        present(source.load())
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Throwable) {
                        failedGroup(source.addonName, source.addonId, e)
                    }
                    results.send(index to group)
                }
            }
            withTimeoutOrNull(timeoutMs) {
                repeat(sources.size) {
                    val (index, group) = results.receive()
                    arrivedByIndex[index] = group
                }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            log.w(e) { "Stream loading error: ${e.message}" }
        } finally {
            loadScope.cancel()
        }

        val arrivedGroups = sources.indices.mapNotNull { arrivedByIndex[it] }
        return StreamAutoPlaySelector.orderAddonStreams(
            groups = arrivedGroups,
            installedOrder = targets.installedAddonOrder,
            preferredGroupIds = targets.preferredGroupIds,
        ).flatMap { it.streams }""",
        """        // Fast 0ms seed if StreamsRepository already resolved this exact episode/movie in session
        val tokenPrefix = "$type::$videoId::$season::$episode::"
        val cachedState = StreamsRepository.uiState.value
        if (onProgress != null && cachedState.requestToken?.startsWith(tokenPrefix) == true) {
            val preloaded = cachedState.groups.flatMap { it.streams }
            if (preloaded.isNotEmpty()) {
                onProgress(preloaded)
                if (!cachedState.isAnyLoading) {
                    return preloaded
                }
            }
        }

        val emissions = Channel<SourceEmission>(Channel.UNLIMITED)
        var nextSourceIndex = 0

        val directCloudSources = if (directCloudRoute != null && AppFeaturePolicy.pluginsEnabled) {
            CloudStreamRepository.initialize()
            val pluginItem = CloudStreamRepository.uiState.value.plugins
                .firstOrNull { it.metadata.id.value == directCloudRoute.providerId }
            val directName = pluginItem?.metadata?.name ?: "CloudStream"
            val directAddonId = cloudStreamAddonId(directCloudRoute.providerId)
            val myIndex = nextSourceIndex++
            listOf(
                StreamSource(directName, directAddonId) {
                    val items = loadCloudStreamRouteProgressive(
                        providerId = directCloudRoute.providerId,
                        providerName = directName,
                        linkData = directCloudRoute.data,
                        onProgress = { partialItems ->
                            if (partialItems.isNotEmpty()) {
                                emissions.trySend(
                                    SourceEmission(
                                        index = myIndex,
                                        group = present(
                                            AddonStreamGroup(
                                                addonName = directName,
                                                addonId = directAddonId,
                                                streams = partialItems.sortedForGroupedDisplay(),
                                                isLoading = true,
                                            ),
                                        ),
                                        isFinal = false,
                                    ),
                                )
                            }
                        },
                    ).getOrThrow()
                    AddonStreamGroup(
                        addonName = directName,
                        addonId = directAddonId,
                        streams = items.sortedForGroupedDisplay(),
                        isLoading = false,
                    )
                },
            )
        } else {
            emptyList()
        }
        val addonSources = targets.streamAddons.map { addon ->
            nextSourceIndex++
            StreamSource(addon.addonName, addon.addonId) {
                val group = fetchAddonGroup(addon, type, videoId, forceRefresh = false)
                checkDebridCache(group, targets.streamAddonIds)
            }
        }
        val pluginSources = targets.pluginProviderGroups.map { providerGroup ->
            nextSourceIndex++
            StreamSource(providerGroup.addonName, providerGroup.addonId) {
                loadPluginProviderGroup(providerGroup, type, videoId, season, episode)
            }
        }
        val csSources = cloudStreamGroups
            .filterNot { it.providerId == directCloudRoute?.providerId }
            .map { csGroup ->
                val myIndex = nextSourceIndex++
                StreamSource(csGroup.addonName, csGroup.addonId) {
                    resolveCloudStreamProviderStreams(
                        providerGroup = csGroup,
                        request = cloudStreamSearchRequest,
                        onProgress = { partialItems ->
                            if (partialItems.isNotEmpty()) {
                                emissions.trySend(
                                    SourceEmission(
                                        index = myIndex,
                                        group = present(
                                            AddonStreamGroup(
                                                addonName = csGroup.addonName,
                                                addonId = csGroup.addonId,
                                                streams = partialItems.sortedForGroupedDisplay(),
                                                isLoading = true,
                                            ),
                                        ),
                                        isFinal = false,
                                    ),
                                )
                            }
                        },
                    )
                }
            }
        val serverSources = targets.serverSources.map { source ->
            nextSourceIndex++
            StreamSource(source.addonName, source.addonId) { source.load() }
        }
        val sources = directCloudSources + addonSources + pluginSources + csSources + serverSources
        if (sources.isEmpty()) return emptyList()

        val arrivedByIndex = mutableMapOf<Int, AddonStreamGroup>()
        var lastEmittedCount = 0

        fun buildOrderedStreams(): List<StreamItem> {
            val arrivedGroups = sources.indices.mapNotNull { arrivedByIndex[it] }
            return StreamAutoPlaySelector.orderAddonStreams(
                groups = arrivedGroups,
                installedOrder = targets.installedAddonOrder,
                preferredGroupIds = targets.preferredGroupIds,
            ).flatMap { it.streams }
        }

        val loadScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        try {
            sources.forEachIndexed { index, source ->
                loadScope.launch {
                    val group = try {
                        present(source.load())
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Throwable) {
                        failedGroup(source.addonName, source.addonId, e)
                    }
                    emissions.send(SourceEmission(index = index, group = group, isFinal = true))
                }
            }
            var completedFinals = 0
            withTimeoutOrNull(timeoutMs) {
                while (completedFinals < sources.size) {
                    val emission = emissions.receive()
                    val existing = arrivedByIndex[emission.index]
                    // Never overwrite a non-empty partial group with a timed-out empty group
                    if (emission.group.streams.isNotEmpty() || existing == null) {
                        arrivedByIndex[emission.index] = emission.group
                    }
                    if (emission.isFinal) {
                        completedFinals += 1
                    }
                    if (onProgress != null && emission.group.streams.isNotEmpty()) {
                        val orderedNow = buildOrderedStreams()
                        if (orderedNow.isNotEmpty() && orderedNow.size != lastEmittedCount) {
                            lastEmittedCount = orderedNow.size
                            onProgress(orderedNow)
                        }
                    }
                }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            log.w(e) { "Stream loading error: ${e.message}" }
        } finally {
            loadScope.cancel()
        }

        return buildOrderedStreams()""",
        "StreamSourceLoader progressive live emissions & non-blocking CloudStream",
    )
    changed.append(str(loader_path.relative_to(root)))

    # 2. BatchDownloadCoordinator.kt: higher parallelism, progressive updates, Stop Scan, Next N unwatched, Apply Provider to Season
    coord_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/BatchDownloadCoordinator.kt"
    )
    _replace_once(
        coord_path,
        """data class PlannedEpisodeItem(
    val episode: MetaVideo,
    val status: EpisodePlanStatus,
    val streamCandidate: StreamItem? = null,
    val allAvailableStreams: List<StreamItem> = emptyList(),
    val resolutionLabel: String? = null,
    val sizeBytes: Long? = null,
)""",
        """data class PlannedEpisodeItem(
    val episode: MetaVideo,
    val status: EpisodePlanStatus,
    val streamCandidate: StreamItem? = null,
    val allAvailableStreams: List<StreamItem> = emptyList(),
    val resolutionLabel: String? = null,
    val sizeBytes: Long? = null,
    val isScanningMore: Boolean = false,
    val userOverridden: Boolean = false,
)""",
        "PlannedEpisodeItem progressive fields",
    )

    _replace_once(
        coord_path,
        """    private const val SOURCE_LOAD_PARALLELISM = 2
    private const val SOURCE_LOAD_TIMEOUT_MS = 90_000L""",
        """    private const val SOURCE_LOAD_PARALLELISM = 5
    private const val SOURCE_LOAD_TIMEOUT_MS = 25_000L""",
        "BatchDownloadCoordinator parallelism 5 & 25s timeout",
    )

    _replace_once(
        coord_path,
        """    /** Parent of the open plan's source loading; cancelled when the plan closes. */
    private var planJob: Job? = null""",
        """    /** Parent of the open plan's source loading; cancelled when the plan closes. */
    private var planJob: Job? = null
    private var activeScanJob: Job? = null""",
        "BatchDownloadCoordinator activeScanJob",
    )

    _replace_once(
        coord_path,
        """    fun selectUnwatchedForSeason(
        season: Int,
        isEpisodeWatched: (MetaVideo) -> Boolean,
    ) {
        updateSeasonSelection(season) { episode, isUnavailable ->
            !isUnavailable && !isEpisodeWatched(episode)
        }
    }""",
        """    fun selectUnwatchedForSeason(
        season: Int,
        isEpisodeWatched: (MetaVideo) -> Boolean,
    ) {
        updateSeasonSelection(season) { episode, isUnavailable ->
            !isUnavailable && !isEpisodeWatched(episode)
        }
    }

    fun selectNextUnwatchedForSeason(
        season: Int,
        limit: Int,
        isEpisodeWatched: (MetaVideo) -> Boolean,
    ) {
        if (limit <= 0) return
        DownloadsRepository.ensureLoaded()
        val currentDownloads = DownloadsRepository.uiState.value.items
        _activePlan.update { current ->
            if (current == null) return@update null
            val keys = current.selectedEpisodeKeys.toMutableSet()
            val seasonEpisodes = current.episodesBySeason[season].orEmpty()
            // Clear current season keys first, then pick next N unwatched & available
            for (ep in seasonEpisodes) {
                val epNo = ep.episode ?: continue
                keys -= batchEpisodeKey(season, epNo)
            }
            var picked = 0
            for (ep in seasonEpisodes) {
                if (picked >= limit) break
                val epNo = ep.episode ?: continue
                val unavailable = isBatchEpisodeUnavailable(currentDownloads, current.meta.id, ep, season)
                if (!unavailable && !isEpisodeWatched(ep)) {
                    keys += batchEpisodeKey(season, epNo)
                    picked += 1
                }
            }
            current.copy(selectedEpisodeKeys = keys)
        }
    }

    fun stopActiveScan() {
        activeScanJob?.cancel()
        activeScanJob = null
        _activePlan.update { current ->
            if (current == null) return@update null
            val settledPlans = current.seasonPlans.mapValues { (_, sp) ->
                sp.copy(
                    isPlanning = false,
                    episodes = sp.episodes.map { ep ->
                        when {
                            ep.status == EpisodePlanStatus.Loading && ep.streamCandidate != null ->
                                ep.copy(status = EpisodePlanStatus.Ready, isScanningMore = false)
                            ep.status == EpisodePlanStatus.Loading ->
                                ep.copy(status = EpisodePlanStatus.NoSourceFound, isScanningMore = false)
                            else -> ep.copy(isScanningMore = false)
                        }
                    },
                )
            }
            current.copy(seasonPlans = settledPlans)
        }
    }

    fun applyAddonProviderToSeason(season: Int, preferredAddonName: String) {
        if (preferredAddonName.isBlank()) return
        val preferredResolution = DownloadsSettingsRepository.preferredResolution.value
        val plan = _activePlan.value ?: return
        updateSeasonPlan(plan.meta.id, season) { seasonPlan ->
            seasonPlan?.copy(
                episodes = seasonPlan.episodes.map { item ->
                    val matchingProviderStreams = item.allAvailableStreams.filter {
                        it.addonName.equals(preferredAddonName, ignoreCase = true)
                    }
                    if (matchingProviderStreams.isEmpty()) {
                        item
                    } else {
                        val picked = StreamSourcePrefillSelector.selectForBatch(
                            matchingProviderStreams,
                            preferredResolution,
                        )
                        if (picked != null) {
                            item.withSelectedStream(picked.stream, picked.facts, picked.sizeBytes)
                                .copy(userOverridden = true)
                        } else {
                            item
                        }
                    }
                },
            )
        }
    }""",
        "BatchDownloadCoordinator Next N, stopActiveScan & applyAddonProviderToSeason",
    )

    _replace_once(
        coord_path,
        """    private fun launchSourceLoading(
        plan: BatchDownloadPlan,
        parentJob: Job,
        season: Int,
        episodesToLoad: List<MetaVideo>,
    ) {
        scope.launch(parentJob) {
            val preferredResolution = DownloadsSettingsRepository.preferredResolution.value
            episodesToLoad.map { episode ->
                launch(Dispatchers.Default) {
                    sourceLoadPermits.withPermit {
                        try {
                            val target = plan.meta.batchTargetFor(episode, season)
                            val streams = runCatchingUnlessCancelled {
                                StreamSourceLoader.loadStreams(
                                    type = plan.meta.type,
                                    videoId = target.streamVideoId,
                                    season = target.season,
                                    episode = target.episode,
                                    embeddedStreams = plan.meta.findEmbeddedStreams(target.streamVideoId),
                                    timeoutMs = SOURCE_LOAD_TIMEOUT_MS,
                                    meta = plan.meta,
                                )
                            }.getOrElse { emptyList() }
                            val currentPlan = _activePlan.value
                            val activeFilter = currentPlan?.sourceFilter ?: BatchSourceFilter.All
                            val activeQuery = currentPlan?.searchQuery.orEmpty()
                            val filteredStreams = streams.filter {
                                it.matchesBatchSourceFilter(activeFilter) && it.matchesBatchSearchQuery(activeQuery)
                            }
                            val selection = StreamSourcePrefillSelector.selectForBatch(filteredStreams, preferredResolution)

                            updateEpisode(plan.meta.id, season, episode) { item ->
                                if (item.status == EpisodePlanStatus.AlreadyDownloaded) item
                                else if (selection == null) {
                                    item.copy(
                                        streamCandidate = null,
                                        resolutionLabel = null,
                                        sizeBytes = null,
                                        allAvailableStreams = streams,
                                        status = EpisodePlanStatus.NoSourceFound,
                                    )
                                } else {
                                    item.withSelectedStream(selection.stream, selection.facts, selection.sizeBytes)
                                        .copy(allAvailableStreams = streams)
                                }
                            }
                        } finally {
                            updateEpisode(plan.meta.id, season, episode) { item ->
                                if (item.status == EpisodePlanStatus.Loading) item.copy(status = EpisodePlanStatus.NoSourceFound) else item
                            }
                        }
                    }
                }
            }.joinAll()
            updateSeasonPlan(plan.meta.id, season) { it?.copy(isPlanning = false) }
            // Re-run to include episodes selected while the source requests were in flight.
            loadSourcesForSeason(season)
        }
    }""",
        """    private fun applyStreamListToEpisode(
        metaId: String,
        season: Int,
        episode: MetaVideo,
        streams: List<StreamItem>,
        preferredResolution: DownloadPreferredResolution,
        isFinal: Boolean,
    ) {
        val currentPlan = _activePlan.value
        val activeFilter = currentPlan?.sourceFilter ?: BatchSourceFilter.All
        val activeQuery = currentPlan?.searchQuery.orEmpty()
        val filteredStreams = streams.filter {
            it.matchesBatchSourceFilter(activeFilter) && it.matchesBatchSearchQuery(activeQuery)
        }
        val selection = StreamSourcePrefillSelector.selectForBatch(filteredStreams, preferredResolution)

        updateEpisode(metaId, season, episode) { item ->
            when {
                item.status == EpisodePlanStatus.AlreadyDownloaded ||
                    item.status == EpisodePlanStatus.AlreadyInProgress -> item
                item.userOverridden && item.streamCandidate != null -> {
                    item.copy(
                        allAvailableStreams = streams,
                        isScanningMore = !isFinal,
                        status = EpisodePlanStatus.Ready,
                    )
                }
                selection != null -> {
                    item.withSelectedStream(selection.stream, selection.facts, selection.sizeBytes)
                        .copy(
                            allAvailableStreams = streams,
                            isScanningMore = !isFinal,
                        )
                }
                !isFinal -> {
                    item.copy(
                        allAvailableStreams = streams,
                        isScanningMore = true,
                    )
                }
                else -> {
                    item.copy(
                        streamCandidate = null,
                        resolutionLabel = null,
                        sizeBytes = null,
                        allAvailableStreams = streams,
                        isScanningMore = false,
                        status = EpisodePlanStatus.NoSourceFound,
                    )
                }
            }
        }
    }

    private fun launchSourceLoading(
        plan: BatchDownloadPlan,
        parentJob: Job,
        season: Int,
        episodesToLoad: List<MetaVideo>,
    ) {
        activeScanJob?.cancel()
        activeScanJob = scope.launch(parentJob) {
            val preferredResolution = DownloadsSettingsRepository.preferredResolution.value
            episodesToLoad.map { episode ->
                launch(Dispatchers.Default) {
                    sourceLoadPermits.withPermit {
                        try {
                            val target = plan.meta.batchTargetFor(episode, season)
                            val finalStreams = runCatchingUnlessCancelled {
                                StreamSourceLoader.loadStreams(
                                    type = plan.meta.type,
                                    videoId = target.streamVideoId,
                                    season = target.season,
                                    episode = target.episode,
                                    embeddedStreams = plan.meta.findEmbeddedStreams(target.streamVideoId),
                                    timeoutMs = SOURCE_LOAD_TIMEOUT_MS,
                                    meta = plan.meta,
                                    onProgress = { partialStreams ->
                                        if (partialStreams.isNotEmpty()) {
                                            applyStreamListToEpisode(
                                                metaId = plan.meta.id,
                                                season = season,
                                                episode = episode,
                                                streams = partialStreams,
                                                preferredResolution = preferredResolution,
                                                isFinal = false,
                                            )
                                        }
                                    },
                                )
                            }.getOrElse { emptyList() }
                            applyStreamListToEpisode(
                                metaId = plan.meta.id,
                                season = season,
                                episode = episode,
                                streams = finalStreams,
                                preferredResolution = preferredResolution,
                                isFinal = true,
                            )
                        } finally {
                            updateEpisode(plan.meta.id, season, episode) { item ->
                                if (item.status == EpisodePlanStatus.Loading) {
                                    item.copy(status = EpisodePlanStatus.NoSourceFound, isScanningMore = false)
                                } else {
                                    item.copy(isScanningMore = false)
                                }
                            }
                        }
                    }
                }
            }.joinAll()
            updateSeasonPlan(plan.meta.id, season) { it?.copy(isPlanning = false) }
            // Re-run to include episodes selected while the source requests were in flight.
            loadSourcesForSeason(season)
        }
    }""",
        "BatchDownloadCoordinator progressive launchSourceLoading",
    )

    _replace_once(
        coord_path,
        """                    episodes = seasonPlan.episodes.map { item ->
                        if (item.status == EpisodePlanStatus.AlreadyDownloaded ||
                            item.status == EpisodePlanStatus.AlreadyInProgress ||
                            item.status == EpisodePlanStatus.Loading
                        ) {
                            item
                        } else {""",
        """                    episodes = seasonPlan.episodes.map { item ->
                        if (item.status == EpisodePlanStatus.AlreadyDownloaded ||
                            item.status == EpisodePlanStatus.AlreadyInProgress ||
                            (item.status == EpisodePlanStatus.Loading && item.allAvailableStreams.isEmpty())
                        ) {
                            item
                        } else {""",
        "BatchDownloadCoordinator applyFilterAndQuery live streams support",
    )

    _replace_once(
        coord_path,
        """    fun overrideEpisodeStream(season: Int, episode: MetaVideo, stream: StreamItem) {
        val plan = _activePlan.value ?: return
        val facts = DebridStreamMetadata.facts(stream, DebridStreamPreferences())
        updateEpisode(plan.meta.id, season, episode) {
            it.withSelectedStream(stream, facts, StreamSourcePrefillSelector.sizeBytes(stream))
        }
    }""",
        """    fun overrideEpisodeStream(season: Int, episode: MetaVideo, stream: StreamItem) {
        val plan = _activePlan.value ?: return
        val facts = DebridStreamMetadata.facts(stream, DebridStreamPreferences())
        updateEpisode(plan.meta.id, season, episode) {
            it.withSelectedStream(stream, facts, StreamSourcePrefillSelector.sizeBytes(stream))
                .copy(userOverridden = true)
        }
    }""",
        "BatchDownloadCoordinator overrideEpisodeStream userOverridden flag",
    )

    _replace_once(
        coord_path,
        """    fun closePlan() {
        planJob?.cancel()
        planJob = null
        _activePlan.value = null
    }""",
        """    fun closePlan() {
        activeScanJob?.cancel()
        activeScanJob = null
        planJob?.cancel()
        planJob = null
        _activePlan.value = null
    }""",
        "BatchDownloadCoordinator closePlan cancel activeScanJob",
    )
    changed.append(str(coord_path.relative_to(root)))

    # 3. BatchDownloadDialog.kt: unlock Queue immediately, Stop Scan, Next 3/5/10, Total Size, Apply Provider to Season
    dialog_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/BatchDownloadDialog.kt"
    )
    _replace_once(
        dialog_path,
        """            onSelect = { stream ->
                BatchDownloadCoordinator.overrideEpisodeStream(
                    season = currentSeason,
                    episode = overrideItem.episode,
                    stream = stream,
                )
                overrideTargetItem = null
            },""",
        """            showSyncSeasonAction = !plan.isSingleTitle &&
                (plan.seasonPlans[currentSeason]?.episodes?.size ?: 0) > 1,
            onSelectAndApplySeason = { stream ->
                BatchDownloadCoordinator.overrideEpisodeStream(
                    season = currentSeason,
                    episode = overrideItem.episode,
                    stream = stream,
                )
                BatchDownloadCoordinator.applyAddonProviderToSeason(
                    season = currentSeason,
                    preferredAddonName = stream.addonName,
                )
                overrideTargetItem = null
            },
            onSelect = { stream ->
                BatchDownloadCoordinator.overrideEpisodeStream(
                    season = currentSeason,
                    episode = overrideItem.episode,
                    stream = stream,
                )
                overrideTargetItem = null
            },""",
        "BatchDownloadDialog StreamOverrideDialog sync season callback",
    )

    _replace_once(
        dialog_path,
        """                    SelectionTextButton(Res.string.downloads_select_unwatched) {
                        BatchDownloadCoordinator.selectUnwatchedForSeason(
                            season = plan.visibleSeason,
                            isEpisodeWatched = isEpisodeWatched,
                        )
                    }
                    SelectionTextButton(Res.string.downloads_select_all) {
                        BatchDownloadCoordinator.selectAllForSeason(plan.visibleSeason)
                    }
                    SelectionTextButton(Res.string.downloads_deselect_all) {
                        BatchDownloadCoordinator.deselectAllForSeason(plan.visibleSeason)
                    }""",
        """                    SelectionTextButton(Res.string.downloads_select_unwatched) {
                        BatchDownloadCoordinator.selectUnwatchedForSeason(
                            season = plan.visibleSeason,
                            isEpisodeWatched = isEpisodeWatched,
                        )
                    }
                    listOf(3, 5, 10).forEach { packCount ->
                        if (currentSeasonEpisodes.size > packCount) {
                            TextButton(
                                onClick = {
                                    BatchDownloadCoordinator.selectNextUnwatchedForSeason(
                                        season = plan.visibleSeason,
                                        limit = packCount,
                                        isEpisodeWatched = isEpisodeWatched,
                                    )
                                },
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                            ) {
                                Text(
                                    text = "Next $packCount",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = tokens.colors.accent,
                                )
                            }
                        }
                    }
                    SelectionTextButton(Res.string.downloads_select_all) {
                        BatchDownloadCoordinator.selectAllForSeason(plan.visibleSeason)
                    }
                    SelectionTextButton(Res.string.downloads_deselect_all) {
                        BatchDownloadCoordinator.deselectAllForSeason(plan.visibleSeason)
                    }""",
        "EpisodeSelectionDialog Next 3 / 5 / 10 commuter pack buttons",
    )

    _replace_once(
        dialog_path,
        """            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                if (currentSeasonLabel.isNotBlank()) {
                    Text(
                        text = currentSeasonLabel,
                        style = MaterialTheme.typography.titleMedium,
                        color = tokens.colors.textPrimary,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
                if (isPlanning) {
                    FindingSourceIndicator(compact = false)
                }
            }""",
        """            val readyInSeason = remember(episodes) {
                episodes.count { it.status == EpisodePlanStatus.Ready && it.streamCandidate != null }
            }
            val totalKnownBytes = remember(episodes) {
                episodes.mapNotNull { ep ->
                    ep.sizeBytes?.takeIf { ep.status == EpisodePlanStatus.Ready && it > 0L }
                }.sum()
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    if (currentSeasonLabel.isNotBlank()) {
                        Text(
                            text = currentSeasonLabel,
                            style = MaterialTheme.typography.titleMedium,
                            color = tokens.colors.textPrimary,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                    if (episodes.isNotEmpty()) {
                        val sizePart = if (totalKnownBytes > 0L) " · ~${formatBytes(totalKnownBytes)}" else ""
                        Text(
                            text = "$readyInSeason/${episodes.size} ready$sizePart",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (readyInSeason > 0) tokens.colors.accent else tokens.colors.textMuted,
                        )
                    }
                }
                if (isPlanning) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        FindingSourceIndicator(compact = true)
                        Surface(
                            shape = RoundedCornerShape(NuvioTokens.Radius.full),
                            color = tokens.colors.surfaceCard,
                            border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                            modifier = Modifier.clickable { BatchDownloadCoordinator.stopActiveScan() },
                        ) {
                            Text(
                                text = "Stop scan",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = tokens.colors.textSecondary,
                                modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
                            )
                        }
                    }
                }
            }""",
        "SourceSelectionDialog live ready + size summary + Stop scan pill",
    )

    _replace_once(
        dialog_path,
        """            if (!isLastSeason && !plan.isSingleTitle) {
                DialogButton(
                    text = stringResource(Res.string.downloads_next_season),
                    onClick = { BatchDownloadCoordinator.goToSeasonIndex(seasonIndex + 1) },
                    style = DialogButtonStyle.Primary,
                    enabled = !isPlanning,
                    loading = isPlanning,
                )
            } else {
                DialogButton(
                    text = stringResource(Res.string.downloads_action_queue),
                    onClick = onConfirm,
                    style = DialogButtonStyle.Primary,
                    enabled = !isPlanning && plan.seasonPlans.values.any { it.readyToDownloadCount > 0 },
                    loading = isPlanning,
                )
            }""",
        """            val totalReadyAcrossPlan = plan.seasonPlans.values.sumOf { it.readyToDownloadCount }
            if (!isLastSeason && !plan.isSingleTitle) {
                DialogButton(
                    text = stringResource(Res.string.downloads_next_season),
                    onClick = { BatchDownloadCoordinator.goToSeasonIndex(seasonIndex + 1) },
                    style = DialogButtonStyle.Primary,
                    enabled = !isPlanning || (currentSeasonPlan?.readyToDownloadCount ?: 0) > 0,
                    loading = isPlanning && (currentSeasonPlan?.readyToDownloadCount ?: 0) == 0,
                )
            } else {
                DialogButton(
                    text = if (totalReadyAcrossPlan > 0 && !plan.isSingleTitle) {
                        "${stringResource(Res.string.downloads_action_queue)} ($totalReadyAcrossPlan)"
                    } else {
                        stringResource(Res.string.downloads_action_queue)
                    },
                    onClick = onConfirm,
                    style = DialogButtonStyle.Primary,
                    enabled = totalReadyAcrossPlan > 0,
                    loading = isPlanning && totalReadyAcrossPlan == 0,
                )
            }""",
        "SourceSelectionDialog unlock Queue button immediately on first ready source",
    )

    _replace_once(
        dialog_path,
        """                        val metaSummary = streamSourceSummary(badge, provider, size)
                        if (metaSummary.isNotBlank()) {
                            Text(
                                text = metaSummary,
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = tokens.colors.accent,
                            )
                        }
                    }""",
        """                        val metaSummary = streamSourceSummary(badge, provider, size)
                        if (metaSummary.isNotBlank()) {
                            Text(
                                text = metaSummary,
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = tokens.colors.accent,
                            )
                        }
                        if (item.allAvailableStreams.size > 1) {
                            Text(
                                text = if (item.isScanningMore) {
                                    "· ${item.allAvailableStreams.size} sources (scanning…)"
                                } else {
                                    "· ${item.allAvailableStreams.size} sources"
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = tokens.colors.textMuted,
                            )
                        }
                    }""",
        "EpisodeSourcePlanRow live alt source counter",
    )

    _replace_once(
        dialog_path,
        """private fun StreamOverrideDialog(
    target: PlannedEpisodeItem,
    initialFilter: BatchSourceFilter,
    initialQuery: String = "",
    onSelect: (StreamItem) -> Unit,
    onDismiss: () -> Unit,
) {""",
        """private fun StreamOverrideDialog(
    target: PlannedEpisodeItem,
    initialFilter: BatchSourceFilter,
    initialQuery: String = "",
    showSyncSeasonAction: Boolean = false,
    onSelectAndApplySeason: ((StreamItem) -> Unit)? = null,
    onSelect: (StreamItem) -> Unit,
    onDismiss: () -> Unit,
) {""",
        "StreamOverrideDialog sync season params",
    )

    _replace_once(
        dialog_path,
        """        DialogButtons {
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismiss,
                style = DialogButtonStyle.Secondary,
            )
        }""",
        """        DialogButtons {
            if (showSyncSeasonAction && onSelectAndApplySeason != null && target.streamCandidate != null) {
                val activeCandidate = target.streamCandidate
                DialogButton(
                    text = "Use ${activeCandidate.addonName.ifBlank { "provider" }} for season",
                    onClick = { onSelectAndApplySeason(activeCandidate) },
                    style = DialogButtonStyle.Secondary,
                )
            }
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismiss,
                style = DialogButtonStyle.Secondary,
            )
        }""",
        "StreamOverrideDialog Use provider for season button",
    )
    changed.append(str(dialog_path.relative_to(root)))


def _patch_subscribed_release_radar(root: Path, changed: list[str]) -> None:
    radar_path = (
        root
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/home/HomePremiumModels.kt"
    )
    if not radar_path.is_file():
        return
    _replace_once(
        radar_path,
        """        val libraryItemsByRadarKey = libraryItems.associateBy(::libraryItemKeyForHomeRadar)
        resolvedLibraryDetails.forEach { (radarKey, details) ->
            val libraryItem = libraryItemsByRadarKey[radarKey] ?: return@forEach
            details.videos
                .asSequence()
                .mapNotNull { video ->
                    val releaseIso = video.released.releaseIsoDateOrNull() ?: return@mapNotNull null
                    val days = daysBetweenIsoDates(todayIsoDate, releaseIso) ?: return@mapNotNull null
                    if (days !in earliestReleaseDay..HomeReleaseRadarUpcomingWindowDays) {
                        return@mapNotNull null
                    }
                    details.toReleaseRadarItem(
                        video = video,
                        libraryItem = libraryItem,
                        releaseIsoDate = releaseIso,
                        daysFromToday = days,
                    )
                }
                .forEach(::add)
        }""",
        """        val libraryItemsByRadarKey = libraryItems.associateBy(::libraryItemKeyForHomeRadar)
        resolvedLibraryDetails.forEach { (radarKey, details) ->
            val libraryItem = libraryItemsByRadarKey[radarKey] ?: return@forEach
            val isSubscribed = "local:subscribed" in libraryItem.listKeys
            val itemEarliestDay = if (isSubscribed) minOf(earliestReleaseDay, -7) else earliestReleaseDay
            details.videos
                .asSequence()
                .mapNotNull { video ->
                    val releaseIso = video.released.releaseIsoDateOrNull() ?: return@mapNotNull null
                    val days = daysBetweenIsoDates(todayIsoDate, releaseIso) ?: return@mapNotNull null
                    if (days !in itemEarliestDay..HomeReleaseRadarUpcomingWindowDays) {
                        return@mapNotNull null
                    }
                    val base = details.toReleaseRadarItem(
                        video = video,
                        libraryItem = libraryItem,
                        releaseIsoDate = releaseIso,
                        daysFromToday = days,
                    )
                    if (isSubscribed) {
                        base.copy(
                            subtitle = listOfNotNull("🔔 Subscribed", base.subtitle?.takeIf { it.isNotBlank() })
                                .joinToString(" · "),
                        )
                    } else {
                        base
                    }
                }
                .forEach(::add)
        }""",
        "HomePremiumModels subscribed episode radar window & badge",
    )
    _replace_once(
        radar_path,
        """    return releaseItems
        .distinctBy { item -> item.key }
        .sortedWith(
            compareBy<HomeReleaseRadarItem> { item -> item.daysFromToday?.releaseRadarSortWeight() ?: Int.MAX_VALUE }
                .thenByDescending { item -> item.releaseRadarSignalWeight() }
                .thenBy { item -> item.title.lowercase() }
        )
        .take(HomeReleaseRadarItemLimit)""",
        """    val subscribedIds = libraryItems
        .filter { "local:subscribed" in it.listKeys }
        .mapTo(hashSetOf()) { it.id }
    return releaseItems
        .distinctBy { item -> item.key }
        .sortedWith(
            compareByDescending<HomeReleaseRadarItem> { item -> item.preview.id in subscribedIds }
                .thenBy { item -> item.daysFromToday?.releaseRadarSortWeight() ?: Int.MAX_VALUE }
                .thenByDescending { item -> item.releaseRadarSignalWeight() }
                .thenBy { item -> item.title.lowercase() }
        )
        .take(HomeReleaseRadarItemLimit)""",
        "HomePremiumModels subscribed priority sorting",
    )
    changed.append(str(radar_path.relative_to(root)))


def apply_v118_ux_overhaul_patch(root: Path) -> list[str]:
    changed: list[str] = []
    _patch_version_118(root, changed)
    _patch_library_categories_and_dedup(root, changed)
    _patch_library_screen_tabs_and_search(root, changed)
    _patch_subscribed_release_radar(root, changed)
    _patch_details_and_poster_picker(root, changed)
    _patch_cloudstream_filter_and_sort(root, changed)
    _patch_fast_batch_downloads(root, changed)
    return changed
