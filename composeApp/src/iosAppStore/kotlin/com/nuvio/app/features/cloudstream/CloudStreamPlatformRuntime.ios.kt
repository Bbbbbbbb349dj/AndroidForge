package com.nuvio.app.features.cloudstream

internal actual object CloudStreamPlatformRuntime {
    actual val supportsAndroidDex: Boolean = false

    actual fun initialize(context: Any?) = Unit
    actual suspend fun provider(plugin: CloudStreamPluginItem): CloudStreamProvider? = null
    actual suspend fun openSettings(plugin: CloudStreamPluginItem): Result<Unit> = Result.failure(UnsupportedOperationException("CloudStream extension settings are available only in Android full builds"))
    // No syncDynamicRepositories: the expect object declares no such member
    // and nothing calls it; the stale actual broke the iOS build.
    actual suspend fun registerNativeRepository(url: String, name: String, iconUrl: String?) = Unit
    actual suspend fun removeNativeRepository(url: String) = Unit
    actual fun unload(pluginId: String) = Unit
    actual fun clear() = Unit
}
