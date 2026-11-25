#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 7: Smart Stream Auto-Switch (Section 13).

  - `tryFallbackToNextSourceAfterError()` now covers pre-start errors, mid-playback
    fatal errors and sustained stalls, for auto AND manually picked streams
    (position is preserved by `playReplacementSource`).
  - Non-blocking "Switching to backup stream…" pill while a fallback runs
    (`sourceFallbackStatus` rendered by `PlayerPlaybackOverlays`).
  - Stall watchdog (`BindSourceFallbackStallWatchdog`): no position progress for 12s
    while playback should be running triggers the fallback path.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 fallback] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 fallback] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_state(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeState.kt"
    _replace_once(
        path,
        """    var sourceFallbackJob: Job? = null""",
        """    var sourceFallbackJob: Job? = null
    /** Nuvio Enhanced: transient non-blocking status shown while a backup stream is tried. */
    var sourceFallbackStatus: String? = null""",
        "sourceFallbackStatus state",
    )


def _patch_fallback(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeSourceFallback.kt"
    _replace_once(
        path,
        """import kotlinx.coroutines.delay
import kotlinx.coroutines.launch""",
        """import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.time.Duration.Companion.seconds
import kotlin.time.TimeSource
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect""",
        "fallback imports",
    )

    _replace_once(
        path,
        """/**
 * When the auto-selected source fails before playback starts, quietly plays the next source that
 * auto source selection would pick, up to the configured number of further sources. It never
 * applies to a source the user picked, and it excludes the engine switch on error.
 *
 * Returns `true` when a fallback was started and the error must not be shown yet.
 */
internal fun PlayerScreenRuntime.tryFallbackToNextSourceAfterError(message: String?): Boolean {
    if (sourceFallbackJob?.isActive == true) return true
    val settings = playerSettingsUiState
    if (!settings.streamAutoPlayFallbackActive) return false
    if (!isIos && settings.autoSwitchPlaybackEngineOnError) return false
    if (initialLoadCompleted) return false
    val failedUrl = activeSourceUrl
    if (failedUrl.isBlank() || failedUrl != autoSelectedSourceUrl) return false
    if (sourceFallbackAttempts >= settings.streamAutoPlayFallbackMaxSources) return false""",
        """/**
 * When the current source fails (before playback starts or mid-playback) or playback stalls,
 * quietly plays the next source that auto source selection would pick — with the configured
 * quality/language preferences applied by the rankings — up to the configured number of further
 * sources. Mid-playback fallbacks continue from the current position, and the failing source may
 * be auto-selected or manually picked. The engine switch on error is excluded.
 *
 * Returns `true` when a fallback was started and the error must not be shown yet.
 */
internal fun PlayerScreenRuntime.tryFallbackToNextSourceAfterError(message: String?): Boolean {
    if (sourceFallbackJob?.isActive == true) return true
    val settings = playerSettingsUiState
    if (!settings.streamAutoPlayFallbackActive) return false
    if (!isIos && settings.autoSwitchPlaybackEngineOnError) return false
    // v1.20: covers pre-start errors, mid-playback fatal errors and sustained stalls,
    // whether the failing source was auto-selected or manually picked.
    val failedUrl = activeSourceUrl
    if (failedUrl.isBlank()) return false
    if (sourceFallbackAttempts >= settings.streamAutoPlayFallbackMaxSources) return false""",
        "fallback gates",
    )

    _replace_once(
        path,
        """    errorMessage = null

    sourceFallbackJob = scope.launch {
        try {""",
        """    errorMessage = null
    sourceFallbackStatus = "Switching to backup stream…"

    sourceFallbackJob = scope.launch {
        try {""",
        "status set on start",
    )

    _replace_once(
        path,
        """        } finally {
            PlayerStreamsRepository.stopSourcesLoading()
        }""",
        """        } finally {
            PlayerStreamsRepository.stopSourcesLoading()
            sourceFallbackStatus = null
        }""",
        "status cleared",
    )

    _replace_once(
        path,
        """    return StreamAutoPlaySelector.evaluateAutoPlayStream(
        streams = untried,
        mode = settings.streamAutoPlayMode,
        regexPattern = settings.streamAutoPlayRegex,
        source = settings.streamAutoPlaySource,
        installedAddonNames = installedAddonNames,
        selectedAddons = settings.streamAutoPlaySelectedAddons,
        selectedPlugins = settings.streamAutoPlaySelectedPlugins,
        debridEnabled = debridEnabled,
        activeResolverProviderId = activeResolverProviderId,
    ).readyStreams.firstOrNull()
}""",
        """    return StreamAutoPlaySelector.evaluateAutoPlayStream(
        streams = untried,
        mode = settings.streamAutoPlayMode,
        regexPattern = settings.streamAutoPlayRegex,
        source = settings.streamAutoPlaySource,
        installedAddonNames = installedAddonNames,
        selectedAddons = settings.streamAutoPlaySelectedAddons,
        selectedPlugins = settings.streamAutoPlaySelectedPlugins,
        debridEnabled = debridEnabled,
        activeResolverProviderId = activeResolverProviderId,
    ).readyStreams.firstOrNull()
}

/**
 * Nuvio Enhanced (v1.20): sustained-stall watchdog. When playback should be running but the
 * position makes no progress for [STALL_THRESHOLD], quietly fall back to the next source.
 */
@Composable
internal fun PlayerScreenRuntime.BindSourceFallbackStallWatchdog() {
    LaunchedEffect(Unit) {
        val timeSource = TimeSource.Monotonic
        var lastPositionMs = playbackSnapshot.positionMs
        var lastProgressAt = timeSource.markNow()
        while (true) {
            delay(STALL_POLL_INTERVAL)
            val snapshot = playbackSnapshot
            if (snapshot.positionMs != lastPositionMs) {
                lastPositionMs = snapshot.positionMs
                lastProgressAt = timeSource.markNow()
                continue
            }
            val shouldCurrentlyPlay = shouldPlay &&
                !snapshot.isEnded &&
                !snapshot.isLoading &&
                !snapshot.isOpening
            if (!shouldCurrentlyPlay || errorMessage != null || sourceFallbackStatus != null) {
                lastProgressAt = timeSource.markNow()
                continue
            }
            if (lastProgressAt.elapsedNow() >= STALL_THRESHOLD) {
                // One probe per interval; the fallback's own gates decide applicability.
                tryFallbackToNextSourceAfterError("Playback stalled — trying a backup stream")
                lastProgressAt = timeSource.markNow()
                lastPositionMs = playbackSnapshot.positionMs
            }
        }
    }
}

private val STALL_POLL_INTERVAL = 2_000L
private val STALL_THRESHOLD = 12.seconds""",
        "stall watchdog",
    )


def _patch_overlays(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerPlaybackOverlays.kt"
    _replace_once(
        path,
        """import androidx.compose.runtime.Composable""",
        """import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color""",
        "overlays imports",
    )
    _replace_once(
        path,
        """    errorMessage: String?,
    onDismissError: () -> Unit,
) {""",
        """    sourceFallbackStatus: String? = null,
    errorMessage: String?,
    onDismissError: () -> Unit,
) {""",
        "overlays status param",
    )
    _replace_once(
        path,
        """    if (errorMessage != null) {
        ErrorModal(
            message = errorMessage,
            onDismiss = onDismissError,
        )
    }
}""",
        """    if (sourceFallbackStatus != null && errorMessage == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = 58.dp),
            contentAlignment = Alignment.TopCenter,
        ) {
            Surface(
                shape = RoundedCornerShape(50),
                color = Color.Black.copy(alpha = 0.72f),
            ) {
                Text(
                    text = sourceFallbackStatus.orEmpty(),
                    color = Color.White,
                    style = MaterialTheme.typography.labelLarge,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                )
            }
        }
    }

    if (errorMessage != null) {
        ErrorModal(
            message = errorMessage,
            onDismiss = onDismissError,
        )
    }
}""",
        "switching pill UI",
    )


def _patch_ui_call_site(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeUi.kt"
    _replace_once(
        path,
        """        currentGestureFeedback = currentGestureFeedback,
        renderedGestureFeedback = renderedGestureFeedback,""",
        """        currentGestureFeedback = currentGestureFeedback,
        renderedGestureFeedback = renderedGestureFeedback,
        sourceFallbackStatus = sourceFallbackStatus,""",
        "overlays call site status",
    )


def _patch_content_effects(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenContent.kt"
    _replace_once(
        path,
        """        runtime.BindPlayerRuntimeEffects()""",
        """        runtime.BindPlayerRuntimeEffects()
        runtime.BindSourceFallbackStallWatchdog()""",
        "bind stall watchdog",
    )


def apply_v120_source_fallback_patch(source_dir: Path) -> None:
    _patch_state(source_dir)
    _patch_fallback(source_dir)
    _patch_overlays(source_dir)
    _patch_ui_call_site(source_dir)
    _patch_content_effects(source_dir)
    print("[v1.20-module-8] Smart stream auto-switch: mid-playback/stall fallback + switching pill applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_source_fallback_patch.py <source_dir>")
    apply_v120_source_fallback_patch(Path(sys.argv[1]).resolve())
