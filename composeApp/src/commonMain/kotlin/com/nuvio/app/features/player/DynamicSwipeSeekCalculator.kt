package com.nuvio.app.features.player

import kotlin.math.abs
import kotlin.math.pow
import kotlin.math.roundToLong
import kotlin.math.sign

/**
 * Dynamic horizontal swipe-to-seek calculator combining:
 * 1. Dead-zone noise filtering (`12 dp`) so micro-taps and vertical volume/brightness drags never trigger seeks.
 * 2. Progressive distance curve (`effectiveDp / widthDp`) for precise 1–5s frame/line scrubbing on short/slow drags.
 * 3. Velocity acceleration (`dpPerSec`) so fast flicks jump 1–5+ minutes smoothly without lifting and re-swiping.
 * 4. Strict clamping to `[0L, durationMs]`.
 */
object DynamicSwipeSeekCalculator {
    const val DEAD_ZONE_DP: Float = 12f

    fun calculateDeltaMs(
        totalDragDp: Float,
        velocityDpPerSec: Float,
        surfaceWidthDp: Float,
        durationMs: Long,
        sensitivity: Float = 1.0f,
    ): Long {
        if (durationMs <= 0L) return 0L
        val absDp = abs(totalDragDp)
        if (absDp <= DEAD_ZONE_DP) return 0L

        val direction = sign(totalDragDp)
        val safeWidthDp = surfaceWidthDp.coerceAtLeast(240f)
        val effectiveDp = absDp - DEAD_ZONE_DP
        val normalizedDistance = (effectiveDp / safeWidthDp).coerceIn(0f, 1.75f)

        // Base full-swipe span scales gently with total runtime (90s for clips, ~180s for episodes, ~300s for long films)
        val durationMinutes = (durationMs / 60_000.0).coerceAtLeast(1.0)
        val baseFullSwipeSeconds = when {
            durationMinutes <= 12.0 -> 75.0
            durationMinutes <= 55.0 -> 165.0
            else -> 260.0
        }

        // Super-linear distance curve: small movements yield sub-second / 1-5s precision; wide drags cover minutes
        val distanceSeconds = normalizedDistance.toDouble().pow(1.42) * baseFullSwipeSeconds

        // Smoothed velocity multiplier:
        //   < 110 dp/s (deliberate slow scrub) -> 0.55x .. 0.85x fine control
        //   110 .. 450 dp/s (normal drag)      -> 0.85x .. 1.35x balanced seek
        //   > 450 dp/s (fast flick)            -> up to 2.65x rapid chapter-scale seek
        val absVel = abs(velocityDpPerSec).coerceIn(0f, 2400f)
        val velocityFactor = when {
            absVel < 110f -> 0.55 + (absVel / 110f) * 0.30
            absVel < 450f -> 0.85 + ((absVel - 110f) / 340f) * 0.50
            else -> 1.35 + ((absVel - 450f) / 1950f).pow(0.85f) * 1.30
        }

        val clampedSensitivity = sensitivity.coerceIn(0.4f, 2.5f).toDouble()
        val rawDeltaMs = (distanceSeconds * velocityFactor * clampedSensitivity * 1000.0).roundToLong()
        return (rawDeltaMs * direction.toLong()).coerceIn(-durationMs, durationMs)
    }

    fun clampTargetPositionMs(
        startPositionMs: Long,
        deltaMs: Long,
        durationMs: Long,
    ): Long {
        if (durationMs <= 0L) return 0L
        return (startPositionMs + deltaMs).coerceIn(0L, durationMs)
    }
}
