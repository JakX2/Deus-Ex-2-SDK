"""Fixture-only WTO Terminal neighborhood audit regression checks."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2_missing_geometry_neighbors import neighbors


def actor(name, export, x, mesh, kind="StaticMeshActor"):
    return {"name": name, "export": export, "class": kind,
            "location": [x, -272, 396], "rotation": [0, 16384, 0], "mesh": mesh}


class MissingGeometryNeighborsTests(unittest.TestCase):
    def setUp(self):
        self.actors = {"meta":{"source_map":"M1_Seattle_Hub_WTOterminal.gmp"},
                       "actors":[
            actor("StaticMeshActor__119", 554, 0, "1Hub_wto_term2-trim2-4ft"),
            actor("MissingTrim", 559, 8, "MissingPiece"),
            actor("VisibleWall", 560, 50, "Wall"),
            actor("ZeroFaces", 561, 60, "Empty"),
            actor("UnresolvedMesh", 562, 70, None),
            actor("FarWall", 563, 12000, "Far"),
            actor("GameplayActor", 564, 2, None, "Trigger"),
        ]}
        self.report = {"placement_actor_details":[{"export":554}, {"export":560}],
                       "missing_mesh_actors":[{"export":559,"mesh":"MissingPiece"}],
                       "mesh_export_coverage":{"empty_render_sections":[{"export":561,"mesh":"Empty"}]}}

    def test_adjacent_actors_have_distinct_render_statuses(self):
        result = neighbors(self.actors, self.report, "StaticMeshActor__119", 3)
        self.assertEqual(result["target_export"], 554)
        statuses = {x["actor"]: x["status"] for x in result["neighbors"]}
        self.assertEqual(statuses, {
            "MissingTrim":"missing_ibd_resource", "VisibleWall":"rendered",
            "ZeroFaces":"empty_render_sections",
            "UnresolvedMesh":"unresolved_gmp_mesh_reference"
        })
        self.assertFalse(result["game_verified"])
        self.assertFalse(any(x["actor"] == "GameplayActor" for x in result["neighbors"]))
        self.assertFalse(any(x["actor"] == "FarWall" for x in result["neighbors"]))

    def test_missing_placement_audit_must_not_claim_mesh_is_missing(self):
        source = {"actors":[actor("StaticMeshActor__119",554,0,"Trim"),
                            actor("Neighbor",555,1,"Wall")]}
        report = neighbors(source, {}, "StaticMeshActor__119")
        self.assertFalse(report["placement_records_available"])
        self.assertEqual(report["neighbors"][0]["status"], "unverified_no_render_record")

    def test_invalid_radius_or_unknown_actor_rejected(self):
        with self.assertRaises(ValueError):
            neighbors(self.actors, self.report, "no such actor")
        with self.assertRaises(ValueError):
            neighbors(self.actors, self.report, "StaticMeshActor__119", -2)


if __name__ == "__main__":
    unittest.main()
