"""Asset-free native DX2 ambient sound ZoneProperties editing tests.

Build a synthetic v95 map, then make two original-style ZoneProperties
actors with different authored stream names. Never require game assets.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / "native_editor/tests",
               ROOT / "native_editor/package_writer",
               ROOT / "third_party/t3sdk_assets"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from test_dx2_actor_clone_probe import level_fixture
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter, enc_fstring
from t3pack import apply_edits, verify_patch
from dx2_zone_sound_probe import compare_zone_schema, write_isolated, SCHEMA


def zone_fixture(path: Path):
    level_fixture(path)
    pkg = Package(path)
    writer = PackageWriter(pkg)
    # Reuse the synthetic import class entry, not a retail actor or binary.
    actor_export = writer.exports[0]
    imported_class = -actor_export.class_ref - 1
    assert imported_class >= 0
    writer.imports[imported_class].name = writer.name_index("ZoneProperties")
    actor_export.name = writer.name_index("ZoneProperties__1")
    act = ActorEdit(writer, pkg.exports[0])
    act.set_block(1286, enc_fstring("TestSmall"), "StreamSchema2",
                  insert_id=(4 << 16) | 1286)
    act.set_block(1287, enc_fstring("TestMap"), "StreamSchema1",
                  insert_id=(4 << 16) | 1287)
    act.set_block(1467, enc_fstring("TestLoopA"), "NonStreamSchema1",
                  insert_id=(4 << 16) | 1467)
    assert act.commit()
    path.write_bytes(writer.write())
    parsed = Package(path)
    assert parsed.export_class(parsed.exports[0]) == "ZoneProperties"
    assert parsed.read_actor(parsed.exports[0]).block(1286).value == "TestSmall"
    patch = apply_edits(parsed, {"actors": {}, "removed": [],
                                 "added": [{"copy_of": "ZoneProperties__1",
                                            "gamesys": {"prop1286": "TestLarge",
                                                        "prop1467": "TestLoopB"}}]})
    final = patch.writer.write()
    path.write_bytes(final)
    check = Package(path)
    assert check.level_actors() == [2, 0, 1, 3]
    assert check.read_actor(check.exports[2]).block(1286).value == "TestLarge"
    return final


class ZoneSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "Original" / "M1_Test.gmp"
        self.source.parent.mkdir()
        self.original = zone_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.kw = {"source_sha256": self.sha,
                   "actor_export": 1, "actor_name": "ZoneProperties__1",
                   "property_id": 1286, "expect": "TestSmall",
                   "replace": "TestLarge"}

    def test_existing_sound_zone_schema_only_modifies_one_actor(self):
        report, updated = compare_zone_schema(self.source, **self.kw)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertTrue(report["reverse_payload_parity"])
        self.assertTrue(report["original_exports_preserved_except_target"])
        self.assertFalse(report["source_modified"])
        self.assertFalse(report["runtime_verified"])
        self.assertFalse(report["creates_sound_emitter"])
        self.assertEqual(report["replacement_schema"], "TestLarge")
        self.assertEqual(self.source.read_bytes(), self.original)
        newer = Package(self.source, data=updated)
        old = Package(self.source)
        self.assertEqual(newer.level_actors(), old.level_actors())
        self.assertEqual(newer.read_actor(newer.exports[0]).block(1286).value,
                         "TestLarge")
        for index in range(1, len(old.exports)):
            self.assertEqual(old.export_bytes(old.exports[index]),
                             newer.export_bytes(newer.exports[index]))

    def test_nonstream_existing_schema_and_isolated_manifest(self):
        opts = {**self.kw, "property_id": 1467,
                "expect": "TestLoopA", "replace": "TestLoopB"}
        output = self.source.parent.parent / "Research" / self.source.name
        record = write_isolated(self.source, output, **opts)
        self.assertEqual(record["property_name"], "NonStreamSchema1")
        self.assertTrue(output.exists())
        self.assertTrue(output.with_suffix(".dx2ed-sound-zone.json").exists())
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),
                         record["output_sha256"])
        with self.assertRaises(FileExistsError):
            write_isolated(self.source, output, **opts)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuses_unsafe_or_unverified_schema_mutations(self):
        bad = [
            {"expect":"wrong"},
            {"replace":"NeverSeen"},
            {"replace":"TestSmall"},
            {"replace":"../../evil"},
            {"property_id":92},
            {"actor_name":"StaticMeshActor__1"},
            {"actor_export":2},
            {"source_sha256":"0"*64},
        ]
        for updates in bad:
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                compare_zone_schema(self.source, **{**self.kw, **updates})
        with self.assertRaises(ValueError):
            write_isolated(
                self.source,
                self.source.parent.parent / "Game" / "Content" / "DX2" / "Maps" / self.source.name,
                **self.kw)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_reports_in_memory_validation_without_game_writes(self):
        script = ROOT / "native_editor/package_writer/dx2_zone_sound_probe.py"
        cmd = [sys.executable, str(script), str(self.source),
               "--source-sha256", self.sha, "--actor-export", "1",
               "--actor-name", "ZoneProperties__1",
               "--property-id", "1286", "--expect", "TestSmall",
               "--replace", "TestLarge"]
        completed = subprocess.run(cmd, text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr+completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["status"],
                         "in-memory-verified-runtime-unverified")
        refused = subprocess.run(cmd[:-1] + ["InventedSchema"], text=True,
                                 capture_output=True)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)["status"], "refused")
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
