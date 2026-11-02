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
from dx2_package_roundtrip import inspect_noop, write_noop_copy, cross_check_translation, main
from dx2level import SCALE, actor_matrix


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

    def _translation_metadata(self):
        source = self.original
        import hashlib
        actors_file = self.root / "Cache" / "actors.json"
        actors_file.parent.mkdir(exist_ok=True)
        name = "StaticMeshActor__1"
        actor = {
            "name": name, "class": "StaticMeshActor", "export": 1,
            "mesh": "FictionalBox", "location": [100.0, 200.0, 300.0],
            "rotation": [0, 0, 0],
        }
        actors_file.write_text(json.dumps({"meta": {
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "source_map": self.source.name,
        }, "actors": [actor]}))
        matrix = actor_matrix({
            "x": 100.0, "y": 200.0, "z": 300.0,
            "rotation": [0, 0, 0],
        })
        transform = [
            matrix[0], matrix[1], matrix[2],
            matrix[4], matrix[5], matrix[6],
            matrix[8], matrix[9], matrix[10],
            120 * SCALE, 320 * SCALE, 240 * SCALE,
        ]
        draft = {
            "schema": "DX2Ed-prop-draft-v1",
            "read_only_source": True,
            "map_cache": str(actors_file.parent),
            "moved": [{"actor": name, "transform": transform}],
            "copies": [], "property_edits": [],
        }
        draft_file = actors_file.parent / "draft.json"
        draft_file.write_text(json.dumps(draft))
        return actors_file, draft_file, draft

    def test_t3sdk_edited_export_matches_existing_native_patch_exactly(self):
        actors, draft_path, _ = self._translation_metadata()
        report = cross_check_translation(self.source, actors, draft_path)
        self.assertEqual(report["status"], "in-memory-match-only")
        self.assertTrue(report["serializers_agree_byte_for_byte"])
        self.assertTrue(report["same_byte_length"])
        self.assertGreater(report["changed_bytes"], 0)
        self.assertLessEqual(report["changed_bytes"], 12)
        self.assertEqual(len(report["edited_existing_actors"]), 1)
        self.assertEqual(report["edited_existing_actors"][0]["after"], [120.,240.,320.])
        self.assertFalse(report["output_written"])
        self.assertFalse(report["runtime_game_verified"])
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(self.output.exists())
        self.assertEqual(main(["compare-translation", str(self.source),
                              "--actors", str(actors), "--draft", str(draft_path)]), 0)

    def test_cross_check_refuses_unsupported_rotations_and_new_actors(self):
        actors, draft_path, draft = self._translation_metadata()
        draft["moved"][0]["transform"][0] = 0.5
        draft_path.write_text(json.dumps(draft))
        with self.assertRaisesRegex(ValueError, "rotation/scale"):
            cross_check_translation(self.source, actors, draft_path)
        draft["moved"][0]["transform"][0] = actor_matrix({
            "x": 100.0, "y": 200.0, "z": 300.0, "rotation": [0, 0, 0]
        })[0]
        draft["copies"] = [{"from_actor": "StaticMeshActor__1", "name": "Copy"}]
        draft_path.write_text(json.dumps(draft))
        with self.assertRaisesRegex(ValueError, "native writer"):
            cross_check_translation(self.source, actors, draft_path)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_audit_does_not_write_and_rejects_wrong_output(self):
        self.assertEqual(main(["audit", str(self.source)]), 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(main(["copy", str(self.source),
                               "--output", str(self.output.with_suffix(".txt"))]), 1)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
