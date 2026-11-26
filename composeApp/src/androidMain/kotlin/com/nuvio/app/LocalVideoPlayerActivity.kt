package com.nuvio.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.nuvio.app.core.ui.NuvioSheetBackdrop
import com.nuvio.app.core.ui.NuvioSheetBackdropHost
import com.nuvio.app.core.ui.NuvioToastController
import com.nuvio.app.core.ui.glass.rememberNuvioBackdrop
import com.nuvio.app.features.downloads.DownloadSubtitles
import com.nuvio.app.features.downloads.LocalEpisodePlaylistRegistry
import com.nuvio.app.features.downloads.LocalFolderVideosPlatform
import com.nuvio.app.features.downloads.LocalMediaParser
import com.nuvio.app.features.downloads.LocalPlaylistEpisode
import com.nuvio.app.features.player.ExternalPlayerPlatform
import com.nuvio.app.features.player.PlayerScreen
import com.nuvio.app.features.profiles.ProfileRepository
import com.nuvio.app.features.watchprogress.WatchProgressRepository
import java.io.File

class LocalVideoPlayerActivity : MainActivity() {
    private var activeIntent by mutableStateOf<Intent?>(null)
    private var intentNonce by mutableLongStateOf(0L)

    override fun onCreate(savedInstanceState: Bundle?) {
        LocalFolderVideosPlatform.initialize(applicationContext)
        activeIntent = intent
        intentNonce += 1L
        super.onCreate(savedInstanceState)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        activeIntent = intent
        intentNonce += 1L
    }

