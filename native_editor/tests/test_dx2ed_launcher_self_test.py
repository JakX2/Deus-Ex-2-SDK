"""Windows launcher safety check: failed Godot fixtures must fail --self-test."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "prototype" / "START_DX2ED.cmd"


class WindowsSelfTestExitCodeTests(unittest.TestCase):
    def test_failed_fixture_is_not_silently_reported_as_pass(self):
        script = LAUNCHER.read_text(encoding="utf8")
        self.assertIn("setlocal EnableExtensions EnableDelayedExpansion", script)
        self.assertIn('set "DX2ED_SELFTEST_FAILED=1"', script)
        self.assertIn('if "!DX2ED_SELFTEST_FAILED!"=="1"', script)
        self.assertIn("DX2Ed Windows prototype self-test: FAIL", script)
        self.assertIn("exit /b 1", script)
        self.assertIn("DX2Ed Windows prototype self-test: PASS", script)


if __name__ == "__main__":
    unittest.main()
