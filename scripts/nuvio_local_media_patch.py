#!/usr/bin/env python3
"""Local Android Folder Videos in DownloadsScreen + 'Open with Nuvio' from Storage."""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")
    if new:
        if new in content:
            return False
    elif old not in content:
        return False
    if old not in content:
        raise RuntimeError(f"Patch anchor missing for {label} in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return True


def _write_text(root: Path, rel_path: str, content: str, patched: list[str]) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    patched.append(rel_path)


def apply_local_media_patch(root: Path) -> list[str]:
    patched: list[str] = []

    # 1. LocalVideoLaunchRequest in AppUrlBridge.kt
    bridge_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/deeplink/AppUrlBridge.kt"
    if bridge_kt.is_file():
        changed = False
        changed |= _replace_once(
            bridge_kt,
            "sealed interface AppDeepLink {\n",
            "data class LocalVideoLaunchRequest(\n"
            "    val uri: String,\n"
            "    val title: String,\n"
            "    val filename: String? = null,\n"
            "    val subtitle: String? = null,\n"
            "    val mimeType: String? = null,\n"
            "    val nonce: Long = 0L,\n"
            ")\n\n"
            "sealed interface AppDeepLink {\n",
            "AppUrlBridge LocalVideoLaunchRequest",
        )
        changed |= _replace_once(
            bridge_kt,
            "object AppDeepLinkRepository {\n"
            "    private val _pendingDeepLink = MutableStateFlow<AppDeepLink?>(null)\n"
            "    val pendingDeepLink: StateFlow<AppDeepLink?> = _pendingDeepLink.asStateFlow()\n",
            "object AppDeepLinkRepository {\n"
            "    private val _pendingDeepLink = MutableStateFlow<AppDeepLink?>(null)\n"
            "    val pendingDeepLink: StateFlow<AppDeepLink?> = _pendingDeepLink.asStateFlow()\n\n"
            "    private var localVideoSeq = 0L\n"
            "    private val _pendingLocalVideo = MutableStateFlow<LocalVideoLaunchRequest?>(null)\n"
            "    val pendingLocalVideo: StateFlow<LocalVideoLaunchRequest?> = _pendingLocalVideo.asStateFlow()\n\n"
            "    fun openLocalVideo(\n"
            "        uri: String,\n"
            "        title: String,\n"
            "        filename: String? = null,\n"
            "        subtitle: String? = null,\n"
            "        mimeType: String? = null,\n"
            "    ) {\n"
            "        val trimmed = uri.trim()\n"
            "        if (trimmed.isEmpty()) return\n"
            "        localVideoSeq += 1L\n"
            "        _pendingLocalVideo.value = LocalVideoLaunchRequest(\n"
            "            uri = trimmed,\n"
            "            title = title.trim().ifEmpty { \"Local Video\" },\n"
            "            filename = filename?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            subtitle = subtitle?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            mimeType = mimeType?.trim()?.takeIf { it.isNotEmpty() },\n"
            "            nonce = localVideoSeq,\n"
            "        )\n"
            "    }\n\n"
            "    fun markLocalVideoConsumed(request: LocalVideoLaunchRequest) {\n"
            "        if (_pendingLocalVideo.value?.nonce == request.nonce) {\n"
            "            _pendingLocalVideo.value = null\n"
            "        }\n"
            "    }\n",
            "AppDeepLinkRepository pendingLocalVideo",
        )
        if changed:
            patched.append(str(bridge_kt.relative_to(root)))

    # 2. LocalFolderVideosPlatform (commonMain + iosMain + androidMain)
    _write_text(
        root,
        "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.kt",
        r'''package com.nuvio.app.features.downloads

import kotlinx.coroutines.flow.StateFlow

data class LocalVideoFolder(
    val treeUri: String,
    val displayName: String,
)

data class LocalVideoFileItem(
    val id: String,
    val uri: String,
    val title: String,
    val filename: String,
    val folderUri: String,
    val folderName: String,
    val sizeBytes: Long,
    val lastModifiedMs: Long,
    val mimeType: String?,
    val extensionLabel: String,
)

data class LocalFolderVideosState(
    val isSupported: Boolean = false,
    val isScanning: Boolean = false,
    val folders: List<LocalVideoFolder> = emptyList(),
    val videos: List<LocalVideoFileItem> = emptyList(),
    val errorMessage: String? = null,
)

internal expect object LocalFolderVideosPlatform {
    val state: StateFlow<LocalFolderVideosState>

    fun addFolder()
    fun removeFolder(treeUri: String)
    fun refresh()
    fun pickAndPlaySingleVideo()
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/iosMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.ios.kt",
        r'''package com.nuvio.app.features.downloads

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

internal actual object LocalFolderVideosPlatform {
    private val _state = MutableStateFlow(LocalFolderVideosState(isSupported = false))
    actual val state: StateFlow<LocalFolderVideosState> = _state.asStateFlow()

    actual fun addFolder() = Unit
    actual fun removeFolder(treeUri: String) = Unit
    actual fun refresh() = Unit
    actual fun pickAndPlaySingleVideo() = Unit
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/LocalFolderVideosPlatform.android.kt",
        r'''package com.nuvio.app.features.downloads

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import androidx.appcompat.app.AppCompatActivity
import com.nuvio.app.core.deeplink.AppDeepLinkRepository
import com.nuvio.app.core.ui.NuvioToastController
import java.lang.ref.WeakReference
import java.util.Locale
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

internal actual object LocalFolderVideosPlatform {
    private const val PREFS_NAME = "nuvio_local_video_folders"
    private const val KEY_TREE_URIS = "folder_tree_uris"
    private const val REQUEST_ADD_LOCAL_FOLDER = 51044
    private const val REQUEST_PICK_SINGLE_VIDEO = 51045
    private const val MAX_SCAN_DEPTH = 5
    private const val MAX_FILES_PER_SCAN = 1500

    private val VIDEO_EXTENSIONS = setOf(
        "mp4", "mkv", "avi", "webm", "mov", "m4v", "ts", "m2ts",
        "mts", "flv", "wmv", "3gp", "3g2", "mpg", "mpeg", "ogv", "vob", "m3u8",
    )

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var scanJob: Job? = null
    private var appContext: Context? = null
    private var activityRef: WeakReference<AppCompatActivity>? = null

    private val _state = MutableStateFlow(LocalFolderVideosState(isSupported = true))
    actual val state: StateFlow<LocalFolderVideosState> = _state.asStateFlow()

    fun initialize(context: Context) {
        appContext = context.applicationContext
        refresh()
    }

    fun bindActivity(activity: AppCompatActivity) {
        activityRef = WeakReference(activity)
    }

    fun unbindActivity(activity: AppCompatActivity) {
        if (activityRef?.get() === activity) {
            activityRef = null
        }
    }

    @Suppress("DEPRECATION")
    actual fun addFolder() {
        val activity = activityRef?.get()?.takeUnless { it.isFinishing || it.isDestroyed }
        if (activity == null) {
            NuvioToastController.show("Folder picker is unavailable right now")
            return
        }
        runCatching {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
                addFlags(Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)
            }
            activity.startActivityForResult(intent, REQUEST_ADD_LOCAL_FOLDER)
        }.onFailure { err ->
            NuvioToastController.show(err.message ?: "Could not open Android folder picker")
        }
    }

    @Suppress("DEPRECATION")
    actual fun pickAndPlaySingleVideo() {
        val activity = activityRef?.get()?.takeUnless { it.isFinishing || it.isDestroyed }
        if (activity == null) {
            NuvioToastController.show("File picker is unavailable right now")
            return
        }
        runCatching {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "video/*"
                putExtra(
                    Intent.EXTRA_MIME_TYPES,
                    arrayOf(
                        "video/*",
                        "application/x-matroska",
                        "application/mp4",
                        "application/vnd.apple.mpegurl",
                        "application/x-mpegurl",
                    ),
                )
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            }
            activity.startActivityForResult(intent, REQUEST_PICK_SINGLE_VIDEO)
        }.onFailure { err ->
            NuvioToastController.show(err.message ?: "Could not open video file picker")
        }
    }

    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        val ctx = appContext ?: return false
        when (requestCode) {
            REQUEST_ADD_LOCAL_FOLDER -> {
                if (resultCode != Activity.RESULT_OK) return true
                val uri = data?.data ?: return true
                runCatching {
                    val flags = (data.flags and (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION))
                        .let { if (it == 0) Intent.FLAG_GRANT_READ_URI_PERMISSION else it }
                    ctx.contentResolver.takePersistableUriPermission(
                        uri,
                        flags and Intent.FLAG_GRANT_READ_URI_PERMISSION,
                    )
                }
                val saved = getSavedTreeUris(ctx).toMutableSet()
                saved += uri.toString()
                saveTreeUris(ctx, saved)
                refresh()
                NuvioToastController.show("Added folder: ${friendlyTreeName(uri)}")
                return true
            }
            REQUEST_PICK_SINGLE_VIDEO -> {
                if (resultCode != Activity.RESULT_OK) return true
                val uri = data?.data ?: return true
                runCatching {
                    ctx.contentResolver.takePersistableUriPermission(
                        uri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION,
                    )
                }
                val displayName = resolveDisplayName(ctx, uri)
                val cleanTitle = cleanVideoTitle(displayName)
                val mime = ctx.contentResolver.getType(uri)
                AppDeepLinkRepository.openLocalVideo(
                    uri = uri.toString(),
                    title = cleanTitle,
                    filename = displayName,
                    subtitle = "Local Storage",
                    mimeType = mime,
                )
                return true
            }
            else -> return false
        }
    }

    actual fun removeFolder(treeUri: String) {
        val ctx = appContext ?: return
        val saved = getSavedTreeUris(ctx).toMutableSet()
        if (saved.remove(treeUri)) {
            saveTreeUris(ctx, saved)
            refresh()
        }
    }

    actual fun refresh() {
        val ctx = appContext ?: return
        scanJob?.cancel()
        scanJob = scope.launch {
            _state.value = _state.value.copy(isSupported = true, isScanning = true, errorMessage = null)
            runCatching {
                val configuredExternal = DownloadsExternalFolderPlatform.state.value.uri
                    ?.trim()
                    ?.takeIf { it.isNotEmpty() }
                val allTreeStrings = buildList {
                    addAll(getSavedTreeUris(ctx))
                    if (configuredExternal != null && configuredExternal !in this) {
                        add(configuredExternal)
                    }
                }
                val folders = allTreeStrings.map { raw ->
                    val parsed = Uri.parse(raw)
                    LocalVideoFolder(
                        treeUri = raw,
                        displayName = friendlyTreeName(parsed),
                    )
                }
                val collected = ArrayList<LocalVideoFileItem>()
                val seenUris = HashSet<String>()
                for (folder in folders) {
                    if (collected.size >= MAX_FILES_PER_SCAN) break
                    val treeUri = runCatching { Uri.parse(folder.treeUri) }.getOrNull() ?: continue
                    val rootDocId = runCatching { DocumentsContract.getTreeDocumentId(treeUri) }.getOrNull()
                        ?: continue
                    scanDocumentFolder(
                        ctx = ctx,
                        treeUri = treeUri,
                        parentDocId = rootDocId,
                        rootFolderUri = folder.treeUri,
                        folderLabel = folder.displayName,
                        depth = 0,
                        seenUris = seenUris,
                        out = collected,
                    )
                }
                collected.sortWith(
                    compareByDescending<LocalVideoFileItem> { it.lastModifiedMs }
                        .thenBy { it.title.lowercase(Locale.US) },
                )
                _state.value = LocalFolderVideosState(
                    isSupported = true,
                    isScanning = false,
                    folders = folders,
                    videos = collected,
                    errorMessage = null,
                )
            }.onFailure { err ->
                _state.value = _state.value.copy(
                    isSupported = true,
                    isScanning = false,
                    errorMessage = err.message ?: "Could not scan local video folders",
                )
            }
        }
    }

    private fun scanDocumentFolder(
        ctx: Context,
        treeUri: Uri,
        parentDocId: String,
        rootFolderUri: String,
        folderLabel: String,
        depth: Int,
        seenUris: MutableSet<String>,
        out: MutableList<LocalVideoFileItem>,
    ) {
        if (depth > MAX_SCAN_DEPTH || out.size >= MAX_FILES_PER_SCAN) return
        val childrenUri = runCatching {
            DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, parentDocId)
        }.getOrNull() ?: return

        val projection = arrayOf(
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED,
        )

        val subDirs = ArrayList<Pair<String, String>>()
        runCatching {
            ctx.contentResolver.query(childrenUri, projection, null, null, null)?.use { cursor ->
                val idCol = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DOCUMENT_ID)
                val nameCol = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DISPLAY_NAME)
                val mimeCol = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_MIME_TYPE)
                val sizeCol = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_SIZE)
                val modCol = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_LAST_MODIFIED)

                while (cursor.moveToNext() && out.size < MAX_FILES_PER_SCAN) {
                    val docId = if (idCol >= 0) cursor.getString(idCol) else null
                    val name = if (nameCol >= 0) cursor.getString(nameCol) else null
                    if (docId.isNullOrBlank() || name.isNullOrBlank() || name.startsWith(".")) continue
                    val mime = if (mimeCol >= 0 && !cursor.isNull(mimeCol)) cursor.getString(mimeCol) else null

                    if (mime == DocumentsContract.Document.MIME_TYPE_DIR) {
                        subDirs += docId to "$folderLabel / $name"
                        continue
                    }

                    val ext = name.substringAfterLast('.', "").lowercase(Locale.US)
                    val isVideo = (mime?.startsWith("video/", ignoreCase = true) == true) ||
                        ext in VIDEO_EXTENSIONS ||
                        mime.equals("application/x-matroska", ignoreCase = true) ||
                        mime.equals("application/mp4", ignoreCase = true)
                    if (!isVideo) continue
                    // Skip incomplete .part files
                    if (name.endsWith(".part", ignoreCase = true) || name.endsWith(".crdownload", ignoreCase = true)) {
                        continue
                    }

                    val docUri = DocumentsContract.buildDocumentUriUsingTree(treeUri, docId)
                    val uriStr = docUri.toString()
                    if (!seenUris.add(uriStr)) continue

                    val sizeBytes = if (sizeCol >= 0 && !cursor.isNull(sizeCol)) cursor.getLong(sizeCol) else 0L
                    val lastMod = if (modCol >= 0 && !cursor.isNull(modCol)) cursor.getLong(modCol) else 0L

                    out += LocalVideoFileItem(
                        id = uriStr,
                        uri = uriStr,
                        title = cleanVideoTitle(name),
                        filename = name,
                        folderUri = rootFolderUri,
                        folderName = folderLabel,
                        sizeBytes = sizeBytes.coerceAtLeast(0L),
                        lastModifiedMs = lastMod.coerceAtLeast(0L),
                        mimeType = mime,
                        extensionLabel = ext.uppercase(Locale.US).ifBlank { "VIDEO" },
                    )
                }
            }
        }

        for ((subDocId, subLabel) in subDirs) {
            if (out.size >= MAX_FILES_PER_SCAN) break
            scanDocumentFolder(
                ctx = ctx,
                treeUri = treeUri,
                parentDocId = subDocId,
                rootFolderUri = rootFolderUri,
                folderLabel = subLabel,
                depth = depth + 1,
                seenUris = seenUris,
                out = out,
            )
        }
    }

    internal fun resolveDisplayName(ctx: Context, uri: Uri): String {
        if (uri.scheme.equals("content", ignoreCase = true)) {
            runCatching {
                ctx.contentResolver.query(
                    uri,
                    arrayOf(OpenableColumns.DISPLAY_NAME),
                    null,
                    null,
                    null,
                )?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (idx >= 0) {
                            val name = cursor.getString(idx)?.trim()
                            if (!name.isNullOrEmpty()) return name
                        }
                    }
                }
            }
        }
        return uri.lastPathSegment
            ?.substringAfterLast('/')
            ?.substringAfterLast(':')
            ?.trim()
            ?.takeIf { it.isNotEmpty() }
            ?: "Local Video"
    }

    internal fun cleanVideoTitle(filename: String): String {
        val withoutExt = filename.substringBeforeLast('.', filename)
        return withoutExt
            .replace('_', ' ')
            .replace(Regex("\\s+"), " ")
            .trim()
            .ifEmpty { filename }
    }

    private fun friendlyTreeName(uri: Uri): String {
        val docId = runCatching { DocumentsContract.getTreeDocumentId(uri) }.getOrNull()
            ?: uri.lastPathSegment
            ?: return "Local Folder"
        val cleaned = docId.substringAfter(':', docId).trim('/')
        return if (cleaned.isEmpty()) "Internal Storage" else cleaned.substringAfterLast('/')
    }

    private fun getSavedTreeUris(ctx: Context): List<String> {
        val raw = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getStringSet(KEY_TREE_URIS, emptySet())
            .orEmpty()
        return raw.filter { it.isNotBlank() }.sorted()
    }

    private fun saveTreeUris(ctx: Context, uris: Set<String>) {
        ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putStringSet(KEY_TREE_URIS, uris)
            .apply()
    }
}
''',
        patched,
    )

    # 3. DownloadsScreen.kt: Local Android Folders + Local Video playback
    dl_screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsScreen.kt"
    if dl_screen.is_file():
        changed = False
        changed |= _replace_once(
            dl_screen,
            "import androidx.compose.material.icons.Icons\n"
            "import androidx.compose.material.icons.rounded.Download\n"
            "import androidx.compose.material.icons.rounded.Settings\n",
            "import androidx.compose.foundation.BorderStroke\n"
            "import androidx.compose.foundation.clickable\n"
            "import androidx.compose.foundation.horizontalScroll\n"
            "import androidx.compose.foundation.layout.Spacer\n"
            "import androidx.compose.foundation.layout.width\n"
            "import androidx.compose.foundation.rememberScrollState\n"
            "import androidx.compose.foundation.shape.RoundedCornerShape\n"
            "import androidx.compose.material.icons.Icons\n"
            "import androidx.compose.material.icons.rounded.Add\n"
            "import androidx.compose.material.icons.rounded.Close\n"
            "import androidx.compose.material.icons.rounded.Download\n"
            "import androidx.compose.material.icons.rounded.Folder\n"
            "import androidx.compose.material.icons.rounded.Movie\n"
            "import androidx.compose.material.icons.rounded.PlayArrow\n"
            "import androidx.compose.material.icons.rounded.Refresh\n"
            "import androidx.compose.material.icons.rounded.Settings\n"
            "import androidx.compose.material3.Surface\n"
            "import androidx.compose.ui.text.font.FontWeight\n"
            "import androidx.compose.ui.text.style.TextOverflow\n",
            "DownloadsScreen local folder imports",
        )
        changed |= _replace_once(
            dl_screen,
            "import com.nuvio.app.core.ui.NuvioScreen\n",
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n"
            "import com.nuvio.app.core.ui.NuvioScreen\n",
            "DownloadsScreen AppDeepLinkRepository import",
        )
        changed |= _replace_once(
            dl_screen,
            "    var deleteItemId by rememberSaveable { mutableStateOf<String?>(null) }\n",
            "    var deleteItemId by rememberSaveable { mutableStateOf<String?>(null) }\n"
            "    val localState by LocalFolderVideosPlatform.state.collectAsStateWithLifecycle()\n"
            "    var viewFilter by rememberSaveable { mutableStateOf(\"all\") }\n"
            "    var selectedLocalFolderUri by rememberSaveable { mutableStateOf<String?>(null) }\n",
            "DownloadsScreen localState & viewFilter",
        )
        changed |= _replace_once(
            dl_screen,
            "        val showId = selectedShowId\n"
            "        if (showId == null) {\n"
            "            downloadsRootContent(\n"
            "                items = uiState.items,\n"
            "                speeds = speeds,\n"
            "                watchStatusOf = watchStatusOf,\n"
            "                onPlay = onOpenDownload,\n"
            "                onOpenShow = { item ->\n"
            "                    onNavigateToShow?.invoke(item.parentMetaId, item.title) ?: run { selectedShowId = item.parentMetaId }\n"
            "                },\n"
            "                onOpenActions = onOpenActions,\n"
            "            )\n"
            "        } else {\n",
            "        val showId = selectedShowId\n"
            "        if (showId == null) {\n"
            "            downloadsRootContent(\n"
            "                items = uiState.items,\n"
            "                localState = localState,\n"
            "                viewFilter = viewFilter,\n"
            "                onViewFilterChange = { viewFilter = it },\n"
            "                selectedLocalFolderUri = selectedLocalFolderUri,\n"
            "                onSelectLocalFolderUri = { selectedLocalFolderUri = it },\n"
            "                onAddLocalFolder = { LocalFolderVideosPlatform.addFolder() },\n"
            "                onRemoveLocalFolder = { uri ->\n"
            "                    if (selectedLocalFolderUri == uri) selectedLocalFolderUri = null\n"
            "                    LocalFolderVideosPlatform.removeFolder(uri)\n"
            "                },\n"
            "                onPickSingleVideo = { LocalFolderVideosPlatform.pickAndPlaySingleVideo() },\n"
            "                onRefreshLocalFolders = { LocalFolderVideosPlatform.refresh() },\n"
            "                onPlayLocalVideo = { video ->\n"
            "                    AppDeepLinkRepository.openLocalVideo(\n"
            "                        uri = video.uri,\n"
            "                        title = video.title,\n"
            "                        filename = video.filename,\n"
            "                        subtitle = video.folderName,\n"
            "                        mimeType = video.mimeType,\n"
            "                    )\n"
            "                },\n"
            "                speeds = speeds,\n"
            "                watchStatusOf = watchStatusOf,\n"
            "                onPlay = onOpenDownload,\n"
            "                onOpenShow = { item ->\n"
            "                    onNavigateToShow?.invoke(item.parentMetaId, item.title) ?: run { selectedShowId = item.parentMetaId }\n"
            "                },\n"
            "                onOpenActions = onOpenActions,\n"
            "            )\n"
            "        } else {\n",
            "DownloadsScreen pass localState to downloadsRootContent",
        )
        changed |= _replace_once(
            dl_screen,
            "private fun LazyListScope.downloadsRootContent(\n"
            "    items: List<DownloadItem>,\n"
            "    speeds: Map<String, Long>,\n"
            "    watchStatusOf: (DownloadItem) -> DownloadWatchStatus,\n"
            "    onPlay: (DownloadItem) -> Unit,\n"
            "    onOpenShow: (DownloadItem) -> Unit,\n"
            "    onOpenActions: (DownloadItem) -> Unit,\n"
            ") {\n"
            "    if (items.isEmpty()) {\n"
            "        item(key = \"empty\") {\n"
            "            DownloadsEmptyState(\n"
            "                title = stringResource(Res.string.downloads_empty_title),\n"
            "                message = stringResource(Res.string.downloads_empty_message),\n"
            "            )\n"
            "        }\n"
            "        return\n"
            "    }\n",
            "private fun LazyListScope.downloadsRootContent(\n"
            "    items: List<DownloadItem>,\n"
            "    localState: LocalFolderVideosState,\n"
            "    viewFilter: String,\n"
            "    onViewFilterChange: (String) -> Unit,\n"
            "    selectedLocalFolderUri: String?,\n"
            "    onSelectLocalFolderUri: (String?) -> Unit,\n"
            "    onAddLocalFolder: () -> Unit,\n"
            "    onRemoveLocalFolder: (String) -> Unit,\n"
            "    onPickSingleVideo: () -> Unit,\n"
            "    onRefreshLocalFolders: () -> Unit,\n"
            "    onPlayLocalVideo: (LocalVideoFileItem) -> Unit,\n"
            "    speeds: Map<String, Long>,\n"
            "    watchStatusOf: (DownloadItem) -> DownloadWatchStatus,\n"
            "    onPlay: (DownloadItem) -> Unit,\n"
            "    onOpenShow: (DownloadItem) -> Unit,\n"
            "    onOpenActions: (DownloadItem) -> Unit,\n"
            ") {\n"
            "    if (localState.isSupported) {\n"
            "        item(key = \"local-folders-toolbar\") {\n"
            "            LocalFoldersToolbar(\n"
            "                viewFilter = viewFilter,\n"
            "                appDownloadsCount = items.size,\n"
            "                localVideosCount = localState.videos.size,\n"
            "                folders = localState.folders,\n"
            "                selectedFolderUri = selectedLocalFolderUri,\n"
            "                isScanning = localState.isScanning,\n"
            "                onViewFilterChange = onViewFilterChange,\n"
            "                onSelectFolderUri = onSelectLocalFolderUri,\n"
            "                onAddFolder = onAddLocalFolder,\n"
            "                onRemoveFolder = onRemoveLocalFolder,\n"
            "                onPickSingleVideo = onPickSingleVideo,\n"
            "                onRefresh = onRefreshLocalFolders,\n"
            "            )\n"
            "        }\n"
            "    }\n\n"
            "    val showAppDownloads = !localState.isSupported || viewFilter == \"all\" || viewFilter == \"app\"\n"
            "    val showLocalFolders = localState.isSupported && (viewFilter == \"all\" || viewFilter == \"local\")\n"
            "    val visibleLocalVideos = if (selectedLocalFolderUri == null) {\n"
            "        localState.videos\n"
            "    } else {\n"
            "        localState.videos.filter { it.folderUri == selectedLocalFolderUri }\n"
            "    }\n\n"
            "    if (showLocalFolders && visibleLocalVideos.isNotEmpty()) {\n"
            "        item(key = \"header-local-videos\") {\n"
            "            NuvioSectionLabel(\n"
            "                text = \"Local Folder Videos (${visibleLocalVideos.size})\",\n"
            "                modifier = Modifier.padding(top = NuvioTokens.Space.s8, bottom = 2.dp),\n"
            "            )\n"
            "        }\n"
            "        items(visibleLocalVideos, key = { \"local:${it.id}\" }) { video ->\n"
            "            LocalVideoFileCard(\n"
            "                video = video,\n"
            "                onClick = { onPlayLocalVideo(video) },\n"
            "            )\n"
            "        }\n"
            "    } else if (localState.isSupported && viewFilter == \"local\" && !localState.isScanning) {\n"
            "        item(key = \"local-empty\") {\n"
            "            DownloadsEmptyState(\n"
            "                title = if (localState.folders.isEmpty()) \"No Android folders added yet\" else \"No video files found\",\n"
            "                message = if (localState.folders.isEmpty()) {\n"
            "                    \"Tap '+ Add Folder' above to browse and play videos from any folder on your phone, or 'Open Video' to play a single file.\"\n"
            "                } else {\n"
            "                    \"No playable video files (.mp4, .mkv, .avi, .webm, .mov, .ts) were found in the selected folder.\"\n"
            "                },\n"
            "            )\n"
            "        }\n"
            "    }\n\n"
            "    if (!showAppDownloads) return\n\n"
            "    if (items.isEmpty()) {\n"
            "        if (!showLocalFolders || visibleLocalVideos.isEmpty()) {\n"
            "            item(key = \"empty\") {\n"
            "                DownloadsEmptyState(\n"
            "                    title = stringResource(Res.string.downloads_empty_title),\n"
            "                    message = stringResource(Res.string.downloads_empty_message),\n"
            "                )\n"
            "            }\n"
            "        }\n"
            "        return\n"
            "    }\n",
            "DownloadsScreen local videos section in downloadsRootContent",
        )

        local_composables = r'''

@Composable
private fun LocalFoldersToolbar(
    viewFilter: String,
    appDownloadsCount: Int,
    localVideosCount: Int,
    folders: List<LocalVideoFolder>,
    selectedFolderUri: String?,
    isScanning: Boolean,
    onViewFilterChange: (String) -> Unit,
    onSelectFolderUri: (String?) -> Unit,
    onAddFolder: () -> Unit,
    onRemoveFolder: (String) -> Unit,
    onPickSingleVideo: () -> Unit,
    onRefresh: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            listOf(
                "all" to "All (${appDownloadsCount + localVideosCount})",
                "app" to "App Downloads ($appDownloadsCount)",
                "local" to "Local Folders ($localVideosCount)",
            ).forEach { (key, label) ->
                val selected = viewFilter == key
                Surface(
                    shape = RoundedCornerShape(999.dp),
                    color = if (selected) tokens.colors.accent.copy(alpha = 0.22f) else tokens.colors.surfaceElevated,
                    border = BorderStroke(
                        width = 1.dp,
                        color = if (selected) tokens.colors.accent else tokens.colors.borderSubtle,
                    ),
                    modifier = Modifier.clickable { onViewFilterChange(key) },
                ) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
                        color = if (selected) tokens.colors.textPrimary else tokens.colors.textSecondary,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                    )
                }
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = tokens.colors.surfaceElevated,
                border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                modifier = Modifier.clickable(onClick = onAddFolder),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Add,
                        contentDescription = null,
                        tint = tokens.colors.accent,
                        modifier = Modifier.size(16.dp),
                    )
                    Spacer(Modifier.width(5.dp))
                    Icon(
                        imageVector = Icons.Rounded.Folder,
                        contentDescription = null,
                        tint = tokens.colors.textPrimary,
                        modifier = Modifier.size(15.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = "Add Folder",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.textPrimary,
                    )
                }
            }

            Surface(
                shape = RoundedCornerShape(10.dp),
                color = tokens.colors.surfaceElevated,
                border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                modifier = Modifier.clickable(onClick = onPickSingleVideo),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Movie,
                        contentDescription = null,
                        tint = tokens.colors.textPrimary,
                        modifier = Modifier.size(15.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = "Open Video",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = tokens.colors.textPrimary,
                    )
                }
            }

            if (folders.isNotEmpty() || isScanning) {
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = tokens.colors.surfaceElevated,
                    border = BorderStroke(1.dp, tokens.colors.borderSubtle),
                    modifier = Modifier.clickable(onClick = onRefresh),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Refresh,
                            contentDescription = "Refresh local folders",
                            tint = tokens.colors.textSecondary,
                            modifier = Modifier.size(15.dp),
                        )
                        Spacer(Modifier.width(5.dp))
                        Text(
                            text = if (isScanning) "Scanning..." else "Refresh",
                            style = MaterialTheme.typography.labelMedium,
                            color = tokens.colors.textSecondary,
                        )
                    }
                }
            }
        }

        if (folders.isNotEmpty()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (folders.size > 1) {
                    val allSelected = selectedFolderUri == null
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = if (allSelected) tokens.colors.accent.copy(alpha = 0.18f) else tokens.colors.surface,
                        border = BorderStroke(1.dp, if (allSelected) tokens.colors.accent else tokens.colors.borderSubtle),
                        modifier = Modifier.clickable { onSelectFolderUri(null) },
                    ) {
                        Text(
                            text = "All Folders",
                            style = MaterialTheme.typography.labelSmall,
                            color = tokens.colors.textPrimary,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
                        )
                    }
                }
                folders.forEach { folder ->
                    val selected = selectedFolderUri == folder.treeUri
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = if (selected) tokens.colors.accent.copy(alpha = 0.18f) else tokens.colors.surface,
                        border = BorderStroke(1.dp, if (selected) tokens.colors.accent else tokens.colors.borderSubtle),
                        modifier = Modifier.clickable {
                            onSelectFolderUri(if (selected) null else folder.treeUri)
                        },
                    ) {
                        Row(
                            modifier = Modifier.padding(start = 9.dp, end = 6.dp, top = 5.dp, bottom = 5.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                imageVector = Icons.Rounded.Folder,
                                contentDescription = null,
                                tint = tokens.colors.textSecondary,
                                modifier = Modifier.size(13.dp),
                            )
                            Spacer(Modifier.width(5.dp))
                            Text(
                                text = folder.displayName,
                                style = MaterialTheme.typography.labelSmall,
                                color = tokens.colors.textPrimary,
                            )
                            Spacer(Modifier.width(4.dp))
                            Icon(
                                imageVector = Icons.Rounded.Close,
                                contentDescription = "Remove ${folder.displayName}",
                                tint = tokens.colors.textMuted,
                                modifier = Modifier
                                    .size(14.dp)
                                    .clickable { onRemoveFolder(folder.treeUri) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LocalVideoFileCard(
    video: LocalVideoFileItem,
    onClick: () -> Unit,
) {
    val tokens = MaterialTheme.nuvio
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = tokens.colors.surfaceElevated,
        border = BorderStroke(1.dp, tokens.colors.borderSubtle),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(tokens.colors.accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Rounded.PlayArrow,
                    contentDescription = null,
                    tint = tokens.colors.accent,
                    modifier = Modifier.size(24.dp),
                )
            }
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                Text(
                    text = video.title,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = tokens.colors.textPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = video.extensionLabel,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = tokens.colors.accent,
                    )
                    if (video.sizeBytes > 0L) {
                        Text(
                            text = "• ${formatBytes(video.sizeBytes)}",
                            style = MaterialTheme.typography.labelSmall,
                            color = tokens.colors.textSecondary,
                        )
                    }
                    Text(
                        text = "• ${video.folderName}",
                        style = MaterialTheme.typography.labelSmall,
                        color = tokens.colors.textMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}
'''
        current_dl = dl_screen.read_text(encoding="utf-8", errors="replace")
        if "fun LocalFoldersToolbar(" not in current_dl:
            dl_screen.write_text(current_dl + local_composables, encoding="utf-8")
            changed = True
        if changed:
            patched.append(str(dl_screen.relative_to(root)))

    # 4. AndroidManifest.xml: Register Nuvio as an Android video handler ("Open with Nuvio")
    manifest_xml = root / "androidApp/src/main/AndroidManifest.xml"
    if manifest_xml.is_file():
        changed = _replace_once(
            manifest_xml,
            '        <activity\n'
            '            android:exported="true"\n'
            '            android:name="com.nuvio.app.MainActivity"\n'
            '            android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"\n'
            '            android:supportsPictureInPicture="true"\n'
            '            android:theme="@style/Theme.Nuvio.Splash" />\n',
            '        <activity\n'
            '            android:exported="true"\n'
            '            android:name="com.nuvio.app.MainActivity"\n'
            '            android:label="@string/app_name"\n'
            '            android:launchMode="singleTask"\n'
            '            android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"\n'
            '            android:supportsPictureInPicture="true"\n'
            '            android:theme="@style/Theme.Nuvio.Splash">\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.VIEW" />\n'
            '                <category android:name="android.intent.category.DEFAULT" />\n'
            '                <category android:name="android.intent.category.BROWSABLE" />\n'
            '                <data android:scheme="content" />\n'
            '                <data android:scheme="file" />\n'
            '                <data android:mimeType="video/*" />\n'
            '                <data android:mimeType="application/mp4" />\n'
            '                <data android:mimeType="application/x-matroska" />\n'
            '                <data android:mimeType="application/vnd.apple.mpegurl" />\n'
            '                <data android:mimeType="application/x-mpegurl" />\n'
            '                <data android:mimeType="application/ogg" />\n'
            '            </intent-filter>\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.SEND" />\n'
            '                <category android:name="android.intent.category.DEFAULT" />\n'
            '                <data android:mimeType="video/*" />\n'
            '            </intent-filter>\n'
            '        </activity>\n',
            "AndroidManifest Open with Nuvio video intent-filters",
        )
        if changed:
            patched.append(str(manifest_xml.relative_to(root)))

    # 5. MainActivity.kt: Wire LocalFolderVideosPlatform + handle ACTION_VIEW / ACTION_SEND video files
    main_act = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/MainActivity.kt"
    if main_act.is_file():
        changed = False
        changed |= _replace_once(
            main_act,
            "import com.nuvio.app.features.downloads.DownloadsExternalFolderPlatform\n",
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n"
            "import com.nuvio.app.features.downloads.DownloadsExternalFolderPlatform\n"
            "import com.nuvio.app.features.downloads.LocalFolderVideosPlatform\n",
            "MainActivity LocalFolderVideosPlatform & AppDeepLinkRepository imports",
        )
        changed |= _replace_once(
            main_act,
            "        DownloadsExternalFolderPlatform.initialize(applicationContext)\n"
            "        DownloadsExternalFolderPlatform.bindActivity(this)\n",
            "        DownloadsExternalFolderPlatform.initialize(applicationContext)\n"
            "        DownloadsExternalFolderPlatform.bindActivity(this)\n"
            "        LocalFolderVideosPlatform.initialize(applicationContext)\n"
            "        LocalFolderVideosPlatform.bindActivity(this)\n",
            "MainActivity initialize & bind LocalFolderVideosPlatform",
        )
        changed |= _replace_once(
            main_act,
            "        DownloadsExternalFolderPlatform.unbindActivity(this)\n",
            "        DownloadsExternalFolderPlatform.unbindActivity(this)\n"
            "        LocalFolderVideosPlatform.unbindActivity(this)\n",
            "MainActivity unbind LocalFolderVideosPlatform",
        )
        changed |= _replace_once(
            main_act,
            "        if (DownloadsExternalFolderPlatform.handleActivityResult(requestCode, resultCode, data)) {\n"
            "            return\n"
            "        }\n",
            "        if (DownloadsExternalFolderPlatform.handleActivityResult(requestCode, resultCode, data)) {\n"
            "            return\n"
            "        }\n"
            "        if (LocalFolderVideosPlatform.onActivityResult(requestCode, resultCode, data)) {\n"
            "            return\n"
            "        }\n",
            "MainActivity LocalFolderVideosPlatform onActivityResult",
        )
        changed |= _replace_once(
            main_act,
            "    private fun handleIncomingAppIntent(intent: Intent?) {\n"
            "        val appUrl = (intent?.dataString ?: intent?.getStringExtra(LinkActivity.EXTRA_LINK))?.trim().orEmpty()\n"
            "        if (appUrl.isBlank()) return\n"
            "        handleAppUrl(appUrl)\n"
            "    }\n",
            "    private fun handleIncomingAppIntent(intent: Intent?) {\n"
            "        if (handleIncomingVideoFileIntent(intent)) {\n"
            "            intent?.data = null\n"
            "            intent?.clipData = null\n"
            "            intent?.action = Intent.ACTION_MAIN\n"
            "            return\n"
            "        }\n"
            "        val appUrl = (intent?.dataString ?: intent?.getStringExtra(LinkActivity.EXTRA_LINK))?.trim().orEmpty()\n"
            "        if (appUrl.isBlank()) return\n"
            "        handleAppUrl(appUrl)\n"
            "    }\n\n"
            "    private fun handleIncomingVideoFileIntent(intent: Intent?): Boolean {\n"
            "        if (intent == null) return false\n"
            "        val action = intent.action ?: return false\n"
            "        val uri = when (action) {\n"
            "            Intent.ACTION_VIEW -> intent.data ?: intent.clipData?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.uri\n"
            "            Intent.ACTION_SEND -> {\n"
            "                @Suppress(\"DEPRECATION\")\n"
            "                (intent.getParcelableExtra(Intent.EXTRA_STREAM) as? android.net.Uri)\n"
            "                    ?: intent.clipData?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.uri\n"
            "            }\n"
            "            else -> null\n"
            "        } ?: return false\n\n"
            "        val scheme = uri.scheme?.lowercase() ?: return false\n"
            "        if (scheme != \"content\" && scheme != \"file\") return false\n\n"
            "        val mime = intent.type?.takeIf { it.isNotBlank() }\n"
            "            ?: runCatching { contentResolver.getType(uri) }.getOrNull()\n"
            "        val displayName = LocalFolderVideosPlatform.resolveDisplayName(applicationContext, uri)\n"
            "        val ext = displayName.substringAfterLast('.', \"\").lowercase()\n"
            "        val looksLikeVideo = mime?.startsWith(\"video/\", ignoreCase = true) == true ||\n"
            "            mime.equals(\"application/mp4\", ignoreCase = true) ||\n"
            "            mime.equals(\"application/x-matroska\", ignoreCase = true) ||\n"
            "            mime.equals(\"application/vnd.apple.mpegurl\", ignoreCase = true) ||\n"
            "            mime.equals(\"application/x-mpegurl\", ignoreCase = true) ||\n"
            "            mime.equals(\"application/ogg\", ignoreCase = true) ||\n"
            "            ext in setOf(\n"
            "                \"mp4\", \"mkv\", \"avi\", \"webm\", \"mov\", \"m4v\", \"ts\", \"m2ts\",\n"
            "                \"mts\", \"flv\", \"wmv\", \"3gp\", \"mpg\", \"mpeg\", \"ogv\", \"vob\", \"m3u8\",\n"
            "            )\n"
            "        if (!looksLikeVideo) return false\n\n"
            "        if (scheme == \"content\" && (intent.flags and Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION) != 0) {\n"
            "            runCatching {\n"
            "                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)\n"
            "            }\n"
            "        }\n"
            "        AppDeepLinkRepository.openLocalVideo(\n"
            "            uri = uri.toString(),\n"
            "            title = LocalFolderVideosPlatform.cleanVideoTitle(displayName),\n"
            "            filename = displayName,\n"
            "            subtitle = \"Local Storage\",\n"
            "            mimeType = mime,\n"
            "        )\n"
            "        return true\n"
            "    }\n",
            "MainActivity handleIncomingVideoFileIntent",
        )
        if changed:
            patched.append(str(main_act.relative_to(root)))

    # 6. MainAppContent.kt: Observe pendingLocalVideo and open Nuvio built-in PlayerRoute
    main_app = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"
    if main_app.is_file():
        changed = False
        changed |= _replace_once(
            main_app,
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n",
            "import com.nuvio.app.core.deeplink.AppDeepLinkRepository\n"
            "import com.nuvio.app.core.deeplink.LocalVideoLaunchRequest\n",
            "MainAppContent LocalVideoLaunchRequest import",
        )
        changed |= _replace_once(
            main_app,
            "            val launchId = PlayerLaunchStore.put(playerLaunch)\n"
            "            navController.navigate(PlayerRoute(launchId = launchId, title = playerLaunch.title))\n"
            "        }\n",
            "            val launchId = PlayerLaunchStore.put(playerLaunch)\n"
            "            navController.navigate(PlayerRoute(launchId = launchId, title = playerLaunch.title))\n"
            "        }\n\n"
            "        fun openLocalVideo(req: LocalVideoLaunchRequest) {\n"
            "            val syntheticId = \"local:${req.uri.hashCode().toUInt().toString(16)}\"\n"
            "            val resumeEntry = WatchProgressRepository.progressForVideo(syntheticId)\n"
            "                ?.takeIf { it.isResumable }\n"
            "            val cleanMime = req.mimeType\n"
            "                ?.trim()\n"
            "                ?.takeIf { it.isNotEmpty() && !it.endsWith(\"/*\") }\n"
            "            val playerLaunch = PlayerLaunch(\n"
            "                profileId = activePlaybackProfileId,\n"
            "                title = req.title,\n"
            "                sourceUrl = req.uri,\n"
            "                externalSubtitles = DownloadSubtitles.localSubtitles(req.uri),\n"
            "                streamType = cleanMime,\n"
            "                streamTitle = req.filename ?: req.title,\n"
            "                streamSubtitle = req.subtitle ?: \"Local Storage\",\n"
            "                providerName = \"Local Storage\",\n"
            "                contentType = \"movie\",\n"
            "                videoId = syntheticId,\n"
            "                parentMetaId = syntheticId,\n"
            "                parentMetaType = \"movie\",\n"
            "                sourceFilename = req.filename,\n"
            "                initialPositionMs = resumeEntry?.lastPositionMs?.takeIf { it > 0L } ?: 0L,\n"
            "                initialProgressFraction = resumeEntry?.progressFraction?.takeIf { it > 0f },\n"
            "            )\n"
            "            val launchId = PlayerLaunchStore.put(playerLaunch)\n"
            "            navController.navigate(PlayerRoute(launchId = launchId, title = playerLaunch.title))\n"
            "        }\n\n"
            "        LaunchedEffect(navController, ownsAppRuntime) {\n"
            "            if (!ownsAppRuntime) return@LaunchedEffect\n"
            "            AppDeepLinkRepository.pendingLocalVideo.collect { req ->\n"
            "                if (req == null) return@collect\n"
            "                AppDeepLinkRepository.markLocalVideoConsumed(req)\n"
            "                openLocalVideo(req)\n"
            "            }\n"
            "        }\n",
            "MainAppContent openLocalVideo & pendingLocalVideo collector",
        )
        if changed:
            patched.append(str(main_app.relative_to(root)))

    # 7. PlaybackMediaItems.android.kt: Fallback to contentResolver.getType(uri) when header sniffing doesn't match
    media_items = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlaybackMediaItems.android.kt"
    if media_items.is_file():
        changed = _replace_once(
            media_items,
            "private fun sniffLocalMimeType(url: String): String? {\n"
            "    val header = readLocalHeaderBytes(url) ?: return null\n"
            "    return mimeTypeFromHeader(header)\n"
            "}\n",
            "private fun sniffLocalMimeType(url: String): String? {\n"
            "    val header = readLocalHeaderBytes(url)\n"
            "    if (header != null) {\n"
            "        mimeTypeFromHeader(header)?.let { return it }\n"
            "    }\n"
            "    return runCatching {\n"
            "        val uri = Uri.parse(url)\n"
            "        if (uri.scheme?.equals(\"content\", ignoreCase = true) == true) {\n"
            "            val context = PlayerSettingsStorage.applicationContext() ?: return@runCatching null\n"
            "            val resolverType = context.contentResolver.getType(uri)?.trim()\n"
            "            normalizeMimeType(resolverType)\n"
            "                ?: resolverType?.takeIf { it.startsWith(\"video/\", ignoreCase = true) && !it.endsWith(\"/*\") }\n"
            "        } else {\n"
            "            null\n"
            "        }\n"
            "    }.getOrNull()\n"
            "}\n",
            "PlaybackMediaItems sniffLocalMimeType contentResolver fallback",
        )
        if changed:
            patched.append(str(media_items.relative_to(root)))

    return patched
