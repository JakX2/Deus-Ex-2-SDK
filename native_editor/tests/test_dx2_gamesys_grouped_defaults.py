"""Pure synthetic tests for original DX2 length-prefixed archetype groups.

No proprietary DX2 or Thief data is included.
"""
from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / "third_party" / "t3sdk_assets",
               ROOT / "native_editor" / "package_writer",
               ROOT / "native_editor" / "tests"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from test_native_save_as import fixture_gmp
from upkg import Package
from t3common import Reader, write_index
from dx2_gamesys_archetype_arrays import scan_property_groups


def _group(encoded_id, blobs):
    payload = struct.pack("<II", encoded_id, len(blobs))
    return payload + b"".join(struct.pack("<I", len(b)) + b for b in blobs)


class OriginalDX2GroupedDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = Package("synthetic.gmp", data=fixture_gmp())

    def scan(self, raw):
        return scan_property_groups(self.pkg, Reader(raw))

    def test_all_29_vulnerability_struct_elements_have_exact_bounds(self):
        raw = _group(0x000803BF, [b"\x00"] * 29) + struct.pack("<I", 0)
        decoded = self.scan(raw)
        self.assertEqual(decoded["multi_element_group_count"], 1)
        group = decoded["groups"][0]
        self.assertEqual(group["property_id"], 959)
        self.assertEqual(group["encoding"], "struct")
        self.assertEqual(group["element_count"], 29)
        self.assertEqual(len(group["elements"]), 29)
        self.assertEqual(group["elements"][1]["typed_fields"], [])
        self.assertEqual(group["elements"][-1]["payload_offset"], len(raw) - 5)
        self.assertFalse(group["native_edit_enabled"])

    def test_three_biomod_strings_recover_exact_length_and_text(self):
        values = ["Level 1 increased vision", "Level 2 stronger vision", "Level 3 maximum vision"]
        blobs = [write_index(len(v) + 1) + v.encode("latin1") + b"\0" for v in values]
        raw = _group(0x00040725, blobs)
        decoded = self.scan(raw)
        group = decoded["groups"][0]
        self.assertEqual(group["element_count"], 3)
        self.assertEqual([r["string_value"] for r in group["elements"]], values)

    def test_three_biomod_modifier_structs_are_supported(self):
        group = self.scan(_group(0x000804F0, [b"\x00"] * 3))["groups"][0]
        self.assertEqual(len(group["elements"]), 3)
        self.assertTrue(all(element["typed_fields"] == [] for element in group["elements"]))

    def test_corrupted_element_size_and_unknown_multi_encoding_fail_closed(self):
        bad = struct.pack("<III", 0x000803BF, 29, 100000) + b"\x00"
        with self.assertRaisesRegex(ValueError, "exceeds original export"):
            self.scan(bad)
        unknown = _group(0x00040060, [b"\x01\x00"] * 3)
        with self.assertRaisesRegex(ValueError, "Unknown multi-element"):
            self.scan(unknown)
        with self.assertRaisesRegex(ValueError, "outside verified bounds"):
            self.scan(struct.pack("<III", 0x000803BF, 999999, 1) + b"\x00")

    def test_refuses_unknown_trailing_bytes_and_incomplete_headers(self):
        with self.assertRaisesRegex(ValueError, "Incomplete grouped GameSys identifier"):
            self.scan(_group(0x000803BF, [b"\x00"] * 29) + b"\x01")
        with self.assertRaisesRegex(ValueError, "Incomplete grouped"):
            self.scan(b"\x01\x02")

    def test_old_source_parser_failure_does_not_poison_verified_ancestry(self):
        from t3gamesys import Archetype
        from dx2_gamesys_archetype_audit import ancestry_status
        parent = Archetype("D_1198", "PawnVulnerabilities", "VulnerabilityObject",
                           error="old parser misreads struct element sizes")
        child = Archetype("D_1179", "BotBasicVuln", "D_1198",
                          error="old parser misreads struct element sizes")
        mapping = {"D_1198": parent, "D_1179": child}
        original = ancestry_status(child, mapping)
        self.assertFalse(original[1])
        verified = ancestry_status(child, mapping, frozenset({"D_1198", "D_1179"}))
        self.assertEqual(verified[0], ["D_1179", "D_1198"])
        self.assertTrue(verified[1])
        self.assertIsNone(verified[2])


if __name__ == "__main__":
    unittest.main()
