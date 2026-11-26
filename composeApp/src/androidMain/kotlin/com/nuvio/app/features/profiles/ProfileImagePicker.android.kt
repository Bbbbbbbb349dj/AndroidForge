package com.nuvio.app.features.profiles

import android.content.Context
import android.net.Uri
import android.webkit.MimeTypeMap
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
internal actual fun rememberProfileImagePicker(
    onPicked: (fileUri: String) -> Unit,
    onError: (String) -> Unit,
): () -> Unit {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val currentOnPicked = rememberUpdatedState(onPicked)
    val currentOnError = rememberUpdatedState(onError)
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            val stored = withContext(Dispatchers.IO) {
                runCatching { copyToProfileImages(context, uri) }
            }
            stored
                .onSuccess { currentOnPicked.value(it) }
                .onFailure { error -> currentOnError.value(error.message ?: "Failed to load the selected image") }
        }
    }
    return remember(launcher) {
        {
            launcher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
        }
    }
}

private fun copyToProfileImages(context: Context, uri: Uri): String {
    val mime = context.contentResolver.getType(uri)
    val extension = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime) ?: "jpg"
    val directory = File(context.filesDir, "profile_images").apply { mkdirs() }
    val target = File(directory, "img-${System.currentTimeMillis()}.$extension")
    context.contentResolver.openInputStream(uri)?.use { input ->
        target.outputStream().use { output -> input.copyTo(output) }
    } ?: error("Unable to read the selected image")
    return "file://${target.absolutePath}"
}
