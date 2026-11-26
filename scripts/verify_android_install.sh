#!/usr/bin/env bash
# Test the exact published APK, not a rebuilt or re-signed approximation.
set -euo pipefail
mkdir -p install-diagnostics
adb shell getprop > install-diagnostics/emulator-properties.txt
adb logcat -c
set +e
adb install --no-streaming "$APK_PATH" 2>&1 | tee install-diagnostics/install-result.txt
install_status=${PIPESTATUS[0]}
set -e
adb logcat -d -b all > install-diagnostics/package-manager-logcat.txt
if [ "$install_status" -ne 0 ]; then
  echo "::error::Android 16 rejected the published APK. See install-result.txt for the actual INSTALL_* code."
  exit "$install_status"
fi
adb shell dumpsys package com.nuvio.enhanced > install-diagnostics/installed-package.txt
if ! grep -q 'versionCode=210' install-diagnostics/installed-package.txt; then
  echo '::error::Installed package is not the expected v1.21 build.'
  exit 1
fi
{
  echo '## Android 16 installation check'
  echo ''
  echo 'Exact published v1.21 ARM64 APK installed successfully on an API 36 Google APIs emulator.'
  echo 'This validates installation on that emulator, not on a physical Motorola device.'
} >> "$GITHUB_STEP_SUMMARY"
