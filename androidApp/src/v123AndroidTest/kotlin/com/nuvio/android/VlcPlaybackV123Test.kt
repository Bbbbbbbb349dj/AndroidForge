package com.nuvio.android

import android.net.Uri
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.Lifecycle
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.nuvio.app.features.player.*
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Real native decoder smoke test. Not a substitute for physical-device/network profiling. */
@RunWith(AndroidJUnit4::class)
class VlcPlaybackV123Test {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    @Test fun embeddedVlcPlaysSeeksPausesAndRecreatesWithoutExternalApp() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val video = File(instrumentation.targetContext.cacheDir, "vlc-v123.mp4")
        instrumentation.context.assets.open("subtitles/video.mp4").use { input -> video.outputStream().use(input::copyTo) }
        val visible = mutableStateOf(true)
        val play = mutableStateOf(true)
        var controller: PlayerEngineController? = null
        var snapshot = PlayerPlaybackSnapshot()
        var error: String? = null
        PlayerSettingsRepository.ensureLoaded()
        try {
            compose.setContent {
                if (visible.value) PlatformPlayerSurface(
                    sourceUrl = Uri.fromFile(video).toString(), modifier = Modifier.fillMaxSize(),
                    playbackEngine = AndroidPlaybackEngine.Vlc, playWhenReady = play.value,
                    onControllerReady = { controller = it }, onSnapshot = { snapshot = it }, onError = { error = it },
                )
            }
            fun awaitPlayback() = compose.waitUntil(45_000) {
                compose.runOnIdle { assertNull(error); snapshot.isPlaying && snapshot.positionMs > 500 && snapshot.videoWidth > 0 }
            }
            awaitPlayback()
            compose.runOnIdle {
                assertEquals(AndroidPlaybackEngine.Vlc, controller!!.playbackEngine)
                assertFalse(controller!!.supportsNightMode)
                controller!!.setPlaybackSpeed(1.25f)
                controller!!.seekTo(4_000)
            }
            compose.waitUntil(15_000) { compose.runOnIdle { snapshot.positionMs >= 4_000 } }
            compose.runOnIdle { play.value = false }
            compose.waitUntil(10_000) { compose.runOnIdle { !snapshot.isPlaying } }
            compose.activityRule.scenario.moveToState(Lifecycle.State.CREATED)
            compose.activityRule.scenario.moveToState(Lifecycle.State.RESUMED)
            compose.runOnIdle { assertFalse(snapshot.isPlaying); play.value = true }
            awaitPlayback()
            compose.runOnIdle { visible.value = false }
            compose.waitForIdle()
            compose.runOnIdle { snapshot = PlayerPlaybackSnapshot(); controller = null; visible.value = true }
            awaitPlayback()
        } finally {
            compose.runOnIdle { visible.value = false }
            video.delete()
        }
    }
}
