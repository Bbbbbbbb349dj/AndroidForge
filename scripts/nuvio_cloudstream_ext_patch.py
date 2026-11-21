#!/usr/bin/env python3
"""CloudStream SyncProviders Host ABI & Universal Extension Settings Workaround."""
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


def apply_cloudstream_ext_patch(root: Path) -> list[str]:
    patched: list[str] = []

    # 1. Update CloudStreamApp.kt to include openBrowser overloads used by AuthRepo & plugin settings
    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/CloudStreamApp.kt",
        r'''package com.lagradost.cloudstream3

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.net.Uri
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import com.lagradost.cloudstream3.ui.settings.Globals
import com.lagradost.cloudstream3.utils.AppContextUtils.openBrowser
import com.lagradost.cloudstream3.utils.DataStore
import java.lang.ref.WeakReference

/** Host-context and preference ABI used by CloudStream extensions. */
class CloudStreamApp {
    companion object {
        private var contextReference: WeakReference<Context>? = null

        var context: Context?
            get() = contextReference?.get()
            set(value) {
                contextReference = value?.let(::WeakReference)
                if (value != null) com.lagradost.api.setContext(WeakReference(value as Any))
            }

        tailrec fun Context.getActivity(): Activity? = when (this) {
            is Activity -> this
            is ContextWrapper -> baseContext.getActivity()
            else -> null
        }

        fun <T : Any> getKeyClass(path: String, valueType: Class<T>): T? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.getKey(path, valueType) }
            }
        }

        fun <T : Any> setKeyClass(path: String, value: T) {
            setKey(path, value)
        }

        inline fun <reified T : Any> getKey(path: String): T? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.getKey<T>(path) }
            }
        }

        inline fun <reified T : Any> getKey(path: String, defVal: T?): T? {
            return getKey<T>(path) ?: defVal
        }

        inline fun <reified T : Any> getKey(folder: String, path: String): T? {
            return getKey<T>(DataStore.getFolderName(folder, path))
        }

        inline fun <reified T : Any> getKey(folder: String, path: String, defVal: T?): T? {
            return getKey<T>(folder, path) ?: defVal
        }

        fun <T> setKey(path: String, value: T) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.setKey(path, value) }
            }
        }

        fun <T> setKey(folder: String, path: String, value: T) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.setKey(folder, path, value) }
            }
        }

        fun removeKey(path: String) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.removeKey(path) }
            }
        }

        fun removeKey(folder: String, path: String) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.removeKey(folder, path) }
            }
        }

        fun removeKeys(folder: String): Int? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.removeKeys(folder) }
            }
        }

        fun getKeys(folder: String): List<String>? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.getKeys(folder) }
            }
        }

        fun openBrowser(url: String, fallbackWebView: Boolean = false, fragment: Fragment? = null) {
            val target = CommonActivity.activity ?: context
            if (target != null) {
                target.openBrowser(url, fallbackWebView, fragment)
            } else {
                runCatching {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context?.startActivity(intent)
                }
            }
        }

        fun openBrowser(url: String, activity: Activity?) {
            openBrowser(
                url,
                Globals.isLayout(Globals.TV or Globals.EMULATOR),
                (activity as? FragmentActivity)?.supportFragmentManager?.fragments?.lastOrNull(),
            )
        }
    }
}
''',
        patched,
    )

    # 2. Subtitles entities & UI enums/globals required by SyncAPI & SubtitleAPI
    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/subtitles/SubtitlesCompat.kt",
        r'''package com.lagradost.cloudstream3.subtitles

import com.lagradost.cloudstream3.TvType

object AbstractSubtitleEntities {
    data class SubtitleEntity(
        var idPrefix: String,
        var name: String,
        var lang: String,
        var data: String,
        var type: TvType = TvType.Movie,
        var source: String = idPrefix,
        var epNumber: Int? = null,
        var seasonNumber: Int? = null,
        var year: Int? = null,
        var isHearingImpaired: Boolean = false,
    )

    data class SubtitleSearch(
        var query: String,
        var imdbId: String? = null,
        var tmdbId: Int? = null,
        var malId: Int? = null,
        var aniListId: Int? = null,
        var lang: String? = null,
        var epNumber: Int? = null,
        var seasonNumber: Int? = null,
        var year: Int? = null,
    )
}

class SubtitleResource {
    val subtitles: MutableList<String> = mutableListOf()

    fun addUrl(url: String?) {
        if (!url.isNullOrBlank()) {
            subtitles += url
        }
    }
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/ui/WatchType.kt",
        r'''package com.lagradost.cloudstream3.ui

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes

enum class WatchType(val internalId: Int, @StringRes val stringRes: Int, @DrawableRes val iconRes: Int) {
    WATCHING(0, 0, 0),
    COMPLETED(1, 0, 0),
    ONHOLD(2, 0, 0),
    DROPPED(3, 0, 0),
    PLANTOWATCH(4, 0, 0),
    NONE(5, 0, 0);

    companion object {
        fun fromInternalId(id: Int?) = entries.find { value -> value.internalId == id } ?: NONE
    }
}

enum class SyncWatchType(val internalId: Int, @StringRes val stringRes: Int, @DrawableRes val iconRes: Int) {
    NONE(-1, 0, 0),
    WATCHING(0, 0, 0),
    COMPLETED(1, 0, 0),
    ONHOLD(2, 0, 0),
    DROPPED(3, 0, 0),
    PLANTOWATCH(4, 0, 0),
    REWATCHING(5, 0, 0);

    companion object {
        fun fromInternalId(id: Int?) = entries.find { value -> value.internalId == id } ?: NONE
    }
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/ui/library/ListSorting.kt",
        r'''package com.lagradost.cloudstream3.ui.library

enum class ListSorting {
    Default,
    Query,
    RatingHigh,
    RatingLow,
    AlphabeticalA,
    AlphabeticalZ,
    UpdatedNew,
    UpdatedOld,
    ReleaseDateNew,
    ReleaseDateOld,
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/ui/settings/Globals.kt",
        r'''package com.lagradost.cloudstream3.ui.settings

import android.content.Context
import android.content.res.Configuration
import android.content.res.Resources

object Globals {
    var beneneCount = 0

    const val PHONE: Int = 0b00001
    const val TV: Int = 0b00010
    const val EMULATOR: Int = 0b00100
    private var layoutId: Int = PHONE

    fun Context.updateTv() {
        val uiMode = resources?.configuration?.uiMode ?: 0
        layoutId = if ((uiMode and Configuration.UI_MODE_TYPE_MASK) == Configuration.UI_MODE_TYPE_TELEVISION) {
            TV
        } else {
            PHONE
        }
    }

    fun isLandscape(): Boolean =
        isLayout(TV or EMULATOR) ||
            Resources.getSystem().configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    fun isLayout(flags: Int): Boolean = (layoutId and flags) != 0
}
''',
        patched,
    )

    # 3. Host UI & Dialog utils (UiText, AppContextUtils, DataStoreHelper, UIHelper, SingleSelectionHelper)
    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/utils/CloudStreamHostUiUtils.kt",
        r'''package com.lagradost.cloudstream3.utils

import android.app.Activity
import android.app.Dialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.util.TypedValue
import android.view.Menu
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.PopupMenu
import androidx.annotation.AttrRes
import androidx.annotation.ColorInt
import androidx.annotation.StringRes
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.lagradost.cloudstream3.CloudStreamApp
import com.lagradost.cloudstream3.CommonActivity

sealed class UiText {
    data class DynamicString(val value: String) : UiText()
    class StringResource(@StringRes val resId: Int, vararg val args: Any) : UiText()

    fun asString(context: Context?): String = when (this) {
        is DynamicString -> value
        is StringResource -> {
            val ctx = context ?: CommonActivity.activity ?: CloudStreamApp.context
            runCatching { ctx?.getString(resId, *args) }.getOrNull() ?: ""
        }
    }
}

fun txt(value: String): UiText = UiText.DynamicString(value)
fun txt(@StringRes resId: Int, vararg args: Any): UiText = UiText.StringResource(resId, *args)

object DataStoreHelper {
    var currentAccount: String = "0"
}

object AppContextUtils {
    fun Context.openBrowser(url: String, fallbackWebView: Boolean = false, fragment: Fragment? = null) {
        val trimmed = url.trim()
        if (trimmed.isEmpty()) return
        runCatching {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(trimmed)).apply {
                if (this@openBrowser !is Activity) {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            }
            startActivity(intent)
        }.onFailure {
            CommonActivity.showToast("Could not open URL: $trimmed")
        }
    }
}

object UIHelper {
    fun Context.checkWrite(): Boolean = true
    fun Activity.requestRW() = Unit

    fun clipboardHelper(label: UiText, text: CharSequence) {
        val ctx = CommonActivity.activity ?: CloudStreamApp.context ?: return
        val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
        cm.setPrimaryClip(ClipData.newPlainText(label.asString(ctx), text))
    }

    fun Context.getSpanCount(isHorizontal: Boolean = false): Int = if (isHorizontal) 2 else 3

    fun Fragment.hideKeyboard() {
        hideKeyboard(view)
    }

    fun Activity.hideKeyboard() {
        hideKeyboard(currentFocus)
    }

    fun hideKeyboard(view: View?) {
        if (view == null) return
        val imm = view.context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.hideSoftInputFromWindow(view.windowToken, 0)
    }

    fun showInputMethod(view: View?) {
        if (view == null) return
        val imm = view.context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.showSoftInput(view, InputMethodManager.SHOW_IMPLICIT)
    }

    fun Context.getResourceColor(@AttrRes resource: Int, alphaFactor: Float = 1f): Int {
        val color = colorFromAttribute(resource)
        return if (alphaFactor < 1f) adjustAlpha(color, alphaFactor) else color
    }

    fun Context.colorFromAttribute(@AttrRes attribute: Int): Int {
        val typedValue = TypedValue()
        return if (theme.resolveAttribute(attribute, typedValue, true)) {
            typedValue.data
        } else {
            Color.WHITE
        }
    }

    fun adjustAlpha(@ColorInt color: Int, factor: Float): Int {
        val alpha = Math.round(Color.alpha(color) * factor)
        return Color.argb(alpha, Color.red(color), Color.green(color), Color.blue(color))
    }

    fun fixPaddingStatusbarMargin(v: View?) = Unit
    fun fixPaddingStatusbarView(v: View?) = Unit

