#!/usr/bin/env python3
"""Nuvio Enhanced v1.20 — Module 6: Software Codec & Engine Escalation (Section 2).

  - `SoftwareVideoDecoder` gains AV1/VP9 candidate names (`dav1d` then `av1`, `vp9`)
    with a try-until-open loop, so exotic streams can decode in software.
  - HEVC Main 10 (profile idc 2) is now handled by the software renderer path
    (previously only Format Extensions profile 4 was, leaving Main10 devices stranded).
  - `activeEngine` auto-escalates ExoPlayer -> Libmpv (once per source) when the
    engine preference is Auto and the ExoPlayer surface reports an error.
"""
from __future__ import annotations

from pathlib import Path


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 codec] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 codec] Ambiguous anchor ({count} matches) for {label} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_decoder(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/swdecoder/SoftwareVideoDecoder.kt"
    _replace_once(
        path,
        """    init {
        val name = codecNameFor(format.sampleMimeType)
        handle = if (name != null && isAvailable) nativeCreate(name, extraData(format), threads) else 0L
        if (handle == 0L) {
            release()
            throw SoftwareVideoDecoderException("Failed to initialize software decoder for ${format.sampleMimeType}")
        }
        codecName = name!!
""",
        """    init {
        val names = codecNamesFor(format.sampleMimeType)
        var chosenName: String? = null
        handle = if (isAvailable && names.isNotEmpty()) {
            val extra = extraData(format)
            names.firstNotNullOfOrNull { candidate ->
                val created = nativeCreate(candidate, extra, threads)
                if (created != 0L) {
                    chosenName = candidate
                    created
                } else {
                    null
                }
            } ?: 0L
        } else {
            0L
        }
        if (handle == 0L) {
            release()
            throw SoftwareVideoDecoderException(
                "Failed to initialize software decoder for ${format.sampleMimeType} (tried ${names.joinToString()})",
            )
        }
        codecName = requireNotNull(chosenName)
""",
        "decoder init candidate loop",
    )
    _replace_once(
        path,
        """        private val HIGH_BIT_DEPTH_AVC_PROFILES = setOf(44, 110, 122, 244)
        private const val HEVC_PROFILE_RANGE_EXTENSIONS = 4""",
        """        private val HIGH_BIT_DEPTH_AVC_PROFILES = setOf(44, 110, 122, 244)
        private const val HEVC_PROFILE_RANGE_EXTENSIONS = 4
        private const val HEVC_PROFILE_MAIN_10 = 2""",
        "Main10 profile const",
    )
    _replace_once(
        path,
        """        fun codecNameFor(mimeType: String?): String? =
            when (mimeType) {
                MimeTypes.VIDEO_H264 -> "h264"
                MimeTypes.VIDEO_H265 -> "hevc"
                MimeTypes.VIDEO_VC1 -> "vc1"
                else -> null
            }

        fun needsSoftwareDecoding(format: Format): Boolean =
            when (format.sampleMimeType) {
                MimeTypes.VIDEO_H264 -> avcProfile(format) in HIGH_BIT_DEPTH_AVC_PROFILES
                MimeTypes.VIDEO_H265 -> hevcProfile(format) == HEVC_PROFILE_RANGE_EXTENSIONS
                MimeTypes.VIDEO_VC1 -> true
                else -> false
            }""",
        """        /** Candidate FFmpeg decoder names, tried in order until one opens successfully. */
        fun codecNamesFor(mimeType: String?): List<String> =
            when (mimeType) {
                MimeTypes.VIDEO_H264 -> listOf("h264")
                MimeTypes.VIDEO_H265 -> listOf("hevc")
                MimeTypes.VIDEO_VC1 -> listOf("vc1")
                MimeTypes.VIDEO_VP9 -> listOf("vp9")
                MimeTypes.VIDEO_AV1 -> listOf("dav1d", "av1")
                else -> emptyList()
            }

        fun codecNameFor(mimeType: String?): String? = codecNamesFor(mimeType).firstOrNull()

        fun needsSoftwareDecoding(format: Format): Boolean =
            when (format.sampleMimeType) {
                MimeTypes.VIDEO_H264 -> avcProfile(format) in HIGH_BIT_DEPTH_AVC_PROFILES
                MimeTypes.VIDEO_H265 ->
                    hevcProfile(format) == HEVC_PROFILE_RANGE_EXTENSIONS ||
                        hevcProfile(format) == HEVC_PROFILE_MAIN_10
                MimeTypes.VIDEO_VC1 -> true
                else -> false
            }""",
        "codec name candidates + Main10 handling",
    )


def _patch_renderer(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/swdecoder/SoftwareVideoRenderer.kt"
    _replace_once(
        path,
        """        if (SoftwareVideoDecoder.codecNameFor(format.sampleMimeType) == null) {
            return RendererCapabilities.create(C.FORMAT_UNSUPPORTED_TYPE)
        }""",
        """        if (SoftwareVideoDecoder.codecNamesFor(format.sampleMimeType).isEmpty()) {
            return RendererCapabilities.create(C.FORMAT_UNSUPPORTED_TYPE)
        }""",
        "renderer capability gate via codec list",
    )


def _patch_engine_escalation(root: Path) -> None:
    path = root / "composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlayerEngine.android.kt"
    _replace_once(
        path,
        """    val surfaceOnError: (String?) -> Unit = { message ->
        if (message == null || castBridge?.isCasting != true) onError(message)
    }

    val requestedEngine = playbackEngine ?: playerSettings.androidPlaybackEngine
    val activeEngine by remember(playerSourceKey, requestedEngine) {
        mutableStateOf(requestedEngine.initialAndroidEngine())
    }
""",
        """    val requestedEngine = playbackEngine ?: playerSettings.androidPlaybackEngine
    var activeEngine by remember(playerSourceKey, requestedEngine) {
        mutableStateOf(requestedEngine.initialAndroidEngine())
    }
    var engineAutoEscalated by remember(playerSourceKey, requestedEngine) { mutableStateOf(false) }
    val surfaceOnError: (String?) -> Unit = { message ->
        // Nuvio Enhanced: with the engine preference on Auto, a genuine CODEC/DECODER
        // failure escalates ExoPlayer -> Libmpv exactly once per source. Link/HTTP/network
        // errors must NOT escalate — the runtime's link-refresh path handles those first,
        // and escalating them doubled load times (e.g. CloudStream expired links).
        val looksLikeCodecFailure = message != null &&
            Regex(
                "decod|codec|renderer|MediaCodec|OMX|c2\\\\.|unsupported (video|audio|mime)|video format|format not supported",
                RegexOption.IGNORE_CASE,
            ).containsMatchIn(message)
        if (
            looksLikeCodecFailure &&
            activeEngine == ResolvedAndroidPlaybackEngine.ExoPlayer &&
            requestedEngine == AndroidPlaybackEngine.Auto &&
            !engineAutoEscalated &&
            castBridge?.isCasting != true
        ) {
            engineAutoEscalated = true
            InAppLogger.warn(
                "Player/Android",
                "auto-escalating engine ExoPlayer -> Libmpv after error: ${message.take(200)}",
            )
            activeEngine = ResolvedAndroidPlaybackEngine.Libmpv
        } else if (message == null || castBridge?.isCasting != true) {
            onError(message)
        }
    }
""",
        "auto engine escalation",
    )


def apply_v120_player_codec_patch(source_dir: Path) -> None:
    _patch_decoder(source_dir)
    _patch_renderer(source_dir)
    _patch_engine_escalation(source_dir)
    print("[v1.20-module-7] SW codec candidates, HEVC Main10, and engine auto-escalation applied cleanly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/nuvio_v120_player_codec_patch.py <source_dir>")
    apply_v120_player_codec_patch(Path(sys.argv[1]).resolve())
