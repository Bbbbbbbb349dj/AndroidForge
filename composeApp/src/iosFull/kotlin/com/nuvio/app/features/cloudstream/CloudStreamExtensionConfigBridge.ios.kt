package com.nuvio.app.features.cloudstream

internal actual object CloudStreamExtensionConfigBridge {
    actual val isSupported: Boolean = false

    actual fun preferNuvioSettingsUi(): Boolean = false

    actual fun setPreferNuvioSettingsUi(enabled: Boolean) = Unit

    actual suspend fun inspect(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot> =
        Result.failure(UnsupportedOperationException("Extension configuration is available on Android full builds"))

    actual suspend fun updateSubProvider(
        plugin: CloudStreamPluginItem,
        apiClassName: String,
        enabled: Boolean,
        overrideMainUrl: String,
    ): Result<CloudStreamPluginConfigSnapshot> = inspect(plugin)

    actual suspend fun toggleInternalSource(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        sourceId: String,
        enabled: Boolean,
    ): Result<CloudStreamPluginConfigSnapshot> = inspect(plugin)

    actual suspend fun setAllInternalSources(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        sourceIds: List<String>,
        enabled: Boolean,
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
