"""Strict, repeat-safe v1.22 -> v1.23 player rework shared by APK and source export."""
from pathlib import Path
import subprocess


def v123_is_applied(root: Path) -> bool:
    patch = Path(__file__).with_name("nuvio_v123.patch")
    return subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "--reverse", "--check", str(patch)],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def apply_v123_patch(root: Path) -> list[str]:
    if v123_is_applied(root):
        return []
    patch = Path(__file__).with_name("nuvio_v123.patch")
    command = ["git", "apply", "--whitespace=nowarn"]
    subprocess.run(command + ["--check", str(patch)], cwd=root, check=True)
    subprocess.run(command + [str(patch)], cwd=root, check=True)
    return ["v1.23 bounded buffering, bottom player chrome and embedded VLC delta"]
