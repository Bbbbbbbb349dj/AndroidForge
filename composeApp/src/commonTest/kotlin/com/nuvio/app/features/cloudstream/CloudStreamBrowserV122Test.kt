package com.nuvio.app.features.cloudstream

import kotlin.test.*

class CloudStreamBrowserV122Test {
    @Test fun screenshotTypeFiltersRecognizeProviderWireTypes() {
        assertTrue(cloudStreamMatchesBrowserType(listOf("TvSeries"), "Series"))
        assertTrue(cloudStreamMatchesBrowserType(listOf("AnimeMovie"), "Anime"))
        assertTrue(cloudStreamMatchesBrowserType(listOf("TvType.AsianDrama"), "Asian Drama"))
        assertFalse(cloudStreamMatchesBrowserType(listOf("Movie"), "Anime"))
        assertTrue(cloudStreamMatchesBrowserType(emptyList(), null))
        assertEquals(5, cloudStreamBrowserTypes.size)
    }

    @Test fun summaryBucketsAreExclusiveAndIncludeDisabledRepositories() {
        val metadata = CloudStreamRepositoryParser.parsePluginList(
            "https://example.com/repo.json", "https://example.com/plugins.json",
            """[{"name":"Example","internalName":"Example","url":"https://example.com/p.cs3","version":1,"status":1}]""",
        ).single()
        val available = CloudStreamPluginItem(metadata, CloudStreamCompatibilityResolver.resolve(metadata, true))
        val enabled = available.copy(installedVersion = 1, enabled = true)
        val disabled = enabled.copy(enabled = false)
        val summary = cloudStreamExtensionSummary(listOf(available, enabled, disabled))
        assertEquals(CloudStreamExtensionSummary(1, 1, 1), summary)
        assertEquals(3, summary.total)
        assertEquals(CloudStreamExtensionSummary(0, 2, 1),
            cloudStreamExtensionSummary(listOf(available, enabled, disabled), setOf(metadata.repositoryManifestUrl)))
        assertEquals(0, cloudStreamExtensionSummary(emptyList()).total)
    }

    @Test fun fixedFooterFitsBelowMeasuredHeaderAndSafeInsets() {
        assertEquals(624, cloudStreamBrowserViewportHeight(800, 24, 64, 76, 12))
        assertEquals(1, cloudStreamBrowserViewportHeight(200, 24, 64, 176, 12))
    }

    @Test fun languageLabelsKeepUnrecognizedLanguagesVisible() {
        assertTrue(cloudStreamBrowserLanguage("hi").contains("Hindi"))
        assertEquals("XX", cloudStreamBrowserLanguage("xx"))
        assertEquals("Unspecified language", cloudStreamBrowserLanguage(null))
    }
}
