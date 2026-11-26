"""Exercise the actual install gate without requiring adb or an emulator locally."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_android_install.sh"


class AndroidInstallGateTest(unittest.TestCase):
    def run_gate(self, failure=False, version="220", package="com.nuvio.enhanced.standalone"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adb = root / "adb"
            adb.write_text("""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$ADB_COMMANDS"
if [ "$1" = install ]; then
  if [ "$FAIL_INSTALL" = true ]; then
    echo 'Failure [INSTALL_FAILED_INVALID_APK: synthetic test failure]'
    exit 1
  fi
  echo Success
elif [ "$1 $2" = 'shell dumpsys' ]; then
  echo "versionCode=$TEST_VERSION minSdk=24 targetSdk=36"
fi
""")
            adb.chmod(0o755)
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"],
                       APK_PATH=str(root / "exact-signed.apk"), PACKAGE_ID=package,
                       FAIL_INSTALL=str(failure).lower(), TEST_VERSION=version,
                       ADB_COMMANDS=str(root / "commands"), GITHUB_STEP_SUMMARY=str(root / "summary"))
            result = subprocess.run(["bash", str(SCRIPT)], cwd=root, env=env,
                                    capture_output=True, text=True)
            return result, (root / "commands").read_text(), (root / "summary").exists()

    def test_success_checks_requested_separate_package(self):
        result, commands, summary = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("shell dumpsys package com.nuvio.enhanced.standalone", commands)
        self.assertIn("install --no-streaming", commands)
        self.assertTrue(summary)

    def test_installer_failure_blocks_publication(self):
        result, commands, summary = self.run_gate(failure=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INSTALL_FAILED_INVALID_APK", result.stdout)
        self.assertNotIn("dumpsys package", commands)
        self.assertFalse(summary)

    def test_wrong_version_fails_closed(self):
        result, _, summary = self.run_gate(version="200")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(summary)


if __name__ == "__main__":
    unittest.main()
