"""No-retail-asset tests for source-cache original triangle slope histogram."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"dx2"))
import audit_source_surface_slope_cache as audit

SHA="1"*64


def fixture():
    return {
        "schema":audit.CACHE_SCHEMA,
        "source_map":"Synthetic.gmp",
        "source_sha256":SHA,
        "read_only":True,
        "not_a_native_collision_writer":True,
        "physics_materials_verified":False,
        "coordinate_system":audit.COORD,
        "edge_provenance_schema":audit.EDGE_SCHEMA,
        "source_flat_vertex_count":4,
        "source_triangle_count":2,
        "mopp_leaf_triangle_count":2,
        "vertices_godot_xyz":[[0.,0.,0.],[2.,0.,0.],[0.,0.,2.],[2.,0.,2.]],
        "render_material_names":["MatA","MatB"],
        "leaf_triangles":[
            {"triangle_id":0,"vertex_indices":[0,1,2],
             "source_edge_kinds":[1,2,1]},
            {"triangle_id":1,"vertex_indices":[1,3,2],
             "source_edge_kinds":[1,1,2]},
        ],
        "source_topology_summary":{
            "source_exact_welded_vertex_count":4,
            "unique_source_edges":5,
            "open_boundary_edges":4,
            "two_triangle_same_material_edges":0,
            "two_triangle_render_material_seams":1,
            "three_or_more_triangle_edges":0,
            "max_triangles_using_one_edge":2,
        }
    }


def one_face(verts):
    doc=fixture()
    doc["vertices_godot_xyz"]=verts
    doc["source_flat_vertex_count"]=3
    doc["source_triangle_count"]=1
    doc["mopp_leaf_triangle_count"]=1
    doc["leaf_triangles"]=[{
        "triangle_id":0,"vertex_indices":[0,1,2],
        "source_edge_kinds":[1,1,1]}]
    doc["source_topology_summary"].update({
        "source_exact_welded_vertex_count":3,
        "unique_source_edges":3,
        "open_boundary_edges":3,
        "two_triangle_same_material_edges":0,
        "two_triangle_render_material_seams":0,
        "max_triangles_using_one_edge":1,
    })
    return doc


class SurfaceSlopeCacheTests(unittest.TestCase):
    def test_two_original_flat_surfaces_report_aggregate_only(self):
        doc=fixture()
        before=hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest()
        result=audit.inspect_document(doc,SHA)
        self.assertEqual(result["source_mopp_nonzero_area_leaf_triangles"],2)
        self.assertEqual(result["counts"]["plane_slope_0_to_5_degrees"],2)
        self.assertEqual(result["edge_uses_by_source_class"]["different_render_material_seam"],2)
        self.assertFalse(result["walkable_floor_or_ceiling_verified"])
        self.assertFalse(result["original_source_coordinates_in_result"])
        self.assertNotIn("vertices_godot_xyz",json.dumps(result))
        self.assertEqual(before,hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest())

    def test_analytic_ramp_matches_5_to_30_degree_bucket(self):
        doc=one_face([[0,0,0],[2,1,0],[0,0,2]])
        result=audit.inspect_document(doc,SHA)
        self.assertEqual(result["counts"]["plane_slope_over_5_to_30_degrees"],1)

    def test_vertical_source_wall_is_75_to_90_degrees(self):
        doc=one_face([[0,0,0],[0,2,0],[0,0,2]])
        result=audit.inspect_document(doc,SHA)
        self.assertEqual(result["counts"]["plane_slope_over_75_to_90_degrees"],1)

    def test_original_triangle_id_gaps_are_preserved(self):
        doc=fixture()
        doc["source_triangle_count"]=3
        doc["leaf_triangles"][1]["triangle_id"]=2
        result=audit.inspect_document(doc,SHA)
        self.assertEqual(result["source_triangle_total"],3)
        self.assertEqual(result["source_mopp_nonzero_area_leaf_triangles"],2)

    def test_source_sha_and_authentication_flags_fail_closed(self):
        doc=fixture()
        for change in [
            {"source_sha256":"2"*64},
            {"physics_materials_verified":True},
            {"read_only":False},
            {"coordinate_system":"wrong"},
            {"edge_provenance_schema":"old"},
        ]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                audit.inspect_document(doc|change,SHA)

    def test_nonexistent_or_degenerate_geometry_is_rejected(self):
        doc=fixture()
        bad=copy.deepcopy(doc)
        bad["leaf_triangles"][0]["vertex_indices"]=[0,0,0]
        with self.assertRaises(ValueError):
            audit.inspect_document(bad,SHA)
        bad=copy.deepcopy(doc)
        bad["leaf_triangles"][0]["triangle_id"]=99999
        with self.assertRaises(ValueError):
            audit.inspect_document(bad,SHA)

    def test_edge_source_provenance_count_conflict_is_rejected(self):
        doc=fixture()
        doc["leaf_triangles"][1]["source_edge_kinds"]=[1,1,1]
        with self.assertRaises(ValueError):
            audit.inspect_document(doc,SHA)

    def test_read_only_cli_output_and_no_private_coords(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cache_dir=root/"private_cache"
            cache_dir.mkdir()
            path=cache_dir/"source_collision_selection_v2.json"
            path.write_text(json.dumps(fixture()),encoding="utf-8")
            before=path.read_bytes()
            out=root/"public_aggregate"/"slope_counts.json"
            self.assertEqual(audit.main([
                "--cache",str(path),"--expected-sha256",SHA,
                "--report",str(out)]),0)
            self.assertTrue(out.is_file())
            self.assertNotIn("vertices_godot_xyz",out.read_text())
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(audit.main([
                "--cache",str(path),"--expected-sha256",SHA,
                "--report",str(out)]),1)
            self.assertEqual(path.read_bytes(),before)

    def test_cli_rejects_reports_inside_private_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/"source_collision_selection_v2.json"
            path.write_text(json.dumps(fixture()),encoding="utf-8")
            output=root/"slope.json"
            self.assertEqual(audit.main([
                "--cache",str(path),"--expected-sha256",SHA,
                "--report",str(output)]),1)
            self.assertFalse(output.exists())


if __name__=="__main__":
    unittest.main()
