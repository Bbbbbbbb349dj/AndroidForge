"""Nuvio Enhanced v1.20 — Player Core v2.

Rebuild of the playback recovery pipeline around the user-reported local-file failure
(``Libgav1VideoRenderer error, ... video/av01, format_supported=YES``):

1. Finite in-engine DECODER LADDER for local/offline files — each decoder-class failure
   re-creates ExoPlayer with the next decoder configuration (OFF <-> PREFER), position
   preserved, before any engine switch or user-visible error.
2. Single orchestration point — the surface only reports; expired-link refresh -> source
   fallback -> codec-gated engine switch -> error all run in PlayerScreenRuntimeUi.
3. Codec-gated engine switch now ALLOWS local files (Libmpv/ffmpeg is the fix for local
   AV1/HEVC decode failures); non-codec errors never reload the engine.
"""

from __future__ import annotations

from pathlib import Path

_ENGINE = "composeApp/src/androidMain/kotlin/com/nuvio/app/features/player/PlayerEngine.android.kt"
_RUNTIME_ACTIONS = (
    "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenRuntimePlaybackActions.kt"
)

_CODEC_REGEX_PY = (
    '"decod|codec|renderer|MediaCodec|OMX|c2\\\\.|libgav1|'
    "unsupported (video|audio|mime)|video format|format not supported\""
)


