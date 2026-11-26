"""Reconstruct the player delta from the committed v1.22 baseline; fail closed on drift."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nuvio_v123_patch import apply_v123_patch, v123_is_applied


class PlayerDeltaTest(unittest.TestCase):
    def test_exact_reconstruction_idempotence_and_drift_rejection(self):
        patch = ROOT / "scripts/nuvio_v123.patch"
        # Parent baseline remains stable as subsequent fixes are committed.
        baseline = "4aa44de"
        files = [line[6:] for line in patch.read_text().splitlines() if line.startswith("+++ b/")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for name in files:
                result = subprocess.run(["git", "show", f"{baseline}:{name}"], cwd=ROOT, capture_output=True)
                if result.returncode == 0:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(result.stdout)
            self.assertTrue(apply_v123_patch(root))
            self.assertTrue(v123_is_applied(root))
            self.assertEqual([], apply_v123_patch(root))
            # Compare against the committed v1.23 baseline, not later redesigned files.
            for name in files:
                expected = subprocess.check_output(["git", "show", f"88c084d:{name}"], cwd=ROOT)
                self.assertEqual(expected, (root / name).read_bytes(), name)
            target = root / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlaybackStartupPolicy.kt"
            target.write_text(target.read_text().replace("1_500", "0"))
            self.assertFalse(v123_is_applied(root))
            with self.assertRaises(subprocess.CalledProcessError):
                apply_v123_patch(root)

    def test_player_does_not_request_live_frame_readback(self):
        text = (ROOT / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player/PlayerScreenContent.kt").read_text()
        self.assertNotIn("provides rememberVideoFrameBackdrop(", text)
        self.assertIn("LocalLiquidGlassBackdrop provides null", text)

    def test_actions_live_in_both_bottom_layouts_not_side_overlay(self):
        player = ROOT / "composeApp/src/commonMain/kotlin/com/nuvio/app/features/player"
        self.assertEqual(2, (player / "PlayerControls.kt").read_text().count("extraActions = bottomActions"))
        actions = (player / "PlayerFeatureActions.kt").read_text()
        self.assertNotIn("Alignment.CenterEnd", actions)
        for token in ["ModalBottomSheet(", "AsyncImage(", "preview.description", "preview.imdbRating"]:
            self.assertIn(token, actions)


if __name__ == "__main__":
    unittest.main()
