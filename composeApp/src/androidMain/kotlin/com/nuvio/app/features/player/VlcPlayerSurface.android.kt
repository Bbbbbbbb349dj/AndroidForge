package com.nuvio.app.features.player

import android.content.Context
import android.content.ContextWrapper
import android.app.Activity
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.nuvio.app.features.streams.StreamSubtitle
import kotlinx.coroutines.*
import org.videolan.libvlc.LibVLC
import org.videolan.libvlc.Media
import org.videolan.libvlc.MediaPlayer
import org.videolan.libvlc.interfaces.IMedia
import org.videolan.libvlc.util.VLCVideoLayout
import java.util.concurrent.atomic.AtomicBoolean

private val vlcReleaseScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

/** Native LibVLC renders straight into its SurfaceView; Compose only receives 2 Hz snapshots. */
@Composable
internal fun VlcPlayerSurface(
    sourceUrl: String,
    sourceHeaders: Map<String, String>,
    externalSubtitles: List<StreamSubtitle>,
    modifier: Modifier,
    playWhenReady: Boolean,
    initialPositionMs: Long?,
    initialPositionRequestKey: String?,
    resizeMode: PlayerResizeMode,
    onInitialPositionHandled: (String, Boolean) -> Unit,
    onControllerReady: (PlayerEngineController) -> Unit,
    onSnapshot: (PlayerPlaybackSnapshot) -> Unit,
    onError: (String?) -> Unit,
) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val latestSnapshot = rememberUpdatedState(onSnapshot)
    val latestError = rememberUpdatedState(onError)
    val latestInitialHandled = rememberUpdatedState(onInitialPositionHandled)
    val sessionResult = remember(sourceUrl, sourceHeaders, initialPositionRequestKey) {
        runCatching { VlcSession(context.applicationContext, sourceUrl, sourceHeaders, externalSubtitles) }
    }
    val session = sessionResult.getOrNull()
    if (session == null) {
        LaunchedEffect(sessionResult) { latestError.value("VLC could not initialize. Try ExoPlayer or MPV.") }
        return
    }
    var attached by remember(session) { mutableStateOf(false) }
    var opening by remember(session) { mutableStateOf(true) }
    var buffering by remember(session) { mutableStateOf(true) }
    var ended by remember(session) { mutableStateOf(false) }
    var resumePending by remember(session) { mutableStateOf(true) }
    var stoppedForLifecycle by remember(session) { mutableStateOf(false) }

    fun publish() {
        if (session.closed.get()) return
        val player = session.player
        val video = player.currentVideoTrack
        val position = player.time.coerceAtLeast(0L)
        latestSnapshot.value(PlayerPlaybackSnapshot(
            isLoading = opening || buffering, isOpening = opening,
            isPlaying = player.isPlaying && !buffering, isEnded = ended,
            durationMs = player.length.coerceAtLeast(0L), positionMs = position,
            // LibVLC buffering percent is NOT a whole-file buffered position. Never invent it.
            bufferedPositionMs = position, playbackSpeed = player.rate,
            videoWidth = video?.width ?: 0, videoHeight = video?.height ?: 0,
        ))
    }

    DisposableEffect(session, owner) {
        session.player.setEventListener { event ->
            if (!session.closed.get()) {
                when (event.type) {
                    MediaPlayer.Event.Opening -> { opening = true; buffering = true; ended = false }
                    MediaPlayer.Event.Buffering -> buffering = event.buffering < 100f
                    MediaPlayer.Event.Playing -> {
                        opening = false; buffering = false; ended = false
                        latestError.value(null)
                        if (resumePending) {
                            resumePending = false
                            val requested = initialPositionMs?.takeIf { it > 0 }
                            val handled = requested != null && session.player.isSeekable && session.player.setTime(requested) >= 0
                            initialPositionRequestKey?.let { latestInitialHandled.value(it, handled) }
                        }
                        // FILE_LOADED/Playing can arrive after the user pauses or the activity stops.
                        if (!session.wantsPlayback || stoppedForLifecycle) session.player.pause()
                    }
                    MediaPlayer.Event.EndReached -> { opening = false; buffering = false; ended = true }
                    MediaPlayer.Event.EncounteredError -> {
                        opening = false; buffering = false
                        latestError.value("VLC could not play this source. Retry or switch playback engine.")
                    }
                }
                // TimeChanged/PositionChanged arrive at native video cadence: the poller handles them.
                if (event.type != MediaPlayer.Event.TimeChanged && event.type != MediaPlayer.Event.PositionChanged) publish()
            }
        }
        val observer = LifecycleEventObserver { _, event ->
            if (!session.closed.get()) when (event) {
                Lifecycle.Event.ON_STOP -> {
                    val activity = context.vlcActivity()
                    val pip = Build.VERSION.SDK_INT >= 24 && activity?.isInPictureInPictureMode == true
                    if (!pip && session.player.isPlaying) { stoppedForLifecycle = true; session.player.pause() }
                }
                Lifecycle.Event.ON_START -> if (stoppedForLifecycle) {
                    stoppedForLifecycle = false
                    if (session.wantsPlayback) session.player.play()
                }
                else -> Unit
            }
        }
        owner.lifecycle.addObserver(observer)
        onDispose {
            owner.lifecycle.removeObserver(observer)
            session.release()
        }
    }
    LaunchedEffect(session, attached) {
        if (!attached) return@LaunchedEffect
        onControllerReady(session.controller)
        session.player.play()
        if (!session.wantsPlayback) session.player.pause()
        while (isActive && !session.closed.get()) { publish(); delay(500) }
    }
    LaunchedEffect(session, playWhenReady) {
        session.wantsPlayback = playWhenReady
        if (attached && !session.closed.get()) {
            if (playWhenReady && !stoppedForLifecycle) session.player.play() else session.player.pause()
        }
    }
    LaunchedEffect(session, resizeMode, attached) {
        if (attached && !session.closed.get()) session.player.setVideoScale(when (resizeMode) {
            PlayerResizeMode.Fit -> MediaPlayer.ScaleType.SURFACE_BEST_FIT
            PlayerResizeMode.Fill -> MediaPlayer.ScaleType.SURFACE_FILL
            PlayerResizeMode.Zoom -> MediaPlayer.ScaleType.SURFACE_FIT_SCREEN
        })
    }
    Box(modifier) {
        AndroidView(modifier = Modifier.fillMaxSize(), factory = {
            VLCVideoLayout(it).also { layout -> session.player.attachViews(layout, null, true, false); attached = true }
        })
    }
}

