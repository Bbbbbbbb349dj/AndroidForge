#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 8: Subtitle Sync UI (Section 14).

  - `SubtitleStylePanel` delay stepper gains hold-repeat (±100ms per tick while held).
  - Fine (±50/±100 ms) and coarse (±500 ms) nudge chips plus a `0ms` reset chip.
  - Floating live-preview "Subtitle Sync" card on the player while a non-zero delay is set.
  Engine wiring already exists (`subtitleDelayMs` drives sidecar/ASS/Exo/MPV paths).
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 subsync] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 subsync] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_style_panel(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/SubtitleStylePanel.kt"
    _replace_once(
        path,
        """        SubtitleStyleSection(title = stringResource(Res.string.compose_player_subtitle_delay)) {
            SubtitleStyleStepper(
                value = formatSubtitleDelay(subtitleDelayMs),
                onDecrease = {
                    onSubtitleDelayChanged(
                        (subtitleDelayMs - SUBTITLE_DELAY_STEP_MS).coerceAtLeast(SUBTITLE_DELAY_MIN_MS),
                    )
                },
                onIncrease = {
                    onSubtitleDelayChanged(
                        (subtitleDelayMs + SUBTITLE_DELAY_STEP_MS).coerceAtMost(SUBTITLE_DELAY_MAX_MS),
                    )
                },
            )
            SubtitleTextAction(
                label = stringResource(Res.string.compose_player_reset),
                onClick = onSubtitleDelayReset,
            )
            SubtitleSyncByEarAction(
                label = stringResource(Res.string.compose_player_sync_by_ear),
                onClick = onSyncByEarClick,
            )
        }""",
        """        SubtitleStyleSection(title = stringResource(Res.string.compose_player_subtitle_delay)) {
            SubtitleStyleStepper(
                value = formatSubtitleDelay(subtitleDelayMs),
                onDecrease = {
                    onSubtitleDelayChanged(
                        (subtitleDelayMs - SUBTITLE_DELAY_STEP_MS).coerceAtLeast(SUBTITLE_DELAY_MIN_MS),
                    )
                },
                onIncrease = {
                    onSubtitleDelayChanged(
                        (subtitleDelayMs + SUBTITLE_DELAY_STEP_MS).coerceAtMost(SUBTITLE_DELAY_MAX_MS),
                    )
                },
                // Hold-repeat: keep nudging by one step while the button is held.
                onDecreaseHold = {
                    onSubtitleDelayChanged(
                        (subtitleDelayMs - SUBTITLE_DELAY_STEP_MS).coerceAtLeast(SUBTITLE_DELAY_MIN_MS),
                    )
                },
                onIncreaseHold = {
                    onSubtitleDelayChanged(
                        (subtitleDelayMs + SUBTITLE_DELAY_STEP_MS).coerceAtMost(SUBTITLE_DELAY_MAX_MS),
                    )
                },
            )
            // Fine / coarse nudge chips with a one-tap reset.
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                listOf(-500, -100, -50, 50, 100, 500).forEach { deltaMs ->
                    SubtitleDelayChip(
                        label = buildString {
                            if (deltaMs > 0) append('+') else append('\\u2212')
                            append(abs(deltaMs))
                            append("ms")
                        },
                        highlighted = false,
                        onClick = {
                            onSubtitleDelayChanged(
                                (subtitleDelayMs + deltaMs).coerceIn(SUBTITLE_DELAY_MIN_MS, SUBTITLE_DELAY_MAX_MS),
                            )
                        },
                    )
                }
                SubtitleDelayChip(
                    label = "0ms",
                    highlighted = subtitleDelayMs == 0,
                    onClick = onSubtitleDelayReset,
                )
            }
            SubtitleTextAction(
                label = stringResource(Res.string.compose_player_reset),
                onClick = onSubtitleDelayReset,
            )
            SubtitleSyncByEarAction(
                label = stringResource(Res.string.compose_player_sync_by_ear),
                onClick = onSyncByEarClick,
            )
        }""",
        "hold-repeat + nudge chips",
    )

    _replace_once(
        path,
        """private fun formatSubtitleDelay(delayMs: Int): String {""",
        """@Composable
private fun SubtitleDelayChip(
    label: String,
    highlighted: Boolean,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(
                if (highlighted) Color.White.copy(alpha = 0.22f)
                else Color.White.copy(alpha = 0.08f),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = label,
            color = Color.White,
            style = MaterialTheme.typography.labelMedium,
        )
    }
}

private fun formatSubtitleDelay(delayMs: Int): String {""",
        "SubtitleDelayChip composable",
    )


def _patch_overlays(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerPlaybackOverlays.kt"
    _replace_once(
        path,
        """    sourceFallbackStatus: String? = null,
    errorMessage: String?,
    onDismissError: () -> Unit,
) {""",
        """    sourceFallbackStatus: String? = null,
    subtitleDelayMs: Int = 0,
    errorMessage: String?,
    onDismissError: () -> Unit,
) {""",
        "overlays subtitleDelayMs param",
    )
    _replace_once(
        path,
        """    if (sourceFallbackStatus != null && errorMessage == null) {""",
        """    if (subtitleDelayMs != 0 && sourceFallbackStatus == null && errorMessage == null) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = 16.dp),
            contentAlignment = Alignment.TopCenter,
        ) {
            Surface(
                shape = RoundedCornerShape(50),
                color = Color.Black.copy(alpha = 0.72f),
            ) {
                val sign = if (subtitleDelayMs >= 0) "+" else "\\u2212"
                Text(
                    text = "Subtitle Sync  " + sign +
                        kotlin.math.abs(subtitleDelayMs) + "ms",
                    color = Color.White,
                    style = MaterialTheme.typography.labelLarge,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                )
            }
        }
    }

    if (sourceFallbackStatus != null && errorMessage == null) {""",
        "floating sync card",
    )


def _patch_ui_call_site(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimeUi.kt"
    _replace_once(
        path,
        """        sourceFallbackStatus = sourceFallbackStatus,""",
        """        sourceFallbackStatus = sourceFallbackStatus,
        subtitleDelayMs = subtitleDelayMs,""",
        "overlays call site subtitleDelayMs",
    )


def apply_v120_subtitle_sync_patch(source_dir: Path) -> None:
    _patch_style_panel(source_dir)
    _patch_overlays(source_dir)
    _patch_ui_call_site(source_dir)
    print("[v1.20-module-9] Subtitle sync hold-repeat, nudge chips & floating preview card applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_subtitle_sync_patch.py <source_dir>")
    apply_v120_subtitle_sync_patch(Path(sys.argv[1]).resolve())
