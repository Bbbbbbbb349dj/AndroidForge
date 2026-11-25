#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 5: Profile Enhancements (Section 12).

  - `isValidAvatarUrl()` accepts `file://` URIs (gallery-picked images).
  - Deduplicates the two mirrored custom-backdrop input fields in `ProfileEditScreen`.
  - Built-in offline avatar palette (`builtInAvatarCatalog()`), available without network.
  - Gallery pickers for avatar + backdrop (`rememberProfileImagePicker` expect/actual)
    returning persisted `file://` URIs.
  - `usesPrimaryPlugins` gains a save path + edit-screen toggle (field existed, no UI).
  - Biometric/PIN unlock works on EVERY profile instead of only `profileIndex == 1`.
  - `AppBackgroundRepository.reload()` runs on profile switch so the background follows.
"""
from __future__ import annotations

from pathlib import Path

NEW_PICKER_COMMON = """package com.nuvio.app.features.profiles

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
"""

NEW_PICKER_ANDROID = """package com.nuvio.app.features.profiles

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
"""

NEW_PICKER_IOS = """package com.nuvio.app.features.profiles

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
"""


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 profiles] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 profiles] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_models(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/profiles/ProfileModels.kt"
    _replace_once(
        path,
        """fun String.isValidAvatarUrl(): Boolean {
    val value = trim()
    return value.length <= 2048 &&
        !value.any { it.isWhitespace() } &&
        (value.startsWith("https://") || value.startsWith("http://"))
}""",
        """fun String.isValidAvatarUrl(): Boolean {
    val value = trim()
    return value.length <= 2048 &&
        !value.any { it.isWhitespace() } &&
        (value.startsWith("https://") || value.startsWith("http://") || value.startsWith("file://"))
}""",
        "isValidAvatarUrl file:// support",
    )

    _replace_once(
        path,
        """val PROFILE_COLORS = listOf(""",
        """/**
 * Built-in offline avatar palette (Nuvio Enhanced): color-circle avatars that render
 * without any network catalog, so profile editing works fully offline.
 */
fun builtInAvatarCatalog(): List<AvatarCatalogItem> = listOf(
    "builtin-aurora" to "#00ACC1",
    "builtin-flame" to "#F4511E",
    "builtin-forest" to "#43A047",
    "builtin-violet" to "#8E24AA",
    "builtin-sun" to "#FB8C00",
    "builtin-rose" to "#D81B60",
    "builtin-ocean" to "#3949AB",
    "builtin-lime" to "#C0CA33",
).mapIndexed { index, (id, color) ->
    AvatarCatalogItem(
        id = id,
        displayName = id.substringAfter("builtin-").replaceFirstChar { it.uppercase() },
        storagePath = "",
        category = "builtin",
        sortOrder = index,
        bgColor = color,
    )
}

val PROFILE_COLORS = listOf(""",
        "builtInAvatarCatalog()",
    )


def _patch_repository(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/profiles/ProfileRepository.kt"

    _replace_once(
        path,
        """    fun selectProfile(profileIndex: Int) {
        activeProfileIndex = profileIndex
        CustomPosterUrlRepository.onProfileChanged()""",
        """    fun selectProfile(profileIndex: Int) {
        activeProfileIndex = profileIndex
        CustomPosterUrlRepository.onProfileChanged()
        com.nuvio.app.core.ui.background.AppBackgroundRepository.reload()""",
        "reload app background on switch",
    )

    _replace_once(
        path,
        """        profileBackgroundId: String? = null,
        profileBackgroundUrl: String? = null,
        usesPrimaryAddons: Boolean = false,
    ) {
        val existing = _state.value.profiles""",
        """        profileBackgroundId: String? = null,
        profileBackgroundUrl: String? = null,
        usesPrimaryAddons: Boolean = false,
        usesPrimaryPlugins: Boolean = false,
    ) {
        val existing = _state.value.profiles""",
        "createProfile plugins param",
    )

    _replace_once(
        path,
        """        } + ProfilePushPayload(
            profileIndex = nextIndex,
            name = name,
            avatarColorHex = avatarColorHex,
            usesPrimaryAddons = usesPrimaryAddons,
            avatarId = avatarId,""",
        """        } + ProfilePushPayload(
            profileIndex = nextIndex,
            name = name,
            avatarColorHex = avatarColorHex,
            usesPrimaryAddons = usesPrimaryAddons,
            usesPrimaryPlugins = usesPrimaryPlugins,
            avatarId = avatarId,""",
        "createProfile new payload plugins",
    )

    _replace_once(
        path,
        """        profileBackgroundId: String? = null,
        profileBackgroundUrl: String? = null,
        usesPrimaryAddons: Boolean = false,
    ) {
        val allPayloads = _state.value.profiles.map { profile ->""",
        """        profileBackgroundId: String? = null,
        profileBackgroundUrl: String? = null,
        usesPrimaryAddons: Boolean = false,
        usesPrimaryPlugins: Boolean = false,
    ) {
        val allPayloads = _state.value.profiles.map { profile ->""",
        "updateProfile plugins param",
    )

    _replace_once(
        path,
        """                ProfilePushPayload(
                    profileIndex = profileIndex,
                    name = name,
                    avatarColorHex = avatarColorHex,
                    usesPrimaryAddons = usesPrimaryAddons,
                    avatarId = avatarId,""",
        """                ProfilePushPayload(
                    profileIndex = profileIndex,
                    name = name,
                    avatarColorHex = avatarColorHex,
                    usesPrimaryAddons = usesPrimaryAddons,
                    usesPrimaryPlugins = usesPrimaryPlugins,
                    avatarId = avatarId,""",
        "updateProfile edited payload plugins",
    )


def _patch_edit_screen(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/profiles/ProfileEditScreen.kt"

    _replace_once(
        path,
        """import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults""",
        """import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import com.nuvio.app.core.ui.NuvioToastController""",
        "NuvioToastController import",
    )

    _replace_once(
        path,
        """    val avatars by AvatarRepository.avatars.collectAsStateWithLifecycle()""",
        """    val remoteAvatars by AvatarRepository.avatars.collectAsStateWithLifecycle()
    val avatars = remember(remoteAvatars) { builtInAvatarCatalog() + remoteAvatars }""",
        "offline built-in avatars merged",
    )

    _replace_once(
        path,
        """    var usesPrimaryAddons by rememberSaveable { mutableStateOf(currentProfile?.usesPrimaryAddons ?: false) }""",
        """    var usesPrimaryAddons by rememberSaveable { mutableStateOf(currentProfile?.usesPrimaryAddons ?: false) }
    var usesPrimaryPlugins by rememberSaveable { mutableStateOf(currentProfile?.usesPrimaryPlugins ?: false) }""",
        "usesPrimaryPlugins state",
    )

    _replace_once(
        path,
        """                        usesPrimaryAddons = usesPrimaryAddons,
                    )
                } else {""",
        """                        usesPrimaryAddons = usesPrimaryAddons,
                        usesPrimaryPlugins = usesPrimaryPlugins,
                    )
                } else {""",
        "createProfile call plugins",
    )

    _replace_once(
        path,
        """                        usesPrimaryAddons = usesPrimaryAddons,
                    )
                }
                onSaved()""",
        """                        usesPrimaryAddons = usesPrimaryAddons,
                        usesPrimaryPlugins = usesPrimaryPlugins,
                    )
                }
                onSaved()""",
        "updateProfile call plugins",
    )

    _replace_once(
        path,
        """                usesPrimaryAddons = usesPrimaryAddons,
                onNameChange = { name = it },
                onUsesPrimaryAddonsChange = { usesPrimaryAddons = it },""",
        """                usesPrimaryAddons = usesPrimaryAddons,
                onNameChange = { name = it },
                onUsesPrimaryAddonsChange = { usesPrimaryAddons = it },
                usesPrimaryPlugins = usesPrimaryPlugins,
                onUsesPrimaryPluginsChange = { usesPrimaryPlugins = it },""",
        "ProfileIdentityCard call plugins",
    )

    _replace_once(
        path,
        """    usesPrimaryAddons: Boolean,
    onNameChange: (String) -> Unit,
    onUsesPrimaryAddonsChange: (Boolean) -> Unit,""",
        """    usesPrimaryAddons: Boolean,
    usesPrimaryPlugins: Boolean,
    onNameChange: (String) -> Unit,
    onUsesPrimaryAddonsChange: (Boolean) -> Unit,
    onUsesPrimaryPluginsChange: (Boolean) -> Unit,""",
        "ProfileIdentityCard signature plugins",
    )

    _replace_once(
        path,
        """            ProfileOptionRow(
                title = stringResource(Res.string.profile_use_primary_addons),
                description = stringResource(Res.string.profile_use_primary_addons_description),
                checked = usesPrimaryAddons,
                onCheckedChange = onUsesPrimaryAddonsChange,
            )
        }
    }
}""",
        """            ProfileOptionRow(
                title = stringResource(Res.string.profile_use_primary_addons),
                description = stringResource(Res.string.profile_use_primary_addons_description),
                checked = usesPrimaryAddons,
                onCheckedChange = onUsesPrimaryAddonsChange,
            )
            ProfileOptionRow(
                title = stringResource(Res.string.profile_use_primary_plugins),
                description = stringResource(Res.string.profile_use_primary_plugins_description),
                checked = usesPrimaryPlugins,
                onCheckedChange = onUsesPrimaryPluginsChange,
            )
        }
    }
}""",
        "ProfileOptionRow plugins toggle",
    )

    # PIN/biometric: available for every profile (was primary-only).
    _replace_once(
        path,
        """                    currentProfile?.profileIndex == 1 && (platformAvailable || biometricConfigured)""",
        """                    platformAvailable || biometricConfigured""",
        "pin/biometric all profiles",
    )

    # Backdrop dedupe: remove the mirrored custom-URL input inside the picker card;
    # the dedicated "Custom background URL" card below remains the single editor.
    _replace_once(
        path,
        """                            onSelectionChange = { id, url ->
                                selectedBackgroundId = id
                                selectedBackgroundUrl = url
                                if (url != null) {
                                    customBackgroundUrlInput = url
                                } else if (id != null) {
                                    customBackgroundUrlInput = ""
                                }
                            },
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = stringResource(Res.string.profile_background_custom),
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                        NuvioInputField(
                            value = customBackgroundUrlInput,
                            onValueChange = { value ->
                                customBackgroundUrlInput = value
                                if (value.isNotBlank()) {
                                    selectedBackgroundId = null
                                    selectedBackgroundUrl = value
                                } else {
                                    if (selectedBackgroundUrl != null && selectedBackgroundId == null) {
                                        selectedBackgroundUrl = null
                                    }
                                }
                            },
                            placeholder = "https://example.com/background.jpg",
                        )
                    }
                }
            }
        }""",
        """                            onSelectionChange = { id, url ->
                                selectedBackgroundId = id
                                selectedBackgroundUrl = url
                                if (url != null) {
                                    customBackgroundUrlInput = url
                                } else if (id != null) {
                                    customBackgroundUrlInput = ""
                                }
                            },
                        )
                    }
                }
            }
        }""",
        "remove duplicated backdrop input row",
    )

    _replace_once(
        path,
        """    Box(modifier = modifier.fillMaxSize()) {
    NuvioScreen {""",
        """    val pickAvatarImage = rememberProfileImagePicker(
        onPicked = { uri ->
            avatarUrl = uri
            selectedAvatarId = null
        },
        onError = { message -> NuvioToastController.show(message) },
    )
    val pickBackgroundImage = rememberProfileImagePicker(
        onPicked = { uri ->
            selectedBackgroundId = null
            selectedBackgroundUrl = uri
            customBackgroundUrlInput = uri
        },
        onError = { message -> NuvioToastController.show(message) },
    )

    Box(modifier = modifier.fillMaxSize()) {
    NuvioScreen {""",
        "gallery picker hooks",
    )

    _replace_once(
        path,
        """                    if (avatarUrlIsInvalid) {
                        Text(
                            text = stringResource(Res.string.profile_avatar_url_invalid),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }""",
        """                    if (avatarUrlIsInvalid) {
                        Text(
                            text = stringResource(Res.string.profile_avatar_url_invalid),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                    Button(onClick = pickAvatarImage) {
                        Text(text = stringResource(Res.string.profile_choose_from_gallery))
                    }
                }""",
        "avatar gallery button",
    )

    _replace_once(
        path,
        """                        if (customBackgroundUrlIsInvalid) {
                            Text(
                                text = stringResource(Res.string.profile_background_url_invalid),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                    }""",
        """                        if (customBackgroundUrlIsInvalid) {
                            Text(
                                text = stringResource(Res.string.profile_background_url_invalid),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                        Button(onClick = pickBackgroundImage) {
                            Text(text = stringResource(Res.string.profile_choose_from_gallery))
                        }
                    }""",
        "background gallery button",
    )


def _patch_strings(root: Path) -> None:
    path = root / "composeApp/src/commonMain/composeResources/values/strings.xml"
    _replace_once(
        path,
        """    <string name="layout_rating_map_position">Rating Map Position</string>""",
        """    <string name="layout_rating_map_position">Rating Map Position</string>
    <string name="profile_use_primary_plugins">Use primary profile plugins</string>
    <string name="profile_use_primary_plugins_description">Share the primary profile's installed plugins with this profile.</string>
    <string name="profile_choose_from_gallery">Choose from gallery</string>""",
        "profile strings",
    )


def _patch_new_picker_files(root: Path) -> None:
    files = {
        "composeApp/src/commonMain/kotlin/com/nuvio/app/features/profiles/ProfileImagePicker.kt": NEW_PICKER_COMMON,
        "composeApp/src/androidMain/kotlin/com/nuvio/app/features/profiles/ProfileImagePicker.android.kt": NEW_PICKER_ANDROID,
        "composeApp/src/iosMain/kotlin/com/nuvio/app/features/profiles/ProfileImagePicker.ios.kt": NEW_PICKER_IOS,
    }
    for rel, content in files.items():
        target = root / rel
        if target.exists() and target.read_text(encoding="utf-8") == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def apply_v120_profiles_patch(source_dir: Path) -> None:
    _patch_models(source_dir)
    _patch_repository(source_dir)
    _patch_strings(source_dir)
    _patch_edit_screen(source_dir)
    _patch_new_picker_files(source_dir)
    print("[v1.20-module-6] Profile file:// avatars, offline avatars, plugins toggle & PIN for all profiles applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_profiles_patch.py <source_dir>")
    apply_v120_profiles_patch(Path(sys.argv[1]).resolve())