    override fun showContent() {
        setContent {
            val currentIntent = activeIntent
            val currentNonce = intentNonce
            val resolved = remember(currentIntent, currentNonce) {
                extractPlayableVideo(currentIntent)
            }
            if (resolved == null) {
                NuvioToastController.show("Unable to open selected video file")
                finish()
                return@setContent
            }

            val sheetBackdropSource = rememberNuvioBackdrop()
            val sheetBackdrop = remember(sheetBackdropSource) { NuvioSheetBackdrop(sheetBackdropSource) }

            NuvioSheetBackdropHost(sheetBackdrop = sheetBackdrop) {
                AppEnvironment(drawAppBackground = false) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color.Black),
                    ) {
                        key(currentNonce, resolved.uriString) {
                            PlayerScreen(
                                profileId = ProfileRepository.activeProfileId,
                                title = resolved.title,
                                sourceUrl = resolved.uriString,
                                externalSubtitles = DownloadSubtitles.localSubtitles(resolved.uriString),
                                streamType = resolved.cleanMimeType,
                                providerName = "Local Storage",
                                streamTitle = resolved.displayName,
                                streamSubtitle = "Local Storage",
                                onBack = { finish() },
                                onOpenInExternalPlayer = { request ->
                                    ExternalPlayerPlatform.open(request, null)
                                },
                                seasonNumber = resolved.seasonNumber,
                                episodeNumber = resolved.episodeNumber,
                                episodeTitle = resolved.episodeTitle,
                                contentType = resolved.contentType,
                                videoId = resolved.syntheticId,
                                parentMetaId = resolved.parentMetaId,
                                parentMetaType = resolved.contentType,
                                initialPositionMs = resolved.resumePositionMs,
                                initialProgressFraction = resolved.resumeFraction,
                                sourceFilename = resolved.displayName,
                            )
                        }
                    }
                }
            }
        }
        contentReady = true
    }

    private data class ResolvedExternalVideo(
        val uriString: String,
        val displayName: String,
        val title: String,
        val cleanMimeType: String?,
        val contentType: String,
        val seasonNumber: Int?,
        val episodeNumber: Int?,
        val episodeTitle: String?,
        val syntheticId: String,
        val parentMetaId: String,
        val resumePositionMs: Long,
        val resumeFraction: Float?,
    )

    private fun extractPlayableVideo(intent: Intent?): ResolvedExternalVideo? {
        if (intent == null) return null
        val uri: Uri = when (intent.action) {
            Intent.ACTION_SEND -> {
                @Suppress("DEPRECATION")
                (intent.getParcelableExtra(Intent.EXTRA_STREAM) as? Uri)
                    ?: intent.clipData?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.uri
                    ?: intent.data
            }
            else -> {
                intent.data
                    ?: intent.clipData?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.uri
            }
        } ?: return null

        val scheme = uri.scheme?.lowercase() ?: return null
        if (scheme != "content" && scheme != "file") return null

        if (scheme == "content" && (intent.flags and Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION) != 0) {
            runCatching {
                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
        }

        val displayName = LocalFolderVideosPlatform.resolveDisplayName(applicationContext, uri)
        val rawMime = intent.type?.trim()?.takeIf { it.isNotEmpty() && !it.endsWith("/*") }
            ?: runCatching { contentResolver.getType(uri)?.trim() }.getOrNull()
                ?.takeIf { it.isNotEmpty() && !it.endsWith("/*") && it != "application/octet-stream" }

        val uriString = uri.toString()
        val parentDirFile = if (scheme == "file") uri.path?.let(::File)?.parentFile else null
        val parsed = LocalMediaParser.parse(
            filename = displayName,
            parentFolderName = parentDirFile?.name,
            grandParentFolderName = parentDirFile?.parentFile?.name,
        )
        val syntheticId = "local:${uriString.hashCode().toUInt().toString(16)}"

        // Check scanned Local Storage Folders first, or scan sibling files when opened via file://
        val scannedVideos = LocalFolderVideosPlatform.state.value.videos
        val matchedScanned = scannedVideos.firstOrNull { it.uri == uriString || it.filename.equals(displayName, ignoreCase = true) }
        val seriesParentMetaId = when {
            matchedScanned != null && matchedScanned.isSeries -> {
                val (groups, _) = LocalMediaParser.groupVideos(scannedVideos)
                val grp = groups.firstOrNull { g -> g.episodes.any { it.uri == matchedScanned.uri } }
                if (grp != null) {
                    LocalEpisodePlaylistRegistry.registerFromItems(matchedScanned.effectiveParentMetaId, grp.episodes)
                }
                matchedScanned.effectiveParentMetaId
            }
            parsed.isSeries && parentDirFile != null && parentDirFile.isDirectory -> {
                val pId = "local_series:${LocalMediaParser.canonicalSeriesKey(parsed.cleanTitle)}"
                val videoExts = setOf("mp4", "mkv", "avi", "webm", "mov", "m4v", "ts", "m2ts", "flv", "wmv", "mpg", "mpeg")
                val siblings = parentDirFile.listFiles()
                    .orEmpty()
                    .filter { f -> f.isFile && f.extension.lowercase() in videoExts }
                    .mapNotNull { f ->
                        val p = LocalMediaParser.parse(f.name, parentDirFile.name, parentDirFile.parentFile?.name)
                        if (!p.isSeries || p.episodeNumber == null) return@mapNotNull null
                        val fUri = Uri.fromFile(f).toString()
                        LocalPlaylistEpisode(
                            videoId = "local:${fUri.hashCode().toUInt().toString(16)}",
                            uri = fUri,
                            title = p.cleanTitle,
                            filename = f.name,
                            seasonNumber = (p.seasonNumber ?: 1).coerceAtLeast(1),
                            episodeNumber = p.episodeNumber.coerceAtLeast(1),
                            episodeTitle = p.episodeTitle,
                        )
                    }
                if (siblings.size > 1) {
                    LocalEpisodePlaylistRegistry.registerPlaylist(pId, siblings)
                }
                pId
            }
            parsed.isSeries -> "local_series:${LocalMediaParser.canonicalSeriesKey(parsed.cleanTitle)}"
            else -> syntheticId
        }

        val isSeries = parsed.isSeries || (matchedScanned?.isSeries == true)
        val effectiveSeason = matchedScanned?.seasonNumber ?: parsed.seasonNumber ?: (if (isSeries) 1 else null)
        val effectiveEpisode = matchedScanned?.episodeNumber ?: parsed.episodeNumber ?: (if (isSeries) 1 else null)

        WatchProgressRepository.ensureLoaded()
        val resumeEntry = runCatching {
            WatchProgressRepository.progressForVideo(
                videoId = syntheticId,
                parentMetaId = seriesParentMetaId,
                seasonNumber = effectiveSeason,
                episodeNumber = effectiveEpisode,
            )?.takeIf { it.isResumable }
        }.getOrNull()

        return ResolvedExternalVideo(
            uriString = uriString,
            displayName = displayName,
            title = matchedScanned?.title ?: parsed.cleanTitle,
            cleanMimeType = rawMime,
            contentType = if (isSeries) "series" else "movie",
            seasonNumber = effectiveSeason,
            episodeNumber = effectiveEpisode,
            episodeTitle = matchedScanned?.episodeTitle ?: parsed.episodeTitle,
            syntheticId = matchedScanned?.syntheticVideoId ?: syntheticId,
            parentMetaId = seriesParentMetaId,
            resumePositionMs = resumeEntry?.lastPositionMs?.takeIf { it > 0L } ?: 0L,
            resumeFraction = resumeEntry?.progressFraction?.takeIf { it > 0f },
        )
    }
}
