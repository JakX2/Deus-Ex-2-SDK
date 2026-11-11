"""DX2Ed v0.75: synthetic World BSP field2 grouped-plane hypothesis tests."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import struct
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

from dx2sdk.bsp_surface_plane_coherence import (
    analyze_surface_plane_coherence, inspect_original_surface_plane_coherence,
)
from test_dx2_world_bsp_zone_relations import synthetic_world


def row(field2, plane=(1., 0., 0., 8.), *, coplanar=-1, offset=10):
    return {"field2": field2, "plane": plane,
            "field2_offset_in_model": offset, "coplanar": coplanar}


class OriginalBSPSurfacePlaneCoherenceTests(unittest.TestCase):
    def test_reused_field2_values_share_one_original_infinite_plane(self):
        nodes = [row(4, offset=5), row(4, offset=120), row(5, offset=240),
                 row(4, offset=360)]
        original = deepcopy(nodes)
        out = analyze_surface_plane_coherence(nodes)
        self.assertEqual(out["source_node_count"], 4)
        self.assertEqual(out["source_reused_field2_groups"], 1)
        self.assertEqual(out["source_singleton_field2_groups"], 1)
        self.assertEqual(out["source_nodes_in_reused_field2_groups"], 3)
        self.assertEqual(out["reused_field2_groups_plane_coherent_with_first_node"], 1)
        self.assertEqual(out["reused_field2_groups_containing_different_planes"], 0)
        self.assertEqual(out["within_reused_field2_anchor_comparisons"]["same_orientation"], 2)
        self.assertFalse(out["source_field2_is_authenticated_surface_index"])
        self.assertFalse(out["native_BSP_or_collision_writer_enabled"])
        self.assertFalse(out["retail_runtime_verified"])
        self.assertEqual(nodes, original)

    def test_opposite_oriented_planes_are_same_infinite_plane(self):
        nodes = [row(2, (0., 0., 1., 4.)),
                 row(2, (0., 0., -1., -4.)),
                 row(2, (0., 0., 1., 4.1))]
        out = analyze_surface_plane_coherence(nodes)
        relations = out["within_reused_field2_anchor_comparisons"]
        self.assertEqual(relations["same_orientation"], 1)
        self.assertEqual(relations["opposite_orientation"], 1)
        self.assertEqual(relations["different_plane"], 0)

    def test_same_numeric_field2_with_different_plane_flags_falsification(self):
        nodes = [row(1), row(1, (0., 1., 0., 8.), offset=21),
                 row(1, (1., 0., 0., 9.), offset=31),
                 row(2)]
        out = analyze_surface_plane_coherence(nodes)
        self.assertEqual(out["reused_field2_groups_containing_different_planes"], 1)
        self.assertEqual(out["within_reused_field2_anchor_comparisons"]["different_plane"], 2)
        self.assertEqual(out["example_reused_field2_plane_disagreements"][0], {
            "raw_field2_value": 1, "anchor_node": 0, "conflicting_node": 1,
            "anchor_field2_offset_in_model": 10,
            "conflicting_field2_offset_in_model": 21,
            "plane_relation": "different_plane",
        })

    def test_coplanar_field5_links_crossed_with_field2_identity(self):
        # Field 5 is independently rooted-BSP source-observed. Same plane
        # can still have a different field 2. Do not collapse the two IDs.
        nodes = [
            row(0, (0., 0., 1., 0.), coplanar=1),
            row(1, (0., 0., 1., 0.), coplanar=2),
            row(1, (0., 1., 0., 0.), coplanar=3),
            row(1, (0., 1., 0., 0.)),
        ]
        out = analyze_surface_plane_coherence(nodes)
        links = out["candidate_coplanar_field5_link_evidence"]
        self.assertEqual(links["total"], 3)
        self.assertEqual(links["same_field2"], 2)
        self.assertEqual(links["different_field2_same_plane"], 1)
        self.assertEqual(links["same_field2_different_plane"], 1)
        self.assertEqual(links["different_infinite_plane"], 1)

    def test_source_minus_one_field2_sentinel_excluded_from_grouping(self):
        out = analyze_surface_plane_coherence([
            row(-1), row(-1, (0., 1., 0., 0.)), row(3)])
        self.assertEqual(out["source_field2_minus_one_sentinels"], 2)
        self.assertEqual(out["source_distinct_nonnegative_field2_values"], 1)
        self.assertEqual(out["source_reused_field2_groups"], 0)

    def test_bad_original_compact_record_and_plane_refuse_without_coercion(self):
        invalid = [[], [row(True)], [row(-2)], [row(0, coplanar=0)],
                   [row(0, coplanar=99)], [row(0, offset=True)],
                   [row(0, (0., 0., 2., 0.))], [row(0, (float("nan"), 0., 1., 2.))],
                   [row(0, (0., 0., 1.))]]
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError):
                analyze_surface_plane_coherence(case)

    def test_large_reused_field2_group_is_linear_not_pairwise(self):
        nodes = [row(7, offset=i) for i in range(4000)]
        out = analyze_surface_plane_coherence(nodes)
        self.assertEqual(out["source_nodes_in_reused_field2_groups"], 4000)
        self.assertEqual(out["within_reused_field2_anchor_comparisons"]["same_orientation"],
                         3999)
        self.assertEqual(out["reused_field2_groups_containing_different_planes"], 0)

    def test_original_gmp_model_export_offsets_are_sha_checked(self):
        payload, frame = synthetic_world()
        raw = b"\x5a"*64 + payload + b"\xfe"*13
        model_export = {"offset": 64, "size": len(payload)}
        class Package:
            data = raw
            exports = [model_export]
            def class_name(self, exp):
                return "Model"
            def payload(self, exp):
                return self.data[exp["offset"]:exp["offset"]+exp["size"]]
        class World:
            source = Path("Synthetic.gmp")
            source_sha256 = hashlib.sha256(raw).hexdigest()
            _package = Package()
            checks = 0
            def _check_original_unchanged(self):
                self.checks += 1
        world = World()
        validated = {
            "world_model_export": 1, "world_model_sha256": hashlib.sha256(payload).hexdigest(),
            "node_count": frame["candidate_node_count"],
            "nodes": [{"plane": struct.unpack_from("<4f", payload, node["start"])}
                      for node in frame["node_records"]],
        }
        with patch("dx2sdk.bsp_surface_plane_coherence._load_model",
                   return_value=validated):
            out = inspect_original_surface_plane_coherence(world)
        self.assertEqual(out["source_node_count"], 3)
        self.assertEqual(out["source_sha256"], world.source_sha256)
        self.assertEqual(out["original_world_model_offset_in_gmp"], 64)
        self.assertTrue(out["source_reused_field2_groups"])
        self.assertFalse(out["original_source_modified"])
        self.assertEqual(world.checks, 2)
        self.assertEqual(raw, Package.data)
        world.source_sha256 = "f"*64
        with patch("dx2sdk.bsp_surface_plane_coherence._load_model",
                   return_value=validated), self.assertRaisesRegex(ValueError, "SHA"):
            inspect_original_surface_plane_coherence(world)

    def test_cli_flag_routes_to_original_plane_coherence_not_level_correlator(self):
        import inspect_bsp_surface_provenance_hypotheses as cli
        class FakeWorld:
            source_sha256 = "a"*64
            source = Path("Synthetic.gmp")
            def inspect_bsp_surface_plane_coherence(self):
                return {"status": "read-only-original-BSP-field2-plane-coherence-hypothesis",
                        "source_sha256": self.source_sha256,
                        "source_reused_field2_groups": 2,
                        "source_field2_is_authenticated_surface_index": False,
                        "retail_runtime_verified": False}
            def inspect_bsp_surface_provenance_hypotheses(self):
                raise AssertionError("CLI chose wrong hypothesis mode")
        output = StringIO()
        with patch.object(cli.DX2Map, "open", return_value=FakeWorld()), redirect_stdout(output):
            status = cli.main(["Synthetic.gmp", "--source-sha256", "a"*64,
                               "--field2-plane-coherence"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["source_reused_field2_groups"], 2)
        output = StringIO()
        with patch.object(cli.DX2Map, "open", return_value=FakeWorld()), redirect_stderr(output):
            status = cli.main(["Synthetic.gmp", "--source-sha256", "b"*64,
                               "--field2-plane-coherence"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "refused")


if __name__ == "__main__":
    unittest.main()
