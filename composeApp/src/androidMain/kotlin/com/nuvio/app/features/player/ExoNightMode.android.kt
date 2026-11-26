@file:OptIn(androidx.media3.common.util.UnstableApi::class)

package com.nuvio.app.features.player

import android.media.audiofx.DynamicsProcessing
import android.os.Build
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.nuvio.app.core.logging.InAppLogger

/** Real dynamic-range compression on ExoPlayer, bound to its current audio session. */
@Composable
internal fun BindExoNightMode(player: ExoPlayer, enabled: Boolean) {
    DisposableEffect(player, enabled) {
        var effect: DynamicsProcessing? = null
        fun bind(sessionId: Int) {
            effect?.release()
            effect = null
            if (!enabled || Build.VERSION.SDK_INT < 28 || sessionId == C.AUDIO_SESSION_ID_UNSET || sessionId <= 0) return
            effect = runCatching {
                val limiter = DynamicsProcessing.Limiter(
                    true, true, 0, 5f, 150f, 6f, -24f, 6f,
                )
                val config = DynamicsProcessing.Config.Builder(
                    DynamicsProcessing.VARIANT_FAVOR_TIME_RESOLUTION,
                    2, false, 0, false, 0, false, 0, true,
                ).setLimiterAllChannelsTo(limiter).build()
                val processor = DynamicsProcessing(0, sessionId, config)
                try {
                    check(processor.setEnabled(true) == android.media.audiofx.AudioEffect.SUCCESS)
                    processor
                } catch (error: Throwable) {
                    processor.release()
                    throw error
                }
            }.onFailure {
                InAppLogger.warn("Player/NightMode", "Audio compression unavailable on this device: ${it.message}")
            }.getOrNull()
        }
        val listener = object : Player.Listener {
            override fun onAudioSessionIdChanged(audioSessionId: Int) = bind(audioSessionId)
        }
        player.addListener(listener)
        bind(player.audioSessionId)
        onDispose {
            player.removeListener(listener)
            effect?.release()
        }
    }
}
