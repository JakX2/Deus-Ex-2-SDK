"""Fixture-only tests for in-memory tagged int32/float32 actor edit parity.

The original native fixture has a tagged int32, then this suite adds a
synthetic Unreal state frame through the upstream package writer. No game
source data is required or committed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "package_writer"))
sys.path.insert(0, str(ROOT / "native_editor" / "tests"))
from dx2_scalar_property_probe import compare_scalar, main
from test_native_save_as import fixture_gmp
from upkg import Package as T3Package
from upkgwrite import PackageWriter
from dx2inspect import HAS_STACK


def stateful_fixture(path: Path, kind: str) -> bytes:
    base = fixture_gmp()
    source = T3Package(path, data=base)
    writer = PackageWriter(source)
    original_body = source.export_bytes(source.exports[0])
    if kind == "float":
        token = bytes([9, 0x22]) + struct.pack("<i", 98765)
        replacement = bytes([9, 0x24]) + struct.pack("<f", 1.25)
        if original_body.count(token) != 1:
            raise AssertionError("Expected exactly one original FixtureFlag int32 tag")
        original_body = original_body.replace(token, replacement, 1)
    writer.exports[0].flags |= HAS_STACK
    state_frame = bytes([0, 0]) + bytes(8) + bytes(4)
    writer.set_object(0, state_frame + original_body)
    result = writer.write()
    path.write_bytes(result)
    return result


class NativeScalarPropertyParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "M1_Test.gmp"

    def test_existing_actor_int32_tagged_edit_matches_entire_package(self):
        raw = stateful_fixture(self.source, "int")
        source_hash = hashlib.sha256(raw).hexdigest()
        result = compare_scalar(self.source, 1, "StaticMeshActor__1",
                                "FixtureFlag", "int", 98765, 98766,
                                source_sha256=source_hash)
        self.assertEqual(result["status"], "in-memory-match-only")
        self.assertTrue(result["serializers_agree_byte_for_byte"])
        self.assertFalse(result["runtime_game_verified"])
        self.assertFalse(result["edited_package_written"])
        self.assertLessEqual(result["changed_bytes"], 4)
        self.assertGreater(result["changed_bytes"], 0)
        self.assertEqual(self.source.read_bytes(), raw)
        self.assertEqual(main([str(self.source), "--source-sha256", source_hash,
                               "--actor-export", "1", "--actor-name",
                               "StaticMeshActor__1", "--property", "FixtureFlag",
                               "--kind", "int", "--expect", "98765",
                               "--replace", "98766"]), 0)

    def test_existing_actor_float32_tagged_edit_matches_entire_package(self):
        raw = stateful_fixture(self.source, "float")
        source_hash = hashlib.sha256(raw).hexdigest()
        result = compare_scalar(self.source, 1, "StaticMeshActor__1",
                                "FixtureFlag", "float", 1.25, 2.5,
                                source_sha256=source_hash)
        self.assertTrue(result["serializers_agree_byte_for_byte"])
        self.assertEqual(result["original_bytes_hex"], struct.pack("<f", 1.25).hex())
        self.assertEqual(result["replacement_bytes_hex"], struct.pack("<f", 2.5).hex())
        self.assertFalse(result["source_modified"])
        self.assertEqual(self.source.read_bytes(), raw)

    def test_noop_stale_hash_wrong_actor_and_wrong_original_are_rejected(self):
        raw = stateful_fixture(self.source, "int")
        source_hash = hashlib.sha256(raw).hexdigest()
        def probe(**kwargs):
            args = dict(
                source=self.source, actor_export=1, actor_name="StaticMeshActor__1",
                property_name="FixtureFlag", kind="int", expected=98765,
                replacement=1, source_sha256=source_hash
            )
            args.update(kwargs)
            return compare_scalar(**args)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            probe(source_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "No change"):
            probe(replacement=98765)
        with self.assertRaisesRegex(ValueError, "name does not match"):
            probe(actor_name="StaticMeshActor__999")
        with self.assertRaisesRegex(ValueError, "Pinned original"):
            probe(expected=555)
        with self.assertRaisesRegex(ValueError, "exactly one existing"):
            probe(property_name="NonExisting")
        with self.assertRaisesRegex(ValueError, "not a standalone"):
            probe(kind="float", expected=1., replacement=2.)
        self.assertEqual(self.source.read_bytes(), raw)

    def test_rejects_invalid_scalar_types_and_values(self):
        from dx2_scalar_property_probe import _value_bytes
        for value in (True, 2 ** 40, -2 ** 40, 1.25):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _value_bytes("int", value)
        for value in (True, float("nan"), float("inf"), float("-inf"), 1e100):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _value_bytes("float", value)

    def test_catalog_lists_only_independently_verified_existing_scalars(self):
        from dx2_native_scalar_catalog import inventory_scalar_properties
        raw = stateful_fixture(self.source, "int")
        catalog = inventory_scalar_properties(self.source)
        self.assertTrue(catalog["read_only"])
        self.assertEqual(catalog["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(catalog["actors_scanned"], 1)
        self.assertEqual(catalog["actors_unparsed"], 0)
        self.assertEqual(catalog["scalar_fields_found"], 1)
        field = catalog["fields"][0]
        self.assertEqual(field["property"], "FixtureFlag")
        self.assertEqual(field["kind"], "int")
        self.assertEqual(field["value"], 98765)
        self.assertEqual(raw[field["offset"]:field["offset"]+4].hex(),
                         field["raw_hex"])
        self.assertFalse(catalog["native_property_write_enabled"])
        self.assertEqual(self.source.read_bytes(), raw)

    def test_catalog_accepts_float_tags_and_rejects_retail_source_writes(self):
        from dx2_native_scalar_catalog import inventory_scalar_properties, main as inventory_cli
        raw = stateful_fixture(self.source, "float")
        report = inventory_scalar_properties(self.source)
        self.assertEqual(report["fields"][0]["kind"], "float")
        self.assertEqual(report["fields"][0]["value"], 1.25)
        output = self.source.parent / "source-scalar-index.json"
        self.assertEqual(inventory_cli([str(self.source),"--output",str(output)]),0)
        self.assertEqual(self.source.read_bytes(),raw)
        with self.assertRaises(ValueError):
            # Calls to original unmodified game files are always read-only:
            # this test demonstrates the separate JSON-only output guard.
            from dx2_scalar_property_probe import _value_bytes
            _value_bytes("float", float("inf"))
        self.assertEqual(inventory_cli([str(self.source),"--output",str(self.source)]),1)
        self.assertEqual(self.source.read_bytes(),raw)
        self.assertEqual(inventory_cli([str(self.source),"--output",str(output)]),1)

    def test_missing_actor_state_frame_is_rejected(self):
        raw = fixture_gmp()
        self.source.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "actor state frame"):
            compare_scalar(self.source, 1, "StaticMeshActor__1",
                           "FixtureFlag", "int", 98765, 98766,
                           source_sha256=hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
