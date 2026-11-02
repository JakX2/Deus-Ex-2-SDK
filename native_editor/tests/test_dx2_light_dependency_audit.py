"""Asset-free synthetic DX2 Light dependency provenance tests.

Native Light spawning remains blocked. This constructs its own v95 GMP
and *never* bundles, downloads or commits retail game bytes.
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
from upkgwrite import ActorEdit, PackageWriter, ImportEntry, enc_index
from dx2_light_dependency_audit import inspect_original_lights, inspect_light, SCHEMA


def _synthetic_light_map(path: Path, *, missing_region: bool = False):
    level_fixture(path)
    pkg = Package(path)
    w = PackageWriter(pkg)
    original_actor = pkg.exports[0]
    cls = -original_actor.class_ref - 1
    assert 0 <= cls < len(w.imports)
    w.imports[cls].name = w.name_index("Light")
    w.exports[0].name = w.name_index("Light__0")
    class_idx = w.name_index("Class")
    actor_bytes = pkg.export_bytes(original_actor)
    for name, cls_name in [("LevelInfo__0", "LevelInfo"),
                           ("DefaultPhysicsVolume__6", "DefaultPhysicsVolume")]:
        w.imports.append(ImportEntry(0, class_idx, 0, w.name_index(cls_name),
                                     (b"", b"", b"")))
        target = w.add_export(0, name, actor_bytes)
        w.exports[target].class_ref = -len(w.imports)
    act = ActorEdit(w, pkg.exports[0])
    if not missing_region:
        zone = act._new_tag("Region", 10, struct_name="PointRegion")
        zone.fields.tags.append(act._new_tag("Zone", 5, enc_index(3)))
        zone.fields.tags.append(act._new_tag("iLeaf", 2, (20).to_bytes(4,"little",signed=True)))
        zone.fields.tags.append(act._new_tag("ZoneNumberLow", 1, bytes([8])))
        act.layout.props.tags.append(zone)
    act.layout.props.tags.append(act._new_tag("PhysicsVolume", 5, enc_index(4)))
    act.layout.props.tags.append(act._new_tag("Level", 5, enc_index(3)))
    act.layout.props.tags.append(act._new_tag("bDynamicLight", 3 | (1<<7)))
    act.changes.append("synthetic source-only lights fixture")
    assert act.commit()
    data = w.write()
    path.write_bytes(data)
    parsed = Package(path)
    assert parsed.export_class(parsed.exports[0]) == "Light"
    assert parsed.export_class(parsed.exports[2]) == "LevelInfo"
    assert parsed.export_class(parsed.exports[3]) == "DefaultPhysicsVolume"
    return data


class OriginalLightDependencyAuditTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.source = Path(temp.name) / "Original" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        self.raw = _synthetic_light_map(self.source)
        self.sha = hashlib.sha256(self.raw).hexdigest()

    def test_verified_native_references_and_region_are_read_only(self):
        doc = inspect_original_lights(self.source, source_sha256=self.sha)
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["source_light_count"], 1)
        self.assertEqual(doc["distinct_zone_numbers"], [8])
        self.assertEqual(doc["distinct_bsp_leaf_count"], 1)
        row = doc["lights"][0]
        self.assertEqual(row["actor"], "Light__0")
        self.assertEqual(row["export"], 1)
        self.assertEqual(row["region_leaf"], 20)
        self.assertEqual(row["region_zone_number_low"], 8)
        self.assertEqual(row["physics_volume"]["export"], 4)
        self.assertEqual(row["region_zone"]["export"], 3)
        self.assertEqual(row["level"]["export"], 3)
        self.assertTrue(row["tagged_object_references_checked"])
        self.assertFalse(row["region_for_new_position_verified"])
        self.assertFalse(row["state_frame_clone_verified"])
        self.assertFalse(row["light_clone_enabled"])
        self.assertFalse(doc["native_light_spawn_enabled"])
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_rejects_non_light_and_wrong_pin_and_missing_region(self):
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
            inspect_original_lights(self.source,source_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"not a placed Light"):
            inspect_original_lights(self.source,source_sha256=self.sha,actor_export=2)
        self.source.write_bytes(_synthetic_light_map(self.source,missing_region=True))
        sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"Region lacks"):
            inspect_original_lights(self.source,source_sha256=sha)

    def test_cli_safe_json_and_no_gmp_writes(self):
        script=ROOT/"native_editor/package_writer/dx2_light_dependency_audit.py"
        save=self.source.parent.parent/"Research"/"lights.json"
        cmd=[sys.executable,str(script),str(self.source),"--source-sha256",self.sha,
             "--output",str(save)]
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        reply=json.loads(run.stdout)
        self.assertEqual(reply["lights"],1)
        self.assertTrue(save.exists())
        self.assertFalse(json.loads(save.read_text())["native_light_spawn_enabled"])
        self.assertEqual(self.source.read_bytes(),self.raw)
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)["status"],"refused")

if __name__=="__main__":
    unittest.main()
