"""DX2Ed v0.15 batch numeric tagged actor field GUI worker synthetic tests.

Creates a complete tiny original-style v95 GMP with *two* fictional
StaticMeshActors and distinct originally authored int32/float32 tags.
No game assets, no retail runtime, no real source package redistribution.
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

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from test_native_save_as import ci,NAMES
from dx2inspect import Package, TAG
from dx2sdk import DX2Map
from tools.build_dx2sdk_source_release import ARCHIVE,build

WORKER=ROOT/"native_editor/godot_editor/backend/dx2_sdk_multi_scalar_worker.py"
BRIDGE="DX2Ed-GUI-original-multi-native-scalar-worker-v1"

def invented_two_actor_numeric_gmp():
    names=tuple(NAMES)+("StaticMeshActor__2","FixtureFloat","FixtureInt2")
    ix={name:i for i,name in enumerate(names)}
    def payload(x,y,z,first_int,other_name,other_kind,other_value):
        nested=b"".join(
            ci(ix[axis])+b"\x24"+struct.pack("<f",float(value))
            for axis,value in zip("XYZ",(x,y,z))
        )+ci(0)
        loc=(ci(ix["Location"])+b"\x7a"+ci(ix["Vector"])
             +struct.pack("<I",len(nested))+nested)
        first=ci(ix["FixtureFlag"])+b"\x22"+struct.pack("<i",first_int)
        other=ci(ix[other_name])+bytes([0x20+other_kind])+(
            struct.pack("<f",float(other_value)) if other_kind==4
            else struct.pack("<i",other_value))
        return loc+first+other+ci(0)
    actor1=payload(100,200,300,98765,"FixtureFloat",4,12.5)
    actor2=payload(400,500,600,43210,"FixtureInt2",2,44)
    names_blob=b"".join(
        ci(len(name.encode("ascii"))+1)+name.encode("ascii")
        +b"\x00"+struct.pack("<I",0) for name in names)
    imports=(ci(0)+ci(ix["Class"])+struct.pack("<i",0)
             +ci(ix["StaticMeshActor"]))
    name_offset=76
    import_offset=name_offset+len(names_blob)
    export_offset=import_offset+len(imports)
    def entry(name,body,offset):
        return (ci(-1)+ci(0)+struct.pack("<i",0)+ci(ix[name])
                +struct.pack("<I",0)+ci(len(body))+ci(offset))
    start=export_offset+28
    for _ in range(12):
        new=export_offset+len(entry("StaticMeshActor__1",actor1,start)) +len(
            entry("StaticMeshActor__2",actor2,start+len(actor1)))
        if new==start:
            break
        start=new
    exports=(entry("StaticMeshActor__1",actor1,start)
             +entry("StaticMeshActor__2",actor2,start+len(actor1)))
    assert start==export_offset+len(exports)
    header=(struct.pack("<IHHI",TAG,95,69,0)
            +struct.pack("<IIIIII",len(names),name_offset,
                         2,export_offset,1,import_offset)
            +struct.pack("<I",0)+bytes(16)+struct.pack("<I",1)
            +struct.pack("<II",1,len(names))+struct.pack("<II",0,0))
    assert len(header)==76
    raw=header+names_blob+imports+exports+actor1+actor2
    return raw


class MultiNativeScalarGUIWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix="dx2sdk_multi_native_scalar_v015_")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"Original"/"Content"/"DX2"/"Maps"/"M1_Invented.gmp"
        self.source.parent.mkdir(parents=True)
        self.original=invented_two_actor_numeric_gmp()
        self.source.write_bytes(self.original)
        self.cache=self.root/"PrivateCache"/"actors.json"
        self.cache.parent.mkdir()
        self.cache.write_text(json.dumps({
            "meta":{
                "source_map":self.source.name,
                "source_sha256":hashlib.sha256(self.original).hexdigest()},
            "actors":[
                {"name":"StaticMeshActor__1","class":"StaticMeshActor",
                 "export":1,"location":[100.,200.,300.],"rotation":[0,0,0],
                 "mesh":"SyntheticBox1","game_properties":[]},
                {"name":"StaticMeshActor__2","class":"StaticMeshActor",
                 "export":2,"location":[400.,500.,600.],"rotation":[0,0,0],
                 "mesh":"SyntheticBox2","game_properties":[]},
            ]},sort_keys=True))
        self.sha=hashlib.sha256(self.original).hexdigest()
        self.cache_sha=hashlib.sha256(self.cache.read_bytes()).hexdigest()
        self.output=self.root/"Isolated"/self.source.name
        self.manifest=self.output.with_suffix(".dx2sdk-scalar.json")
        self.rows=[
            {"actor":"StaticMeshActor__1","export":1,
             "property":"FixtureFlag","type":"int32",
             "expected":98765,"replacement":123456},
            {"actor":"StaticMeshActor__1","export":1,
             "property":"FixtureFloat","type":"float32",
             "expected":12.5,"replacement":15.75},
            {"actor":"StaticMeshActor__2","export":2,
             "property":"FixtureInt2","type":"int32",
             "expected":44,"replacement":-7},
        ]
        pkg=Package(self.source)
        self.assertEqual(len(pkg.scene_actors()[0]),2)
        world=DX2Map.open(self.source,self.cache)
        self.assertEqual(len(world.native_scalar_fields("StaticMeshActor__1")["fields"]),2)
        self.assertEqual(len(world.native_scalar_fields("StaticMeshActor__2")["fields"]),2)

    def cli(self,action,*,rows=None,output=None,actor=None,export=None,
            sha=None,cache_sha=None,script=WORKER):
        args=[sys.executable,"-B",str(script),action,
              "--map",str(self.source),"--actors",str(self.cache),
              "--source-sha256",sha or self.sha,
              "--actors-sha256",cache_sha or self.cache_sha]
        if rows is not None: args+=["--rows-json",json.dumps(rows,allow_nan=True)]
        if output is not None: args+=["--output",str(output)]
        if actor is not None: args+=["--actor",actor]
        if export is not None: args+=["--export",str(export)]
        run=subprocess.run(args,cwd=self.root,capture_output=True,text=True,timeout=90)
        try: doc=json.loads(run.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(run.stdout+"\n"+run.stderr) from e
        return run,doc

    def test_original_two_actor_list_and_each_typed_field_inventory(self):
        r,doc=self.cli("list")
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(doc["bridge_schema"],BRIDGE)
        self.assertEqual(doc["shown_count"],2)
        self.assertEqual({a["export"] for a in doc["actors"]},{1,2})
        self.assertFalse(doc["runtime_game_verified"])
        r,doc=self.cli("fields",actor="StaticMeshActor__1",export=1)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual({f["property"]:f["type"] for f in doc["fields"]},
                         {"FixtureFlag":"int32","FixtureFloat":"float32"})
        r,doc=self.cli("fields",actor="StaticMeshActor__2",export=2)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual({f["property"]:f["source_value"] for f in doc["fields"]},
                         {"FixtureFlag":43210,"FixtureInt2":44})
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_two_actors_three_original_fields_preview_then_verified_isolated_save(self):
        r,dry=self.cli("preview",rows=self.rows,output=self.output)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(dry["status"],"dry-run")
        self.assertEqual(dry["edited_field_count"],3)
        self.assertEqual(dry["action"],"preview")
        self.assertTrue(dry["original_source_noop_T3SDK_parity_verified"])
        self.assertFalse(dry["edited_package_written"])
        self.assertFalse(dry["saved_binary_structure_verified"])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())
        r,done=self.cli("apply",rows=list(reversed(self.rows)),output=self.output)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(done["action"],"apply")
        self.assertEqual(done["status"],"isolated-multi-native-scalars-verified-runtime-unverified")
        self.assertEqual(done["edited_field_count"],3)
        self.assertEqual(done["changed_byte_count"],dry["changed_byte_count"])
        self.assertEqual(done["rows"],dry["rows"])
        self.assertTrue(done["saved_binary_structure_verified"])
        self.assertTrue(done["independent_saved_whole_GMP_byte_verification"])
        self.assertFalse(done["runtime_game_verified"])
        self.assertEqual(self.source.read_bytes(),self.original)
        self.assertTrue(self.output.exists())
        self.assertTrue(self.manifest.exists())
        pkg=Package(self.output)
        a=pkg.decode_object(pkg.exports[0])
        b=pkg.decode_object(pkg.exports[1])
        self.assertEqual(a["FixtureFlag"],123456)
        self.assertEqual(a["FixtureFloat"],15.75)
        self.assertEqual(b["FixtureInt2"],-7)
        self.assertEqual(b["FixtureFlag"],43210)
        self.assertEqual(
            sum(x!=y for x,y in zip(self.original,self.output.read_bytes())),
            done["changed_byte_count"])
        again,doc=self.cli("apply",rows=self.rows,output=self.output)
        self.assertEqual(again.returncode,2)
        self.assertEqual(doc["status"],"refused")

    def test_rejects_unsupported_limits_duplicates_nonfinite_and_native_injection(self):
        invalid=[
            [],[self.rows[0]],self.rows*3,
            [self.rows[0],self.rows[0]],
            [self.rows[0],{**self.rows[1],"export":2}],
            [self.rows[0],{**self.rows[2],"actor":"StaticMeshActor__1"}],
            [self.rows[0],{**self.rows[2],"export":1}],
            [self.rows[0],{**self.rows[1],"property":"Location"}],
            [self.rows[0],{**self.rows[1],"property":"Rotation"}],
            [self.rows[0],{**self.rows[1],"expected":13.5}],
            [self.rows[0],{**self.rows[1],"replacement":12.5}],
            [self.rows[0],{**self.rows[1],"replacement":float("nan")}],
            [self.rows[0],{**self.rows[1],"replacement":float("inf")}],
            [self.rows[0],{**self.rows[1],"replacement":True}],
            [self.rows[0],{**self.rows[1],"type":"int32"}],
            [self.rows[0],{**self.rows[1],"extra":"unsafe"}],
            [self.rows[0],{**self.rows[1],"actor":"WrongOriginalName"}],
            [self.rows[0],{**self.rows[1],"export":True}],
            [self.rows[0],{**self.rows[1],"replacement":1e60}],
        ]
        for rows in invalid:
            with self.subTest(rows=rows):
                r,doc=self.cli("apply",rows=rows,output=self.output)
                self.assertEqual(r.returncode,2,r.stderr)
                self.assertEqual(doc["status"],"refused")
                self.assertFalse(self.output.exists())
                self.assertFalse(self.manifest.exists())
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_private_output_and_source_cache_drift_refuse_native_writes(self):
        for target in (
            self.source,self.source.parent/"nested"/self.source.name,
            self.root/"Game"/"Content"/"DX2"/"Maps"/self.source.name,
            self.root/"Wrong.gmp",
        ):
            with self.subTest(target=target):
                r,doc=self.cli("apply",rows=self.rows,output=target)
                self.assertEqual(r.returncode,2,r.stderr)
                self.assertFalse(self.output.exists())
        for kwargs in ({"sha":"0"*64},{"cache_sha":"0"*64}):
            r,doc=self.cli("apply",rows=self.rows,output=self.output,**kwargs)
            self.assertEqual(r.returncode,2,r.stderr)
            self.assertFalse(self.output.exists())
        self.manifest.parent.mkdir()
        self.manifest.write_text("do not overwrite me")
        r,doc=self.cli("apply",rows=self.rows,output=self.output)
        self.assertEqual(r.returncode,2,r.stderr)
        self.assertEqual(self.manifest.read_text(),"do not overwrite me")
        self.manifest.unlink()
        original_cache=self.cache.read_bytes()
        self.cache.write_bytes(original_cache+b" ")
        r,doc=self.cli("apply",rows=self.rows,output=self.output)
        self.assertEqual(r.returncode,2,r.stderr)
        self.cache.write_bytes(original_cache)
        self.source.write_bytes(self.original+b"drift")
        r,doc=self.cli("apply",rows=self.rows,output=self.output)
        self.assertEqual(r.returncode,2,r.stderr)
        self.assertFalse(self.output.exists())

    def test_portable_zip_extracted_source_contains_and_runs_batch_worker(self):
        archive=self.root/"v015.zip"
        build(ROOT,archive)
        rel="native_editor/godot_editor/backend/dx2_sdk_multi_scalar_worker.py"
        with ZipFile(archive) as z:
            self.assertIn(f"{ARCHIVE}/{rel}",z.namelist())
            z.extractall(self.root/"Unpacked")
        script=self.root/"Unpacked"/ARCHIVE/rel
        r,dry=self.cli("preview",rows=self.rows,output=self.output,script=script)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(dry["edited_field_count"],3)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())


if __name__=="__main__":
    unittest.main()
