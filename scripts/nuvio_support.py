#!/usr/bin/env python3
"""AndroidForge — Nuvio Enhanced Project Support & Runtime Patch Suite.

Prepares an extracted Nuvio / Nuvio Enhanced 2 Kotlin Multiplatform source tree
for Android APK builds and applies targeted fixes for v1.1.2:

  1. Restores `com/nuvio/app/core/build/AppFeaturePolicy*.kt` files if omitted
     from the source archive.
  2. Fixes v1.1.2 source-level Kotlin compile issues in `CloudStreamRepository.kt`
     and `CloudStreamSettingsSection.kt`.
  3. Issue #1: Replaces the Live TV navigation tab with the Downloads screen on
     both phone and tablet navigation bars.
  4. Issue #2: Fixes CloudStream extension gear-icon settings (`AppCompatActivity`
     host binding, MaterialComponents theme & widgets, `.cs3` `resources.arsc`
     attachment, `CommonActivity.showToast` + `AcraApplication` + `CloudStreamApp`
     ABI surface, R8/resource keep rules, and visible toast feedback).
  5. Issue #3: Fixes CloudStream extensions (such as `StreamPlay`) missing from
     Home catalogues and disappearing on movie/series source screens (`MainActivity`
     activity context during `Plugin.load`, `"all"` default Home CS3 selection +
     auto-heal of empty bootstrap selections, multi-API `getMainPage` deduplication,
     `StreamsScreen` title/meta forwarding, multi-API `TvType.Movie` search-card
     scoring for TV series, `±1` release-year & null-year movie matching, and
     bounded HTTP/link timeouts that preserve partial extractor callbacks).
  6. Issues #4, #5, #6: Fixes Details screen Batch Download compressed text,
     adds `All / Nuvio / CloudStream` source filtering & visual badges, integrates
     CloudStream extensions into `StreamSourceLoader` + `BatchDownloadCoordinator`
     with 10-minute search/load caching, and adds native HLS (`.m3u8`, fMP4,
     AES-128) segment downloading in `AndroidDownloadTransfer.kt`.
  7. Issue #7: Registers missing `entry<DownloadsSettingsRoute>` in
     `MainAppContent.kt` so tapping the Settings icon in Downloads never crashes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


APP_FEATURE_POLICY_FILES: dict[str, str] = {
    "composeApp/src/commonMain/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.kt": """\
package com.nuvio.app.core.build

enum class TrailerPlaybackMode {
    IN_APP,
    EXTERNAL,
}

expect object AppFeaturePolicy {
    val pluginsEnabled: Boolean
    val accountDeletionEnabled: Boolean
    val personalMediaAddonCopyEnabled: Boolean
    val p2pEnabled: Boolean
    val trailerPlaybackMode: TrailerPlaybackMode
    val heroTrailerPlaybackSupported: Boolean
    val inAppUpdaterEnabled: Boolean
    val imdbRatingLogoEnabled: Boolean
    val mediaPlaybackForegroundServiceEnabled: Boolean
    val downloadForegroundServiceEnabled: Boolean
    val customServerConnectionsEnabled: Boolean
}
""",
    "composeApp/src/androidFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.android.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = true
    actual val accountDeletionEnabled: Boolean = false
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = true
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.IN_APP
    actual val heroTrailerPlaybackSupported: Boolean = true
    actual val inAppUpdaterEnabled: Boolean = true
    actual val imdbRatingLogoEnabled: Boolean = true
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = true
    actual val downloadForegroundServiceEnabled: Boolean = true
    actual val customServerConnectionsEnabled: Boolean = true
}
""",
    "composeApp/src/androidPlaystore/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.android.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = false
    actual val accountDeletionEnabled: Boolean = true
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = true
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.EXTERNAL
    actual val heroTrailerPlaybackSupported: Boolean = false
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = false
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = false
}
""",
    "composeApp/src/desktopMain/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.desktop.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = false
    actual val accountDeletionEnabled: Boolean = false
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = false
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.EXTERNAL
    actual val heroTrailerPlaybackSupported: Boolean = false
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = true
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = false
}
""",
    "composeApp/src/iosFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.ios.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = true
    actual val accountDeletionEnabled: Boolean = false
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = true
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.IN_APP
    actual val heroTrailerPlaybackSupported: Boolean = true
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = true
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = true
}
""",
    "composeApp/src/iosAppStore/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.ios.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = false
    actual val accountDeletionEnabled: Boolean = true
    actual val personalMediaAddonCopyEnabled: Boolean = true
    actual val p2pEnabled: Boolean = false
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.EXTERNAL
    actual val heroTrailerPlaybackSupported: Boolean = false
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = false
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = false
}
""",
}


