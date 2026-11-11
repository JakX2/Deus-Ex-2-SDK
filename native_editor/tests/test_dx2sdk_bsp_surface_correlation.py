"""Asset-free v0.74 DX2 native Model field2 vs Level/MOPP provenance tests."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from unittest.mock import patch
import unittest

from dx2sdk.bsp_surface_correlation import (
    correlate_surface_candidates, inspect_original_bsp_surface_correlation,
)
from dx2sdk.bsp_mopp_plane_impact import _source_triangle_rows
from test_dx2_level_mopp_triangle_provenance import fixture
from test_dx2_world_bsp_zone_relations import synthetic_world


def render_triangles(blocks):
    out = []
    for bi, block in enumerate(blocks):
        for si, section in enumerate(block["sections"]):
            for ti in range(0, len(section["indices"]), 3):
                corners = tuple(block["vertices"][idx][0]
                                for idx in section["indices"][ti:ti+3])
                out.append(([bi, si, ti//3], corners))
    return out


def nodes(*surfaces, sphere=(0., 0., 0., 100.)):
    return [{
        "field2": field2, "field2_offset_in_model": i*109 + 51,
        "plane": (0., 0., 1., 0.), "sphere": sphere,
    } for i, field2 in enumerate(surfaces)]


class BSPModelSurfaceHypothesisTests(unittest.TestCase):
    def test_original_two_render_sections_distinguishes_numeric_domains(self):
        level, blocks, _ = fixture()
        rows, _ = _source_triangle_rows(level, blocks)
        geometry = render_triangles(blocks)
        originals = deepcopy((nodes(0), geometry, rows))
        result = correlate_surface_candidates(nodes(0), geometry, rows)
        self.assertEqual(result["original_flat_triangle_count"], 2)
        self.assertEqual(result["unique_geometric_node_candidates"], 2)
        self.assertEqual(result["original_mopp_leaves_among_unique_candidates"], 2)
        equal = result["numeric_equality_only"]
        self.assertEqual(equal["field2_equals_level_provenance_A"], 2)
        self.assertEqual(equal["field2_equals_render_block_ordinal"], 2)
        self.assertEqual(equal["field2_equals_render_section_ordinal"], 1)
        self.assertEqual(equal["field2_equals_flat_triangle_ordinal"], 1)
        self.assertEqual(result["candidate_field2_groups_multiple_render_sections"], 1)
        self.assertFalse(result["field2_is_engine_authenticated_surface_index"])
        self.assertFalse(result["native_BSP_or_collision_writer_enabled"])
        self.assertFalse(result["retail_runtime_verified"])
        self.assertEqual(originals, (nodes(0), geometry, rows))

    def test_skipped_source_A_ids_not_confused_with_block_ordinals(self):
        level, blocks, _ = fixture(separate_blocks=True)
        rows, _ = _source_triangle_rows(level, blocks)
        result = correlate_surface_candidates(nodes(0), render_triangles(blocks), rows)
        equal = result["numeric_equality_only"]
        self.assertEqual(equal["field2_equals_level_provenance_A"], 1)
        self.assertEqual(equal["field2_equals_render_block_ordinal"], 1)
        self.assertEqual(equal["field2_equals_render_section_ordinal"], 2)
        self.assertEqual(result["candidate_field2_groups_multiple_provenance_A"], 1)
        self.assertEqual(result["candidate_field2_groups_multiple_render_blocks"], 1)

    def test_coplanar_ambiguous_node_candidates_are_not_promoted_to_ownership(self):
        level, blocks, _ = fixture()
        rows, _ = _source_triangle_rows(level, blocks)
        result = correlate_surface_candidates(nodes(0, 1), render_triangles(blocks), rows)
        self.assertEqual(result["ambiguous_geometric_node_candidates"], 2)
        self.assertEqual(result["unique_geometric_node_candidates"], 0)
        self.assertEqual(result["candidate_field2_groups_with_matched_triangles"], 0)
        self.assertTrue(all(value == 0 for value in result["numeric_equality_only"].values()))

    def test_outside_source_node_sphere_does_not_create_fake_surface_match(self):
        level, blocks, _ = fixture()
        rows, _ = _source_triangle_rows(level, blocks)
        result = correlate_surface_candidates(
            nodes(0, sphere=(0., 0., 0., .1)), render_triangles(blocks), rows)
        self.assertEqual(result["unique_geometric_node_candidates"], 0)
        self.assertEqual(result["unmatched_or_degenerate_render_triangles"], 2)

    def test_degenerate_original_triangle_remains_explicit_nonleaf(self):
        level, blocks, _ = fixture(code=b"\x28\x00\xff\x31", degenerate=True)
        rows, _ = _source_triangle_rows(level, blocks)
        result = correlate_surface_candidates(nodes(0), render_triangles(blocks), rows)
        self.assertEqual(result["unique_geometric_node_candidates"], 1)
        self.assertEqual(result["unmatched_or_degenerate_render_triangles"], 1)
        self.assertEqual(result["original_mopp_leaves_among_unique_candidates"], 1)

    def test_corrupt_render_order_or_original_provenance_fails_closed(self):
        level, blocks, _ = fixture()
        rows, _ = _source_triangle_rows(level, blocks)
        geom = render_triangles(blocks)
        badcases = [
            (list(reversed(geom)), rows),
            ([geom[0], geom[0]], rows),
            (geom[:1], rows),
            (geom, [rows[0], rows[0]]),
        ]
        for triangles, identity in badcases:
            with self.subTest(case=identity), self.assertRaises(ValueError):
                correlate_surface_candidates(nodes(0), triangles, identity)
        for bad in ([], [{"field2": True, "field2_offset_in_model": 0,
                         "plane": (0,0,1,0), "sphere": (0,0,0,10)}],
                    [{"field2": -2, "field2_offset_in_model": 0,
                      "plane": (0,0,1,0), "sphere": (0,0,0,10)}]):
            with self.subTest(node=bad), self.assertRaises(ValueError):
                correlate_surface_candidates(bad, geom, rows)

    def test_source_sha_pinned_cli_can_report_without_retail_writes(self):
        import json
        from contextlib import redirect_stdout, redirect_stderr
        from io import StringIO
        import inspect_bsp_surface_provenance_hypotheses as cli

        class FakeWorld:
            source_sha256 = "a"*64
            source = Path("/private/Maps/Synthetic.gmp")
            def inspect_bsp_surface_provenance_hypotheses(self):
                return {
                    "status": "read-only-cross-domain-field2-numeric-hypotheses",
                    "source_sha256": self.source_sha256,
                    "unique_geometric_node_candidates": 2,
                    "field2_is_engine_authenticated_surface_index": False,
                    "retail_runtime_verified": False,
                }
        stdout = StringIO()
        with patch.object(cli.DX2Map, "open", return_value=FakeWorld()), redirect_stdout(stdout):
            self.assertEqual(cli.main(["Synthetic.gmp", "--source-sha256", "a"*64]), 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["unique_geometric_node_candidates"], 2)
        self.assertFalse(report["field2_is_engine_authenticated_surface_index"])
        stderr = StringIO()
        with patch.object(cli.DX2Map, "open", return_value=FakeWorld()), redirect_stderr(stderr):
            self.assertEqual(cli.main(["Synthetic.gmp", "--source-sha256", "b"*64]), 2)
        self.assertEqual(json.loads(stderr.getvalue())["status"], "refused")

    def test_original_export_offsets_and_compact_field2_source_position(self):
        model, frame = synthetic_world()
        level, blocks, _ = fixture()
        prefix = b"\x7f"*64
        all_bytes = prefix + model + level
        model_exp = {"offset": 64, "size": len(model), "kind": "Model"}
        level_exp = {"offset": 64+len(model), "size": len(level), "kind": "Level"}
        class Package:
            data = all_bytes
            exports = [model_exp, level_exp]
            def class_name(self, exp):
                return exp["kind"]
            def payload(self, exp):
                return self.data[exp["offset"]:exp["offset"]+exp["size"]]
        class World:
            _package = Package()
            source = Path("Synthetic.gmp")
            source_sha256 = hashlib.sha256(all_bytes).hexdigest()
            checks = 0
            def _check_original_unchanged(self):
                self.checks += 1
        world = World()
        old = [{
            "plane": tuple(__import__("struct").unpack_from("<4f", model, row["start"]))
        } for row in frame["node_records"]]
        validated = {
            "world_model_export": 1, "world_model_sha256": hashlib.sha256(model).hexdigest(),
            "node_count": len(old), "nodes": old,
        }
        with patch("dx2sdk.bsp_surface_correlation._load_model", return_value=validated), patch(
                "dx2sdk.bsp_surface_correlation.find_bsp", return_value=blocks), patch(
                "dx2sdk.bsp_surface_correlation._triangles_from_render_blocks",
                return_value=iter(render_triangles(blocks))):
            report = inspect_original_bsp_surface_correlation(world)
        self.assertEqual(world.checks, 2)
        self.assertEqual(report["source_model_absolute_offset"], 64)
        self.assertEqual(report["source_level_export"], 2)
        self.assertTrue(report["model_compact_field2_byte_positions_source_checked"])
        self.assertFalse(report["original_gmp_modified"])
        self.assertEqual(report["source_sha256"], world.source_sha256)
        self.assertEqual(Package.data, all_bytes)


if __name__ == "__main__":
    unittest.main()
