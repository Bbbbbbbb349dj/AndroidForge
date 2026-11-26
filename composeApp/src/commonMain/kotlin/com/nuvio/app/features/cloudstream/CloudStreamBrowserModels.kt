package com.nuvio.app.features.cloudstream

/** Mutually exclusive buckets; disabling a repository also disables its installed extensions. */
internal data class CloudStreamExtensionSummary(val downloaded: Int, val disabled: Int, val available: Int) {
    val total: Int get() = downloaded + disabled + available
}

internal fun cloudStreamExtensionSummary(
    plugins: List<CloudStreamPluginItem>,
    disabledRepositories: Set<String> = emptySet(),
): CloudStreamExtensionSummary = CloudStreamExtensionSummary(
    downloaded = plugins.count { it.isInstalled && it.enabled && it.metadata.repositoryManifestUrl !in disabledRepositories },
    disabled = plugins.count { it.isInstalled && (!it.enabled || it.metadata.repositoryManifestUrl in disabledRepositories) },
    available = plugins.count { !it.isInstalled },
)

internal val cloudStreamBrowserTypes = listOf("Movie", "Series", "Anime", "Cartoon", "Asian Drama")

internal fun cloudStreamMatchesBrowserType(rawTypes: List<String>, selected: String?): Boolean {
    if (selected == null) return true
    val accepted = when (selected) {
        "Movie" -> setOf("movie")
        "Series" -> setOf("tvseries", "series")
        "Anime" -> setOf("anime", "animemovie", "ova")
        "Cartoon" -> setOf("cartoon")
        "Asian Drama" -> setOf("asiandrama")
        else -> setOf(selected.lowercase().replace(" ", ""))
    }
    return rawTypes.any { it.substringAfterLast('.').lowercase().replace(" ", "") in accepted }
}

internal fun cloudStreamBrowserLanguage(code: String?): String = when (code?.lowercase()) {
    "en" -> "🇬🇧 English"
    "hi" -> "🇮🇳 Hindi"
    "ta" -> "🇮🇳 Tamil"
    "te" -> "🇮🇳 Telugu"
    "ml" -> "🇮🇳 Malayalam"
    "bn" -> "🇧🇩 Bengali"
    "es" -> "🇪🇸 Spanish"
    "es-mx" -> "🇲🇽 Spanish (Mexico)"
    "de" -> "🇩🇪 German"
    "fr" -> "🇫🇷 French"
    "ja" -> "🇯🇵 Japanese"
    "ko" -> "🇰🇷 Korean"
    "tr" -> "🇹🇷 Turkish"
    "ar" -> "Arabic"
    "pt", "pt-br" -> "Portuguese"
    "multi", "all" -> "Multi-language"
    null, "" -> "Unspecified language"
    else -> code.uppercase()
}

/** Remaining Settings viewport after its measured pinned header, spacing and safe insets. */
internal fun cloudStreamBrowserViewportHeight(
    viewport: Int,
    beforePadding: Int,
    afterPadding: Int,
    chromeHeight: Int,
    gaps: Int,
): Int = (viewport - beforePadding - afterPadding - chromeHeight - gaps).coerceAtLeast(1)
