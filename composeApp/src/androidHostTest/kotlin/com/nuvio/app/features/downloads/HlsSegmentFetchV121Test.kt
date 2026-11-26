package com.nuvio.app.features.downloads

import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.*
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.*
import kotlin.test.*

class HlsSegmentFetchV121Test {
    @Test fun parallelRequestsReturnInCallerOrder(): Unit = runBlocking {
        MockWebServer().use { server ->
            val arrived = CountDownLatch(4)
            server.dispatcher = object : Dispatcher() {
                override fun dispatch(request: RecordedRequest): MockResponse {
                    arrived.countDown()
                    check(arrived.await(5, TimeUnit.SECONDS)) { "Segments were fetched serially" }
                    return MockResponse().setBody(request.path.orEmpty())
                }
            }
            val client = OkHttpClient()
            val results = (0..3).map { index -> async {
                fetchHlsSegment(client, Request.Builder().url(server.url("/$index")).build(), null).decodeToString()
            } }.awaitAll()
            assertEquals(listOf("/0", "/1", "/2", "/3"), results)
        }
    }

    @Test fun ignoredByteRangeIsRejectedInsteadOfCorruptingVideo(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setBody("whole file"))
            assertFailsWith<IOException> {
                fetchHlsSegment(OkHttpClient(), Request.Builder().url(server.url("/range")).build(), 0L to 3L)
            }
        }
    }

    @Test fun validRangeIsAcceptedAndHugeSegmentsAreRejected(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setResponseCode(206).setHeader("Content-Range", "bytes 0-3/10").setBody("data"))
            val request = Request.Builder().url(server.url("/range")).build()
            assertEquals("data", fetchHlsSegment(OkHttpClient(), request, 0L to 3L).decodeToString())
            server.enqueue(MockResponse().setBody("x").setHeader("Content-Length", "40000000"))
            assertFailsWith<IOException> { fetchHlsSegment(OkHttpClient(), request, null) }
        }
    }

    @Test fun cancellingAnInFlightSegmentDoesNotWaitForTheReadTimeout(): Unit = runBlocking {
        MockWebServer().use { server ->
            server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
            val request = Request.Builder().url(server.url("/slow")).build()
            val job = launch { fetchHlsSegment(OkHttpClient(), request, null) }
            withContext(Dispatchers.IO) { assertNotNull(server.takeRequest(5, TimeUnit.SECONDS)) }
            withTimeout(2_000) { job.cancelAndJoin() }
            assertTrue(job.isCancelled)
        }
    }
}
