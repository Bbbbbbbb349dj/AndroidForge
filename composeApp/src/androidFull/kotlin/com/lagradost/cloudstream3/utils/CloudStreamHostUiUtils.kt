package com.lagradost.cloudstream3.utils

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
