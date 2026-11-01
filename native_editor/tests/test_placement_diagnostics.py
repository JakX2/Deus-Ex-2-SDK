"""Fixture-only tests for reading mesh-local pivot evidence from DX2 source data."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))
sys.path.insert(0, str(ROOT / "native_editor" / "godot_editor" / "backend"))

from dx2placement import analyze_mesh_placement, summarize_placement
from dx2_native_backend import enrich_placement_report


def mesh(bounds, positions):
    return SimpleNamespace(name="FictionalTable", bounds=bounds, positions=positions)


def actor(bounds=None, export=42):
    return {"name":"StaticMeshActor__42", "export":export, "x":100,"y":20,"z":7,
            "rotation":[0,0,0], "mesh":{"name":"FictionalTable","bounds":bounds}}


class PlacementDiagnosticsTests(unittest.TestCase):
    def test_consistent_gmp_ibd_vertices_do_not_claim_placement_is_correct(self):
        bounds = [-1,-2,-3,1,2,3]
        resource = mesh(bounds, [(-1,-2,-3),(1,2,3)])
        diagnostic = analyze_mesh_placement(actor([bounds[:3],bounds[3:]]),
                                            resource,"Mission.ibd")
        self.assertFalse(diagnostic["needs_review"])
        self.assertEqual(diagnostic["mesh_local_center_ue"], [0,0,0])
        self.assertEqual(diagnostic["mesh_pivot_to_center_m"], 0.0)
        self.assertEqual(diagnostic["source_position_ue"],[100,20,7])
        self.assertIn("gmp_vertex_bounds_max_delta_ue",diagnostic)

    def test_far_mesh_local_pivot_is_reported_as_warning_not_autocorrected(self):
        bounds = [200,0,-5,220,5,5]
        resource=mesh(bounds, [(200,0,-5),(220,5,5)])
        diag=analyze_mesh_placement(actor([bounds[:3],bounds[3:]]),resource,"Mission.ibd")
        self.assertIn("large_mesh_local_pivot_offset",diag["warnings"])
        self.assertGreater(diag["mesh_pivot_to_center_m"],3)
        self.assertNotIn("transform_override",diag)
        report=summarize_placement([diag])
        self.assertFalse(report["game_verified"])
        self.assertEqual(report["review_actor_count"],1)

    def test_gmp_vs_ibd_bounds_disagreement_is_source_evidence(self):
        resource=mesh([0,0,0,1,1,1], [(0,0,0),(1,1,1)])
        diag=analyze_mesh_placement(actor([[50,50,50],[55,55,55]]),resource,"Mission.ibd")
        self.assertIn("gmp_vertex_bounds_disagree",diag["warnings"])
        self.assertNotIn("ibd_vertex_bounds_disagree",diag["warnings"])

    def test_invalid_ibd_bounds_are_not_used_to_infer_placement(self):
        resource=mesh([float("inf"),0,0,1,1,1], [(0,0,0),(1,1,1)])
        diag=analyze_mesh_placement(actor(None),resource,"Mission.ibd")
        self.assertIn("ibd_bounds_unavailable",diag["warnings"])
        self.assertIn("gmp_bounds_unavailable",diag["warnings"])

    def test_cache_placement_upgrade_attaches_by_export_not_by_name(self):
        rec=[{"name":"StaticMeshActor__42","class":"StaticMeshActor","mesh":"FictionalTable",
              "mesh_bounds":[[0,0,0],[1,1,1]],"rotation":[0,0,0],
              "location":[11,22,33],"export":42}]
        report={}
        resource=mesh([0,0,0,1,1,1], [(0,0,0),(1,1,1)])
        source=(SimpleNamespace(name="Mission.ibd"),SimpleNamespace(index=3))
        indexes={4:{"fictionaltable":source},8:{},10:{}}
        with patch("dx2_native_backend.load_resource_index",return_value=([],indexes,{})), \
             patch("dx2_native_backend.parse_mesh",return_value=resource):
            changed=enrich_placement_report(rec,[Path("Mission.ibd")],report)
        self.assertTrue(changed)
        self.assertEqual(rec[0]["placement_diagnostic"]["export"],42)
        self.assertEqual(report["placement_audit"]["observed_actor_count"],1)
        # The second call should be idempotent, without reparsing IBD resources.
        self.assertFalse(enrich_placement_report(rec,[],report))


if __name__=="__main__":
    unittest.main()
