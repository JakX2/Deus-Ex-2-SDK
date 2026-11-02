"""BF material sections are non-rendering in Ion Storm's T3SDK reference.

Keep DX2 static meshes consistent with existing BSP BF suppression so
placeholder geometry does not obscure the map preview.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2bundles import Mesh
from dx2level import Builder


def mesh_with_skins(materials):
    return Mesh(
        name="WTOFixture", skins=[{"name":"Default", "materials":materials}],
        flags=0, hardpoints=[],
        positions=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)],
        normals=[(0.,0.,1.)] * 4, uv=[(0.,0.)] * 4,
        indices=[0,1,2,0,2,3],
        sections=[
            {"name":"BF", "first_index":0, "index_count":3},
            {"name":"Stone", "first_index":3, "index_count":3},
        ],
        bounds=[[0.,0.,0.],[1.,1.,1.]],
    )


class HiddenMeshSectionTests(unittest.TestCase):
    def test_bf_source_section_is_not_exported(self):
        builder = Builder({}, {}, {}, alternate_skin_fallback=False)
        idx = builder.mesh_data(mesh_with_skins(["BF","Stone"]), "Mission.ibd")
        self.assertEqual(idx, 0)
        record = builder.doc["meshes"][idx]
        self.assertEqual(len(record["primitives"]), 1)
        self.assertEqual(record["extras"]["meshTriangles"], 2)
        self.assertEqual(record["extras"]["DX2VisibleTriangles"], 1)
        self.assertEqual(builder.doc["materials"][0]["name"],"Stone")

    def test_all_hidden_mesh_has_no_render_primitive(self):
        builder = Builder({}, {}, {}, alternate_skin_fallback=False)
        self.assertIsNone(builder.mesh_data(mesh_with_skins(["BF","bf"]), "Mission.ibd"))
        self.assertEqual(builder.doc["meshes"], [])

    def test_effective_skin_controls_visibility(self):
        # The selected skin is authoritative; source section labels are not
        # enough to hide a face when a real material overrides its name.
        builder = Builder({}, {}, {}, alternate_skin_fallback=False)
        idx = builder.mesh_data(mesh_with_skins(["Stone","Stone"]), "Mission.ibd")
        self.assertEqual(len(builder.doc["meshes"][idx]["primitives"]),2)
        self.assertEqual(builder.doc["meshes"][idx]["extras"]["DX2VisibleTriangles"],2)


if __name__ == "__main__":
    unittest.main()
