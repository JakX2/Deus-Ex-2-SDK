"""Asset-free v0.13 DX2Ed batch LightColor GUI bridge integration.

All original-looking GMP bytes are invented by tests, never shipped game maps.
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
sys.path.insert(0, str(ROOT))
from test_dx2sdk_multi_light_colors import original_two_lightcolors
from tools.build_dx2sdk_source_release import build, ARCHIVE

WORKER = ROOT / "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py"


class MultiLightColorGUIWorkerTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2ed_gui_multi_lightcolor_v013_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "Original" / "M1_Gui_Synthetic.gmp"
        self.source.parent.mkdir()
        self.original, second = original_two_lightcolors(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.output = self.root / "Private" / self.source.name
        self.plan = self.output.with_suffix(".dx2sdk-multi-lightcolor-plan.json")
        self.manifest = self.output.with_suffix(".dx2sdk-multi-lightcolor.json")
        self.rows = [
            {"actor": "StaticMeshActor__1", "export": 1,
             "expected": [96, 150, 32],
             "changes": {"brightness": 255, "hue": 0}},
            {"actor": second, "export": 3,
             "expected": [80, 90, 100],
             "changes": {"saturation": 255}},
        ]
        self.prefix = ("--map", str(self.source),
                       "--source-sha256", self.sha)

    def cli(self, action, *, rows=None, output=None, script=WORKER,
            source_sha=None, extra=()):
        argv = [sys.executable, "-B", str(script), action, "--map",
                str(self.source), "--source-sha256", source_sha or self.sha]
        if rows is not None:
            argv += ["--rows-json", json.dumps(rows)]
        if output is not None:
            argv += ["--output", str(output)]
        argv += list(extra)
        run = subprocess.run(argv, cwd=self.root, capture_output=True,
                             text=True, timeout=90)
        try:
            doc = json.loads(run.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError("Bad GUI batch worker JSON: "+
                                 run.stdout+run.stderr) from exc
        return run, doc

    def test_original_inventory_unmodified_with_two_authored_lightcolors(self):
        result, report = self.cli("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["bridge_schema"],
                         "DX2Ed-GUI-source-multi-LightColor-worker-v1")
        self.assertEqual(report["status"], "read-only-source-verified")
        self.assertEqual(report["source_sha256"], self.sha)
        self.assertEqual(report["eligible_actor_count"], 2)
        self.assertEqual(
            {item["export"] for item in report["shown"]}, {1, 3})
        self.assertFalse(report["native_new_light_actor_creation_enabled"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_memory_preview_then_single_opt_in_isolated_two_actor_copy(self):
        run, dry = self.cli("preview", rows=self.rows, output=self.output)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(dry["status"], "dry-run")
        self.assertEqual(dry["action"], "preview")
        self.assertEqual(dry["edited_actor_count"], 2)
        self.assertEqual(dry["changed_bytes"], 3)
        self.assertTrue(dry["independent_full_package_byte_match"])
        self.assertFalse(dry["edited_package_written"])
        self.assertFalse(dry["plan_created"])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.plan.exists())
        self.assertFalse(self.manifest.exists())
        run, saved = self.cli("apply", rows=self.rows, output=self.output)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(saved["action"], "apply")
        self.assertEqual(saved["status"],
                         "isolated-multi-LightColor-verified-runtime-unverified")
        self.assertEqual(saved["edited_actor_count"], 2)
        self.assertEqual(saved["changed_bytes"], 3)
        self.assertEqual(saved["actors"], dry["actors"])
        self.assertTrue(saved["verified_binary_structure"])
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.plan.is_file())
        self.assertTrue(self.manifest.is_file())
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(
            sum(a != b for a, b in zip(self.original, self.output.read_bytes())),3)
        again, refused = self.cli("apply", rows=self.rows, output=self.output)
        self.assertEqual(again.returncode, 2)
        self.assertEqual(refused["status"], "refused")

    def test_missing_changed_original_output_and_duplicate_rows_refused(self):
        invalid_rows = [
            [],
            self.rows[:1],
            self.rows*5,
            [self.rows[0], self.rows[0]],
            [{**self.rows[0], "export": True}, self.rows[1]],
            [{**self.rows[0], "actor": "Wrong"}, self.rows[1]],
            [{**self.rows[0], "expected": [97,150,32]}, self.rows[1]],
            [{**self.rows[0], "changes": {"brightness":96}}, self.rows[1]],
            [{**self.rows[0], "changes": {"brightness":256}}, self.rows[1]],
            [{**self.rows[0], "changes": {"hue": True}}, self.rows[1]],
            [{**self.rows[0], "changes": {}}, self.rows[1]],
            [{**self.rows[0], "arbitrary": 99}, self.rows[1]],
        ]
        for rows in invalid_rows:
            with self.subTest(rows=rows):
                run, doc = self.cli("apply", rows=rows, output=self.output)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual(doc["status"], "refused")
                self.assertFalse(self.output.exists())
                self.assertFalse(self.plan.exists())
        for target in (self.source,
                       self.source.parent / "nested" / self.source.name,
                       self.root / "Game" / "Content" / "DX2" / "Maps" / self.source.name,
                       self.root / "Wrong.gmp"):
            with self.subTest(target=target):
                run, doc = self.cli("apply", rows=self.rows, output=target)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertFalse(self.output.exists())
                self.assertFalse(self.plan.exists())
        run, doc = self.cli("apply", rows=self.rows, output=self.output,
                            source_sha="0"*64)
        self.assertEqual(run.returncode, 2)
        self.assertIn("changed", doc["reason"].lower())
        self.assertFalse(self.output.exists())
        self.assertFalse(self.plan.exists())
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_private_plan_conflicts_and_stale_source_are_refused(self):
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text('{"forged":true}', encoding="utf8")
        run, doc = self.cli("apply", rows=self.rows, output=self.output)
        self.assertEqual(run.returncode,2)
        self.assertEqual(doc["status"], "refused")
        self.assertEqual(self.plan.read_text(), '{"forged":true}')
        self.assertFalse(self.output.exists())
        self.plan.unlink()
        self.source.write_bytes(self.original + b"source changed")
        for action in ("preview", "apply", "list"):
            run, doc = self.cli(action, rows=self.rows, output=self.output)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(doc["status"], "refused")
        self.assertFalse(self.output.exists())

    def test_extracted_portable_source_standalone_worker(self):
        zip_path = self.root / "v013.zip"
        build(ROOT, zip_path)
        rel = "native_editor/godot_editor/backend/dx2_sdk_multi_lightcolor_worker.py"
        with ZipFile(zip_path) as archive:
            self.assertIn(f"{ARCHIVE}/{rel}", archive.namelist())
            archive.extractall(self.root / "extracted")
        extracted = self.root / "extracted" / ARCHIVE / rel
        run, report = self.cli("preview", rows=self.rows,
                               output=self.output,script=extracted)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(report["changed_bytes"], 3)
        self.assertTrue(report["independent_full_package_byte_match"])
        self.assertFalse(self.plan.exists())
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
