"""Asset-free end-to-end tests for the experimental GMP translation-only Save As.

Build a tiny synthetic but structurally valid Ion v95 package, with real
nested tagged FVector Location fields and an unrelated property. Verify the
real Package parser can reopen both original and patched variants.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "native_editor" / "godot_editor" / "backend"
MAP_EXPORTER = ROOT / "map_exporter"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(MAP_EXPORTER))

from dx2inspect import Package, TAG
from dx2level import SCALE, actor_matrix
from dx2_native_save_as import (
    apply_location_plan, export_translation_copy, location_float_offsets,
    plan_translation_changes
)


def ci(value: int) -> bytes:
    if value < 0:
        if -value > 63:
            raise ValueError("test fixture supports only short negative compact indices")
        return bytes([0x80 | -value])
    if value < 64:
        return bytes([value])
    if value < 8192:
        return bytes([0x40 | (value & 63), value >> 6])
    raise ValueError("fixture offset too large")


NAMES = (
    "None", "Location", "Vector", "X", "Y", "Z",
    "StaticMeshActor", "StaticMeshActor__1", "Class", "FixtureFlag",
)


def fixture_gmp(x=100.0, y=200.0, z=300.0) -> bytes:
    # Property body: FString-style tagged struct with three float32 fields.
    nested = b"".join(
        ci(NAMES.index(axis)) + bytes([0x24]) + struct.pack("<f", value)
        for axis, value in zip("XYZ", (x, y, z))
    ) + ci(0)
    location = (
        ci(NAMES.index("Location")) + bytes([0x7A]) +
        ci(NAMES.index("Vector")) + struct.pack("<I", len(nested)) + nested
    )
    other = ci(NAMES.index("FixtureFlag")) + bytes([0x22]) + struct.pack("<i", 98765)
    payload = location + other + ci(0)
    # Unreal string names are signed compact lengths plus terminated bytes.
    names = b"".join(
        ci(len(name.encode("ascii")) + 1) + name.encode("ascii") +
        b"\0" + struct.pack("<I", 0)
        for name in NAMES
    )
    # Single import: class named StaticMeshActor.
    imports = (
        ci(0) + ci(NAMES.index("Class")) +
        struct.pack("<i", 0) + ci(NAMES.index("StaticMeshActor"))
    )
    names_offset = 76
    imports_offset = names_offset + len(names)
    exports_offset = imports_offset + len(imports)

    def export_entry(offset):
        return (
            ci(-1) + ci(0) + struct.pack("<i", 0) +
            ci(NAMES.index("StaticMeshActor__1")) + struct.pack("<I", 0) +
            ci(len(payload)) + ci(offset)
        )

    offset = exports_offset + len(export_entry(exports_offset + 14))
    for _ in range(5):
        updated = exports_offset + len(export_entry(offset))
        if updated == offset:
            break
        offset = updated
    exports = export_entry(offset)
    assert offset == exports_offset + len(exports)

    header = (
        struct.pack("<IHHI", TAG, 95, 69, 0) +
        struct.pack("<IIIIII", len(NAMES), names_offset,
                    1, exports_offset, 1, imports_offset) +
        struct.pack("<I", 0) + bytes(16) + struct.pack("<I", 1) +
        struct.pack("<II", 1, len(NAMES)) +
        struct.pack("<II", 0, 0)
    )
    assert len(header) == 76
    return header + names + imports + exports + payload


class NativeGmpSaveAsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "RetailFixture" / "M1_Test.gmp"
        self.source.parent.mkdir()
        self.source.write_bytes(fixture_gmp())
        self.actors_file = self.base / "Cache" / "actors.json"
        self.actors_file.parent.mkdir()
        self.actor = {
            "name": "StaticMeshActor__1", "class": "StaticMeshActor",
            "export": 1, "mesh": "FictionalBox",
            "location": [100.0, 200.0, 300.0],
            "rotation": [0, 0, 0],
        }
        self.actors = {
            "meta": {
                "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                "source_map": self.source.name,
            },
            "actors": [self.actor],
        }
        self.actors_file.write_text(json.dumps(self.actors))
        self.draft_path = self.actors_file.parent / "draft.json"
        matrix = actor_matrix({
            "x": 100.0, "y": 200.0, "z": 300.0,
            "rotation": [0, 0, 0],
        })
        self.transform = [
            matrix[0], matrix[1], matrix[2],
            matrix[4], matrix[5], matrix[6],
            matrix[8], matrix[9], matrix[10],
            120 * SCALE, 320 * SCALE, 240 * SCALE,
        ]
        self.draft = {
            "schema": "DX2Ed-prop-draft-v1",
            "read_only_source": True,
            "map_cache": str(self.actors_file.parent),
            "moved": [{"actor": self.actor["name"], "transform": self.transform}],
            "copies": [], "property_edits": [],
        }
        self.draft_path.write_text(json.dumps(self.draft))
        self.output = self.base / "IsolatedOutput" / self.source.name

    def test_true_unreal_package_fixture_roundtrip(self):
        original = Package(self.source)
        self.assertEqual(original.version, 95)
        self.assertEqual(original.class_name(original.exports[0]), "StaticMeshActor")
        self.assertEqual(len(original.scene_actors()[0]), 1)
        offsets = location_float_offsets(original, original.exports[0])
        self.assertEqual(
            [struct.unpack_from("<f", original.data, offsets[k])[0] for k in "XYZ"],
            [100.0, 200.0, 300.0]
        )
        plan = plan_translation_changes(original, self.actors, self.draft)
        self.assertEqual(len(plan), 1)
        changed = apply_location_plan(original.data, plan)
        self.assertEqual(len(changed), len(original.data))
        self.assertIn(struct.pack("<i", 98765), changed)
        self.assertNotEqual(changed, original.data)

    def test_save_as_reopens_and_original_remains_identical(self):
        source_before = self.source.read_bytes()
        dry = export_translation_copy(
            self.source, self.actors_file, self.draft_path, self.output,
            dry_run=True
        )
        self.assertEqual(dry["status"], "dry-run")
        self.assertFalse(self.output.exists())
        result = export_translation_copy(
            self.source, self.actors_file, self.draft_path, self.output
        )
        self.assertEqual(result["status"], "written-unverified")
        self.assertFalse(result["game_verified"])
        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(self.output.stat().st_size, self.source.stat().st_size)
        patched = Package(self.output)
        offsets = location_float_offsets(patched, patched.exports[0])
        self.assertAlmostEqual(struct.unpack_from("<f", patched.data, offsets["X"])[0], 120, places=4)
        self.assertAlmostEqual(struct.unpack_from("<f", patched.data, offsets["Y"])[0], 240, places=4)
        self.assertAlmostEqual(struct.unpack_from("<f", patched.data, offsets["Z"])[0], 320, places=4)
        self.assertEqual(patched.props_after_ignore if hasattr(patched, "props_after_ignore") else
                         patched.decode_object(patched.exports[0])["FixtureFlag"], 98765)
        self.assertTrue(self.output.with_suffix(".dx2ed-manifest.json").is_file())
        with self.assertRaisesRegex(FileExistsError, "overwrite"):
            export_translation_copy(
                self.source, self.actors_file, self.draft_path, self.output)

    def test_edited_rotation_is_rejected(self):
        self.draft["moved"][0]["transform"][0] = 0.5
        self.draft_path.write_text(json.dumps(self.draft))
        with self.assertRaisesRegex(ValueError, "rotation/scale"):
            export_translation_copy(self.source, self.actors_file, self.draft_path, self.output)
        self.assertFalse(self.output.exists())

    def test_new_actor_or_property_is_rejected(self):
        self.draft["copies"].append({"name": "DraftProp_1", "from_actor": "Brush::Box"})
        self.draft_path.write_text(json.dumps(self.draft))
        with self.assertRaisesRegex(ValueError, "native writer"):
            export_translation_copy(self.source, self.actors_file, self.draft_path, self.output)
        self.assertFalse(self.output.exists())

    def test_wrong_hash_is_rejected(self):
        self.actors["meta"]["source_sha256"] = "0" * 64
        self.actors_file.write_text(json.dumps(self.actors))
        with self.assertRaisesRegex(ValueError, "SHA"):
            export_translation_copy(self.source, self.actors_file, self.draft_path, self.output)

    def test_retail_folder_and_wrong_name_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "OUTSIDE"):
            export_translation_copy(
                self.source, self.actors_file, self.draft_path,
                self.source.parent / "M1_Test.gmp")
        with self.assertRaisesRegex(ValueError, "filename"):
            export_translation_copy(
                self.source, self.actors_file, self.draft_path,
                self.base / "Other" / "Wrong_Name.gmp")

    def test_source_actor_identity_mismatch_rejected(self):
        self.actor["export"] = 5
        self.actors_file.write_text(json.dumps(self.actors))
        with self.assertRaisesRegex(ValueError, "Invalid export"):
            export_translation_copy(self.source, self.actors_file, self.draft_path, self.output)

    def test_draft_cache_mismatch_rejected(self):
        self.draft["map_cache"] = str(self.base / "DifferentMap")
        self.draft_path.write_text(json.dumps(self.draft))
        with self.assertRaisesRegex(ValueError, "different DX2Ed map cache"):
            export_translation_copy(self.source, self.actors_file, self.draft_path, self.output)


if __name__ == "__main__":
    unittest.main()
