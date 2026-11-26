"""Strict, repeat-safe v1.23 -> v1.24 visual rework shared by APK and source export."""
from pathlib import Path
import subprocess


def v124_is_applied(root: Path) -> bool:
    patch = Path(__file__).with_name("nuvio_v124.patch")
    return subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "--reverse", "--check", str(patch)],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def apply_v124_patch(root: Path) -> list[str]:
    if v124_is_applied(root):
        return []
    patch = Path(__file__).with_name("nuvio_v124.patch")
    command = ["git", "apply", "--whitespace=nowarn"]
    subprocess.run(command + ["--check", str(patch)], cwd=root, check=True)
    subprocess.run(command + [str(patch)], cwd=root, check=True)
    return ["v1.24 compact player and editorial profile delta"]
