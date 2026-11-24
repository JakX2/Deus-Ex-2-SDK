"""Synthetic native hull regressions; no original assets."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_hull_writer import (validate_points,box_points,select_hull,inspect_hull,
    replace_hull,write_candidate)
from dx2_ibd_integrity import verify_bundle,sha256
from dx2_ibd_repack import _build,_parts
from test_dx2_mesh_writer import fixture as mesh_fixture

TETRA=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]


def fixture():
    raw=mesh_fixture()
    b=verify_bundle(raw)
    rows=_parts(raw,b)
    records=[raw[52+304*i:52+304*(i+1)] for i in range(len(rows))]
    pts=box_points((-1,-2,-3),(1,2,3))
    rows.append([struct.pack("<I",8),b"\0",struct.pack("<I",len(pts)),
                 b"".join(struct.pack("<4f",*p,0) for p in pts)])
    rec=bytearray(304)
    rec[40]=5
    rec[41:55]=b"fixture_hull-0"
    records.append(bytes(rec))
    return _build(raw,b,rows,record_templates=records)


class HullWriterTests(unittest.TestCase):
    def test_convex_extreme_points_and_box(self):
        self.assertEqual(validate_points(TETRA),tuple(TETRA))
        pts=box_points((-2,-1,-3),(4,5,6))
        self.assertEqual(len(pts),8)
        self.assertEqual(len(set(pts)),8)
        self.assertEqual(validate_points(pts),pts)

    def test_invalid_clouds_rejected(self):
        for pts in (TETRA+[(.1,.1,.1)],TETRA+[(.5,.5,0)],
                    TETRA+[(.5,0,0)],TETRA+[(0,0,0)],
                    [(0,0,0),(1,0,0),(0,1,0),(1,1,0)],
                    TETRA+[(1+1e-9,0,0)],TETRA+[(float("nan"),0,0)],
                    TETRA+[(True,0,0)],TETRA[:3]):
            with self.subTest(pts=pts),self.assertRaises(ValueError):
                validate_points(pts)
        with self.assertRaises(ValueError):box_points((0,0,0),(1,0,1))

    def test_replacement_changes_count_and_inverse(self):
        raw=fixture()
        before=verify_bundle(raw)
        resource=select_hull(before,"fixture_hull-0")
        old=inspect_hull(before,resource)
        changed=replace_hull(raw,resource.name,TETRA)
        b=verify_bundle(changed)
        after=inspect_hull(b,select_hull(b,resource.name))
        self.assertEqual(after.parts[:2],old.parts[:2])
        self.assertEqual(after.points,tuple(TETRA))
        self.assertEqual(len(after.parts[-1]),64)
        self.assertEqual(replace_hull(changed,resource.name,old.points),raw)
        for a,c in zip(before.resources,b.resources):
            if a.index!=resource.index:
                self.assertEqual(before.raw(a),b.raw(c))

    def test_unknown_layout_refused(self):
        raw=fixture()
        b=verify_bundle(raw);r=select_hull(b,"fixture_hull-0")
        rows=_parts(raw,b)
        for slot,value in ((0,struct.pack("<I",99)),(1,b"\1"),(2,struct.pack("<I",99)),
                           (3,bytes(rows[r.index][3][:12])+b"\0\0\x80\x3f"+bytes(rows[r.index][3][16:]))):
            changed=list(rows);changed[r.index]=list(rows[r.index]);changed[r.index][slot]=value
            malformed=_build(raw,b,changed)
            with self.subTest(slot=slot),self.assertRaises(ValueError):
                replace_hull(malformed,r.name,TETRA)

    def test_isolated_output_pin_and_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"source"/"test.ibd";source.parent.mkdir()
            raw=fixture();source.write_bytes(raw)
            geometry=root/"box.json";geometry.write_text(json.dumps({"min":[0,0,0],"max":[1,2,3]}))
            output=root/"candidate"/source.name
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                write_candidate(source,output,"0"*64,"fixture_hull-0",geometry)
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_candidate(source,source.parent/"nested"/source.name,sha256(raw),"fixture_hull-0",geometry)
            receipt=write_candidate(source,output,sha256(raw),"fixture_hull-0",geometry)
            self.assertFalse(receipt["runtime_verified"])
            self.assertFalse(receipt["physics_registration_verified"])
            self.assertEqual(source.read_bytes(),raw)
            b=verify_bundle(output.read_bytes())
            self.assertEqual(inspect_hull(b,select_hull(b,"fixture_hull-0")).points,box_points((0,0,0),(1,2,3)))
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_candidate(source,output,sha256(raw),"fixture_hull-0",geometry)


if __name__=="__main__":unittest.main()
