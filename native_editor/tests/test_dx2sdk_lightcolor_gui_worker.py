"""DX2Ed v0.12 GUI worker, fabricated original GameSys source only.

No original retail DX2 files, copyrighted assets or runtime testing.
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
WORKER = ROOT/"native_editor/godot_editor/backend/dx2_sdk_lightcolor_worker.py"
sys.path.insert(0, str(ROOT))
from test_dx2sdk_light_colors import synthetic_lightcolor_map
from tools.build_dx2sdk_source_release import ARCHIVE, build


class LightColorGUIWorkerTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2ed_lightcolor_gui_v012_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root/"Original"/"M1_Synthetic.gmp"
        self.source.parent.mkdir()
        self.original = synthetic_lightcolor_map(self.source)
        self.digest = hashlib.sha256(self.original).hexdigest()
        self.output = self.root/"Private"/self.source.name
        self.prefix = ("--map",str(self.source),"--source-sha256",self.digest)
        self.edit = ("--export","1","--actor","StaticMeshActor__1",
                     "--expect","96","150","32","--brightness","255",
                     "--saturation","255","--output",str(self.output))

    def cli(self, action, *args, script=WORKER):
        run = subprocess.run([sys.executable,"-B",str(script),action,*args],
                             cwd=self.root, capture_output=True,text=True,timeout=50)
        try:
            doc=json.loads(run.stdout)
        except ValueError as exc:
            raise AssertionError("GUI worker emitted invalid JSON: "+
                                 run.stdout+run.stderr) from exc
        return run,doc

    def test_source_listing_has_pinned_original_bytes_and_no_game_write(self):
        p,r=self.cli("list",*self.prefix)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(r["bridge_schema"],
                         "DX2Ed-GUI-original-LightColor-worker-v1")
        self.assertEqual(r["status"],"read-only-source-verified")
        self.assertEqual(r["source_sha256"],self.digest)
        self.assertEqual(r["eligible_actor_count"],1)
        self.assertEqual(r["shown"][0]["original_values"],
                         {"brightness":96,"hue":150,"saturation":32})
        self.assertFalse(r["gameplay_runtime_verified"])
        self.assertFalse(r["source_original_modified"])
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_explicit_dry_run_then_source_locked_isolated_apply(self):
        p,dry=self.cli("preview",*self.prefix,*self.edit)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(dry["status"],"dry-run")
        self.assertEqual(dry["action"],"preview")
        self.assertTrue(dry["dual_serializer_full_package_match"])
        self.assertEqual(dry["changed_bytes"],2)
        self.assertFalse(self.output.exists())
        p,saved=self.cli("apply",*self.prefix,*self.edit)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(saved["status"],"isolated-verified-runtime-unverified")
        self.assertEqual(saved["action"],"apply")
        self.assertTrue(saved["verified_binary_structure"])
        self.assertTrue(saved["dual_serializer_full_package_match"])
        self.assertEqual(saved["changed_bytes"],2)
        self.assertFalse(saved["gameplay_runtime_verified"])
        self.assertFalse(saved["new_light_actor_created"])
        self.assertTrue(self.output.exists())
        self.assertTrue(self.output.with_suffix(".dx2sdk-lightcolor.json").exists())
        self.assertEqual(self.source.read_bytes(),self.original)
        self.assertEqual(
            sum(a!=b for a,b in zip(self.original,self.output.read_bytes())),2)
        p,blocked=self.cli("apply",*self.prefix,*self.edit)
        self.assertEqual(p.returncode,2)
        self.assertEqual(blocked["status"],"refused")

    def test_wrong_sha_source_actor_and_output_path_refused(self):
        for change in (
            ("--map",str(self.source),"--source-sha256","0"*64),
            (*self.prefix,"--export","2","--actor","StaticMeshActor__1",
             "--expect","96","150","32","--hue","0","--output",str(self.output)),
            (*self.prefix,"--export","1","--actor","Wrong",
             "--expect","96","150","32","--hue","0","--output",str(self.output)),
            (*self.prefix,"--export","1","--actor","StaticMeshActor__1",
             "--expect","96","150","33","--hue","0","--output",str(self.output)),
            (*self.prefix,*self.edit[:-1],str(self.source)),
            (*self.prefix,"--export","1","--actor","StaticMeshActor__1",
             "--expect","96","150","32","--brightness","96",
             "--output",str(self.output)),
        ):
            with self.subTest(case=change):
                action="list" if "--export" not in change else "apply"
                p,doc=self.cli(action,*change)
                self.assertEqual(p.returncode,2,p.stderr)
                self.assertEqual(doc["status"],"refused")
                self.assertFalse(doc["native_new_light_actor_creation_enabled"])
                self.assertFalse(self.output.exists())
                self.assertEqual(self.source.read_bytes(),self.original)

    def test_native_change_since_UI_sha_pinned_is_rejected(self):
        self.source.write_bytes(self.original+b"changed")
        for action in ("list","apply"):
            p,doc=self.cli(action,*self.prefix,*(self.edit if action=="apply" else ()))
            self.assertEqual(p.returncode,2)
            self.assertIn("changed",doc["reason"].lower())
        self.assertFalse(self.output.exists())

    def test_extracted_portable_sdk_has_worker_and_python_imports(self):
        zip_path=self.root/"v012.zip"
        build(ROOT,zip_path)
        with ZipFile(zip_path) as z:
            rel="native_editor/godot_editor/backend/dx2_sdk_lightcolor_worker.py"
            self.assertIn(f"{ARCHIVE}/{rel}",z.namelist())
            z.extractall(self.root/"Extracted")
        script=self.root/"Extracted"/ARCHIVE/rel
        p,doc=self.cli("list",*self.prefix,script=script)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(doc["shown"][0]["export"],1)
        p,doc=self.cli("preview",*self.prefix,*self.edit,script=script)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(doc["changed_bytes"],2)
        self.assertFalse(self.output.exists())


if __name__=="__main__":
    unittest.main()
