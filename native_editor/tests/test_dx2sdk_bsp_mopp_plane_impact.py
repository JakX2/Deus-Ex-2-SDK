"""DX2Ed v0.72: source-verified BSP/render candidate → MOPP ID join.

Every input is a synthetic Level/MOPP fixture, not retail game data.
"""
import copy
import hashlib
import struct
import unittest
from unittest.mock import patch
from pathlib import Path

from dx2sdk.bsp_mopp_plane_impact import (
    _source_triangle_rows, compare_render_collision_candidates,
    compare_original_plane_mopp_impact,
)
from dx2sdk.bsp_render_plane_impact import compare_plane_render_triangles
from test_dx2_level_mopp_triangle_provenance import fixture


def triangles(blocks):
    rows = []
    for bi, block in enumerate(blocks):
        for si, section in enumerate(block["sections"]):
            for ti in range(0, len(section["indices"]), 3):
                corners = tuple(block["vertices"][i][0] for i in section["indices"][ti:ti+3])
                rows.append(([bi, si, ti//3], corners))
    return rows


PLANE = (0., 0., 1., 0.)
SPHERE = (0., 0., 0., 100.)
REPLACEMENT = (0., 0., 1., 2.)


class OriginalMoppCrosswalkTests(unittest.TestCase):
    def test_two_render_sections_resolve_to_original_mopp_terminal_ids(self):
        level, blocks, _ = fixture()
        original = copy.deepcopy((level, blocks))
        render = triangles(blocks)
        result = compare_render_collision_candidates(
            [(PLANE, SPHERE)], render, level, blocks, node=0, replacement=REPLACEMENT)
        self.assertEqual(result["lost_candidate_render_triangles"], 2)
        self.assertEqual(result["gained_candidate_render_triangles"], 0)
        self.assertEqual(result["lost_candidate_original_mopp_leaf_count"], 2)
        self.assertEqual(result["source_mopp_terminal_leaf_count"], 2)
        self.assertEqual([x["flattened_triangle_id"] for x in
                          result["lost_candidate_mopp_id_examples"]], [0, 1])
        self.assertEqual([x["render_locator"] for x in
                          result["lost_candidate_mopp_id_examples"]],
                         [[0, 0, 0], [0, 1, 0]])
        self.assertEqual([x["source_provenance_section_field_b"] for x in
                          result["lost_candidate_mopp_id_examples"]], [0, 1])
        self.assertEqual([x["source_provenance_block_field_a"] for x in
                          result["lost_candidate_mopp_id_examples"]], [0, 0])
        self.assertFalse(result["native_collision_writer_enabled"])
        self.assertFalse(result["native_bsp_writer_enabled"])
        self.assertFalse(result["candidate_matching_is_engine_ownership"])
        self.assertFalse(result["retail_runtime_verified"])
        self.assertEqual((level, blocks), original)
        self.assertEqual(result, compare_render_collision_candidates(
            [(PLANE, SPHERE)], render, level, blocks, node=0, replacement=REPLACEMENT))

    def test_source_skipped_block_ids_are_preserved_not_renumbered(self):
        level, blocks, _ = fixture(separate_blocks=True)
        result = compare_render_collision_candidates(
            [(PLANE, SPHERE)], triangles(blocks), level, blocks,
            node=0, replacement=REPLACEMENT)
        self.assertEqual([x["render_locator"] for x in
                          result["lost_candidate_mopp_id_examples"]],
                         [[0, 0, 0], [1, 0, 0]])
        self.assertEqual([x["source_provenance_block_field_a"] for x in
                          result["lost_candidate_mopp_id_examples"]], [0, 2])
        self.assertEqual([x["flattened_triangle_id"] for x in
                          result["lost_candidate_mopp_id_examples"]], [0, 1])

    def test_degenerate_nonleaf_stays_out_of_geometric_candidate_set(self):
        level, blocks, _ = fixture(
            code=b"\x28\x00\xff\x31", degenerate=True)
        result = compare_render_collision_candidates(
            [(PLANE, SPHERE)], triangles(blocks), level, blocks,
            node=0, replacement=REPLACEMENT)
        self.assertEqual(result["source_render_triangle_count"], 2)
        self.assertEqual(result["source_non_mopp_degenerate_triangle_count"], 1)
        self.assertEqual(result["lost_candidate_original_mopp_leaf_count"], 1)
        self.assertEqual(result["lost_candidate_nonleaf_count"], 0)
        self.assertEqual(result["lost_candidate_mopp_id_examples"][0]["flattened_triangle_id"], 1)

    def test_refuse_corrupt_level_or_wrong_render_order(self):
        level, blocks, table_start = fixture()
        original = triangles(blocks)
        for bad in (list(reversed(original)), original[:1],
                    [original[0], original[0]]):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "inventory|order"):
                compare_render_collision_candidates(
                    [(PLANE, SPHERE)], bad, level, blocks,
                    node=0, replacement=REPLACEMENT)
        bad = bytearray(level)
        struct.pack_into("<I", bad, table_start+24+4, 1234)
        with self.assertRaises(ValueError):
            compare_render_collision_candidates(
                [(PLANE, SPHERE)], original, bytes(bad), blocks,
                node=0, replacement=REPLACEMENT)
        with self.assertRaises(ValueError):
            compare_render_collision_candidates(
                [(PLANE, SPHERE)], original, level[:-1] + b"\xff", blocks,
                node=0, replacement=REPLACEMENT)

    def test_refuse_noop_invalid_sample_and_invalid_normal(self):
        level, blocks, _ = fixture()
        for kw in (
            {"node": 0, "replacement": PLANE},
            {"node": 0, "replacement": (0, 0, 2, 2)},
            {"node": True, "replacement": REPLACEMENT},
            {"node": 0, "replacement": REPLACEMENT, "max_examples": 0},
            {"node": 0, "replacement": REPLACEMENT, "max_examples": 33},
        ):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                compare_render_collision_candidates(
                    [(PLANE, SPHERE)], triangles(blocks), level, blocks, **kw)

    def test_high_level_original_source_sha_and_model_crosscheck(self):
        level, blocks, _ = fixture()
        model = bytearray(100)
        struct.pack_into("<4f", model, 0, *PLANE)
        struct.pack_into("<4f", model, 47, *SPHERE)
        model = bytes(model)
        class Package:
            exports = [
                {"size": len(level), "kind": "Level"},
                {"size": len(model), "kind": "Model"},
            ]
            def class_name(self, export):
                return export["kind"]
            def payload(self, export):
                return level if export["kind"] == "Level" else model
        class World:
            _package = Package()
            source = Path("Synthetic.gmp")
            source_sha256 = "a"*64
            checked = 0
            def _check_original_unchanged(self):
                self.checked += 1
        world = World()
        base = compare_plane_render_triangles(
            [(PLANE, SPHERE)], triangles(blocks), node=0, replacement=REPLACEMENT)
        render = {
            **base, "world_model_export": 2,
            "world_model_sha256": hashlib.sha256(model).hexdigest(),
            "validated_render_blocks": len(blocks),
            "source_render_triangles": len(triangles(blocks)),
            "source_sha256": world.source_sha256,
        }
        frame = {"candidate_node_count": 1,
                 "node_records": [{"start": 0, "length": 100}]}
        with patch("dx2sdk.bsp_mopp_plane_impact.compare_original_plane_render_impact",
                   return_value=render), patch(
                "dx2sdk.bsp_mopp_plane_impact.parse_world_model",
                return_value=frame), patch(
                "dx2sdk.bsp_mopp_plane_impact.find_bsp",
                return_value=blocks), patch(
                "dx2sdk.bsp_mopp_plane_impact._triangles_from_render_blocks",
                return_value=iter(triangles(blocks))):
            result = compare_original_plane_mopp_impact(
                world, node=0, replacement=REPLACEMENT)
        self.assertEqual(result["source_sha256"], world.source_sha256)
        self.assertEqual(result["source_level_export"], 1)
        self.assertEqual(result["source_mopp_terminal_leaf_count"], 2)
        self.assertEqual(world.checked, 2)


if __name__ == "__main__":
    unittest.main()
