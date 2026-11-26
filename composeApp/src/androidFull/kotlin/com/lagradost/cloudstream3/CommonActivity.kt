package com.lagradost.cloudstream3

import android.app.Activity
import android.widget.Toast
import androidx.annotation.MainThread
import androidx.annotation.StringRes
import com.nuvio.app.core.ui.NuvioToastController
import java.lang.ref.WeakReference

/** Current-activity and Toast ABI used by CloudStream extensions and settings screens. */
object CommonActivity {
    const val TAG = "COMPACT"

    private var activityReference: WeakReference<Activity>? = null

    var activity: Activity?
        get() = activityReference?.get()
        private set(value) {
            activityReference = value?.let(::WeakReference)
        }

    @MainThread
    fun setActivityInstance(newActivity: Activity?) {
        activity = newActivity
    }

    fun showToast(@StringRes message: Int, duration: Int? = null) {
        val act = activity ?: CloudStreamApp.context ?: return
        val text = runCatching { act.getString(message) }.getOrNull() ?: return
        showToast(activity, text, duration)
    }

    fun showToast(message: String?, duration: Int? = null) {
        if (message.isNullOrBlank()) return
        val act = activity
        if (act != null && !act.isFinishing && !act.isDestroyed) {
            act.runOnUiThread {
                showToast(act, message, duration)
            }
        } else {
            NuvioToastController.show(message.trim())
        }
    }

    @MainThread
    fun showToast(act: Activity?, @StringRes message: Int, duration: Int? = null) {
        val ctx = act ?: activity ?: CloudStreamApp.context ?: return
        val text = runCatching { ctx.getString(message) }.getOrNull() ?: return
        showToast(act, text, duration)
    }

    @MainThread
    fun showToast(act: Activity?, message: String?, duration: Int? = null) {
        val trimmed = message?.trim()?.takeIf { it.isNotEmpty() } ?: return
        val target = act ?: activity ?: CloudStreamApp.context
        val toastLength = if (duration == Toast.LENGTH_LONG) Toast.LENGTH_LONG else Toast.LENGTH_SHORT
        if (target != null) {
            runCatching {
                Toast.makeText(target, trimmed, toastLength).show()
            }.onFailure {
                NuvioToastController.show(trimmed)
            }
        } else {
            NuvioToastController.show(trimmed)
        }
    }
}
