"""Asset-free tests for the T3SDK -> DX2 GMP no-op writer bridge.

The synthetic GMP fixture is produced by the native writer test suite;
copyrighted game packages are never committed.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "package_writer"))
sys.path.insert(0, str(ROOT / "native_editor" / "tests"))

from test_native_save_as import fixture_gmp
from dx2_package_roundtrip import inspect_noop, write_noop_copy, main


class DX2T3SDKRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original_folder = self.root / "RetailMaps"
        self.original_folder.mkdir()
        self.source = self.original_folder / "M1_Test.gmp"
        self.original = fixture_gmp()
        self.source.write_bytes(self.original)
        self.output = self.root / "IsolatedTestMaps" / self.source.name

    def test_rebuild_noop_is_bit_exact_and_independently_validated(self):
        report, reconstructed = inspect_noop(self.source)
        self.assertEqual(reconstructed, self.original)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertTrue(report["byte_identical"])
        self.assertEqual(report["status"], "byte-identical")
        self.assertEqual(report["licensee_version"], 69)
        self.assertEqual(report["package_version"], 95)
        self.assertEqual(report["edited_exports"], 0)
        self.assertFalse(report["runtime_game_verified"])
        self.assertEqual(report["export_count"], 1)

    def test_copies_only_to_separate_folder_and_writes_manifest(self):
        report = write_noop_copy(self.source, self.output)
        self.assertEqual(report["status"], "written-identical-unverified")
        self.assertEqual(self.output.read_bytes(), self.original)
        self.assertEqual(self.source.read_bytes(), self.original)
        manifest = self.output.with_suffix(".dx2ed-roundtrip.json")
        data = json.loads(manifest.read_text(encoding="utf8"))
        self.assertEqual(data["output_sha256"], data["source_sha256"])
        self.assertFalse(data["runtime_game_verified"])
        self.assertEqual(data["edited_exports"], 0)
        with self.assertRaisesRegex(FileExistsError, "overwrite"):
            write_noop_copy(self.source, self.output)

    def test_rejects_original_folder_and_nested_retail_outputs(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            write_noop_copy(self.source, self.source)
        with self.assertRaisesRegex(ValueError, "outside"):
            write_noop_copy(self.source, self.source.parent / "TestSubdir" / self.source.name)
        with self.assertRaisesRegex(ValueError, "exact source"):
            write_noop_copy(self.source, self.root / "Other" / "Wrong.gmp")
        self.assertFalse(self.output.exists())

    def test_rejects_existing_manifest_even_when_output_absent(self):
        manifest = self.output.with_suffix(".dx2ed-roundtrip.json")
        manifest.parent.mkdir(parents=True)
        manifest.write_text("{}")
        with self.assertRaisesRegex(FileExistsError, "manifest"):
            write_noop_copy(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_other_ion_storm_licensees_not_assumed_compatible(self):
        blob = bytearray(self.original)
        struct.pack_into("<H", blob, 6, 133)  # Thief 3 map, not retail DX2
        self.source.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "licensee"):
            inspect_noop(self.source)
        self.assertFalse(self.output.exists())

    def test_rejects_corrupted_gmp(self):
        self.source.write_bytes(b"not a package")
        with self.assertRaises((ValueError, IndexError, EOFError)):
            inspect_noop(self.source)

    def test_fault_in_writer_cannot_silently_emit_different_bytes(self):
        class BrokenWriter:
            def __init__(self, pkg):
                pass
            def write(self):
                changed = bytearray(self_original)
                changed[-1] ^= 0x04
                return bytes(changed)

        self_original = self.original
        with patch("dx2_package_roundtrip.PackageWriter", BrokenWriter):
            with self.assertRaisesRegex(ValueError, "changed bytes"):
                write_noop_copy(self.source, self.output)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(self.output.exists())

    def test_cli_audit_does_not_write_and_rejects_wrong_output(self):
        self.assertEqual(main(["audit", str(self.source)]), 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(main(["copy", str(self.source),
                               "--output", str(self.output.with_suffix(".txt"))]), 1)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
