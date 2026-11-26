package com.nuvio.app.features.profiles

import androidx.compose.runtime.Composable

/**
 * Opens the platform gallery and hands back a persisted `file://` URI for the picked image
 * (Nuvio Enhanced: custom profile avatar / backdrop from the device gallery).
 */
@Composable
internal expect fun rememberProfileImagePicker(
    onPicked: (fileUri: String) -> Unit,
    onError: (String) -> Unit,
): () -> Unit
