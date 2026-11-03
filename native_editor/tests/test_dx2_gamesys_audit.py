"""Synthetic Ion v95 native GameSys boundary and declared-name audit tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for directory in (
    ROOT / "native_editor" / "package_writer",
    ROOT / "native_editor" / "tests",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from test_native_save_as import fixture_gmp
from dx2_gamesys_audit import audit_gamesys, scan_dx2_gamesys, main
from dx2_package_roundtrip import _parse_both
from upkg import Package as T3Package
from upkgwrite import PackageWriter
from dx2inspect import HAS_STACK

FLOAT_ID = (0x0010 << 16) | 237
OBJECT_ID = (0x0002 << 16) | 43
UNKNOWN_ID = (0x0040 << 16) | 175


def fixture_with_gamesys(source: Path, *, bad_length=False) -> bytes:
    base = fixture_gmp()
    package = T3Package(source, data=base)
    writer = PackageWriter(package)
    payload = package.export_bytes(package.exports[0])
    writer.exports[0].flags |= HAS_STACK
    state = bytes([0, 0]) + bytes(8) + bytes(4)
    blocks = (
        struct.pack("<III", FLOAT_ID, 1, 4)
        + struct.pack("<f", 2.5)
        + struct.pack("<III", OBJECT_ID, 1, 1)
        + b"\x00"
        + struct.pack("<III", UNKNOWN_ID, 3, 3 if not bad_length else 10000)
        + b"\x7f\x98\xac"
        + struct.pack("<I", 0)
        + struct.pack("<I", 0)
    )
    writer.set_object(0, state + payload + blocks)
    raw = writer.write()
    source.write_bytes(raw)
    return raw


class NativeGameSysAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "M1_Test.gmp"

    def _cache(self, raw):
        cache = self.base / "actors.json"
        cache.write_text(json.dumps({
            "meta": {"source_sha256": hashlib.sha256(raw).hexdigest(),
                     "source_map": self.source.name},
            "actors": [{
                "export": 1, "name": "StaticMeshActor__1",
                "game_properties": [
                    {"id": 237, "version": 1, "encoding": "float"},
                    {"id": 43, "version": 1, "encoding": "object"},
                    {"id": 175, "version": 3, "encoding": "type0x40"},
                ],
            }],
        }))
        return cache

    def _schema(self):
        schema = self.base / "declared.json"
        schema.write_text(json.dumps({
            "schema": "dx2-catalog-0.1",
            "properties": {
                "237": {"name": "SyntheticLevelOpacity", "type": "float",
                        "declared_in": "Fixture.TestClass"},
                "43": {"name": "SyntheticMeshReference", "type": "object",
                       "declared_in": "Fixture.TestClass"},
            },
        }))
        return schema

    def test_full_native_block_boundaries_match_independent_t3sdk(self):
        raw = fixture_with_gamesys(self.source)
        t3, dx2 = _parse_both(self.source, raw)
        original_records, terminator = scan_dx2_gamesys(dx2, dx2.exports[0])
        self.assertEqual(len(original_records), 3)
        self.assertEqual(original_records[0]["encoded_id"], FLOAT_ID)
        self.assertEqual(original_records[1]["encoded_id"], OBJECT_ID)
        self.assertEqual(original_records[2]["encoded_id"], UNKNOWN_ID)
        for record in original_records:
            offset = record["payload_offset"]
            size = record["payload_bytes"]
            self.assertEqual(hashlib.sha256(raw[offset:offset+size]).hexdigest(),
                             record["payload_sha256"])
        self.assertEqual(raw[terminator:terminator+4], b"\x00\x00\x00\x00")
        self.assertEqual(t3.read_actor(t3.exports[0]).parse_error, None)

    def test_audit_and_source_declarations_preserve_unknown_types(self):
        raw = fixture_with_gamesys(self.source)
        cache, schema = self._cache(raw), self._schema()
        report = audit_gamesys(self.source, system_source=schema, actors_file=cache)
        self.assertTrue(report["read_only"])
        self.assertEqual(report["state_frame_actors_checked"], 1)
        self.assertEqual(report["verified_game_properties"], 3)
        self.assertEqual(report["actor_verification_errors"], 0)
        self.assertEqual(report["property_type_counts"],
                         {"float": 1, "object": 1, "type0x40": 1})
        self.assertEqual(report["property_ids_with_source_declarations"], 2)
        self.assertEqual(report["fields"][0]["source_declared_name"], "SyntheticLevelOpacity")
        self.assertEqual(report["fields"][0]["preview_value"], 2.5)
        self.assertTrue(report["fields"][1]["cached_actor_index_agrees"])
        self.assertIsNone(report["fields"][2]["preview_value"])
        self.assertFalse(report["native_gamesys_write_supported"])
        self.assertFalse(report["runtime_game_verified"])
        self.assertEqual(self.source.read_bytes(), raw)

    def test_original_dx2_opaque_type_word_0x40_uses_only_verified_alias(self):
        raw = fixture_with_gamesys(self.source)
        cache = self._cache(raw)
        data = json.loads(cache.read_text())
        data["actors"][0]["game_properties"][2]["encoding"] = "unknown"
        cache.write_text(json.dumps(data))
        report = audit_gamesys(self.source, actors_file=cache)
        self.assertEqual(report["fields"][2]["encoding"], "type0x40")
        self.assertIn("opaque original type word",
                      report["fields"][2]["cached_encoding_alias"])
        self.assertIsNone(report["fields"][2]["preview_value"])
        self.assertFalse(report["native_gamesys_write_supported"])
        self.assertEqual(self.source.read_bytes(), raw)

    def test_corrupt_block_length_fails_closed_without_writing(self):
        raw = fixture_with_gamesys(self.source, bad_length=True)
        with self.assertRaisesRegex(ValueError, "extends beyond actor|actor parse"):
            audit_gamesys(self.source)
        report = audit_gamesys(self.source, strict=False)
        self.assertEqual(report["verified_game_properties"], 0)
        self.assertEqual(report["actor_verification_errors"], 1)
        self.assertEqual(self.source.read_bytes(), raw)

    def test_cache_staleness_or_misordered_ids_is_rejected(self):
        raw = fixture_with_gamesys(self.source)
        cache = self._cache(raw)
        data = json.loads(cache.read_text())
        data["meta"]["source_sha256"] = "0" * 64
        cache.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "SHA"):
            audit_gamesys(self.source, actors_file=cache)
        data["meta"]["source_sha256"] = hashlib.sha256(raw).hexdigest()
        data["actors"][0]["game_properties"][0]["id"] = 999
        cache.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "property #0 differs"):
            audit_gamesys(self.source, actors_file=cache)

    def test_noop_audit_cli_exports_only_new_json(self):
        raw = fixture_with_gamesys(self.source)
        result = self.base / "index.json"
        self.assertEqual(main([str(self.source), "--output", str(result)]), 0)
        doc = json.loads(result.read_text())
        self.assertEqual(doc["verified_game_properties"], 3)
        self.assertEqual(self.source.read_bytes(), raw)
        self.assertEqual(main([str(self.source), "--output", str(self.source)]), 1)
        self.assertEqual(main([str(self.source), "--output", str(result)]), 1)


if __name__ == "__main__":
    unittest.main()
