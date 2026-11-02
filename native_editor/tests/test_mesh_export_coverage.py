"""Source-only tests: classify why original static mesh actors lack GLB geometry."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2coverage import summarize_mesh_export_coverage


def actor(i, name, mesh=None, kind="StaticMeshActor"):
    return {"name": name, "export": i, "class": kind,
            "mesh": {"name":mesh} if mesh is not None else None}


class MeshExportCoverageTests(unittest.TestCase):
    def test_disambiguates_missing_refs_from_rendered_and_gameplay(self):
        actors = [
            actor(1, "Visible", "Trim"),
            actor(2, "MissingResource", "MissingModel"),
            actor(3, "MissingRenderFaces", "EmptyModel"),
            actor(4, "UnresolvedReference"),
            actor(5, "GameLogic", None, "Trigger"),
            actor(6, "Unaccounted", "Unexplained"),
        ]
        report = summarize_mesh_export_coverage(
            actors, [actors[0]],
            [{"actor": "MissingResource", "export":2, "mesh":"MissingModel"}],
            [{"actor": "MissingRenderFaces", "export":3, "mesh":"EmptyModel"}],
        )
        self.assertEqual(report["source_scene_actor_count"], 6)
        self.assertEqual(report["source_staticmesh_actor_count"], 5)
        self.assertEqual(report["source_mesh_linked_actor_count"], 4)
        self.assertEqual(report["rendered_mesh_actor_count"], 1)
        self.assertEqual(report["missing_ibd_resource_count"], 1)
        self.assertEqual(report["empty_render_sections_count"], 1)
        self.assertEqual(report["unresolved_gmp_staticmesh_reference_count"], 1)
        self.assertEqual(report["unaccounted_nonrendered_mesh_actor_count"], 1)
        self.assertEqual(report["unresolved_gmp_staticmesh_references"][0]["export"],4)
        self.assertEqual(report["unaccounted_nonrendered_mesh_actors"][0]["actor"],"Unaccounted")
        self.assertFalse(any(a["actor"] == "GameLogic" for a in
                             report["unresolved_gmp_staticmesh_references"]))

    def test_string_mesh_from_native_cached_actors_json(self):
        actors = [{"name":"StaticMeshActor__119", "export":554,
                   "class":"StaticMeshActor", "mesh":"Trim"}]
        report = summarize_mesh_export_coverage(actors, actors, [], [])
        self.assertEqual(report["source_mesh_linked_actor_count"],1)
        self.assertEqual(report["rendered_mesh_actor_count"],1)
        self.assertEqual(report["unaccounted_nonrendered_mesh_actor_count"],0)

    def test_all_inputs_empty(self):
        report = summarize_mesh_export_coverage([],[],[],[])
        self.assertEqual(report["source_scene_actor_count"],0)
        self.assertEqual(report["missing_ibd_resource_count"],0)


if __name__ == "__main__":
    unittest.main()
