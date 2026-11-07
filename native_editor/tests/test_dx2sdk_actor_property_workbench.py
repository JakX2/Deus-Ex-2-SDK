"""DX2SDK v0.16 source-authored Actor property workbench tests.

All original UE95 package bytes are invented by a local fixture; no retail
map, proprietary actor content, or native gameplay compatibility is inferred.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dx2sdk import DX2Map
from dx2sdk.actor_workbench import SCHEMA, original_actor_property_workbench
from test_dx2sdk_multi_scalar_gui_worker import invented_two_actor_numeric_gmp
from tools.build_dx2sdk_source_release import ARCHIVE, build

WORKER = ROOT / "native_editor/godot_editor/backend/dx2_sdk_multi_scalar_worker.py"


class OriginalActorPropertyWorkbenchTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_native_property_workbench_v016_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "Original" / "M1_Invented.gmp"
        self.source.parent.mkdir()
        self.original = invented_two_actor_numeric_gmp()
        self.source.write_bytes(self.original)
        self.cache = self.root / "Cache" / "actors.json"
        self.cache.parent.mkdir()
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.cache.write_text(json.dumps({
            "meta": {"source_map": self.source.name, "source_sha256": self.sha},
            "actors": [
                {"name": "StaticMeshActor__1", "class": "StaticMeshActor",
                 "export": 1, "location": [100., 200., 300.],
                 "rotation": [0, 0, 0], "mesh": "Fictional01"},
                {"name": "StaticMeshActor__2", "class": "StaticMeshActor",
                 "export": 2, "location": [400., 500., 600.],
                 "rotation": [0, 0, 0], "mesh": "Fictional02"},
            ],
        }, sort_keys=True))
        self.cache_sha = hashlib.sha256(self.cache.read_bytes()).hexdigest()
        self.world = DX2Map.open(self.source, self.cache)

    def cli(self, *args, cwd=ROOT, worker=False):
        run = subprocess.run(
            [sys.executable, "-B", str(WORKER), *args] if worker
            else [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=cwd, text=True, capture_output=True, timeout=70)
        try:
            data = json.loads(run.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(run.stdout + run.stderr) from exc
        return run, data

    def test_original_typed_tags_and_protected_opaque_are_distinct(self):
        doc = self.world.original_actor_property_workbench("StaticMeshActor__1")
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["status"], "source-original-actor-property-catalog")
        self.assertEqual(doc["source_sha256"], self.sha)
        self.assertEqual(doc["actors_sha256"], self.cache_sha)
        self.assertEqual(doc["actor"], "StaticMeshActor__1")
        self.assertEqual(doc["export"], 1)
        self.assertEqual(doc["original_location_native_xyz"], [100., 200., 300.])
        self.assertEqual(doc["source_top_level_tag_count"], 3)
        self.assertEqual(doc["eligible_original_numeric_count"], 2)
        self.assertEqual(doc["read_only_original_tag_count"], 1)
        self.assertTrue(doc["read_only"])
        self.assertFalse(doc["new_tag_insertion_enabled"])
        self.assertFalse(doc["gameplay_runtime_verified"])
        groups = {c["key"]: c for c in doc["categories"]}
        eligible = groups["eligible-original-numeric"]["fields"]
        self.assertEqual({x["property"]: x["original_value"] for x in eligible},
                         {"FixtureFlag": 98765, "FixtureFloat": 12.5})
        self.assertEqual({x["native_kind"] for x in eligible}, {2, 4})
        self.assertTrue(all(x["editable_existing_tag"] and
                            x["serialized_payload_size"] == 4
                            and not x["indexed_or_special"]
                            for x in eligible))
        protect = groups["protected-original"]["fields"]
        self.assertEqual(len(protect), 1)
        self.assertEqual(protect[0]["property"], "Location")
        self.assertIsNone(protect[0]["original_value"])
        self.assertFalse(protect[0]["editable_existing_tag"])
        self.assertEqual(sum(c["count"] for c in doc["categories"]), 3)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_multiple_original_actors_use_distinct_evidence(self):
        first = self.world.original_actor_property_workbench("StaticMeshActor__1")
        second = self.world.original_actor_property_workbench("StaticMeshActor__2")
        self.assertEqual(second["export"], 2)
        self.assertEqual(second["original_location_native_xyz"], [400., 500., 600.])
        self.assertEqual(
            {r["property"]: r["original_value"] for
             r in second["categories"][0]["fields"]},
            {"FixtureFlag": 43210, "FixtureInt2": 44})
        self.assertNotEqual(
            first["categories"][0]["fields"][0]["source_byte_offset"],
            second["categories"][0]["fields"][0]["source_byte_offset"])
        self.assertFalse(self.root.joinpath("Isolated", self.source.name).exists())

    def test_other_tag_kinds_duplicates_index_flags_and_nonfinite_values_readonly(self):
        actual = self.world.original_actor_property_workbench("StaticMeshActor__1")
        good = actual["categories"][0]["fields"][0]["source_byte_offset"]
        artificial = [
            {"property": "OpaqueEngineBlock", "native_kind": 12,
             "size": 13, "offset": good, "has_array_or_special_flag": False},
            {"property": "FixtureFlag", "native_kind": 2,
             "size": 4, "offset": good + 4, "has_array_or_special_flag": False},
            {"property": "FixtureFlag", "native_kind": 2,
             "size": 4, "offset": good + 8, "has_array_or_special_flag": False},
            {"property": "IndexedFoo", "native_kind": 4,
             "size": 4, "offset": good + 12, "has_array_or_special_flag": True},
            {"property": "WrongNumericSize", "native_kind": 2,
             "size": 8, "offset": good + 16, "has_array_or_special_flag": False},
            {"property": "Location", "native_kind": 10,
             "size": 18, "offset": good + 24, "has_array_or_special_flag": False},
        ]
        with patch("dx2sdk.actor_workbench._native_tags", return_value=artificial), patch(
                "dx2sdk.actor_workbench._numeric_candidates", return_value=[]):
            doc = original_actor_property_workbench(self.world, "StaticMeshActor__1")
        counts = {c["key"]: c["count"] for c in doc["categories"]}
        self.assertEqual(counts, {
            "eligible-original-numeric": 0,
            "protected-original": 1,
            "duplicate-original-name": 2,
            "indexed-or-special": 1,
            "unsupported-numeric-layout": 1,
            "opaque-uninterpreted": 1,
        })
        self.assertEqual(doc["read_only_original_tag_count"], 6)
        self.assertTrue(all(not r["editable_existing_tag"] and r["original_value"] is None
                            for c in doc["categories"] for r in c["fields"]))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_public_sdk_cli_and_sha_locked_worker_catalog(self):
        run, doc = self.cli(
            "actor-properties", "--map", str(self.source), "--actors",
            str(self.cache), "--actor", "StaticMeshActor__1")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["eligible_original_numeric_count"], 2)
        worker_args = [
            "catalog", "--map", str(self.source), "--actors", str(self.cache),
            "--source-sha256", self.sha, "--actors-sha256", self.cache_sha,
            "--actor", "StaticMeshActor__1", "--export", "1",
        ]
        run, report = self.cli(*worker_args, worker=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(report["action"], "catalog")
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["categories"], doc["categories"])
        self.assertFalse(report["new_tag_insertion_enabled"])
        self.assertFalse(report["gameplay_runtime_verified"])
        for override in (
            ["--export", "2"], ["--actor", "ForeignActor"],
            ["--source-sha256", "0" * 64],
            ["--actors-sha256", "0" * 64],
        ):
            argv = worker_args.copy()
            name = override[0]
            argv[argv.index(name) + 1] = override[1]
            bad, rejected = self.cli(*argv, worker=True)
            self.assertEqual(bad.returncode, 2, bad.stderr)
            self.assertEqual(rejected["status"], "refused")

    def test_missing_cache_unrecognized_actor_stale_source_and_cache_refused(self):
        for actor in ("UnknownActor", "Light__0", "", "StaticMeshActor__3"):
            with self.subTest(actor=actor), self.assertRaises(ValueError):
                self.world.original_actor_property_workbench(actor)
        with self.assertRaises(ValueError):
            DX2Map.open(self.source).original_actor_property_workbench("StaticMeshActor__1")
        self.cache.write_text(self.cache.read_text() + " ")
        with self.assertRaises(ValueError):
            self.world.original_actor_property_workbench("StaticMeshActor__1")
        self.cache.write_text(self.cache.read_text().rstrip())
        self.source.write_bytes(self.original + b"drift")
        with self.assertRaises(ValueError):
            self.world.original_actor_property_workbench("StaticMeshActor__1")

    def test_portable_extracted_sdk_supports_actor_property_workbench_and_bridge(self):
        archive = self.root / "v016.zip"
        build(ROOT, archive)
        rel = "dx2sdk/actor_workbench.py"
        bridge = "native_editor/godot_editor/backend/dx2_sdk_multi_scalar_worker.py"
        with ZipFile(archive) as z:
            self.assertIn(f"{ARCHIVE}/{rel}", z.namelist())
            self.assertIn(f"{ARCHIVE}/{bridge}", z.namelist())
            z.extractall(self.root / "Unpacked")
        cwd = self.root / "Unpacked" / ARCHIVE
        run, doc = self.cli(
            "actor-properties", "--map", str(self.source), "--actors",
            str(self.cache), "--actor", "StaticMeshActor__2", cwd=cwd)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(doc["export"], 2)
        worker = cwd / bridge
        call = subprocess.run([
            sys.executable, "-B", str(worker), "catalog", "--map", str(self.source),
            "--actors", str(self.cache), "--source-sha256", self.sha,
            "--actors-sha256", self.cache_sha, "--actor", "StaticMeshActor__2",
            "--export", "2",
        ], cwd=cwd, capture_output=True, text=True, timeout=60)
        self.assertEqual(call.returncode, 0, call.stderr)
        self.assertEqual(json.loads(call.stdout)["eligible_original_numeric_count"], 2)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
