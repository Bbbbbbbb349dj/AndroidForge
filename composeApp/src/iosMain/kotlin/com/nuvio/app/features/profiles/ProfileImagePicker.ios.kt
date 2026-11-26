package com.nuvio.app.features.profiles

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember

@Composable
internal actual fun rememberProfileImagePicker(
    onPicked: (fileUri: String) -> Unit,
    onError: (String) -> Unit,
): () -> Unit {
    return remember {
        { onError("Gallery picker is not available on this platform") }
    }
}
