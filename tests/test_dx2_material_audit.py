"""Aggregate-only material audit regressions with synthetic data."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_material_audit import audit,read_mlb,source_key
from dx2_material_writer import inspect_material,select_material
from dx2_ibd_integrity import verify_bundle
from dx2_ibd_repack import _parts,_build
from test_dx2_material_writer import fixture


class AuditTests(unittest.TestCase):
    def test_full_path_matching_and_clone_audit(self):
        raw=fixture()
        b=verify_bundle(raw)
        r=select_material(b,"test_material")
        rows=_parts(raw,b)
        rows[r.index]=list(rows[r.index])
        src=b"..\\Content\\DX2\\MatLib\\DynamicallyLoaded\\synthetic.mlb\0"
        rows[r.index][17:19]=[struct.pack("<I",len(src)),src]
        raw=_build(raw,b,rows)
        b=verify_bundle(raw)
        m=inspect_material(b,select_material(b,"test_material"))
        record=bytearray(788)
        record[:13]=b"test_material"
        record[64:68]=m.parts[2]
        record[144:148]=m.parts[1]
        record[148:159]=b"fixture_tex"
        library=struct.pack("<3I",3,0xface,1)+record
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ibd=root/"bundles.zip"
            mlb=root/"libraries.zip"
            with zipfile.ZipFile(ibd,"w") as z:z.writestr("source.ibd",raw)
            with zipfile.ZipFile(mlb,"w") as z:
                z.writestr("MatLib/synthetic.mlb",library)
                z.writestr("MatLib/DynamicallyLoaded/synthetic.mlb",library)
            result=audit(ibd,mlb_zip=mlb,verify_clones=True)
            c=result["counts"]
            self.assertEqual(c["mlb_libraries"],2)
            self.assertEqual(c["mlb_unique_matches"],1)
            self.assertEqual(c["mlb_diffuse_exact"],1)
            self.assertEqual(c["mlb_flags_exact"],1)
            self.assertEqual(c["mlb_stage_mask_exact"],1)
            self.assertEqual(c["clone_reversals"],1)
            self.assertFalse(result["runtime_verified"])
            self.assertNotIn("test_material",str(result))

    def test_bad_library_format_and_source_paths(self):
        for raw in (b"",struct.pack("<3I",3,0xface,1),struct.pack("<3I",4,0xface,0)):
            with self.assertRaises(ValueError):read_mlb(raw)
        self.assertIsNone(source_key(""))
        self.assertIsNone(source_key("MatLib/../a.mlb"))
        self.assertEqual(source_key(r"..\Content\DX2\MatLib\A.MLB"),"matlib/a.mlb")


if __name__=="__main__":
    unittest.main()
