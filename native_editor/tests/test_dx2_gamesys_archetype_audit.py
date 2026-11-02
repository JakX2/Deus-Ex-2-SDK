"""Asset-free DX2Gamesys archetype ancestry and source identity tests."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT / "native_editor" / "package_writer",
                  ROOT / "third_party" / "t3sdk_assets"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from dx2_gamesys_archetype_audit import ancestry_status, _original_gamesys, main
from t3gamesys import Archetype


class DX2GamesysArchetypeTests(unittest.TestCase):
    def test_complete_dx2_parent_chain_only_if_all_parsed(self):
        parent = Archetype("D_1", "Generic", "DX2Actor")
        child = Archetype("D_2", "Guard", "D_1")
        chain, complete, issue = ancestry_status(child, {"D_1": parent, "D_2": child})
        self.assertEqual(chain, ["D_2", "D_1"])
        self.assertTrue(complete)
        self.assertIsNone(issue)

    def test_rejects_missing_parent_cycles_and_damaged_ancestors(self):
        a = Archetype("D_1", "A", "D_2")
        b = Archetype("D_2", "B", "D_1")
        chain, ok, reason = ancestry_status(a, {"D_1": a, "D_2": b})
        self.assertFalse(ok)
        self.assertIn("cycle", reason)
        self.assertEqual(chain, ["D_1", "D_2"])
        b.parent = "D_999"
        self.assertIn("missing", ancestry_status(a, {"D_1": a, "D_2": b})[2])
        b.parent = "DX2Actor"
        b.error = "unknown original bytes"
        self.assertIn("unparsed", ancestry_status(a, {"D_1": a, "D_2": b})[2])

    def test_original_zip_requires_unambiguous_dx2_gamesys_member(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp)/"System.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("System/DX2Gamesys.d2u", b"synthetic original")
            data, member = _original_gamesys(p)
            self.assertEqual(data, b"synthetic original")
            self.assertEqual(member, "System/DX2Gamesys.d2u")
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("System/DX2Gamesys.d2u", b"one")
                z.writestr("extra/DX2Gamesys.d2u", b"two")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                _original_gamesys(p)
            with self.assertRaisesRegex(ValueError, "fresh JSON"):
                main([str(p), "--output", str(p)])

    def test_no_gamesys_package_is_not_treated_as_empty_valid_schema(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)/"System"
            folder.mkdir()
            with self.assertRaises(FileNotFoundError):
                _original_gamesys(folder)


if __name__ == "__main__":
    unittest.main()
