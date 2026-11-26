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

    val existingExact = remember(targetItem, visible) {
        targetItem?.let { candidate -> LibraryRepository.findSavedItem(candidate.id, candidate.type) }
    }
    val otherDuplicates = remember(targetItem, visible) {
        targetItem?.let(LibraryRepository::findOtherDuplicateCandidates).orEmpty()
    }
    val existingDuplicates = remember(existingExact, otherDuplicates) {
        buildList {
            if (existingExact != null) add(existingExact)
            addAll(otherDuplicates)
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
                    if (
                        onSaveWithResolution != null &&
                        hasAnyLocalSelected &&
                        existingExact == null &&
                        otherDuplicates.isNotEmpty()
                    ) {
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
        existingItems = otherDuplicates,
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
