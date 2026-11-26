package com.lagradost.cloudstream3

import android.content.Context

/** Legacy CloudStream host ABI still referenced by several popular .cs3 extensions. */
class AcraApplication {
    companion object {
        val context: Context?
            get() = CloudStreamApp.context

        fun removeKeys(folder: String): Int? = CloudStreamApp.removeKeys(folder)

        fun <T> setKey(path: String, value: T) = CloudStreamApp.setKey(path, value)

        fun <T> setKey(folder: String, path: String, value: T) =
            CloudStreamApp.setKey(folder, path, value)

        inline fun <reified T : Any> getKey(path: String, defVal: T?): T? =
            CloudStreamApp.getKey(path, defVal)

        inline fun <reified T : Any> getKey(path: String): T? =
            CloudStreamApp.getKey(path)

        inline fun <reified T : Any> getKey(folder: String, path: String): T? =
            CloudStreamApp.getKey(folder, path)

        inline fun <reified T : Any> getKey(folder: String, path: String, defVal: T?): T? =
            CloudStreamApp.getKey(folder, path, defVal)

        fun removeKey(path: String) = CloudStreamApp.removeKey(path)

        fun removeKey(folder: String, path: String) = CloudStreamApp.removeKey(folder, path)

        fun getKeys(folder: String): List<String>? = CloudStreamApp.getKeys(folder)
    }
}
