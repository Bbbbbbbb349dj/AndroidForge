package com.nuvio.app

import androidx.compose.ui.graphics.Color
import com.nuvio.app.core.ui.AppTheme
import com.nuvio.app.core.ui.CatppuccinAccent
import com.nuvio.app.core.ui.CatppuccinFlavor
import com.nuvio.app.core.ui.CatppuccinPalettes
import com.nuvio.app.core.ui.ThemeColors
import com.nuvio.app.features.catalog.CatalogTarget
import com.nuvio.app.features.home.HomeCatalogSection
import com.nuvio.app.features.home.MetaPreview
import com.nuvio.app.features.library.LibraryItem
import com.nuvio.app.features.library.LocalLibraryCategory
import com.nuvio.app.features.library.mergeLibraryItemPreservingLocalMetadata
import com.nuvio.app.features.library.normalizeLocalCategoryKeys
import com.nuvio.app.features.library.toggleLocalCategoryMembership
import com.nuvio.app.features.player.DynamicSwipeSeekCalculator
import com.nuvio.app.features.search.buildSearchAutocompleteSuggestions
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class NuvioV119VerificationTest {
    @Test
    fun libraryWatchStatusTransitionsReplacePreviousStatusWhilePreservingCollections() {
        val initial = mapOf(
            LocalLibraryCategory.PLAN_TO_WATCH.key to true,
            LocalLibraryCategory.FAVOURITES.key to true,
        )
        val afterCompleted = toggleLocalCategoryMembership(
            current = initial,
            toggledKey = LocalLibraryCategory.COMPLETED.key,
        )
        val normalized = normalizeLocalCategoryKeys(
            afterCompleted.filterValues { it }.keys,
        )

        assertTrue(LocalLibraryCategory.COMPLETED.key in normalized)
        assertFalse(LocalLibraryCategory.PLAN_TO_WATCH.key in normalized)
        assertTrue(LocalLibraryCategory.FAVOURITES.key in normalized)
    }

    @Test
    fun librarySyncMergePreservesLocalCategoriesAndEnrichedMetadata() {
        val localSaved = LibraryItem(
            id = "tt15239678",
            type = "movie",
            name = "Dune: Part Two",
            poster = "https://img.example/poster.jpg",
            banner = "https://img.example/banner.jpg",
            description = "Paul Atreides unites with Chani and the Fremen.",
            releaseInfo = "2024",
            imdbRating = "8.5",
            listKeys = setOf(
                LocalLibraryCategory.ON_HOLD.key,
                LocalLibraryCategory.SUBSCRIBED.key,
            ),
            savedAtEpochMs = 1_700_000_000_000L,
        )
        val sparseRemotePayload = LibraryItem(
            id = "tt15239678",
            type = "movie",
            name = "Dune: Part Two",
            poster = null,
            banner = null,
            description = null,
            releaseInfo = null,
            imdbRating = null,
            listKeys = emptySet(),
            savedAtEpochMs = 0L,
        )

        val merged = mergeLibraryItemPreservingLocalMetadata(
            existing = localSaved,
            incoming = sparseRemotePayload,
        )

        assertEquals(
            setOf(LocalLibraryCategory.ON_HOLD.key, LocalLibraryCategory.SUBSCRIBED.key),
            merged.listKeys,
        )
        assertEquals("https://img.example/poster.jpg", merged.poster)
        assertEquals("https://img.example/banner.jpg", merged.banner)
        assertEquals("8.5", merged.imdbRating)
        assertEquals(1_700_000_000_000L, merged.savedAtEpochMs)
    }

    @Test
    fun searchAutocompleteRanksHistoryFirstAndDeduplicatesCatalogItems() {
        val section = HomeCatalogSection(
            key = "cinemeta_movies",
            title = "Popular Movies",
            subtitle = "Featured",
            addonName = "Cinemeta",
            target = CatalogTarget.Addon(
                manifestUrl = "https://v3-cinemeta.strem.io/manifest.json",
                contentType = "movie",
                catalogId = "top",
            ),
            items = listOf(
                MetaPreview(
                    id = "tt0816692",
                    type = "movie",
                    name = "Interstellar",
                    releaseInfo = "2014",
                ),
                MetaPreview(
                    id = "tt0816692_dup",
                    type = "movie",
                    name = "interstellar",
                    releaseInfo = "2014",
                ),
                MetaPreview(
                    id = "tt0133093",
                    type = "movie",
                    name = "The Matrix",
                    releaseInfo = "1999",
                ),
            ),
        )

        val suggestions = buildSearchAutocompleteSuggestions(
            rawQuery = "inter",
            recentSearches = listOf("interstellar soundtrack", "blade runner"),
            sections = listOf(section),
        )

        assertEquals(3, suggestions.size)
        assertTrue(suggestions.first().isHistory)
        assertEquals("interstellar soundtrack", suggestions.first().text)
        assertEquals("Interstellar", suggestions[1].text)
    }

    @Test
    fun dynamicSwipeSeekScalesWithVelocitySensitivityAndClampsDuration() {
        val durationMs = 2L * 3_600_000L
        val widthDp = 400f

        val insideDeadZone = DynamicSwipeSeekCalculator.calculateDeltaMs(
            totalDragDp = 6f,
            velocityDpPerSec = 40f,
            surfaceWidthDp = widthDp,
            durationMs = durationMs,
            sensitivity = 1.0f,
        )
        assertEquals(0L, insideDeadZone)

        val slowSeek = DynamicSwipeSeekCalculator.calculateDeltaMs(
            totalDragDp = 90f,
            velocityDpPerSec = 60f,
            surfaceWidthDp = widthDp,
            durationMs = durationMs,
            sensitivity = 1.0f,
        )
        val mediumSeek = DynamicSwipeSeekCalculator.calculateDeltaMs(
            totalDragDp = 90f,
            velocityDpPerSec = 320f,
            surfaceWidthDp = widthDp,
            durationMs = durationMs,
            sensitivity = 1.0f,
        )
        val fastSeek = DynamicSwipeSeekCalculator.calculateDeltaMs(
            totalDragDp = 90f,
            velocityDpPerSec = 950f,
            surfaceWidthDp = widthDp,
            durationMs = durationMs,
            sensitivity = 1.0f,
        )
        val turboSeek = DynamicSwipeSeekCalculator.calculateDeltaMs(
            totalDragDp = 90f,
            velocityDpPerSec = 950f,
            surfaceWidthDp = widthDp,
            durationMs = durationMs,
            sensitivity = 1.75f,
        )
        val backwardSeek = DynamicSwipeSeekCalculator.calculateDeltaMs(
            totalDragDp = -90f,
            velocityDpPerSec = 320f,
            surfaceWidthDp = widthDp,
            durationMs = durationMs,
            sensitivity = 1.0f,
        )

        assertTrue(slowSeek > 0L)
        assertTrue(mediumSeek > slowSeek)
        assertTrue(fastSeek > mediumSeek)
        assertTrue(turboSeek > fastSeek)
        assertEquals(-mediumSeek, backwardSeek)
        assertEquals(0L, DynamicSwipeSeekCalculator.clampTargetPositionMs(5_000L, -50_000L, durationMs))
        assertEquals(durationMs, DynamicSwipeSeekCalculator.clampTargetPositionMs(durationMs - 2_000L, 50_000L, durationMs))
    }

    @Test
    fun catppuccinPalettesMatchOfficialSpecificationAndLightDarkInvariants() {
        val latte = CatppuccinPalettes.tokensFor(CatppuccinFlavor.LATTE)
        val frappe = CatppuccinPalettes.tokensFor(CatppuccinFlavor.FRAPPE)
        val macchiato = CatppuccinPalettes.tokensFor(CatppuccinFlavor.MACCHIATO)
        val mocha = CatppuccinPalettes.tokensFor(CatppuccinFlavor.MOCHA)

        assertTrue(latte.flavor.isLight)
        assertFalse(frappe.flavor.isLight)
        assertFalse(macchiato.flavor.isLight)
        assertFalse(mocha.flavor.isLight)

        assertEquals(Color(0xFFEFF1F5), latte.base)
        assertEquals(Color(0xFF4C4F69), latte.text)
        assertEquals(Color(0xFF8839EF), latte.mauve)

        assertEquals(Color(0xFF303446), frappe.base)
        assertEquals(Color(0xFFC6D0F5), frappe.text)
        assertEquals(Color(0xFFCA9EE6), frappe.mauve)

        assertEquals(Color(0xFF24273A), macchiato.base)
        assertEquals(Color(0xFFCAD3F5), macchiato.text)
        assertEquals(Color(0xFFC6A0F6), macchiato.mauve)

        assertEquals(Color(0xFF1E1E2E), mocha.base)
        assertEquals(Color(0xFFCDD6F4), mocha.text)
        assertEquals(Color(0xFFCBA6F7), mocha.mauve)

        assertEquals(14, CatppuccinAccent.entries.size)
        CatppuccinAccent.entries.forEach { accent ->
            val lattePalette = CatppuccinPalettes.buildThemeColorPalette(CatppuccinFlavor.LATTE, accent)
            val mochaPalette = CatppuccinPalettes.buildThemeColorPalette(CatppuccinFlavor.MOCHA, accent)
            assertTrue(lattePalette.isLight)
            assertFalse(mochaPalette.isLight)
            assertEquals(latte.base, lattePalette.background)
            assertEquals(mocha.base, mochaPalette.background)
            assertEquals(latte.colorForAccent(accent), lattePalette.secondary)
            assertEquals(mocha.colorForAccent(accent), mochaPalette.secondary)
        }
        assertEquals(latte.base, ThemeColors.getColorPalette(AppTheme.CATPPUCCIN_LATTE).background)
        assertEquals(mocha.base, ThemeColors.getColorPalette(AppTheme.CATPPUCCIN_MOCHA).background)
    }
}
