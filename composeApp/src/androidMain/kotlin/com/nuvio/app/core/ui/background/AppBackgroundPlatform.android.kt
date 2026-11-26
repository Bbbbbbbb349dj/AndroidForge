package com.nuvio.app.core.ui.background

import android.content.Context
import android.content.SharedPreferences
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
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
import coil3.request.ImageRequest
import coil3.request.allowHardware
import com.nuvio.app.core.storage.ProfileScopedKey
import java.io.ByteArrayInputStream
import java.io.File
import java.io.InputStream
import kotlin.math.max
import kotlin.math.roundToInt
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

internal actual object AppBackgroundStorage {
    private const val preferencesName = "nuvio_app_background"
    private const val configKey = "enhanced_local_app_background"
    private const val directoryName = "app_background"

    private var preferences: SharedPreferences? = null
    private var filesDir: File? = null

    fun initialize(context: Context) {
        val appContext = context.applicationContext
        preferences = appContext.getSharedPreferences(preferencesName, Context.MODE_PRIVATE)
        filesDir = appContext.filesDir
    }

    actual fun load(): String? = preferences?.getString(ProfileScopedKey.of(configKey), null)

    actual fun save(value: String) {
        preferences?.edit()?.putString(ProfileScopedKey.of(configKey), value)?.apply()
    }

    internal fun directory(): File? = filesDir?.let { File(it, directoryName) }

    actual fun localFilePath(fileName: String): String =
        File(directory() ?: File(directoryName), fileName).absolutePath

    actual fun deleteLocalFile(fileName: String) {
        directory()?.let { File(it, fileName).delete() }
    }
}

internal actual fun ImageRequest.Builder.softwareBitmap(): ImageRequest.Builder = allowHardware(false)

/**
 * Copies a picked background into app storage, preserving animated GIF/WebP bytes
 * and downsampling EXIF-rotated static images to [MAX_DIMENSION]px on the long edge.
 */
internal object AppBackgroundImageProcessor {
    private const val MAX_DIMENSION = 2560

    fun write(input: InputStream, output: File, mime: String) {
        val bytes = input.readBytes()
        if (mime == "image/gif" || (mime == "image/webp" && looksAnimatedWebp(bytes))) {
            // Animated formats must keep their original bytes (re-encoding strips frames).
            output.outputStream().use { it.write(bytes) }
            return
        }

        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        val orientation = runCatching {
            ExifInterface(ByteArrayInputStream(bytes)).getAttributeInt(
                ExifInterface.TAG_ORIENTATION,
                ExifInterface.ORIENTATION_NORMAL,
            )
        }.getOrDefault(ExifInterface.ORIENTATION_NORMAL)
        // Rotation never changes the long edge, so max(width, height) is stable.
        val longEdge = max(bounds.outWidth, bounds.outHeight)
        if (orientation == ExifInterface.ORIENTATION_NORMAL && longEdge in 1..MAX_DIMENSION) {
            output.outputStream().use { it.write(bytes) }
            return
        }

        val options = BitmapFactory.Options().apply {
            inSampleSize = sampleSize(bounds.outWidth, bounds.outHeight)
        }
        var bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options)
            ?: run {
                output.outputStream().use { it.write(bytes) }
                return
            }

        val matrix = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.postScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.postScale(1f, -1f)
            ExifInterface.ORIENTATION_TRANSPOSE -> {
                matrix.postRotate(90f)
                matrix.postScale(-1f, 1f)
            }
            ExifInterface.ORIENTATION_TRANSVERSE -> {
                matrix.postRotate(270f)
                matrix.postScale(-1f, 1f)
            }
        }
        if (!matrix.isIdentity) {
            val rotated = runCatching {
                Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
            }.getOrNull()
            if (rotated != null && rotated != bitmap) {
                bitmap.recycle()
                bitmap = rotated
            }
        }

        val longEdgeNow = max(bitmap.width, bitmap.height)
        if (longEdgeNow > MAX_DIMENSION) {
            val scale = MAX_DIMENSION.toFloat() / longEdgeNow
            val scaled = Bitmap.createScaledBitmap(
                bitmap,
                (bitmap.width * scale).roundToInt().coerceAtLeast(1),
                (bitmap.height * scale).roundToInt().coerceAtLeast(1),
                true,
            )
            if (scaled != bitmap) {
                bitmap.recycle()
                bitmap = scaled
            }
        }

        val format = if (mime == "image/png") Bitmap.CompressFormat.PNG else Bitmap.CompressFormat.JPEG
        output.outputStream().use { stream ->
            bitmap.compress(format, if (format == Bitmap.CompressFormat.PNG) 100 else 92, stream)
        }
        bitmap.recycle()
    }

    private fun sampleSize(width: Int, height: Int): Int {
        if (width <= 0 || height <= 0) return 1
        var sample = 1
        while (max(width, height) / sample > MAX_DIMENSION) {
            sample *= 2
        }
        return sample
    }

    private fun looksAnimatedWebp(bytes: ByteArray): Boolean {
        if (bytes.size < 16) return false
        val header = String(bytes, 0, minOf(bytes.size, 64), Charsets.US_ASCII)
        return header.startsWith("RIFF") && "WEBP" in header && "ANIM" in header
    }
}

@Composable
internal actual fun rememberAppBackgroundImagePicker(
    onPicked: (fileName: String) -> Unit,
    onError: (String) -> Unit,
): () -> Unit {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val currentOnPicked = rememberUpdatedState(onPicked)
    val currentOnError = rememberUpdatedState(onError)
    remember(context) { AppBackgroundStorage.initialize(context) }

    fun handle(uri: Uri?) {
        if (uri == null) return
        scope.launch {
            val stored = withContext(Dispatchers.IO) {
                runCatching {
                    AppBackgroundStorage.initialize(context)
                    val mime = context.contentResolver.getType(uri)
                    val extension = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime) ?: "jpg"
                    val directory = AppBackgroundStorage.directory()?.apply { mkdirs() }
                        ?: error("Storage unavailable")
                    val name = "bg-${System.currentTimeMillis()}.$extension"
                    context.contentResolver.openInputStream(uri)?.use { input ->
                        AppBackgroundImageProcessor.write(input, File(directory, name), mime ?: "")
                    } ?: error("Unable to read the selected image")
                    name
                }
            }
            stored
                .onSuccess { currentOnPicked.value(it) }
                .onFailure { currentOnError.value(it.message ?: "Failed to load the selected image") }
        }
    }

    val mediaLauncher = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        handle(uri)
    }
    val documentLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        handle(uri)
    }
    val usePhotoPicker = remember(context) {
        runCatching {
            ActivityResultContracts.PickVisualMedia.isPhotoPickerAvailable(context)
        }.getOrDefault(false)
    }
    return remember(mediaLauncher, documentLauncher, usePhotoPicker) {
        {
            if (usePhotoPicker) {
                mediaLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            } else {
                // Fallback for devices without the system Photo Picker.
                documentLauncher.launch(arrayOf("image/*"))
            }
        }
    }
}
