package com.nuvio.app.features.plugins

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil3.compose.AsyncImage
import com.nuvio.app.core.ui.PlatformBackHandler
import com.nuvio.app.core.ui.NuvioToastController
import com.nuvio.app.features.cloudstream.*
import com.nuvio.app.features.settings.AppLanguage
import com.nuvio.app.features.streams.StreamSourcePreferencesRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/** Repository-first browser; the app's existing Settings header and bottom navigation remain. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun CloudStreamSettingsSection(modifier: Modifier = Modifier) {
    LaunchedEffect(Unit) { CloudStreamRepository.initialize() }
    val state by CloudStreamRepository.uiState.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    var repositoryUrl by rememberSaveable { mutableStateOf<String?>(null) }
    var repositoryQuery by rememberSaveable { mutableStateOf("") }
    var extensionQuery by rememberSaveable(repositoryUrl) { mutableStateOf("") }
    var type by rememberSaveable(repositoryUrl) { mutableStateOf<String?>(null) }
    var language by rememberSaveable(repositoryUrl) { mutableStateOf<String?>(null) }
    var status by rememberSaveable(repositoryUrl) { mutableStateOf("all") }
    var showLanguages by remember { mutableStateOf(false) }
    var showAdd by remember { mutableStateOf(false) }
    var addUrl by rememberSaveable { mutableStateOf("") }
    var adding by remember { mutableStateOf(false) }
    var addError by remember { mutableStateOf<String?>(null) }
    var removeUrl by remember { mutableStateOf<String?>(null) }
    var showMenu by remember { mutableStateOf(false) }
    var advanced by rememberSaveable { mutableStateOf(false) }
    var selectedPluginId by rememberSaveable { mutableStateOf<String?>(null) }
    var configuringPluginId by rememberSaveable { mutableStateOf<String?>(null) }
    val selectedRepository = state.repositories.firstOrNull { it.manifest.sourceUrl == repositoryUrl }
    LaunchedEffect(state.repositories, repositoryUrl) {
        if (repositoryUrl != null && selectedRepository == null) repositoryUrl = null
    }
    val back: () -> Unit = { if (advanced) advanced = false else repositoryUrl = null }
    PlatformBackHandler(enabled = advanced || repositoryUrl != null, onBack = back)
    val scopedPlugins = remember(state.plugins, repositoryUrl) {
        state.plugins.filter { repositoryUrl == null || it.metadata.repositoryManifestUrl == repositoryUrl }
    }
    val disabledRepos = remember(state.repositories) {
        state.repositories.filterNot { it.enabled }.map { it.manifest.sourceUrl }.toSet()
    }
    val summary = remember(scopedPlugins, disabledRepos) { cloudStreamExtensionSummary(scopedPlugins, disabledRepos) }
    val plugins = remember(scopedPlugins, extensionQuery, type, language, status, disabledRepos) {
        val query = extensionQuery.trim()
        scopedPlugins.filter {
            (query.isBlank() || it.metadata.name.contains(query, true) || it.metadata.description.orEmpty().contains(query, true)) &&
                cloudStreamMatchesBrowserType(it.metadata.rawTvTypes, type) &&
                (language == null || it.metadata.language == language) && when (status) {
                    "downloaded" -> it.isInstalled && it.enabled && it.metadata.repositoryManifestUrl !in disabledRepos
                    "disabled" -> it.isInstalled && (!it.enabled || it.metadata.repositoryManifestUrl in disabledRepos)
                    "available" -> !it.isInstalled
                    else -> true
                }
        }.sortedBy { it.metadata.name.lowercase() }
    }
    val repositories = remember(state.repositories, repositoryQuery) {
        state.repositories.filter { it.manifest.name.contains(repositoryQuery.trim(), true) ||
            it.manifest.description.orEmpty().contains(repositoryQuery.trim(), true) }
    }
    val listState = rememberLazyListState()
    LaunchedEffect(repositoryUrl, advanced, type, language, status) { listState.scrollToItem(0) }

    // Settings' scrolling content does not establish a Material Surface content color.
    // Bind text/icons to the same scheme as this browser's dark/light background.
    CompositionLocalProvider(LocalContentColor provides MaterialTheme.colorScheme.onSurface) {
    Column(modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            if (repositoryUrl != null || advanced) IconButton(onClick = back) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, "Back to repositories")
            }
            Text(if (advanced) "Advanced management" else selectedRepository?.manifest?.name ?: "Extensions",
                style = MaterialTheme.typography.titleLarge, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f))
            if (!advanced) {
                if (selectedRepository != null) IconButton(onClick = { showLanguages = true }) {
                    Icon(Icons.Rounded.Translate, "Filter extension language")
                }
                Box {
                    IconButton(onClick = { showMenu = true }) { Icon(Icons.Rounded.MoreVert, "Extension options") }
                    DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                        DropdownMenuItem(text = { Text("Refresh repositories") }, onClick = {
                            showMenu = false
                            repositoryUrl?.let(CloudStreamRepository::refreshRepository) ?: CloudStreamRepository.refreshAll()
                        })
                        if (selectedRepository != null) DropdownMenuItem(text = {
                            Text(if (selectedRepository.enabled) "Disable repository" else "Enable repository")
                        }, onClick = {
                            CloudStreamRepository.setRepositoryEnabled(selectedRepository.manifest.sourceUrl, !selectedRepository.enabled)
                            showMenu = false
                        })
                        DropdownMenuItem(text = { Text("Advanced management & settings") }, onClick = { showMenu = false; advanced = true })
                    }
                }
            }
        }
        if (advanced) {
            LazyColumn(Modifier.weight(1f)) { item { Column { CloudStreamAdvancedSettingsSection() } } }
        } else {
            OutlinedTextField(
                value = if (repositoryUrl == null) repositoryQuery else extensionQuery,
                onValueChange = { if (repositoryUrl == null) repositoryQuery = it else extensionQuery = it },
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                placeholder = { Text("Search…") }, leadingIcon = { Icon(Icons.Rounded.Search, null) },
                shape = RoundedCornerShape(32.dp), singleLine = true,
            )
            if (repositoryUrl != null) {
                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    cloudStreamBrowserTypes.forEach { label ->
                        FilterChip(selected = type == label, onClick = { type = if (type == label) null else label }, label = { Text(label) })
                    }
                }
                if (language != null || status != "all") TextButton(onClick = { language = null; status = "all" }) {
                    Text("Clear filters · ${language?.let(::cloudStreamBrowserLanguage) ?: status}")
                }
                if (selectedRepository?.enabled == false) Text("This repository is disabled. Enable it from the options menu to use its providers.",
                    color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
            Box(Modifier.weight(1f).fillMaxWidth()) {
                LazyColumn(state = listState, modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = if (repositoryUrl == null) 88.dp else 16.dp)) {
                    if (!state.securityWarningAccepted) item {
                        ElevatedCard(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                            Column(Modifier.padding(16.dp)) {
                                Text("Third-party extensions", fontWeight = FontWeight.Bold)
                                Text("Extensions run third-party code and contact external services. Install only repositories you trust.")
                                TextButton(onClick = CloudStreamRepository::acceptSecurityWarning) { Text("I understand") }
                            }
                        }
                    }
                    if (repositoryUrl == null) {
                        items(repositories, key = { it.manifest.sourceUrl }) { repository ->
                            val entries = state.plugins.filter { it.metadata.repositoryManifestUrl == repository.manifest.sourceUrl }
                            Row(Modifier.fillMaxWidth().clickable { repositoryUrl = repository.manifest.sourceUrl }.padding(vertical = 20.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                BrowserIcon(repository.manifest.iconUrl, repository.manifest.name)
                                Column(Modifier.weight(1f).padding(horizontal = 16.dp)) {
                                    Text(repository.manifest.name, style = MaterialTheme.typography.titleMedium,
                                        color = MaterialTheme.colorScheme.onSurface)
                                    Text("Downloaded: ${entries.count { it.isInstalled }}/${entries.size}" + if (!repository.enabled) " · Disabled" else "",
                                        style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    repository.manifest.description?.let { Text(it, Modifier.padding(top = 8.dp), style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis) }
                                    repository.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                                }
                                if (repository.isRefreshing) CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                                else IconButton(onClick = { removeUrl = repository.manifest.sourceUrl }) { Icon(Icons.Rounded.DeleteOutline, "Remove ${repository.manifest.name}") }
                            }
                        }
                        if (repositories.isEmpty()) item { BrowserEmpty(if (state.repositories.isEmpty()) "Add a repository to browse its extensions." else "No matching repositories.") }
                    } else {
                        items(plugins, key = { it.metadata.id.value }) { plugin ->
                            Row(Modifier.fillMaxWidth().clickable { selectedPluginId = plugin.metadata.id.value }.padding(vertical = 18.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                BrowserIcon(plugin.metadata.iconUrl, plugin.metadata.name)
                                Column(Modifier.weight(1f).padding(horizontal = 16.dp)) {
                                    Text(plugin.metadata.name, style = MaterialTheme.typography.titleMedium,
                                        color = MaterialTheme.colorScheme.onSurface)
                                    val size = plugin.metadata.fileSize?.let { "  ${it / 1024} kB" }.orEmpty()
                                    Text("${cloudStreamBrowserLanguage(plugin.metadata.language)}  v${plugin.installedVersion ?: plugin.metadata.version}$size",
                                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    plugin.metadata.description?.let { Text(it, style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis) }
                                    if (plugin.isInstalled && !plugin.enabled) Text("Disabled", color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.labelSmall)
                                    plugin.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
                                }
                                if (plugin.isInstalling) CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                                else IconButton(enabled = plugin.isInstalled || (state.securityWarningAccepted && plugin.metadata.status.canInstall && plugin.compatibility.isRunnable), onClick = {
                                    if (plugin.isInstalled && !plugin.hasUpdate) selectedPluginId = plugin.metadata.id.value
                                    else scope.launch {
                                        val result = if (plugin.hasUpdate) CloudStreamRepository.updatePlugin(plugin.metadata.id.value)
                                            else CloudStreamRepository.installPlugin(plugin.metadata.id.value)
                                        NuvioToastController.show(when (result) {
                                            is CloudStreamInstallResult.Success -> "Installed ${result.plugin.metadata.name}"
                                            is CloudStreamInstallResult.Error -> result.message
                                        })
                                    }
                                }) { Icon(when { plugin.hasUpdate -> Icons.Rounded.Update; plugin.isInstalled -> Icons.Rounded.CheckCircleOutline; else -> Icons.Rounded.DownloadForOffline },
                                    if (plugin.hasUpdate) "Update ${plugin.metadata.name}" else if (plugin.isInstalled) "Manage ${plugin.metadata.name}" else "Download ${plugin.metadata.name}") }
                            }
                        }
                        if (plugins.isEmpty()) item { BrowserEmpty(if (selectedRepository?.isRefreshing == true) "Loading extensions…" else "No extensions match your filters. Try clearing search, type or language.") }
                    }
                }
                if (repositoryUrl == null) ExtendedFloatingActionButton(onClick = { showAdd = true; addError = null },
                    modifier = Modifier.align(Alignment.BottomEnd).padding(12.dp), icon = { Icon(Icons.Rounded.Add, null) }, text = { Text("Add repository") })
            }
            ExtensionSummary(summary, status) { selection ->
                if (repositoryUrl == null) NuvioToastController.show("Open a repository to filter its extensions")
                else status = if (status == selection) "all" else selection
            }
        }
    }
    if (showAdd) AlertDialog(onDismissRequest = { if (!adding) showAdd = false }, title = { Text("Add repository") },
        text = { Column {
            Text("Paste a repository URL, or enter MegaRepo to discover repositories.")
            OutlinedTextField(value = addUrl, onValueChange = { addUrl = it; addError = null }, singleLine = true, label = { Text("Repository URL") })
            addError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        } }, confirmButton = { TextButton(enabled = addUrl.isNotBlank() && !adding, onClick = {
            adding = true
            scope.launch {
                try {
                    val input = addUrl.trim()
                    if (input.equals("MegaRepo", true) || input.equals("MegaProvider", true)) {
                        CloudStreamRepository.discoverRepositories(input).fold(onSuccess = {
                            showAdd = false; advanced = true; addUrl = ""
                            NuvioToastController.show("Discovered $it repositories. Choose which to install.")
                        }, onFailure = { addError = it.message ?: "Discovery failed" })
                    } else when (val result = CloudStreamRepository.addRepository(input)) {
                        is AddCloudStreamRepositoryResult.Success -> { showAdd = false; addUrl = "" }
                        is AddCloudStreamRepositoryResult.Error -> addError = result.message
                    }
                } catch (error: CancellationException) {
                    throw error
                } catch (error: Exception) {
                    addError = error.message ?: "Could not add repository"
                } finally {
                    adding = false
                }
            }
        }) { Text(if (adding) "Adding…" else "Add") } }, dismissButton = { TextButton(enabled = !adding, onClick = { showAdd = false }) { Text("Cancel") } })
    removeUrl?.let { url -> AlertDialog(onDismissRequest = { removeUrl = null }, title = { Text("Remove repository?") },
        text = { Text("This also removes its downloaded extensions. Other repositories are not affected.") },
        confirmButton = { TextButton(onClick = { CloudStreamRepository.removeRepository(url); removeUrl = null }) { Text("Remove") } },
        dismissButton = { TextButton(onClick = { removeUrl = null }) { Text("Cancel") } }) }
    if (showLanguages) AlertDialog(onDismissRequest = { showLanguages = false }, title = { Text("Extension language") },
        text = { LazyColumn { item { TextButton(onClick = { language = null; showLanguages = false }) { Text("All languages") } }
            items(scopedPlugins.mapNotNull { it.metadata.language }.distinct().sorted()) { code ->
                TextButton(onClick = { language = code; showLanguages = false }) { Text(cloudStreamBrowserLanguage(code)) }
            }
        } }, confirmButton = { TextButton(onClick = { showLanguages = false }) { Text("Close") } })
    val selectedPlugin = state.plugins.firstOrNull { it.metadata.id.value == selectedPluginId }
    if (selectedPlugin != null) {
        val sourcePreferences by remember { StreamSourcePreferencesRepository.ensureLoaded(); StreamSourcePreferencesRepository.uiState }.collectAsStateWithLifecycle()
        ModalBottomSheet(onDismissRequest = { selectedPluginId = null }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(16.dp)) {
                CloudStreamPluginCard(selectedPlugin, state.securityWarningAccepted, sourcePreferences.pinnedSources.map { it.id }.toSet(),
                    CloudStreamSettingsCopy.forLanguage(AppLanguage.ENGLISH), CloudStreamExtensionConfigBridge.preferNuvioSettingsUi(),
                    onMessage = { NuvioToastController.show(it) }, onOpenConfig = { configuringPluginId = selectedPluginId; selectedPluginId = null })
            }
        }
    }
    state.plugins.firstOrNull { it.metadata.id.value == configuringPluginId }?.let { plugin ->
        CloudStreamExtensionSettingsDialog(plugin, onDismiss = { configuringPluginId = null }, onLaunchNativeSettings = {
            configuringPluginId = null
            scope.launch { CloudStreamRepository.openPluginSettings(plugin.metadata.id.value).onFailure { NuvioToastController.show(it.message ?: "Settings unavailable") } }
        })
    }
    }
}

@Composable private fun BrowserIcon(url: String?, name: String) {
    Box(Modifier.size(40.dp).clip(CircleShape).background(MaterialTheme.colorScheme.surfaceContainerHigh), contentAlignment = Alignment.Center) {
        Text(name.take(1), color = MaterialTheme.colorScheme.primary)
        AsyncImage(model = url, contentDescription = null, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
    }
}

@Composable private fun BrowserEmpty(message: String) { Text(message, Modifier.fillMaxWidth().padding(vertical = 40.dp), color = MaterialTheme.colorScheme.onSurfaceVariant) }

@Composable private fun ExtensionSummary(summary: CloudStreamExtensionSummary, selected: String, onSelect: (String) -> Unit) {
    Surface(color = MaterialTheme.colorScheme.surfaceContainerHigh) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Extensions", style = MaterialTheme.typography.titleMedium)
            Row(Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(3.dp)).background(MaterialTheme.colorScheme.surfaceVariant)) {
                if (summary.downloaded > 0) Box(Modifier.weight(summary.downloaded.toFloat()).fillMaxHeight().background(MaterialTheme.colorScheme.primary))
                if (summary.disabled > 0) Box(Modifier.weight(summary.disabled.toFloat()).fillMaxHeight().background(MaterialTheme.colorScheme.tertiary))
                if (summary.available > 0) Box(Modifier.weight(summary.available.toFloat()).fillMaxHeight().background(MaterialTheme.colorScheme.outline))
            }
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf(Triple("downloaded", "Downloaded: ${summary.downloaded}", MaterialTheme.colorScheme.primary),
                    Triple("disabled", "Disabled: ${summary.disabled}", MaterialTheme.colorScheme.tertiary),
                    Triple("available", "Not downloaded: ${summary.available}", MaterialTheme.colorScheme.outline)).forEach { (key, label, color) ->
                    Row(Modifier.clickable { onSelect(key) }.padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(8.dp).clip(RoundedCornerShape(2.dp)).background(color))
                        Text(label, Modifier.padding(start = 5.dp), style = MaterialTheme.typography.labelSmall,
                            fontWeight = if (selected == key) FontWeight.Bold else FontWeight.Normal)
                    }
                }
            }
        }
    }
}
