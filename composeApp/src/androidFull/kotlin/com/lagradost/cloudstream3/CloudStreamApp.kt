package com.lagradost.cloudstream3

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
