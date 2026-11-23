#!/usr/bin/env python3
"""Nuvio Enhanced v1.19 — Module 3:
- Phase 9: Official Catppuccin Theme System (Latte Light + Frappé / Macchiato / Mocha Dark + 14 Official Accents + System Bar Contrast)
- Phase 10: Complete Purge of 'Support Nuvio Enhanced 2.0' & 'raja_ji' / 'RAJA JI' + Configurable Buy Me a Coffee Card
- Settings UI polish: Catppuccin Flavor Showcase & Accent Picker, Library Category Bar Position, & Swipe Seek Sensitivity
"""

from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[{label}] Expected anchor not found in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] Anchor matched {count} times in {path} (expected 1)")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 9 — Official Catppuccin Palette, Light/Dark ColorSchemes & System Bars
# ---------------------------------------------------------------------------

def patch_catppuccin_theme_engine(source_dir: Path) -> None:
    # 1. Create CatppuccinPalette.kt with all 104 official Catppuccin tokens (4 flavors x 26 colors)
    cat_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/CatppuccinPalette.kt"
    cat_path.write_text(
        r"""package com.nuvio.app.core.ui

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import kotlinx.serialization.Serializable

@Serializable
enum class CatppuccinFlavor(
    val displayName: String,
    val subtitle: String,
    val isLight: Boolean,
) {
    LATTE(
        displayName = "Catppuccin Latte",
        subtitle = "Warm crisp light",
        isLight = true,
    ),
    FRAPPE(
        displayName = "Catppuccin Frappé",
        subtitle = "Subdued cool dark",
        isLight = false,
    ),
    MACCHIATO(
        displayName = "Catppuccin Macchiato",
        subtitle = "Medium contrast dark",
        isLight = false,
    ),
    MOCHA(
        displayName = "Catppuccin Mocha",
        subtitle = "Deep cozy dark",
        isLight = false,
    ),
}

@Serializable
enum class CatppuccinAccent(val displayName: String) {
    ROSEWATER("Rosewater"),
    FLAMINGO("Flamingo"),
    PINK("Pink"),
    MAUVE("Mauve"),
    RED("Red"),
    MAROON("Maroon"),
    PEACH("Peach"),
    YELLOW("Yellow"),
    GREEN("Green"),
    TEAL("Teal"),
    SKY("Sky"),
    SAPPHIRE("Sapphire"),
    BLUE("Blue"),
    LAVENDER("Lavender"),
}

data class CatppuccinFlavorTokens(
    val flavor: CatppuccinFlavor,
    val rosewater: Color,
    val flamingo: Color,
    val pink: Color,
    val mauve: Color,
    val red: Color,
    val maroon: Color,
    val peach: Color,
    val yellow: Color,
    val green: Color,
    val teal: Color,
    val sky: Color,
    val sapphire: Color,
    val blue: Color,
    val lavender: Color,
    val text: Color,
    val subtext1: Color,
    val subtext0: Color,
    val overlay2: Color,
    val overlay1: Color,
    val overlay0: Color,
    val surface2: Color,
    val surface1: Color,
    val surface0: Color,
    val base: Color,
    val mantle: Color,
    val crust: Color,
) {
    fun colorForAccent(accent: CatppuccinAccent): Color = when (accent) {
        CatppuccinAccent.ROSEWATER -> rosewater
        CatppuccinAccent.FLAMINGO -> flamingo
        CatppuccinAccent.PINK -> pink
        CatppuccinAccent.MAUVE -> mauve
        CatppuccinAccent.RED -> red
        CatppuccinAccent.MAROON -> maroon
        CatppuccinAccent.PEACH -> peach
        CatppuccinAccent.YELLOW -> yellow
        CatppuccinAccent.GREEN -> green
        CatppuccinAccent.TEAL -> teal
        CatppuccinAccent.SKY -> sky
        CatppuccinAccent.SAPPHIRE -> sapphire
        CatppuccinAccent.BLUE -> blue
        CatppuccinAccent.LAVENDER -> lavender
    }

    fun secondaryCompanionFor(accent: CatppuccinAccent): Color = when (accent) {
        CatppuccinAccent.ROSEWATER -> flamingo
        CatppuccinAccent.FLAMINGO -> pink
        CatppuccinAccent.PINK -> mauve
        CatppuccinAccent.MAUVE -> lavender
        CatppuccinAccent.RED -> maroon
        CatppuccinAccent.MAROON -> peach
        CatppuccinAccent.PEACH -> yellow
        CatppuccinAccent.YELLOW -> peach
        CatppuccinAccent.GREEN -> teal
        CatppuccinAccent.TEAL -> sapphire
        CatppuccinAccent.SKY -> sapphire
        CatppuccinAccent.SAPPHIRE -> blue
        CatppuccinAccent.BLUE -> lavender
        CatppuccinAccent.LAVENDER -> mauve
    }
}

object CatppuccinPalettes {
    var activeAccent: CatppuccinAccent = CatppuccinAccent.MAUVE

    val Latte = CatppuccinFlavorTokens(
        flavor = CatppuccinFlavor.LATTE,
        rosewater = Color(0xFFDC8A78),
        flamingo = Color(0xFFDD7878),
        pink = Color(0xFFEA76CB),
        mauve = Color(0xFF8839EF),
        red = Color(0xFFD20F39),
        maroon = Color(0xFFE64553),
        peach = Color(0xFFFE640B),
        yellow = Color(0xFFDF8E1D),
        green = Color(0xFF40A02B),
        teal = Color(0xFF179299),
        sky = Color(0xFF04A5E5),
        sapphire = Color(0xFF209FB5),
        blue = Color(0xFF1E66F5),
        lavender = Color(0xFF7287FD),
        text = Color(0xFF4C4F69),
        subtext1 = Color(0xFF5C5F77),
        subtext0 = Color(0xFF6C6F85),
        overlay2 = Color(0xFF7C7F93),
        overlay1 = Color(0xFF8C8FA1),
        overlay0 = Color(0xFF9CA0B0),
        surface2 = Color(0xFFACB0BE),
        surface1 = Color(0xFFBCC0CC),
        surface0 = Color(0xFFCCD0DA),
        base = Color(0xFFEFF1F5),
        mantle = Color(0xFFE6E9EF),
        crust = Color(0xFFDCE0E8),
    )

    val Frappe = CatppuccinFlavorTokens(
        flavor = CatppuccinFlavor.FRAPPE,
        rosewater = Color(0xFFF2D5CF),
        flamingo = Color(0xFFEEBEBE),
        pink = Color(0xFFF4B8E4),
        mauve = Color(0xFFCA9EE6),
        red = Color(0xFFE78284),
        maroon = Color(0xFFEA999C),
        peach = Color(0xFFEF9F76),
        yellow = Color(0xFFE5C890),
        green = Color(0xFFA6D189),
        teal = Color(0xFF81C8BE),
        sky = Color(0xFF99D1DB),
        sapphire = Color(0xFF85C1DC),
        blue = Color(0xFF8CAAEE),
        lavender = Color(0xFFBABBF1),
        text = Color(0xFFC6D0F5),
        subtext1 = Color(0xFFB5BFE2),
        subtext0 = Color(0xFFA5ADCE),
        overlay2 = Color(0xFF949CBB),
        overlay1 = Color(0xFF838BA7),
        overlay0 = Color(0xFF737994),
        surface2 = Color(0xFF626880),
        surface1 = Color(0xFF51576D),
        surface0 = Color(0xFF414559),
        base = Color(0xFF303446),
        mantle = Color(0xFF292C3C),
        crust = Color(0xFF232634),
    )

    val Macchiato = CatppuccinFlavorTokens(
        flavor = CatppuccinFlavor.MACCHIATO,
        rosewater = Color(0xFFF4DBD6),
        flamingo = Color(0xFFF0C6C6),
        pink = Color(0xFFF5BDE6),
        mauve = Color(0xFFC6A0F6),
        red = Color(0xFFED8796),
        maroon = Color(0xFFEE99A0),
        peach = Color(0xFFF5A97F),
        yellow = Color(0xFFEED49F),
        green = Color(0xFFA6DA95),
        teal = Color(0xFF8BD5CA),
        sky = Color(0xFF91D7E3),
        sapphire = Color(0xFF7DC4E4),
        blue = Color(0xFF8AADF4),
        lavender = Color(0xFFB7BDF8),
        text = Color(0xFFCAD3F5),
        subtext1 = Color(0xFFB8C0E0),
        subtext0 = Color(0xFFA5ADCB),
        overlay2 = Color(0xFF939AB7),
        overlay1 = Color(0xFF8087A2),
        overlay0 = Color(0xFF6E738D),
        surface2 = Color(0xFF5B6078),
        surface1 = Color(0xFF494D64),
        surface0 = Color(0xFF363A4F),
        base = Color(0xFF24273A),
        mantle = Color(0xFF1E2030),
        crust = Color(0xFF181926),
    )

    val Mocha = CatppuccinFlavorTokens(
        flavor = CatppuccinFlavor.MOCHA,
        rosewater = Color(0xFFF5E0DC),
        flamingo = Color(0xFFF2CDCD),
        pink = Color(0xFFF5C2E7),
        mauve = Color(0xFFCBA6F7),
        red = Color(0xFFF38BA8),
        maroon = Color(0xFFEBA0AC),
        peach = Color(0xFFFAB387),
        yellow = Color(0xFFF9E2AF),
        green = Color(0xFFA6E3A1),
        teal = Color(0xFF94E2D5),
        sky = Color(0xFF89DCEB),
        sapphire = Color(0xFF74C7EC),
        blue = Color(0xFF89B4FA),
        lavender = Color(0xFFB4BEFE),
        text = Color(0xFFCDD6F4),
        subtext1 = Color(0xFFBAC2DE),
        subtext0 = Color(0xFFA6ADC8),
        overlay2 = Color(0xFF9399B2),
        overlay1 = Color(0xFF7F849C),
        overlay0 = Color(0xFF6C7086),
        surface2 = Color(0xFF585B70),
        surface1 = Color(0xFF45475A),
        surface0 = Color(0xFF313244),
        base = Color(0xFF1E1E2E),
        mantle = Color(0xFF181825),
        crust = Color(0xFF11111B),
    )

    fun tokensFor(flavor: CatppuccinFlavor): CatppuccinFlavorTokens = when (flavor) {
        CatppuccinFlavor.LATTE -> Latte
        CatppuccinFlavor.FRAPPE -> Frappe
        CatppuccinFlavor.MACCHIATO -> Macchiato
        CatppuccinFlavor.MOCHA -> Mocha
    }

    fun buildThemeColorPalette(
        flavor: CatppuccinFlavor,
        accent: CatppuccinAccent = activeAccent,
    ): ThemeColorPalette {
        val t = tokensFor(flavor)
        val primary = t.colorForAccent(accent)
        val secondary = t.secondaryCompanionFor(accent)
        val onPrimary = if (primary.luminance() > 0.44f) t.crust else Color(0xFFEFF1F5)
        val onSecondary = if (secondary.luminance() > 0.44f) t.crust else Color(0xFFEFF1F5)
        return ThemeColorPalette(
            secondary = primary,
            secondaryVariant = secondary,
            accentGradient = listOf(primary, secondary),
            nativeAccentHex = primary.toThemeHex(),
            onSecondary = onPrimary,
            onSecondaryVariant = onSecondary,
            focusRing = primary,
            focusBackground = if (t.flavor.isLight) {
                primary.copy(alpha = 0.16f)
            } else {
                t.surface1
            },
            background = t.base,
            backgroundElevated = if (t.flavor.isLight) t.mantle else t.mantle,
            backgroundCard = t.surface0,
            isLight = t.flavor.isLight,
            textPrimary = t.text,
            textSecondary = t.subtext1,
            textMuted = t.subtext0,
            borderDefault = t.surface1,
            borderStrong = t.surface2,
            errorColor = t.red,
            onErrorColor = if (t.flavor.isLight) t.base else t.crust,
            warningColor = t.yellow,
            successColor = t.green,
            infoColor = t.sapphire,
        )
    }
}
""",
        encoding="utf-8",
    )

    # 2. composeResources/values/strings.xml — add Catppuccin theme labels + clean Buy Me a Coffee copy
    strings_path = source_dir / "composeApp/src/commonMain/composeResources/values/strings.xml"
    _replace_once(
        strings_path,
        """    <string name="theme_graphite">Graphite</string>""",
        """    <string name="theme_graphite">Graphite</string>
    <string name="theme_catppuccin_latte">Latte</string>
    <string name="theme_catppuccin_frappe">Frappé</string>
    <string name="theme_catppuccin_macchiato">Macchiato</string>
    <string name="theme_catppuccin_mocha">Mocha</string>""",
        "strings.catppuccinThemeNames",
    )

    _replace_once(
        strings_path,
        r"""    <string name="support_buymeacoffee_title">Support Nuvio Enhanced 2.0</string>
    <string name="support_buymeacoffee_message">Every update of Nuvio Enhanced 2.0 comes from one person\'s free time — no team, no sponsors, no ads. A small coffee from you means this app stays free and keeps getting better.</string>
    <string name="support_buymeacoffee_button">Buy Me a Coffee</string>""",
        r"""    <string name="support_buymeacoffee_title">Buy Me a Coffee</string>
    <string name="support_buymeacoffee_message">Enjoying Nuvio Enhanced? Buy the developer a coffee to help keep independent releases polished, fast, and ad-free.</string>
    <string name="support_buymeacoffee_button">Buy Me a Coffee</string>""",
        "strings.cleanBuyMeACoffeeCopy",
    )

    # 3. AppTheme.kt — register all 4 Catppuccin flavors & helpers
    app_theme_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/AppTheme.kt"
    _replace_once(
        app_theme_path,
        """import nuvio.composeapp.generated.resources.theme_arctic_blue
import nuvio.composeapp.generated.resources.theme_graphite
import org.jetbrains.compose.resources.StringResource""",
        """import nuvio.composeapp.generated.resources.theme_arctic_blue
import nuvio.composeapp.generated.resources.theme_catppuccin_frappe
import nuvio.composeapp.generated.resources.theme_catppuccin_latte
import nuvio.composeapp.generated.resources.theme_catppuccin_macchiato
import nuvio.composeapp.generated.resources.theme_catppuccin_mocha
import nuvio.composeapp.generated.resources.theme_graphite
import org.jetbrains.compose.resources.StringResource""",
        "AppTheme.imports",
    )

    _replace_once(
        app_theme_path,
        """    ARCTIC_BLUE,
    GRAPHITE,
}""",
        """    ARCTIC_BLUE,
    GRAPHITE,
    CATPPUCCIN_LATTE,
    CATPPUCCIN_FRAPPE,
    CATPPUCCIN_MACCHIATO,
    CATPPUCCIN_MOCHA,
}

val AppTheme.catppuccinFlavorOrNull: CatppuccinFlavor?
    get() = when (this) {
        AppTheme.CATPPUCCIN_LATTE -> CatppuccinFlavor.LATTE
        AppTheme.CATPPUCCIN_FRAPPE -> CatppuccinFlavor.FRAPPE
        AppTheme.CATPPUCCIN_MACCHIATO -> CatppuccinFlavor.MACCHIATO
        AppTheme.CATPPUCCIN_MOCHA -> CatppuccinFlavor.MOCHA
        else -> null
    }

val AppTheme.isCatppuccin: Boolean
    get() = catppuccinFlavorOrNull != null""",
        "AppTheme.enumEntries",
    )

    _replace_once(
        app_theme_path,
        """        AppTheme.ARCTIC_BLUE -> Res.string.theme_arctic_blue
        AppTheme.GRAPHITE -> Res.string.theme_graphite
    }""",
        """        AppTheme.ARCTIC_BLUE -> Res.string.theme_arctic_blue
        AppTheme.GRAPHITE -> Res.string.theme_graphite
        AppTheme.CATPPUCCIN_LATTE -> Res.string.theme_catppuccin_latte
        AppTheme.CATPPUCCIN_FRAPPE -> Res.string.theme_catppuccin_frappe
        AppTheme.CATPPUCCIN_MACCHIATO -> Res.string.theme_catppuccin_macchiato
        AppTheme.CATPPUCCIN_MOCHA -> Res.string.theme_catppuccin_mocha
    }""",
        "AppTheme.labelRes",
    )

    # 4. ThemeColors.kt — extend ThemeColorPalette with light/dark semantic tokens & wire Catppuccin palettes
    theme_colors_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/ThemeColors.kt"
    _replace_once(
        theme_colors_path,
        """data class ThemeColorPalette(
    val secondary: Color,
    val secondaryVariant: Color,
    val accentGradient: List<Color> = listOf(secondary),
    val nativeAccentHex: String,
    val onSecondary: Color = Color.White,
    val onSecondaryVariant: Color = Color.White,
    val focusRing: Color,
    val focusBackground: Color,
    val background: Color = Color(0xFF0D0D0D),
    val backgroundElevated: Color = Color(0xFF1A1A1A),
    val backgroundCard: Color = Color(0xFF242424),
)""",
        """data class ThemeColorPalette(
    val secondary: Color,
    val secondaryVariant: Color,
    val accentGradient: List<Color> = listOf(secondary),
    val nativeAccentHex: String,
    val onSecondary: Color = Color.White,
    val onSecondaryVariant: Color = Color.White,
    val focusRing: Color,
    val focusBackground: Color,
    val background: Color = Color(0xFF0D0D0D),
    val backgroundElevated: Color = Color(0xFF1A1A1A),
    val backgroundCard: Color = Color(0xFF242424),
    val isLight: Boolean = false,
    val textPrimary: Color = Color(0xFFF5F7F8),
    val textSecondary: Color = Color(0xFFB8BEC5),
    val textMuted: Color = Color(0xFF969CA3),
    val borderDefault: Color = Color(0xFF252A2A),
    val borderStrong: Color = Color(0xFF3A4040),
    val errorColor: Color = Color(0xFFE36A8A),
    val onErrorColor: Color = Color(0xFFFCE5EC),
    val warningColor: Color = Color(0xFFFFC857),
    val successColor: Color = Color(0xFF66BB6A),
    val infoColor: Color = Color(0xFF42A5F5),
)""",
        "ThemeColors.paletteFields",
    )

    _replace_once(
        theme_colors_path,
        """    fun getColorPalette(
        theme: AppTheme,
        customFirst: Color = ThemeAccentColor.PINK.color,
        customSecond: Color = ThemeAccentColor.CYAN.color,
    ): ThemeColorPalette {""",
        """    fun getColorPalette(
        theme: AppTheme,
        customFirst: Color = ThemeAccentColor.PINK.color,
        customSecond: Color = ThemeAccentColor.CYAN.color,
        catppuccinAccent: CatppuccinAccent = CatppuccinPalettes.activeAccent,
    ): ThemeColorPalette {""",
        "ThemeColors.getColorPaletteSig",
    )

    _replace_once(
        theme_colors_path,
        """            AppTheme.ARCTIC_BLUE -> ArcticBlue
            AppTheme.GRAPHITE -> Graphite
        }
    }""",
        """            AppTheme.ARCTIC_BLUE -> ArcticBlue
            AppTheme.GRAPHITE -> Graphite
            AppTheme.CATPPUCCIN_LATTE -> CatppuccinPalettes.buildThemeColorPalette(CatppuccinFlavor.LATTE, catppuccinAccent)
            AppTheme.CATPPUCCIN_FRAPPE -> CatppuccinPalettes.buildThemeColorPalette(CatppuccinFlavor.FRAPPE, catppuccinAccent)
            AppTheme.CATPPUCCIN_MACCHIATO -> CatppuccinPalettes.buildThemeColorPalette(CatppuccinFlavor.MACCHIATO, catppuccinAccent)
            AppTheme.CATPPUCCIN_MOCHA -> CatppuccinPalettes.buildThemeColorPalette(CatppuccinFlavor.MOCHA, catppuccinAccent)
        }
    }""",
        "ThemeColors.getColorPaletteCatppuccin",
    )

    # 5. Tokens.kt — respect palette.isLight and semantic Catppuccin tokens
    tokens_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/Tokens.kt"
    _replace_once(
        tokens_path,
        """internal fun defaultNuvioThemeTokens(
    palette: ThemeColorPalette,
    amoled: Boolean,
    colorScheme: ColorScheme?,
): NuvioThemeTokens {
    val background = if (amoled) Color.Black else palette.background
    val textPrimary = Color(0xFFF5F7F8)
    val textSecondary = Color(0xFFB8BEC5)
    val textMuted = Color(0xFF969CA3)
    val surface = palette.backgroundElevated
    val surfaceCard = palette.backgroundCard
    val accent = palette.secondary
    val accentStrong = palette.secondaryVariant
    val borderSubtle = Color(0xFF252A2A).copy(alpha = 0.55f)
    val borderDefault = Color(0xFF252A2A)
    val overlayScrim = Color.Black.copy(alpha = NuvioTokens.Opacity.overlayMedium)

    return NuvioThemeTokens(
        colors = NuvioColorTokens(
            background = background,
            backgroundAmoled = Color.Black,
            surface = surface,
            surfaceElevated = surface,
            surfaceCard = surfaceCard,
            surfaceSheet = surface,
            surfaceDialog = surface,
            surfacePopover = surfaceCard,
            nativeChrome = background,
            textPrimary = textPrimary,
            textSecondary = textSecondary,
            textMuted = textMuted,
            textDisabled = textMuted.copy(alpha = NuvioTokens.Opacity.disabled),
            textInverse = Color(0xFF111111),
            accent = accent,
            accentStrong = accentStrong,
            onAccent = palette.onSecondary,
            focusRing = palette.focusRing,
            focusBackground = palette.focusBackground,
            borderSubtle = borderSubtle,
            borderDefault = borderDefault,
            borderStrong = Color(0xFF3A4040),
            borderFocus = palette.focusRing,
            borderSelected = accent.copy(alpha = NuvioTokens.Opacity.strong),
            success = Color(0xFF66BB6A),
            warning = Color(0xFFFFC857),
            danger = colorScheme?.error ?: Color(0xFFE36A8A),
            info = Color(0xFF42A5F5),
            neutral = textMuted,
            overlayScrim = overlayScrim,
            overlayHover = Color.White.copy(alpha = NuvioTokens.Opacity.hover),
            overlayPressed = Color.White.copy(alpha = NuvioTokens.Opacity.pressed),
            overlaySelected = Color.White.copy(alpha = NuvioTokens.Opacity.selected),
            overlayDisabled = Color.Black.copy(alpha = NuvioTokens.Opacity.disabled),
            shimmer = Color.White.copy(alpha = 0.10f),
            skeleton = Color.White.copy(alpha = 0.06f),""",
        """internal fun defaultNuvioThemeTokens(
    palette: ThemeColorPalette,
    amoled: Boolean,
    colorScheme: ColorScheme?,
): NuvioThemeTokens {
    val effectiveAmoled = amoled && !palette.isLight
    val background = if (effectiveAmoled) Color.Black else palette.background
    val textPrimary = palette.textPrimary
    val textSecondary = palette.textSecondary
    val textMuted = palette.textMuted
    val surface = palette.backgroundElevated
    val surfaceCard = palette.backgroundCard
    val accent = palette.secondary
    val accentStrong = palette.secondaryVariant
    val borderSubtle = palette.borderDefault.copy(alpha = if (palette.isLight) 0.72f else 0.55f)
    val borderDefault = palette.borderDefault
    val overlayScrim = Color.Black.copy(alpha = if (palette.isLight) 0.42f else NuvioTokens.Opacity.overlayMedium)
    val interactiveTint = if (palette.isLight) palette.textPrimary else Color.White

    return NuvioThemeTokens(
        colors = NuvioColorTokens(
            background = background,
            backgroundAmoled = if (palette.isLight) palette.background else Color.Black,
            surface = surface,
            surfaceElevated = surface,
            surfaceCard = surfaceCard,
            surfaceSheet = surface,
            surfaceDialog = surface,
            surfacePopover = surfaceCard,
            nativeChrome = background,
            textPrimary = textPrimary,
            textSecondary = textSecondary,
            textMuted = textMuted,
            textDisabled = textMuted.copy(alpha = NuvioTokens.Opacity.disabled),
            textInverse = if (palette.isLight) Color(0xFFEFF1F5) else Color(0xFF111111),
            accent = accent,
            accentStrong = accentStrong,
            onAccent = palette.onSecondary,
            focusRing = palette.focusRing,
            focusBackground = palette.focusBackground,
            borderSubtle = borderSubtle,
            borderDefault = borderDefault,
            borderStrong = palette.borderStrong,
            borderFocus = palette.focusRing,
            borderSelected = accent.copy(alpha = NuvioTokens.Opacity.strong),
            success = palette.successColor,
            warning = palette.warningColor,
            danger = colorScheme?.error ?: palette.errorColor,
            info = palette.infoColor,
            neutral = textMuted,
            overlayScrim = overlayScrim,
            overlayHover = interactiveTint.copy(alpha = NuvioTokens.Opacity.hover),
            overlayPressed = interactiveTint.copy(alpha = NuvioTokens.Opacity.pressed),
            overlaySelected = interactiveTint.copy(alpha = NuvioTokens.Opacity.selected),
            overlayDisabled = interactiveTint.copy(alpha = NuvioTokens.Opacity.disabled),
            shimmer = interactiveTint.copy(alpha = if (palette.isLight) 0.14f else 0.10f),
            skeleton = interactiveTint.copy(alpha = if (palette.isLight) 0.09f else 0.06f),""",
        "Tokens.lightDarkAwareTokens",
    )

    # 6. AppSystemUiController (commonMain, androidMain, iosMain) — light/dark system bar icon appearance
    sys_common = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/AppSystemUiController.kt"
    sys_common.write_text(
        """package com.nuvio.app.core.ui

internal expect object AppSystemUiController {
    fun setStatusBarVisible(visible: Boolean)
    fun setLightSystemBars(isLight: Boolean)
}
""",
        encoding="utf-8",
    )

    sys_ios = source_dir / "composeApp/src/iosMain/kotlin/com/nuvio/app/core/ui/AppSystemUiController.ios.kt"
    sys_ios.write_text(
        """package com.nuvio.app.core.ui

internal actual object AppSystemUiController {
    actual fun setStatusBarVisible(visible: Boolean) = Unit
    actual fun setLightSystemBars(isLight: Boolean) = Unit
}
""",
        encoding="utf-8",
    )

    sys_android = source_dir / "composeApp/src/androidMain/kotlin/com/nuvio/app/core/ui/AppSystemUiController.android.kt"
    sys_android.write_text(
        """package com.nuvio.app.core.ui

import android.app.Activity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat

internal actual object AppSystemUiController {
    private var activity: Activity? = null
    private var statusBarVisible: Boolean = true
    private var lightSystemBars: Boolean = false

    fun bind(activity: Activity) {
        this.activity = activity
        apply()
    }

    fun unbind(activity: Activity) {
        if (this.activity === activity) {
            this.activity = null
        }
    }

    actual fun setStatusBarVisible(visible: Boolean) {
        statusBarVisible = visible
        apply()
    }

    actual fun setLightSystemBars(isLight: Boolean) {
        lightSystemBars = isLight
        apply()
    }

    private fun apply() {
        val window = activity?.window ?: return
        val controller = WindowCompat.getInsetsController(window, window.decorView)
        controller.isAppearanceLightStatusBars = lightSystemBars
        controller.isAppearanceLightNavigationBars = lightSystemBars
        if (statusBarVisible) {
            controller.show(WindowInsetsCompat.Type.statusBars())
        } else {
            controller.hide(WindowInsetsCompat.Type.statusBars())
            controller.systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }
}
""",
        encoding="utf-8",
    )

    # 7. Theme.kt — support Material 3 lightColorScheme for Catppuccin Latte & darkColorScheme for Frappé/Macchiato/Mocha
    theme_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/core/ui/Theme.kt"
    _replace_once(
        theme_path,
        """import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember""",
        """import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember""",
        "Theme.imports",
    )

    _replace_once(
        theme_path,
        """private fun buildColorScheme(palette: ThemeColorPalette, amoled: Boolean = false) = darkColorScheme(
    primary = palette.secondary,
    onPrimary = palette.onSecondary,
    primaryContainer = palette.focusBackground,
    onPrimaryContainer = contentColorFor(palette.focusBackground),
    secondary = palette.secondaryVariant,
    onSecondary = palette.onSecondaryVariant,
    background = if (amoled) Color.Black else palette.background,
    onBackground = Color(0xFFF5F7F8),
    surface = palette.backgroundElevated,
    onSurface = Color(0xFFF5F7F8),
    surfaceVariant = palette.backgroundCard,
    onSurfaceVariant = Color(0xFF969CA3),
    outline = Color(0xFF252A2A),
    error = Color(0xFFE36A8A),
    onError = Color(0xFFFCE5EC),
)""",
        """internal fun buildColorScheme(palette: ThemeColorPalette, amoled: Boolean = false) =
    if (palette.isLight) {
        lightColorScheme(
            primary = palette.secondary,
            onPrimary = palette.onSecondary,
            primaryContainer = palette.focusBackground,
            onPrimaryContainer = palette.textPrimary,
            secondary = palette.secondaryVariant,
            onSecondary = palette.onSecondaryVariant,
            background = palette.background,
            onBackground = palette.textPrimary,
            surface = palette.backgroundElevated,
            onSurface = palette.textPrimary,
            surfaceVariant = palette.backgroundCard,
            onSurfaceVariant = palette.textSecondary,
            outline = palette.borderDefault,
            outlineVariant = palette.borderDefault.copy(alpha = 0.6f),
            error = palette.errorColor,
            onError = palette.onErrorColor,
        )
    } else {
        darkColorScheme(
            primary = palette.secondary,
            onPrimary = palette.onSecondary,
            primaryContainer = palette.focusBackground,
            onPrimaryContainer = contentColorFor(palette.focusBackground),
            secondary = palette.secondaryVariant,
            onSecondary = palette.onSecondaryVariant,
            background = if (amoled) Color.Black else palette.background,
            onBackground = palette.textPrimary,
            surface = palette.backgroundElevated,
            onSurface = palette.textPrimary,
            surfaceVariant = palette.backgroundCard,
            onSurfaceVariant = palette.textMuted,
            outline = palette.borderDefault,
            outlineVariant = palette.borderDefault.copy(alpha = 0.6f),
            error = palette.errorColor,
            onError = palette.onErrorColor,
        )
    }""",
        "Theme.buildColorSchemeLightDark",
    )

    _replace_once(
        theme_path,
        """@Composable
fun NuvioTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    appTheme: AppTheme = AppTheme.WHITE,
    customFirst: Color = ThemeAccentColor.PINK.color,
    customSecond: Color = ThemeAccentColor.CYAN.color,
    amoled: Boolean = false,
    customThemeColors: CustomThemeColors = CustomThemeColors.Default,
    content: @Composable () -> Unit,
) {
    val palette = remember(appTheme, customFirst, customSecond) {
        ThemeColors.getColorPalette(appTheme, customFirst, customSecond)
    }
    val animatedVisuals = rememberAnimatedThemeVisuals(appTheme, customFirst, customSecond)
    val colorScheme = buildColorScheme(palette, amoled = amoled)
    val tokens = defaultNuvioThemeTokens(palette, amoled = amoled, colorScheme = colorScheme)

    val density = LocalDensity.current
    CompositionLocalProvider(
        LocalDensity provides Density(
            density = density.density,
            fontScale = 1f,
        ),
        LocalNuvioThemeTokens provides tokens,
        LocalNuvioTypeScale provides NuvioTypeTokens,
        LocalRippleConfiguration provides NuvioRippleConfiguration,
        LocalAppTheme provides appTheme,
        LocalThemePalette provides palette,
        LocalAnimatedThemeVisuals provides animatedVisuals,
    ) {""",
        """@Composable
fun NuvioTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    appTheme: AppTheme = AppTheme.WHITE,
    customFirst: Color = ThemeAccentColor.PINK.color,
    customSecond: Color = ThemeAccentColor.CYAN.color,
    amoled: Boolean = false,
    customThemeColors: CustomThemeColors = CustomThemeColors.Default,
    catppuccinAccent: CatppuccinAccent = CatppuccinPalettes.activeAccent,
    content: @Composable () -> Unit,
) {
    val palette = remember(appTheme, customFirst, customSecond, catppuccinAccent) {
        ThemeColors.getColorPalette(
            theme = appTheme,
            customFirst = customFirst,
            customSecond = customSecond,
            catppuccinAccent = catppuccinAccent,
        )
    }
    val animatedVisuals = rememberAnimatedThemeVisuals(appTheme, customFirst, customSecond)
    val colorScheme = buildColorScheme(palette, amoled = amoled)
    val tokens = defaultNuvioThemeTokens(palette, amoled = amoled, colorScheme = colorScheme)
    val rippleConfig = remember(palette.isLight, palette.textPrimary) {
        RippleConfiguration(color = if (palette.isLight) palette.textPrimary else Color.Black)
    }

    SideEffect {
        AppSystemUiController.setLightSystemBars(palette.isLight)
    }

    val density = LocalDensity.current
    CompositionLocalProvider(
        LocalDensity provides Density(
            density = density.density,
            fontScale = 1f,
        ),
        LocalNuvioThemeTokens provides tokens,
        LocalNuvioTypeScale provides NuvioTypeTokens,
        LocalRippleConfiguration provides rippleConfig,
        LocalAppTheme provides appTheme,
        LocalThemePalette provides palette,
        LocalAnimatedThemeVisuals provides animatedVisuals,
    ) {""",
        "Theme.nuvioThemeComposable",
    )


