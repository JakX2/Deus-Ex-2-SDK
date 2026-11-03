"""Synthetic tests for DX2 BSP world-node vs Level render-triangle spatial audit."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_bsp_render_spatial_candidates as audit


TRIANGLE = ((0.,0.,0.), (1.,0.,0.), (0.,1.,0.))
PLANE = (0.,0.,1.,0.)
SPHERE = (0.,0.,0.,4.)


def labelled(triangle=TRIANGLE):
    return [([0,0,0], triangle)]


class CrossRenderTests(unittest.TestCase):
    def test_unique_candidate_and_opposite_winding(self):
        for tri in (TRIANGLE, TRIANGLE[::-1]):
            with self.subTest(winding=tri):
                r = audit.analyze_spatial_candidates(
                    [(PLANE, SPHERE)], labelled(tri), include_matches=True)
                self.assertEqual(r["counts"]["same_infinite_plane"],1)
                self.assertEqual(r["counts"]["all_triangle_vertices_in_node_sphere"],1)
                self.assertEqual(r["counts"]["unique_candidate"],1)
                self.assertEqual(r["candidate_triangle_nodes"][0]["candidate_nodes"],[0])

    def test_same_plane_but_outside_bounding_sphere_not_assigned(self):
        r = audit.analyze_spatial_candidates(
            [(PLANE,(0.,0.,0.,0.2))], labelled())
        self.assertEqual(r["counts"]["same_infinite_plane"],1)
        self.assertNotIn("all_triangle_vertices_in_node_sphere",r["counts"])
        self.assertEqual(r["examples"]["spatial_unmatched"],[[0,0,0]])

    def test_wrong_plane_offset_is_not_a_match(self):
        r = audit.analyze_spatial_candidates(
            [((0.,0.,1.,5.),SPHERE)],labelled())
        self.assertEqual(r["counts"]["nondegenerate_triangles"],1)
        self.assertNotIn("same_infinite_plane",r["counts"])
        self.assertEqual(r["examples"]["plane_unmatched"],[[0,0,0]])

    def test_coplanar_overlapping_nodes_are_ambiguous(self):
        r = audit.analyze_spatial_candidates(
            [(PLANE,SPHERE),(PLANE,(0.5,0.5,0.,6.))],
            labelled(),include_matches=True)
        self.assertEqual(r["counts"]["ambiguous_candidates"],1)
        self.assertNotIn("unique_candidate",r["counts"])
        self.assertEqual(r["candidate_triangle_nodes"][0]["candidate_nodes"],[0,1])

    def test_degenerate_triangle_skipped_without_false_assignment(self):
        r=audit.analyze_spatial_candidates(
            [(PLANE,SPHERE)],labelled(((0.,0.,0.),(1.,0.,0.),(2.,0.,0.))))
        self.assertEqual(r["counts"]["degenerate_triangles"],1)
        self.assertNotIn("same_infinite_plane",r["counts"])

    def test_invalid_source_fields_rejected(self):
        for nodes, triangles in [
            ([],labelled()),
            ([((0.,0.,0.,0.),SPHERE)],labelled()),
            ([(PLANE,(0.,0.,0.,-5.))],labelled()),
            ([(PLANE,SPHERE)],labelled(((0.,0.,0.),(1.,0.,0.),(float("nan"),1.,0.)))),
        ]:
            with self.subTest(nodes=nodes,triangles=triangles),self.assertRaises(ValueError):
                audit.analyze_spatial_candidates(nodes,triangles)

    def test_render_block_must_have_exact_length_prefix(self):
        block={
            "offset":100,"end":300,"id":200,
            "vertices":[(xyz,(0.,0.,1.),(0.,0.)) for xyz in TRIANGLE],
            "sections":[{"indices":[0,1,2]}],
        }
        rows=list(audit._triangles_from_render_blocks([block]))
        self.assertEqual(rows,[([0,0,0],TRIANGLE)])
        with self.assertRaisesRegex(ValueError,"length prefix"):
            list(audit._triangles_from_render_blocks([{**block,"id":19}]))
        with self.assertRaisesRegex(ValueError,"index outside"):
            list(audit._triangles_from_render_blocks([{**block,
                "sections":[{"indices":[0,1,9]}]}]))

    def test_synthetic_gmp_integration_and_no_file_mutation(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name)
            source=base/"Maps"/"synthetic.gmp"
            source.parent.mkdir()
            source.write_bytes(b"fixture only, never mutated")
            payload=bytearray(51+112)
            struct.pack_into("<4f",payload,51,*PLANE)
            struct.pack_into("<4f",payload,51+112-53,*SPHERE)
            frame={"candidate_node_count":1,
                   "node_records":[{"start":51,"length":112}]}
            class FakePackage:
                def __init__(self,path):
                    self.data=Path(path).read_bytes()
                    self.version=95
                    self.licensee=68
                    self.exports=[{"index":1,"name":"ModelWorld"}]
                def payload(self,exp):
                    return bytes(payload)
                def class_name(self,exp):
                    return "Model"
            block={
                "offset":100,"end":300,"id":200,
                "vertices":[(xyz,(0.,0.,1.),(0.,0.)) for xyz in TRIANGLE],
                "sections":[{"indices":[0,1,2]}],
            }
            with patch.object(audit.boundaries.world,"Package",side_effect=FakePackage), \
                 patch.object(audit.boundaries.world,"_parse_world_model",
                              return_value={"world_model_export_ref":1}), \
                 patch.object(audit.boundaries,"parse_world_model",return_value=frame), \
                 patch.object(audit,"find_bsp",return_value=[block]):
                report=audit.audit_maps([source],include_matches=True)
            self.assertEqual(report["schema"],audit.SCHEMA)
            self.assertEqual(report["summary"]["unique_candidate"],1)
            self.assertTrue(report["maps"][0]["all_render_block_length_prefixes_verified"])
            self.assertEqual(report["maps"][0]["candidate_triangle_nodes"][0]["candidate_nodes"],[0])
            self.assertFalse(report["native_geometry_writer_implemented"])
            self.assertFalse(report["engine_node_triangle_index_decoded"])
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                audit.audit_maps([source,source])
            with self.assertRaisesRegex(ValueError,"outside original"):
                audit.boundaries.world.write_report(
                    report,source.parent/"report.json",[source])
            dest=base/"Reports"/"candidates.json"
            audit.boundaries.world.write_report(report,dest,[source])
            self.assertEqual(json.loads(dest.read_text())["schema"],audit.SCHEMA)
            with self.assertRaises(FileExistsError):
                audit.boundaries.world.write_report(report,dest,[source])
            self.assertEqual(source.read_bytes(),b"fixture only, never mutated")


if __name__=="__main__":
    unittest.main()