    fun Dialog?.dismissSafe(activity: Activity?) {
        if (this == null) return
        if (activity != null && (activity.isFinishing || activity.isDestroyed)) return
        runCatching { if (isShowing) dismiss() }
    }

    fun Dialog?.dismissSafe() {
        if (this == null) return
        runCatching { if (isShowing) dismiss() }
    }

    fun View.popupMenuNoIcons(
        items: List<Pair<Int, Int>>,
        onMenuItemClick: android.view.MenuItem.() -> Unit,
    ): PopupMenu {
        val popup = PopupMenu(context, this)
        items.forEach { (id, stringRes) ->
            val label = runCatching { context.getString(stringRes) }.getOrDefault(id.toString())
            popup.menu.add(Menu.NONE, id, Menu.NONE, label)
        }
        popup.setOnMenuItemClickListener { item ->
            item.onMenuItemClick()
            true
        }
        popup.show()
        return popup
    }

    fun View.popupMenuNoIconsAndNoStringRes(
        items: List<Pair<Int, String>>,
        onMenuItemClick: android.view.MenuItem.() -> Unit,
    ): PopupMenu {
        val popup = PopupMenu(context, this)
        items.forEach { (id, title) ->
            popup.menu.add(Menu.NONE, id, Menu.NONE, title)
        }
        popup.setOnMenuItemClickListener { item ->
            item.onMenuItemClick()
            true
        }
        popup.show()
        return popup
    }
}

object SingleSelectionHelper {
    fun Activity?.showOptionSelectStringRes(
        view: View?,
        poster: String?,
        options: List<Int>,
        tvOptions: List<Int> = emptyList(),
        callback: (Pair<Boolean, Int>) -> Unit,
    ) {
        val act = this ?: CommonActivity.activity ?: return
        val labels = options.map { id -> runCatching { act.getString(id) }.getOrDefault(id.toString()) }
        act.showDialog(
            items = labels,
            selectedIndex = -1,
            name = "",
            showApply = false,
            dismissCallback = {},
            callback = { index -> callback(false to index) },
        )
    }

    fun Activity?.showMultiDialog(
        items: List<String>,
        selectedIndex: List<Int>,
        name: String,
        dismissCallback: () -> Unit,
        callback: (List<Int>) -> Unit,
    ) {
        val act = (this ?: CommonActivity.activity)?.takeUnless { it.isFinishing || it.isDestroyed } ?: return
        val checked = BooleanArray(items.size) { idx -> idx in selectedIndex }
        AlertDialog.Builder(act)
            .setTitle(name)
            .setMultiChoiceItems(items.toTypedArray(), checked) { _, which, isChecked ->
                if (which in checked.indices) checked[which] = isChecked
            }
            .setPositiveButton(android.R.string.ok) { dialog, _ ->
                val chosen = checked.indices.filter { checked[it] }
                callback(chosen)
                dialog.dismiss()
            }
            .setNegativeButton(android.R.string.cancel) { dialog, _ ->
                dialog.dismiss()
            }
            .setOnDismissListener { dismissCallback() }
            .show()
    }

    fun Activity?.showDialog(
        items: List<String>,
        selectedIndex: Int,
        name: String,
        showApply: Boolean,
        dismissCallback: () -> Unit,
        callback: (Int) -> Unit,
    ) {
        val act = (this ?: CommonActivity.activity)?.takeUnless { it.isFinishing || it.isDestroyed } ?: return
        var current = selectedIndex
        val builder = AlertDialog.Builder(act)
            .setTitle(name)
            .setSingleChoiceItems(items.toTypedArray(), selectedIndex) { dialog, which ->
                current = which
                if (!showApply) {
                    callback(which)
                    dialog.dismiss()
                }
            }
            .setOnDismissListener { dismissCallback() }
        if (showApply) {
            builder.setPositiveButton(android.R.string.ok) { dialog, _ ->
                if (current in items.indices) callback(current)
                dialog.dismiss()
            }
        }
        builder.setNegativeButton(android.R.string.cancel) { dialog, _ -> dialog.dismiss() }
        builder.show()
    }

    fun Activity?.showBottomDialog(
        items: List<String>,
        selectedIndex: Int,
        name: String,
        showApply: Boolean,
        dismissCallback: () -> Unit,
        callback: (Int) -> Unit,
    ) {
        showDialog(items, selectedIndex, name, showApply, dismissCallback, callback)
    }

    fun Activity.showBottomDialogInstant(
        items: List<String>,
        name: String,
        dismissCallback: () -> Unit,
        callback: (Int) -> Unit,
    ): BottomSheetDialog {
        val sheet = BottomSheetDialog(this)
        showDialog(items, -1, name, false, dismissCallback, callback)
        return sheet
    }
}
''',
        patched,
    )

    # 4. Complete SyncProviders & AccountManager ABI (SyncRepo, SyncAPI, AuthRepo, AuthAPI, AccountManager, providers)
    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/syncproviders/SyncProvidersCompat.kt",
        r'''package com.lagradost.cloudstream3.syncproviders

import android.net.Uri
import androidx.annotation.WorkerThread
import com.fasterxml.jackson.annotation.JsonAlias
import com.fasterxml.jackson.annotation.JsonProperty
import com.lagradost.cloudstream3.ActorData
import com.lagradost.cloudstream3.CloudStreamApp
import com.lagradost.cloudstream3.CloudStreamApp.Companion.getKey
import com.lagradost.cloudstream3.CloudStreamApp.Companion.setKey
import com.lagradost.cloudstream3.CommonActivity.showToast
import com.lagradost.cloudstream3.ErrorLoadingException
import com.lagradost.cloudstream3.LoadResponse
import com.lagradost.cloudstream3.NextAiring
import com.lagradost.cloudstream3.Score
import com.lagradost.cloudstream3.SearchQuality
import com.lagradost.cloudstream3.SearchResponse
import com.lagradost.cloudstream3.ShowStatus
import com.lagradost.cloudstream3.TvType
import com.lagradost.cloudstream3.base64Encode
import com.lagradost.cloudstream3.mvvm.safe
import com.lagradost.cloudstream3.subtitles.AbstractSubtitleEntities.SubtitleEntity
import com.lagradost.cloudstream3.subtitles.AbstractSubtitleEntities.SubtitleSearch
import com.lagradost.cloudstream3.subtitles.SubtitleResource
import com.lagradost.cloudstream3.syncproviders.providers.Addic7ed
import com.lagradost.cloudstream3.syncproviders.providers.AniListApi
import com.lagradost.cloudstream3.syncproviders.providers.KitsuApi
import com.lagradost.cloudstream3.syncproviders.providers.LocalList
import com.lagradost.cloudstream3.syncproviders.providers.MALApi
import com.lagradost.cloudstream3.syncproviders.providers.OpenSubtitlesApi
import com.lagradost.cloudstream3.syncproviders.providers.SimklApi
import com.lagradost.cloudstream3.syncproviders.providers.SubDlApi
import com.lagradost.cloudstream3.syncproviders.providers.SubSourceApi
import com.lagradost.cloudstream3.ui.SyncWatchType
import com.lagradost.cloudstream3.ui.library.ListSorting
import com.lagradost.cloudstream3.utils.DataStoreHelper
import com.lagradost.cloudstream3.utils.UiText
import java.security.SecureRandom
import java.util.Date
import java.util.concurrent.TimeUnit
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonNames

data class AuthLoginPage(
    val url: String,
    val payload: String? = null,
)

@Serializable
data class AuthToken(
    @JsonProperty("accessToken") @SerialName("accessToken")
    val accessToken: String? = null,
    @JsonProperty("refreshToken") @SerialName("refreshToken")
    val refreshToken: String? = null,
    @JsonProperty("accessTokenLifetime") @SerialName("accessTokenLifetime")
    val accessTokenLifetime: Long? = null,
    @JsonProperty("refreshTokenLifetime") @SerialName("refreshTokenLifetime")
    val refreshTokenLifetime: Long? = null,
    @JsonProperty("payload") @SerialName("payload")
    val payload: String? = null,
) {
    fun isAccessTokenExpired(marginSec: Long = 10L): Boolean =
        accessTokenLifetime != null && (System.currentTimeMillis() / 1000L) + marginSec >= accessTokenLifetime

    fun isRefreshTokenExpired(marginSec: Long = 10L): Boolean =
        refreshTokenLifetime != null && (System.currentTimeMillis() / 1000L) + marginSec >= refreshTokenLifetime
}

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class AuthUser(
    @JsonProperty("name") @SerialName("name")
    val name: String?,
    @JsonProperty("id") @SerialName("id")
    val id: Int,
    @JsonProperty("profilePicture") @SerialName("profilePicture")
    val profilePicture: String? = null,
    @JsonProperty("profilePictureHeaders") @JsonAlias("profilePictureHeader")
    @SerialName("profilePictureHeaders") @JsonNames("profilePictureHeader")
    val profilePictureHeaders: Map<String, String>? = null,
)

@Serializable
data class AuthData(
    @JsonProperty("user") @SerialName("user") val user: AuthUser,
    @JsonProperty("token") @SerialName("token") val token: AuthToken,
)

data class AuthPinData(
    val deviceCode: String,
    val userCode: String,
    val verificationUrl: String,
    val expiresIn: Int,
    val interval: Int,
)

data class AuthLoginRequirement(
    val password: Boolean = false,
    val username: Boolean = false,
    val email: Boolean = false,
    val server: Boolean = false,
)

@Serializable
data class AuthLoginResponse(
    @JsonProperty("password") @SerialName("password") val password: String?,
    @JsonProperty("username") @SerialName("username") val username: String?,
    @JsonProperty("email") @SerialName("email") val email: String?,
    @JsonProperty("server") @SerialName("server") val server: String?,
)

abstract class AuthAPI {
    open val name: String = "NONE"
    open val idPrefix: String = "NONE"
    open val icon: Int? = null
    open val requiresLogin: Boolean = true
    open val createAccountUrl: String? = null
    open val redirectUrlIdentifier: String? = null
    open val hasOAuth2: Boolean = false
    open val hasPin: Boolean = false
    open val hasInApp: Boolean = false
    open val inAppLoginRequirement: AuthLoginRequirement? = null

