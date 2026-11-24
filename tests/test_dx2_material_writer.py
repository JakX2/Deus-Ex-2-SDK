"""Synthetic material binding and append-only texture reconstruction tests."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_ibd_integrity import verify_bundle
from dx2_ibd_repack import _build, _parts, rebuild_canonical
from dx2_material_writer import (inspect_material, select_material, retarget_diffuse,
    clone_and_bind, reverse_clone_trial, write_candidate)
from dx2_texture_writer import inspect_layout, select_texture, marker_mips
from test_dx2_texture_writer import make_fixture


def fixture():
    base=make_fixture()
    b=verify_bundle(base)
    rows=_parts(base,b)
    records=[base[52+304*i:52+304*(i+1)] for i in range(len(rows))]
    def record(typ,name):
        r=bytearray(304)
        r[40]=typ
        r[41:41+len(name)]=name
        return bytes(r)
    u=lambda v: struct.pack("<I",v)
    def string(s): return [u(len(s)+1),s+b"\0"]
    color=struct.pack("<4f",0,0,0,1)
    mat=[b"\0",u(1),u(1),color,color,color,u(0),u(0),u(0),b"\1",u(0),u(0),
         b"\1",b"\0",b"\0",u(0),u(0)]+string(b"synthetic.mlb")+[u(0),b"\0",u(0)]
    for stage in [b"fixture_tex"]+[b""]*8:
        mat.extend(string(stage))
    rows.append(mat)
    records.append(record(10,b"test_material"))
    rows.append(list(rows[0]))
    records.append(record(8,b"another_texture"))
    return _build(base,b,rows,record_templates=records)


class MaterialWriterTests(unittest.TestCase):
    def test_original_layout_and_existing_retarget(self):
        raw=fixture()
        b=verify_bundle(raw)
        mat=inspect_material(b,select_material(b,"test_material"))
        self.assertEqual(mat.stages[0],"fixture_tex")
        result=retarget_diffuse(raw,"test_material","another_texture")
        a=verify_bundle(result)
        m=inspect_material(a,select_material(a,"test_material"))
        self.assertEqual(m.stages[0],"another_texture")
        self.assertEqual(m.parts[:22],mat.parts[:22])
        self.assertEqual(m.parts[24:],mat.parts[24:])
        self.assertEqual(retarget_diffuse(result,"test_material","fixture_tex"),raw)

    def test_append_moves_header_boundary_and_preserves_original_texture(self):
        raw=fixture()
        old=verify_bundle(raw)
        new_name="custom_texture_longer"
        result=clone_and_bind(raw,"test_material",new_name,palette="magenta")
        b=verify_bundle(result)
        self.assertEqual(b.data_start,old.data_start+2048)
        self.assertEqual(len(b.resources),len(old.resources)+1)
        for before,after in zip(old.resources,b.resources):
            self.assertEqual((before.name,before.typ,before.index),(after.name,after.typ,after.index))
            if before.typ!=10:self.assertEqual(old.raw(before),b.raw(after))
        clone=select_texture(b,new_name)
        self.assertEqual(clone.index,len(old.resources))
        self.assertEqual(clone.first_part,old.part_count)
        layout=inspect_layout(old,select_texture(old,"fixture_tex"))
        altered=inspect_layout(b,clone)
        self.assertEqual(tuple(altered.parts[i] for i in altered.pixel_slots),marker_mips(layout,"magenta"))
        self.assertEqual(rebuild_canonical(result),result)
        self.assertEqual(reverse_clone_trial(result,hashlib.sha256(raw).hexdigest(),
            "test_material","fixture_tex",new_name,palette="magenta"),raw)

    def test_refuse_bad_names_missing_bindings_and_wrong_reverse_pin(self):
        raw=fixture()
        for name in ("","../name","fixture_tex","TEST_MATERIAL","a"*97):
            with self.subTest(name=name),self.assertRaises(ValueError):
                clone_and_bind(raw,"test_material",name)
        with self.assertRaises(ValueError):
            retarget_diffuse(raw,"test_material","missing")
        with self.assertRaises(ValueError):
            retarget_diffuse(raw,"test_material","fixture_tex")
        result=clone_and_bind(raw,"test_material","new_name")
        with self.assertRaisesRegex(ValueError,"original SHA-256"):
            reverse_clone_trial(result,"0"*64,"test_material","fixture_tex","new_name")

    def test_material_mask_and_string_corruption_refused(self):
        raw=fixture()
        b=verify_bundle(raw)
        rows=_parts(raw,b)
        i=select_material(b,"test_material").index
        for slot,replacement in ((2,struct.pack("<I",3)),(22,struct.pack("<I",99)),(23,b"a\0b\0")):
            edited=list(rows)
            edited[i]=list(rows[i])
            edited[i][slot]=replacement
            malformed=_build(raw,b,edited)
            with self.subTest(slot=slot),self.assertRaises(ValueError):
                clone_and_bind(malformed,"test_material","new_name")

    def test_nonzero_name_tail_refused(self):
        raw=bytearray(fixture())
        b=verify_bundle(bytes(raw))
        raw[52+304*select_texture(b,"fixture_tex").index+300]=1
        raw[32:52]=bytes(20)
        raw[32:52]=hashlib.sha1(raw[:b.data_start]).digest()
        with self.assertRaisesRegex(ValueError,"unknown nonzero"):
            clone_and_bind(bytes(raw),"test_material","new_name")

    def test_pinned_disk_candidate_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"source"/"test.ibd"
            source.parent.mkdir()
            raw=fixture()
            source.write_bytes(raw)
            pin=hashlib.sha256(raw).hexdigest()
            target=root/"isolated"/source.name
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                write_candidate(source,target,"0"*64,"test_material",new_name="new")
            self.assertFalse(target.exists())
            receipt=write_candidate(source,target,pin,"test_material",new_name="new",palette="cyan")
            self.assertFalse(receipt["runtime_verified"])
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(target.read_bytes(),clone_and_bind(raw,"test_material","new",palette="cyan"))
            with self.assertRaisesRegex(ValueError,"isolated"):
                write_candidate(source,target,pin,"test_material",new_name="new")


if __name__=="__main__":
    unittest.main()
