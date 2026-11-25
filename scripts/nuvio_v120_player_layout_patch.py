#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 13: Player top-bar overlap coordination (Section 16).

  - `PlayerPlaybackOverlays` gains `playerStatusOverlayEnabled`; the floating
    Subtitle-Sync card and "Switching to backup stream…" pill stagger BELOW the
    centered status overlay instead of stacking on it.
  - Legacy TopCenter gesture pill shifts down while the status overlay is shown.
  - Clock overlay: legacy layout moves to TopCenter (clear of the header's action
    row) and the modern TopStart slot is hidden while the parental-guide card
    occupies TopStart.
  The `36.dp`/`12.dp`/`0.dp` title-end/actions-start toolbar padding gated on
  `playerStatusOverlayEnabled` already exists in `PlayerControls` and is preserved.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return  # already applied
        raise RuntimeError(f"[v1.20 layout] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 layout] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_overlays(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerPlaybackOverlays.kt"
    _replace_once(
        path,
        """    sourceFallbackStatus: String? = null,
    subtitleDelayMs: Int = 0,
    errorMessage: String?,
    onDismissError: () -> Unit,
) {""",
        """    sourceFallbackStatus: String? = null,
    subtitleDelayMs: Int = 0,
    playerStatusOverlayEnabled: Boolean = false,
    errorMessage: String?,
    onDismissError: () -> Unit,
) {""",
        "status flag param",
    )
    _replace_once(
        path,
        """    if (subtitleDelayMs != 0 && sourceFallbackStatus == null && errorMessage == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = 16.dp),""",
        """    if (subtitleDelayMs != 0 && sourceFallbackStatus == null && errorMessage == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = if (playerStatusOverlayEnabled) 52.dp else 16.dp),""",
        "sync card offset",
    )
    _replace_once(
        path,
        """    if (sourceFallbackStatus != null && errorMessage == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = 58.dp),""",
        """    if (sourceFallbackStatus != null && errorMessage == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = if (playerStatusOverlayEnabled) 96.dp else 58.dp),""",
        "fallback pill offset",
    )
    _replace_once(
        path,
        """    PlayerGestureOverlay(
        currentFeedback = currentGestureFeedback,
        renderedFeedback = renderedGestureFeedback,
        useLegacyLayout = useLegacyLayout,
        horizontalSafePadding = horizontalSafePadding,
        horizontalPadding = metrics.horizontalPadding,
    )""",
        """    PlayerGestureOverlay(
        currentFeedback = currentGestureFeedback,
        renderedFeedback = renderedGestureFeedback,
        useLegacyLayout = useLegacyLayout,
        horizontalSafePadding = horizontalSafePadding,
        horizontalPadding = metrics.horizontalPadding,
        playerStatusOverlayEnabled = playerStatusOverlayEnabled,
    )""",
        "gesture overlay flag",
    )


def _patch_gesture_overlay(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerGestureOverlay.kt"
    _replace_once(
        path,
        """internal fun PlayerGestureOverlay(
    currentFeedback: GestureFeedbackState?,
    renderedFeedback: GestureFeedbackState?,
    useLegacyLayout: Boolean,
    horizontalSafePadding: Dp,
    horizontalPadding: Dp,
) {""",
        """internal fun PlayerGestureOverlay(
    currentFeedback: GestureFeedbackState?,
    renderedFeedback: GestureFeedbackState?,
    useLegacyLayout: Boolean,
    horizontalSafePadding: Dp,
    horizontalPadding: Dp,
    playerStatusOverlayEnabled: Boolean = false,
) {""",
        "gesture overlay signature",
    )
    _replace_once(
        path,
        """                        modifier = Modifier
                            .align(Alignment.TopCenter)
                            .windowInsetsPadding(WindowInsets.safeContent.only(WindowInsetsSides.Top))
                            .padding(horizontal = horizontalSafePadding)
                            .padding(top = 40.dp),""",
        """                        modifier = Modifier
                            .align(Alignment.TopCenter)
                            .windowInsetsPadding(WindowInsets.safeContent.only(WindowInsetsSides.Top))
                            .padding(horizontal = horizontalSafePadding)
                            // Stagger below the centered status overlay when it is shown.
                            .padding(top = if (playerStatusOverlayEnabled) 84.dp else 40.dp),""",
        "gesture pill offset",
    )


def _patch_controls_clock(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerControls.kt"
    _replace_once(
        path,
        """            if (enhancedSettings.playerClockEndTimeEnabled && !enhancedSettings.playerStatusOverlayEnabled) {
                PlayerClockEndTimeOverlay(
                    playbackSnapshot = playbackSnapshot,
                    modifier = Modifier
                        .align(if (useLegacyLayout) Alignment.TopEnd else Alignment.TopStart)
                        .windowInsetsPadding(WindowInsets.safeContent.only(WindowInsetsSides.Top))
                        .padding(
                            start = if (useLegacyLayout) 0.dp else metrics.horizontalPadding,
                            end = if (useLegacyLayout) metrics.horizontalPadding else 0.dp,
                            top = metrics.verticalPadding / 4,
                        ),
                )
            }""",
        """            if (enhancedSettings.playerClockEndTimeEnabled &&
                !enhancedSettings.playerStatusOverlayEnabled &&
                !(showParentalGuide && !useLegacyLayout)
            ) {
                PlayerClockEndTimeOverlay(
                    playbackSnapshot = playbackSnapshot,
                    modifier = Modifier
                        // Legacy header owns TopStart/TopEnd, so the clock uses the free
                        // TopCenter slot (status overlay is disabled in this branch).
                        .align(if (useLegacyLayout) Alignment.TopCenter else Alignment.TopStart)
                        .windowInsetsPadding(WindowInsets.safeContent.only(WindowInsetsSides.Top))
                        .padding(
                            start = if (useLegacyLayout) 0.dp else metrics.horizontalPadding,
                            end = if (useLegacyLayout) 0.dp else metrics.horizontalPadding,
                            top = metrics.verticalPadding / 4,
                        ),
                )
            }""",
        "clock slot coordination",
    )


def _patch_ui_call_site(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeUi.kt"
    _replace_once(
        path,
        """        PlayerPlaybackOverlays(
            playerControlsLocked = playerControlsLocked,""",
        """        val overlayEnhancedSettings by remember {
            NuvioEnhancedSettingsRepository.ensureLoaded()
            NuvioEnhancedSettingsRepository.uiState
        }.collectAsStateWithLifecycle()
        PlayerPlaybackOverlays(
            playerControlsLocked = playerControlsLocked,""",
        "overlay enhanced settings state",
    )
    _replace_once(
        path,
        """        sourceFallbackStatus = sourceFallbackStatus,
        subtitleDelayMs = subtitleDelayMs,""",
        """        sourceFallbackStatus = sourceFallbackStatus,
        subtitleDelayMs = subtitleDelayMs,
        playerStatusOverlayEnabled = overlayEnhancedSettings.playerStatusOverlayEnabled,""",
        "overlays status flag call site",
    )


def apply_v120_player_layout_patch(source_dir: Path) -> None:
    _patch_overlays(source_dir)
    _patch_gesture_overlay(source_dir)
    _patch_controls_clock(source_dir)
    _patch_ui_call_site(source_dir)
    print("[v1.20-module-13] Player top-bar slot coordination (status/gesture/clock/pills) applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_player_layout_patch.py <source_dir>")
    apply_v120_player_layout_patch(Path(sys.argv[1]).resolve())
