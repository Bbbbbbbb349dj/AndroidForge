package com.nuvio.app.features.cloudstream

import android.content.Context
import com.lagradost.cloudstream3.CloudStreamApp
import com.lagradost.cloudstream3.MainAPI
import com.lagradost.cloudstream3.utils.ExtractorApi
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.ConcurrentHashMap
import java.util.zip.ZipFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

internal object CloudStreamExtensionConfigStore {
    private const val CONFIG_PREFS = "nuvio_cloudstream_ext_overrides"
    private const val KEY_PREFER_NUVIO_UI = "prefer_nuvio_settings_ui"
    private val defaultMainUrls = ConcurrentHashMap<String, String>()

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences(CONFIG_PREFS, Context.MODE_PRIVATE)

    private fun enabledKey(pluginId: String, apiClassName: String) =
        "enabled::$pluginId::$apiClassName"

    private fun urlKey(pluginId: String, apiClassName: String) =
        "mainUrl::$pluginId::$apiClassName"

    fun preferNuvioSettingsUi(context: Context?): Boolean {
        val ctx = context ?: return false
        return prefs(ctx).getBoolean(KEY_PREFER_NUVIO_UI, false)
    }

    fun setPreferNuvioSettingsUi(context: Context?, enabled: Boolean) {
        val ctx = context ?: return
        prefs(ctx).edit().putBoolean(KEY_PREFER_NUVIO_UI, enabled).apply()
    }

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
        return providers.filter { api ->
            isSubProviderEnabled(ctx, pluginId, api.javaClass.name)
        }
    }
}

