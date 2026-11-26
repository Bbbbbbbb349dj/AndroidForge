"""Strict, repeat-safe v1.21 -> v1.22 source delta for source exports and APKs."""
from pathlib import Path
import subprocess


def v122_is_applied(root: Path) -> bool:
    patch = Path(__file__).with_name("nuvio_v122.patch")
    return subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "--reverse", "--check", str(patch)],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def apply_v122_patch(root: Path) -> list[str]:
    if v122_is_applied(root):
        return []
    patch = Path(__file__).with_name("nuvio_v122.patch")
    command = ["git", "apply", "--whitespace=nowarn"]
    subprocess.run(command + ["--check", str(patch)], cwd=root, check=True)
    subprocess.run(command + [str(patch)], cwd=root, check=True)
    return ["v1.22 repository browser and first-frame playback delta"]
