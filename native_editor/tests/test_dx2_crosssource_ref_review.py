"""DX2Ed v0.63 synthetic cross-source GMP + IBD/TriggerScript review.

Tests pair a REAL structurally valid synthetic DX2 UE95 Level/actor
package with independently constructed original-style TSD/IBD bytes.
No proprietary assets or game installation modifications.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
for folder in (
    ROOT / "native_editor/tests",
    ROOT / "native_editor/package_writer",
    ROOT / "native_editor/godot_editor/backend",
    ROOT / "third_party/t3sdk_assets",
):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from test_dx2_actor_clone_probe import level_fixture
from test_dx2_script_ibd_provenance import tsd, ibd_resource
from dx2_actor_clone_probe import clone_in_memory
from dx2_crosssource_ref_review import (
    SCHEMA, review_original, export_private_report,
)
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter, enc_index


class SyntheticCrossSourceReferenceReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.game = self.root / "Game" / "Content" / "DX2"
        maps = self.game / "Maps"
        maps.mkdir(parents=True)
        self.map = maps / "SyntheticReferences.gmp"
        raw = level_fixture(self.map)
        _, clone = clone_in_memory(
            self.map, source_sha256=hashlib.sha256(raw).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(120.0, 0.0, 0.0))
        self.map.write_bytes(clone)
        self.map_sha = hashlib.sha256(clone).hexdigest()
        self.actors = self.root / "Cache" / "actors.json"
        self.actors.parent.mkdir()
        self.actors.write_text(json.dumps({
            "meta": {"source_map": self.map.name, "source_sha256": self.map_sha},
            "actors": [
                {"name": "StaticMeshActor__1", "export": 1,
                 "class": "StaticMeshActor", "game_properties": []},
                {"name": "StaticMeshActor__2", "export": 3,
                 "class": "StaticMeshActor", "game_properties": []},
            ],
        }))
        self.script_zip = self.game / "TriggerScript.zip"
        self.tsd = tsd("TS_TEST")
        with ZipFile(self.script_zip, "w") as archive:
            archive.writestr("Defs/TS_TEST.tsd", self.tsd)
        self.ibd = maps / "Kernel_TSDALL.ibd"
        self.ibd.write_bytes(ibd_resource(self.tsd[12:], "TS_TEST"))
        self.report = self.root / "PrivateResearch" / "cross_source.json"

    def _opts(self):
        return dict(
            source_sha256=self.map_sha, actor_export=1,
            actor_name="StaticMeshActor__1", actors_file=self.actors,
            scripts_file=self.script_zip, ibd_file=self.ibd)

    def _linked_source(self):
        pkg = Package(self.map)
        writer = PackageWriter(pkg)
        editor = ActorEdit(writer, pkg.exports[2])
        editor._insert_top(editor._new_tag("SourceTarget", 5, enc_index(1)))
        editor.changes.append("synthetic incoming typed object link")
        editor.commit()
        self.map.write_bytes(writer.write())
        self.map_sha = hashlib.sha256(self.map.read_bytes()).hexdigest()
        cache = json.loads(self.actors.read_text())
        cache["meta"]["source_sha256"] = self.map_sha
        self.actors.write_text(json.dumps(cache))

    def test_zero_gmp_refs_plus_exact_ibd_resource_does_not_claim_safety(self):
        original = [f.read_bytes() for f in
                    (self.map, self.actors, self.script_zip, self.ibd)]
        result = review_original(self.map, **self._opts())
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(
            result["status"],
            "no-known-incoming-reference-but-unresolved-script-links")
        self.assertEqual(result["gmp_explicit_incoming_count"], 0)
        self.assertEqual(result["original_ibd_script_resource_counts"][
            "exact_payload"], 1)
        self.assertEqual(result["target_game_property_92_status"],
                         "not_in_verified_script_actor_rows")
        self.assertFalse(result["target_game_property_92_redecoded"])
        for flag in (
            "target_actor_to_script_binding_verified",
            "incoming_script_links_verified",
            "full_incoming_reference_graph_verified",
            "native_script_writer_enabled",
            "gameplay_runtime_verified",
            "safe_to_unplace_claimed",
            "source_gmp_modified", "source_ibd_modified",
            "source_script_archive_modified"):
            self.assertFalse(result[flag], flag)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["source_map_sha256"], self.map_sha)
        self.assertEqual(original, [f.read_bytes() for f in
                         (self.map, self.actors, self.script_zip, self.ibd)])

    def test_confirmed_gmp_incoming_and_verified_ibd_remain_separate(self):
        self._linked_source()
        report = review_original(self.map, **self._opts())
        self.assertEqual(report["status"], "known-explicit-incoming-reference")
        self.assertEqual(report["gmp_explicit_incoming_count"], 1)
        self.assertIn("SourceTarget",
                      report["gmp_explicit_incoming_references"][0]["field"])
        self.assertEqual(
            report["original_ibd_script_resource_counts"]["exact_payload"], 1)
        self.assertFalse(report["incoming_script_links_verified"])
        self.assertFalse(report["safe_to_unplace_claimed"])

    def test_different_ibd_payload_is_not_claimed_equal(self):
        raw = bytearray(self.tsd[12:])
        raw[-1] ^= 1
        self.ibd.write_bytes(ibd_resource(raw, "TS_TEST"))
        report = review_original(self.map, **self._opts())
        self.assertEqual(report["original_ibd_script_resource_counts"][
            "exact_payload"], 0)
        self.assertEqual(report["original_ibd_script_resource_counts"][
            "different_payload"], 1)
        self.assertFalse(report["target_actor_to_script_binding_verified"])

    def test_stale_original_cache_and_source_pins_refused(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            review_original(self.map, **(self._opts() |
                {"source_sha256": "f" * 64}))
        self.map.write_bytes(self.map.read_bytes() + b"bad")
        self.map_sha = hashlib.sha256(self.map.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "cache does not match"):
            review_original(self.map, **self._opts())

    def test_reports_only_approved_private_json_and_no_overwrite(self):
        saved = export_private_report(
            self.map, self.actors, self.script_zip, self.ibd, self.report,
            source_sha256=self.map_sha, actor_export=1,
            actor_name="StaticMeshActor__1")
        self.assertEqual(json.loads(self.report.read_text()), saved)
        self.assertFalse(saved["safe_to_unplace_claimed"])
        with self.assertRaises((ValueError, FileExistsError)):
            export_private_report(
                self.map, self.actors, self.script_zip, self.ibd, self.report,
                source_sha256=self.map_sha, actor_export=1,
                actor_name="StaticMeshActor__1")
        for unsafe in (
            self.map.parent / "test.json",
            self.game / "test.json",
            self.game.parent / "test.json",
            self.root / "Game" / "test.json",
            self.root / "PrivateResearch" / "wrong.txt",
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                export_private_report(
                    self.map, self.actors, self.script_zip, self.ibd, unsafe,
                    source_sha256=self.map_sha, actor_export=1,
                    actor_name="StaticMeshActor__1")
            self.assertFalse(unsafe.exists())

    def test_cli_read_only_and_new_private_output(self):
        tool = ROOT / "native_editor/package_writer/dx2_crosssource_ref_review.py"
        args = [
            sys.executable, str(tool), "--map", str(self.map),
            "--source-sha256", self.map_sha,
            "--actor-export", "1", "--actor-name", "StaticMeshActor__1",
            "--actors", str(self.actors), "--scripts", str(self.script_zip),
            "--ibd", str(self.ibd),
        ]
        trial = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(trial.returncode, 0, trial.stdout + trial.stderr)
        doc = json.loads(trial.stdout)
        self.assertFalse(doc["output_written"])
        self.assertFalse(doc["actor_to_script_binding_verified"])
        self.assertNotIn(str(self.root), trial.stdout)
        out = subprocess.run(
            [*args, "--output", str(self.report)],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertTrue(self.report.exists())
        self.assertTrue(json.loads(out.stdout)["output_written"])
        refused = subprocess.run(
            [*args[:-1], str(self.root / "NoSource.ibd")],
            capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)["status"], "refused")
        self.assertNotIn(str(self.root), refused.stdout)
        self.assertNotIn("Traceback", refused.stdout + refused.stderr)


if __name__ == "__main__":
    unittest.main()
