"""Asset-free original Level exact-coordinate weld adjacency cache v3 tests."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"native_editor"/"godot_editor"/"backend"))
from test_dx2_collision_selection_cache import fixture_atlas
import dx2_collision_edge_provenance as edges
import dx2_collision_selection_cache as cache

SHA="1"*64


def duplicated_level_vertices(*,separate=0.):
    atlas=copy.deepcopy(fixture_atlas())
    vertices=atlas["vertices"]
    current=atlas["triangles"][1]["vertex_indices_zero_based"]
    new=[]
    for oldid in current:
        xyz=vertices[oldid]
        new.append(len(vertices))
        vertices.append(tuple(float(x)+separate for x in xyz))
    atlas["triangles"][1]["vertex_indices_zero_based"]=new
    atlas["source_vertex_count"]=len(vertices)
    return atlas


class ExactSourceEdgeCacheTests(unittest.TestCase):
    def test_original_duplicate_source_indices_weld_to_exact_original_coords(self):
        atlas=duplicated_level_vertices()
        found=edges.classify_source_edges(atlas)
        self.assertEqual(found["source_exact_welded_vertex_count"],4)
        self.assertEqual(found["two_triangle_render_material_seams"],1)
        self.assertEqual(len(found["exact_source_weld_id_by_vertex_index"]),7)
        doc=cache.prepare_doc(atlas,source_name="Fixture.gmp",source_sha256=SHA)
        self.assertEqual(doc["schema"],cache.SCHEMA)
        self.assertEqual(doc["source_edge_welding"],"exact_original_Level_XYZ_no_epsilon")
        first=doc["leaf_triangles"][0]["source_weld_ids"]
        second=doc["leaf_triangles"][1]["source_weld_ids"]
        self.assertEqual(len(set(first)&set(second)),2)
        self.assertNotEqual(set(doc["leaf_triangles"][0]["vertex_indices"]),
                            set(doc["leaf_triangles"][1]["vertex_indices"]))
        self.assertEqual(doc["source_topology_summary"]["two_triangle_render_material_seams"],1)

    def test_subpreview_coordinate_delta_is_never_epsilon_welded(self):
        atlas=duplicated_level_vertices(separate=0.00000001)
        found=edges.classify_source_edges(atlas)
        self.assertEqual(found["two_triangle_render_material_seams"],0)
        self.assertEqual(found["open_boundary_edges"],6)
        doc=cache.prepare_doc(atlas,source_name="Fixture.gmp",source_sha256=SHA)
        self.assertTrue(set(doc["leaf_triangles"][0]["source_weld_ids"]).isdisjoint(
            set(doc["leaf_triangles"][1]["source_weld_ids"])))

    def test_source_weld_ids_in_triangles_refer_to_vertex_weld_ids(self):
        atlas=fixture_atlas()
        found=edges.classify_source_edges(atlas)
        doc=cache.prepare_doc(atlas,source_name="Fixture.gmp",source_sha256=SHA)
        for face in doc["leaf_triangles"]:
            for original_index,welded_index in zip(
                face["vertex_indices"],face["source_weld_ids"]):
                self.assertEqual(
                    welded_index,
                    found["exact_source_weld_id_by_vertex_index"][original_index])

    def test_zero_area_original_nonleaf_keeps_triangle_id_gap_and_welds(self):
        atlas=fixture_atlas(degenerate=True)
        doc=cache.prepare_doc(atlas,source_name="Fixture.gmp",source_sha256=SHA)
        self.assertEqual([f["triangle_id"] for f in doc["leaf_triangles"]],[1])
        self.assertEqual(len(doc["leaf_triangles"][0]["source_weld_ids"]),3)
        self.assertEqual(doc["source_topology_summary"]["open_boundary_edges"],3)

    def test_original_atlas_is_never_mutated(self):
        atlas=duplicated_level_vertices()
        before=copy.deepcopy(atlas)
        edges.classify_source_edges(atlas)
        cache.prepare_doc(atlas,source_name="Fixture.gmp",source_sha256=SHA)
        self.assertEqual(atlas,before)

    def test_new_schema_rejects_legacy_v2_interpretation(self):
        self.assertEqual(cache.SCHEMA,"DX2Ed-source-MOPP-collision-selection-cache-v3")
        doc=cache.prepare_doc(
            fixture_atlas(),source_name="Fixture.gmp",source_sha256=SHA)
        self.assertNotEqual(doc["schema"],"DX2Ed-source-MOPP-collision-selection-cache-v2")
        self.assertTrue(all(len(f["source_weld_ids"])==3 for f in doc["leaf_triangles"]))


if __name__=="__main__":
    unittest.main()
