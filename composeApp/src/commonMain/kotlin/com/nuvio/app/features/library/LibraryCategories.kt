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

/**
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

private val RELEASE_YEAR_REGEX = Regex("""\b(19\d{2}|20\d{2})\b""")

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