# ---------------------------------------------------------------------------
# Phase 9 & 10 — Settings Persistence, Appearance UI, Playback Seek UI & Branding Purge
# ---------------------------------------------------------------------------

def patch_settings_and_branding(source_dir: Path) -> None:
    # 1. NuvioEnhancedSettingsRepository.kt — persist catppuccinAccent & sync CatppuccinPalettes.activeAccent
    enh_repo_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/NuvioEnhancedSettingsRepository.kt"
    _replace_once(
        enh_repo_path,
        "package com.nuvio.app.features.settings\n",
        "package com.nuvio.app.features.settings\n\nimport com.nuvio.app.core.ui.CatppuccinAccent\nimport com.nuvio.app.core.ui.CatppuccinPalettes\n",
        "NuvioEnhancedSettingsRepository.catppuccinImports",
    )

    enh_text = enh_repo_path.read_text(encoding="utf-8")
    old_pair = """    val swipeSeekSensitivity: Float = 1.0f,
    val cloudStreamHomeLayout: CloudStreamHomeLayout = CloudStreamHomeLayout.ROWS,"""
    new_pair = """    val swipeSeekSensitivity: Float = 1.0f,
    val cloudStreamHomeLayout: CloudStreamHomeLayout = CloudStreamHomeLayout.ROWS,
    val catppuccinAccent: CatppuccinAccent = CatppuccinAccent.MAUVE,"""
    if enh_text.count(old_pair) != 2:
        raise RuntimeError(f"[NuvioEnhancedSettingsRepository.catppuccinField] Expected 2 matches, got {enh_text.count(old_pair)}")
    enh_repo_path.write_text(enh_text.replace(old_pair, new_pair, 2), encoding="utf-8")

    _replace_once(
        enh_repo_path,
        """    fun setCloudStreamHomeLayout(layout: CloudStreamHomeLayout) = update {
        copy(cloudStreamHomeLayout = layout)
    }""",
        """    fun setCloudStreamHomeLayout(layout: CloudStreamHomeLayout) = update {
        copy(cloudStreamHomeLayout = layout)
    }

    fun setCatppuccinAccent(accent: CatppuccinAccent) {
        CatppuccinPalettes.activeAccent = accent
        update { copy(catppuccinAccent = accent) }
        ThemeSettingsRepository.refreshActiveThemePalette()
    }""",
        "NuvioEnhancedSettingsRepository.setCatppuccinAccent",
    )

    _replace_once(
        enh_repo_path,
        """    private fun publish() {
        _uiState.value = NuvioEnhancedSettingsUiState(""",
        """    private fun publish() {
        CatppuccinPalettes.activeAccent = stored.catppuccinAccent
        _uiState.value = NuvioEnhancedSettingsUiState(""",
        "NuvioEnhancedSettingsRepository.syncActiveAccent",
    )

    _replace_once(
        enh_repo_path,
        """            swipeSeekSensitivity = stored.swipeSeekSensitivity.coerceIn(0.4f, 2.5f),
            cloudStreamHomeLayout = stored.cloudStreamHomeLayout,""",
        """            swipeSeekSensitivity = stored.swipeSeekSensitivity.coerceIn(0.4f, 2.5f),
            cloudStreamHomeLayout = stored.cloudStreamHomeLayout,
            catppuccinAccent = stored.catppuccinAccent,""",
        "NuvioEnhancedSettingsRepository.publishCatppuccinAccent",
    )

    # 2. ThemeSettingsRepository.kt — add refreshActiveThemePalette() so native tab bridge updates on accent tap
    theme_repo_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/ThemeSettingsRepository.kt"
    _replace_once(
        theme_repo_path,
        """    private fun applyEffectiveTheme() {""",
        """    fun refreshActiveThemePalette() {
        if (hasLoaded) applyEffectiveTheme()
    }

    private fun applyEffectiveTheme() {""",
        "ThemeSettingsRepository.refreshActiveThemePalette",
    )

    # 3. App.kt — pass enhancedSettings.catppuccinAccent into NuvioTheme
    app_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/App.kt"
    _replace_once(
        app_path,
        """    NuvioTheme(
        appTheme = selectedTheme,
        customFirst = customThemeFirstColor,
        customSecond = customThemeSecondColor,
        amoled = amoledEnabled,
    ) {""",
        """    NuvioTheme(
        appTheme = selectedTheme,
        customFirst = customThemeFirstColor,
        customSecond = customThemeSecondColor,
        amoled = amoledEnabled,
        catppuccinAccent = enhancedSettings.catppuccinAccent,
    ) {""",
        "App.passCatppuccinAccent",
    )

    # 4. AppearanceSettingsPage.kt — Catppuccin Flavor Showcase + 14-swatch Accent Selector + Library Nav Position
    appearance_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/AppearanceSettingsPage.kt"
    _replace_once(
        appearance_path,
        """import com.nuvio.app.core.ui.AppTheme""",
        """import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import com.nuvio.app.core.ui.AppTheme
import com.nuvio.app.core.ui.CatppuccinAccent
import com.nuvio.app.core.ui.CatppuccinFlavor
import com.nuvio.app.core.ui.CatppuccinPalettes
import com.nuvio.app.core.ui.catppuccinFlavorOrNull
import com.nuvio.app.core.ui.isCatppuccin
import com.nuvio.app.features.library.LibraryCategoryNavPosition
import com.nuvio.app.features.library.LibraryDisplaySettingsRepository""",
        "AppearanceSettingsPage.imports",
    )

    _replace_once(
        appearance_path,
        """                        CustomThemeColorPicker(
                            label = stringResource(Res.string.settings_appearance_theme_custom_second),
                            selectedColor = customSecond,
                            onColorSelected = ThemeSettingsRepository::setCustomThemeSecondColor,
                        )
                    }
                }
            }
        }
    }""",
        """                        CustomThemeColorPicker(
                            label = stringResource(Res.string.settings_appearance_theme_custom_second),
                            selectedColor = customSecond,
                            onColorSelected = ThemeSettingsRepository::setCustomThemeSecondColor,
                        )
                    }

                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.72f))

                    val enhancedUiState by NuvioEnhancedSettingsRepository.uiState.collectAsStateWithLifecycle()
                    ThemeSectionLabel("Catppuccin Official")
                    CatppuccinFlavorShowcase(
                        selectedTheme = selectedTheme,
                        selectedAccent = enhancedUiState.catppuccinAccent,
                        onThemeSelected = onThemeSelected,
                    )

                    AnimatedVisibility(visible = selectedTheme.isCatppuccin) {
                        val activeFlavor = selectedTheme.catppuccinFlavorOrNull ?: CatppuccinFlavor.MOCHA
                        Column(
                            modifier = Modifier.padding(top = 8.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.72f))
                            ThemeSectionLabel("Catppuccin Accent (${enhancedUiState.catppuccinAccent.displayName})")
                            CatppuccinAccentPicker(
                                flavor = activeFlavor,
                                selectedAccent = enhancedUiState.catppuccinAccent,
                                onAccentSelected = NuvioEnhancedSettingsRepository::setCatppuccinAccent,
                            )
                        }
                    }
                }
            }
        }
    }""",
        "AppearanceSettingsPage.catppuccinShowcaseAndAccent",
    )

    _replace_once(
        appearance_path,
        """                SettingsSwitchRow(
                    title = stringResource(Res.string.settings_appearance_catalog_accent),
                    description = stringResource(Res.string.settings_appearance_catalog_accent_description),
                    checked = showCatalogAccentEnabled,
                    isTablet = isTablet,
                    onCheckedChange = onShowCatalogAccentToggle,
                )""",
        """                SettingsSwitchRow(
                    title = stringResource(Res.string.settings_appearance_catalog_accent),
                    description = stringResource(Res.string.settings_appearance_catalog_accent_description),
                    checked = showCatalogAccentEnabled,
                    isTablet = isTablet,
                    onCheckedChange = onShowCatalogAccentToggle,
                )
                SettingsGroupDivider(isTablet = isTablet)
                val libraryControlsState by remember {
                    LibraryDisplaySettingsRepository.ensureLoaded()
                    LibraryDisplaySettingsRepository.uiState
                }.collectAsStateWithLifecycle()
                SettingsNavigationRow(
                    title = "Library Category Bar Position",
                    description = if (libraryControlsState.categoryNavPosition == LibraryCategoryNavPosition.BOTTOM) {
                        "Bottom (thumb-friendly above navigation bar)"
                    } else {
                        "Top (classic header tabs)"
                    },
                    isTablet = isTablet,
                    onClick = {
                        val next = if (libraryControlsState.categoryNavPosition == LibraryCategoryNavPosition.TOP) {
                            LibraryCategoryNavPosition.BOTTOM
                        } else {
                            LibraryCategoryNavPosition.TOP
                        }
                        LibraryDisplaySettingsRepository.setCategoryNavPosition(next)
                    },
                )""",
        "AppearanceSettingsPage.libraryNavPositionRow",
    )

    appearance_text = appearance_path.read_text(encoding="utf-8")
    appearance_text += r"""

@Composable
private fun CatppuccinFlavorShowcase(
    selectedTheme: AppTheme,
    selectedAccent: CatppuccinAccent,
    onThemeSelected: (AppTheme) -> Unit,
) {
    val entries = listOf(
        AppTheme.CATPPUCCIN_LATTE to CatppuccinPalettes.Latte,
        AppTheme.CATPPUCCIN_FRAPPE to CatppuccinPalettes.Frappe,
        AppTheme.CATPPUCCIN_MACCHIATO to CatppuccinPalettes.Macchiato,
        AppTheme.CATPPUCCIN_MOCHA to CatppuccinPalettes.Mocha,
    )
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        entries.chunked(2).forEach { pair ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                pair.forEach { (theme, flavorTokens) ->
                    val isSelected = selectedTheme == theme
                    val accentColor = flavorTokens.colorForAccent(selectedAccent)
                    val cardShape = RoundedCornerShape(16.dp)
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .clip(cardShape)
                            .background(flavorTokens.base)
                            .border(
                                width = if (isSelected) 2.dp else 1.dp,
                                color = if (isSelected) accentColor else flavorTokens.surface1,
                                shape = cardShape,
                            )
                            .clickable { onThemeSelected(theme) }
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = flavorTokens.flavor.displayName.removePrefix("Catppuccin "),
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = flavorTokens.text,
                                    maxLines = 1,
                                )
                                Text(
                                    text = flavorTokens.flavor.subtitle,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = flavorTokens.subtext0,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            if (isSelected) {
                                Box(
                                    modifier = Modifier
                                        .size(22.dp)
                                        .clip(CircleShape)
                                        .background(accentColor),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Check,
                                        contentDescription = null,
                                        tint = if (accentColor.luminance() > 0.44f) flavorTokens.crust else Color(0xFFEFF1F5),
                                        modifier = Modifier.size(14.dp),
                                    )
                                }
                            }
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            listOf(
                                flavorTokens.rosewater,
                                flavorTokens.pink,
                                flavorTokens.mauve,
                                flavorTokens.peach,
                                flavorTokens.green,
                                flavorTokens.sapphire,
                            ).forEach { swatch ->
                                Box(
                                    modifier = Modifier
                                        .size(14.dp)
                                        .clip(CircleShape)
                                        .background(swatch),
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CatppuccinAccentPicker(
    flavor: CatppuccinFlavor,
    selectedAccent: CatppuccinAccent,
    onAccentSelected: (CatppuccinAccent) -> Unit,
) {
    val tokens = CatppuccinPalettes.tokensFor(flavor)
    FlowRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        CatppuccinAccent.entries.forEach { accent ->
            val swatch = tokens.colorForAccent(accent)
            val isSelected = accent == selectedAccent
            val pillShape = RoundedCornerShape(999.dp)
            Row(
                modifier = Modifier
                    .clip(pillShape)
                    .background(
                        if (isSelected) swatch.copy(alpha = 0.20f)
                        else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                    )
                    .border(
                        width = if (isSelected) 1.5.dp else 1.dp,
                        color = if (isSelected) swatch else MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                        shape = pillShape,
                    )
                    .clickable { onAccentSelected(accent) }
                    .padding(horizontal = 10.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(14.dp)
                        .clip(CircleShape)
                        .background(swatch),
                )
                Text(
                    text = accent.displayName,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                    color = if (isSelected) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
"""
    appearance_path.write_text(appearance_text, encoding="utf-8")

    # 5. PlaybackInterfaceSettings.kt — add Swipe Seek Sensitivity preset selector right below Swipe to Seek
    playback_ui_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/PlaybackInterfaceSettings.kt"
    _replace_once(
        playback_ui_path,
        """import androidx.compose.runtime.Composable""",
        """import androidx.compose.runtime.Composable
import androidx.lifecycle.compose.collectAsStateWithLifecycle""",
        "PlaybackInterfaceSettings.imports",
    )

    _replace_once(
        playback_ui_path,
        """                if (settings.touchGesturesEnabled && !settings.externalPlayerEnabled) {
                    SettingsGroupDivider(isTablet = isTablet)
                    SettingsSwitchRow(
                        title = stringResource(Res.string.settings_playback_swipe_to_seek),
                        description = stringResource(Res.string.settings_playback_swipe_to_seek_description),
                        checked = settings.swipeToSeekEnabled,
                        isTablet = isTablet,
                        onCheckedChange = PlayerSettingsRepository::setSwipeToSeekEnabled,
                    )
                }""",
        """                if (settings.touchGesturesEnabled && !settings.externalPlayerEnabled) {
                    val enhancedPlayerState by NuvioEnhancedSettingsRepository.uiState.collectAsStateWithLifecycle()
                    SettingsGroupDivider(isTablet = isTablet)
                    SettingsSwitchRow(
                        title = stringResource(Res.string.settings_playback_swipe_to_seek),
                        description = stringResource(Res.string.settings_playback_swipe_to_seek_description),
                        checked = settings.swipeToSeekEnabled,
                        isTablet = isTablet,
                        onCheckedChange = PlayerSettingsRepository::setSwipeToSeekEnabled,
                    )
                    if (settings.swipeToSeekEnabled) {
                        val currentSensitivity = enhancedPlayerState.swipeSeekSensitivity
                        val presetLabel = when {
                            currentSensitivity <= 0.75f -> "Fine (0.65x • frame & subtitle precision)"
                            currentSensitivity <= 1.20f -> "Balanced (1.0x • dynamic distance + velocity)"
                            currentSensitivity <= 1.70f -> "Fast (1.45x • brisk chapter scrubbing)"
                            else -> "Turbo (2.0x • rapid long-form jumps)"
                        }
                        SettingsGroupDivider(isTablet = isTablet)
                        SettingsNavigationRow(
                            title = "Swipe Seek Sensitivity",
                            description = presetLabel,
                            isTablet = isTablet,
                            onClick = {
                                val next = when {
                                    currentSensitivity <= 0.75f -> 1.0f
                                    currentSensitivity <= 1.20f -> 1.45f
                                    currentSensitivity <= 1.70f -> 2.0f
                                    else -> 0.65f
                                }
                                NuvioEnhancedSettingsRepository.setSwipeSeekSensitivity(next)
                            },
                        )
                    }
                }""",
        "PlaybackInterfaceSettings.swipeSeekSensitivityRow",
    )

    # 6. SupportConfig.kt + BuyMeACoffeeSupportCard.kt + SettingsRootPage.kt — complete purge & clean Buy Me a Coffee card
    support_cfg_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/SupportConfig.kt"
    support_cfg_path.write_text(
        """package com.nuvio.app.features.settings

/**
 * Centralized developer support configuration.
 * Replace [BUY_ME_A_COFFEE_URL] with a custom Buy Me a Coffee profile URL when desired.
 */
object SupportConfig {
    const val BUY_ME_A_COFFEE_URL: String = "https://buymeacoffee.com/"
}
""",
        encoding="utf-8",
    )

    bmac_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/BuyMeACoffeeSupportCard.kt"
    bmac_path.write_text(
        r"""package com.nuvio.app.features.settings

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.OpenInNew
import androidx.compose.material.icons.rounded.LocalCafe
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioTokens
import com.nuvio.app.core.ui.nuvio
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.support_buymeacoffee_button
import nuvio.composeapp.generated.resources.support_buymeacoffee_message
import nuvio.composeapp.generated.resources.support_buymeacoffee_title
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun BuyMeACoffeeSupportCard(
    modifier: Modifier = Modifier,
) {
    val tokens = MaterialTheme.nuvio
    val uriHandler = LocalUriHandler.current
    val accent = tokens.colors.accent
    val backgroundBrush = remember(accent) {
        Brush.linearGradient(
            listOf(
                accent.copy(alpha = 0.16f),
                accent.copy(alpha = 0.06f),
            ),
        )
    }
    val borderBrush = remember(accent) {
        Brush.linearGradient(
            listOf(
                accent.copy(alpha = 0.48f),
                accent.copy(alpha = 0.24f),
            ),
        )
    }
    val shape = RoundedCornerShape(NuvioTokens.Radius.xl)

    Surface(
        modifier = modifier.fillMaxWidth(),
        color = tokens.colors.surfaceCard,
        shape = shape,
        border = BorderStroke(tokens.borders.hairline, borderBrush),
    ) {
        Box(
            modifier = Modifier
                .background(backgroundBrush)
                .padding(18.dp),
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(CircleShape)
                            .background(accent.copy(alpha = 0.18f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.LocalCafe,
                            contentDescription = null,
                            tint = accent,
                            modifier = Modifier.size(22.dp),
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = stringResource(Res.string.support_buymeacoffee_title),
                            style = MaterialTheme.typography.titleMedium,
                            color = tokens.colors.textPrimary,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = stringResource(Res.string.support_buymeacoffee_message),
                            style = MaterialTheme.typography.bodySmall,
                            color = tokens.colors.textSecondary,
                        )
                    }
                }
                Button(
                    onClick = { runCatching { uriHandler.openUri(SupportConfig.BUY_ME_A_COFFEE_URL) } },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = accent,
                        contentColor = tokens.colors.onAccent,
                    ),
                ) {
                    Icon(
                        imageVector = Icons.Rounded.LocalCafe,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = stringResource(Res.string.support_buymeacoffee_button),
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Icon(
                        imageVector = Icons.AutoMirrored.Rounded.OpenInNew,
                        contentDescription = null,
                        modifier = Modifier.size(15.dp),
                    )
                }
            }
        }
    }
}
""",
        encoding="utf-8",
    )

    root_page_path = source_dir / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/SettingsRootPage.kt"
    _replace_once(
        root_page_path,
        """            androidx.compose.foundation.layout.Spacer(
                modifier = Modifier.height(2.dp),
            )
            Text(
                text = "by RAJA JI",
                modifier = Modifier.fillMaxWidth(),
                style = MaterialTheme.typography.labelLarge.copy(
                    fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
                ),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )""",
        """            androidx.compose.foundation.layout.Spacer(
                modifier = Modifier.height(2.dp),
            )""",
        "SettingsRootPage.purgeRajaJiFooter",
    )

    readme_path = source_dir / "README.md"
    if readme_path.is_file():
        readme_text = readme_path.read_text(encoding="utf-8")
        readme_text = readme_text.replace("Nuvio Enhanced 2.0", "Nuvio Enhanced")
        readme_text = readme_text.replace(
            "[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-raja__ji-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/raja_ji)",
            "[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20Development-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com)",
        )
        readme_path.write_text(readme_text, encoding="utf-8")