def _replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"[v1.20 player-core-v2] Missing anchor for {label} in {path}")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[v1.20 player-core-v2] Ambiguous anchor ({count} matches) for {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_decoder_ladder(source_dir: Path) -> None:
    path = source_dir / _ENGINE
    # 1) Retry counter next to the existing override state.
    _replace_once(
        path,
        """    var decoderPriorityOverride by remember(playerSourceKey) { mutableStateOf<Int?>(null) }""",
        """    var decoderPriorityOverride by remember(playerSourceKey) { mutableStateOf<Int?>(null) }
    // Player Core v2: finite decoder ladder — one re-prepare per rung, per source.
    var decoderRetryCount by remember(playerSourceKey) { mutableStateOf(0) }""",
        "decoder retry counter",
    )
    # 2) The ladder itself: local files walk decoder configurations before giving up.
    _replace_once(
        path,
        """        fun reportPlayerError(error: PlaybackException) {
            if (
                playerSettings.decoderPriority == DefaultRenderersFactory.EXTENSION_RENDERER_MODE_ON &&
                effectiveDecoderPriority != DefaultRenderersFactory.EXTENSION_RENDERER_MODE_PREFER &&
                error.isDecoderFailure()
            ) {
                Log.w(
                    TAG,
                    "Decoder failure (${error.errorCodeName}); retrying with app decoders",
                    error,
                )
                InAppLogger.warn(
                    "ExoPlayer/Android",
                    "Decoder failure ${error.errorCodeName}; retrying with preferred app decoders. " +
                        "cause=${error.cause?.let(InAppLogger::throwableSummary) ?: InAppLogger.throwableSummary(error)}",
                )
                fallbackStartPositionMs = exoPlayer.currentPosition.coerceAtLeast(0L)
                decoderPriorityOverride = DefaultRenderersFactory.EXTENSION_RENDERER_MODE_PREFER
                latestOnError.value(null)
                return
            }
            InAppLogger.error(""",
        """        fun reportPlayerError(error: PlaybackException) {
            // Nuvio Enhanced Player Core v2: finite decoder ladder for LOCAL/offline files
            // (streams switch source first at the runtime layer instead). Every decoder-class
            // failure re-creates ExoPlayer with the next decoder configuration, position
            // preserved, before any engine switch or user-visible error:
            //   ON -> OFF  (hardware / framework-software MediaCodec path)
            //   OFF -> PREFER (extension decoders first, e.g. libgav1)
            //   two rungs exhausted -> codec-gated engine switch (runtime) -> clear error.
            val decoderClassFailure = error.isDecoderFailure() ||
                (error.localizedMessage ?: error.message)?.contains(
                    Regex(
                        %s,
                        RegexOption.IGNORE_CASE,
                    ),
                ) == true
            if (isLocalFileSource && decoderRetryCount < 2 && decoderClassFailure) {
                val nextMode = if (effectiveDecoderPriority == DefaultRenderersFactory.EXTENSION_RENDERER_MODE_OFF) {
                    DefaultRenderersFactory.EXTENSION_RENDERER_MODE_PREFER
                } else {
                    DefaultRenderersFactory.EXTENSION_RENDERER_MODE_OFF
                }
                decoderRetryCount++
                Log.w(
                    TAG,
                    "Decoder failure (${error.errorCodeName}); decoder ladder -> mode=$nextMode (attempt $decoderRetryCount)",
                    error,
                )
                InAppLogger.warn(
                    "ExoPlayer/Android",
                    "Decoder ladder ${error.errorCodeName} -> mode=$nextMode attempt=$decoderRetryCount. " +
                        "cause=${error.cause?.let(InAppLogger::throwableSummary) ?: InAppLogger.throwableSummary(error)}",
                )
                fallbackStartPositionMs = exoPlayer.currentPosition.coerceAtLeast(0L)
                decoderPriorityOverride = nextMode
                latestOnError.value(null)
                return
            }
            InAppLogger.error(""" % _CODEC_REGEX_PY,
        "decoder ladder in reportPlayerError",
    )


def _patch_surface_reporting(source_dir: Path) -> None:
    """The surface must only report; recovery is orchestrated in PlayerScreenRuntimeUi."""
    path = source_dir / _ENGINE
    _replace_once(
        path,
        """    val surfaceOnError: (String?) -> Unit = { message ->
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
    }""",
        """    val surfaceOnError: (String?) -> Unit = { message ->
        // Nuvio Enhanced Player Core v2: the surface only REPORTS. All recovery runs once
        // in PlayerScreenRuntimeUi.onError — expired-link refresh -> source fallback ->
        // codec-gated engine switch (position preserved) -> error. A surface-side engine
        // flip here would skip source fallback and could lose the playback position.
        if (message == null || castBridge?.isCasting != true) {
            onError(message)
        }
    }""",
        "surface reports only",
    )


def _patch_runtime_engine_gate(source_dir: Path) -> None:
    """Codec-class engine switches must be allowed for local files — Libmpv/ffmpeg is the
    fix for local AV1/HEVC decode failures. Non-codec errors never reload the engine."""
    path = source_dir / _RUNTIME_ACTIONS
    _replace_once(
        path,
        """    // v1.20: never reload engines for local/offline sources — a full engine switch cannot fix
    // file:// or content:// problems and only restarts playback of the same failing local file.
    val failoverSourceUrl = activeSourceUrl
    if (failoverSourceUrl.startsWith("file:") || failoverSourceUrl.startsWith("content:")) return false
    // v1.20: when the failing message is known, only codec/decoder-class failures may escalate
    // engines. Link/HTTP/network errors must flow through refresh/fallback first; escalating
    // them caused a full Exo->Libmpv reload ahead of the runtime link-refresh (double reload,
    // endless loading on CloudStream expired links). Callers passing no message keep legacy
    // behaviour (host tests).
    if (message != null) {
        val looksLikeCodecFailure =
            Regex(
                "decod|codec|renderer|MediaCodec|OMX|c2\\\\.|unsupported (video|audio|mime)|video format|format not supported",
                RegexOption.IGNORE_CASE,
            ).containsMatchIn(message)
        if (!looksLikeCodecFailure) return false
    }""",
        """    // v1.20 Player Core v2: only codec/decoder-class failures may switch engines — and that
    // INCLUDES local files (a local MKV failing in libgav1 is fixed by Libmpv/ffmpeg, so a
    // blanket file:// block would strand the user on an unplayable local file). Link/HTTP
    // errors never reload the engine: refresh/fallback handle those first, and local files
    // have nothing to refresh. Callers passing no message keep legacy behaviour (host tests).
    if (message != null) {
        val looksLikeCodecFailure =
            Regex(
                "decod|codec|renderer|MediaCodec|OMX|c2\\\\.|libgav1|unsupported (video|audio|mime)|video format|format not supported",
                RegexOption.IGNORE_CASE,
            ).containsMatchIn(message)
        if (!looksLikeCodecFailure) return false
    } else {
        val failoverSourceUrl = activeSourceUrl
        if (failoverSourceUrl.startsWith("file:") || failoverSourceUrl.startsWith("content:")) return false
    }""",
        "runtime codec gate allows local files",
    )


def apply_v120_player_core_v2_patch(source_dir: Path) -> None:
    _patch_decoder_ladder(source_dir)
    _patch_surface_reporting(source_dir)
    _patch_runtime_engine_gate(source_dir)
    print(
        "[v1.20-module-13] Player Core v2: decoder ladder for local files, single-point "
        "recovery orchestration, codec-gated engine switch incl. local sources applied cleanly."
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: nuvio_v120_player_core_v2_patch.py <source-root>")
    apply_v120_player_core_v2_patch(Path(sys.argv[1]))
