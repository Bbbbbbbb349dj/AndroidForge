"""Apply the strict v1.20 -> v1.21 source delta for both APK and source-export jobs.

The patch is intentionally separate from earlier release modules: it is reviewable,
checks every context before writing, and fails closed if the baseline has changed.
"""
from pathlib import Path
import subprocess


def apply_v121_patch(root: Path) -> list[str]:
    patch = Path(__file__).with_name("nuvio_v121.patch")
    command = ["git", "apply", "--whitespace=nowarn"]
    # Reverse-check makes repeated preparation safe without trusting a stale marker.
    if subprocess.run(command + ["--reverse", "--check", str(patch)], cwd=root,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return []
    subprocess.run(command + ["--check", str(patch)], cwd=root, check=True)
    subprocess.run(command + [str(patch)], cwd=root, check=True)
    return ["v1.21 source delta"]
