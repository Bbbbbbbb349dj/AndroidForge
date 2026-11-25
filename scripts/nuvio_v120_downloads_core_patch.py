#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 11: Downloads core (Sections 9 / 10 / 15).

  Sec 15 — concurrency:
    * `DownloadConcurrencyLimit.MAX_VALUE` 5 -> 16 with an `UNLIMITED` sentinel.
    * Settings chooser offers 1..16 + Unlimited.
    * OkHttp `Dispatcher(maxRequests=64, maxRequestsPerHost=32)` on the download client.
    * Foreground in-process pool bypasses JobScheduler's ~5 user-initiated job cap.

  Sec 10 — resume correctness:
    * `replaceExistingDownload()` no longer deletes the `.part` of an ACTIVE download.
    * HLS segment checkpoint/append resume (`download-checkpoints/<file>.hls`).
    * Progress updates preserve the last known `totalBytes` instead of dropping to null.
    * `DownloadSpeedTracker` becomes a process-wide singleton.
    * `observeInputs()` debounces transient `transportState` flickers (2.5s settle).

  Sec 9 — notifications:
    * One unified notification slot per item (legacy `inactive:` slot cleaned up).
    * Subtitle gains provider • SUB/DUB/DUAL • speed • percent while downloading.
    * Pause / Resume / Cancel actions.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return  # already applied
        raise RuntimeError(f"[v1.20 downloads] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 downloads] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_models(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsModels.kt"
    _replace_once(
        path,
        """    fun clamp(value: Int): Int = value.coerceIn(1, MAX_VALUE)

    companion object {
        const val MAX_VALUE = 5
    }""",
        """    fun clamp(value: Int): Int =
        if (value == UNLIMITED) UNLIMITED else value.coerceIn(1, MAX_VALUE)

    companion object {
        const val MAX_VALUE = 16

        /** Sentinel accepted by [clamp] meaning "no cap". */
        const val UNLIMITED = Int.MAX_VALUE
    }""",
        "concurrency range 1..16 + Unlimited",
    )


def _patch_settings_page(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/settings/DownloadsSettingsPage.kt"
    _replace_once(
        path,
        """            options = (1..DownloadConcurrencyLimit.MAX_VALUE).toList(),
            selected = value,
            label = formatCount,""",
        """            options = (1..DownloadConcurrencyLimit.MAX_VALUE).toList() + DownloadConcurrencyLimit.UNLIMITED,
            selected = value,
            label = { count ->
                if (count == DownloadConcurrencyLimit.UNLIMITED) "Unlimited" else formatCount(count)
            },""",
        "unlimited option in chooser",
    )


def _patch_transfer(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/AndroidDownloadTransfer.kt"
    _replace_once(
        path,
        """    .followRedirects(true)
    .followSslRedirects(true)
    .build()""",
        """    .followRedirects(true)
    .followSslRedirects(true)
    .dispatcher(okhttp3.Dispatcher().apply {
        maxRequests = 64
        maxRequestsPerHost = 32
    })
    .build()""",
        "okhttp dispatcher 64/32",
    )

    _replace_once(
        path,
        """    onHeaders(null, null)
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
}""",
        """    // Nuvio Enhanced: segment checkpoint so an interrupted HLS transfer resumes
    // instead of restarting from byte zero.
    val checkpointFile = DownloadsLiveStatusPlatform.checkpointFile("${item.fileName}.hls")
    var checkpointBytes = 0L
    var startSegmentIndex = 0
    val savedCheckpoint = checkpointFile?.takeIf { it.isFile }?.readText()?.split('\\n')
    if (savedCheckpoint != null && savedCheckpoint.size == 3 && savedCheckpoint[0] == playlistUrl) {
        startSegmentIndex = savedCheckpoint[1].toIntOrNull()?.coerceIn(0, segments.size) ?: 0
        checkpointBytes = savedCheckpoint[2].toLongOrNull() ?: 0L
    }
    val canResume = checkpointBytes > 0 && startSegmentIndex > 0 && sink.length() == checkpointBytes
    if (!canResume) {
        checkpointBytes = 0L
        startSegmentIndex = 0
        checkpointFile?.delete()
    }

    onHeaders(null, null)
    var downloadedBytes = checkpointBytes
    onProgress(downloadedBytes, null)

    sink.open(append = canResume).use { output ->
        if (initSegment != null && !canResume) {
            val initRaw = fetchBytesWithRetry(initSegment.url, initSegment.byteRange)
            val initPlain = decryptIfNeeded(initRaw, initSegment)
            output.write(initPlain)
            downloadedBytes += initPlain.size
            onProgress(downloadedBytes, null)
        }

        val totalCount = segments.size
        segments.forEachIndexed { idx, segment ->
            if (idx < startSegmentIndex) return@forEachIndexed
            kotlinx.coroutines.currentCoroutineContext().ensureActive()
            val rawBytes = fetchBytesWithRetry(segment.url, segment.byteRange)
            val clearBytes = decryptIfNeeded(rawBytes, segment)
            output.write(clearBytes)
            downloadedBytes += clearBytes.size
            val completed = idx + 1
            runCatching { checkpointFile?.writeText("$playlistUrl\\n$completed\\n$downloadedBytes") }
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
    checkpointFile?.delete()
    onHeaders(downloadedBytes, null)
    onProgress(downloadedBytes, downloadedBytes)
}""",
        "hls checkpoint resume",
    )


def _patch_scheduler(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/AndroidDownloadScheduler.kt"
    _replace_once(
        path,
        """import android.app.job.JobScheduler""",
        """import android.app.job.JobScheduler
import kotlinx.coroutines.Job""",
        "scheduler Job import",
    )
    _replace_once(
        path,
        """    private val cleanupScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
""",
        """    private val cleanupScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    // Nuvio Enhanced: in-process foreground pool used when JobScheduler's user-initiated
    // quota (about 5 jobs on many devices) refuses to schedule another transfer, so total
    // download concurrency can reach DownloadConcurrencyLimit.MAX_VALUE (16).
    private val foregroundScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val foregroundSlots = java.util.concurrent.Semaphore(16)
    private val foregroundRuns = ConcurrentHashMap<String, Job>()
""",
        "foreground pool members",
    )
    _replace_once(
        path,
        """        } catch (error: Exception) {
            if (Build.VERSION.SDK_INT >= 34) {
                store.update(item.fileName, transfer.generation) {
                    it.copy(item = it.item.copy(status = DownloadStatus.Queued, errorMessage = null))
                }
                cancelScheduled(transfer)
                Log.w(TAG, "Download is queued until the app returns to foreground", error)
            } else {
                fail(transfer, error)
            }
        }
        return store.get(item.fileName) ?: transfer
    }
""",
        """        } catch (error: Exception) {
            if (Build.VERSION.SDK_INT >= 34) {
                // Nuvio Enhanced: bypass the user-initiated job quota with the foreground pool.
                Log.w(TAG, "JobScheduler refused the download job; running in the foreground pool", error)
                launchInForegroundPool(transfer)
            } else {
                fail(transfer, error)
            }
        }
        return store.get(item.fileName) ?: transfer
    }

    private fun launchInForegroundPool(transfer: AndroidDownloadTransfer) {
        val fileName = transfer.item.fileName
        foregroundRuns[fileName]?.takeIf { it.isActive }?.let { return }
        val run = foregroundScope.launch {
            foregroundSlots.acquire()
            try {
                if (!isActive(transfer)) return@launch
                DownloadsLiveStatusPlatform.initialize(context)
                val retry = execute(transfer, onProgress = { updated ->
                    DownloadsLiveStatusPlatform.notifyTransfer(updated.item)
                })
                notifyCurrent(fileName)
                if (retry) {
                    runCatching { reschedule(fileName) }.onFailure { error ->
                        Log.w(TAG, "Foreground reschedule failed for $fileName", error)
                    }
                }
            } finally {
                foregroundSlots.release()
            }
        }
        foregroundRuns[fileName] = run
        run.invokeOnCompletion { foregroundRuns.remove(fileName, run) }
    }
""",
        "foreground pool fallback",
    )


def _patch_repository(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadsRepository.kt"
    _replace_once(
        path,
        """    private fun replaceExistingDownload(logicalKey: String): DownloadItem? {
        val existing = _uiState.value.items.firstOrNull { it.logicalContentKey == logicalKey } ?: return null
        dropHandle(existing.id)?.cancel()
        DownloadsPlatformDownloader.removeFile(playableLocalFileUri(existing) ?: existing.localFileUri)
        DownloadsPlatformDownloader.removePartialFile(existing.fileName)
        return existing
    }""",
        """    private fun replaceExistingDownload(logicalKey: String): DownloadItem? {
        val existing = _uiState.value.items.firstOrNull { it.logicalContentKey == logicalKey } ?: return null
        dropHandle(existing.id)?.cancel()
        // Nuvio Enhanced: never delete the partial file of an ACTIVE download — the
        // replacement transfer resumes from it instead of starting from zero.
        if (!existing.isActive) {
            DownloadsPlatformDownloader.removeFile(playableLocalFileUri(existing) ?: existing.localFileUri)
            DownloadsPlatformDownloader.removePartialFile(existing.fileName)
        }
        return existing
    }""",
        "active .part guard",
    )
    _replace_once(
        path,
        """                            current.copy(
                                downloadedBytes = downloadedBytes.coerceAtLeast(0L),
                                totalBytes = totalBytes?.takeIf { it > 0L },
                                updatedAtEpochMs = DownloadsClock.nowEpochMs(),
                                errorMessage = null,
                            )""",
        """                            current.copy(
                                downloadedBytes = downloadedBytes.coerceAtLeast(0L),
                                totalBytes = totalBytes?.takeIf { it > 0L } ?: current.totalBytes,
                                updatedAtEpochMs = DownloadsClock.nowEpochMs(),
                                errorMessage = null,
                            )""",
        "preserve last totalBytes",
    )
    _replace_once(
        path,
        """            .distinctUntilChanged()
            .onEach { (_, allowMobile, networkAllowed) ->
                if (!hasLoaded) return@onEach
                // Running transfers keep the network rule they started with, so restart them when it
                // changes. Where a restart loses progress (iOS), only do so when the rule gets stricter.
                val ruleChanged = lastAllowMobile != null && lastAllowMobile != allowMobile
                val becameWifiOnly = lastAllowMobile == true && !allowMobile
                lastAllowMobile = allowMobile
                if (!networkAllowed || becameWifiOnly || (ruleChanged && DownloadsPlatformDownloader.restartKeepsProgress)) {""",
        """            .distinctUntilChanged()
            .onEach { (_, allowMobile, networkAllowed) ->
                if (!hasLoaded) return@onEach
                // Nuvio Enhanced: transient transportState flickers must not queue running
                // transfers — only act on a denial that still holds after the settle window.
                val networkDenied = if (!networkAllowed) {
                    kotlinx.coroutines.delay(2_500L)
                    !isDownloadNetworkAllowed()
                } else {
                    false
                }
                // Running transfers keep the network rule they started with, so restart them when it
                // changes. Where a restart loses progress (iOS), only do so when the rule gets stricter.
                val ruleChanged = lastAllowMobile != null && lastAllowMobile != allowMobile
                val becameWifiOnly = lastAllowMobile == true && !allowMobile
                lastAllowMobile = allowMobile
                if (networkDenied || becameWifiOnly || (ruleChanged && DownloadsPlatformDownloader.restartKeepsProgress)) {""",
        "transport flicker debounce",
    )


def _patch_speeds(root: Path) -> None:
    path = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/downloads/DownloadSpeeds.kt"
    _replace_once(
        path,
        """@Composable
internal fun rememberDownloadSpeeds(items: List<DownloadItem>): Map<String, Long> {
    val tracker = remember { DownloadSpeedTracker() }
    LaunchedEffect(items) {
        tracker.update(items)
    }
    return tracker.speeds
}""",
        """// Nuvio Enhanced: one process-wide tracker so speeds survive recomposition and
// screen changes instead of restarting from scratch in every fresh `remember`.
private val sharedDownloadSpeedTracker = DownloadSpeedTracker()

@Composable
internal fun rememberDownloadSpeeds(items: List<DownloadItem>): Map<String, Long> {
    val tracker = sharedDownloadSpeedTracker
    LaunchedEffect(items) {
        tracker.update(items)
    }
    return tracker.speeds
}""",
        "singleton speed tracker",
    )


def _patch_notifications(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/DownloadsLiveStatusPlatform.android.kt"
    _replace_once(
        path,
        """    internal fun notifyTransfer(item: DownloadItem) {
        val context = appContext ?: return
        if (!canPostNotifications(context)) return
        val manager = NotificationManagerCompat.from(context)
        if (item.status == DownloadStatus.Completed) {
            removeNotification(item.id)
        } else {
            val active = item.status == DownloadStatus.Downloading
            manager.cancel(notificationId(if (active) "inactive:${item.id}" else item.id))
            manager.notify(notificationId(if (active) item.id else "inactive:${item.id}"), buildNotification(context, item))
        }
    }""",
        """    internal fun notifyTransfer(item: DownloadItem) {
        val context = appContext ?: return
        if (!canPostNotifications(context)) return
        val manager = NotificationManagerCompat.from(context)
        if (item.status == DownloadStatus.Completed) {
            removeNotification(item.id)
        } else {
            // Nuvio Enhanced: one unified notification slot per item; drop the legacy slot.
            manager.cancel(notificationId("inactive:${item.id}"))
            manager.notify(notificationId(item.id), buildNotification(context, item))
        }
    }

    internal fun checkpointFile(name: String): java.io.File? {
        val base = appContext?.filesDir ?: return null
        if (name.isBlank() || name.contains('/') || name.contains('\\\\')) return null
        val dir = java.io.File(base, "download-checkpoints")
        if (!dir.isDirectory) dir.mkdirs()
        return java.io.File(dir, name)
    }

    private val speedSamples = java.util.concurrent.ConcurrentHashMap<String, LongArray>()

    private fun currentSpeedBytesPerSec(item: DownloadItem): Long? {
        val now = System.currentTimeMillis()
        val sample = speedSamples.compute(item.id) { _, previous ->
            if (previous == null) {
                longArrayOf(item.downloadedBytes, now, 0L)
            } else {
                val elapsedMs = now - previous[1]
                val deltaBytes = item.downloadedBytes - previous[0]
                val ema = if (elapsedMs in 1..60_000L && deltaBytes >= 0L) {
                    val instant = deltaBytes * 1_000L / elapsedMs
                    if (previous[2] == 0L) instant else (previous[2] * 7L + instant * 3L) / 10L
                } else {
                    previous[2]
                }
                longArrayOf(item.downloadedBytes, now, ema)
            }
        } ?: return null
        return sample[2].takeIf { it > 0L }
    }""",
        "unified notify + checkpoint helper + speed",
    )
    _replace_once(
        path,
        """                    .addAction(
                        0,
                        runBlocking { getString(Res.string.compose_action_pause) },
                        buildActionPendingIntent(
                            context = context,
                            action = DownloadsNotificationActionReceiver.actionPause,
                            downloadId = item.id,
                            fileName = item.fileName,
                        ),
                    )
""",
        """                    .addAction(
                        0,
                        runBlocking { getString(Res.string.compose_action_pause) },
                        buildActionPendingIntent(
                            context = context,
                            action = DownloadsNotificationActionReceiver.actionPause,
                            downloadId = item.id,
                            fileName = item.fileName,
                        ),
                    )
                    .addAction(
                        0,
                        runBlocking { getString(Res.string.action_cancel) },
                        buildActionPendingIntent(
                            context = context,
                            action = DownloadsNotificationActionReceiver.actionCancel,
                            downloadId = item.id,
                            fileName = item.fileName,
                        ),
                    )
""",
        "cancel action",
    )
    _replace_once(
        path,
        """            DownloadStatus.Downloading -> {
                val downloaded = formatBytes(item.downloadedBytes)
                val total = item.totalBytes?.let(::formatBytes)
                if (total != null) {
                    runBlocking { getString(Res.string.downloads_live_downloading_with_total, detail, downloaded, total) }
                } else {
                    runBlocking { getString(Res.string.downloads_live_downloading, detail, downloaded) }
                }
            }""",
        """            DownloadStatus.Downloading -> {
                val downloaded = formatBytes(item.downloadedBytes)
                val total = item.totalBytes?.let(::formatBytes)
                val base = if (total != null) {
                    runBlocking { getString(Res.string.downloads_live_downloading_with_total, detail, downloaded, total) }
                } else {
                    runBlocking { getString(Res.string.downloads_live_downloading, detail, downloaded) }
                }
                val extras = buildList {
                    item.providerName.takeIf { it.isNotBlank() }?.let(::add)
                    item.audioVariant?.let(::add)
                    currentSpeedBytesPerSec(item)?.let { add("${formatBytes(it)}/s") }
                    progressPercent(item).takeIf { it >= 0 }?.let { add("$it%") }
                }
                if (extras.isEmpty()) base else "$base \\u2022 ${extras.joinToString(" \\u2022 ")}"
            }""",
        "rich downloading subtitle",
    )


def _patch_action_receiver(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/downloads/DownloadsNotificationActionReceiver.kt"
    _replace_once(
        path,
        """        val action = intent?.action ?: return
        val downloadId = intent.getStringExtra(extraDownloadId)?.trim().orEmpty()
        if (downloadId.isBlank()) return
""",
        """        val action = intent?.action ?: return
        val downloadId = intent.getStringExtra(extraDownloadId)?.trim().orEmpty()
        if (downloadId.isBlank()) return
        if (action == actionCancel) {
            DownloadsRepository.cancelDownload(downloadId)
            return
        }
""",
        "cancel action handling",
    )
    _replace_once(
        path,
        """        const val actionPause = "com.nuvio.app.downloads.action.PAUSE"
        const val actionResume = "com.nuvio.app.downloads.action.RESUME\"""",
        """        const val actionPause = "com.nuvio.app.downloads.action.PAUSE"
        const val actionResume = "com.nuvio.app.downloads.action.RESUME"
        const val actionCancel = "com.nuvio.app.downloads.action.CANCEL\"""",
        "cancel action constant",
    )


def apply_v120_downloads_core_patch(source_dir: Path) -> None:
    _patch_models(source_dir)
    _patch_settings_page(source_dir)
    _patch_transfer(source_dir)
    _patch_scheduler(source_dir)
    _patch_repository(source_dir)
    _patch_speeds(source_dir)
    _patch_notifications(source_dir)
    _patch_action_receiver(source_dir)
    print("[v1.20-module-12] Downloads: 16+Unlimited concurrency, foreground pool, HLS resume & rich notifications applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_downloads_core_patch.py <source_dir>")
    apply_v120_downloads_core_patch(Path(sys.argv[1]).resolve())
