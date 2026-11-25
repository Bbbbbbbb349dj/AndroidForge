#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 3: CloudStream Sort/Filter Sheet (Section 6).

The provider search card used to push four full chip rows (status, sort, language,
type) inline, crowding the page. They now open from a trailing Tune icon + active
filter count badge on the search field, inside a `NuvioModalBottomSheet`.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 cloudstream] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 cloudstream] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_cloudstream_filter_sheet(root: Path) -> None:
    path = root / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/plugins/CloudStreamSettingsSection.kt"

    _replace_once(
        path,
        """import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Button""",
        """import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button""",
        "Badge imports",
    )
    _replace_once(
        path,
        """import com.nuvio.app.core.ui.NuvioInputField
import com.nuvio.app.core.ui.NuvioPrimaryButton""",
        """import com.nuvio.app.core.ui.NuvioInputField
import com.nuvio.app.core.ui.NuvioModalBottomSheet
import com.nuvio.app.core.ui.NuvioPrimaryButton""",
        "NuvioModalBottomSheet import",
    )

    _replace_once(
        path,
        """    val selectedSortOrder = remember(sortOrderKey) {
        CloudStreamSortOrder.entries.firstOrNull { it.key == sortOrderKey } ?: CloudStreamSortOrder.SMART
    }""",
        """    val selectedSortOrder = remember(sortOrderKey) {
        CloudStreamSortOrder.entries.firstOrNull { it.key == sortOrderKey } ?: CloudStreamSortOrder.SMART
    }
    var showFilterSheet by remember { mutableStateOf(false) }
    val activeFilterCount =
        (if (selectedStatusFilter != CloudStreamStatusFilter.ALL) 1 else 0) +
            (if (selectedSortOrder != CloudStreamSortOrder.SMART) 1 else 0) +
            (if (selectedLanguage != null) 1 else 0) +
            (if (selectedType != null) 1 else 0)""",
        "filter sheet state + badge count",
    )

    _replace_once(
        path,
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
                CloudStreamFilterChip(copy.allLanguages, selectedLanguage == null) { selectedLanguage = null }
                languages.forEach { language ->
                    CloudStreamFilterChip(language.uppercase(), selectedLanguage == language) {
                        selectedLanguage = language.takeUnless { selectedLanguage == language }
                    }
                }
            }
            if (types.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    CloudStreamFilterChip(copy.allTypes, selectedType == null) { selectedType = null }
                    types.forEach { type ->
                        CloudStreamFilterChip(type, selectedType == type) {
                            selectedType = type.takeUnless { selectedType == type }
                        }
                    }
                }
            }""",
        """            NuvioInputField(
                value = query,
                onValueChange = { query = it },
                placeholder = copy.searchPlaceholder,
                trailingContent = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { showFilterSheet = true }) {
                            if (activeFilterCount > 0) {
                                BadgedBox(
                                    badge = { Badge { Text(text = activeFilterCount.toString()) } },
                                ) {
                                    Icon(Icons.Rounded.Tune, contentDescription = "Sort and filter extensions")
                                }
                            } else {
                                Icon(Icons.Rounded.Tune, contentDescription = "Sort and filter extensions")
                            }
                        }
                        if (query.isNotEmpty()) {
                            IconButton(onClick = { query = "" }) {
                                Icon(Icons.Rounded.Close, contentDescription = "Clear search")
                            }
                        }
                    }
                },
            )
            if (showFilterSheet) {
                NuvioModalBottomSheet(onDismissRequest = { showFilterSheet = false }) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 20.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        Text(
                            text = "Extension Status",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
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
                        Text(
                            text = "Sort Extensions",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
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
                        Text(
                            text = "Languages & Types",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        FlowRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            CloudStreamFilterChip(copy.allLanguages, selectedLanguage == null) { selectedLanguage = null }
                            languages.forEach { language ->
                                CloudStreamFilterChip(language.uppercase(), selectedLanguage == language) {
                                    selectedLanguage = language.takeUnless { selectedLanguage == language }
                                }
                            }
                        }
                        if (types.isNotEmpty()) {
                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                CloudStreamFilterChip(copy.allTypes, selectedType == null) { selectedType = null }
                                types.forEach { type ->
                                    CloudStreamFilterChip(type, selectedType == type) {
                                        selectedType = type.takeUnless { selectedType == type }
                                    }
                                }
                            }
                        }
                    }
                }
            }""",
        "move chip rows into filter sheet",
    )


def apply_v120_cloudstream_filter_patch(source_dir: Path) -> None:
    _patch_cloudstream_filter_sheet(source_dir)
    print("[v1.20-module-3] CloudStream sort/filter bottom sheet applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_cloudstream_filter_patch.py <source_dir>")
    apply_v120_cloudstream_filter_patch(Path(sys.argv[1]).resolve())