    companion object {
        val unixTime: Long get() = System.currentTimeMillis() / 1000L
        val unixTimeMs: Long get() = System.currentTimeMillis()

        fun splitRedirectUrl(redirectUrl: String): Map<String, String> = runCatching {
            val normalized = redirectUrl.replace(AccountManager.APP_STRING, "https").replace("/#", "?")
            val uri = Uri.parse(normalized)
            buildMap {
                for (name in uri.queryParameterNames) {
                    uri.getQueryParameter(name)?.let { put(name, it) }
                }
            }
        }.getOrDefault(emptyMap())

        fun generateCodeVerifier(): String {
            val secureRandom = SecureRandom()
            val codeVerifierBytes = ByteArray(96)
            secureRandom.nextBytes(codeVerifierBytes)
            return base64Encode(codeVerifierBytes).trimEnd('=')
                .replace("+", "-")
                .replace("/", "_")
                .replace("\n", "")
        }
    }

    open fun isValidRedirectUrl(url: String): Boolean =
        redirectUrlIdentifier != null && url.contains("/$redirectUrlIdentifier")

    open suspend fun login(redirectUrl: String, payload: String?): AuthToken? = throw NotImplementedError()
    open fun loginRequest(): AuthLoginPage? = throw NotImplementedError()
    open suspend fun pinRequest(): AuthPinData? = throw NotImplementedError()
    open suspend fun refreshToken(token: AuthToken): AuthToken? = throw NotImplementedError()
    open suspend fun login(payload: AuthPinData): AuthToken? = throw NotImplementedError()
    open suspend fun login(form: AuthLoginResponse): AuthToken? = throw NotImplementedError()
    open suspend fun user(token: AuthToken?): AuthUser? = throw NotImplementedError()
    open suspend fun invalidateToken(token: AuthToken): Nothing = throw NotImplementedError()

    fun toRepo(): AuthRepo = when (this) {
        is SubtitleAPI -> SubtitleRepo(this)
        is SyncAPI -> SyncRepo(this)
        else -> PlainAuthRepo(this)
    }

    fun loginInfo(): LoginInfo? = toRepo().authUser()?.let { u ->
        LoginInfo(profilePicture = u.profilePicture, name = u.name, accountIndex = 0)
    }

    suspend fun getPersonalLibrary(): SyncAPI.LibraryMetadata? =
        (toRepo() as? SyncRepo)?.library()?.getOrThrow()

    class LoginInfo(
        val profilePicture: String? = null,
        val name: String?,
        val accountIndex: Int = 0,
    )
}

/** Legacy compatibility base classes used by older CloudStream extensions. */
abstract class InAppAuthAPI : AuthAPI() {
    override val hasInApp: Boolean = true
}

abstract class OAuth2API : AuthAPI() {
    override val hasOAuth2: Boolean = true
}

class PlainAuthRepo(api: AuthAPI) : AuthRepo(api)

abstract class AuthRepo(open val api: AuthAPI) {
    fun isValidRedirectUrl(url: String): Boolean = safe { api.isValidRedirectUrl(url) } ?: false
    val idPrefix: String get() = api.idPrefix
    val name: String get() = api.name
    val icon: Int? get() = api.icon
    val requiresLogin: Boolean get() = api.requiresLogin
    val createAccountUrl: String? get() = api.createAccountUrl
    val hasOAuth2: Boolean get() = api.hasOAuth2
    val hasPin: Boolean get() = api.hasPin
    val hasInApp: Boolean get() = api.hasInApp
    val inAppLoginRequirement: AuthLoginRequirement? get() = api.inAppLoginRequirement
    val isAvailable: Boolean get() = !api.requiresLogin || authUser() != null

    companion object {
        private val oauthPayload: MutableMap<String, String?> = mutableMapOf()
    }

    protected suspend fun freshAuth(): AuthData? {
        val data = authData() ?: return null
        if (data.token.isAccessTokenExpired()) {
            val newToken = runCatching { api.refreshToken(data.token) }.getOrNull() ?: return null
            val newAuth = AuthData(user = data.user, token = newToken)
            refreshUser(newAuth)
            return newAuth
        }
        return data
    }

    fun openOAuth2Page(): Boolean {
        val page = runCatching { api.loginRequest() }.getOrNull() ?: return false
        synchronized(oauthPayload) {
            oauthPayload[idPrefix] = page.payload
        }
        CloudStreamApp.openBrowser(page.url)
        return true
    }

    fun openOAuth2PageWithToast() {
        try {
            if (!openOAuth2Page()) {
                showToast("Authentication is not configured for ${api.name}")
            }
        } catch (t: Throwable) {
            t.printStackTrace()
            val msg = (t as? ErrorLoadingException)?.message ?: "Could not authenticate with ${api.name}"
            showToast(msg)
        }
    }

    suspend fun logout(from: AuthUser) {
        val currentAccounts = AccountManager.accounts(idPrefix)
        val (newAccounts, oldAccounts) = currentAccounts.partition { it.user.id != from.id }
        if (newAccounts.size < currentAccounts.size) {
            AccountManager.updateAccounts(idPrefix, newAccounts.toTypedArray())
            AccountManager.updateAccountsId(idPrefix, AccountManager.NONE_ID)
        }
        for (oldAccount in oldAccounts) {
            try {
                api.invalidateToken(oldAccount.token)
            } catch (_: Throwable) {
            }
        }
    }

    fun refreshUser(newAuth: AuthData) {
        val currentAccounts = AccountManager.accounts(idPrefix)
        val newAccounts = currentAccounts.map { if (it.user.id == newAuth.user.id) newAuth else it }.toTypedArray()
        AccountManager.updateAccounts(idPrefix, newAccounts)
    }

    fun authData(): AuthData? = synchronized(AccountManager.cachedAccountIds) {
        AccountManager.cachedAccountIds[idPrefix]?.let { id ->
            AccountManager.cachedAccounts[idPrefix]?.firstOrNull { data -> data.user.id == id }
        }
    }

    fun authToken(): AuthToken? = authData()?.token
    fun authUser(): AuthUser? = authData()?.user

    val accounts: Array<AuthData>
        get() = synchronized(AccountManager.cachedAccounts) {
            AccountManager.cachedAccounts[idPrefix] ?: emptyArray()
        }

    var accountId: Int
        get() = synchronized(AccountManager.cachedAccountIds) {
            AccountManager.cachedAccountIds[idPrefix] ?: AccountManager.NONE_ID
        }
        set(value) {
            AccountManager.updateAccountsId(idPrefix, value)
        }

    suspend fun pinRequest(): AuthPinData? = api.pinRequest()

    private suspend fun setupLogin(token: AuthToken): Boolean {
        val user = api.user(token) ?: return false
        val newAccount = AuthData(token = token, user = user)
        val currentAccounts = AccountManager.accounts(idPrefix)
        val filtered = currentAccounts.filterNot { it.user.id == newAccount.user.id }.toTypedArray()
        AccountManager.updateAccounts(idPrefix, filtered + newAccount)
        AccountManager.updateAccountsId(idPrefix, user.id)
        if (this is SyncRepo) {
            requireLibraryRefresh = true
        }
        return true
    }

    suspend fun login(form: AuthLoginResponse): Boolean = setupLogin(api.login(form) ?: return false)
    suspend fun login(payload: AuthPinData): Boolean = setupLogin(api.login(payload) ?: return false)
    suspend fun login(redirectUrl: String): Boolean = setupLogin(
        api.login(redirectUrl, synchronized(oauthPayload) { oauthPayload[api.idPrefix] }) ?: return false,
    )
}

abstract class SyncAPI : AuthAPI() {
    open var requireLibraryRefresh: Boolean = true
    open val mainUrl: String = "NONE"
    open val supportedWatchTypes: Set<SyncWatchType> = SyncWatchType.entries.toSet()
    open val syncIdName: SyncIdName? = null

    @WorkerThread
    open suspend fun updateStatus(auth: AuthData?, id: String, newStatus: AbstractSyncStatus): Boolean =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun status(auth: AuthData?, id: String): AbstractSyncStatus? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun load(auth: AuthData?, id: String): SyncResult? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun search(auth: AuthData?, query: String): List<SyncSearchResult>? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun library(auth: AuthData?): LibraryMetadata? =
        throw NotImplementedError()

    open fun urlToId(url: String): String? = null

    data class SyncSearchResult(
        override val name: String,
        override val apiName: String,
        var syncId: String,
        override val url: String,
        override var posterUrl: String?,
        override var type: TvType? = null,
        override var quality: SearchQuality? = null,
        override var posterHeaders: Map<String, String>? = null,
        override var id: Int? = null,
        override var score: Score? = null,
    ) : SearchResponse

    abstract class AbstractSyncStatus {
        abstract var status: SyncWatchType
        abstract var score: Score?
        abstract var watchedEpisodes: Int?
        abstract var isFavorite: Boolean?
        abstract var maxEpisodes: Int?
    }

    data class SyncStatus(
        override var status: SyncWatchType,
        override var score: Score?,
        override var watchedEpisodes: Int?,
        override var isFavorite: Boolean? = null,
        override var maxEpisodes: Int? = null,
    ) : AbstractSyncStatus()

    data class SyncResult(
        var id: String,
        var totalEpisodes: Int? = null,
        var title: String? = null,
        var publicScore: Score? = null,
        var duration: Int? = null,
        var synopsis: String? = null,
        var airStatus: ShowStatus? = null,
        var nextAiring: NextAiring? = null,
        var studio: List<String>? = null,
        var genres: List<String>? = null,
        var synonyms: List<String>? = null,
        var trailers: List<String>? = null,
        var isAdult: Boolean? = null,
        var posterUrl: String? = null,
        var backgroundPosterUrl: String? = null,
        var startDate: Long? = null,
        var endDate: Long? = null,
        var recommendations: List<SyncSearchResult>? = null,
        var nextSeason: SyncSearchResult? = null,
        var prevSeason: SyncSearchResult? = null,
        var actors: List<ActorData>? = null,
    )

