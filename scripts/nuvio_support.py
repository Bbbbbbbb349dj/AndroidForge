#!/usr/bin/env python3
"""AndroidForge — Nuvio Enhanced Project Support.

Prepares an extracted Nuvio / Nuvio Enhanced 2 Kotlin Multiplatform source tree
for Android APK builds:

  1. Restores `com/nuvio/app/core/build/AppFeaturePolicy*.kt` files ONLY if they
     were accidentally stripped from the source archive (e.g. by a `*/build/*`
     ZIP exclusion rule matching the `core/build` package directory).
  2. Ensures `native/thumbs/src/bin/thumbs-bench/main.rs` exists if declared in
     `native/thumbs/Cargo.toml` (in case `*/bin/*` was excluded during archiving).
  3. Writes `local.properties` (`sdk.dir`) if an Android SDK path is available.
  4. Configures runner-safe Gradle / Kotlin daemon JVM memory bounds in
     `~/.gradle/gradle.properties` so developer-workstation `-Xmx12288M` flags
     do not OOM-kill CI runners.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


APP_FEATURE_POLICY_FILES: dict[str, str] = {
    "composeApp/src/commonMain/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.kt": """\
package com.nuvio.app.core.build

enum class TrailerPlaybackMode {
    IN_APP,
    EXTERNAL,
}

expect object AppFeaturePolicy {
    val pluginsEnabled: Boolean
    val accountDeletionEnabled: Boolean
    val personalMediaAddonCopyEnabled: Boolean
    val p2pEnabled: Boolean
    val trailerPlaybackMode: TrailerPlaybackMode
    val heroTrailerPlaybackSupported: Boolean
    val inAppUpdaterEnabled: Boolean
    val imdbRatingLogoEnabled: Boolean
    val mediaPlaybackForegroundServiceEnabled: Boolean
    val downloadForegroundServiceEnabled: Boolean
    val customServerConnectionsEnabled: Boolean
}
""",
    "composeApp/src/androidFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.android.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = true
    actual val accountDeletionEnabled: Boolean = false
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = true
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.IN_APP
    actual val heroTrailerPlaybackSupported: Boolean = true
    actual val inAppUpdaterEnabled: Boolean = true
    actual val imdbRatingLogoEnabled: Boolean = true
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = true
    actual val downloadForegroundServiceEnabled: Boolean = true
    actual val customServerConnectionsEnabled: Boolean = true
}
""",
    "composeApp/src/androidPlaystore/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.android.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = false
    actual val accountDeletionEnabled: Boolean = true
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = true
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.EXTERNAL
    actual val heroTrailerPlaybackSupported: Boolean = false
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = false
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = false
}
""",
    "composeApp/src/desktopMain/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.desktop.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = false
    actual val accountDeletionEnabled: Boolean = false
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = false
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.EXTERNAL
    actual val heroTrailerPlaybackSupported: Boolean = false
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = true
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = false
}
""",
    "composeApp/src/iosFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.ios.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = true
    actual val accountDeletionEnabled: Boolean = false
    actual val personalMediaAddonCopyEnabled: Boolean = false
    actual val p2pEnabled: Boolean = true
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.IN_APP
    actual val heroTrailerPlaybackSupported: Boolean = true
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = true
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = true
}
""",
    "composeApp/src/iosAppStore/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.ios.kt": """\
package com.nuvio.app.core.build

