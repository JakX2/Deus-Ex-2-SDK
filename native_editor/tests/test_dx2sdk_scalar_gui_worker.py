"""DX2SDK v0.14: native scalar GUI bridge, synthetic UE95 source only.

The GMP and its private actors.json are fabricated by fixture_gmp().
No Deus Ex original game assets, bytes, scripts, maps or runtime.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dx2inspect import Package
from dx2sdk.scalars import _native_tags
from test_native_save_as import fixture_gmp
from tools.build_dx2sdk_source_release import ARCHIVE, build

WORKER = ROOT / "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py"
SCHEMA = "DX2Ed-GUI-original-native-scalar-worker-v1"


class NativeScalarGUIWorkerTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2ed_v014_native_scalar_gui_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "PrivateSource" / "Content" / "DX2" / "Maps" / "M1_Test.gmp"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(fixture_gmp())
        self.cache = self.root / "PrivateCache" / "actors.json"
        self.cache.parent.mkdir()
        self._cache()
        self._pin()
        self.output = self.root / "Isolated" / self.source.name
        self.manifest = self.output.with_suffix(".dx2sdk-scalar.json")
        self.req = {
            "actor": "StaticMeshActor__1",
            "export": 1,
            "property": "FixtureFlag",
            "type": "int32",
            "expected": 98765,
            "replacement": 123456,
        }

    def _cache(self):
        self.cache.write_text(json.dumps({
            "meta": {
                "source_map": self.source.name,
                "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            },
            "actors": [{
                "name": "StaticMeshActor__1", "class": "StaticMeshActor",
                "mesh": "InventedCube", "export": 1,
                "location": [100.0, 200.0, 300.0],
                "rotation": [0, 0, 0], "game_properties": [],
            }],
        }, sort_keys=True))

    def _pin(self):
        self.map_sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.cache_sha = hashlib.sha256(self.cache.read_bytes()).hexdigest()

    def cli(self, action, *, script=WORKER, request=None, output=None,
            actor=None, export=None, map_sha=None, cache_sha=None,
            source=None, cache=None):
        command = [
            sys.executable, "-B", str(script), action,
            "--map", str(source or self.source),
            "--actors", str(cache or self.cache),
            "--source-sha256", map_sha or self.map_sha,
            "--actors-sha256", cache_sha or self.cache_sha,
        ]
        if request is not None:
            command += ["--request-json", json.dumps(request, allow_nan=True)]
        if output is not None:
            command += ["--output", str(output)]
        if actor is not None:
            command += ["--actor", actor]
        if export is not None:
            command += ["--export", str(export)]
        run = subprocess.run(command, cwd=self.root, text=True,
                             capture_output=True, timeout=60)
        try:
            doc = json.loads(run.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(run.stdout + run.stderr) from exc
        return run, doc

    def test_actor_list_only_original_staticmesh_and_authenticated_cache(self):
        run, doc = self.cli("list")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(doc["bridge_schema"], SCHEMA)
        self.assertEqual(doc["status"], "original_staticmeshactor_list")
        self.assertEqual(doc["source_sha256"], self.map_sha)
        self.assertEqual(doc["actors_sha256"], self.cache_sha)
        self.assertEqual(doc["shown_count"], 1)
        self.assertEqual(doc["actors"], [
            {"actor": "StaticMeshActor__1", "export": 1,
             "actor_class": "StaticMeshActor"}])
        self.assertTrue(doc["source_actor_cache_verified"])
        self.assertFalse(doc["runtime_game_verified"])
        self.assertFalse(doc["native_new_actor_creation_enabled"])
        self.assertFalse(self.output.exists())

    def test_original_typed_int32_inventory_and_source_pinned_single_field(self):
        run, doc = self.cli("fields", actor="StaticMeshActor__1", export=1)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(doc["status"], "original_scalar_field_inventory")
        self.assertEqual(doc["export"], 1)
        self.assertEqual(doc["fields"], [
            {"property": "FixtureFlag", "type": "int32", "source_value": 98765}])
        for actor,export in (("OtherActor",1),("StaticMeshActor__1",2),
                             ("StaticMeshActor__1",0)):
            with self.subTest(actor=actor,export=export):
                bad, response = self.cli("fields", actor=actor, export=export)
                self.assertEqual(bad.returncode, 2, bad.stderr)
                self.assertEqual(response["status"], "refused")
        self.assertEqual(self.source.read_bytes(), fixture_gmp())

    def test_preview_does_not_write_and_apply_has_whole_file_verification(self):
        preview, doc = self.cli("preview", request=self.req, output=self.output)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(doc["status"], "dry-run")
        self.assertEqual(doc["action"], "preview")
        self.assertEqual(doc["expected"], 98765)
        self.assertEqual(doc["replacement"], 123456)
        self.assertEqual(doc["type"], "int32")
        self.assertEqual(doc["export"], 1)
        self.assertGreater(doc["changed_byte_count"], 0)
        self.assertLessEqual(doc["changed_byte_count"], 4)
        self.assertTrue(doc["source_noop_T3SDK_parity_verified"])
        self.assertFalse(doc["edited_package_written"])
        self.assertFalse(doc["saved_binary_structure_verified"])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())
        saved, record = self.cli("apply", request=self.req, output=self.output)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(record["status"],
                         "isolated-native-scalar-verified-runtime-unverified")
        self.assertTrue(record["saved_binary_structure_verified"])
        self.assertTrue(record["independent_saved_whole_GMP_byte_verification"])
        self.assertEqual(record["changed_byte_count"], doc["changed_byte_count"])
        self.assertFalse(record["runtime_game_verified"])
        self.assertFalse(record["source_original_modified"])
        self.assertTrue(self.output.exists())
        self.assertTrue(self.manifest.exists())
        self.assertEqual(Package(self.output).decode_object(
            Package(self.output).exports[0])["FixtureFlag"], 123456)
        self.assertEqual(self.source.read_bytes(), fixture_gmp())
        refused, response = self.cli("apply", request=self.req, output=self.output)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(response["status"], "refused")

    def test_rejects_wrong_value_type_original_identity_and_protected_names(self):
        failures = [
            {**self.req, "expected": 98766},
            {**self.req, "expected": True},
            {**self.req, "replacement": 123456.0},
            {**self.req, "replacement": True},
            {**self.req, "replacement": 98765},
            {**self.req, "replacement": 2147483648},
            {**self.req, "replacement": -2147483649},
            {**self.req, "property": "Location"},
            {**self.req, "property": "Rotation"},
            {**self.req, "property": "SomeGameSys"},
            {**self.req, "type": "float32"},
            {**self.req, "export": 2},
            {**self.req, "actor": "Unknown"},
            {**self.req, "injected": "write everything"},
        ]
        for item in failures:
            with self.subTest(item=item):
                run, doc = self.cli("apply", request=item, output=self.output)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(doc["status"], "refused")
                self.assertFalse(self.output.exists())
                self.assertFalse(self.manifest.exists())
        self.assertEqual(self.source.read_bytes(), fixture_gmp())

    def test_refuses_foreign_source_and_cache_digest_or_stale_bytes(self):
        for args in ({"map_sha": "0"*64}, {"cache_sha": "0"*64},
                     {"map_sha":"invalid"}, {"cache_sha":"A"*64}):
            with self.subTest(args=args):
                run, doc = self.cli("list", **args)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(doc["status"], "refused")
        original_cache = self.cache.read_bytes()
        self.cache.write_bytes(original_cache+b" ")
        stale, doc = self.cli("apply", request=self.req, output=self.output)
        self.assertEqual(stale.returncode, 2)
        self.assertFalse(self.output.exists())
        self.cache.write_bytes(original_cache)
        self.source.write_bytes(self.source.read_bytes()+b"tampered")
        stale, doc = self.cli("apply", request=self.req, output=self.output)
        self.assertEqual(stale.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_refuses_original_retail_maps_output_and_existing_private_manifest(self):
        wrong = (self.source, self.source.parent / "nested" / self.source.name,
                 self.root / "OtherGame" / "Content" / "DX2" / "Maps" / self.source.name,
                 self.root / "Wrong.gmp")
        for target in wrong:
            with self.subTest(target=target):
                run, doc = self.cli("apply", request=self.req, output=target)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(doc["status"], "refused")
                self.assertFalse(self.output.exists())
        self.manifest.parent.mkdir()
        self.manifest.write_text("existing private manifest")
        run, doc = self.cli("apply", request=self.req, output=self.output)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual(self.manifest.read_text(), "existing private manifest")
        self.assertFalse(self.output.exists())

    def test_source_float32_variant_only_existing_four_byte_kind4(self):
        # The invented original has UE95 int32 FixtureFlag. Switch exactly
        # its original native TAG type nibble to FloatProperty, then change
        # its original FOUR-BYTE payload to an original authored 12.5f.
        pkg = Package(self.source)
        exp = pkg.exports[0]
        rows = [t for t in _native_tags(pkg, exp) if t["property"] == "FixtureFlag"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["native_kind"], 2)
        offset = rows[0]["offset"]
        self.assertEqual(pkg.data[offset-1] & 0x0f, 2)
        raw = bytearray(self.source.read_bytes())
        raw[offset-1] = (raw[offset-1]&0xf0)|4
        raw[offset:offset+4] = struct.pack("<f", 12.5)
        self.source.write_bytes(raw)
        self._cache()
        self._pin()
        edit = {**self.req, "type":"float32", "expected":12.5,
                "replacement":15.75}
        inv, doc = self.cli("fields",actor="StaticMeshActor__1", export=1)
        self.assertEqual(inv.returncode,0,inv.stderr)
        self.assertEqual(doc["fields"],[
            {"property":"FixtureFlag","type":"float32","source_value":12.5}])
        preview,doc=self.cli("preview",request=edit,output=self.output)
        self.assertEqual(preview.returncode,0,preview.stderr)
        self.assertEqual(doc["replacement"],15.75)
        self.assertFalse(self.output.exists())
        apply,doc=self.cli("apply",request=edit,output=self.output)
        self.assertEqual(apply.returncode,0,apply.stderr)
        self.assertTrue(doc["saved_binary_structure_verified"])
        self.assertEqual(Package(self.output).decode_object(
            Package(self.output).exports[0])["FixtureFlag"],15.75)
        for value in (float("nan"),float("inf"),1e8, True):
            with self.subTest(value=value):
                bad, _ = self.cli("preview",request={**edit,"replacement":value},
                                  output=self.root/"New"/self.source.name)
                self.assertEqual(bad.returncode,2,bad.stderr)

    def test_extracted_portable_python_worker_needs_no_repository(self):
        archive_file = self.root / "v014.zip"
        build(ROOT, archive_file)
        rel = "native_editor/godot_editor/backend/dx2_sdk_scalar_worker.py"
        with ZipFile(archive_file) as z:
            self.assertIn(f"{ARCHIVE}/{rel}",z.namelist())
            z.extractall(self.root/"Extracted")
        script = self.root/"Extracted"/ARCHIVE/rel
        scan,doc=self.cli("list",script=script)
        self.assertEqual(scan.returncode,0,scan.stderr)
        fields,doc=self.cli("fields",script=script,actor="StaticMeshActor__1",export=1)
        self.assertEqual(fields.returncode,0,fields.stderr)
        preview,doc=self.cli("preview",script=script,
                              request=self.req,output=self.output)
        self.assertEqual(preview.returncode,0,preview.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