    data class Page(
        val title: UiText,
        var items: List<LibraryItem>,
    ) {
        fun sort(method: ListSorting?, query: String? = null) {
            items = when (method) {
                ListSorting.Query -> if (query != null) {
                    val q = query.lowercase()
                    items.sortedByDescending { item ->
                        val lower = item.name.lowercase()
                        when {
                            lower == q -> 3
                            lower.startsWith(q) -> 2
                            lower.contains(q) -> 1
                            else -> 0
                        }
                    }
                } else items
                ListSorting.RatingHigh -> items.sortedBy { -(it.personalRating?.toInt(100) ?: 0) }
                ListSorting.RatingLow -> items.sortedBy { it.personalRating?.toInt(100) ?: 0 }
                ListSorting.AlphabeticalA -> items.sortedBy { it.name }
                ListSorting.AlphabeticalZ -> items.sortedByDescending { it.name }
                ListSorting.UpdatedNew -> items.sortedByDescending { it.lastUpdatedUnixTime }
                ListSorting.UpdatedOld -> items.sortedBy { it.lastUpdatedUnixTime }
                ListSorting.ReleaseDateNew -> items.sortedByDescending { it.releaseDate }
                ListSorting.ReleaseDateOld -> items.sortedBy { it.releaseDate }
                else -> items
            }
        }
    }

    data class LibraryMetadata(
        val allLibraryLists: List<LibraryList>,
        val supportedListSorting: Set<ListSorting>,
    )

    data class LibraryList(
        val name: UiText,
        val items: List<LibraryItem>,
    )

    data class LibraryItem(
        override val name: String,
        override val url: String,
        val syncId: String,
        val episodesCompleted: Int?,
        val episodesTotal: Int?,
        val personalRating: Score?,
        val lastUpdatedUnixTime: Long?,
        override val apiName: String,
        override var type: TvType?,
        override var posterUrl: String?,
        override var posterHeaders: Map<String, String>?,
        override var quality: SearchQuality?,
        val releaseDate: Date?,
        override var id: Int? = null,
        val plot: String? = null,
        override var score: Score? = null,
        val tags: List<String>? = null,
    ) : SearchResponse
}

/** Stateless safe abstraction of SyncAPI (required by StreamPlay & Ultima settings). */
class SyncRepo(override val api: SyncAPI) : AuthRepo(api) {
    val syncIdName: SyncIdName? = api.syncIdName
    var requireLibraryRefresh: Boolean
        get() = api.requireLibraryRefresh
        set(value) {
            api.requireLibraryRefresh = value
        }

    suspend fun updateStatus(id: String, newStatus: SyncAPI.AbstractSyncStatus): Result<Boolean> =
        runCatching {
            val status = api.updateStatus(freshAuth() ?: return@runCatching false, id, newStatus)
            requireLibraryRefresh = true
            status
        }

    suspend fun status(id: String): Result<SyncAPI.AbstractSyncStatus?> = runCatching {
        api.status(freshAuth(), id)
    }

    suspend fun load(id: String): Result<SyncAPI.SyncResult?> = runCatching {
        api.load(freshAuth(), id)
    }

    suspend fun library(): Result<SyncAPI.LibraryMetadata?> = runCatching {
        api.library(freshAuth())
    }
}

abstract class SubtitleAPI : AuthAPI() {
    @WorkerThread
    open suspend fun search(auth: AuthData?, query: SubtitleSearch): List<SubtitleEntity>? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun load(auth: AuthData?, subtitle: SubtitleEntity): String? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun SubtitleResource.getResources(auth: AuthData?, subtitle: SubtitleEntity) {
        addUrl(load(auth, subtitle))
    }

    @WorkerThread
    suspend fun resource(auth: AuthData?, subtitle: SubtitleEntity): SubtitleResource =
        SubtitleResource().apply { getResources(auth, subtitle) }
}

class SubtitleRepo(override val api: SubtitleAPI) : AuthRepo(api) {
    @WorkerThread
    suspend fun resource(data: SubtitleEntity): Result<SubtitleResource> = runCatching {
        api.resource(freshAuth(), data)
    }