def patch_nuvio_enhanced_settings_and_unit_tests(source_dir: Path) -> None:
    enhanced_page_path = (
        source_dir
        / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/NuvioEnhancedSettingsPage.kt"
    )
    _replace_once(
        enhanced_page_path,
        """                SettingsSwitchRow(
                    title = stringResource(Res.string.nuvio_enhanced_profile_stats_title),
                    description = stringResource(Res.string.nuvio_enhanced_profile_stats_desc),
                    checked = settings.profileStatsEnabled,
                    enabled = settings.enhancedHomeFeaturesEnabled && settings.nuvioConciergeEnabled,
                    isTablet = isTablet,
                    highlighted = isNew(NuvioEnhancedFeature.HomeExperienceControls),
                    onCheckedChange = {
                        markSeen(NuvioEnhancedFeature.HomeExperienceControls)
                        NuvioEnhancedSettingsRepository.setProfileStatsEnabled(it)
                    },
                )
            }
        }""",
        """                SettingsSwitchRow(
                    title = stringResource(Res.string.nuvio_enhanced_profile_stats_title),
                    description = stringResource(Res.string.nuvio_enhanced_profile_stats_desc),
                    checked = settings.profileStatsEnabled,
                    enabled = settings.enhancedHomeFeaturesEnabled && settings.nuvioConciergeEnabled,
                    isTablet = isTablet,
                    highlighted = isNew(NuvioEnhancedFeature.HomeExperienceControls),
                    onCheckedChange = {
                        markSeen(NuvioEnhancedFeature.HomeExperienceControls)
                        NuvioEnhancedSettingsRepository.setProfileStatsEnabled(it)
                    },
                )
                SettingsGroupDivider(isTablet = isTablet)
                SettingsSwitchRow(
                    title = "CloudStream Columns Grid Layout",
                    description = "Display CloudStream extension discovery catalogs in a multi-column poster grid instead of horizontal rows",
                    checked = settings.cloudStreamHomeLayout == CloudStreamHomeLayout.COLUMNS,
                    isTablet = isTablet,
                    onCheckedChange = { useColumns ->
                        NuvioEnhancedSettingsRepository.setCloudStreamHomeLayout(
                            if (useColumns) CloudStreamHomeLayout.COLUMNS else CloudStreamHomeLayout.ROWS,
                        )
                    },
                )
            }
        }""",
        "NuvioEnhancedSettingsPage.cloudStreamHomeLayoutToggle",
    )

    test_path = (
        source_dir
        / "composeApp/src/commonTest/kotlin/com/nuvio/app/NuvioV119VerificationTest.kt"
    )
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(
        r'''package com.nuvio.app

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
''',
        encoding="utf-8",
    )


def apply_v119_catppuccin_settings_patch(source_dir: Path) -> None:
    patch_catppuccin_theme_engine(source_dir)
    patch_settings_and_branding(source_dir)
    patch_nuvio_enhanced_settings_and_unit_tests(source_dir)
    print("[v1.19-module-3] Official Catppuccin Palettes, Light/Dark ColorSchemes, Settings UI, Unit Tests, & Branding Purge applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v119_catppuccin_settings_patch.py <source_dir>")
    apply_v119_catppuccin_settings_patch(Path(sys.argv[1]).resolve())
