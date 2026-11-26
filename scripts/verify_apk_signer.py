"""Fail closed rather than publish an APK that cannot update the reference app.

Only public certificate fingerprints are read. Private signing material stays in
GitHub Actions secrets/cache and is never downloaded to the working repository.
"""
import argparse
import re
import subprocess


def certificate_fingerprints(output: str) -> set[str]:
    fingerprints = set()
    for line in output.splitlines():
        marker = "certificate SHA-256 digest:"
        if marker in line:
            value = line.split(marker, 1)[1].strip().replace(":", "").lower()
            if re.fullmatch(r"[0-9a-f]{64}", value):
                fingerprints.add(value)
    if not fingerprints:
        raise ValueError("apksigner did not report a valid signing-certificate SHA-256 fingerprint")
    return fingerprints


def verify_same_signer(apksigner: str, previous: str, candidate: str) -> None:
    def fingerprints(path: str) -> set[str]:
        result = subprocess.run(
            [apksigner, "verify", "--print-certs", path],
            check=True, capture_output=True, text=True,
        )
        return certificate_fingerprints(result.stdout)
    old, new = fingerprints(previous), fingerprints(candidate)
    print("Reference public signing-certificate SHA-256:", ", ".join(sorted(old)))
    print("Candidate public signing-certificate SHA-256:", ", ".join(sorted(new)))
    if old != new:
        raise SystemExit(
            "::error::Signing certificate changed. APK publication is blocked to protect upgrade compatibility. "
            "Configure the existing release keystore in the repository's NUVIO_RELEASE_* Actions secrets; "
            "do not uninstall the installed app or commit/upload private keys to the repository."
        )
    print("Signing identity matches the reference APK; an in-place upgrade is permitted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apksigner", required=True)
    parser.add_argument("--previous", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()
    verify_same_signer(args.apksigner, args.previous, args.candidate)
