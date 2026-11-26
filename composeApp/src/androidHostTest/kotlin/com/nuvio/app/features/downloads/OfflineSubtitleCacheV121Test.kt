package com.nuvio.app.features.downloads

import java.io.File
import java.net.URI
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Rule
import org.junit.rules.TemporaryFolder
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import kotlin.test.Test
import kotlin.test.assertEquals

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class OfflineSubtitleCacheV121Test {
    @get:Rule val temporary = TemporaryFolder()

    @Test
    fun manuallySelectedSubtitleIsSavedOnceAndReusedWithoutNetwork(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody(srt))
            val video = temporary.newFile("manual.mkv").toURI().toString()
            val subtitle = com.nuvio.app.features.player.AddonSubtitle(
                "forced", server.url("/en.srt").toString(), "en", "English forced",
            )
            val first = DownloadSubtitles.cacheSelected(video, subtitle)
            val second = DownloadSubtitles.cacheSelected(video, subtitle)
            assertEquals(first, second)
            assertEquals(1, server.requestCount)
            assertEquals(srt, File(URI(first)).readText())
            assertEquals(1, DownloadSubtitles.localSubtitles(video).size)
        }
    }

    private val srt = "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
}
