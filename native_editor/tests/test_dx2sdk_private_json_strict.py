"""Regression for strict source-private JSON parsing in both Python CLIs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dx2sdk.private_brush_preflight import load_private_json_text

VALID = ('{"kind":"Box","size":[2,2,2],"steps":1,'
         '"clip_plane":{"normal":[1,0,0],"distance":0,'
         '"keep_positive":false}}')


class StrictPrivateJSONTests(unittest.TestCase):
    def test_valid_input_and_nested_duplicate_refusal(self):
        self.assertEqual(load_private_json_text(VALID)["kind"], "Box")
        for invalid in (
            VALID.replace('"steps":1', '"steps":1,"steps":1'),
            VALID.replace('"distance":0', '"distance":0,"distance":0'),
            VALID.replace('"kind":"Box"', '"kind":"Box","kind":"Box"'),
            VALID.replace('"distance":0', '"distance":NaN'),
            VALID.replace('"distance":0', '"distance":Infinity'),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                load_private_json_text(invalid)

    def test_both_clis_refuse_duplicate_keys_without_writing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "private.json"
            original = root / "Original.gmp"
            original.write_bytes(b"UNCHANGED_RETAIL_SENTINEL")
            before = original.read_bytes()
            cases = (
                VALID.replace('"steps":1', '"steps":1,"steps":1'),
                VALID.replace('"distance":0', '"distance":0,"distance":0'),
                VALID.replace('"distance":0', '"distance":NaN'),
            )
            for index, payload in enumerate(cases):
                source.write_text(payload, encoding="utf-8")
                out = root / f"invalid_{index}.obj"
                for module, args in (
                    ("dx2sdk.private_brush_preflight", [str(source)]),
                    ("dx2sdk.private_brush_obj", [str(source), str(out)]),
                ):
                    result = subprocess.run(
                        [sys.executable, "-m", module, *args],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("REFUSED", result.stderr)
                    self.assertFalse(out.exists())
            self.assertEqual(original.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
