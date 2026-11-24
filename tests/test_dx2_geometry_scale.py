"""Synthetic coordinated geometry scaling tests."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_ibd_integrity import verify_bundle,sha256
from dx2_ibd_repack import _build,_parts
from dx2_mesh_writer import select_mesh
from dx2_hull_writer import select_hull,inspect_hull
from dx2bundles import parse_mesh
from dx2_geometry_scale import scale_archive,collect,prepare
from test_dx2_hull_writer import fixture as hull_fixture


def fixture():
    raw=hull_fixture();b=verify_bundle(raw)
    rows=_parts(raw,b)
    r=select_mesh(b,"fixture_mesh")
    row=list(rows[r.index]);row[9]=struct.pack("<I",1)
    row[10:10]=[struct.pack("<12f",2,3,4,1,0,0,0,1,0,0,0,1),
                struct.pack("<I",3),b"hp\0"]
    payload=bytearray(row[-1])
    nv=struct.unpack_from("<I",payload,40)[0]
    at=80+nv*64
    aux=b"".join(struct.pack("<3fI",*v,0x7f00ff) for v in ((0,0,.1),(2,0,.1),(0,1,.1)))
    payload[at:at]=aux+struct.pack("<3H",0,1,2)
    struct.pack_into("<3I",payload,56,3,1,3)
    row[-2:]=[struct.pack("<I",len(payload)),bytes(payload)]
    rows[r.index]=row
    records=[bytearray(raw[52+304*i:52+304*(i+1)]) for i in range(len(rows))]
    h=select_hull(b,"fixture_hull-0")
    records[h.index][41:]=b"fixture_mesh--0".ljust(263,b"\0")
    return _build(raw,b,rows,record_templates=records)


class GeometryScaleTests(unittest.TestCase):
    def test_render_hardpoints_auxiliary_and_hull_exact_inverse(self):
        raw=fixture();b=verify_bundle(raw)
        r=select_mesh(b,"fixture_mesh");h=select_hull(b,"fixture_mesh--0")
        candidate=scale_archive(raw,[r.index,h.index],1)
        after=verify_bundle(candidate)
        old=parse_mesh(b,r);new=parse_mesh(after,after.resources[r.index])
        self.assertEqual(new.positions,[tuple(2*x for x in v) for v in old.positions])
        self.assertEqual(new.normals,old.normals)
        self.assertEqual(new.uv,old.uv)
        self.assertEqual(new.indices,old.indices)
        self.assertEqual(new.hardpoints[0]["matrix"][:3],(4,6,8))
        self.assertEqual(new.hardpoints[0]["matrix"][3:],old.hardpoints[0]["matrix"][3:])
        a=list(b.parts(r))[-1];c=list(after.parts(after.resources[r.index]))[-1]
        start=80+64*len(old.positions)
        self.assertEqual(struct.unpack_from("<f",c,start+8)[0],2*struct.unpack_from("<f",a,start+8)[0])
        self.assertEqual(c[start+12:start+16],a[start+12:start+16])
        self.assertEqual(c[start+48:],a[start+48:])
        old_h=inspect_hull(b,h);new_h=inspect_hull(after,after.resources[h.index])
        self.assertEqual(new_h.points,tuple(tuple(2*x for x in v) for v in old_h.points))
        self.assertEqual(scale_archive(candidate,[r.index,h.index],-1),raw)

    def test_malformed_shadow_index_refused(self):
        raw=fixture();b=verify_bundle(raw);r=select_mesh(b,"fixture_mesh")
        rows=_parts(raw,b);rows[r.index]=list(rows[r.index])
        payload=bytearray(rows[r.index][-1])
        nv=struct.unpack_from("<I",payload,40)[0]
        struct.pack_into("<H",payload,80+nv*64+3*16,99)
        rows[r.index][-1]=bytes(payload)
        bad=_build(raw,b,rows)
        with self.assertRaisesRegex(ValueError,"Auxiliary index"):
            scale_archive(bad,[r.index],1)

    def test_zip_counts_and_isolated_candidate(self):
        raw=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"assets.zip"
            with zipfile.ZipFile(source,"w") as z:
                z.writestr("A.ibd",raw)
                z.writestr("B.ibd",raw)
            pin=sha256(source.read_bytes())
            selected,nm,nh=collect(source,pin,"fixture_mesh")
            self.assertEqual((nm,nh),(2,2))
            with self.assertRaisesRegex(ValueError,"counts differ"):
                prepare(source,pin,"fixture_mesh",1,1,2,root/"bad")
            self.assertFalse((root/"bad").exists())
            receipt=prepare(source,pin,"fixture_mesh",1,2,2,root/"trial")
            self.assertFalse(receipt["runtime_verified"])
            self.assertFalse(receipt["mass_inertia_updated"])
            for row in receipt["files"]:
                self.assertEqual(sha256((root/"trial"/row["relative_path"]).read_bytes()),row["candidate_sha256"])
            self.assertEqual(sha256(source.read_bytes()),pin)


if __name__=="__main__":unittest.main()
