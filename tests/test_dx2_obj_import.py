"""OBJ conversion regression tests; no external assets."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_obj_import import convert_obj, PREVIEW_SCALE
from dx2_mesh_writer import replace_geometry,inspect_template,select_mesh
from dx2_ibd_integrity import verify_bundle
from test_dx2_mesh_writer import fixture

OBJ = """# native plane
o imported
v 0 0 0
v 2 0 0
v 2 1 0
v 0 1 0
vt 0 0
vt 1 0
vt 1 1
vt 0 1
vn 0 0 1
usemtl example
f 1/1/1 2/2/1 3/3/1
f 1/1/1 3/3/1 4/4/1
"""


class ObjImportTests(unittest.TestCase):
    def test_native_and_real_serialization(self):
        g=convert_obj(OBJ)
        self.assertEqual(len(g["positions"]),4)
        self.assertEqual(g["indices"],[0,1,2,0,2,3])
        g["positions"][1][0]=3
        candidate=replace_geometry(fixture(),"fixture_mesh",g)
        b=verify_bundle(candidate)
        m=inspect_template(b,select_mesh(b,"fixture_mesh"))
        self.assertEqual(m.mesh.bounds,[0,0,0,3,1,0])

    def test_preview_coordinates_and_winding(self):
        # SDK preview exports (x,z,y)*scale and reverses triangle winding.
        s=PREVIEW_SCALE
        source=f"""v 0 0 0
v {2*s} 0 0
v 0 0 {s}
vt 0 0
vt 1 0
vt 0 1
vn 0 1 0
f 1/1/1 3/3/1 2/2/1
"""
        doc=convert_obj(source,coordinates="sdk-preview")
        self.assertEqual(doc["positions"],[[0,0,0],[2,0,0],[0,1,0]])
        self.assertEqual(doc["normals"],[[0,0,1]]*3)
        self.assertEqual(doc["indices"],[0,1,2])

    def test_seam_splits_distinct_corner_attributes(self):
        source=OBJ.replace("vn 0 0 1","vt .1 .1\nvn 0 0 1").replace(
            "f 1/1/1 3/3/1 4/4/1","f 1/5/1 3/3/1 4/4/1")
        doc=convert_obj(source)
        self.assertEqual(len(doc["positions"]),5)
        self.assertEqual(doc["positions"][0],doc["positions"][3])
        self.assertNotEqual(doc["uv"][0],doc["uv"][3])

    def test_unsupported_or_invalid_faces_refused(self):
        for source in (OBJ.replace("f 1/1/1 2/2/1 3/3/1","f 1/1/1 2/2/1 3/3/1 4/4/1"),
                       OBJ.replace("1/1/1","1//1"),OBJ.replace("1/1/1","-1/1/1"),
                       OBJ.replace("1/1/1","9/1/1"),OBJ.replace("vn 0 0 1","vn 0 0 -1"),
                       OBJ.replace("f 1/1/1 3/3/1 4/4/1","usemtl another\nf 1/1/1 3/3/1 4/4/1")):
            with self.subTest(source=source),self.assertRaises(ValueError):
                convert_obj(source)


if __name__=="__main__":unittest.main()
