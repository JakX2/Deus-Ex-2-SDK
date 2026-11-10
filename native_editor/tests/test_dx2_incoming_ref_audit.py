"""Synthetic regression for conservative incoming original actor references.

Only nonproprietary DX2 v95 fixtures. Unplace is blocked on decoded inbound
ObjectProperties/GameSys object fields/export metadata; opaque fields remain
explicitly unresolved.
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
for parent in (
    ROOT / "native_editor/tests",
    ROOT / "native_editor/package_writer",
    ROOT / "third_party/t3sdk_assets",
):
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from dx2_actor_unplace_probe import check_actor, unplace_in_memory
from dx2_incoming_ref_audit import (
    SCHEMA, audit_original, require_no_explicit_incoming, scan_package,
)
from dx2_native_prop_plan import SCHEMA as PLAN_SCHEMA, compile_in_memory
from t3common import enc_index
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter


class ExplicitIncomingReferencesTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.source = self.dir / "Original" / "M1_RefAudit.gmp"
        self.source.parent.mkdir(parents=True)
        initial = level_fixture(self.source)
        _, updated = clone_in_memory(
            self.source,
            source_sha256=hashlib.sha256(initial).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(100.0, 0.0, 0.0),
        )
        self.source.write_bytes(updated)
        self.source_sha256 = hashlib.sha256(updated).hexdigest()
        self.original = updated

    def _current_sha(self):
        return hashlib.sha256(self.source.read_bytes()).hexdigest()

    def _linked(self, kind):
        pkg = Package(self.source)
        writer = PackageWriter(pkg)
        original = pkg.exports[2]
        if kind == "tagged-object":
            editor = ActorEdit(writer, original)
            editor._insert_top(editor._new_tag("SourceTarget", 5, enc_index(1)))
            editor.changes.append("add test ObjectProperty reference")
            self.assertTrue(editor.commit())
        elif kind == "gamesys-object":
            editor = ActorEdit(writer, original)
            editor.set_block(
                2701, enc_index(1), "TestObject",
                insert_id=(0x0002 << 16) | 2701)
            self.assertTrue(editor.commit())
        elif kind == "export-outer":
            writer.exports[2].package = 1
        else:
            raise AssertionError(kind)
        self.source.write_bytes(writer.write())
        self.assertEqual(Package(self.source).exports[0].name, "StaticMeshActor__1")

    def _combined_copy_unplace(self):
        plan = {
            "schema": PLAN_SCHEMA,
            "moves": [],
            "copies": [
                {"actor": "StaticMeshActor__1", "export": 1,
                 "delta": [75.0, 0.0, 0.0]},
            ],
            "unplaces": [
                {"actor": "StaticMeshActor__1", "export": 1},
            ],
        }
        return compile_in_memory(
            self.source, source_sha256=self._current_sha(), plan=plan)

    def test_no_explicit_incoming_is_not_certified_fully_safe(self):
        pkg = Package(self.source)
        result = scan_package(pkg, 1)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["confirmed_incoming_count"], 0)
        self.assertFalse(result["incoming_references_verified"])
        self.assertFalse(result["safe_to_unplace_claimed"])
        self.assertFalse(result["runtime_game_verified"])
        same = require_no_explicit_incoming(pkg, 1)
        self.assertEqual(same["confirmed_incoming_references"], [])
        report = audit_original(
            self.source, source_sha256=self.source_sha256,
            actor_export=1, actor_name="StaticMeshActor__1",
        )
        self.assertFalse(report["explicit_incoming_blocker"])
        self.assertEqual(report["source_sha256"], self.source_sha256)
        self.assertFalse(report["original_gmp_modified"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_unplace_and_combined_writer_still_work_without_known_inbounds(self):
        report = check_actor(
            self.source, source_sha256=self.source_sha256,
            actor_export=1, actor_name="StaticMeshActor__1")
        self.assertTrue(report["explicit_incoming_references_checked"])
        self.assertEqual(report["explicit_incoming_reference_count"], 0)
        _, binary = unplace_in_memory(
            self.source, source_sha256=self.source_sha256,
            actor_export=1, actor_name="StaticMeshActor__1")
        self.assertNotEqual(binary, self.original)
        combined, data = self._combined_copy_unplace()
        self.assertTrue(combined["explicit_incoming_references_checked"])
        self.assertEqual(len(combined["copied"]), 1)
        self.assertEqual(len(combined["unplaced"]), 1)
        self.assertFalse(combined["incoming_references_verified"])
        self.assertNotEqual(data, binary)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_typed_object_property_inbound_ref_blocks_both_writers(self):
        self._linked("tagged-object")
        sha = self._current_sha()
        result = audit_original(
            self.source, source_sha256=sha,
            actor_export=1, actor_name="StaticMeshActor__1")
        self.assertTrue(result["explicit_incoming_blocker"])
        self.assertEqual(result["confirmed_incoming_count"], 1)
        self.assertIn("SourceTarget", result["confirmed_incoming_references"][0]["field"])
        self.assertEqual(result["confirmed_incoming_references"][0]["kind"], "tagged-object")
        with self.assertRaisesRegex(ValueError, "explicit incoming actor reference"):
            check_actor(self.source, source_sha256=sha,
                        actor_export=1, actor_name="StaticMeshActor__1")
        with self.assertRaisesRegex(ValueError, "explicit incoming actor reference"):
            self._combined_copy_unplace()

    def test_gamesys_object_block_inbound_ref_blocks_both_writers(self):
        self._linked("gamesys-object")
        report = audit_original(
            self.source, source_sha256=self._current_sha(),
            actor_export=1, actor_name="StaticMeshActor__1")
        self.assertTrue(report["explicit_incoming_blocker"])
        self.assertEqual(report["confirmed_incoming_count"], 1)
        self.assertIn("gamesys.2701", report["confirmed_incoming_references"][0]["field"])
        with self.assertRaisesRegex(ValueError, "explicit incoming actor reference"):
            check_actor(self.source, source_sha256=self._current_sha(),
                        actor_export=1, actor_name="StaticMeshActor__1")
        with self.assertRaisesRegex(ValueError, "explicit incoming actor reference"):
            self._combined_copy_unplace()

    def test_export_metadata_inbound_ref_blocks_unplace(self):
        self._linked("export-outer")
        audit = scan_package(Package(self.source), 1)
        self.assertTrue(audit["confirmed_incoming_references"])
        self.assertEqual(audit["confirmed_incoming_references"][0]["field"],
                         "export.package")
        with self.assertRaisesRegex(ValueError, "explicit incoming actor reference"):
            unplace_in_memory(
                self.source, source_sha256=self._current_sha(),
                actor_export=1, actor_name="StaticMeshActor__1")

    def test_read_only_cli_reports_positive_hit_and_incomplete_scope(self):
        self._linked("tagged-object")
        sha = self._current_sha()
        script = ROOT / "native_editor/package_writer/dx2_incoming_ref_audit.py"
        args = [sys.executable, str(script), str(self.source),
                "--source-sha256", sha, "--actor-export", "1",
                "--actor-name", "StaticMeshActor__1"]
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["status"], "explicit-incoming-reference-found")
        self.assertTrue(result["explicit_incoming_blocker"])
        self.assertFalse(result["incoming_references_verified"])
        self.assertFalse(result["original_gmp_modified"])
        failed = subprocess.run(args[:-1] + ["WrongActor"],
                                capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout)["status"], "refused")
        self.assertNotIn("Traceback", failed.stdout + failed.stderr)

    def test_invalid_target_export_or_sha_is_refused(self):
        with self.assertRaises(ValueError):
            scan_package(Package(self.source), True)
        with self.assertRaises(ValueError):
            scan_package(Package(self.source), 0)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            audit_original(self.source, source_sha256="f" * 64,
                           actor_export=1, actor_name="StaticMeshActor__1")
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
