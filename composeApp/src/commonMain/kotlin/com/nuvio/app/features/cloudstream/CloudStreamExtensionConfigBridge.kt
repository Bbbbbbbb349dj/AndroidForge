package com.nuvio.app.features.cloudstream

data class CloudStreamSubProviderConfig(
    val apiClassName: String,
    val name: String,
    val defaultMainUrl: String,
    val overrideMainUrl: String,
    val lang: String,
    val enabled: Boolean,
    val supportedTypes: List<String> = emptyList(),
)

data class CloudStreamInternalSource(
    val id: String,
    val name: String,
    val kind: String, // "Scraper" | "Provider" | "Extractor"
    val enabled: Boolean = true,
    val canToggle: Boolean = true,
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
    val internalSources: List<CloudStreamInternalSource> = emptyList(),
    val preferences: List<CloudStreamPreferenceEntry> = emptyList(),
)

internal expect object CloudStreamExtensionConfigBridge {
    val isSupported: Boolean

    fun preferNuvioSettingsUi(): Boolean

    fun setPreferNuvioSettingsUi(enabled: Boolean)

    suspend fun inspect(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot>

    suspend fun updateSubProvider(
        plugin: CloudStreamPluginItem,
        apiClassName: String,
        enabled: Boolean,
        overrideMainUrl: String,
    ): Result<CloudStreamPluginConfigSnapshot>

    suspend fun toggleInternalSource(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        sourceId: String,
        enabled: Boolean,
    ): Result<CloudStreamPluginConfigSnapshot>

    suspend fun setAllInternalSources(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        sourceIds: List<String>,
        enabled: Boolean,
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
