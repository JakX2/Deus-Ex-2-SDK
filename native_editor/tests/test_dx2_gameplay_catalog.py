"""Asset-free contract tests for DX2 original TriggerScript/AI browser."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor/godot_editor/backend"))
from dx2_gameplay_catalog import (SCHEMA, audit_actor_cache, build_catalog, parse_tsd)

def tsd(name="TestSwitch", title="Light switch", action="kTAT_LinkedPropertySet"):
    fields = (name + "\x00" + title + "\x00" +
              "kTCT_ReceivePropagateMsgLink\x00" + action + "\x00")
    return b"1FFE2FST" + b"\x00" * 8 + fields.encode("utf-16le")


class GameplayCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.map = self.path / "M1_Test.gmp"
        self.map.write_bytes(b"synthetic GMP bytes only")
        self.actors = self.path / "actors.json"
        self.scripts = self.path / "TriggerScript.zip"
        sha = hashlib.sha256(self.map.read_bytes()).hexdigest()
        self.actor_data = {"meta": {"source_map": self.map.name,
                                    "source_sha256": sha},
                           "actors": [
            {"name":"D_527__0","class":"D_527","export":5,
             "location":[1,2,3],
             "game_properties":[{"id":82,"value":"AI"}],
             "trigger_script_serialized":{"items":[432,424],"interpretation":"index"}},
            {"name":"StaticMeshActor__1","class":"StaticMeshActor","export":6,
             "game_properties":[{"id":82,"value":"Staticmeshes"}],
             "trigger_script_serialized":None}]}
        self.actors.write_text(json.dumps(self.actor_data))
        with zipfile.ZipFile(self.scripts,"w") as z:
            z.writestr("Defs/TestSwitch.tsd", tsd())

    def test_catalog_definitions_original_ai_markers_and_unresolved_indexes(self):
        result = build_catalog(self.map, self.actors, self.scripts)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["spawn_enabled"])
        self.assertFalse(result["bindings_verified"])
        self.assertEqual(result["counts"], {"scripts":1,"ai_candidates":1,"raw_script_fields":1})
        definition = result["script_definitions"][0]
        self.assertEqual(definition["id"], "TestSwitch")
        self.assertEqual(definition["title"], "Light switch")
        self.assertIn("kTAT_LinkedPropertySet",definition["actions"])
        self.assertIn("kTCT_ReceivePropagateMsgLink",definition["conditions"])
        self.assertEqual(result["ai_layer_candidates"][0]["actor"],"D_527__0")
        self.assertFalse(result["ai_layer_candidates"][0]["spawnable_verified"])
        raw=result["actors_with_serialized_script_data"][0]
        self.assertEqual(raw["raw_property"]["items"], [432,424])
        self.assertFalse(raw["script_names_resolved"])

    def test_refuses_modified_map_or_actor_cache_identity(self):
        self.map.write_bytes(b"changed original bytes")
        with self.assertRaisesRegex(ValueError,"cache does not match"):
            build_catalog(self.map,self.actors,self.scripts)
        self.map.write_bytes(b"synthetic GMP bytes only")
        self.actor_data["actors"].append({**self.actor_data["actors"][0]})
        self.actors.write_text(json.dumps(self.actor_data))
        with self.assertRaisesRegex(ValueError,"Duplicated"):
            build_catalog(self.map,self.actors,self.scripts)

    def test_invalid_binary_and_archive_name_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unrecognized"):
            parse_tsd("Defs/TestSwitch.tsd",b"not a real definition".ljust(30,b" "))
        with self.assertRaisesRegex(ValueError,"disagrees"):
            parse_tsd("Defs/Other.tsd",tsd())
        with zipfile.ZipFile(self.scripts,"w") as z:
            z.writestr("Defs/Subdir/TestSwitch.tsd",tsd())
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            build_catalog(self.map,self.actors,self.scripts)

    def test_cli_writes_private_json_and_never_modifies_sources(self):
        output=self.path / "Private" / "catalog.json"
        inputs=[self.map,self.actors,self.scripts]
        before=[hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs]
        exe=ROOT/"native_editor/godot_editor/backend/dx2_gameplay_catalog.py"
        run=subprocess.run([sys.executable,str(exe),"--map",str(self.map),
                            "--actors",str(self.actors),"--scripts",str(self.scripts),
                            "--output",str(output)],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr+run.stdout)
        self.assertEqual(json.loads(run.stdout)["status"],"ok")
        self.assertEqual(json.loads(output.read_text())["counts"]["ai_candidates"],1)
        self.assertEqual([hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs],before)
        refused=subprocess.run([sys.executable,str(exe),"--map",str(self.map),
                                "--actors",str(self.actors),"--scripts",str(self.scripts),
                                "--output",str(self.map)],capture_output=True,text=True)
        self.assertEqual(refused.returncode,2)
        self.assertEqual(json.loads(refused.stdout)["status"],"refused")

if __name__ == "__main__":
    unittest.main()