    @WorkerThread
    suspend fun search(query: SubtitleSearch): Result<List<SubtitleEntity>> = runCatching {
        api.search(freshAuth(), query).orEmpty()
    }
}

abstract class AccountManager {
    companion object {
        const val NONE_ID: Int = -1

        val malApi = MALApi()
        val kitsuApi = KitsuApi()
        val aniListApi = AniListApi()
        val simklApi = SimklApi()
        val localListApi = LocalList()

        val openSubtitlesApi = OpenSubtitlesApi()
        val addic7ed = Addic7ed()
        val subDlApi = SubDlApi()
        val subSourceApi = SubSourceApi()

        var cachedAccounts: MutableMap<String, Array<AuthData>> = mutableMapOf()
        var cachedAccountIds: MutableMap<String, Int> = mutableMapOf()

        const val ACCOUNT_TOKEN = "auth_tokens"
        const val ACCOUNT_IDS = "auth_ids"

        fun accounts(prefix: String): Array<AuthData> {
            if (prefix == "NONE") return emptyArray()
            return runCatching {
                getKey<Array<AuthData>>(ACCOUNT_TOKEN, "${prefix}/${DataStoreHelper.currentAccount}")
            }.getOrNull() ?: emptyArray()
        }

        fun updateAccounts(prefix: String, array: Array<AuthData>) {
            if (prefix == "NONE") return
            runCatching {
                setKey(ACCOUNT_TOKEN, "${prefix}/${DataStoreHelper.currentAccount}", array)
            }
            synchronized(cachedAccounts) {
                cachedAccounts[prefix] = array
            }
        }

        fun updateAccountsId(prefix: String, id: Int) {
            if (prefix == "NONE") return
            runCatching {
                setKey(ACCOUNT_IDS, "${prefix}/${DataStoreHelper.currentAccount}", id)
            }
            synchronized(cachedAccountIds) {
                cachedAccountIds[prefix] = id
            }
        }

        val allApis: Array<AuthRepo> = arrayOf(
            SyncRepo(malApi),
            SyncRepo(kitsuApi),
            SyncRepo(aniListApi),
            SyncRepo(simklApi),
            SyncRepo(localListApi),
            SubtitleRepo(openSubtitlesApi),
            SubtitleRepo(addic7ed),
            SubtitleRepo(subDlApi),
            SubtitleRepo(subSourceApi),
        )

        val subtitleProviders: Array<SubtitleRepo> = arrayOf(
            SubtitleRepo(openSubtitlesApi),
            SubtitleRepo(addic7ed),
            SubtitleRepo(subDlApi),
            SubtitleRepo(subSourceApi),
        )

        val syncApis: Array<SyncRepo> = arrayOf(
            SyncRepo(malApi),
            SyncRepo(kitsuApi),
            SyncRepo(aniListApi),
            SyncRepo(simklApi),
            SyncRepo(localListApi),
        )

        fun updateAccountIds() {
            val ids = mutableMapOf<String, Int>()
            for (repo in allApis) {
                ids[repo.idPrefix] = runCatching {
                    getKey<Int>(ACCOUNT_IDS, "${repo.idPrefix}/${DataStoreHelper.currentAccount}", NONE_ID)
                }.getOrNull() ?: NONE_ID
            }
            synchronized(cachedAccountIds) {
                cachedAccountIds = ids
            }
        }

        fun initMainAPI() {
            LoadResponse.malIdPrefix = malApi.idPrefix
            LoadResponse.kitsuIdPrefix = kitsuApi.idPrefix
            LoadResponse.aniListIdPrefix = aniListApi.idPrefix
            LoadResponse.simklIdPrefix = simklApi.idPrefix
        }

        const val APP_STRING = "cloudstreamapp"
        const val APP_STRING_REPO = "cloudstreamrepo"
        const val APP_STRING_PLAYER = "cloudstreamplayer"
        const val APP_STRING_SEARCH = "cloudstreamsearch"
        const val APP_STRING_RESUME_WATCHING = "cloudstreamcontinuewatching"
        const val APP_STRING_SHARE = "csshare"

        fun secondsToReadable(seconds: Int, completedValue: String): String {
            var secondsLong = seconds.toLong()
            val days = TimeUnit.SECONDS.toDays(secondsLong)
            secondsLong -= TimeUnit.DAYS.toSeconds(days)
            val hours = TimeUnit.SECONDS.toHours(secondsLong)
            secondsLong -= TimeUnit.HOURS.toSeconds(hours)
            val minutes = TimeUnit.SECONDS.toMinutes(secondsLong)
            if (minutes < 0) return completedValue
            return "${if (days != 0L) "${days}d " else ""}${if (hours != 0L) "${hours}h " else ""}${minutes}m"
        }
    }
}
''',
        patched,
    )

    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/syncproviders/providers/SyncProviderImpls.kt",
        r'''package com.lagradost.cloudstream3.syncproviders.providers

import com.lagradost.cloudstream3.syncproviders.SubtitleAPI
import com.lagradost.cloudstream3.syncproviders.SyncAPI
import com.lagradost.cloudstream3.syncproviders.SyncIdName

class MALApi : SyncAPI() {
    override val name: String = "MAL"
    override val idPrefix: String = "mal"
    override val mainUrl: String = "https://myanimelist.net"
    override val syncIdName: SyncIdName = SyncIdName.MyAnimeList
    override val hasOAuth2: Boolean = true
}

class AniListApi : SyncAPI() {
    override val name: String = "AniList"
    override val idPrefix: String = "anilist"
    override val mainUrl: String = "https://anilist.co"
    override val syncIdName: SyncIdName = SyncIdName.Anilist
    override val hasOAuth2: Boolean = true
}

class KitsuApi : SyncAPI() {
    override val name: String = "Kitsu"
    override val idPrefix: String = "kitsu"
    override val mainUrl: String = "https://kitsu.app"
    override val syncIdName: SyncIdName = SyncIdName.Kitsu
    override val hasInApp: Boolean = true
}

class SimklApi : SyncAPI() {
    override val name: String = "Simkl"
    override val idPrefix: String = "simkl"
    override val mainUrl: String = "https://simkl.com"
    override val syncIdName: SyncIdName = SyncIdName.Simkl
    override val hasOAuth2: Boolean = true
    override val hasPin: Boolean = true
}

class LocalList : SyncAPI() {
    override val name: String = "Local"
    override val idPrefix: String = "local"
    override val requiresLogin: Boolean = false
    override val syncIdName: SyncIdName = SyncIdName.LocalList
}

class OpenSubtitlesApi : SubtitleAPI() {
    override val name: String = "OpenSubtitles"
    override val idPrefix: String = "opensubtitles"
    override val hasInApp: Boolean = true
}

class Addic7ed : SubtitleAPI() {
    override val name: String = "Addic7ed"
    override val idPrefix: String = "addic7ed"
    override val requiresLogin: Boolean = false
}

class SubDlApi : SubtitleAPI() {
    override val name: String = "SubDL"
    override val idPrefix: String = "subdl"
    override val requiresLogin: Boolean = false
}

class SubSourceApi : SubtitleAPI() {
    override val name: String = "SubSource"
    override val idPrefix: String = "subsource"
    override val requiresLogin: Boolean = false
}
''',
        patched,
    )

    # 5. Universal CloudStream Extension Config Bridge (commonMain + androidFull/androidPlaystore + iosFull/iosAppStore)
    _write_text(
        root,
        "composeApp/src/commonMain/kotlin/com/nuvio/app/features/cloudstream/CloudStreamExtensionConfigBridge.kt",
        r'''package com.nuvio.app.features.cloudstream

data class CloudStreamSubProviderConfig(
    val apiClassName: String,
    val name: String,
    val defaultMainUrl: String,
    val overrideMainUrl: String,
    val lang: String,
    val enabled: Boolean,
)

data class CloudStreamPreferenceEntry(
    val prefFile: String,
    val key: String,
    val value: String,
    val valueType: String, // "string" | "boolean" | "int"
    val isDiscoveredHint: Boolean = false,
)

data class CloudStreamPluginConfigSnapshot(
    val pluginId: String,
    val pluginName: String,
    val hasNativeSettings: Boolean,
    val defaultPrefFile: String,
    val candidatePrefFiles: List<String> = emptyList(),
    val subProviders: List<CloudStreamSubProviderConfig> = emptyList(),
    val preferences: List<CloudStreamPreferenceEntry> = emptyList(),
)

internal expect object CloudStreamExtensionConfigBridge {
    val isSupported: Boolean

    suspend fun inspect(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot>

    suspend fun updateSubProvider(
        plugin: CloudStreamPluginItem,
        apiClassName: String,
        enabled: Boolean,
        overrideMainUrl: String,
    ): Result<CloudStreamPluginConfigSnapshot>

    suspend fun savePreference(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        key: String,
        value: String,
        valueType: String,
    ): Result<CloudStreamPluginConfigSnapshot>

    suspend fun deletePreference(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        key: String,
    ): Result<CloudStreamPluginConfigSnapshot>

    suspend fun reloadPlugin(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot>
}
''',
        patched,
    )

    unsupported_bridge_stub = r'''package com.nuvio.app.features.cloudstream

internal actual object CloudStreamExtensionConfigBridge {
    actual val isSupported: Boolean = false

    actual suspend fun inspect(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot> =
        Result.failure(UnsupportedOperationException("Extension configuration is available on Android full builds"))

    actual suspend fun updateSubProvider(
        plugin: CloudStreamPluginItem,
        apiClassName: String,
        enabled: Boolean,
        overrideMainUrl: String,
    ): Result<CloudStreamPluginConfigSnapshot> = inspect(plugin)

    actual suspend fun savePreference(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        key: String,
        value: String,
        valueType: String,
    ): Result<CloudStreamPluginConfigSnapshot> = inspect(plugin)

    actual suspend fun deletePreference(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        key: String,
    ): Result<CloudStreamPluginConfigSnapshot> = inspect(plugin)

    actual suspend fun reloadPlugin(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot> =
        inspect(plugin)
}
'''

    for stub_rel in (
        "composeApp/src/iosFull/kotlin/com/nuvio/app/features/cloudstream/CloudStreamExtensionConfigBridge.ios.kt",
        "composeApp/src/iosAppStore/kotlin/com/nuvio/app/features/cloudstream/CloudStreamExtensionConfigBridge.ios.kt",
        "composeApp/src/androidPlaystore/kotlin/com/nuvio/app/features/cloudstream/CloudStreamExtensionConfigBridge.android.kt",
    ):
        _write_text(root, stub_rel, unsupported_bridge_stub, patched)

    _write_text(
        root,
        "composeApp/src/androidFull/kotlin/com/nuvio/app/features/cloudstream/CloudStreamExtensionConfigBridge.android.kt",
        r'''package com.nuvio.app.features.cloudstream

import android.content.Context
import com.lagradost.cloudstream3.CloudStreamApp
import com.lagradost.cloudstream3.MainAPI
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.ConcurrentHashMap
import java.util.zip.ZipFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

internal object CloudStreamExtensionConfigStore {
    private const val CONFIG_PREFS = "nuvio_cloudstream_ext_overrides"
    private val defaultMainUrls = ConcurrentHashMap<String, String>()

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences(CONFIG_PREFS, Context.MODE_PRIVATE)

    private fun enabledKey(pluginId: String, apiClassName: String) =
        "enabled::$pluginId::$apiClassName"

    private fun urlKey(pluginId: String, apiClassName: String) =
        "mainUrl::$pluginId::$apiClassName"

    fun recordDefaultUrl(pluginId: String, api: MainAPI): String =
        defaultMainUrls.getOrPut("$pluginId::${api.javaClass.name}") { api.mainUrl }

    fun isSubProviderEnabled(context: Context?, pluginId: String, apiClassName: String): Boolean {
        val ctx = context ?: return true
        return prefs(ctx).getBoolean(enabledKey(pluginId, apiClassName), true)
    }

    fun getOverrideMainUrl(context: Context?, pluginId: String, apiClassName: String): String {
        val ctx = context ?: return ""
        return prefs(ctx).getString(urlKey(pluginId, apiClassName), "")?.trim().orEmpty()
    }

    fun setSubProviderConfig(
        context: Context,
        pluginId: String,
        apiClassName: String,
        enabled: Boolean,
        overrideMainUrl: String,
    ) {
        prefs(context).edit()
            .putBoolean(enabledKey(pluginId, apiClassName), enabled)
            .putString(urlKey(pluginId, apiClassName), overrideMainUrl.trim().trimEnd('/'))
            .apply()
    }

    fun applyOverrideToApi(pluginId: String, api: MainAPI) {
        val defaultUrl = recordDefaultUrl(pluginId, api)
        val ctx = CloudStreamPlatformRuntime.currentAppContext() ?: CloudStreamApp.context
        val overrideUrl = getOverrideMainUrl(ctx, pluginId, api.javaClass.name)
        val desired = overrideUrl.ifBlank { defaultUrl }
        if (desired.isNotBlank() && api.mainUrl != desired) {
            runCatching { api.mainUrl = desired }
        }
    }

    fun activeProviders(pluginId: String, providers: List<MainAPI>): List<MainAPI> {
        val ctx = CloudStreamPlatformRuntime.currentAppContext() ?: CloudStreamApp.context
        providers.forEach { api -> applyOverrideToApi(pluginId, api) }
        val enabled = providers.filter { api ->
            isSubProviderEnabled(ctx, pluginId, api.javaClass.name)
        }
        return enabled
    }
}

internal actual object CloudStreamExtensionConfigBridge {
    actual val isSupported: Boolean = true

    private val HINT_KEYWORDS = listOf(
        "token", "cookie", "febbox", "superstream", "debrid", "realdebrid", "torbox",
        "alldebrid", "premiumize", "tmdb", "imdb", "api_key", "apikey", "proxy",
        "domain", "base_url", "baseurl", "custom_url", "host", "mirror", "server",
        "quality", "adult", "nsfw", "sub", "dub", "prefer",
    )

    actual suspend fun inspect(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot> =
        withContext(Dispatchers.IO) {
            runCatching {
                val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                    "Android context is not ready"
                }
                val (hasNativeSettings, providers) = CloudStreamPlatformRuntime.inspectPluginProviders(plugin)
                val subProviders = providers.map { api ->
                    val defaultUrl = CloudStreamExtensionConfigStore.recordDefaultUrl(plugin.metadata.id.value, api)
                    val overrideUrl = CloudStreamExtensionConfigStore.getOverrideMainUrl(
                        ctx,
                        plugin.metadata.id.value,
                        api.javaClass.name,
                    )
                    val enabled = CloudStreamExtensionConfigStore.isSubProviderEnabled(
                        ctx,
                        plugin.metadata.id.value,
                        api.javaClass.name,
                    )
                    CloudStreamExtensionConfigStore.applyOverrideToApi(plugin.metadata.id.value, api)
                    CloudStreamSubProviderConfig(
                        apiClassName = api.javaClass.name,
                        name = api.name,
                        defaultMainUrl = defaultUrl,
                        overrideMainUrl = overrideUrl,
                        lang = api.lang,
                        enabled = enabled,
                    )
                }

                val dexScan = scanCs3DexForPrefs(plugin)
                val internalClean = plugin.metadata.internalName.removeSuffix("Plugin").trim()
                    .ifBlank { plugin.metadata.name.trim() }
                val sharedPrefsDir = File(ctx.applicationInfo.dataDir, "shared_prefs")
                val existingMatchingFiles = sharedPrefsDir.listFiles()
                    ?.mapNotNull { f -> f.name.removeSuffix(".xml").takeIf { f.name.endsWith(".xml") } }
                    ?.filter { name ->
                        name.equals(internalClean, ignoreCase = true) ||
                            name.equals(plugin.metadata.internalName, ignoreCase = true) ||
                            name.equals(plugin.metadata.name, ignoreCase = true) ||
                            name.contains(internalClean, ignoreCase = true)
                    }
                    .orEmpty()

                val candidateFiles = (
                    existingMatchingFiles +
                        dexScan.prefFileCandidates +
                        listOf(internalClean, plugin.metadata.internalName, plugin.metadata.name)
                    )
                    .map { it.trim() }
                    .filter { it.isNotBlank() && !it.startsWith("nuvio_") && !it.startsWith("androidx.") }
                    .distinct()

                val primaryPrefFile = candidateFiles.firstOrNull() ?: internalClean.ifBlank { "PluginPrefs" }
                val entries = mutableListOf<CloudStreamPreferenceEntry>()
                val seenKeys = HashSet<String>()

                for (prefName in candidateFiles) {
                    val sp = ctx.getSharedPreferences(prefName, Context.MODE_PRIVATE)
                    sp.all.entries.sortedBy { it.key }.forEach { (key, rawVal) ->
                        val valueType = when (rawVal) {
                            is Boolean -> "boolean"
                            is Int, is Long -> "int"
                            else -> "string"
                        }
                        if (seenKeys.add("$prefName::$key")) {
                            entries += CloudStreamPreferenceEntry(
                                prefFile = prefName,
                                key = key,
                                value = rawVal?.toString().orEmpty(),
                                valueType = valueType,
                                isDiscoveredHint = false,
                            )
                        }
                    }
                }

                // Also surface DataStore keys under the plugin's folder if any exist
                CloudStreamApp.getKeys(internalClean).orEmpty().forEach { fullKey ->
                    val shortKey = fullKey.substringAfter('/', fullKey)
                    val raw = CloudStreamApp.getKey<String>(fullKey)
                    if (raw != null && seenKeys.add("$primaryPrefFile::$shortKey")) {
                        entries += CloudStreamPreferenceEntry(
                            prefFile = primaryPrefFile,
                            key = shortKey,
                            value = raw,
                            valueType = "string",
                            isDiscoveredHint = false,
                        )
                    }
                }

                // Append discovered DEX preference key hints that haven't been set yet
                dexScan.keyCandidates.take(16).forEach { hintKey ->
                    if (entries.none { it.key.equals(hintKey, ignoreCase = true) } &&
                        seenKeys.add("$primaryPrefFile::$hintKey")
                    ) {
                        val guessedType = if (
                            hintKey.startsWith("enable", true) ||
                            hintKey.startsWith("disable", true) ||
                            hintKey.startsWith("is_", true) ||
                            hintKey.startsWith("use_", true) ||
                            hintKey.contains("adult", true) ||
                            hintKey.contains("nsfw", true)
                        ) {
                            "boolean"
                        } else {
                            "string"
                        }
                        entries += CloudStreamPreferenceEntry(
                            prefFile = primaryPrefFile,
                            key = hintKey,
                            value = if (guessedType == "boolean") "false" else "",
                            valueType = guessedType,
                            isDiscoveredHint = true,
                        )
                    }
                }

                CloudStreamPluginConfigSnapshot(
                    pluginId = plugin.metadata.id.value,
                    pluginName = plugin.metadata.name,
                    hasNativeSettings = hasNativeSettings,
                    defaultPrefFile = primaryPrefFile,
                    candidatePrefFiles = candidateFiles,
                    subProviders = subProviders,
                    preferences = entries,
                )
            }
        }

    actual suspend fun updateSubProvider(
        plugin: CloudStreamPluginItem,
        apiClassName: String,
        enabled: Boolean,
        overrideMainUrl: String,
    ): Result<CloudStreamPluginConfigSnapshot> = withContext(Dispatchers.IO) {
        runCatching {
            val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                "Android context is not ready"
            }
            CloudStreamExtensionConfigStore.setSubProviderConfig(
                context = ctx,
                pluginId = plugin.metadata.id.value,
                apiClassName = apiClassName,
                enabled = enabled,
                overrideMainUrl = overrideMainUrl,
            )
            inspect(plugin).getOrThrow()
        }
    }

    actual suspend fun savePreference(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        key: String,
        value: String,
        valueType: String,
    ): Result<CloudStreamPluginConfigSnapshot> = withContext(Dispatchers.IO) {
        runCatching {
            val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                "Android context is not ready"
            }
            val cleanKey = key.trim()
            require(cleanKey.isNotEmpty()) { "Preference key cannot be empty" }
            val targetPref = prefFile.trim().ifBlank {
                plugin.metadata.internalName.removeSuffix("Plugin").ifBlank { plugin.metadata.name }
            }
            val targets = listOf(
                targetPref,
                plugin.metadata.internalName.removeSuffix("Plugin"),
                plugin.metadata.internalName,
                plugin.metadata.name,
            ).map { it.trim() }.filter { it.isNotBlank() }.distinct()

            // Write to matching SharedPreferences files AND CloudStream DataStore so whichever
            // storage backend the .cs3 extension reads at runtime receives the value immediately.
            targets.forEach { fileName ->
                val editor = ctx.getSharedPreferences(fileName, Context.MODE_PRIVATE).edit()
                when (valueType.lowercase()) {
                    "boolean" -> {
                        val b = value.equals("true", ignoreCase = true) || value == "1"
                        editor.putBoolean(cleanKey, b)
                        CloudStreamApp.setKey(cleanKey, b)
                        CloudStreamApp.setKey(fileName, cleanKey, b)
                    }
                    "int" -> {
                        val n = value.trim().toIntOrNull() ?: 0
                        editor.putInt(cleanKey, n)
                        CloudStreamApp.setKey(cleanKey, n)
                        CloudStreamApp.setKey(fileName, cleanKey, n)
                    }
                    else -> {
                        editor.putString(cleanKey, value)
                        CloudStreamApp.setKey(cleanKey, value)
                        CloudStreamApp.setKey(fileName, cleanKey, value)
                    }
                }
                editor.apply()
            }
            CloudStreamPlatformRuntime.unload(plugin.metadata.id.value)
            inspect(plugin).getOrThrow()
        }
    }

    actual suspend fun deletePreference(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        key: String,
    ): Result<CloudStreamPluginConfigSnapshot> = withContext(Dispatchers.IO) {
        runCatching {
            val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                "Android context is not ready"
            }
            val cleanKey = key.trim()
            val targets = listOf(
                prefFile,
                plugin.metadata.internalName.removeSuffix("Plugin"),
                plugin.metadata.internalName,
                plugin.metadata.name,
            ).map { it.trim() }.filter { it.isNotBlank() }.distinct()
            targets.forEach { fileName ->
                ctx.getSharedPreferences(fileName, Context.MODE_PRIVATE).edit().remove(cleanKey).apply()
                CloudStreamApp.removeKey(fileName, cleanKey)
            }
            CloudStreamApp.removeKey(cleanKey)
            CloudStreamPlatformRuntime.unload(plugin.metadata.id.value)
            inspect(plugin).getOrThrow()
        }
    }

    actual suspend fun reloadPlugin(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot> =
        withContext(Dispatchers.IO) {
            runCatching {
                CloudStreamPlatformRuntime.unload(plugin.metadata.id.value)
                inspect(plugin).getOrThrow()
            }
        }

    private data class DexPrefScanResult(
        val prefFileCandidates: List<String> = emptyList(),
        val keyCandidates: List<String> = emptyList(),
    )

    private fun scanCs3DexForPrefs(plugin: CloudStreamPluginItem): DexPrefScanResult {
        val path = CloudStreamPlatformStorage.packagePath(plugin.metadata.id.storageKey) ?: return DexPrefScanResult()
        val file = File(path)
        if (!file.isFile) return DexPrefScanResult()
        return runCatching {
            val strings = mutableListOf<String>()
            ZipFile(file).use { zf ->
                val entries = zf.entries()
                while (entries.hasMoreElements()) {
                    val entry = entries.nextElement()
                    if (entry.name.endsWith(".dex")) {
                        val bytes = zf.getInputStream(entry).readBytes()
                        strings += extractDexStrings(bytes)
                    }
                }
            }
            val baseName = plugin.metadata.internalName.removeSuffix("Plugin")
            val prefFiles = strings.filter { s ->
                s.length in 3..48 &&
                    s.matches(Regex("^[A-Za-z0-9_.-]+$")) &&
                    (s.equals(baseName, ignoreCase = true) ||
                        s.contains("Pref", ignoreCase = false) ||
                        s.endsWith("_prefs", ignoreCase = true) ||
                        s.endsWith("_settings", ignoreCase = true))
            }.distinct()

            val keys = strings.filter { s ->
                s.length in 3..38 &&
                    s.matches(Regex("^[a-zA-Z][a-zA-Z0-9_.-]*$")) &&
                    !s.contains('.') &&
                    !s.startsWith("http", ignoreCase = true) &&
                    !s.startsWith("get") &&
                    !s.startsWith("set") &&
                    !s.endsWith("Fragment") &&
                    !s.endsWith("Plugin") &&
                    !s.endsWith("Activity") &&
                    HINT_KEYWORDS.any { kw -> s.contains(kw, ignoreCase = true) }
            }.distinct()

            DexPrefScanResult(prefFileCandidates = prefFiles, keyCandidates = keys)
        }.getOrDefault(DexPrefScanResult())
    }

    private fun extractDexStrings(dex: ByteArray): List<String> {
        if (dex.size < 0x70) return emptyList()
        if (dex[0] != 'd'.code.toByte() || dex[1] != 'e'.code.toByte() || dex[2] != 'x'.code.toByte()) {
            return emptyList()
        }
        val buf = ByteBuffer.wrap(dex).order(ByteOrder.LITTLE_ENDIAN)
        val stringIdsSize = buf.getInt(0x38)
        val stringIdsOff = buf.getInt(0x3C)
        if (stringIdsSize <= 0 || stringIdsSize > 200_000 || stringIdsOff <= 0 || stringIdsOff >= dex.size) {
            return emptyList()
        }
        val out = ArrayList<String>(stringIdsSize.coerceAtMost(4096))
        for (i in 0 until stringIdsSize) {
            val idPos = stringIdsOff + i * 4
            if (idPos + 4 > dex.size) break
            var dataOff = buf.getInt(idPos)
            if (dataOff <= 0 || dataOff >= dex.size) continue
            // Skip ULEB128 utf16_size
            var shift = 0
            var uleb = 0
            while (dataOff < dex.size && shift < 35) {
                val b = dex[dataOff++].toInt() and 0xFF
                uleb = uleb or ((b and 0x7F) shl shift)
                if ((b and 0x80) == 0) break
                shift += 7
            }
            if (uleb in 2..64 && dataOff < dex.size) {
                var end = dataOff
                val maxEnd = (dataOff + 128).coerceAtMost(dex.size)
                while (end < maxEnd && dex[end].toInt() != 0) end++
                val len = end - dataOff
                if (len in 2..64) {
                    out += String(dex, dataOff, len, Charsets.UTF_8)
                }
            }
        }
        return out
    }
}
''',
        patched,
    )

    # 6. Hook CloudStreamExtensionConfigStore into CloudStreamPlatformRuntime.android.kt
    runtime_kt = root / "composeApp/src/androidFull/kotlin/com/nuvio/app/features/cloudstream/CloudStreamPlatformRuntime.android.kt"
    if runtime_kt.is_file():
        changed = False
        changed |= _replace_once(
            runtime_kt,
            "    actual fun clear() {\n",
            "    internal fun currentAppContext(): Context? = getContext()\n\n"
            "    internal suspend fun inspectPluginProviders(\n"
            "        plugin: CloudStreamPluginItem,\n"
            "    ): Pair<Boolean, List<MainAPI>> {\n"
            "        provider(plugin)\n"
            "        val loadedPlugin = synchronized(loadedLock) { loaded[plugin.metadata.id.value] }\n"
            "            ?: error(\"CloudStream extension could not be loaded\")\n"
            "        val hasNative = (loadedPlugin.instance as? Plugin)?.openSettings != null\n"
            "        return hasNative to loadedPlugin.providers\n"
            "    }\n\n"
            "    actual fun clear() {\n",
            "CloudStreamPlatformRuntime inspectPluginProviders & currentAppContext",
        )
        changed |= _replace_once(
            runtime_kt,
            "    override suspend fun getMainPage(\n"
            "        page: Int,\n"
            "    ): List<Pair<String, List<CloudStreamSearchItem>>> = withContext(Dispatchers.IO) {\n"
            "        val eligibleProviders = providers\n",
            "    override suspend fun getMainPage(\n"
            "        page: Int,\n"
            "    ): List<Pair<String, List<CloudStreamSearchItem>>> = withContext(Dispatchers.IO) {\n"
            "        val activeList = CloudStreamExtensionConfigStore.activeProviders(id, providers)\n"
            "        if (activeList.isEmpty()) return@withContext emptyList()\n"
            "        val eligibleProviders = activeList\n",
            "CloudStreamPlatformRuntime getMainPage use activeProviders",
        )
        changed |= _replace_once(
            runtime_kt,
            "            .ifEmpty { providers }\n",
            "            .ifEmpty { activeList }\n",
            "CloudStreamPlatformRuntime getMainPage fallback activeList",
        )
        changed |= _replace_once(
            runtime_kt,
            "    override suspend fun search(query: String): List<CloudStreamSearchItem> = withContext(Dispatchers.IO) {\n"
            "        val apiGate = Semaphore(CLOUDSTREAM_API_CONCURRENCY)\n"
            "        var lastError: Throwable? = null\n"
            "        val sanitizedQuery = query.replace('&', ' ').replace('#', ' ').replace(Regex(\"\\\\s+\"), \" \").trim()\n"
            "        val orderedResults = arrayOfNulls<List<CloudStreamSearchItem>>(providers.size)\n\n"
            "        coroutineScope {\n"
            "            providers.mapIndexed { index, api ->\n",
            "    override suspend fun search(query: String): List<CloudStreamSearchItem> = withContext(Dispatchers.IO) {\n"
            "        val activeList = CloudStreamExtensionConfigStore.activeProviders(id, providers)\n"
            "        if (activeList.isEmpty()) return@withContext emptyList()\n"
            "        val apiGate = Semaphore(CLOUDSTREAM_API_CONCURRENCY)\n"
            "        var lastError: Throwable? = null\n"
            "        val sanitizedQuery = query.replace('&', ' ').replace('#', ' ').replace(Regex(\"\\\\s+\"), \" \").trim()\n"
            "        val orderedResults = arrayOfNulls<List<CloudStreamSearchItem>>(activeList.size)\n\n"
            "        coroutineScope {\n"
            "            activeList.mapIndexed { index, api ->\n",
            "CloudStreamPlatformRuntime search use activeProviders",
        )
        changed |= _replace_once(
            runtime_kt,
            "    private fun findProvider(className: String): MainAPI =\n"
            "        providers.firstOrNull { it.javaClass.name == className }\n"
            "            ?: error(\"CloudStream provider is no longer registered\")\n",
            "    private fun findProvider(className: String): MainAPI =\n"
            "        providers.firstOrNull { it.javaClass.name == className }\n"
            "            ?.also { api -> CloudStreamExtensionConfigStore.applyOverrideToApi(id, api) }\n"
            "            ?: error(\"CloudStream provider is no longer registered\")\n",
            "CloudStreamPlatformRuntime findProvider applyOverrideToApi",
        )
        if changed:
            patched.append(str(runtime_kt.relative_to(root)))

    # 7. Patch CloudStreamSettingsSection.kt so Gear icon opens Universal Extension Settings Dialog
    section_kt = root / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/plugins/CloudStreamSettingsSection.kt"
    if section_kt.is_file():
        changed = False
        changed |= _replace_once(
            section_kt,
            "import androidx.compose.foundation.layout.height\n",
            "import androidx.compose.foundation.layout.height\n"
            "import androidx.compose.foundation.layout.heightIn\n"
            "import androidx.compose.foundation.rememberScrollState\n"
            "import androidx.compose.foundation.verticalScroll\n",
            "CloudStreamSettingsSection scroll imports",
        )
        changed |= _replace_once(
            section_kt,
            "import androidx.compose.material.icons.rounded.Settings\n",
            "import androidx.compose.material.icons.rounded.Add\n"
            "import androidx.compose.material.icons.rounded.Check\n"
            "import androidx.compose.material.icons.rounded.OpenInNew\n"
            "import androidx.compose.material.icons.rounded.Settings\n",
            "CloudStreamSettingsSection extra icon imports",
        )
        changed |= _replace_once(
            section_kt,
            "import androidx.compose.ui.unit.dp\n",
            "import androidx.compose.ui.unit.dp\n"
            "import androidx.compose.ui.window.DialogProperties\n"
            "import com.nuvio.app.core.ui.DialogButton\n"
            "import com.nuvio.app.core.ui.DialogButtonStyle\n"
            "import com.nuvio.app.core.ui.DialogButtons\n"
            "import com.nuvio.app.core.ui.DialogSurface\n",
            "CloudStreamSettingsSection DialogSurface imports",
        )
        changed |= _replace_once(
            section_kt,
            "import com.nuvio.app.features.cloudstream.CloudStreamPluginItem\n",
            "import com.nuvio.app.features.cloudstream.CloudStreamExtensionConfigBridge\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamPluginConfigSnapshot\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamPluginItem\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamPreferenceEntry\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamSubProviderConfig\n"
            "import kotlinx.coroutines.delay\n",
            "CloudStreamSettingsSection ConfigBridge imports",
        )
        changed |= _replace_once(
            section_kt,
            "    var isBulkInstalling by remember { mutableStateOf(false) }\n",
            "    var isBulkInstalling by remember { mutableStateOf(false) }\n"
            "    var configuringPluginId by rememberSaveable { mutableStateOf<String?>(null) }\n",
            "CloudStreamSettingsSection configuringPluginId state",
        )
        changed |= _replace_once(
            section_kt,
            "    visiblePlugins.forEach { plugin ->\n"
            "        CloudStreamPluginCard(\n"
            "            plugin = plugin,\n"
            "            securityWarningAccepted = state.securityWarningAccepted,\n"
            "            pinnedSourceIds = pinnedSourceIds,\n"
            "            copy = copy,\n"
            "            onMessage = { message = it },\n"
            "        )\n"
            "    }\n"
            "}\n",
            "    visiblePlugins.forEach { plugin ->\n"
            "        CloudStreamPluginCard(\n"
            "            plugin = plugin,\n"
            "            securityWarningAccepted = state.securityWarningAccepted,\n"
            "            pinnedSourceIds = pinnedSourceIds,\n"
            "            copy = copy,\n"
            "            onMessage = { message = it },\n"
            "            onOpenConfig = { configuringPluginId = plugin.metadata.id.value },\n"
            "        )\n"
            "    }\n\n"
            "    val configuringPlugin = configuringPluginId?.let { id ->\n"
            "        state.plugins.firstOrNull { it.metadata.id.value == id }\n"
            "    }\n"
            "    if (configuringPlugin != null) {\n"
            "        CloudStreamExtensionSettingsDialog(\n"
            "            plugin = configuringPlugin,\n"
            "            onDismiss = { configuringPluginId = null },\n"
            "            onLaunchNativeSettings = {\n"
            "                val targetId = configuringPlugin.metadata.id.value\n"
            "                configuringPluginId = null\n"
            "                scope.launch {\n"
            "                    delay(140)\n"
            "                    CloudStreamRepository.openPluginSettings(targetId)\n"
            "                        .onFailure { error ->\n"
            "                            val errText = error.message\n"
            "                                ?: \"Could not open built-in extension UI\"\n"
            "                            message = errText\n"
            "                            NuvioToastController.show(errText)\n"
            "                        }\n"
            "                }\n"
            "            },\n"
            "        )\n"
            "    }\n"
            "}\n",
            "CloudStreamSettingsSection render CloudStreamExtensionSettingsDialog",
        )
        changed |= _replace_once(
            section_kt,
            "private fun CloudStreamPluginCard(\n"
            "    plugin: CloudStreamPluginItem,\n"
            "    securityWarningAccepted: Boolean,\n"
            "    pinnedSourceIds: Set<String>,\n"
            "    copy: CloudStreamSettingsCopy,\n"
            "    onMessage: (String) -> Unit,\n"
            ") {\n",
            "private fun CloudStreamPluginCard(\n"
            "    plugin: CloudStreamPluginItem,\n"
            "    securityWarningAccepted: Boolean,\n"
            "    pinnedSourceIds: Set<String>,\n"
            "    copy: CloudStreamSettingsCopy,\n"
            "    onMessage: (String) -> Unit,\n"
            "    onOpenConfig: () -> Unit = {},\n"
            ") {\n",
            "CloudStreamPluginCard onOpenConfig parameter",
        )
        changed |= _replace_once(
            section_kt,
            "                if (plugin.isInstalled) {\n"
            "                    IconButton(\n"
            "                        enabled = plugin.verified && plugin.compatibility.isRunnable,\n"
            "                        onClick = {\n"
            "                            scope.launch {\n"
            "                                CloudStreamRepository.openPluginSettings(plugin.metadata.id.value)\n"
            "                                    .onFailure { error ->\n"
            "                                        val errText = error.message\n"
            "                                            ?: \"This extension does not provide configurable settings\"\n"
            "                                        onMessage(errText)\n"
            "                                        NuvioToastController.show(errText)\n"
            "                                    }\n"
            "                            }\n"
            "                        },\n"
            "                    ) {\n",
            "                if (plugin.isInstalled) {\n"
            "                    IconButton(\n"
            "                        enabled = plugin.verified && plugin.compatibility.isRunnable,\n"
            "                        onClick = {\n"
            "                            if (CloudStreamExtensionConfigBridge.isSupported) {\n"
            "                                onOpenConfig()\n"
            "                            } else {\n"
            "                                scope.launch {\n"
            "                                    CloudStreamRepository.openPluginSettings(plugin.metadata.id.value)\n"
            "                                        .onFailure { error ->\n"
            "                                            val errText = error.message\n"
            "                                                ?: \"This extension does not provide configurable settings\"\n"
            "                                            onMessage(errText)\n"
            "                                            NuvioToastController.show(errText)\n"
            "                                        }\n"
            "                                }\n"
            "                            }\n"
            "                        },\n"
            "                    ) {\n",
            "CloudStreamPluginCard gear button open CloudStreamExtensionSettingsDialog",
        )

        dialog_code = r'''

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CloudStreamExtensionSettingsDialog(
    plugin: CloudStreamPluginItem,
    onDismiss: () -> Unit,
    onLaunchNativeSettings: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    var snapshot by remember(plugin.metadata.id.value) { mutableStateOf<CloudStreamPluginConfigSnapshot?>(null) }
    var loadError by remember(plugin.metadata.id.value) { mutableStateOf<String?>(null) }
    var isBusy by remember { mutableStateOf(true) }
    var newKey by remember { mutableStateOf("") }
    var newValue by remember { mutableStateOf("") }
    var newType by remember { mutableStateOf("string") }

    LaunchedEffect(plugin.metadata.id.value) {
        isBusy = true
        loadError = null
        CloudStreamExtensionConfigBridge.inspect(plugin)
            .onSuccess { snapshot = it }
            .onFailure { loadError = it.message ?: "Failed to inspect extension settings" }
        isBusy = false
    }

    DialogSurface(
        onDismissRequest = onDismiss,
        modifier = Modifier.fillMaxWidth(0.95f),
        title = "${plugin.metadata.name} Settings",
        properties = DialogProperties(usePlatformDefaultWidth = false),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 460.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            val snap = snapshot
            if (isBusy && snap == null) {
                Text(
                    text = "Loading extension configuration...",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            loadError?.let { err ->
                Text(
                    text = err,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }

            if (snap != null) {
                if (snap.hasNativeSettings) {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.5f)),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Column(
                            modifier = Modifier.padding(12.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Text(
                                text = "Built-in Extension Settings",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                            )
                            Text(
                                text = "Launch ${plugin.metadata.name}'s native dialog, or configure providers, domains, and tokens directly below.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Button(
                                onClick = onLaunchNativeSettings,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Icon(Icons.Rounded.OpenInNew, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Open Native Extension UI")
                            }
                        }
                    }
                }

                if (snap.subProviders.isNotEmpty()) {
                    NuvioSectionLabel(text = "Sub-Providers & Custom Domains (${snap.subProviders.size})")
                    snap.subProviders.forEach { sub ->
                        SubProviderConfigCard(
                            sub = sub,
                            onSave = { enabled, overrideUrl ->
                                scope.launch {
                                    CloudStreamExtensionConfigBridge.updateSubProvider(
                                        plugin = plugin,
                                        apiClassName = sub.apiClassName,
                                        enabled = enabled,
                                        overrideMainUrl = overrideUrl,
                                    ).onSuccess { updated ->
                                        snapshot = updated
                                        NuvioToastController.show("Saved ${sub.name}")
                                    }.onFailure { err ->
                                        NuvioToastController.show(err.message ?: "Could not save provider config")
                                    }
                                }
                            },
                        )
                    }
                }

                NuvioSectionLabel(text = "Extension Tokens & Preferences (${snap.defaultPrefFile})")
                Text(
                    text = "Set extension keys such as FebBox/SuperStream UI token, API keys, cookies, or custom flags.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    listOf(
                        "token" to "string",
                        "cookie" to "string",
                        "tmdb_api" to "string",
                        "domain" to "string",
                    ).forEach { (presetKey, presetType) ->
                        CloudStreamFilterChip(
                            label = "+ $presetKey",
                            selected = newKey == presetKey,
                            onClick = {
                                newKey = presetKey
                                newType = presetType
                            },
                        )
                    }
                }

                snap.preferences.forEach { entry ->
                    PreferenceEntryCard(
                        entry = entry,
                        onSave = { updatedVal ->
                            scope.launch {
                                CloudStreamExtensionConfigBridge.savePreference(
                                    plugin = plugin,
                                    prefFile = entry.prefFile,
                                    key = entry.key,
                                    value = updatedVal,
                                    valueType = entry.valueType,
                                ).onSuccess { updated ->
                                    snapshot = updated
                                    NuvioToastController.show("Saved ${entry.key}")
                                }.onFailure { err ->
                                    NuvioToastController.show(err.message ?: "Failed saving ${entry.key}")
                                }
                            }
                        },
                        onDelete = {
                            scope.launch {
                                CloudStreamExtensionConfigBridge.deletePreference(
                                    plugin = plugin,
                                    prefFile = entry.prefFile,
                                    key = entry.key,
                                ).onSuccess { updated ->
                                    snapshot = updated
                                    NuvioToastController.show("Removed ${entry.key}")
                                }
                            }
                        },
                    )
                }

                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.4f)),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(
                            text = "Add / Set Preference Key",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            listOf("string", "boolean", "int").forEach { t ->
                                CloudStreamFilterChip(
                                    label = t.uppercase(),
                                    selected = newType == t,
                                    onClick = {
                                        newType = t
                                        if (t == "boolean" && newValue !in listOf("true", "false")) {
                                            newValue = "true"
                                        }
                                    },
                                )
                            }
                        }
                        NuvioInputField(
                            value = newKey,
                            onValueChange = { newKey = it },
                            placeholder = "Key name (e.g. token, cookie, proxy_url)",
                        )
                        NuvioInputField(
                            value = newValue,
                            onValueChange = { newValue = it },
                            placeholder = if (newType == "boolean") "true or false" else "Value",
                        )
                        OutlinedButton(
                            enabled = newKey.isNotBlank(),
                            onClick = {
                                val k = newKey.trim()
                                val v = newValue
                                val vt = newType
                                scope.launch {
                                    CloudStreamExtensionConfigBridge.savePreference(
                                        plugin = plugin,
                                        prefFile = snap.defaultPrefFile,
                                        key = k,
                                        value = v,
                                        valueType = vt,
                                    ).onSuccess { updated ->
                                        snapshot = updated
                                        newKey = ""
                                        newValue = ""
                                        NuvioToastController.show("Saved $k")
                                    }.onFailure { err ->
                                        NuvioToastController.show(err.message ?: "Failed saving key")
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(Icons.Rounded.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Save Key")
                        }
                    }
                }
            }
        }

        DialogButtons {
            DialogButton(
                text = "Reload Extension",
                onClick = {
                    scope.launch {
                        CloudStreamExtensionConfigBridge.reloadPlugin(plugin)
                            .onSuccess {
                                snapshot = it
                                NuvioToastController.show("Reloaded ${plugin.metadata.name}")
                            }
                    }
                },
                style = DialogButtonStyle.Secondary,
            )
            DialogButton(
                text = "Done",
                onClick = onDismiss,
                style = DialogButtonStyle.Primary,
            )
        }
    }
}

@Composable
private fun SubProviderConfigCard(
    sub: CloudStreamSubProviderConfig,
    onSave: (enabled: Boolean, overrideUrl: String) -> Unit,
) {
    var urlDraft by remember(sub.apiClassName, sub.overrideMainUrl) {
        mutableStateOf(sub.overrideMainUrl)
    }
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.35f)),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = sub.name,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = "${sub.lang.uppercase()} • Default: ${sub.defaultMainUrl}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Switch(
                    checked = sub.enabled,
                    onCheckedChange = { checked -> onSave(checked, urlDraft) },
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    NuvioInputField(
                        value = urlDraft,
                        onValueChange = { urlDraft = it },
                        placeholder = "Custom domain override (${sub.defaultMainUrl})",
                    )
                }
                IconButton(
                    onClick = { onSave(sub.enabled, urlDraft) },
                ) {
                    Icon(Icons.Rounded.Check, contentDescription = "Save domain")
                }
                if (urlDraft.isNotBlank()) {
                    IconButton(
                        onClick = {
                            urlDraft = ""
                            onSave(sub.enabled, "")
                        },
                    ) {
                        Icon(Icons.Rounded.Refresh, contentDescription = "Reset domain")
                    }
                }
            }
        }
    }
}