private class VlcSession(
    context: Context,
    sourceUrl: String,
    headers: Map<String, String>,
    subtitles: List<StreamSubtitle>,
) {
    val closed = AtomicBoolean(false)
    var wantsPlayback = true
    private val lib = LibVLC(context, arrayListOf("--no-video-title-show", "--network-caching=1500", "--file-caching=300"))
    val player: MediaPlayer
    private var descriptor: ParcelFileDescriptor? = null

    init {
        try {
            player = MediaPlayer(lib)
            try {
                val uri = Uri.parse(sourceUrl)
                val media = if (uri.scheme == "content") {
                    descriptor = context.contentResolver.openFileDescriptor(uri, "r")
                        ?: error("Could not open local video")
                    Media(lib, descriptor!!.fileDescriptor)
                } else Media(lib, uri)
                try {
                    media.setHWDecoderEnabled(true, false)
                    val settings = PlayerSettingsRepository.uiState.value
                    if (settings.customPlaybackBuffersEnabled) {
                        media.addOption(":network-caching=${(settings.playbackStartBufferSeconds * 1000).coerceIn(500, 10000)}")
                    }
                    headers.forEach { (name, value) -> when {
                        name.equals("User-Agent", true) -> media.addOption(":http-user-agent=$value")
                        name.equals("Referer", true) || name.equals("Referrer", true) -> media.addOption(":http-referrer=$value")
                    } }
                    subtitles.forEach { media.addSlave(IMedia.Slave(IMedia.Slave.Type.Subtitle, 0, it.url)) }
                    player.media = media
                } finally { media.release() }
            } catch (error: Throwable) { player.release(); throw error }
        } catch (error: Throwable) { descriptor?.close(); lib.release(); throw error }
    }

    val controller = object : PlayerEngineController {
        override val playbackEngine = AndroidPlaybackEngine.Vlc
        override val supportsNightMode = false
        override fun play() { wantsPlayback = true; if (!closed.get()) player.play() }
        override fun pause() { wantsPlayback = false; if (!closed.get()) player.pause() }
        override fun seekTo(positionMs: Long) { if (!closed.get() && player.isSeekable) player.setTime(positionMs.coerceAtLeast(0)) }
        override fun seekBy(offsetMs: Long) { if (!closed.get()) seekTo(player.time + offsetMs) }
        override fun retry() { if (!closed.get()) { player.stop(); player.play() } }
        override fun setPlaybackSpeed(speed: Float) { if (!closed.get()) player.setRate(speed.coerceIn(0.25f, 4f)) }
        override fun currentPlayerVolume() = if (closed.get()) PlayerAudioLevel(1f, false) else PlayerAudioLevel(player.volume.coerceIn(0, 100) / 100f, player.volume == 0)
        override fun setPlayerVolume(level: Float): PlayerAudioLevel { if (!closed.get()) player.setVolume((level.coerceIn(0f, 1f) * 100).toInt()); return currentPlayerVolume() }
        override fun setMuted(muted: Boolean) { if (!closed.get()) player.setVolume(if (muted) 0 else 100) }
        override fun setVideoZoom(scale: Float) { if (!closed.get()) player.setScale(if (scale == 1f) 0f else scale.coerceIn(0.5f, 4f)) }
        override fun getAudioTracks() = (if (closed.get()) null else player.audioTracks).orEmpty().filter { it.id >= 0 }.map { AudioTrack(it.id, "vlc-audio-${it.id}", it.name, isSelected = player.audioTrack == it.id) }
        override fun getSubtitleTracks() = (if (closed.get()) null else player.spuTracks).orEmpty().filter { it.id >= 0 }.map { SubtitleTrack(it.id, "vlc-sub-${it.id}", it.name, isSelected = player.spuTrack == it.id) }
        override fun applyAudioLanguagePreferences(languages: List<String>) {
            val track = getAudioTracks().firstOrNull { entry -> languages.any { entry.label.contains(it, true) } }
            track?.let { selectAudioTrack(it.index) }
        }
        override fun selectAudioTrack(index: Int) { if (!closed.get()) player.setAudioTrack(index) }
        override fun selectSubtitleTrack(index: Int) { if (!closed.get()) player.setSpuTrack(index) }
        override fun setSubtitleUri(url: String) { if (!closed.get()) player.addSlave(IMedia.Slave.Type.Subtitle, Uri.parse(url), true) }
        override fun clearExternalSubtitle() { if (!closed.get()) player.setSpuTrack(-1) }
        override fun clearExternalSubtitleAndSelect(trackIndex: Int) = selectSubtitleTrack(trackIndex)
        override fun setSubtitleDelayMs(delayMs: Int) { if (!closed.get()) player.setSpuDelay(delayMs.toLong() * 1000) }
        override val supportsAudioDelay = true
        override fun setAudioDelayMs(delayMs: Int) { if (!closed.get()) player.setAudioDelay(delayMs.toLong() * 1000) }
    }

    fun release() {
        if (!closed.compareAndSet(false, true)) return
        player.setEventListener(null)
        player.detachViews()
        // Native stop/release can wait for network I/O; never block Compose/input dispatch.
        vlcReleaseScope.launch {
            try { player.stop() } finally {
                try { player.release() } finally { descriptor?.close(); lib.release() }
            }
        }
    }
}

private tailrec fun Context.vlcActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.vlcActivity()
    else -> null
}
