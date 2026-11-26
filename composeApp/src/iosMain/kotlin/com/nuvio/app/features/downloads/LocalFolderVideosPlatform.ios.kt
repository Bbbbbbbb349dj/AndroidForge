package com.nuvio.app.features.downloads

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