@Composable
private fun PreferenceEntryCard(
    entry: CloudStreamPreferenceEntry,
    onSave: (String) -> Unit,
    onDelete: () -> Unit,
) {
    var draft by remember(entry.prefFile, entry.key, entry.value) { mutableStateOf(entry.value) }
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = if (entry.isDiscoveredHint) 0.22f else 0.38f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = entry.key,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = if (entry.isDiscoveredHint) "Detected key (${entry.valueType}) — not set" else "${entry.prefFile} (${entry.valueType})",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (entry.valueType == "boolean") {
                    Switch(
                        checked = draft.equals("true", ignoreCase = true),
                        onCheckedChange = { checked ->
                            val next = checked.toString()
                            draft = next
                            onSave(next)
                        },
                    )
                }
                if (!entry.isDiscoveredHint) {
                    IconButton(onClick = onDelete) {
                        Icon(Icons.Rounded.Delete, contentDescription = "Delete ${entry.key}")
                    }
                }
            }
            if (entry.valueType != "boolean") {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        NuvioInputField(
                            value = draft,
                            onValueChange = { draft = it },
                            placeholder = "Enter ${entry.key}...",
                        )
                    }
                    IconButton(onClick = { onSave(draft) }) {
                        Icon(Icons.Rounded.Check, contentDescription = "Save ${entry.key}")
                    }
                }
            }
        }
    }
}
'''
        current_sec = section_kt.read_text(encoding="utf-8", errors="replace")
        if "fun CloudStreamExtensionSettingsDialog(" not in current_sec:
            section_kt.write_text(current_sec + dialog_code, encoding="utf-8")
            changed = True
        if changed:
            patched.append(str(section_kt.relative_to(root)))

    return patched