def _replace_once(path: Path, old: str, new: str, label: str) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")
    if new:
        if new in content:
            return False
    elif old not in content:
        return False
    if old not in content:
        raise RuntimeError(f"Patch anchor missing for {label} in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return True


def is_nuvio_project(root: Path) -> bool:
    """Detect whether `root` is a Nuvio / Nuvio Enhanced KMP Android project."""
    if root.name.lower().startswith("nuvio"):
        return True
    candidates = [
        root / "gradle.properties",
        root / "settings.gradle.kts",
        root / "composeApp" / "build.gradle.kts",
        root / "androidApp" / "build.gradle.kts",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if (
            "nuvio.android.distribution" in text
            or "com.nuvio.enhanced" in text
            or 'rootProject.name = "Nuvio"' in text
        ):
            return True
    return False


def _patch_navigation_and_downloads_tab(root: Path) -> list[str]:
    """Fix Issue #7 (DownloadsSettingsRoute crash) and Issue #1 (Replace Live TV with Downloads)."""
    patched: list[str] = []

    main_app = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt"
    if main_app.is_file():
        changed = False
        changed |= _replace_once(
            main_app,
            "import com.nuvio.app.features.settings.ContinueWatchingSettingsScreen\n",
            "import com.nuvio.app.features.settings.ContinueWatchingSettingsScreen\n"
            "import com.nuvio.app.features.settings.DownloadsSettingsScreen\n",
            "MainAppContent DownloadsSettingsScreen import",
        )
        changed |= _replace_once(
            main_app,
            "        val showLiveTvInNavigation = liveTvUiState.showInNavigation\n",
            "        val showLiveTvInNavigation = true\n",
            "MainAppContent always show Downloads tab",
        )
        changed |= _replace_once(
            main_app,
            "                                onDownloadsClick = { navController.navigate(DownloadsRoute(downloadsTitle)) },\n",
            "                                onDownloadsClick = { navController.navigate(DownloadsRoute(downloadsTitle)) },\n"
            "                                onOpenDownload = ::openDownloadedItem,\n"
            "                                onDownloadDetailsClick = { item ->\n"
            "                                    navController.navigate(\n"
            "                                        DetailRoute(\n"
            "                                            type = item.parentMetaType,\n"
            "                                            id = item.parentMetaId,\n"
            "                                            title = item.title,\n"
            "                                        ),\n"
            "                                    )\n"
            "                                },\n"
            "                                onDownloadShowClick = if (useNativeNavigation) {\n"
            "                                    { showId, title -> navController.navigate(DownloadShowRoute(showId, title)) }\n"
            "                                } else {\n"
            "                                    null\n"
            "                                },\n"
            "                                onDownloadSettingsClick = {\n"
            "                                    navController.navigate(DownloadsSettingsRoute(downloadsTitle))\n"
            "                                },\n",
            "MainAppContent Downloads tab actions",
        )
        changed |= _replace_once(
            main_app,
            "                entry<DownloadShowRoute> { route ->\n"
            "                    DownloadShowDestination(\n"
            "                        route = route,\n"
            "                        navController = navController,\n"
            "                        onOpenDownload = ::openDownloadedItem,\n"
            "                    )\n"
            "                }\n",
            "                entry<DownloadShowRoute> { route ->\n"
            "                    DownloadShowDestination(\n"
            "                        route = route,\n"
            "                        navController = navController,\n"
            "                        onOpenDownload = ::openDownloadedItem,\n"
            "                    )\n"
            "                }\n"
            "                entry<DownloadsSettingsRoute> { route ->\n"
            "                    SettingsDestination(route, navController) { onBack ->\n"
            "                        DownloadsSettingsScreen(onBack = onBack)\n"
            "                    }\n"
            "                }\n",
            "MainAppContent DownloadsSettingsRoute entry",
        )
        if changed:
            patched.append(str(main_app.relative_to(root)))

    shell = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/AppShellComponents.kt"
    if shell.is_file():
        changed = False
        changed |= _replace_once(
            shell,
            "import androidx.compose.material.icons.filled.Tv\n",
            "import androidx.compose.material.icons.filled.Tv\n"
            "import androidx.compose.material.icons.rounded.Download\n",
            "AppShellComponents Download icon import",
        )
        changed |= _replace_once(
            shell,
            "import com.nuvio.app.features.downloads.DownloadItem\n",
            "import com.nuvio.app.features.downloads.DownloadItem\n"
            "import com.nuvio.app.features.downloads.DownloadsScreen\n",
            "AppShellComponents DownloadsScreen import",
        )
        changed |= _replace_once(
            shell,
            "import nuvio.composeapp.generated.resources.compose_nav_live_tv\n",
            "import nuvio.composeapp.generated.resources.compose_nav_live_tv\n"
            "import nuvio.composeapp.generated.resources.compose_settings_root_downloads_title\n",
            "AppShellComponents downloads title resource import",
        )
        changed |= _replace_once(
            shell,
            "    val onDownloadsClick: () -> Unit = {},\n"
            "    val onOpenDownload: ((DownloadItem) -> Unit)? = null,\n",
            "    val onDownloadsClick: () -> Unit = {},\n"
            "    val onOpenDownload: ((DownloadItem) -> Unit)? = null,\n"
            "    val onDownloadDetailsClick: ((DownloadItem) -> Unit)? = null,\n"
            "    val onDownloadShowClick: ((String, String) -> Unit)? = null,\n"
            "    val onDownloadSettingsClick: (() -> Unit)? = null,\n",
            "AppShellComponents AppTabActions download callbacks",
        )
        changed |= _replace_once(
            shell,
            "            AppScreenTab.LiveTv -> {\n"
            "                LiveTvScreen(\n"
            "                    modifier = Modifier.fillMaxSize(),\n"
            "                    scrollToTopRequests = requests.liveTvScrollToTopRequests,\n"
            "                    onChannelClick = actions.onLiveTvChannelClick,\n"
            "                    onVodClick = actions.onLiveTvVodClick,\n"
            "                )\n"
            "            }\n",
            "            AppScreenTab.LiveTv -> {\n"
            "                DownloadsScreen(\n"
            "                    onBack = null,\n"
            "                    onOpenDownload = { item -> actions.onOpenDownload?.invoke(item) },\n"
            "                    onOpenDetails = { item -> actions.onDownloadDetailsClick?.invoke(item) },\n"
            "                    onNavigateToShow = actions.onDownloadShowClick,\n"
            "                    onOpenSettings = actions.onDownloadSettingsClick,\n"
            "                )\n"
            "            }\n",
            "AppShellComponents DownloadsScreen in tab host",
        )
        changed |= _replace_once(
            shell,
            "                if (showLiveTv) {\n"
            "                    TabletTopPillItem(\n"
            "                        label = stringResource(Res.string.compose_nav_live_tv),\n"
            "                        selected = selectedTab == AppScreenTab.LiveTv,\n"
            "                        onClick = { onTabSelected(AppScreenTab.LiveTv) },\n"
            "                        icon = {\n"
            "                            Icon(\n"
            "                                imageVector = Icons.Filled.Tv,\n"
            "                                contentDescription = stringResource(Res.string.compose_nav_live_tv),\n"
            "                                modifier = Modifier.size(18.dp),\n"
            "                                tint = if (selectedTab == AppScreenTab.LiveTv) {\n"
            "                                    MaterialTheme.colorScheme.onPrimaryContainer\n"
            "                                } else {\n"
            "                                    MaterialTheme.colorScheme.onSurfaceVariant\n"
            "                                },\n"
            "                            )\n"
            "                        },\n"
            "                    )\n"
            "                }\n",
            "                if (showLiveTv) {\n"
            "                    TabletTopPillItem(\n"
            "                        label = stringResource(Res.string.compose_settings_root_downloads_title),\n"
            "                        selected = selectedTab == AppScreenTab.LiveTv,\n"
            "                        onClick = { onTabSelected(AppScreenTab.LiveTv) },\n"
            "                        icon = {\n"
            "                            Icon(\n"
            "                                imageVector = Icons.Rounded.Download,\n"
            "                                contentDescription = stringResource(Res.string.compose_settings_root_downloads_title),\n"
            "                                modifier = Modifier.size(18.dp),\n"
            "                                tint = if (selectedTab == AppScreenTab.LiveTv) {\n"
            "                                    tokens.colors.textPrimary\n"
            "                                } else {\n"
            "                                    tokens.colors.textMuted\n"
            "                                },\n"
            "                            )\n"
            "                        },\n"
            "                    )\n"
            "                }\n",
            "AppShellComponents TabletTopPillItem Downloads",
        )
        if changed:
            patched.append(str(shell.relative_to(root)))

    tabs_dest = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/MainTabsDestination.kt"
    if tabs_dest.is_file():
        changed = False
        changed |= _replace_once(
            tabs_dest,
            "import androidx.compose.material.icons.filled.Tv\n",
            "import androidx.compose.material.icons.filled.Tv\n"
            "import androidx.compose.material.icons.rounded.Download\n",
            "MainTabsDestination Download icon import",
        )
        changed |= _replace_once(
            tabs_dest,
            "import nuvio.composeapp.generated.resources.compose_nav_live_tv\n",
            "import nuvio.composeapp.generated.resources.compose_nav_live_tv\n"
            "import nuvio.composeapp.generated.resources.compose_settings_root_downloads_title\n",
            "MainTabsDestination downloads title resource import",
        )
        changed |= _replace_once(
            tabs_dest,
            "    if (showLiveTv) {\n"
            "        add(\n"
            "            FloatingNavigationItem(\n"
            "                selected = highlightedTab == AppScreenTab.LiveTv,\n"
            "                onClick = { onTabSelected(AppScreenTab.LiveTv) },\n"
            "                icon = Icons.Filled.Tv,\n"
            "                label = stringResource(Res.string.compose_nav_live_tv),\n"
            "            ),\n"
            "        )\n"
            "    }\n",
            "    if (showLiveTv) {\n"
            "        add(\n"
            "            FloatingNavigationItem(\n"
            "                selected = highlightedTab == AppScreenTab.LiveTv,\n"
            "                onClick = { onTabSelected(AppScreenTab.LiveTv) },\n"
            "                icon = Icons.Rounded.Download,\n"
            "                label = stringResource(Res.string.compose_settings_root_downloads_title),\n"
            "            ),\n"
            "        )\n"
            "    }\n",
            "MainTabsDestination floating nav Downloads",
        )
        changed |= _replace_once(
            tabs_dest,
            "        if (showLiveTv) {\n"
            "            NavItem(\n"
            "                selected = highlightedTab == AppScreenTab.LiveTv,\n"
            "                onClick = { onTabSelected(AppScreenTab.LiveTv) },\n"
            "                icon = Icons.Filled.Tv,\n"
            "                contentDescription = stringResource(Res.string.compose_nav_live_tv),\n"
            "            )\n"
            "        }\n",
            "        if (showLiveTv) {\n"
            "            NavItem(\n"
            "                selected = highlightedTab == AppScreenTab.LiveTv,\n"
            "                onClick = { onTabSelected(AppScreenTab.LiveTv) },\n"
            "                icon = Icons.Rounded.Download,\n"
            "                contentDescription = stringResource(Res.string.compose_settings_root_downloads_title),\n"
            "            )\n"
            "        }\n",
            "MainTabsDestination classic nav Downloads",
        )
        if changed:
            patched.append(str(tabs_dest.relative_to(root)))

    enhanced_settings = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/NuvioEnhancedSettingsPage.kt"
    if enhanced_settings.is_file():
        changed = _replace_once(
            enhanced_settings,
            "                    SettingsGroupDivider(isTablet = isTablet)\n"
            "                    SettingsSwitchRow(\n"
            "                        title = stringResource(Res.string.nuvio_enhanced_live_tv_title),\n"
            "                        description = stringResource(Res.string.nuvio_enhanced_live_tv_desc),\n"
            "                        checked = liveTvUiState.showInNavigation,\n"
            "                        isTablet = isTablet,\n"
            "                        highlighted = isNew(NuvioEnhancedFeature.LiveTvControls),\n"
            "                        onCheckedChange = {\n"
            "                            markSeen(NuvioEnhancedFeature.LiveTvControls)\n"
            "                            LiveTvRepository.setNavigationEnabled(it)\n"
            "                            NuvioEnhancedSettingsRepository.setLiveTvEnabled(it)\n"
            "                        },\n"
            "                    )\n",
            "",
            "NuvioEnhancedSettingsPage remove obsolete Live TV toggle",
        )
        if changed:
            patched.append(str(enhanced_settings.relative_to(root)))

    dl_screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsScreen.kt"
    if dl_screen.is_file():
        changed = False
        changed |= _replace_once(
            dl_screen,
            "@Composable\n"
            "fun DownloadsScreen(\n"
            "    onBack: () -> Unit,\n",
            "@Composable\n"
            "fun DownloadsScreen(\n"
            "    onBack: (() -> Unit)? = null,\n",
            "DownloadsScreen optional onBack parameter",
        )
        changed |= _replace_once(
            dl_screen,
            "                onBack = {\n"
            "                    if (selectedShowId != null) {\n"
            "                        onBackFromShow?.invoke() ?: run { selectedShowId = null }\n"
            "                    } else {\n"
            "                        onBack()\n"
            "                    }\n"
            "                },\n",
            "                onBack = if (selectedShowId != null) {\n"
            "                    { onBackFromShow?.invoke() ?: run { selectedShowId = null } }\n"
            "                } else {\n"
            "                    onBack\n"
            "                },\n",
            "DownloadsScreen hide back arrow when top-level tab",
        )
        if changed:
            patched.append(str(dl_screen.relative_to(root)))

    return patched


def _patch_cloudstream_host_and_settings(root: Path) -> list[str]:
    """Fix Issue #2 & Issue #3 across CloudStream Android host, ABI stubs, Home, and Streams."""
    patched: list[str] = []

    # 1. v1.1.2 compile fixes + Toast feedback on CloudStream gear icon
    repo_kt = root / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/cloudstream/CloudStreamRepository.kt"
    if repo_kt.is_file():
        if _replace_once(
            repo_kt,
            '} ?: Result.failure(\n'
            '                            IllegalStateException("CloudStream provider search timed out',
            '} ?: Result.failure<List<CloudStreamSearchItem>>(\n'
            '                            IllegalStateException("CloudStream provider search timed out',
            "CloudStreamRepository explicit Result.failure type",
        ):
            patched.append(str(repo_kt.relative_to(root)))

    section_kt = root / "composeApp/src/fullCommonMain/kotlin/com/nuvio/app/features/plugins/CloudStreamSettingsSection.kt"
    if section_kt.is_file():
        changed = False
        changed |= _replace_once(
            section_kt,
            "import com.nuvio.app.core.ui.NuvioSurfaceCard\n",
            "import com.nuvio.app.core.ui.NuvioSurfaceCard\n"
            "import com.nuvio.app.core.ui.NuvioToastController\n",
            "CloudStreamSettingsSection NuvioToastController import",
        )
        changed |= _replace_once(
            section_kt,
            "                    IconButton(\n"
            "                        enabled = plugin.verified && plugin.compatibility.isRunnable,\n"
            "                        onClick = {\n"
            "                            repositoryUrl = repository.manifest.sourceUrl\n",
            "                    IconButton(\n"
            "                        onClick = {\n"
            "                            repositoryUrl = repository.manifest.sourceUrl\n",
            "CloudStreamSettingsSection repo edit IconButton",
        )
        changed |= _replace_once(
            section_kt,
            "                if (plugin.isInstalled) {\n"
            "                    IconButton(\n"
            "                        onClick = {\n"
            "                            scope.launch {\n"
            "                                CloudStreamRepository.openPluginSettings(plugin.metadata.id.value)\n"
            "                                    .onFailure { error ->\n"
            "                                        onMessage(\n"
            "                                            error.message ?: \"This extension does not provide configurable settings\",\n"
            "                                        )\n"
            "                                    }\n"
            "                            }\n"
            "                        },\n"
            "                    ) {\n",
            "                if (plugin.isInstalled) {\n"
            "                    IconButton(\n"
            "                        enabled = plugin.verified && plugin.compatibility.isRunnable,\n"
            "                        onClick = {\n"
            "                            scope.launch {\n"
            "                                CloudStreamRepository.openPluginSettings(plugin.metadata.id.value)\n"
            "                                    .onFailure { error ->\n"
            "                                        val errText = error.message\n"
            "                                            ?: \"This extension does not provide configurable settings\"\n"
            "                                        onMessage(errText)\n"
            "                                        NuvioToastController.show(errText)\n"
            "                                    }\n"
            "                            }\n"
            "                        },\n"
            "                    ) {\n",
            "CloudStreamSettingsSection gear IconButton toast & enabled",
        )
        if changed:
            patched.append(str(section_kt.relative_to(root)))

    # 2. MainActivity: pass `this` (AppCompatActivity) in onCreate + onStart + onResume
    main_act = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/MainActivity.kt"
    if main_act.is_file():
        changed = False
        changed |= _replace_once(
            main_act,
            "    override fun onResume() {\n"
            "        super.onResume()\n"
            "        com.nuvio.app.features.cloudstream.CloudStreamPlatformRuntime.initialize(this)\n"
            "    }\n",
            "    override fun onStart() {\n"
            "        super.onStart()\n"
            "        com.nuvio.app.features.cloudstream.CloudStreamPlatformRuntime.initialize(this)\n"
            "    }\n\n"
            "    override fun onResume() {\n"
            "        super.onResume()\n"
            "        com.nuvio.app.features.cloudstream.CloudStreamPlatformRuntime.initialize(this)\n"
            "    }\n",
            "MainActivity onStart CloudStream activity bind",
        )
        changed |= _replace_once(
            main_act,
            "        com.nuvio.app.features.cloudstream.CloudStreamPlatformRuntime.initialize(applicationContext)\n",
            "        com.nuvio.app.features.cloudstream.CloudStreamPlatformRuntime.initialize(this)\n",
            "MainActivity onCreate CloudStream activity bind",
        )
        if changed:
            patched.append(str(main_act.relative_to(root)))

    # 3. Android UI dependencies, MaterialComponents theme, ProGuard & resource shrinker rules
    compose_gradle = root / "composeApp/build.gradle.kts"
    if compose_gradle.is_file():
        if _replace_once(
            compose_gradle,
            '                implementation("androidx.recyclerview:recyclerview:1.4.0")\n',
            '                implementation("androidx.recyclerview:recyclerview:1.4.0")\n'
            '                implementation("com.google.android.material:material:1.12.0")\n'
            '                implementation("androidx.constraintlayout:constraintlayout:2.2.0")\n'
            '                implementation("androidx.cardview:cardview:1.0.0")\n'
            '                implementation("androidx.coordinatorlayout:coordinatorlayout:1.2.0")\n'
            '                implementation("androidx.preference:preference-ktx:1.2.1")\n',
            "composeApp Material & AndroidX UI dependencies",
        ):
            patched.append(str(compose_gradle.relative_to(root)))

    android_gradle = root / "androidApp/build.gradle.kts"
    if android_gradle.is_file():
        if _replace_once(
            android_gradle,
            "    implementation(libs.androidx.appcompat)\n",
            "    implementation(libs.androidx.appcompat)\n"
            '    implementation("com.google.android.material:material:1.12.0")\n',
            "androidApp Material dependency",
        ):
            patched.append(str(android_gradle.relative_to(root)))

    for rel_theme in [
        "composeApp/src/androidMain/res/values/themes.xml",
        "composeApp/src/androidMain/res/values-v31/themes.xml",
    ]:
        theme_path = root / rel_theme
        if theme_path.is_file():
            if _replace_once(
                theme_path,
                'parent="Theme.AppCompat.DayNight.NoActionBar"',
                'parent="Theme.MaterialComponents.DayNight.NoActionBar"',
                f"{rel_theme} MaterialComponents parent",
            ):
                patched.append(rel_theme)

    keep_xml = root / "composeApp/src/androidMain/res/raw/keep_cloudstream_ui.xml"
    keep_xml.parent.mkdir(parents=True, exist_ok=True)
    keep_xml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources xmlns:tools="http://schemas.android.com/tools"\n'
        '    tools:keep="@layout/design_*,@layout/mtrl_*,@style/Widget_MaterialComponents_*,'
        '@style/Widget_Design_*,@style/Theme_Design_*,@style/Theme_MaterialComponents_*" />\n',
        encoding="utf-8",
    )
    patched.append(str(keep_xml.relative_to(root)))

    proguard_cs = root / "composeApp/proguard-cloudstream-full.pro"
    if proguard_cs.is_file():
        extra_rules = (
            "\n# Keep AndroidX & Material UI classes used dynamically by CloudStream .cs3 settings dialogs/fragments\n"
            "-keep class androidx.appcompat.app.** { *; }\n"
            "-keep class androidx.appcompat.widget.** { *; }\n"
            "-keep class androidx.fragment.app.** { *; }\n"
            "-keep class androidx.recyclerview.widget.** { *; }\n"
            "-keep class androidx.constraintlayout.widget.** { *; }\n"
            "-keep class androidx.cardview.widget.** { *; }\n"
            "-keep class androidx.coordinatorlayout.widget.** { *; }\n"
            "-keep class androidx.preference.** { *; }\n"
            "-keep class com.google.android.material.** { *; }\n"
            "-dontwarn com.google.android.material.**\n"
        )
        pg_text = proguard_cs.read_text(encoding="utf-8", errors="replace")
        if "androidx.fragment.app.**" not in pg_text:
            proguard_cs.write_text(pg_text + extra_rules, encoding="utf-8")
            patched.append(str(proguard_cs.relative_to(root)))

    # 4. CloudStream host ABI classes: CommonActivity.showToast, CloudStreamApp, AcraApplication
    common_act = root / "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/CommonActivity.kt"
    common_act.write_text(
        """package com.lagradost.cloudstream3

import android.app.Activity
import android.widget.Toast
import androidx.annotation.MainThread
import androidx.annotation.StringRes
import com.nuvio.app.core.ui.NuvioToastController
import java.lang.ref.WeakReference

/** Current-activity and Toast ABI used by CloudStream extensions and settings screens. */
object CommonActivity {
    const val TAG = "COMPACT"

    private var activityReference: WeakReference<Activity>? = null

    var activity: Activity?
        get() = activityReference?.get()
        private set(value) {
            activityReference = value?.let(::WeakReference)
        }

    @MainThread
    fun setActivityInstance(newActivity: Activity?) {
        activity = newActivity
    }

    fun showToast(@StringRes message: Int, duration: Int? = null) {
        val act = activity ?: CloudStreamApp.context ?: return
        val text = runCatching { act.getString(message) }.getOrNull() ?: return
        showToast(activity, text, duration)
    }

    fun showToast(message: String?, duration: Int? = null) {
        if (message.isNullOrBlank()) return
        val act = activity
        if (act != null && !act.isFinishing && !act.isDestroyed) {
            act.runOnUiThread {
                showToast(act, message, duration)
            }
        } else {
            NuvioToastController.show(message.trim())
        }
    }

    @MainThread
    fun showToast(act: Activity?, @StringRes message: Int, duration: Int? = null) {
        val ctx = act ?: activity ?: CloudStreamApp.context ?: return
        val text = runCatching { ctx.getString(message) }.getOrNull() ?: return
        showToast(act, text, duration)
    }

    @MainThread
    fun showToast(act: Activity?, message: String?, duration: Int? = null) {
        val trimmed = message?.trim()?.takeIf { it.isNotEmpty() } ?: return
        val target = act ?: activity ?: CloudStreamApp.context
        val toastLength = if (duration == Toast.LENGTH_LONG) Toast.LENGTH_LONG else Toast.LENGTH_SHORT
        if (target != null) {
            runCatching {
                Toast.makeText(target, trimmed, toastLength).show()
            }.onFailure {
                NuvioToastController.show(trimmed)
            }
        } else {
            NuvioToastController.show(trimmed)
        }
    }
}
""",
        encoding="utf-8",
    )
    patched.append(str(common_act.relative_to(root)))

    cs_app = root / "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/CloudStreamApp.kt"
    cs_app.write_text(
        """package com.lagradost.cloudstream3

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import com.lagradost.cloudstream3.utils.DataStore
import java.lang.ref.WeakReference

/** Host-context and preference ABI used by CloudStream extensions. */
class CloudStreamApp {
    companion object {
        private var contextReference: WeakReference<Context>? = null

        var context: Context?
            get() = contextReference?.get()
            set(value) {
                contextReference = value?.let(::WeakReference)
                if (value != null) com.lagradost.api.setContext(WeakReference(value as Any))
            }

        tailrec fun Context.getActivity(): Activity? = when (this) {
            is Activity -> this
            is ContextWrapper -> baseContext.getActivity()
            else -> null
        }

        fun <T : Any> getKeyClass(path: String, valueType: Class<T>): T? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.getKey(path, valueType) }
            }
        }

        fun <T : Any> setKeyClass(path: String, value: T) {
            setKey(path, value)
        }

        inline fun <reified T : Any> getKey(path: String): T? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.getKey<T>(path) }
            }
        }

        inline fun <reified T : Any> getKey(path: String, defVal: T?): T? {
            return getKey<T>(path) ?: defVal
        }

        inline fun <reified T : Any> getKey(folder: String, path: String): T? {
            return getKey<T>(DataStore.getFolderName(folder, path))
        }

        inline fun <reified T : Any> getKey(folder: String, path: String, defVal: T?): T? {
            return getKey<T>(folder, path) ?: defVal
        }

        fun <T> setKey(path: String, value: T) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.setKey(path, value) }
            }
        }

        fun <T> setKey(folder: String, path: String, value: T) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.setKey(folder, path, value) }
            }
        }

        fun removeKey(path: String) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.removeKey(path) }
            }
        }

        fun removeKey(folder: String, path: String) {
            context?.let { currentContext ->
                with(DataStore) { currentContext.removeKey(folder, path) }
            }
        }

        fun removeKeys(folder: String): Int? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.removeKeys(folder) }
            }
        }

        fun getKeys(folder: String): List<String>? {
            return context?.let { currentContext ->
                with(DataStore) { currentContext.getKeys(folder) }
            }
        }
    }
}
""",
        encoding="utf-8",
    )
    patched.append(str(cs_app.relative_to(root)))

    acra_app = root / "composeApp/src/androidFull/kotlin/com/lagradost/cloudstream3/AcraApplication.kt"
    acra_app.write_text(
        """package com.lagradost.cloudstream3

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
""",
        encoding="utf-8",
    )
    patched.append(str(acra_app.relative_to(root)))

    # 5. CloudStreamPlatformRuntime.android.kt
    runtime_kt = root / "composeApp/src/androidFull/kotlin/com/nuvio/app/features/cloudstream/CloudStreamPlatformRuntime.android.kt"
    if runtime_kt.is_file():
        changed = False
        changed |= _replace_once(
            runtime_kt,
            "import com.lagradost.cloudstream3.TvType\n",
            "import com.lagradost.cloudstream3.TvType\n"
            "import com.lagradost.cloudstream3.fixUrl\n",
            "CloudStreamPlatformRuntime fixUrl import",
        )
        changed |= _replace_once(
            runtime_kt,
            "    actual suspend fun openSettings(plugin: CloudStreamPluginItem): Result<Unit> = runCatching {\n"
            "        // Loading through the same path as provider execution ensures Plugin.load() has\n"
            "        // populated the extension's openSettings callback and its resources/context.\n"
            "        provider(plugin)\n"
            "        val loadedPlugin = synchronized(loadedLock) { loaded[plugin.metadata.id.value] }\n"
            "            ?: error(\"CloudStream extension could not be loaded\")\n"
            "        val configurablePlugin = loadedPlugin.instance as? Plugin\n"
            "            ?: error(\"This extension does not expose a settings screen\")\n"
            "        val openSettings = configurablePlugin.openSettings\n"
            "            ?: error(\"This extension does not provide configurable settings\")\n"
            "        val activity = activityReference?.get()?.takeUnless { it.isFinishing || it.isDestroyed }\n"
            "            ?: CommonActivity.activity?.takeUnless { it.isFinishing || it.isDestroyed }\n"
            "            ?: error(\"The app activity is not available. Reopen Nuvio and try again.\")\n"
            "        withContext(Dispatchers.Main.immediate) {\n"
            "            CommonActivity.setActivityInstance(activity)\n"
            "            openSettings.invoke(activity)\n"
            "        }\n"
            "        RuntimeDiagnostics.recordLog(\"CloudStream plugin-settings-opened id=${plugin.metadata.id.value}\")\n"
            "    }",
            "    actual suspend fun openSettings(plugin: CloudStreamPluginItem): Result<Unit> = runCatching {\n"
            "        val activity = activityReference?.get()?.takeUnless { it.isFinishing || it.isDestroyed }\n"
            "            ?: CommonActivity.activity?.takeUnless { it.isFinishing || it.isDestroyed }\n"
            "            ?: error(\"The app activity is not available. Reopen Nuvio and try again.\")\n"
            "        CommonActivity.setActivityInstance(activity)\n"
            "        provider(plugin)\n"
            "        var loadedPlugin = synchronized(loadedLock) { loaded[plugin.metadata.id.value] }\n"
            "            ?: error(\"CloudStream extension could not be loaded\")\n"
            "        // Many CloudStream plugins (e.g. StreamPlay) capture `context as AppCompatActivity`\n"
            "        // inside `load(context)` and later call `activity.supportFragmentManager` inside\n"
            "        // `openSettings`. If the plugin loaded before the current Activity existed or after\n"
            "        // an Activity recreation, reload it once bound to the live Activity.\n"
            "        if (loadedPlugin.boundActivity?.get() !== activity) {\n"
            "            loadedPlugin = withContext(Dispatchers.IO) {\n"
            "                loadMutex.withLock {\n"
            "                    synchronized(loadedLock) {\n"
            "                        loaded.remove(plugin.metadata.id.value)?.unload()\n"
            "                        loadPlugin(plugin).also { loaded[plugin.metadata.id.value] = it }\n"
            "                    }\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "        val configurablePlugin = loadedPlugin.instance as? Plugin\n"
            "            ?: error(\"This extension does not expose a settings screen\")\n"
            "        val openSettings = configurablePlugin.openSettings\n"
            "            ?: error(\"This extension does not provide configurable settings\")\n"
            "        withContext(Dispatchers.Main.immediate) {\n"
            "            CommonActivity.setActivityInstance(activity)\n"
            "            openSettings.invoke(activity)\n"
            "        }\n"
            "        RuntimeDiagnostics.recordLog(\"CloudStream plugin-settings-opened id=${plugin.metadata.id.value}\")\n"
            "    }",
            "CloudStreamPlatformRuntime openSettings live Activity rebind",
        )
        changed |= _replace_once(
            runtime_kt,
            "        val manifest = ZipFile(file).use { archive ->\n"
            "            val entry = archive.getEntry(\"manifest.json\")\n"
            "                ?: error(\"CloudStream package has no manifest.json\")\n"
            "            archive.getInputStream(entry).bufferedReader().use { reader ->\n"
            "                json.decodeFromString<CloudStreamCs3Manifest>(reader.readText())\n"
            "            }\n"
            "        }\n",
            "        var hasBundledResources = false\n"
            "        val manifest = ZipFile(file).use { archive ->\n"
            "            hasBundledResources = archive.getEntry(\"resources.arsc\") != null\n"
            "            val entry = archive.getEntry(\"manifest.json\")\n"
            "                ?: error(\"CloudStream package has no manifest.json\")\n"
            "            archive.getInputStream(entry).bufferedReader().use { reader ->\n"
            "                json.decodeFromString<CloudStreamCs3Manifest>(reader.readText())\n"
            "            }\n"
            "        }\n",
            "CloudStreamPlatformRuntime detect resources.arsc",
        )
        changed |= _replace_once(
            runtime_kt,
            "        val identityContext = CloudStreamIdentityContext(context)\n"
            "        CloudStreamApp.context = identityContext\n"
            "        setContext(WeakReference(identityContext))\n"
            "        applyHostCompatibilityDefaults(pluginClassName)\n"
            "        if (manifest.requiresResources) instance.attachResources(identityContext, file)\n",
            "        val identityContext = CloudStreamIdentityContext(context)\n"
            "        val liveActivity = activityReference?.get()?.takeUnless { it.isFinishing || it.isDestroyed }\n"
            "            ?: CommonActivity.activity?.takeUnless { it.isFinishing || it.isDestroyed }\n"
            "        val pluginHostContext: Context = liveActivity ?: identityContext\n"
            "        CloudStreamApp.context = pluginHostContext\n"
            "        setContext(WeakReference(pluginHostContext))\n"
            "        applyHostCompatibilityDefaults(pluginClassName)\n"
            "        if (manifest.requiresResources || hasBundledResources) {\n"
            "            runCatching { instance.attachResources(pluginHostContext, file) }\n"
            "                .onFailure { err -> log.w(err) { \"Failed attaching plugin resources for ${item.metadata.internalName}\" } }\n"
            "        }\n",
            "CloudStreamPlatformRuntime attachResources & AppCompatActivity host context",
        )
        changed |= _replace_once(
            runtime_kt,
            "            if (instance is Plugin) instance.load(identityContext) else instance.load()\n",
            "            if (instance is Plugin) {\n"
            "                try {\n"
            "                    instance.load(pluginHostContext)\n"
            "                } catch (castOrUiError: Throwable) {\n"
            "                    if (pluginHostContext !== identityContext) {\n"
            "                        APIHolder.allProviders.removeAll { it !in providersBefore }\n"
            "                        extractorApis.removeAll { it !in extractorsBefore }\n"
            "                        instance.load(identityContext)\n"
            "                    } else {\n"
            "                        throw castOrUiError\n"
            "                    }\n"
            "                }\n"
            "            } else {\n"
            "                instance.load()\n"
            "            }\n",
            "CloudStreamPlatformRuntime load(pluginHostContext)",
        )
        changed |= _replace_once(
            runtime_kt,
            "            return LoadedPlugin(\n"
            "                id = item.metadata.id.value,\n"
            "                path = file.absolutePath,\n"
            "                context = identityContext,\n"
            "                instance = instance,\n"
            "                providers = providers,\n"
            "                extractors = registeredExtractors,\n"
            "                provider = providers.takeIf { it.isNotEmpty() }\n"
            "                    ?.let { AndroidDexCloudStreamProvider(item.metadata.id.value, it) },\n"
            "            )\n",
            "            return LoadedPlugin(\n"
            "                id = item.metadata.id.value,\n"
            "                path = file.absolutePath,\n"
            "                context = pluginHostContext,\n"
            "                boundActivity = liveActivity?.let(::WeakReference),\n"
            "                instance = instance,\n"
            "                providers = providers,\n"
            "                extractors = registeredExtractors,\n"
            "                provider = providers.takeIf { it.isNotEmpty() }\n"
            "                    ?.let { AndroidDexCloudStreamProvider(item.metadata.id.value, it) },\n"
            "            )\n",
            "CloudStreamPlatformRuntime LoadedPlugin boundActivity",
        )
        changed |= _replace_once(
            runtime_kt,
            "    private const val DEFAULT_HTTP_TIMEOUT_SECONDS = 120L\n",
            "    private const val DEFAULT_HTTP_TIMEOUT_SECONDS = 20L\n",
            "CloudStreamPlatformRuntime HTTP timeout 20s",
        )
        changed |= _replace_once(
            runtime_kt,
            "    private data class LoadedPlugin(\n"
            "        val id: String,\n"
            "        val path: String,\n"
            "        @Suppress(\"unused\") val context: Context,\n"
            "        val instance: BasePlugin,\n",
            "    private data class LoadedPlugin(\n"
            "        val id: String,\n"
            "        val path: String,\n"
            "        @Suppress(\"unused\") val context: Context,\n"
            "        val boundActivity: WeakReference<Activity>? = null,\n"
            "        val instance: BasePlugin,\n",
            "CloudStreamPlatformRuntime LoadedPlugin definition",
        )
        changed |= _replace_once(
            runtime_kt,
            "    override suspend fun getMainPage(\n"
            "        page: Int,\n"
            "    ): List<Pair<String, List<CloudStreamSearchItem>>> = withContext(Dispatchers.IO) {\n"
            "        val sections = Collections.synchronizedList(\n"
            "            mutableListOf<Pair<String, List<CloudStreamSearchItem>>>(),\n"
            "        )\n"
            "        val apiGate = Semaphore(CLOUDSTREAM_API_CONCURRENCY)\n"
            "        var lastError: Throwable? = null\n\n"
            "        coroutineScope {\n"
            "            val eligibleProviders = providers.filter { it.hasMainPage || it.mainPage.isNotEmpty() }\n"
            "                .ifEmpty { providers }\n"
            "            eligibleProviders.map { api ->\n"
            "                async {\n"
            "                    apiGate.withPermit {\n"
            "                        val requests = api.mainPage.ifEmpty {\n"
            "                            listOf(com.lagradost.cloudstream3.MainPageData(api.name, api.mainUrl, false))\n"
            "                        }\n\n"
            "                        suspend fun loadRequest(data: com.lagradost.cloudstream3.MainPageData) =\n"
            "                            runCatching {\n"
            "                                withTimeout(stageTimeout(api.getMainPageTimeoutMs, DEFAULT_DISCOVERY_TIMEOUT_MS)) {\n"
            "                                    api.getMainPage(\n"
            "                                        page.coerceAtLeast(1),\n"
            "                                        MainPageRequest(data.name, data.data, data.horizontalImages),\n"
            "                                    )\n"
            "                                }\n"
            "                            }.onSuccess { response ->\n"
            "                                response?.items.orEmpty().forEach { section ->\n"
            "                                    val title = if (providers.size > 1) \"${api.name} · ${section.name}\" else section.name\n"
            "                                    val items = section.list.map { it.toNuvioSearchItem(api) }\n"
            "                                    if (items.isNotEmpty()) sections += title to items\n"
            "                                }\n"
            "                            }.onFailure { error ->\n"
            "                                synchronized(sections) { lastError = error }\n"
            "                                log.w(error) { \"CloudStream main page failed api=${api.name}\" }\n"
            "                            }\n\n"
            "                        if (api.sequentialMainPage) {\n"
            "                            requests.forEachIndexed { index, data ->\n"
            "                                if (index > 0 && api.sequentialMainPageDelay > 0) {\n"
            "                                    delay(api.sequentialMainPageDelay)\n"
            "                                }\n"
            "                                loadRequest(data)\n"
            "                            }\n"
            "                        } else {\n"
            "                            requests.map { data -> async { loadRequest(data) } }.awaitAll()\n"
            "                        }\n"
            "                    }\n"
            "                }\n"
            "            }.awaitAll()\n"
            "        }\n\n"
            "        if (sections.isEmpty()) throw lastError ?: return@withContext emptyList()\n"
            "        synchronized(sections) { sections.toList() }\n"
            "    }\n\n"
            "    override suspend fun search(query: String): List<CloudStreamSearchItem> = withContext(Dispatchers.IO) {\n"
            "        val results = Collections.synchronizedList(mutableListOf<CloudStreamSearchItem>())\n"
            "        val apiGate = Semaphore(CLOUDSTREAM_API_CONCURRENCY)\n"
            "        var lastError: Throwable? = null\n\n"
            "        coroutineScope {\n"
            "            providers.map { api ->\n"
            "                async {\n"
            "                    apiGate.withPermit {\n"
            "                        runCatching {\n"
            "                            withTimeout(stageTimeout(api.searchTimeoutMs, DEFAULT_DISCOVERY_TIMEOUT_MS)) {\n"
            "                                api.search(query, 1)?.items.orEmpty()\n"
            "                            }\n"
            "                        }.onSuccess { items ->\n"
            "                            log.d {\n"
            "                                \"CloudStream search api=${api.name} query=$query returned=${items.size} \" +\n"
            "                                    \"sample=${items.take(3).joinToString { it.name }}\"\n"
            "                            }\n"
            "                            results += items.map { it.toNuvioSearchItem(api) }\n"
            "                        }.onFailure { error ->\n"
            "                            synchronized(results) { lastError = error }\n"
            "                            log.w(error) { \"CloudStream search failed api=${api.name}\" }\n"
            "                        }\n"
            "                    }\n"
            "                }\n"
            "            }.awaitAll()\n"
            "        }\n\n"
            "        if (results.isEmpty()) throw lastError ?: return@withContext emptyList()\n"
            "        synchronized(results) { results.toList().distinctBy { it.data } }\n"
            "    }",
            "    override suspend fun getMainPage(\n"
            "        page: Int,\n"
            "    ): List<Pair<String, List<CloudStreamSearchItem>>> = withContext(Dispatchers.IO) {\n"
            "        val eligibleProviders = providers\n"
            "            .filter { api ->\n"
            "                api.hasMainPage || api.mainPage.any { it.name.isNotBlank() || it.data.isNotBlank() }\n"
            "            }\n"
            "            .ifEmpty { providers }\n"
            "        // Multi-API packages like StreamPlay register sibling variants (StreamPlayLite,\n"
            "        // StreamPlayTorrent) with identical mainPage definitions. Deduplicate identical\n"
            "        // (name, data) catalogue endpoints across sibling APIs and bound per-API initial\n"
            "        // home rows so Home loads quickly without timing out.\n"
            "        val seenEndpoints = HashSet<String>()\n"
            "        val apiPlans = eligibleProviders.mapNotNull { api ->\n"
            "            val rawRequests = api.mainPage\n"
            "                .filter { it.name.isNotBlank() || it.data.isNotBlank() }\n"
            "                .ifEmpty {\n"
            "                    if (api.hasMainPage) {\n"
            "                        listOf(com.lagradost.cloudstream3.MainPageData(api.name, api.mainUrl, false))\n"
            "                    } else {\n"
            "                        emptyList()\n"
            "                    }\n"
            "                }\n"
            "            val deduped = rawRequests.filter { req ->\n"
            "                val key = \"${req.name.trim().lowercase()}::${req.data.trim()}\"\n"
            "                req.data.isBlank() || seenEndpoints.add(key)\n"
            "            }.take(if (eligibleProviders.size > 1 && page <= 1) 12 else 24)\n"
            "            if (deduped.isEmpty()) null else (api to deduped)\n"
            "        }\n"
            "        val requestGate = Semaphore(6)\n"
            "        var lastError: Throwable? = null\n"
            "        val orderedBuckets = arrayOfNulls<List<Pair<String, List<CloudStreamSearchItem>>>>(apiPlans.size)\n\n"
            "        coroutineScope {\n"
            "            apiPlans.mapIndexed { planIndex, (api, requests) ->\n"
            "                async {\n"
            "                    val apiSections = Collections.synchronizedList(\n"
            "                        mutableListOf<Pair<String, List<CloudStreamSearchItem>>>(),\n"
            "                    )\n"
            "                    suspend fun loadRequest(data: com.lagradost.cloudstream3.MainPageData) {\n"
            "                        requestGate.withPermit {\n"
            "                            runCatching {\n"
            "                                withTimeout(stageTimeout(api.getMainPageTimeoutMs, DEFAULT_MAIN_PAGE_SECTION_TIMEOUT_MS)) {\n"
            "                                    api.getMainPage(\n"
            "                                        page.coerceAtLeast(1),\n"
            "                                        MainPageRequest(data.name, data.data, data.horizontalImages),\n"
            "                                    )\n"
            "                                }\n"
            "                            }.onSuccess { response ->\n"
            "                                response?.items.orEmpty().forEach { section ->\n"
            "                                    val title = if (apiPlans.size > 1) \"${api.name} · ${section.name}\" else section.name\n"
            "                                    val items = section.list.map { it.toNuvioSearchItem(api) }\n"
            "                                    if (items.isNotEmpty()) apiSections += title to items\n"
            "                                }\n"
            "                            }.onFailure { error ->\n"
            "                                synchronized(orderedBuckets) { lastError = error }\n"
            "                                log.w(error) { \"CloudStream main page failed api=${api.name} section=${data.name}\" }\n"
            "                            }\n"
            "                        }\n"
            "                    }\n\n"
            "                    if (api.sequentialMainPage) {\n"
            "                        requests.forEachIndexed { index, data ->\n"
            "                            if (index > 0 && api.sequentialMainPageDelay > 0) {\n"
            "                                delay(api.sequentialMainPageDelay)\n"
            "                            }\n"
            "                            loadRequest(data)\n"
            "                        }\n"
            "                    } else {\n"
            "                        requests.map { data -> async { loadRequest(data) } }.awaitAll()\n"
            "                    }\n"
            "                    orderedBuckets[planIndex] = synchronized(apiSections) { apiSections.toList() }\n"
            "                }\n"
            "            }.awaitAll()\n"
            "        }\n\n"
            "        val merged = orderedBuckets.filterNotNull().flatten()\n"
            "        if (merged.isEmpty()) throw lastError ?: return@withContext emptyList()\n"
            "        merged\n"
            "    }\n\n"
            "    override suspend fun search(query: String): List<CloudStreamSearchItem> = withContext(Dispatchers.IO) {\n"
            "        val apiGate = Semaphore(CLOUDSTREAM_API_CONCURRENCY)\n"
            "        var lastError: Throwable? = null\n"
            "        val sanitizedQuery = query.replace('&', ' ').replace('#', ' ').replace(Regex(\"\\\\s+\"), \" \").trim()\n"
            "        val orderedResults = arrayOfNulls<List<CloudStreamSearchItem>>(providers.size)\n\n"
            "        coroutineScope {\n"
            "            providers.mapIndexed { index, api ->\n"
            "                async {\n"
            "                    apiGate.withPermit {\n"
            "                        val effectiveQuery = sanitizedQuery.ifBlank { query }\n"
            "                        runCatching {\n"
            "                            withTimeout(stageTimeout(api.searchTimeoutMs, DEFAULT_DISCOVERY_TIMEOUT_MS)) {\n"
            "                                api.search(effectiveQuery, 1)?.items.orEmpty()\n"
            "                            }\n"
            "                        }.onSuccess { items ->\n"
            "                            log.d {\n"
            "                                \"CloudStream search api=${api.name} query=$effectiveQuery returned=${items.size} \" +\n"
            "                                    \"sample=${items.take(3).joinToString { it.name }}\"\n"
            "                            }\n"
            "                            orderedResults[index] = items.map { it.toNuvioSearchItem(api) }\n"
            "                        }.onFailure { error ->\n"
            "                            synchronized(orderedResults) { lastError = error }\n"
            "                            log.w(error) { \"CloudStream search failed api=${api.name}\" }\n"
            "                        }\n"
            "                    }\n"
            "                }\n"
            "            }.awaitAll()\n"
            "        }\n\n"
            "        val merged = orderedResults.filterNotNull().flatten().distinctBy { it.data }\n"
            "        if (merged.isEmpty()) throw lastError ?: return@withContext emptyList()\n"
            "        merged\n"
            "    }",
            "CloudStreamPlatformRuntime getMainPage & ordered search",
        )
        changed |= _replace_once(
            runtime_kt,
            "        val response = withTimeout(effectiveTimeoutMs) {\n"
            "            api.load(route.data)\n"
            "        } ?: error(\"CloudStream provider returned no details\")\n",
            "        val fixedRouteData = api.fixUrl(route.data)\n"
            "        val response = withTimeout(effectiveTimeoutMs) {\n"
            "            api.load(fixedRouteData)\n"
            "        } ?: error(\"CloudStream provider returned no details\")\n",
            "CloudStreamPlatformRuntime fixUrl in load",
        )
        changed |= _replace_once(
            runtime_kt,
            "        private const val CLOUDSTREAM_API_CONCURRENCY = 4\n"
            "        private const val DEFAULT_DISCOVERY_TIMEOUT_MS = 30_000L\n"
            "        private const val DEFAULT_LOAD_TIMEOUT_MS = 120_000L\n"
            "        private const val DEFAULT_LINK_TIMEOUT_MS = 120_000L\n",
            "        private const val CLOUDSTREAM_API_CONCURRENCY = 4\n"
            "        private const val DEFAULT_MAIN_PAGE_SECTION_TIMEOUT_MS = 12_000L\n"
            "        private const val DEFAULT_DISCOVERY_TIMEOUT_MS = 18_000L\n"
            "        private const val DEFAULT_LOAD_TIMEOUT_MS = 25_000L\n"
            "        private const val DEFAULT_LINK_TIMEOUT_MS = 24_000L\n",
            "CloudStreamPlatformRuntime stage timeouts",
        )
        if changed:
            patched.append(str(runtime_kt.relative_to(root)))

    # 6. HomeScreen.kt & HomeRepository.kt: default CloudStream provider selection to "all"
    #    and auto-heal when a single selected bootstrap plugin (e.g. MegaRepo) yields 0 sections.
    home_screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/home/HomeScreen.kt"
    if home_screen.is_file():
        if _replace_once(
            home_screen,
            "    LaunchedEffect(runnableCloudStreamProviders, selectedCloudStreamProviderId) {\n"
            "        if (runnableCloudStreamProviders.isNotEmpty()) {\n"
            "            if (selectedCloudStreamProviderId == null) {\n"
            "                HomeRepository.setSelectedCloudStreamProvider(runnableCloudStreamProviders.first().metadata.id.value)\n"
            "            } else if (selectedCloudStreamProviderId != \"off\" &&\n"
            "                selectedCloudStreamProviderId != \"all\" &&\n"
            "                runnableCloudStreamProviders.none { it.metadata.id.value == selectedCloudStreamProviderId }\n"
            "            ) {\n"
            "                HomeRepository.setSelectedCloudStreamProvider(runnableCloudStreamProviders.first().metadata.id.value)\n"
            "            }\n"
            "        } else if (selectedCloudStreamProviderId != null && selectedCloudStreamProviderId != \"off\") {\n"
            "            HomeRepository.setSelectedCloudStreamProvider(null)\n"
            "        }\n"
            "    }\n",
            "    LaunchedEffect(runnableCloudStreamProviders, selectedCloudStreamProviderId) {\n"
            "        if (runnableCloudStreamProviders.isNotEmpty()) {\n"
            "            if (selectedCloudStreamProviderId == null) {\n"
            "                HomeRepository.setSelectedCloudStreamProvider(\"all\")\n"
            "            } else if (selectedCloudStreamProviderId != \"off\" &&\n"
            "                selectedCloudStreamProviderId != \"all\" &&\n"
            "                runnableCloudStreamProviders.none { it.metadata.id.value == selectedCloudStreamProviderId }\n"
            "            ) {\n"
            "                HomeRepository.setSelectedCloudStreamProvider(\"all\")\n"
            "            }\n"
            "        } else if (selectedCloudStreamProviderId != null && selectedCloudStreamProviderId != \"off\") {\n"
            "            HomeRepository.setSelectedCloudStreamProvider(null)\n"
            "        }\n"
            "    }\n",
            "HomeScreen default CloudStream selection to all",
        ):
            patched.append(str(home_screen.relative_to(root)))

    home_repo = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/home/HomeRepository.kt"
    if home_repo.is_file():
        changed = False
        changed |= _replace_once(
            home_repo,
            "        val effectiveSelectedProviderId = when (selectedProviderId) {\n"
            "            \"all\" -> \"all\"\n"
            "            \"off\" -> null\n"
            "            else -> selectedProviderId?.takeIf { id -> runnableCloudPlugins.any { it.metadata.id.value == id } }\n"
            "                ?: if (selectedProviderId == \"off\") null else runnableCloudPlugins.firstOrNull()?.metadata?.id?.value\n"
            "        }\n",
            "        val effectiveSelectedProviderId = when (selectedProviderId) {\n"
            "            \"all\" -> \"all\"\n"
            "            \"off\" -> null\n"
            "            else -> selectedProviderId?.takeIf { id -> runnableCloudPlugins.any { it.metadata.id.value == id } }\n"
            "                ?: if (runnableCloudPlugins.isNotEmpty()) \"all\" else null\n"
            "        }\n",
            "HomeRepository default CloudStream selection to all",
        )
        changed |= _replace_once(
            home_repo,
            "                launch {\n"
            "                    val cloudResult = loadCloudSections(cloudPlugins, requestKey)\n"
            "                    if (activeRequestKey == requestKey) {\n"
            "                        cachedCloudSections = cloudResult.sections\n"
            "                        cloudErrorMessage = cloudResult.errorMessage\n"
            "                        publishCurrentState(isLoading = true, requestKey = requestKey)\n"
            "                    }\n"
            "                }\n",
            "                launch {\n"
            "                    var cloudResult = loadCloudSections(cloudPlugins, requestKey)\n"
            "                    // Auto-heal when an earlier launch auto-selected a bootstrap/repo plugin\n"
            "                    // (such as MegaRepo) that has no catalogues while other extensions exist.\n"
            "                    if (cloudResult.sections.isEmpty() &&\n"
            "                        effectiveSelectedProviderId != null &&\n"
            "                        effectiveSelectedProviderId != \"all\" &&\n"
            "                        runnableCloudPlugins.size > 1 &&\n"
            "                        activeRequestKey == requestKey\n"
            "                    ) {\n"
            "                        _selectedCloudStreamProviderId.value = \"all\"\n"
            "                        HomeCatalogSettingsRepository.setCloudStreamProviderId(\"all\")\n"
            "                        cloudResult = loadCloudSections(runnableCloudPlugins, requestKey)\n"
            "                    }\n"
            "                    if (activeRequestKey == requestKey) {\n"
            "                        cachedCloudSections = cloudResult.sections\n"
            "                        cloudErrorMessage = cloudResult.errorMessage\n"
            "                        publishCurrentState(isLoading = true, requestKey = requestKey)\n"
            "                    }\n"
            "                }\n",
            "HomeRepository auto-heal empty single CloudStream selection",
        )
        if changed:
            patched.append(str(home_repo.relative_to(root)))

    # 7. StreamsScreen.kt, StreamsRepository.kt, and StreamFetchSupport.kt
    streams_screen = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamsScreen.kt"
    if streams_screen.is_file():
        changed = False
        changed |= _replace_once(
            streams_screen,
            "        StreamsRepository.load(\n"
            "            type = type,\n"
            "            videoId = videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            season = seasonNumber,\n"
            "            episode = episodeNumber,\n"
            "            manualSelection = manualSelection,\n"
            "        )\n",
            "        StreamsRepository.load(\n"
            "            type = type,\n"
            "            videoId = videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            parentMetaType = parentMetaType,\n"
            "            season = seasonNumber,\n"
            "            episode = episodeNumber,\n"
            "            manualSelection = manualSelection,\n"
            "            searchTitle = title,\n"
            "        )\n",
            "StreamsScreen load pass parentMetaType & searchTitle",
        )
        changed |= _replace_once(
            streams_screen,
            "        StreamsRepository.reload(\n"
            "            type = type,\n"
            "            videoId = videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            season = seasonNumber,\n"
            "            episode = episodeNumber,\n"
            "            manualSelection = manualSelection,\n"
            "        )\n",
            "        StreamsRepository.reload(\n"
            "            type = type,\n"
            "            videoId = videoId,\n"
            "            parentMetaId = parentMetaId,\n"
            "            parentMetaType = parentMetaType,\n"
            "            season = seasonNumber,\n"
            "            episode = episodeNumber,\n"
            "            manualSelection = manualSelection,\n"
            "            searchTitle = title,\n"
            "        )\n",
            "StreamsScreen reload pass parentMetaType & searchTitle",
        )
        if changed:
            patched.append(str(streams_screen.relative_to(root)))

    streams_repo = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamsRepository.kt"
    if streams_repo.is_file():
        if _replace_once(
            streams_repo,
            "private const val STREAM_PROVIDER_TIMEOUT_MS = 35_000L\n",
            "private const val STREAM_PROVIDER_TIMEOUT_MS = 48_000L\n",
            "StreamsRepository provider timeout 48s",
        ):
            patched.append(str(streams_repo.relative_to(root)))

    fetch_support = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamFetchSupport.kt"
    if fetch_support.is_file():
        changed = False
        changed |= _replace_once(
            fetch_support,
            "import kotlinx.coroutines.async\n",
            "import kotlinx.coroutines.async\n"
            "import kotlinx.coroutines.awaitAll\n"
            "import kotlinx.coroutines.coroutineScope\n"
            "import kotlinx.coroutines.sync.Mutex\n"
            "import kotlinx.coroutines.sync.withLock\n"
            "import kotlin.math.abs\n",
            "StreamFetchSupport concurrency & abs imports",
        )
        changed |= _replace_once(
            fetch_support,
            "private val cloudStreamFetchLog = Logger.withTag(\"CloudStreamFetch\")\n"
            "private val cloudStreamProviderScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)\n",
            "private val cloudStreamFetchLog = Logger.withTag(\"CloudStreamFetch\")\n"
            "private val cloudStreamProviderScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)\n"
            "private val cloudStreamCacheMutex = Mutex()\n"
            "private val cloudStreamSearchCache = LinkedHashMap<String, List<CloudStreamSearchItem>>()\n"
            "private val cloudStreamLoadCache = LinkedHashMap<String, CloudStreamLoadItem>()\n\n"
            "private suspend fun cachedCloudStreamSearch(\n"
            "    providerId: String,\n"
            "    query: String,\n"
            "): List<CloudStreamSearchItem> {\n"
            "    val key = \"$providerId::${query.trim().lowercase()}\"\n"
            "    cloudStreamCacheMutex.withLock {\n"
            "        cloudStreamSearchCache[key]?.let { return it }\n"
            "    }\n"
            "    val fresh = CloudStreamRepository.search(query, providerId)\n"
            "        .firstOrNull()\n"
            "        ?.getOrThrow()\n"
            "        .orEmpty()\n"
            "        .distinctBy { item -> item.type to item.data }\n"
            "    if (fresh.isNotEmpty()) {\n"
            "        cloudStreamCacheMutex.withLock {\n"
            "            if (cloudStreamSearchCache.size >= 64) {\n"
            "                cloudStreamSearchCache.keys.firstOrNull()?.let(cloudStreamSearchCache::remove)\n"
            "            }\n"
            "            cloudStreamSearchCache[key] = fresh\n"
            "        }\n"
            "    }\n"
            "    return fresh\n"
            "}\n\n"
            "private suspend fun cachedCloudStreamLoad(\n"
            "    providerId: String,\n"
            "    data: String,\n"
            "): CloudStreamLoadItem {\n"
            "    val key = \"$providerId::$data\"\n"
            "    cloudStreamCacheMutex.withLock {\n"
            "        cloudStreamLoadCache[key]?.let { return it }\n"
            "    }\n"
            "    val loaded = CloudStreamRepository.load(providerId, data).getOrThrow()\n"
            "    cloudStreamCacheMutex.withLock {\n"
            "        if (cloudStreamLoadCache.size >= 64) {\n"
            "            cloudStreamLoadCache.keys.firstOrNull()?.let(cloudStreamLoadCache::remove)\n"
            "        }\n"
            "        cloudStreamLoadCache[key] = loaded\n"
            "    }\n"
            "    return loaded\n"
            "}\n",
            "StreamFetchSupport search/load LRU cache",
        )
        changed |= _replace_once(
            fetch_support,
            "                val loaded = runCatchingUnlessCancelled {\n"
            "                    CloudStreamRepository.load(providerGroup.providerId, match.data).getOrThrow()\n"
            "                }.onFailure { error -> lastError = error }\n",
            "                val loaded = runCatchingUnlessCancelled {\n"
            "                    cachedCloudStreamLoad(providerGroup.providerId, match.data)\n"
            "                }.onFailure { error -> lastError = error }\n",
            "StreamFetchSupport use cachedCloudStreamLoad",
        )
        changed |= _replace_once(
            fetch_support,
            "                val searchResults = runCatchingUnlessCancelled {\n"
            "                    CloudStreamRepository.search(query, providerGroup.providerId)\n"
            "                        .firstOrNull()\n"
            "                        ?.getOrThrow()\n"
            "                        .orEmpty()\n"
            "                        .distinctBy { item -> item.type to item.data }\n"
            "                }.onFailure { error -> lastError = error }\n",
            "                val searchResults = runCatchingUnlessCancelled {\n"
            "                    cachedCloudStreamSearch(providerGroup.providerId, query)\n"
            "                }.onFailure { error -> lastError = error }\n",
            "StreamFetchSupport use cachedCloudStreamSearch",
        )
        changed |= _replace_once(
            fetch_support,
            "internal suspend fun cloudStreamSourcesToStreamItems(\n"
            "    providerId: String,\n"
            "    providerName: String,\n"
            "    sources: List<CloudStreamPlaybackSource>,\n"
            "): List<StreamItem> =\n"
            "    sources\n"
            "        .map { source ->\n"
            "            source.toStreamItem(\n"
            "                providerId = providerId,\n"
            "                providerName = providerName,\n"
            "            )\n"
            "        }\n"
            "        .flatMap { stream -> stream.expandCloudStreamHlsVariants() }\n",
            "internal suspend fun cloudStreamSourcesToStreamItems(\n"
            "    providerId: String,\n"
            "    providerName: String,\n"
            "    sources: List<CloudStreamPlaybackSource>,\n"
            "): List<StreamItem> = coroutineScope {\n"
            "    sources\n"
            "        .map { source ->\n"
            "            source.toStreamItem(\n"
            "                providerId = providerId,\n"
            "                providerName = providerName,\n"
            "            )\n"
            "        }\n"
            "        .map { stream ->\n"
            "            async {\n"
            "                withTimeoutOrNull(4_000L) { stream.expandCloudStreamHlsVariants() }\n"
            "                    ?: listOf(stream)\n"
            "            }\n"
            "        }\n"
            "        .awaitAll()\n"
            "        .flatten()\n",
            "StreamFetchSupport parallel bounded HLS variant expansion",
        )
        changed |= _replace_once(
            fetch_support,
            "        .distinctBy { stream ->\n"
            "            listOf(\n"
            "                stream.addonId,\n"
            "                stream.sourceName.orEmpty(),\n"
            "                stream.streamLabel,\n"
            "                stream.playableDirectUrl.orEmpty(),\n"
            "            )\n"
            "        }\n",
            "        .distinctBy { stream ->\n"
            "            listOf(\n"
            "                stream.addonId,\n"
            "                stream.sourceName.orEmpty(),\n"
            "                stream.streamLabel,\n"
            "                stream.playableDirectUrl.orEmpty(),\n"
            "            )\n"
            "        }\n"
            "}\n",
            "StreamFetchSupport close coroutineScope",
        )
        changed |= _replace_once(
            fetch_support,
            "private const val CLOUDSTREAM_PROVIDER_STREAM_TIMEOUT_MS = 120_000L\n"
            "private const val CLOUDSTREAM_SEARCH_CANDIDATE_LIMIT = 3\n",
            "private const val CLOUDSTREAM_PROVIDER_STREAM_TIMEOUT_MS = 44_000L\n"
            "private const val CLOUDSTREAM_SEARCH_CANDIDATE_LIMIT = 6\n",
            "StreamFetchSupport timeout 44s & candidate limit 6",
        )
        changed |= _replace_once(
            fetch_support,
            "internal fun List<CloudStreamSearchItem>.bestCloudStreamMatches(\n"
            "    request: CloudStreamSearchRequest,\n"
            "): List<CloudStreamSearchItem> {\n"
            "    val requestedType = normalizeCloudStreamNuvioType(request.type)\n"
            "    val typedCandidates = filter { item -> item.type.matchesCloudStreamType(requestedType) }\n"
            "    val candidates = typedCandidates.ifEmpty { this }\n"
            "    val requestedTitles = request.titleCandidates\n"
            "        .map { title -> title.normalizedCloudStreamSearchTitle() }\n"
            "        .filter { title -> title.isNotBlank() }\n"
            "        .distinct()\n"
            "    return candidates\n"
            "        .mapNotNull { item ->\n"
            "            requestedTitles\n"
            "                .mapIndexedNotNull { index, requestedTitle ->\n"
            "                    item.matchScore(requestedTitle, request.year)?.let { score ->\n"
            "                        score + if (index == 0) 5 else 0\n"
            "                    }\n"
            "                }\n"
            "                .maxOrNull()\n"
            "                ?.let { score -> item to score }\n"
            "        }\n"
            "        .sortedWith(\n"
            "            compareByDescending<Pair<CloudStreamSearchItem, Int>> { (_, score) -> score }\n"
            "                .thenBy { (item, _) -> item.name.length },\n"
            "        )\n"
            "        .map { (item, _) -> item }\n"
            "        .distinctBy { item -> item.data }\n"
            "        .take(CLOUDSTREAM_SEARCH_CANDIDATE_LIMIT)\n"
            "}\n\n"
            "private fun List<CloudStreamSearchItem>.providerRankedCloudStreamFallbacks(\n"
            "    request: CloudStreamSearchRequest,\n"
            "): List<CloudStreamSearchItem> {\n"
            "    val requestedType = normalizeCloudStreamNuvioType(request.type)\n"
            "    val typedCandidates = filter { item -> item.type.matchesCloudStreamType(requestedType) }\n"
            "    // A significant number of real CloudStream providers label every search card as\n"
            "    // Movie and only reveal TvSeries from load(url). This mirrors CloudStream itself:\n"
            "    // trust provider search ranking here, then validate the actual LoadResponse type.\n"
            "    val candidates = typedCandidates.ifEmpty { this }\n"
            "    return candidates\n"
            "        .filter { item ->\n"
            "            val candidateYear = item.year\n"
            "                ?: item.name.normalizedCloudStreamSearchTitle().trailingCloudStreamReleaseYear()\n"
            "            request.year == null || candidateYear == null || candidateYear == request.year\n"
            "        }\n"
            "        // Provider search endpoints already return relevance-ranked results. A localized\n"
            "        // title (for example \"Les Evades\") must not be discarded solely because it is\n"
            "        // different from the metadata title used for the query.\n"
            "        .distinctBy { item -> item.data }\n"
            "        .take(CLOUDSTREAM_SEARCH_CANDIDATE_LIMIT)\n"
            "}\n\n"
            "private fun CloudStreamSearchItem.matchScore(requestedTitle: String, requestedYear: Int?): Int? {\n"
            "    val candidateTitle = name.normalizedCloudStreamSearchTitle()\n"
            "    val requestedCanonical = requestedTitle.cloudStreamCanonicalTitle()\n"
            "    val candidateCanonical = candidateTitle.cloudStreamCanonicalTitle()\n"
            "    if (requestedCanonical.isBlank() || candidateCanonical.isBlank()) return null\n\n"
            "    val candidateYear = year ?: candidateTitle.trailingCloudStreamReleaseYear()\n"
            "    if (requestedYear != null && candidateYear != null && requestedYear != candidateYear) return null\n\n"
            "    val yearBonus = when {\n"
            "        requestedYear != null && candidateYear == requestedYear -> 25\n"
            "        candidateYear != null -> 1\n"
            "        else -> 0\n"
            "    }\n"
            "    return when {\n"
            "        candidateTitle == requestedTitle -> 100 + yearBonus\n"
            "        candidateCanonical == requestedCanonical -> 90 + yearBonus\n"
            "        else -> null\n"
            "    }\n"
            "}\n",
            "internal fun List<CloudStreamSearchItem>.bestCloudStreamMatches(\n"
            "    request: CloudStreamSearchRequest,\n"
            "): List<CloudStreamSearchItem> {\n"
            "    val requestedType = normalizeCloudStreamNuvioType(request.type)\n"
            "    // Never pre-discard Movie-tagged search cards before title scoring: multi-API\n"
            "    // packages like StreamPlay tag TMDB TV series search cards as TvType.Movie while\n"
            "    // sibling StreamPlayAnime cards use TvType.Anime, which previously caused all\n"
            "    // StreamPlay TV series matches to be filtered out.\n"
            "    val requestedTitles = request.titleCandidates\n"
            "        .map { title -> title.normalizedCloudStreamSearchTitle() }\n"
            "        .filter { title -> title.isNotBlank() }\n"
            "        .distinct()\n"
            "    return mapIndexedNotNull { originalIndex, item ->\n"
            "        requestedTitles\n"
            "            .mapIndexedNotNull { index, requestedTitle ->\n"
            "                item.matchScore(requestedTitle, request.year)?.let { score ->\n"
            "                    val typeBonus = if (item.type.matchesCloudStreamType(requestedType)) 4 else 0\n"
            "                    score + (if (index == 0) 5 else 0) + typeBonus\n"
            "                }\n"
            "            }\n"
            "            .maxOrNull()\n"
            "            ?.let { score -> Triple(item, score, originalIndex) }\n"
            "    }\n"
            "        .sortedWith(\n"
            "            compareByDescending<Triple<CloudStreamSearchItem, Int, Int>> { it.second }\n"
            "                .thenBy { it.third }\n"
            "                .thenBy { it.first.name.length },\n"
            "        )\n"
            "        .map { it.first }\n"
            "        .distinctBy { item -> item.data }\n"
            "        .take(CLOUDSTREAM_SEARCH_CANDIDATE_LIMIT)\n"
            "}\n\n"
            "private fun List<CloudStreamSearchItem>.providerRankedCloudStreamFallbacks(\n"
            "    request: CloudStreamSearchRequest,\n"
            "): List<CloudStreamSearchItem> {\n"
            "    return filter { item ->\n"
            "        val candidateYear = item.year\n"
            "            ?: item.name.normalizedCloudStreamSearchTitle().trailingCloudStreamReleaseYear()\n"
            "        request.year == null || candidateYear == null || abs(candidateYear - request.year) <= 1\n"
            "    }\n"
            "        .distinctBy { item -> item.data }\n"
            "        .take(CLOUDSTREAM_SEARCH_CANDIDATE_LIMIT)\n"
            "}\n\n"
            "private fun CloudStreamSearchItem.matchScore(requestedTitle: String, requestedYear: Int?): Int? {\n"
            "    val candidateTitle = name.normalizedCloudStreamSearchTitle()\n"
            "    val requestedCanonical = requestedTitle.cloudStreamCanonicalTitle()\n"
            "    val candidateCanonical = candidateTitle.cloudStreamCanonicalTitle()\n"
            "    if (requestedCanonical.isBlank() || candidateCanonical.isBlank()) return null\n\n"
            "    val candidateYear = year ?: candidateTitle.trailingCloudStreamReleaseYear()\n"
            "    if (requestedYear != null && candidateYear != null && abs(requestedYear - candidateYear) > 1) return null\n\n"
            "    val yearBonus = when {\n"
            "        requestedYear != null && candidateYear == requestedYear -> 25\n"
            "        requestedYear != null && candidateYear != null && abs(requestedYear - candidateYear) == 1 -> 12\n"
            "        candidateYear != null -> 1\n"
            "        else -> 0\n"
            "    }\n"
            "    return when {\n"
            "        candidateTitle == requestedTitle -> 100 + yearBonus\n"
            "        candidateCanonical == requestedCanonical -> 90 + yearBonus\n"
            "        else -> null\n"
            "    }\n"
            "}\n",
            "StreamFetchSupport multi-API TV series & year tolerance matching",
        )
        changed |= _replace_once(
            fetch_support,
            "    val requestedYear = request.year\n"
            "    val searchYear = searchItem.year ?: searchItem.name.normalizedCloudStreamSearchTitle().trailingCloudStreamReleaseYear()\n"
            "    val loadedYear = year ?: loadedTitle.trailingCloudStreamReleaseYear()\n"
            "    if (requestedYear != null) {\n"
            "        if (searchYear != null && searchYear != requestedYear) return false\n"
            "        if (loadedYear != null && loadedYear != requestedYear) return false\n"
            "        if (requestedType == \"movie\" && searchYear != requestedYear && loadedYear != requestedYear) return false\n"
            "    }\n",
            "    val requestedYear = request.year\n"
            "    val searchYear = searchItem.year ?: searchItem.name.normalizedCloudStreamSearchTitle().trailingCloudStreamReleaseYear()\n"
            "    val loadedYear = year ?: loadedTitle.trailingCloudStreamReleaseYear()\n"
            "    if (requestedYear != null) {\n"
            "        if (searchYear != null && abs(searchYear - requestedYear) > 1) return false\n"
            "        if (loadedYear != null && abs(loadedYear - requestedYear) > 1) return false\n"
            "    }\n",
            "StreamFetchSupport matchesCloudStreamRequest null/+-1 year fix",
        )
        if changed:
            patched.append(str(fetch_support.relative_to(root)))

    return patched


def _patch_batch_downloads_and_hls(root: Path) -> list[str]:
    """Fix Issues #4, #5, and #6:
      - CloudStream extensions in StreamSourceLoader & BatchDownloadCoordinator
      - Native HLS (.m3u8 / fMP4 / AES-128) offline downloads in AndroidDownloadTransfer
      - Source filter (All / Nuvio / CloudStream) + source badges + uncompressed UI in BatchDownloadDialog
    """
    patched: list[str] = []

    # 1. DownloadsRepository.kt: allow .m3u8 URLs and map .m3u8 -> .ts file extension
    dl_repo = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsRepository.kt"
    if dl_repo.is_file():
        changed = False
        changed |= _replace_once(
            dl_repo,
            "private fun String.fileExtensionFromUrl(): String {\n"
            "    val withoutQuery = substringBefore('?').substringBefore('#')\n"
            "    val suffix = withoutQuery.substringAfterLast('.', missingDelimiterValue = \"\")\n"
            "        .lowercase()\n"
            "        .trim()\n\n"
            "    return if (suffix.length in 2..5 && suffix.all { it.isLetterOrDigit() }) {\n"
            "        suffix\n"
            "    } else {\n"
            "        \"mp4\"\n"
            "    }\n"
            "}\n\n"
            "internal fun String.isSupportedDownloadUrl(): Boolean {\n"
            "    val normalized = trim().lowercase()\n"
            "    if (normalized.startsWith(\"magnet:\")) return false\n"
            "    if (normalized.endsWith(\".m3u8\") || normalized.contains(\".m3u8?\")) return false\n"
            "    if (normalized.endsWith(\".mpd\") || normalized.contains(\".mpd?\")) return false\n"
            "    if (normalized.endsWith(\".torrent\") || normalized.contains(\".torrent?\")) return false\n"
            "    return normalized.startsWith(\"http://\") || normalized.startsWith(\"https://\")\n"
            "}\n",
            "private fun String.fileExtensionFromUrl(): String {\n"
            "    val withoutQuery = substringBefore('?').substringBefore('#')\n"
            "    val lowerUrl = lowercase()\n"
            "    if (lowerUrl.contains(\".m3u8\") || lowerUrl.contains(\"/hls/\")) {\n"
            "        return \"ts\"\n"
            "    }\n"
            "    val suffix = withoutQuery.substringAfterLast('.', missingDelimiterValue = \"\")\n"
            "        .lowercase()\n"
            "        .trim()\n\n"
            "    return if (suffix in setOf(\"m3u8\", \"m3u\", \"txt\", \"php\", \"aspx\", \"jsp\")) {\n"
            "        \"ts\"\n"
            "    } else if (suffix.length in 2..5 && suffix.all { it.isLetterOrDigit() }) {\n"
            "        suffix\n"
            "    } else {\n"
            "        \"mp4\"\n"
            "    }\n"
            "}\n\n"
            "internal fun String.isSupportedDownloadUrl(): Boolean {\n"
            "    val normalized = trim().lowercase()\n"
            "    if (normalized.startsWith(\"magnet:\")) return false\n"
            "    if (normalized.endsWith(\".mpd\") || normalized.contains(\".mpd?\")) return false\n"
            "    if (normalized.endsWith(\".torrent\") || normalized.contains(\".torrent?\")) return false\n"
            "    return normalized.startsWith(\"http://\") || normalized.startsWith(\"https://\")\n"
            "}\n",
            "DownloadsRepository allow HLS .m3u8 download URLs",
        )
        if changed:
            patched.append(str(dl_repo.relative_to(root)))

    # 2. AndroidDownloadTransfer.kt: add full HLS (.m3u8 master/media, #EXT-X-MAP fMP4, AES-128) downloader
    dl_transfer = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/AndroidDownloadTransfer.kt"
    dl_transfer.write_text(
        r'''package com.nuvio.app.features.downloads

import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.nio.ByteBuffer
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import okhttp3.Call
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

internal val downloadHttpClient = OkHttpClient.Builder()
    .dns(com.nuvio.app.core.network.NuvioDns)
    .connectTimeout(60, TimeUnit.SECONDS)
    .readTimeout(60, TimeUnit.SECONDS)
    .writeTimeout(60, TimeUnit.SECONDS)
    .followRedirects(true)
    .followSslRedirects(true)
    .build()

internal class DownloadHttpException(val statusCode: Int) : IOException("Download failed: HTTP $statusCode")

internal suspend fun transferAndroidDownload(
    item: DownloadItem,
    sink: DownloadSink,
    validator: String?,
    client: OkHttpClient = downloadHttpClient,
    onHeaders: (totalBytes: Long?, validator: String?) -> Unit,
    onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,
): Unit = coroutineScope {
    val activeCall = AtomicReference<Call?>()
    val transfer = async(Dispatchers.IO) {
        try {
            require(File(item.fileName).name == item.fileName && item.fileName.isNotBlank())
            if (looksLikeHlsUrl(item.sourceUrl)) {
                transferHlsPlaylistDownload(item, sink, client, activeCall, onHeaders, onProgress)
                return@async
            }

            var offset = sink.length()
            var restarted = false

            while (true) {
                ensureActive()
                val request = buildDownloadRequest(item.sourceUrl, item.sourceHeaders, offset, validator)
                val call = client.newCall(request)
                activeCall.set(call)
                ensureActive()
                var switchToHlsText: Pair<String, String>? = null
                call.execute().use { response ->
                    if (response.code == 416 && offset > 0L && !restarted) {
                        offset = 0L
                        restarted = true
                        return@use
                    }
                    if (!response.isSuccessful) throw DownloadHttpException(response.code)
                    val contentType = response.header("Content-Type").orEmpty().lowercase()
                    val body = response.body ?: throw IOException("Download response is empty")

                    if (offset == 0L && (contentType.contains("mpegurl") || contentType.contains("m3u"))) {
                        val playlistText = body.string()
                        if (playlistText.trimStart().startsWith("#EXTM3U")) {
                            switchToHlsText = response.request.url.toString() to playlistText
                            return@use
                        }
                    }

                    val range = response.header("Content-Range")?.let(::parseDownloadContentRange)
                    val resumed = response.code == 206
                    if (resumed && (range == null || range.first != offset)) {
                        throw IOException("Server returned an invalid download range")
                    }
                    val startingBytes = if (resumed) offset else 0L
                    val contentLength = body.contentLength().takeIf { it >= 0L }
                    val totalBytes = range?.second ?: contentLength?.let { startingBytes + it }
                    val responseValidator = response.header("ETag")?.takeUnless { it.startsWith("W/") }
                        ?: response.header("Last-Modified")

                    body.byteStream().use { input ->
                        // Sniff disguised HLS playlists served as text/plain or application/octet-stream
                        val headBuffer = ByteArray(16)
                        var headLen = 0
                        if (startingBytes == 0L) {
                            while (headLen < headBuffer.size) {
                                val r = input.read(headBuffer, headLen, headBuffer.size - headLen)
                                if (r <= 0) break
                                headLen += r
                            }
                            val prefix = String(headBuffer, 0, headLen, Charsets.UTF_8).trimStart()
                            if (prefix.startsWith("#EXTM3U")) {
                                val out = ByteArrayOutputStream()
                                out.write(headBuffer, 0, headLen)
                                val buf = ByteArray(16 * 1024)
                                while (true) {
                                    ensureActive()
                                    val r = input.read(buf)
                                    if (r == -1) break
                                    out.write(buf, 0, r)
                                }
                                switchToHlsText = response.request.url.toString() to out.toString("UTF-8")
                                return@use
                            }
                        }

                        onHeaders(totalBytes, responseValidator)
                        var downloaded = startingBytes
                        onProgress(downloaded, totalBytes)
                        sink.open(append = resumed && offset > 0L).use { output ->
                            if (headLen > 0) {
                                output.write(headBuffer, 0, headLen)
                                downloaded += headLen
                                onProgress(downloaded, totalBytes)
                            }
                            val buffer = ByteArray(64 * 1024)
                            while (true) {
                                ensureActive()
                                val size = input.read(buffer)
                                if (size == -1) break
                                output.write(buffer, 0, size)
                                downloaded += size
                                onProgress(downloaded, totalBytes)
                            }
                            output.fd.sync()
                        }
                        ensureActive()
                        if (totalBytes != null && downloaded != totalBytes) {
                            throw IOException("Download ended before all bytes were received")
                        }
                    }
                    return@async
                }

                val hlsDetected = switchToHlsText
                if (hlsDetected != null) {
                    transferHlsPlaylistDownload(
                        item = item,
                        sink = sink,
                        client = client,
                        activeCall = activeCall,
                        onHeaders = onHeaders,
                        onProgress = onProgress,
                        initialPlaylistUrl = hlsDetected.first,
                        initialPlaylistBody = hlsDetected.second,
                    )
                    return@async
                }
            }
        } catch (error: Exception) {
            ensureActive()
            throw error
        }
    }
    try {
        transfer.await()
    } finally {
        activeCall.get()?.cancel()
    }
}

private fun looksLikeHlsUrl(url: String): Boolean {
    val lower = url.trim().lowercase()
    val path = lower.substringBefore('?').substringBefore('#')
    return path.endsWith(".m3u8") || ".m3u8/" in path || lower.contains(".m3u8?")
}

private fun buildDownloadRequest(
    url: String,
    headers: Map<String, String>,
    offset: Long = 0L,
    validator: String? = null,
    byteRange: Pair<Long, Long>? = null,
): Request = Request.Builder().url(url).apply {
    headers.forEach { (key, value) ->
        if (!key.equals("Range", true) && !key.equals("If-Range", true) &&
            !key.equals("Accept-Encoding", true)
        ) {
            header(key, value)
        }
    }
    header("Accept-Encoding", "identity")
    if (byteRange != null) {
        header("Range", "bytes=${byteRange.first}-${byteRange.second}")
    } else if (offset > 0L) {
        header("Range", "bytes=$offset-")
        validator?.let { header("If-Range", it) }
    }
}.build()

private data class HlsKeySpec(
    val method: String,
    val uri: String?,
    val iv: ByteArray?,
)

private data class HlsSegmentSpec(
    val url: String,
    val sequence: Long,
    val key: HlsKeySpec?,
    val byteRange: Pair<Long, Long>?,
)

private suspend fun transferHlsPlaylistDownload(
    item: DownloadItem,
    sink: DownloadSink,
    client: OkHttpClient,
    activeCall: AtomicReference<Call?>,
    onHeaders: (totalBytes: Long?, validator: String?) -> Unit,
    onProgress: (downloadedBytes: Long, totalBytes: Long?) -> Unit,
    initialPlaylistUrl: String? = null,
    initialPlaylistBody: String? = null,
) {
    suspend fun fetchText(url: String): Pair<String, String> {
        val call = client.newCall(buildDownloadRequest(url, item.sourceHeaders))
        activeCall.set(call)
        call.execute().use { response ->
            if (!response.isSuccessful) throw DownloadHttpException(response.code)
            val body = response.body?.string() ?: throw IOException("Empty HLS playlist")
            return response.request.url.toString() to body
        }
    }

    suspend fun fetchBytesWithRetry(url: String, byteRange: Pair<Long, Long>? = null): ByteArray {
        var attempt = 0
        while (true) {
            kotlinx.coroutines.currentCoroutineContext().ensureActive()
            try {
                val call = client.newCall(buildDownloadRequest(url, item.sourceHeaders, byteRange = byteRange))
                activeCall.set(call)
                call.execute().use { response ->
                    if (!response.isSuccessful) throw DownloadHttpException(response.code)
                    return response.body?.bytes() ?: throw IOException("Empty HLS segment")
                }
            } catch (err: Exception) {
                kotlinx.coroutines.currentCoroutineContext().ensureActive()
                attempt++
                if (attempt >= 3) throw err
                delay(600L * attempt)
            }
        }
    }

    var (playlistUrl, playlistText) = if (initialPlaylistUrl != null && initialPlaylistBody != null) {
        initialPlaylistUrl to initialPlaylistBody
    } else {
        fetchText(item.sourceUrl)
    }

    // Resolve master playlist (#EXT-X-STREAM-INF) to best variant media playlist
    if (playlistText.contains("#EXT-X-STREAM-INF")) {
        val variantUrl = selectBestHlsVariant(playlistUrl, playlistText)
            ?: throw IOException("No playable variant found in HLS master playlist")
        val resolved = fetchText(variantUrl)
        playlistUrl = resolved.first
        playlistText = resolved.second
    }

    val (initSegment, segments) = parseHlsMediaPlaylist(playlistUrl, playlistText)
    if (segments.isEmpty()) {
        throw IOException("HLS media playlist contained no segments")
    }

    val keyCache = HashMap<String, ByteArray>()
    suspend fun decryptIfNeeded(raw: ByteArray, segment: HlsSegmentSpec): ByteArray {
        val keySpec = segment.key ?: return raw
        if (keySpec.method.equals("NONE", ignoreCase = true) || keySpec.uri.isNullOrBlank()) {
            return raw
        }
        if (!keySpec.method.equals("AES-128", ignoreCase = true)) {
            throw IOException("Unsupported HLS encryption: ${keySpec.method}")
        }
        val keyBytes = keyCache.getOrPut(keySpec.uri) {
            fetchBytesWithRetry(keySpec.uri)
        }
        val ivBytes = keySpec.iv ?: ByteBuffer.allocate(16).putLong(8, segment.sequence).array()
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(keyBytes, "AES"), IvParameterSpec(ivBytes))
        return cipher.doFinal(raw)
    }

    onHeaders(null, null)
    var downloadedBytes = 0L
    onProgress(0L, null)

    sink.open(append = false).use { output ->
        if (initSegment != null) {
            val initRaw = fetchBytesWithRetry(initSegment.url, initSegment.byteRange)
            val initPlain = decryptIfNeeded(initRaw, initSegment)
            output.write(initPlain)
            downloadedBytes += initPlain.size
            onProgress(downloadedBytes, null)
        }

        val totalCount = segments.size
        segments.forEachIndexed { idx, segment ->
            kotlinx.coroutines.currentCoroutineContext().ensureActive()
            val rawBytes = fetchBytesWithRetry(segment.url, segment.byteRange)
            val clearBytes = decryptIfNeeded(rawBytes, segment)
            output.write(clearBytes)
            downloadedBytes += clearBytes.size
            val completed = idx + 1
            val estimatedTotal = if (completed >= totalCount) {
                downloadedBytes
            } else {
                ((downloadedBytes.toDouble() * totalCount) / completed).toLong().coerceAtLeast(downloadedBytes + 1L)
            }
            onHeaders(estimatedTotal, null)
            onProgress(downloadedBytes, estimatedTotal)
        }
        output.fd.sync()
    }
    onHeaders(downloadedBytes, null)
    onProgress(downloadedBytes, downloadedBytes)
}

private fun resolveRelativeHlsUrl(baseUrl: String, ref: String): String {
    val trimmed = ref.trim()
    if (trimmed.startsWith("http://", true) || trimmed.startsWith("https://", true)) return trimmed
    return baseUrl.toHttpUrlOrNull()?.resolve(trimmed)?.toString()
        ?: runCatching { java.net.URI(baseUrl).resolve(trimmed).toString() }.getOrDefault(trimmed)
}

private fun selectBestHlsVariant(baseUrl: String, masterText: String): String? {
    data class Variant(val url: String, val height: Int, val bandwidth: Long)
    val lines = masterText.lines().map(String::trim)
    val variants = mutableListOf<Variant>()
    var pendingInfo: String? = null
    for (line in lines) {
        if (line.isEmpty()) continue
        if (line.startsWith("#EXT-X-STREAM-INF:", ignoreCase = true)) {
            pendingInfo = line.substringAfter(':')
        } else if (!line.startsWith("#") && pendingInfo != null) {
            val attrs = pendingInfo
            pendingInfo = null
            val height = Regex("RESOLUTION=\\d+x(\\d+)", RegexOption.IGNORE_CASE)
                .find(attrs)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: 0
            val bw = Regex("BANDWIDTH=(\\d+)", RegexOption.IGNORE_CASE)
                .find(attrs)?.groupValues?.getOrNull(1)?.toLongOrNull() ?: 0L
            variants += Variant(resolveRelativeHlsUrl(baseUrl, line), height, bw)
        }
    }
    val preferredMax = DownloadsSettingsRepository.preferredResolution.value.resolution
    val underCap = variants.filter { it.height in 1..preferredMax }
    val chosen = underCap.maxWithOrNull(compareBy<Variant> { it.height }.thenBy { it.bandwidth })
        ?: variants.maxWithOrNull(compareBy<Variant> { it.height }.thenBy { it.bandwidth })
    return chosen?.url
}

private fun parseHlsMediaPlaylist(
    baseUrl: String,
    mediaText: String,
): Pair<HlsSegmentSpec?, List<HlsSegmentSpec>> {
    var mediaSequence = 0L
    var currentKey: HlsKeySpec? = null
    var initSegment: HlsSegmentSpec? = null
    var pendingByteRange: Pair<Long, Long>? = null
    var lastRangeEnd = 0L
    val segments = mutableListOf<HlsSegmentSpec>()

    fun parseAttr(line: String, name: String): String? {
        val quoted = Regex("$name=\"([^\"]*)\"", RegexOption.IGNORE_CASE).find(line)?.groupValues?.getOrNull(1)
        if (quoted != null) return quoted
        return Regex("$name=([^,\\s]+)", RegexOption.IGNORE_CASE).find(line)?.groupValues?.getOrNull(1)
    }

    fun parseByteRangeSpec(spec: String?): Pair<Long, Long>? {
        if (spec.isNullOrBlank()) return null
        val len = spec.substringBefore('@').toLongOrNull() ?: return null
        val start = if ('@' in spec) {
            spec.substringAfter('@').toLongOrNull() ?: lastRangeEnd
        } else {
            lastRangeEnd
        }
        val end = start + len - 1L
        lastRangeEnd = end + 1L
        return start to end
    }

    for (rawLine in mediaText.lines()) {
        val line = rawLine.trim()
        if (line.isEmpty()) continue
        when {
            line.startsWith("#EXT-X-MEDIA-SEQUENCE:", true) -> {
                mediaSequence = line.substringAfter(':').trim().toLongOrNull() ?: 0L
            }
            line.startsWith("#EXT-X-KEY:", true) -> {
                val method = parseAttr(line, "METHOD") ?: "NONE"
                val uri = parseAttr(line, "URI")?.let { resolveRelativeHlsUrl(baseUrl, it) }
                val ivHex = parseAttr(line, "IV")?.removePrefix("0x")?.removePrefix("0X")
                val iv = ivHex?.takeIf { it.length == 32 }?.chunked(2)
                    ?.mapNotNull { it.toIntOrNull(16)?.toByte() }
                    ?.takeIf { it.size == 16 }
                    ?.toByteArray()
                currentKey = HlsKeySpec(method = method, uri = uri, iv = iv)
            }
            line.startsWith("#EXT-X-MAP:", true) -> {
                val mapUri = parseAttr(line, "URI")?.let { resolveRelativeHlsUrl(baseUrl, it) }
                val mapRange = parseByteRangeSpec(parseAttr(line, "BYTERANGE"))
                if (mapUri != null) {
                    initSegment = HlsSegmentSpec(
                        url = mapUri,
                        sequence = mediaSequence,
                        key = currentKey,
                        byteRange = mapRange,
                    )
                }
            }
            line.startsWith("#EXT-X-BYTERANGE:", true) -> {
                pendingByteRange = parseByteRangeSpec(line.substringAfter(':').trim())
            }
            !line.startsWith("#") -> {
                val segIndex = mediaSequence + segments.size
                segments += HlsSegmentSpec(
                    url = resolveRelativeHlsUrl(baseUrl, line),
                    sequence = segIndex,
                    key = currentKey,
                    byteRange = pendingByteRange,
                )
                pendingByteRange = null
            }
        }
    }
    return initSegment to segments
}

internal fun parseDownloadContentRange(value: String): Pair<Long, Long?>? {
    val match = Regex("bytes (\\d+)-(\\d+)/(\\d+|\\*)").matchEntire(value.trim()) ?: return null
    val start = match.groupValues[1].toLongOrNull() ?: return null
    val end = match.groupValues[2].toLongOrNull() ?: return null
    val total = match.groupValues[3].toLongOrNull()
    if (end < start || (total != null && end >= total)) return null
    return start to total
}
''',
        encoding="utf-8",
    )
    patched.append(str(dl_transfer.relative_to(root)))

    # 3. StreamSourceLoader.kt: include CloudStream extensions & direct CloudStream routes in loadStreams()
    loader_kt = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/streams/StreamSourceLoader.kt"
    if loader_kt.is_file():
        changed = False
        changed |= _replace_once(
            loader_kt,
            "import com.nuvio.app.features.addons.fetchAddonResponseText\n",
            "import com.nuvio.app.features.addons.fetchAddonResponseText\n"
            "import com.nuvio.app.features.cloudstream.CloudStreamRepository\n"
            "import com.nuvio.app.features.cloudstream.parseCloudStreamRouteId\n"
            "import com.nuvio.app.features.details.MetaDetails\n",
            "StreamSourceLoader CloudStream & MetaDetails imports",
        )
        changed |= _replace_once(
            loader_kt,
            "    suspend fun loadStreams(\n"
            "        type: String,\n"
            "        videoId: String,\n"
            "        season: Int?,\n"
            "        episode: Int?,\n"
            "        embeddedStreams: List<StreamItem>,\n"
            "        timeoutMs: Long,\n"
            "    ): List<StreamItem> {\n",
            "    suspend fun loadStreams(\n"
            "        type: String,\n"
            "        videoId: String,\n"
            "        season: Int?,\n"
            "        episode: Int?,\n"
            "        embeddedStreams: List<StreamItem>,\n"
            "        timeoutMs: Long,\n"
            "        meta: MetaDetails? = null,\n"
            "    ): List<StreamItem> {\n",
            "StreamSourceLoader loadStreams meta param",
        )
        changed |= _replace_once(
            loader_kt,
            "        val targets = resolveTargets(type = type, videoId = videoId, season = season, episode = episode)\n"
            "        val sources =\n"
            "            targets.streamAddons.map { addon ->\n"
            "                StreamSource(addon.addonName, addon.addonId) {\n"
            "                    val group = fetchAddonGroup(addon, type, videoId, forceRefresh = false)\n"
            "                    checkDebridCache(group, targets.streamAddonIds)\n"
            "                }\n"
            "            } + targets.pluginProviderGroups.map { providerGroup ->\n"
            "                StreamSource(providerGroup.addonName, providerGroup.addonId) {\n"
            "                    loadPluginProviderGroup(providerGroup, type, videoId, season, episode)\n"
            "                }\n"
            "            } + targets.serverSources.map { source ->\n"
            "                StreamSource(source.addonName, source.addonId) { source.load() }\n"
            "            }\n",
            "        val targets = resolveTargets(type = type, videoId = videoId, season = season, episode = episode)\n"
            "        val directCloudRoute = parseCloudStreamRouteId(videoId)\n"
            "            ?: meta?.id?.takeIf { type.equals(\"movie\", ignoreCase = true) }?.let(::parseCloudStreamRouteId)\n"
            "        val cloudStreamSearchRequest = if (AppFeaturePolicy.pluginsEnabled) {\n"
            "            val fallbackReq = buildCloudStreamSearchRequest(\n"
            "                type = type,\n"
            "                videoId = videoId,\n"
            "                parentMetaId = meta?.id,\n"
            "                parentMetaType = meta?.type ?: type,\n"
            "                season = season,\n"
            "                episode = episode,\n"
            "                searchTitle = meta?.name,\n"
            "            )\n"
            "            if (fallbackReq != null) {\n"
            "                fallbackReq.copy(\n"
            "                    year = fallbackReq.year ?: meta?.releaseInfo.cloudStreamReleaseYear(),\n"
            "                    genres = fallbackReq.genres.ifEmpty { meta?.genres.orEmpty() },\n"
            "                )\n"
            "            } else if (meta != null && meta.name.isNotBlank()) {\n"
            "                CloudStreamSearchRequest(\n"
            "                    title = meta.name,\n"
            "                    type = type,\n"
            "                    year = meta.releaseInfo.cloudStreamReleaseYear(),\n"
            "                    season = season,\n"
            "                    episode = episode,\n"
            "                    episodeTitle = meta.videos.firstOrNull {\n"
            "                        (season == null || it.season == season) && (episode == null || it.episode == episode)\n"
            "                    }?.title,\n"
            "                    externalId = sequenceOf(videoId, meta.id)\n"
            "                        .map(String::trim)\n"
            "                        .firstOrNull { it.matches(Regex(\"^tt\\\\d{5,12}$\", RegexOption.IGNORE_CASE)) },\n"
            "                    genres = meta.genres,\n"
            "                )\n"
            "            } else {\n"
            "                null\n"
            "            }\n"
            "        } else {\n"
            "            null\n"
            "        }\n"
            "        val cloudStreamGroups = if (AppFeaturePolicy.pluginsEnabled) {\n"
            "            cloudStreamProviderGroupsForRequest(type = type, request = cloudStreamSearchRequest)\n"
            "        } else {\n"
            "            emptyList()\n"
            "        }\n"
            "        val directCloudSources = if (directCloudRoute != null && AppFeaturePolicy.pluginsEnabled) {\n"
            "            CloudStreamRepository.initialize()\n"
            "            val pluginItem = CloudStreamRepository.uiState.value.plugins\n"
            "                .firstOrNull { it.metadata.id.value == directCloudRoute.providerId }\n"
            "            val directName = pluginItem?.metadata?.name ?: \"CloudStream\"\n"
            "            val directAddonId = cloudStreamAddonId(directCloudRoute.providerId)\n"
            "            listOf(\n"
            "                StreamSource(directName, directAddonId) {\n"
            "                    val rawSources = CloudStreamRepository.loadLinks(directCloudRoute.providerId, directCloudRoute.data)\n"
            "                        .getOrThrow()\n"
            "                    val items = cloudStreamSourcesToStreamItems(\n"
            "                        providerId = directCloudRoute.providerId,\n"
            "                        providerName = directName,\n"
            "                        sources = rawSources,\n"
            "                    )\n"
            "                    AddonStreamGroup(\n"
            "                        addonName = directName,\n"
            "                        addonId = directAddonId,\n"
            "                        streams = items.sortedForGroupedDisplay(),\n"
            "                        isLoading = false,\n"
            "                    )\n"
            "                },\n"
            "            )\n"
            "        } else {\n"
            "            emptyList()\n"
            "        }\n"
            "        val sources = directCloudSources +\n"
            "            targets.streamAddons.map { addon ->\n"
            "                StreamSource(addon.addonName, addon.addonId) {\n"
            "                    val group = fetchAddonGroup(addon, type, videoId, forceRefresh = false)\n"
            "                    checkDebridCache(group, targets.streamAddonIds)\n"
            "                }\n"
            "            } + targets.pluginProviderGroups.map { providerGroup ->\n"
            "                StreamSource(providerGroup.addonName, providerGroup.addonId) {\n"
            "                    loadPluginProviderGroup(providerGroup, type, videoId, season, episode)\n"
            "                }\n"
            "            } + cloudStreamGroups\n"
            "                .filterNot { it.providerId == directCloudRoute?.providerId }\n"
            "                .map { csGroup ->\n"
            "                    StreamSource(csGroup.addonName, csGroup.addonId) {\n"
            "                        resolveCloudStreamProviderStreams(csGroup, cloudStreamSearchRequest)\n"
            "                    }\n"
            "                } + targets.serverSources.map { source ->\n"
            "                StreamSource(source.addonName, source.addonId) { source.load() }\n"
            "            }\n",
            "StreamSourceLoader include CloudStream sources",
        )
        if changed:
            patched.append(str(loader_kt.relative_to(root)))

    # 4. BatchDownloadCoordinator.kt: add BatchSourceFilter (All, Nuvio, CloudStream), pass meta, 48s timeout
    batch_coord = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/BatchDownloadCoordinator.kt"
    if batch_coord.is_file():
        changed = False
        changed |= _replace_once(
            batch_coord,
            "enum class EpisodePlanStatus {\n"
            "    AlreadyDownloaded,\n"
            "    AlreadyInProgress,\n"
            "    Loading,\n"
            "    Ready,\n"
            "    NoSourceFound,\n"
            "}\n",
            "enum class BatchSourceFilter {\n"
            "    All,\n"
            "    Nuvio,\n"
            "    CloudStream,\n"
            "}\n\n"
            "fun StreamItem.isCloudStreamBatchSource(): Boolean =\n"
            "    addonId?.startsWith(\"cloudstream:\", ignoreCase = true) == true\n\n"
            "fun StreamItem.matchesBatchSourceFilter(filter: BatchSourceFilter): Boolean = when (filter) {\n"
            "    BatchSourceFilter.All -> true\n"
            "    BatchSourceFilter.Nuvio -> !isCloudStreamBatchSource()\n"
            "    BatchSourceFilter.CloudStream -> isCloudStreamBatchSource()\n"
            "}\n\n"
            "enum class EpisodePlanStatus {\n"
            "    AlreadyDownloaded,\n"
            "    AlreadyInProgress,\n"
            "    Loading,\n"
            "    Ready,\n"
            "    NoSourceFound,\n"
            "}\n",
            "BatchDownloadCoordinator BatchSourceFilter helpers",
        )
        changed |= _replace_once(
            batch_coord,
            "    val seasonPlans: Map<Int, PlannedSeasonEpisodes> = emptyMap(),\n"
            "    val isSingleTitle: Boolean = false,\n"
            ") {\n",
            "    val seasonPlans: Map<Int, PlannedSeasonEpisodes> = emptyMap(),\n"
            "    val isSingleTitle: Boolean = false,\n"
            "    val sourceFilter: BatchSourceFilter = BatchSourceFilter.All,\n"
            ") {\n",
            "BatchDownloadPlan sourceFilter field",
        )
        changed |= _replace_once(
            batch_coord,
            "    private const val SOURCE_LOAD_PARALLELISM = 2\n"
            "    private const val SOURCE_LOAD_TIMEOUT_MS = 30_000L\n",
            "    private const val SOURCE_LOAD_PARALLELISM = 2\n"
            "    private const val SOURCE_LOAD_TIMEOUT_MS = 48_000L\n",
            "BatchDownloadCoordinator timeout 48s",
        )
        changed |= _replace_once(
            batch_coord,
            "                                StreamSourceLoader.loadStreams(\n"
            "                                    type = plan.meta.type,\n"
            "                                    videoId = target.streamVideoId,\n"
            "                                    season = target.season,\n"
            "                                    episode = target.episode,\n"
            "                                    embeddedStreams = plan.meta.findEmbeddedStreams(target.streamVideoId),\n"
            "                                    timeoutMs = SOURCE_LOAD_TIMEOUT_MS,\n"
            "                                )\n"
            "                            }.getOrElse { emptyList() }\n"
            "                            val selection = StreamSourcePrefillSelector.selectForBatch(streams, preferredResolution)\n\n"
            "                            updateEpisode(plan.meta.id, season, episode) { item ->\n"
            "                                if (item.status == EpisodePlanStatus.AlreadyDownloaded) item\n"
            "                                else if (selection == null) {\n"
            "                                    item.copy(allAvailableStreams = streams, status = EpisodePlanStatus.NoSourceFound)\n"
            "                                } else {\n"
            "                                    item.withSelectedStream(selection.stream, selection.facts, selection.sizeBytes)\n"
            "                                        .copy(allAvailableStreams = streams)\n"
            "                                }\n"
            "                            }\n",
            "                                StreamSourceLoader.loadStreams(\n"
            "                                    type = plan.meta.type,\n"
            "                                    videoId = target.streamVideoId,\n"
            "                                    season = target.season,\n"
            "                                    episode = target.episode,\n"
            "                                    embeddedStreams = plan.meta.findEmbeddedStreams(target.streamVideoId),\n"
            "                                    timeoutMs = SOURCE_LOAD_TIMEOUT_MS,\n"
            "                                    meta = plan.meta,\n"
            "                                )\n"
            "                            }.getOrElse { emptyList() }\n"
            "                            val activeFilter = _activePlan.value?.sourceFilter ?: BatchSourceFilter.All\n"
            "                            val filteredStreams = streams.filter { it.matchesBatchSourceFilter(activeFilter) }\n"
            "                            val selection = StreamSourcePrefillSelector.selectForBatch(filteredStreams, preferredResolution)\n\n"
            "                            updateEpisode(plan.meta.id, season, episode) { item ->\n"
            "                                if (item.status == EpisodePlanStatus.AlreadyDownloaded) item\n"
            "                                else if (selection == null) {\n"
            "                                    item.copy(\n"
            "                                        streamCandidate = null,\n"
            "                                        resolutionLabel = null,\n"
            "                                        sizeBytes = null,\n"
            "                                        allAvailableStreams = streams,\n"
            "                                        status = EpisodePlanStatus.NoSourceFound,\n"
            "                                    )\n"
            "                                } else {\n"
            "                                    item.withSelectedStream(selection.stream, selection.facts, selection.sizeBytes)\n"
            "                                        .copy(allAvailableStreams = streams)\n"
            "                                }\n"
            "                            }\n",
            "BatchDownloadCoordinator pass meta & apply sourceFilter",
        )
        changed |= _replace_once(
            batch_coord,
            "    fun overrideEpisodeStream(season: Int, episode: MetaVideo, stream: StreamItem) {\n",
            "    fun setSourceFilter(filter: BatchSourceFilter) {\n"
            "        val preferredResolution = DownloadsSettingsRepository.preferredResolution.value\n"
            "        _activePlan.update { current ->\n"
            "            if (current == null || current.sourceFilter == filter) return@update current\n"
            "            val updatedPlans = current.seasonPlans.mapValues { (_, seasonPlan) ->\n"
            "                seasonPlan.copy(\n"
            "                    episodes = seasonPlan.episodes.map { item ->\n"
            "                        if (item.status == EpisodePlanStatus.AlreadyDownloaded ||\n"
            "                            item.status == EpisodePlanStatus.AlreadyInProgress ||\n"
            "                            item.status == EpisodePlanStatus.Loading\n"
            "                        ) {\n"
            "                            item\n"
            "                        } else {\n"
            "                            val filtered = item.allAvailableStreams.filter { it.matchesBatchSourceFilter(filter) }\n"
            "                            val selection = StreamSourcePrefillSelector.selectForBatch(filtered, preferredResolution)\n"
            "                            if (selection == null) {\n"
            "                                item.copy(\n"
            "                                    streamCandidate = null,\n"
            "                                    resolutionLabel = null,\n"
            "                                    sizeBytes = null,\n"
            "                                    status = EpisodePlanStatus.NoSourceFound,\n"
            "                                )\n"
            "                            } else {\n"
            "                                item.withSelectedStream(selection.stream, selection.facts, selection.sizeBytes)\n"
            "                            }\n"
            "                        }\n"
            "                    },\n"
            "                )\n"
            "            }\n"
            "            current.copy(sourceFilter = filter, seasonPlans = updatedPlans)\n"
            "        }\n"
            "    }\n\n"
            "    fun overrideEpisodeStream(season: Int, episode: MetaVideo, stream: StreamItem) {\n",
            "BatchDownloadCoordinator setSourceFilter",
        )
        if changed:
            patched.append(str(batch_coord.relative_to(root)))

    # 5. BatchDownloadDialog.kt: uncompressed wide layout + Nuvio vs CloudStream badges & filter bar
    batch_dialog = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/details/components/BatchDownloadDialog.kt"
    batch_dialog.write_text(
        """package com.nuvio.app.features.details.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.app.core.ui.DialogButton
import com.nuvio.app.core.ui.DialogButtonStyle
import com.nuvio.app.core.ui.DialogButtons
import com.nuvio.app.core.ui.DialogSurface
import com.nuvio.app.features.debrid.DebridStreamMetadata
import com.nuvio.app.features.debrid.DebridStreamPreferences
import com.nuvio.app.features.details.MetaVideo
import com.nuvio.app.features.details.seasonLabel
import com.nuvio.app.features.downloads.BatchDialogStep
import com.nuvio.app.features.downloads.BatchDownloadCoordinator
import com.nuvio.app.features.downloads.BatchDownloadPlan
import com.nuvio.app.features.downloads.BatchSourceFilter
import com.nuvio.app.features.downloads.DownloadsRepository
import com.nuvio.app.features.downloads.EpisodePlanStatus
import com.nuvio.app.features.downloads.PlannedEpisodeItem
import com.nuvio.app.features.downloads.batchKey
import com.nuvio.app.features.downloads.formatBytes
import com.nuvio.app.features.downloads.isBatchEpisodeDownloaded
import com.nuvio.app.features.downloads.isBatchEpisodeUnavailable
import com.nuvio.app.features.downloads.isCloudStreamBatchSource
import com.nuvio.app.features.downloads.isDownloadableDirectUrl
import com.nuvio.app.features.downloads.localizedEpisodeLabel
import com.nuvio.app.features.downloads.matchesBatchSourceFilter
import com.nuvio.app.features.downloads.qualityBadge
import com.nuvio.app.features.streams.StreamItem
import com.nuvio.app.features.streams.StreamSourcePrefillSelector
import com.nuvio.app.features.streams.isResolverDependent
import nuvio.composeapp.generated.resources.*
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource

private val WideBatchDialogProperties = DialogProperties(usePlatformDefaultWidth = false)

@Composable
fun BatchDownloadDialog(
    plan: BatchDownloadPlan,
    isEpisodeWatched: (MetaVideo) -> Boolean = { false },
    onDismissRequest: () -> Unit,
    onConfirm: () -> Unit,
) {
    var overrideTargetItem by remember { mutableStateOf<PlannedEpisodeItem?>(null) }

    when (val step = plan.step) {
        is BatchDialogStep.EpisodeSelection -> {
            EpisodeSelectionDialog(
                plan = plan,
                isEpisodeWatched = isEpisodeWatched,
                onDismissRequest = onDismissRequest,
            )
        }
        is BatchDialogStep.SourceSelection -> {
            SourceSelectionDialog(
                plan = plan,
                seasonIndex = step.seasonIndex,
                onDismissRequest = onDismissRequest,
                onConfirm = onConfirm,
                onOverrideClicked = { overrideTargetItem = it },
            )
        }
    }

    val overrideItem = overrideTargetItem
    if (overrideItem != null) {
        val currentSeason = when (val step = plan.step) {
            is BatchDialogStep.SourceSelection -> plan.seasonsToSource[step.seasonIndex]
            else -> plan.visibleSeason
        }
        StreamOverrideDialog(
            target = overrideItem,
            initialFilter = plan.sourceFilter,
            onSelect = { stream ->
                BatchDownloadCoordinator.overrideEpisodeStream(
                    season = currentSeason,
                    episode = overrideItem.episode,
                    stream = stream,
                )
                overrideTargetItem = null
            },
            onDismiss = { overrideTargetItem = null },
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EpisodeSelectionDialog(
    plan: BatchDownloadPlan,
    isEpisodeWatched: (MetaVideo) -> Boolean,
    onDismissRequest: () -> Unit,
) {
    DialogSurface(
        onDismissRequest = onDismissRequest,
        modifier = Modifier.fillMaxWidth(0.94f),
        title = plan.meta.name,
        properties = WideBatchDialogProperties,
    ) {
        val downloadsUiState by remember {
            DownloadsRepository.ensureLoaded()
            DownloadsRepository.uiState
        }.collectAsStateWithLifecycle()
        val currentDownloads = downloadsUiState.items

        fun isUnavailable(episode: MetaVideo, season: Int): Boolean =
            isBatchEpisodeUnavailable(currentDownloads, plan.meta.id, episode, season)

        fun isDownloaded(episode: MetaVideo, season: Int): Boolean =
            isBatchEpisodeDownloaded(currentDownloads, plan.meta.id, episode, season)

        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (plan.availableSeasons.size > 1) {
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(plan.availableSeasons) { seasonNumber ->
                        val sLabel = seasonLabel(seasonNumber)
                        val countInSeason = plan.episodesBySeason[seasonNumber].orEmpty().count { episode ->
                            episode.batchKey(seasonNumber) in plan.selectedEpisodeKeys
                        }
                        val chipText = if (countInSeason > 0) {
                            stringResource(Res.string.season_download_season_count, sLabel, countInSeason)
                        } else sLabel
                        val isSelectedSeason = plan.visibleSeason == seasonNumber

                        FilterChip(
                            selected = isSelectedSeason,
                            onClick = { BatchDownloadCoordinator.showSeason(seasonNumber) },
                            label = { Text(chipText, style = MaterialTheme.typography.labelMedium, maxLines = 1) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                            ),
                        )
                    }
                }
            }
            val currentSeasonEpisodes = plan.episodesBySeason[plan.visibleSeason].orEmpty()
            val currentSeasonLabel = seasonLabel(plan.visibleSeason)

            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = currentSeasonLabel,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    SelectionTextButton(Res.string.downloads_select_unwatched) {
                        BatchDownloadCoordinator.selectUnwatchedForSeason(
                            season = plan.visibleSeason,
                            isEpisodeWatched = isEpisodeWatched,
                        )
                    }
                    SelectionTextButton(Res.string.downloads_select_all) {
                        BatchDownloadCoordinator.selectAllForSeason(plan.visibleSeason)
                    }
                    SelectionTextButton(Res.string.downloads_deselect_all) {
                        BatchDownloadCoordinator.deselectAllForSeason(plan.visibleSeason)
                    }
                }
            }

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 280.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                items(
                    items = currentSeasonEpisodes,
                    key = { it.id.ifBlank { "${it.season}_${it.episode}" } },
                ) { episode ->
                    val episodeNumber = episode.episode ?: 0
                    val key = episode.batchKey(plan.visibleSeason)
                    val isChecked = key in plan.selectedEpisodeKeys
                    val unavailable = isUnavailable(episode, plan.visibleSeason)
                    val completed = isDownloaded(episode, plan.visibleSeason)
                    val watched = isEpisodeWatched(episode)

                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable(enabled = !unavailable) {
                                BatchDownloadCoordinator.toggleEpisodeSelection(plan.visibleSeason, episodeNumber)
                            },
                        shape = RoundedCornerShape(10.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = if (isChecked) 0.5f else 0.25f),
                        border = if (isChecked) BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.5f)) else null,
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 10.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Checkbox(
                                checked = if (unavailable) true else isChecked,
                                enabled = !unavailable,
                                onCheckedChange = {
                                    BatchDownloadCoordinator.toggleEpisodeSelection(plan.visibleSeason, episodeNumber)
                                },
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                val episodeTitle = episode.title?.takeIf { it.isNotBlank() }
                                    ?: stringResource(Res.string.downloads_episode_fallback_title, episodeNumber)
                                Text(
                                    text = localizedEpisodeLabel(plan.visibleSeason, episodeNumber, episodeTitle),
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                                    color = if (unavailable) MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f) else MaterialTheme.colorScheme.onSurface,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                val tags = mutableListOf<String>()
                                if (completed) tags.add(stringResource(Res.string.season_download_already_downloaded))
                                else if (unavailable) tags.add(stringResource(Res.string.downloads_status_already_in_progress))
                                if (watched) tags.add(stringResource(Res.string.episodes_cd_watched))
                                if (tags.isNotEmpty()) {
                                    Text(
                                        text = tags.joinToString(" • "),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = if (completed) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }
                    }
                }
            }
            val selectedCount = plan.totalSelectedCount
            val seasonsCount = plan.availableSeasons.count(plan::isSeasonSelected)
            val summaryText = if (seasonsCount > 1) {
                stringResource(Res.string.downloads_episodes_selected_multi_season, selectedCount, seasonsCount)
            } else {
                stringResource(Res.string.downloads_episodes_selected, selectedCount)
            }

            Text(
                text = summaryText,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        DialogButtons {
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismissRequest,
                style = DialogButtonStyle.Secondary,
            )
            DialogButton(
                text = stringResource(Res.string.downloads_action_continue_source_selection),
                onClick = { BatchDownloadCoordinator.continueToSourceSelection() },
                style = DialogButtonStyle.Primary,
                enabled = plan.totalSelectedCount > 0,
            )
        }
    }
}

@Composable
private fun SourceSelectionDialog(
    plan: BatchDownloadPlan,
    seasonIndex: Int,
    onDismissRequest: () -> Unit,
    onConfirm: () -> Unit,
    onOverrideClicked: (PlannedEpisodeItem) -> Unit,
) {
    val totalSeasons = plan.seasonsToSource.size
    val currentSeason = plan.seasonsToSource[seasonIndex]
    val currentSeasonPlan = plan.seasonPlans[currentSeason]
    val isPlanning = currentSeasonPlan?.isPlanning == true

    val dialogTitle = if (plan.isSingleTitle) {
        plan.meta.name
    } else {
        stringResource(
            Res.string.downloads_season_step_indicator,
            seasonIndex + 1,
            totalSeasons,
        )
    }

    val currentSeasonLabel = if (plan.isSingleTitle) {
        plan.meta.releaseInfo.orEmpty()
    } else {
        seasonLabel(currentSeason)
    }

    val episodes = currentSeasonPlan?.episodes.orEmpty()
    val allStreamsAcrossSeason = remember(episodes) {
        episodes.flatMap { it.allAvailableStreams }
    }
    val nuvioStreamCount = remember(allStreamsAcrossSeason) {
        allStreamsAcrossSeason.count { !it.isCloudStreamBatchSource() }
    }
    val cloudStreamCount = remember(allStreamsAcrossSeason) {
        allStreamsAcrossSeason.count { it.isCloudStreamBatchSource() }
    }

    DialogSurface(
        onDismissRequest = onDismissRequest,
        modifier = Modifier.fillMaxWidth(0.94f),
        title = dialogTitle,
        properties = WideBatchDialogProperties,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                if (currentSeasonLabel.isNotBlank()) {
                    Text(
                        text = currentSeasonLabel,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
                if (isPlanning) {
                    FindingSourceIndicator(compact = false)
                }
            }

            BatchSourceFilterBar(
                selected = plan.sourceFilter,
                nuvioCount = nuvioStreamCount,
                cloudStreamCount = cloudStreamCount,
                onSelect = BatchDownloadCoordinator::setSourceFilter,
            )

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 320.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(
                    items = episodes,
                    key = { it.episode.id.ifBlank { "${it.episode.season}_${it.episode.episode}" } },
                ) { item ->
                    EpisodeSourcePlanRow(
                        item = item,
                        season = currentSeason,
                        defaultTitle = plan.meta.name,
                        activeFilter = plan.sourceFilter,
                        onChangeSource = { onOverrideClicked(item) },
                    )
                }
            }
        }

        val isLastSeason = seasonIndex >= totalSeasons - 1

        DialogButtons {
            DialogButton(
                text = if (plan.isSingleTitle) {
                    stringResource(Res.string.action_cancel)
                } else {
                    stringResource(Res.string.action_back)
                },
                onClick = {
                    if (plan.isSingleTitle) {
                        onDismissRequest()
                    } else if (seasonIndex > 0) {
                        BatchDownloadCoordinator.goToSeasonIndex(seasonIndex - 1)
                    } else {
                        BatchDownloadCoordinator.goToEpisodeSelection()
                    }
                },
                style = DialogButtonStyle.Secondary,
            )

            if (!isLastSeason && !plan.isSingleTitle) {
                DialogButton(
                    text = stringResource(Res.string.downloads_next_season),
                    onClick = { BatchDownloadCoordinator.goToSeasonIndex(seasonIndex + 1) },
                    style = DialogButtonStyle.Primary,
                    enabled = !isPlanning,
                    loading = isPlanning,
                )
            } else {
                DialogButton(
                    text = stringResource(Res.string.downloads_action_queue),
                    onClick = onConfirm,
                    style = DialogButtonStyle.Primary,
                    enabled = !isPlanning && plan.seasonPlans.values.any { it.readyToDownloadCount > 0 },
                    loading = isPlanning,
                )
            }
        }
    }
}

@Composable
private fun BatchSourceFilterBar(
    selected: BatchSourceFilter,
    nuvioCount: Int,
    cloudStreamCount: Int,
    onSelect: (BatchSourceFilter) -> Unit,
) {
    val totalCount = nuvioCount + cloudStreamCount
    LazyRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            FilterChip(
                selected = selected == BatchSourceFilter.All,
                onClick = { onSelect(BatchSourceFilter.All) },
                label = {
                    Text(
                        text = if (totalCount > 0) "All ($totalCount)" else "All Sources",
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                    selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                ),
            )
        }
        item {
            FilterChip(
                selected = selected == BatchSourceFilter.Nuvio,
                onClick = { onSelect(BatchSourceFilter.Nuvio) },
                label = {
                    Text(
                        text = if (totalCount > 0) "Nuvio ($nuvioCount)" else "Nuvio",
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = MaterialTheme.colorScheme.secondaryContainer,
                    selectedLabelColor = MaterialTheme.colorScheme.onSecondaryContainer,
                ),
            )
        }
        item {
            FilterChip(
                selected = selected == BatchSourceFilter.CloudStream,
                onClick = { onSelect(BatchSourceFilter.CloudStream) },
                label = {
                    Text(
                        text = if (totalCount > 0) "CloudStream ($cloudStreamCount)" else "CloudStream",
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = MaterialTheme.colorScheme.tertiaryContainer,
                    selectedLabelColor = MaterialTheme.colorScheme.onTertiaryContainer,
                ),
            )
        }
    }
}

@Composable
private fun SourceOriginBadge(isCloudStream: Boolean) {
    val bgColor = if (isCloudStream) {
        MaterialTheme.colorScheme.tertiaryContainer
    } else {
        MaterialTheme.colorScheme.secondaryContainer
    }
    val fgColor = if (isCloudStream) {
        MaterialTheme.colorScheme.onTertiaryContainer
    } else {
        MaterialTheme.colorScheme.onSecondaryContainer
    }
    Box(
        modifier = Modifier
            .background(bgColor, RoundedCornerShape(6.dp))
            .padding(horizontal = 7.dp, vertical = 2.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = if (isCloudStream) "CLOUDSTREAM" else "NUVIO",
            style = MaterialTheme.typography.labelSmall.copy(
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 0.4.sp,
            ),
            color = fgColor,
            maxLines = 1,
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EpisodeSourcePlanRow(
    item: PlannedEpisodeItem,
    season: Int,
    defaultTitle: String,
    activeFilter: BatchSourceFilter,
    onChangeSource: () -> Unit,
) {
    val episodeTitle = item.episode.title?.takeIf { it.isNotBlank() } ?: defaultTitle
    val displayText = item.episode.episode?.let { episodeNumber ->
        localizedEpisodeLabel(season, episodeNumber, episodeTitle)
    } ?: episodeTitle

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.38f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.35f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = displayText,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )

                if (item.status == EpisodePlanStatus.Ready || item.allAvailableStreams.isNotEmpty()) {
                    OutlinedButton(
                        onClick = onChangeSource,
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier
                            .padding(start = 8.dp)
                            .heightIn(min = 32.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Edit,
                            contentDescription = null,
                            modifier = Modifier.size(13.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = stringResource(Res.string.downloads_override_source),
                            style = MaterialTheme.typography.labelSmall,
                            maxLines = 1,
                        )
                    }
                }
            }

            when {
                item.status == EpisodePlanStatus.Loading -> {
                    FindingSourceIndicator(compact = true)
                }
                item.status == EpisodePlanStatus.AlreadyDownloaded -> {
                    Text(
                        text = stringResource(Res.string.season_download_already_downloaded),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                item.status == EpisodePlanStatus.AlreadyInProgress -> {
                    Text(
                        text = stringResource(Res.string.downloads_status_queued),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                item.status == EpisodePlanStatus.Ready && item.streamCandidate != null -> {
                    val selected = item.streamCandidate
                    val isCs3 = selected.isCloudStreamBatchSource()
                    val badge = item.resolutionLabel
                    val provider = selected.addonName?.takeIf { it.isNotBlank() }
                    val size = item.sizeBytes?.takeIf { it > 0 }?.let(::formatBytes)
                    val streamHeadline = selected.streamLabel
                        .ifBlank { selected.name ?: selected.title.orEmpty() }
                        .trim()

                    FlowRow(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        SourceOriginBadge(isCloudStream = isCs3)
                        val metaSummary = streamSourceSummary(badge, provider, size)
                        if (metaSummary.isNotBlank()) {
                            Text(
                                text = metaSummary,
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    }

                    if (streamHeadline.isNotBlank()) {
                        Text(
                            text = streamHeadline,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.9f),
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
                else -> {
                    val hint = when {
                        activeFilter == BatchSourceFilter.CloudStream && item.allAvailableStreams.any { !it.isCloudStreamBatchSource() } ->
                            "No CloudStream source found (Nuvio sources available)"
                        activeFilter == BatchSourceFilter.Nuvio && item.allAvailableStreams.any { it.isCloudStreamBatchSource() } ->
                            "No Nuvio source found (CloudStream sources available)"
                        else -> stringResource(Res.string.season_download_no_source_found)
                    }
                    Text(
                        text = hint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun StreamOverrideDialog(
    target: PlannedEpisodeItem,
    initialFilter: BatchSourceFilter,
    onSelect: (StreamItem) -> Unit,
    onDismiss: () -> Unit,
) {
    var filter by remember(initialFilter) { mutableStateOf(initialFilter) }
    val episodeNumber = target.episode.episode
    val dialogTitle = if (episodeNumber != null) {
        stringResource(Res.string.downloads_select_source_dialog_title, episodeNumber)
    } else {
        stringResource(Res.string.downloads_select_source_dialog_title_single)
    }

    val allStreams = remember(target.allAvailableStreams) {
        target.allAvailableStreams.filter { stream ->
            isDownloadableDirectUrl(stream.playableDirectUrl) || stream.isResolverDependent()
        }.ifEmpty { target.allAvailableStreams }
    }
    val nuvioCount = remember(allStreams) { allStreams.count { !it.isCloudStreamBatchSource() } }
    val cloudStreamCount = remember(allStreams) { allStreams.count { it.isCloudStreamBatchSource() } }
    val filteredStreams = remember(allStreams, filter) {
        allStreams.filter { it.matchesBatchSourceFilter(filter) }
    }

    DialogSurface(
        onDismissRequest = onDismiss,
        modifier = Modifier.fillMaxWidth(0.94f),
        title = dialogTitle,
        properties = WideBatchDialogProperties,
    ) {
        BatchSourceFilterBar(
            selected = filter,
            nuvioCount = nuvioCount,
            cloudStreamCount = cloudStreamCount,
            onSelect = { filter = it },
        )

        if (filteredStreams.isEmpty()) {
            Text(
                text = stringResource(Res.string.season_download_no_source_found),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 360.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(filteredStreams) { stream ->
                    val facts = remember(stream) {
                        DebridStreamMetadata.facts(stream, DebridStreamPreferences())
                    }
                    val isCurrentSelection = stream == target.streamCandidate
                    val isCs3 = stream.isCloudStreamBatchSource()

                    val badge = facts.qualityBadge()
                    val size = StreamSourcePrefillSelector.sizeBytes(stream)?.let(::formatBytes)
                    val addon = stream.addonName

                    val titleText = stream.streamLabel.ifBlank {
                        stream.name ?: stringResource(Res.string.downloads_stream_fallback_title)
                    }
                    val subtitleText = streamSourceSummary(badge, addon, size)

                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelect(stream) },
                        shape = RoundedCornerShape(10.dp),
                        color = if (isCurrentSelection) {
                            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
                        } else {
                            MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)
                        },
                        border = if (isCurrentSelection) {
                            BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary)
                        } else {
                            BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                        },
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Column(
                                modifier = Modifier.weight(1f),
                                verticalArrangement = Arrangement.spacedBy(4.dp),
                            ) {
                                FlowRow(
                                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                                    verticalArrangement = Arrangement.spacedBy(4.dp),
                                ) {
                                    SourceOriginBadge(isCloudStream = isCs3)
                                    if (subtitleText.isNotBlank()) {
                                        Text(
                                            text = subtitleText,
                                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                            color = if (isCurrentSelection) {
                                                MaterialTheme.colorScheme.primary
                                            } else {
                                                MaterialTheme.colorScheme.onSurfaceVariant
                                            },
                                        )
                                    }
                                }
                                Text(
                                    text = titleText,
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                                    color = MaterialTheme.colorScheme.onSurface,
                                    maxLines = 3,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                val extraDesc = stream.description?.trim()?.takeIf {
                                    it.isNotBlank() && !titleText.contains(it, ignoreCase = true)
                                }
                                if (extraDesc != null) {
                                    Text(
                                        text = extraDesc,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                }
                            }
                            if (isCurrentSelection) {
                                Spacer(modifier = Modifier.width(8.dp))
                                Icon(
                                    imageVector = Icons.Rounded.Check,
                                    contentDescription = null,
                                    modifier = Modifier.size(20.dp),
                                    tint = MaterialTheme.colorScheme.primary,
                                )
                            }
                        }
                    }
                }
            }
        }

        DialogButtons {
            DialogButton(
                text = stringResource(Res.string.action_cancel),
                onClick = onDismiss,
                style = DialogButtonStyle.Secondary,
            )
        }
    }
}

@Composable
private fun SelectionTextButton(label: StringResource, onClick: () -> Unit) {
    TextButton(
        onClick = onClick,
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Text(
            text = stringResource(label),
            style = MaterialTheme.typography.labelMedium,
            maxLines = 1,
        )
    }
}

@Composable
private fun FindingSourceIndicator(compact: Boolean) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(if (compact) 11.dp else 14.dp),
            strokeWidth = if (compact) 1.6.dp else 2.dp,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = stringResource(Res.string.season_download_finding_source),
            style = MaterialTheme.typography.bodySmall,
            color = if (compact) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.primary,
        )
    }
}

private fun streamSourceSummary(badge: String?, addon: String?, size: String?): String =
    listOfNotNull(badge, addon, size).joinToString(" • ")
""",
        encoding="utf-8",
    )
    patched.append(str(batch_dialog.relative_to(root)))

    return patched


def prepare_nuvio_source(
    root: Path,
    android_sdk: str | None = None,
    configure_global_gradle: bool = True,
) -> dict[str, object]:
    """Prepare Nuvio Enhanced source tree for Android builds."""
    restored_files: list[str] = []
    patched_files: list[str] = []

    if (root / "composeApp" / "build.gradle.kts").is_file():
        patched_files.extend(_patch_navigation_and_downloads_tab(root))
        patched_files.extend(_patch_cloudstream_host_and_settings(root))
        patched_files.extend(_patch_batch_downloads_and_hls(root))

        for rel_path, content in APP_FEATURE_POLICY_FILES.items():
            target = root / rel_path
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                restored_files.append(rel_path)

    # Guard against `*/bin/*` archive exclusions breaking Cargo manifest checks
    thumbs_cargo = root / "native" / "thumbs" / "Cargo.toml"
    thumbs_bin_main = root / "native" / "thumbs" / "src" / "bin" / "thumbs-bench" / "main.rs"
    thumbs_bin_alt = root / "native" / "thumbs" / "src" / "bin" / "thumbs-bench.rs"
    if (
        thumbs_cargo.is_file()
        and 'name = "thumbs-bench"' in thumbs_cargo.read_text(encoding="utf-8", errors="replace")
        and not thumbs_bin_main.exists()
        and not thumbs_bin_alt.exists()
    ):
        thumbs_bin_main.parent.mkdir(parents=True, exist_ok=True)
        thumbs_bin_main.write_text("fn main() {}\n", encoding="utf-8")
        restored_files.append(str(thumbs_bin_main.relative_to(root)))

    # Ensure gradlew is executable
    gradlew = root / "gradlew"
    if gradlew.is_file():
        gradlew.chmod(gradlew.stat().st_mode | 0o111)

    # Ensure local.properties exists (required by Nuvio build scripts and AGP)
    sdk_dir = (
        android_sdk
        or os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
    )
    local_props = root / "local.properties"
    if sdk_dir and Path(sdk_dir).exists():
        existing = local_props.read_text(encoding="utf-8", errors="replace") if local_props.exists() else ""
        if "sdk.dir=" not in existing:
            with local_props.open("a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(f"sdk.dir={sdk_dir}\n")
    elif not local_props.exists():
        local_props.touch()

    if configure_global_gradle:
        gradle_user_home = Path(os.environ.get("GRADLE_USER_HOME", str(Path.home() / ".gradle")))
        gradle_user_home.mkdir(parents=True, exist_ok=True)
        user_props = gradle_user_home / "gradle.properties"
        desired_lines = {
            "org.gradle.jvmargs": "org.gradle.jvmargs=-Xmx6g -Dfile.encoding=UTF-8 -XX:MaxMetaspaceSize=1536m",
            "kotlin.daemon.jvmargs": "kotlin.daemon.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1536m -XX:+UseParallelGC",
            "org.gradle.configuration-cache": "org.gradle.configuration-cache=false",
        }
        lines = (
            user_props.read_text(encoding="utf-8", errors="replace").splitlines()
            if user_props.exists()
            else []
        )
        filtered = [
            ln for ln in lines
            if not any(ln.strip().startswith(f"{k}=") or ln.strip().startswith(f"{k} =") for k in desired_lines)
        ]
        filtered.extend(desired_lines.values())
        user_props.write_text("\n".join(filtered) + "\n", encoding="utf-8")

    return {
        "project_root": str(root),
        "is_nuvio": is_nuvio_project(root),
        "restored_files": restored_files,
        "patched_files": patched_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Nuvio Enhanced source tree")
    parser.add_argument("--root", required=True, help="Extracted Nuvio project root")
    parser.add_argument("--android-sdk", default=None, help="Android SDK path")
    parser.add_argument("--no-global-gradle", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    summary = prepare_nuvio_source(
        root,
        android_sdk=args.android_sdk,
        configure_global_gradle=not args.no_global_gradle,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
