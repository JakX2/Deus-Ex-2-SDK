"""Synthetic multi-archive custom DDS import tests."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_custom_texture_import import plan, write_trial, patch_mlb, import_clone
from dx2_ibd_integrity import verify_bundle, sha256
from dx2_ibd_repack import _parts,_build
from dx2_material_writer import inspect_material, select_material
from dx2_texture_writer import inspect_layout, select_texture, marker_mips, to_dds
from test_dx2_material_writer import fixture


def make_sources():
    raw=fixture()
    b=verify_bundle(raw)
    r=select_material(b,"test_material")
    rows=_parts(raw,b)
    rows[r.index]=list(rows[r.index])
    src=b"..\\Content\\DX2\\MatLib\\DynamicallyLoaded\\test.mlb\0"
    rows[r.index][17:19]=[struct.pack("<I",len(src)),src]
    raw=_build(raw,b,rows)
    b=verify_bundle(raw)
    mat=inspect_material(b,select_material(b,"test_material"))
    record=bytearray(788)
    record[:13]=b"test_material"
    record[64:68]=mat.parts[2]
    record[144:148]=mat.parts[1]
    record[148:159]=b"fixture_tex"
    record[700:704]=b"DATA"  # preserve unknown bytes
    mlb=struct.pack("<3I",3,0xface,1)+record
    layout=inspect_layout(b,select_texture(b,"fixture_tex"))
    dds=to_dds(layout.texture)[:128]+b"".join(marker_mips(layout,"cyan"))
    return raw,bytes(mlb),dds


class CustomImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.raw,self.mlb,self.dds=make_sources()
        self.ibd_zip=self.root/"bundles.zip"
        self.mlb_zip=self.root/"libraries.zip"
        self._write()
        self.dds_path=self.root/"custom.dds"
        self.dds_path.write_bytes(self.dds)

    def _write(self,extra=None,mlb=None):
        with zipfile.ZipFile(self.ibd_zip,"w") as z:
            z.writestr("A.ibd",self.raw)
            z.writestr("B.ibd",self.raw)
            if extra is not None:z.writestr("other.ibd",extra)
        with zipfile.ZipFile(self.mlb_zip,"w") as z:
            z.writestr("MatLib/DynamicallyLoaded/test.mlb",self.mlb if mlb is None else mlb)
            z.writestr("MatLib/test.mlb",self.mlb)
        self.ip=sha256(self.ibd_zip.read_bytes())
        self.mp=sha256(self.mlb_zip.read_bytes())

    def args(self,name="SDK_Custom_Texture"):
        return (self.ibd_zip,self.mlb_zip,self.ip,self.mp,
                "MatLib/DynamicallyLoaded/test.mlb","test_material",name)

    def test_two_bundle_import_and_precise_library_change(self):
        results,receipt=plan(*self.args(),self.dds)
        self.assertEqual(receipt["coordinated_bundle_instances"],2)
        self.assertEqual(receipt["libraries_scanned"],2)
        self.assertEqual(set(results),{"Maps/A.ibd","Maps/B.ibd","MatLib/DynamicallyLoaded/test.mlb"})
        self.assertFalse(receipt["runtime_verified"])
        for path in ("Maps/A.ibd","Maps/B.ibd"):
            old,new=results[path]
            b=verify_bundle(new)
            layout=inspect_layout(b,select_texture(b,"SDK_Custom_Texture"))
            self.assertEqual(to_dds(layout.texture),self.dds)
            self.assertEqual(inspect_material(b,select_material(b,"test_material")).stages[0],"SDK_Custom_Texture")
            self.assertEqual(old,self.raw)
        old,new=results["MatLib/DynamicallyLoaded/test.mlb"]
        self.assertEqual(new[:160],old[:160])
        self.assertEqual(new[224:],old[224:])
        self.assertEqual(new[160:224],b"SDK_Custom_Texture".ljust(64,b"\0"))
        self.assertEqual(old,self.mlb)

    def test_pin_name_and_dds_rejections(self):
        for name in ("FIXTURE_TEX","a"*64,"../new","test_material"):
            with self.subTest(name=name),self.assertRaises(ValueError):
                plan(*self.args(name),self.dds)
        with self.assertRaisesRegex(ValueError,"SHA-256"):
            plan(self.ibd_zip,self.mlb_zip,"0"*64,self.mp,*self.args()[4:],self.dds)
        with self.assertRaises(ValueError):
            plan(*self.args(),self.dds[:-1])

    def test_name_collision_in_unselected_standalone_stage(self):
        bad=bytearray(self.mlb)
        bad[224:288]=b"SDK_Custom_Texture".ljust(64,b"\0")
        self._write(mlb=bytes(bad))
        with self.assertRaisesRegex(ValueError,"already referenced"):
            plan(*self.args(),self.dds)

    def test_dirty_diffuse_tail_and_mismatched_flags_refused(self):
        for pos in (12+148+63,12+144,12+64):
            bad=bytearray(self.mlb)
            bad[pos]^=1
            self._write(mlb=bytes(bad))
            with self.assertRaisesRegex(ValueError,"zero-tail"):
                plan(*self.args(),self.dds)

    def test_disk_trial_outputs_and_no_overwrite(self):
        output=self.root/"trial"
        result=write_trial(*self.args(),self.dds_path,output)
        self.assertEqual(len(result["files"]),3)
        for row in result["files"]:
            self.assertEqual(sha256((output/row["relative_path"]).read_bytes()),row["candidate_sha256"])
        self.assertEqual(sha256(self.ibd_zip.read_bytes()),self.ip)
        self.assertEqual(sha256(self.mlb_zip.read_bytes()),self.mp)
        with self.assertRaisesRegex(ValueError,"isolated"):
            write_trial(*self.args(),self.dds_path,output)

    def test_unsafe_windows_candidate_destination_refused(self):
        for name in ("CON.ibd","bad:stream.ibd","bad?.ibd"):
            with self.subTest(name=name):
                with zipfile.ZipFile(self.ibd_zip,"w") as z:
                    z.writestr(name,self.raw)
                self.ip=sha256(self.ibd_zip.read_bytes())
                with self.assertRaisesRegex(ValueError,"portable output path"):
                    plan(*self.args(),self.dds)

    def test_disagreeing_bundled_material_instances_refused(self):
        b=verify_bundle(self.raw)
        rows=_parts(self.raw,b)
        i=select_material(b,"test_material").index
        rows[i]=list(rows[i])
        rows[i][1]=struct.pack("<I",7)
        disagreeing=_build(self.raw,b,rows)
        with zipfile.ZipFile(self.ibd_zip,"w") as z:
            z.writestr("A.ibd",self.raw)
            z.writestr("B.ibd",disagreeing)
        self.ip=sha256(self.ibd_zip.read_bytes())
        with self.assertRaisesRegex(ValueError,"instances disagree"):
            plan(*self.args(),self.dds)

    def test_original_dds_still_creates_new_texture(self):
        b=verify_bundle(self.raw)
        layout=inspect_layout(b,select_texture(b,"fixture_tex"))
        candidate=import_clone(self.raw,"test_material","new_texture",to_dds(layout.texture))
        after=verify_bundle(candidate)
        self.assertEqual(len(after.resources),len(b.resources)+1)
        new=inspect_layout(after,select_texture(after,"new_texture"))
        self.assertEqual(to_dds(new.texture),to_dds(layout.texture))


if __name__=="__main__":
    unittest.main()
