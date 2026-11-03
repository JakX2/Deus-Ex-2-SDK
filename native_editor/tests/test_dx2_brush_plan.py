"""Asset-free tests for DX2Ed brush authoring plans; no retail data or native writer."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "godot_editor" / "backend"))
import dx2_brush_plan as plan

IDENTITY = [1,0,0, 0,1,0, 0,0,1, 0,0,0]


def brush(transform=None, kind="Box", size=None, name="DraftProp_1"):
    return {"name":name, "from_actor":"Brush::"+kind,
            "transform":transform if transform is not None else list(IDENTITY),
            "brush":{"kind":kind,"size":size if size is not None else [2,4,6], "steps":1},
            "class_template":{}}


def draft(copies=None):
    return {"schema":"DX2Ed-prop-draft-v1",
            "map_cache":"synthetic-private-cache-identifier",
            "coordinate_space":plan.COORDS_IN,
            "read_only_source":True, "moved":[], "property_edits":[],
            "copies": copies if copies is not None else [brush()]}


class BrushPlanTests(unittest.TestCase):
    def test_outward_faces_and_dimensions(self):
        result = plan.build_plan(draft(), "abc")
        self.assertEqual(result["schema"], plan.SCHEMA_OUT)
        self.assertFalse(result["native_bsp_compiled"])
        self.assertFalse(result["collision_generated"])
        b = result["brushes"][0]
        self.assertEqual(len(b["faces_quads_outward_ue"]), 6)
        self.assertEqual(len(b["world_vertices_ue_units"]), 8)
        self.assertAlmostEqual(b["bounds_ue_units"]["max"][0], 1/plan.SCALE_METRES_PER_UE_UNIT)
        self.assertAlmostEqual(b["bounds_ue_units"]["max"][1], 3/plan.SCALE_METRES_PER_UE_UNIT)
        self.assertAlmostEqual(b["bounds_ue_units"]["max"][2], 2/plan.SCALE_METRES_PER_UE_UNIT)
        center = plan._mean(b["world_vertices_ue_units"])
        for face in b["faces_quads_outward_ue"]:
            points = [b["world_vertices_ue_units"][i] for i in face["vertices"]]
            n = plan._cross(plan._sub(points[1],points[0]),plan._sub(points[2],points[0]))
            self.assertGreater(plan._dot(n, plan._sub(plan._mean(points),center)), 0)
            self.assertAlmostEqual(plan._length(face["normal"]), 1)

    def test_axis_conversion_rotation_and_translation(self):
        rotate = [0,0,-1, 0,1,0, 1,0,0, 10,20,30]
        b = plan.build_plan(draft([brush(transform=rotate)]), "hash")["brushes"][0]
        self.assertAlmostEqual(b["origin_ue_units"][0], 10/plan.SCALE_METRES_PER_UE_UNIT)
        self.assertAlmostEqual(b["origin_ue_units"][1], 30/plan.SCALE_METRES_PER_UE_UNIT)
        self.assertAlmostEqual(b["origin_ue_units"][2], 20/plan.SCALE_METRES_PER_UE_UNIT)
        self.assertAlmostEqual(b["bounds_ue_units"]["max"][0], 13/plan.SCALE_METRES_PER_UE_UNIT)

    def test_multiple_types_and_mixed_edit_refusal(self):
        result = plan.build_plan(draft([brush(kind="Wall"), brush(kind="Floor",name="DraftProp_2")]),"sha")
        self.assertEqual(len(result["brushes"]), 2)
        for field, value in [("moved",[{"actor":"x"}]),("property_edits",[{"property":1}])]:
            document = draft()
            document[field] = value
            with self.assertRaisesRegex(ValueError, "Non-brush draft edits"):
                plan.build_plan(document,"sha")

    def test_fail_closed_on_stairs_shear_mirror_nan_bool_duplicates_and_limits(self):
        cases = [
            [brush(kind="Stairs")],
            [brush(transform=[1,0,0, 1,1,0, 0,0,1, 0,0,0])],
            [brush(transform=[-1,0,0, 0,1,0, 0,0,1, 0,0,0])],
            [brush(size=[2,float("nan"),6])],
            [brush(size=[True,2,3])],
            [brush(), brush()],
            [brush(kind="Wall",size=[0.01,2,3])],
        ]
        for copies in cases:
            with self.subTest(copies=str(copies)[:70]), self.assertRaises(ValueError):
                plan.build_plan(draft(copies),"sha")
        with self.assertRaisesRegex(ValueError, "excessive"):
            plan.build_plan(draft([brush(name=f"DraftProp_{i}") for i in range(129)]),"sha")

    def test_bad_draft_metadata_rejected(self):
        for change in (
            lambda d: d["copies"][0].update(from_actor="Brush::Wall"),
            lambda d: d["copies"][0].update(class_template={"qualified":"Actor"}),
            lambda d: d.update(coordinate_space="unknown"),
            lambda d: d.update(read_only_source=False),
            lambda d: d.update(schema="broken"),
        ):
            document = draft()
            change(document)
            with self.assertRaises(ValueError):
                plan.build_plan(document,"hash")

    def test_file_input_not_modified_and_output_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/"drafts"/"draft.json"
            source.parent.mkdir()
            raw = json.dumps(draft()).encode("utf8")
            source.write_bytes(raw)
            dest = root/"reports"/"plan.json"
            result = plan.convert_file(source,dest)
            self.assertEqual(result["source_draft_sha256"],hashlib.sha256(raw).hexdigest())
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(json.loads(dest.read_text())["schema"],plan.SCHEMA_OUT)
            self.assertNotIn("synthetic-private-cache-identifier",dest.read_text())
            with self.assertRaises(FileExistsError):
                plan.convert_file(source,dest)
            with self.assertRaisesRegex(ValueError,"outside the original draft"):
                plan.convert_file(source,source.parent/"plan.json")
            with self.assertRaisesRegex(ValueError,"overwrite the source draft"):
                plan.convert_file(source,source)

    def test_no_brushes_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "No draft brushes"):
            plan.build_plan(draft([]),"sha")


if __name__ == "__main__":
    unittest.main()