actual object AppFeaturePolicy {
    actual val pluginsEnabled: Boolean = false
    actual val accountDeletionEnabled: Boolean = true
    actual val personalMediaAddonCopyEnabled: Boolean = true
    actual val p2pEnabled: Boolean = false
    actual val trailerPlaybackMode: TrailerPlaybackMode = TrailerPlaybackMode.EXTERNAL
    actual val heroTrailerPlaybackSupported: Boolean = false
    actual val inAppUpdaterEnabled: Boolean = false
    actual val imdbRatingLogoEnabled: Boolean = false
    actual val mediaPlaybackForegroundServiceEnabled: Boolean = false
    actual val downloadForegroundServiceEnabled: Boolean = false
    actual val customServerConnectionsEnabled: Boolean = false
}
""",
}


def is_nuvio_project(root: Path) -> bool:
    """Detect whether `root` is a Nuvio / Nuvio Enhanced KMP Android project."""
    if root.name.lower().startswith("nuvio"):
        return True
    candidates = [
        root / "gradle.properties",
        root / "settings.gradle.kts",
        root / "composeApp" / "build.gradle.kts",
        root / "androidApp" / "build.gradle.kts",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if (
            "nuvio.android.distribution" in text
            or "com.nuvio.enhanced" in text
            or 'rootProject.name = "Nuvio"' in text
        ):
            return True
    return False


def prepare_nuvio_source(
    root: Path,
    android_sdk: str | None = None,
    configure_global_gradle: bool = True,
) -> dict[str, object]:
    """Prepare Nuvio Enhanced source tree for Android builds."""
    restored_files: list[str] = []

    if (root / "composeApp" / "build.gradle.kts").is_file():
        for rel_path, content in APP_FEATURE_POLICY_FILES.items():
            target = root / rel_path
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                restored_files.append(rel_path)

    # Guard against `*/bin/*` archive exclusions breaking Cargo manifest checks
    thumbs_cargo = root / "native" / "thumbs" / "Cargo.toml"
    thumbs_bin_main = root / "native" / "thumbs" / "src" / "bin" / "thumbs-bench" / "main.rs"
    thumbs_bin_alt = root / "native" / "thumbs" / "src" / "bin" / "thumbs-bench.rs"
    if (
        thumbs_cargo.is_file()
        and 'name = "thumbs-bench"' in thumbs_cargo.read_text(encoding="utf-8", errors="replace")
        and not thumbs_bin_main.exists()
        and not thumbs_bin_alt.exists()
    ):
        thumbs_bin_main.parent.mkdir(parents=True, exist_ok=True)
        thumbs_bin_main.write_text("fn main() {}\n", encoding="utf-8")
        restored_files.append(str(thumbs_bin_main.relative_to(root)))

    # Ensure gradlew is executable
    gradlew = root / "gradlew"
    if gradlew.is_file():
        gradlew.chmod(gradlew.stat().st_mode | 0o111)

    # Ensure local.properties exists (required by Nuvio build scripts and AGP)
    sdk_dir = (
        android_sdk
        or os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
    )
    local_props = root / "local.properties"
    if sdk_dir and Path(sdk_dir).exists():
        existing = local_props.read_text(encoding="utf-8", errors="replace") if local_props.exists() else ""
        if "sdk.dir=" not in existing:
            with local_props.open("a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(f"sdk.dir={sdk_dir}\n")
    elif not local_props.exists():
        local_props.touch()

    if configure_global_gradle:
        gradle_user_home = Path(os.environ.get("GRADLE_USER_HOME", str(Path.home() / ".gradle")))
        gradle_user_home.mkdir(parents=True, exist_ok=True)
        user_props = gradle_user_home / "gradle.properties"
        desired_lines = {
            "org.gradle.jvmargs": "org.gradle.jvmargs=-Xmx6g -Dfile.encoding=UTF-8 -XX:MaxMetaspaceSize=1536m",
            "kotlin.daemon.jvmargs": "kotlin.daemon.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1536m -XX:+UseParallelGC",
            "org.gradle.configuration-cache": "org.gradle.configuration-cache=false",
        }
        lines = (
            user_props.read_text(encoding="utf-8", errors="replace").splitlines()
            if user_props.exists()
            else []
        )
        filtered = [
            ln for ln in lines
            if not any(ln.strip().startswith(f"{k}=") or ln.strip().startswith(f"{k} =") for k in desired_lines)
        ]
        filtered.extend(desired_lines.values())
        user_props.write_text("\n".join(filtered) + "\n", encoding="utf-8")

    return {
        "project_root": str(root),
        "is_nuvio": is_nuvio_project(root),
        "restored_files": restored_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Nuvio Enhanced source tree")
    parser.add_argument("--root", required=True, help="Extracted Nuvio project root")
    parser.add_argument("--android-sdk", default=None, help="Android SDK path")
    parser.add_argument("--no-global-gradle", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    summary = prepare_nuvio_source(
        root,
        android_sdk=args.android_sdk,
        configure_global_gradle=not args.no_global_gradle,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
