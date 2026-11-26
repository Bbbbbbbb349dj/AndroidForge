#!/usr/bin/env bash
# Native decoder/control/lifecycle smoke test on a debug build, separately from signed APK install.
set -euo pipefail
mkdir -p install-diagnostics
DEBUG_APK=$(find "$PROJECT_ROOT/androidApp/build/outputs/apk/full/debug" -name '*arm64-v8a*.apk' | head -1)
TEST_APK=$(find "$PROJECT_ROOT/androidApp/build/outputs/apk/androidTest/full/debug" -name '*.apk' | head -1)
[[ -n "$DEBUG_APK" && -n "$TEST_APK" ]]
adb uninstall "$PACKAGE_ID"
adb install --no-streaming "$DEBUG_APK"
adb install --no-streaming "$TEST_APK"
adb logcat -c
set +e
adb shell am instrument -w -r -e class com.nuvio.android.VlcPlaybackV123Test \
  "$PACKAGE_ID.test/androidx.test.runner.AndroidJUnitRunner" | tee install-diagnostics/vlc-playback-result.txt
status=${PIPESTATUS[0]}
set -e
adb logcat -d > install-diagnostics/vlc-playback-logcat.txt
if [[ "$status" -ne 0 ]] || ! grep -q 'OK (1 test)' install-diagnostics/vlc-playback-result.txt; then
  echo '::error::Embedded VLC playback/lifecycle smoke test failed. Publication is blocked.'
  exit 1
fi
{
  echo '## Embedded VLC native playback smoke check'
  echo 'Debug ARM64 build: local decode, position advance, seek, speed, pause, lifecycle return and surface recreation PASS on API 36 emulator.'
  echo 'Not a physical-device, network, full-player-layout or frame-time performance benchmark.'
} >> "$GITHUB_STEP_SUMMARY"
