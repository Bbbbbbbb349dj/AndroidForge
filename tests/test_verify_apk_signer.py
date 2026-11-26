import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("verify_apk_signer", Path(__file__).resolve().parents[1] / "scripts/verify_apk_signer.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SignerVerificationTest(unittest.TestCase):
    def test_accepts_signer_labels_without_assuming_number_format(self):
        fingerprint = "ab" * 32
        for label in ("Signer #1", "Signer (minSdkVersion=28)"):
            output = f"{label} certificate SHA-256 digest: {fingerprint}"
            self.assertEqual({fingerprint}, module.certificate_fingerprints(output))

    def test_rejects_empty_and_invalid_fingerprints(self):
        for output in ("", "Signer #1 certificate SHA-256 digest: ", "certificate SHA-256 digest: invalid"):
            with self.assertRaises(ValueError):
                module.certificate_fingerprints(output)

    def test_compares_both_verified_apks(self):
        def result(value):
            return subprocess.CompletedProcess([], 0, stdout=f"Signer #1 certificate SHA-256 digest: {value * 64}")
        with patch.object(module.subprocess, "run", side_effect=[result("a"), result("a")]):
            module.verify_same_signer("apksigner", "old.apk", "new.apk")
        with patch.object(module.subprocess, "run", side_effect=[result("a"), result("b")]):
            with self.assertRaises(SystemExit):
                module.verify_same_signer("apksigner", "old.apk", "new.apk")


if __name__ == "__main__":
    unittest.main()
