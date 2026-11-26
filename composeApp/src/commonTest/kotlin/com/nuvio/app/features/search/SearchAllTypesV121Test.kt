package com.nuvio.app.features.search

import com.nuvio.app.features.addons.AddonCatalog
import com.nuvio.app.features.addons.AddonExtraProperty
import com.nuvio.app.features.addons.AddonManifestParser
import kotlin.test.*

class SearchAllTypesV121Test {
    @Test fun moviesSeriesAndCustomTypesAreSearchable() {
        listOf("movie", "series", "anime.series", "anime.movie").forEach { type ->
            assertTrue(AddonCatalog(type, "popular.$type", "Popular", listOf(AddonExtraProperty("search"))).supportsSearch())
        }
    }

    @Test fun noRequestsForNonSearchCatalogsOrUnsatisfiedRequiredParameters() {
        assertFalse(AddonCatalog("movie", "popular", "Popular").supportsSearch())
        assertFalse(AddonCatalog("movie", "popular", "Popular", listOf(
            AddonExtraProperty("search"), AddonExtraProperty("unknown", isRequired = true),
        )).supportsSearch())
    }

    @Test fun legacyExtraSupportedManifestsAreNotLost() {
        val manifest = AddonManifestParser.parse("https://example.test/manifest.json", """
            {"id":"legacy","name":"Legacy","version":"1.0.0","types":["movie","series"],
             "resources":["catalog"],"catalogs":[
               {"type":"movie","id":"popular.movies","extraSupported":["search","skip"]},
               {"type":"series","id":"popular.series","extra":[{"name":"search"}]}]}
        """.trimIndent())
        assertEquals(2, manifest.catalogs.count { it.supportsSearch() })
    }
}
