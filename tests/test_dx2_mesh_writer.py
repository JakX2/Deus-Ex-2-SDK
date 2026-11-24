"""Synthetic native static-mesh topology import regression tests."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_ibd_integrity import verify_bundle,sha256
from dx2_ibd_repack import _build,_parts
from dx2_mesh_writer import (inspect_template,select_mesh,parse_geometry,
    replace_geometry,write_candidate,build_payload,Template)
from test_dx2_material_writer import fixture as material_fixture


def geometry():
    return {"positions":[[0,0,0],[2,0,0],[2,1,0],[0,1,0]],
            "normals":[[0,0,1]]*4,"uv":[[0,0],[1,0],[1,1],[0,1]],
            "indices":[0,1,2,0,2,3]}


def fixture():
    raw=material_fixture()
    bundle=verify_bundle(raw)
    rows=_parts(raw,bundle)
    records=[raw[52+304*i:52+304*(i+1)] for i in range(len(rows))]
    u=lambda n:struct.pack("<I",n)
    def string(b):return [u(len(b)+1),b+b"\0"]
    header=bytearray(80)
    struct.pack_into("<10I",header,40,4,6,2,1,0,0,0,1,64,0)
    payload,_=build_payload(Template(None,(),b"section\0",bytes(header)),geometry())
    row=[u(1)]+string(b"default")+[u(1)]+string(b"test_material")+[u(1),u(0),u(0),u(0),u(len(payload)),payload]
    rec=bytearray(304)
    rec[40]=4
    rec[41:53]=b"fixture_mesh"
    rows.append(row)
    records.append(bytes(rec))
    return _build(raw,bundle,rows,record_templates=records)


def triangle():
    return {"positions":[[0,0,0],[3,0,0],[0,2,0]],
            "normals":[[0,0,1]]*3,"uv":[[0,0],[1,0],[0,1]],
            "indices":[0,1,2]}


class MeshWriterTests(unittest.TestCase):
    def test_new_topology_and_exact_inverse(self):
        raw=fixture()
        b=verify_bundle(raw)
        r=select_mesh(b,"fixture_mesh")
        before=inspect_template(b,r)
        self.assertEqual(len(before.mesh.positions),4)
        candidate=replace_geometry(raw,"fixture_mesh",triangle())
        after=verify_bundle(candidate)
        mesh=inspect_template(after,select_mesh(after,"fixture_mesh"))
        self.assertEqual(len(mesh.mesh.positions),3)
        self.assertEqual(mesh.mesh.indices,[0,1,2])
        self.assertEqual(mesh.mesh.bounds,[0,0,0,3,2,0])
        self.assertEqual(mesh.parts[:-2],before.parts[:-2])
        self.assertEqual(mesh.mesh.skins,before.mesh.skins)
        self.assertEqual(mesh.section_name,before.section_name)
        self.assertEqual(replace_geometry(candidate,"fixture_mesh",geometry()),raw)

    def test_reject_invalid_geometry(self):
        cases=[]
        for key,value in (
            ("indices",[0,2,1]),("indices",[0,1,1]),
            ("indices",[0,1,True]),("indices",[0,1,3]),
            ("positions",[[0,0,0],[0,0,0],[0,1,0]]),
            ("uv",[[0,0]]*3),("normals",[[0,0,-1]]*3),
            ("normals",[[0,0,0]]*3),("positions",[[float("nan"),0,0],[1,0,0],[0,1,0]])):
            doc=triangle();doc[key]=value;cases.append(doc)
        for doc in cases:
            with self.subTest(doc=doc),self.assertRaises(ValueError):
                parse_geometry(doc)

    def test_reject_template_unknown_fields(self):
        raw=fixture();b=verify_bundle(raw)
        r=select_mesh(b,"fixture_mesh")
        rows=_parts(raw,b);rows[r.index]=list(rows[r.index])
        for offset,value in ((76,struct.pack("<I",7)),(60+80,b"\0\0\0\0")):
            data=bytearray(rows[r.index][-1])
            data[offset:offset+len(value)]=value
            changed=list(rows);changed[r.index]=list(rows[r.index]);changed[r.index][-1]=bytes(data)
            bad=_build(raw,b,changed)
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                replace_geometry(bad,"fixture_mesh",triangle())

    def test_disk_pin_and_no_overwrite(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"source"/"fixture.ibd";source.parent.mkdir()
            raw=fixture();source.write_bytes(raw)
            path=root/"geometry.json";path.write_text(json.dumps(triangle()))
            output=root/"candidate"/source.name
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                write_candidate(source,output,"0"*64,"fixture_mesh",path)
            receipt=write_candidate(source,output,sha256(raw),"fixture_mesh",path)
            self.assertEqual(receipt["triangle_count"],1)
            self.assertFalse(receipt["runtime_verified"])
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(output.read_bytes(),replace_geometry(raw,"fixture_mesh",triangle()))
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_candidate(source,output,sha256(raw),"fixture_mesh",path)


if __name__=="__main__":unittest.main()
