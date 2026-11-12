"""Source-only v0.77 original DX2 compiled World Model byte-span ledger tests."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from dx2sdk.bsp_model_spans import (
    build_original_model_span_ledger, inspect_original_model_span_ledger,
    OBSERVED, HYPOTHESIS, OPAQUE,
)
from test_dx2_world_bsp_zone_relations import synthetic_world


class WorldBSPByteSpanLedgerTests(unittest.TestCase):
    def test_complete_source_model_byte_coverage_is_nonoverlapping(self):
        source, frame = synthetic_world()
        original = bytes(source)
        report = build_original_model_span_ledger(source, node_indices=[0, 2])
        self.assertEqual(source, original)
        self.assertEqual(report["original_model_sha256"],
                         hashlib.sha256(source).hexdigest())
        self.assertEqual(report["original_model_byte_length"], len(source))
        self.assertTrue(report["model_byte_ledger_fully_contiguous_nonoverlapping"])
        self.assertTrue(report["original_model_noop_reassembled_byte_identical"])
        self.assertEqual(report["source_model_bytes_without_framing"], 0)
        self.assertEqual(sum(report["byte_class_totals"].values()), len(source))
        self.assertEqual(sum(report["byte_class_span_totals"].values()),
                         report["total_nonoverlapping_source_spans"])
        self.assertEqual(sum(x["total_bytes"] for x in
                             report["role_byte_statistics"].values()), len(source))
        self.assertEqual(sum(report["byte_class_fractions"].values()), 1.)
        self.assertFalse(report["native_edited_BSP_or_MOPP_writer_enabled"])
        self.assertFalse(report["source_surface_array_indexed_from_model_authenticated"])
        self.assertFalse(report["retail_game_runtime_verified"])
        self.assertEqual(report, build_original_model_span_ledger(
            source, node_indices=[0, 2]))

    def test_original_node_spans_cover_all_fields_in_serial_order(self):
        model, frame = synthetic_world()
        report = build_original_model_span_ledger(model, node_indices=[1])
        selected = report["selected_node_source_spans"][0]
        record = frame["node_records"][1]
        self.assertEqual(selected["node"], 1)
        self.assertEqual(selected["original_native_model_record"],
                         {"start": record["start"], "byte_count": 109})
        pieces = selected["spans"]
        self.assertEqual(pieces[0]["role"], "node.candidate_plane_f32_bits")
        self.assertEqual(pieces[1]["role"], "node.subtree_zone_mask_bits")
        self.assertEqual(pieces[2]["role"], "node.compact_field_0")
        self.assertEqual(pieces[4]["role"], "node.compact_field_2")
        self.assertEqual(pieces[-1]["role"], "node.opaque_last_u32")
        self.assertEqual(len(pieces), 2+8+2+3+4)
        self.assertEqual(sum(p["byte_count"] for p in pieces), 109)
        expected = record["start"]
        for item in pieces:
            self.assertEqual(item["original_model_relative_offset"], expected)
            self.assertEqual(item["source_span_sha256"], hashlib.sha256(
                model[expected:expected+item["byte_count"]]).hexdigest())
            self.assertFalse(item["native_writer_permission"])
            expected += item["byte_count"]
        self.assertEqual(expected, record["start"]+record["length"])
        self.assertEqual(pieces[4]["original_model_relative_offset"],
                         record["start"] + 50)

    def test_noncanonical_compact_field_width_is_source_preserved(self):
        model, frame = synthetic_world()
        changed = model[:99] + b"\x40\x00" + model[100:]
        result = build_original_model_span_ledger(changed, node_indices=[0, 1])
        first, second = result["selected_node_source_spans"]
        first_fields = [x for x in first["spans"] if "compact_field_" in x["role"]]
        second_fields = [x for x in second["spans"] if "compact_field_" in x["role"]]
        self.assertEqual(first_fields[0]["byte_count"], 2)
        self.assertEqual(first_fields[2]["original_model_relative_offset"], 102)
        self.assertEqual(second_fields[2]["original_model_relative_offset"],
                         second["original_native_model_record"]["start"]+50)
        self.assertEqual(result["source_compact_integer_field_bytes"], 25)
        self.assertEqual(result["source_node_record_bytes"], 3*109 + 1)

    def test_noncanonical_source_node_count_keeps_original_byte_width(self):
        model, frame = synthetic_world()
        changed = model[:50] + b"\x43\x00" + model[51:]
        report = build_original_model_span_ledger(changed, node_indices=[0])
        self.assertEqual(report["original_node_array_start"], 52)
        self.assertEqual(report["selected_node_source_spans"][0][
            "original_native_model_record"]["start"], 52)
        role = report["role_byte_statistics"]["header.node_count_raw_compact"]
        self.assertEqual(role["total_bytes"], 2)
        self.assertEqual(role["concatenated_source_span_sha256"],
                         hashlib.sha256(b"\x43\x00").hexdigest())

    def test_opaque_original_source_bytes_are_counted_not_named_as_surfaces(self):
        model, frame = synthetic_world()
        opaque = build_original_model_span_ledger(model, node_indices=[0])
        roles = opaque["role_byte_statistics"]
        self.assertEqual(roles["node.opaque_spatial_f32_bits"]["certainty"], OPAQUE)
        self.assertEqual(roles["node.opaque_spatial_f32_bits"]["total_bytes"], 48)
        self.assertEqual(roles["node.opaque_spatial_reserved"]["total_bytes"], 48)
        self.assertEqual(roles["node.compact_field_2"]["certainty"], OPAQUE)
        self.assertEqual(roles["node.compact_field_5"]["certainty"], OBSERVED)
        self.assertEqual(roles["node.candidate_plane_f32_bits"]["certainty"], HYPOTHESIS)
        self.assertFalse(opaque["engine_field_names_authenticated"])

    def test_unknown_spatial_bytes_are_in_source_role_hash_not_normalized(self):
        model, frame = synthetic_world()
        changed = bytearray(model)
        at = frame["node_records"][1]["start"]+109-53
        changed[at:at+4] = b"\x01\x00\x80\x7f"
        changed = bytes(changed)
        report = build_original_model_span_ledger(changed, node_indices=[1])
        target = [p for p in report["selected_node_source_spans"][0]["spans"]
                  if p["role"] == "node.opaque_spatial_f32_bits"][0]
        self.assertEqual(target["original_model_relative_offset"], at)
        self.assertEqual(target["source_span_sha256"], hashlib.sha256(
            changed[at:at+16]).hexdigest())
        self.assertGreater(report["role_byte_statistics"]["node.opaque_spatial_f32_bits"][
            "nonzero_original_bytes"], 0)

    def test_zone_record_ledger_has_source_observed_69_byte_parts(self):
        source, frame = synthetic_world()
        report = build_original_model_span_ledger(source)
        zone_spans = report["first_zone_source_spans"]
        self.assertEqual(len(zone_spans), 3*4)
        self.assertEqual(zone_spans[0]["original_model_relative_offset"],
                         frame["candidate_zone_array_start"])
        self.assertEqual([r["byte_count"] for r in zone_spans[:4]], [1, 32, 32, 4])
        self.assertEqual(report["role_byte_statistics"][
            "zone_record.sourced_relation_mask_bits"]["span_count"], 3)
        self.assertEqual(report["role_byte_statistics"][
            "zone_record.observed_01_padding"]["nonzero_original_bytes"], 96)
        self.assertEqual(report["selected_original_node_ordinals"], [])
        self.assertEqual(report["selected_node_source_spans"], [])

    def test_refuse_bad_node_requests_and_tampered_model_bytes(self):
        model, frame = synthetic_world()
        for indices in ([0, 0], [-1], [3], [True], [0]*13, (0, 1, 1),
                        "0", {0}, range(2)):
            with self.subTest(indices=str(indices)), self.assertRaises(ValueError):
                build_original_model_span_ledger(model, node_indices=indices)
        for changed in (model[:-1], model+b"\x00",
                        model[:frame["candidate_zone_array_start"]+33]
                        + b"\x00" +
                        model[frame["candidate_zone_array_start"]+34:]):
            with self.subTest(length=len(changed)), self.assertRaises(ValueError):
                build_original_model_span_ledger(changed)

    def test_api_refuses_source_mismatch_and_uses_original_absolute_offsets(self):
        payload, frame = synthetic_world()
        original = b"\xe5"*64 + payload + b"\xf2"*11
        exp = {"offset": 64, "size": len(payload)}
        class Package:
            data = original
            exports = [exp]
            def class_name(self, e): return "Model"
            def payload(self, e):
                return self.data[e["offset"]:e["offset"]+e["size"]]
        class World:
            _package = Package()
            source = Path("Synthetic.gmp")
            source_sha256 = hashlib.sha256(original).hexdigest()
            checks = 0
            def _check_original_unchanged(self): self.checks += 1
        world = World()
        reference = {
            "world_model_export": 1,
            "world_model_sha256": hashlib.sha256(payload).hexdigest(),
            "node_count": frame["candidate_node_count"],
            "nodes": [{"plane": struct.unpack_from("<4f", payload, node["start"])}
                      for node in frame["node_records"]],
        }
        with patch("dx2sdk.bsp_model_spans._load_model", return_value=reference):
            report = inspect_original_model_span_ledger(world, [2, 0])
        self.assertEqual(world.checks, 2)
        self.assertEqual(report["selected_original_node_ordinals"], [2, 0])
        self.assertEqual(report["original_model_absolute_offset_in_gmp"], 64)
        for node in report["selected_node_source_spans"]:
            for part in node["spans"]:
                self.assertEqual(part["original_gmp_absolute_offset"],
                                 64+part["original_model_relative_offset"])
        self.assertFalse(report["original_source_modified"])
        self.assertEqual(Package.data, original)
        world.source_sha256 = "f"*64
        with patch("dx2sdk.bsp_model_spans._load_model", return_value=reference), \
                self.assertRaisesRegex(ValueError, "changed"):
            inspect_original_model_span_ledger(world, [0])

    def test_cli_report_is_sha_pinned_and_exposes_selected_original_nodes(self):
        import inspect_world_model_spans as cli
        class FakeWorld:
            source = Path("Synthetic.gmp")
            source_sha256 = "a"*64
            def inspect_original_model_byte_spans(self, node_indices=None):
                return {
                    "status": "read-only-original-World-Model-complete-byte-ledger",
                    "original_gmp_sha256": self.source_sha256,
                    "original_model_noop_reassembled_byte_identical": True,
                    "selected_original_node_ordinals": node_indices or [],
                    "source_surface_array_indexed_from_model_authenticated": False,
                    "native_edited_BSP_or_MOPP_writer_enabled": False,
                }
        output = StringIO()
        with patch.object(cli.DX2Map, "open", return_value=FakeWorld()), redirect_stdout(output):
            status = cli.main(["Synthetic.gmp", "--source-sha256", "a"*64,
                               "--node", "2", "--node", "0"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["selected_original_node_ordinals"],
                         [2, 0])
        refused = StringIO()
        with patch.object(cli.DX2Map, "open", return_value=FakeWorld()), redirect_stderr(refused):
            status = cli.main(["Synthetic.gmp", "--source-sha256", "b"*64])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(refused.getvalue())["status"], "refused")


if __name__ == "__main__":
    unittest.main()