internal actual object CloudStreamExtensionConfigBridge {
    actual val isSupported: Boolean = true

    private const val KEY_DISABLED_PROVIDERS = "disabled_providers"

    private val HINT_KEYWORDS = listOf(
        "token", "cookie", "febbox", "superstream", "wyzie", "debrid", "realdebrid", "torbox",
        "alldebrid", "premiumize", "tmdb", "imdb", "api_key", "apikey", "proxy",
        "domain", "base_url", "baseurl", "custom_url", "host", "mirror", "server",
        "concurrency", "stremio", "quality", "adult", "nsfw", "sub", "dub", "prefer",
    )

    private val HIDDEN_RAW_PREF_KEYS = setOf(
        "disabled_providers",
        "provider_test_status",
        "provider_profiles",
        "enabled_plugins_set",
    )

    actual fun preferNuvioSettingsUi(): Boolean =
        CloudStreamExtensionConfigStore.preferNuvioSettingsUi(
            CloudStreamPlatformRuntime.currentAppContext() ?: CloudStreamApp.context,
        )

    actual fun setPreferNuvioSettingsUi(enabled: Boolean) {
        CloudStreamExtensionConfigStore.setPreferNuvioSettingsUi(
            CloudStreamPlatformRuntime.currentAppContext() ?: CloudStreamApp.context,
            enabled,
        )
    }

    actual suspend fun inspect(plugin: CloudStreamPluginItem): Result<CloudStreamPluginConfigSnapshot> =
        withContext(Dispatchers.IO) {
            runCatching {
                val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                    "Android context is not ready"
                }
                val details = CloudStreamPlatformRuntime.inspectPluginDetails(plugin)
                val providers = details.providers
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
                        supportedTypes = api.supportedTypes.map { it.name },
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
                        listOf(internalClean) +
                        dexScan.prefFileCandidates +
                        listOf(plugin.metadata.internalName, plugin.metadata.name)
                    )
                    .map { it.trim() }
                    .filter { it.isNotBlank() && !it.startsWith("nuvio_") && !it.startsWith("androidx.") }
                    .distinct()

                val primaryPrefFile = candidateFiles.firstOrNull() ?: internalClean.ifBlank { "PluginPrefs" }
                val disabledSet = candidateFiles
                    .flatMap { name ->
                        ctx.getSharedPreferences(name, Context.MODE_PRIVATE)
                            .getStringSet(KEY_DISABLED_PROVIDERS, emptySet())
                            .orEmpty()
                    }
                    .toSet()

                val internalSources = discoverInternalSources(
                    pluginInstance = details.instance,
                    providers = providers,
                    extractors = details.extractors,
                    subProviders = subProviders,
                    dexClassCandidates = dexScan.providerListClasses,
                    disabledIds = disabledSet,
                )

                val entries = mutableListOf<CloudStreamPreferenceEntry>()
                val seenKeys = HashSet<String>()

                for (prefName in candidateFiles) {
                    val sp = ctx.getSharedPreferences(prefName, Context.MODE_PRIVATE)
                    sp.all.entries.sortedBy { it.key }.forEach { (key, rawVal) ->
                        if (key in HIDDEN_RAW_PREF_KEYS || rawVal is Set<*>) return@forEach
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

                CloudStreamApp.getKeys(internalClean).orEmpty().forEach { fullKey ->
                    val shortKey = fullKey.substringAfter('/', fullKey)
                    if (shortKey in HIDDEN_RAW_PREF_KEYS) return@forEach
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

                dexScan.keyCandidates
                    .filterNot { it in HIDDEN_RAW_PREF_KEYS }
                    .take(14)
                    .forEach { hintKey ->
                        if (entries.none { it.key.equals(hintKey, ignoreCase = true) } &&
                            seenKeys.add("$primaryPrefFile::$hintKey")
                        ) {
                            val guessedType = when {
                                hintKey.contains("concurrency", true) || hintKey.endsWith("_count", true) -> "int"
                                hintKey.startsWith("enable", true) ||
                                    hintKey.startsWith("disable", true) ||
                                    hintKey.startsWith("is_", true) ||
                                    hintKey.startsWith("use_", true) ||
                                    hintKey.contains("adult", true) ||
                                    hintKey.contains("nsfw", true) -> "boolean"
                                else -> "string"
                            }
                            entries += CloudStreamPreferenceEntry(
                                prefFile = primaryPrefFile,
                                key = hintKey,
                                value = when (guessedType) {
                                    "boolean" -> "false"
                                    "int" -> "6"
                                    else -> ""
                                },
                                valueType = guessedType,
                                isDiscoveredHint = true,
                            )
                        }
                    }

                CloudStreamPluginConfigSnapshot(
                    pluginId = plugin.metadata.id.value,
                    pluginName = plugin.metadata.name,
                    hasNativeSettings = details.hasNativeSettings,
                    defaultPrefFile = primaryPrefFile,
                    candidatePrefFiles = candidateFiles,
                    subProviders = subProviders,
                    internalSources = internalSources,
                    preferences = entries,
                )
            }
        }

    private fun discoverInternalSources(
        pluginInstance: Any,
        providers: List<MainAPI>,
        extractors: List<ExtractorApi>,
        subProviders: List<CloudStreamSubProviderConfig>,
        dexClassCandidates: List<String>,
        disabledIds: Set<String>,
    ): List<CloudStreamInternalSource> {
        val out = mutableListOf<CloudStreamInternalSource>()
        val seenIds = HashSet<String>()

        val loader = pluginInstance.javaClass.classLoader
        val pkg = pluginInstance.javaClass.`package`?.name.orEmpty()
        val classNames = buildList {
            if (pkg.isNotBlank()) {
                add("$pkg.ProvidersListKt")
                add("$pkg.ProviderListKt")
            }
            addAll(dexClassCandidates)
        }.distinct()

        if (loader != null) {
            for (clsName in classNames) {
                val listObj = runCatching {
                    val cls = Class.forName(clsName, true, loader)
                    val getter = cls.declaredMethods.firstOrNull { m ->
                        m.parameterCount == 0 &&
                            (m.name == "getProviders" || m.name == "buildProviders") &&
                            List::class.java.isAssignableFrom(m.returnType)
                    }
                    getter?.isAccessible = true
                    getter?.invoke(null) as? List<*>
                }.getOrNull()

                listObj?.forEach { item ->
                    if (item == null) return@forEach
                    val id = runCatching {
                        item.javaClass.getMethod("getId").invoke(item) as? String
                    }.getOrNull()?.trim().orEmpty()
                    val name = runCatching {
                        item.javaClass.getMethod("getName").invoke(item) as? String
                    }.getOrNull()?.trim().orEmpty()
                    if (id.isNotEmpty() && seenIds.add("scraper::$id")) {
                        out += CloudStreamInternalSource(
                            id = id,
                            name = name.ifEmpty { id },
                            kind = "Scraper",
                            enabled = id !in disabledIds,
                            canToggle = true,
                        )
                    }
                }
            }
        }

        subProviders.forEach { sub ->
            val key = "api::${sub.apiClassName}"
            if (seenIds.add(key)) {
                val typesLabel = sub.supportedTypes.take(2).joinToString("/")
                out += CloudStreamInternalSource(
                    id = key,
                    name = if (typesLabel.isNotBlank()) "${sub.name} ($typesLabel)" else sub.name,
                    kind = "Provider",
                    enabled = sub.enabled,
                    canToggle = true,
                )
            }
        }

        extractors
            .distinctBy { it.name.lowercase() }
            .sortedBy { it.name.lowercase() }
            .forEach { ext ->
                val extKey = "extractor::${ext.name}"
                if (ext.name.isNotBlank() && seenIds.add(extKey)) {
                    out += CloudStreamInternalSource(
                        id = extKey,
                        name = ext.name,
                        kind = "Extractor",
                        enabled = true,
                        canToggle = false,
                    )
                }
            }

        return out
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

    actual suspend fun toggleInternalSource(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        sourceId: String,
        enabled: Boolean,
    ): Result<CloudStreamPluginConfigSnapshot> = withContext(Dispatchers.IO) {
        runCatching {
            val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                "Android context is not ready"
            }
            if (sourceId.startsWith("api::")) {
                val apiClassName = sourceId.removePrefix("api::")
                val currentUrl = CloudStreamExtensionConfigStore.getOverrideMainUrl(
                    ctx,
                    plugin.metadata.id.value,
                    apiClassName,
                )
                CloudStreamExtensionConfigStore.setSubProviderConfig(
                    context = ctx,
                    pluginId = plugin.metadata.id.value,
                    apiClassName = apiClassName,
                    enabled = enabled,
                    overrideMainUrl = currentUrl,
                )
                return@runCatching inspect(plugin).getOrThrow()
            }

            val targets = listOf(
                prefFile,
                plugin.metadata.internalName.removeSuffix("Plugin"),
                plugin.metadata.name,
            ).map { it.trim() }.filter { it.isNotBlank() }.distinct()

            targets.forEach { fileName ->
                val sp = ctx.getSharedPreferences(fileName, Context.MODE_PRIVATE)
                val updated = HashSet(sp.getStringSet(KEY_DISABLED_PROVIDERS, emptySet()).orEmpty())
                if (enabled) updated.remove(sourceId) else updated.add(sourceId)
                sp.edit().putStringSet(KEY_DISABLED_PROVIDERS, updated).apply()
            }
            inspect(plugin).getOrThrow()
        }
    }

    actual suspend fun setAllInternalSources(
        plugin: CloudStreamPluginItem,
        prefFile: String,
        sourceIds: List<String>,
        enabled: Boolean,
    ): Result<CloudStreamPluginConfigSnapshot> = withContext(Dispatchers.IO) {
        runCatching {
            val ctx = requireNotNull(CloudStreamPlatformRuntime.currentAppContext()) {
                "Android context is not ready"
            }
            val scraperIds = sourceIds.filterNot { it.startsWith("api::") || it.startsWith("extractor::") }
            val apiIds = sourceIds.filter { it.startsWith("api::") }.map { it.removePrefix("api::") }

            apiIds.forEach { apiClassName ->
                val currentUrl = CloudStreamExtensionConfigStore.getOverrideMainUrl(
                    ctx,
                    plugin.metadata.id.value,
                    apiClassName,
                )
                CloudStreamExtensionConfigStore.setSubProviderConfig(
                    context = ctx,
                    pluginId = plugin.metadata.id.value,
                    apiClassName = apiClassName,
                    enabled = enabled,
                    overrideMainUrl = currentUrl,
                )
            }

            if (scraperIds.isNotEmpty()) {
                val targets = listOf(
                    prefFile,
                    plugin.metadata.internalName.removeSuffix("Plugin"),
                    plugin.metadata.name,
                ).map { it.trim() }.filter { it.isNotBlank() }.distinct()

                targets.forEach { fileName ->
                    val sp = ctx.getSharedPreferences(fileName, Context.MODE_PRIVATE)
                    val updated = HashSet(sp.getStringSet(KEY_DISABLED_PROVIDERS, emptySet()).orEmpty())
                    if (enabled) updated.removeAll(scraperIds.toSet()) else updated.addAll(scraperIds)
                    sp.edit().putStringSet(KEY_DISABLED_PROVIDERS, updated).apply()
                }
            }
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
        val providerListClasses: List<String> = emptyList(),
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

            val listClasses = strings.mapNotNull { s ->
                if (s.startsWith("L") && s.endsWith("ProvidersListKt;") && !s.contains('$')) {
                    s.substring(1, s.length - 1).replace('/', '.')
                } else {
                    null
                }
            }.distinct()

            DexPrefScanResult(
                prefFileCandidates = prefFiles,
                keyCandidates = keys,
                providerListClasses = listClasses,
            )
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
        val out = ArrayList<String>(stringIdsSize.coerceAtMost(8192))
        for (i in 0 until stringIdsSize) {
            val idPos = stringIdsOff + i * 4
            if (idPos + 4 > dex.size) break
            var dataOff = buf.getInt(idPos)
            if (dataOff <= 0 || dataOff >= dex.size) continue
            var shift = 0
            var uleb = 0
            while (dataOff < dex.size && shift < 35) {
                val b = dex[dataOff++].toInt() and 0xFF
                uleb = uleb or ((b and 0x7F) shl shift)
                if ((b and 0x80) == 0) break
                shift += 7
            }
            if (uleb in 2..96 && dataOff < dex.size) {
                var end = dataOff
                val maxEnd = (dataOff + 160).coerceAtMost(dex.size)
                while (end < maxEnd && dex[end].toInt() != 0) end++
                val len = end - dataOff
                if (len in 2..96) {
                    out += String(dex, dataOff, len, Charsets.UTF_8)
                }
            }
        }
        return out
    }
}
