"""Fixture-only DX2 original World Model byte-identical no-op tests.

These tests never read, edit or distribute retail Deus Ex: Invisible War data.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from dx2sdk.bsp_model_noop import (
    reassemble_original_world_model, inspect_original_world_model_noop,
)
from inspect_world_bsp_node_boundaries import parse_world_model
from test_dx2_world_bsp_zone_relations import synthetic_world


class OriginalWorldModelNoopTests(unittest.TestCase):
    def test_source_node_zone_model_complete_byte_exact_noop(self):
        source, _ = synthetic_world()
        original = bytes(source)
        rebuilt, result = reassemble_original_world_model(source)
        self.assertEqual(source, original)
        self.assertEqual(source, rebuilt)
        self.assertTrue(result["model_reassembled_byte_identical"])
        self.assertTrue(result["all_source_bytes_accounted_for"])
        self.assertEqual(result["source_model_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(result["reassembled_model_sha256"], result["source_model_sha256"])
        self.assertEqual(result["original_model_bytes"], len(source))
        self.assertEqual(result["source_node_count"], 3)
        self.assertEqual(result["source_zone_count"], 3)
        self.assertEqual(result["node_record_length_histogram"], {"109": 3})
        self.assertEqual(result["compact_integer_width_histogram"], {"1": 24})
        self.assertEqual(result["original_node_compact_field_bytes"], 24)
        self.assertEqual(result["source_reserved_nonzero_bytes_preserved"], 0)
        self.assertEqual(result["original_node_count_compact_width"], 1)
        self.assertFalse(result["native_modified_model_writer_enabled"])
        self.assertFalse(result["native_BSP_surface_or_vertex_pool_recovered"])
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(result, reassemble_original_world_model(source)[1])

    def test_preserve_source_compact_integer_noncanonical_count_bits(self):
        source, _ = synthetic_world()
        # Two-byte compact count encoding of 3; ordinary canonical is one byte.
        changed = source[:50] + b"\x43\x00" + source[51:]
        self.assertEqual(parse_world_model(changed)["candidate_node_count_width"], 2)
        rebuilt, result = reassemble_original_world_model(changed)
        self.assertEqual(rebuilt, changed)
        self.assertEqual(result["original_node_count_compact_width"], 2)
        self.assertTrue(result["source_compact_index_byte_encodings_preserved"])

    def test_preserve_original_record_with_two_byte_compact_index(self):
        source, _ = synthetic_world()
        # Source node0 compact field0 at 51+48; encode 0 with two bytes.
        changed = source[:99] + b"\x40\x00" + source[100:]
        original_frame = parse_world_model(changed, include_nodes=True)
        self.assertEqual(original_frame["node_record_lengths"], {"109": 2, "110": 1})
        rebuilt, report = reassemble_original_world_model(changed)
        self.assertEqual(rebuilt, changed)
        self.assertEqual(report["compact_integer_width_histogram"], {"1": 23, "2": 1})
        self.assertEqual(report["original_node_compact_field_bytes"], 25)
        self.assertEqual(report["first_source_node_compact_field_offsets"][0][
            "original_compact_field_widths"][0], 2)
        self.assertTrue(report["source_original_f32_bits_preserved_without_requantization"])

    def test_source_field2_offsets_track_actual_variable_width_records(self):
        source, _ = synthetic_world()
        changed = source[:99] + b"\x40\x00" + source[100:]
        _, report = reassemble_original_world_model(changed)
        frame = parse_world_model(changed, include_nodes=True)
        first = report["first_source_node_compact_field_offsets"][0]
        second = report["first_source_node_compact_field_offsets"][1]
        self.assertEqual(first["original_field2_offset_in_model"], 51 + 48 + 2 + 1)
        self.assertEqual(second["original_node_start_in_model"],
                         frame["node_records"][1]["start"])
        self.assertEqual(second["original_field2_offset_in_model"],
                         frame["node_records"][1]["start"] + 48 + 2)

    def test_repeated_noop_with_opaque_spatial_f32_payload(self):
        source, frame = synthetic_world()
        raw = bytearray(source)
        # Four original bits are spatial/opaque, not a source plane. Preserve
        # an unusual float32 bit pattern without re-quantizing or naming it.
        at = frame["node_records"][1]["start"] + 109 - 53
        raw[at:at+4] = b"\x01\x00\x80\x7f"  # unclassified float representation
        changed = bytes(raw)
        rebuilt, report = reassemble_original_world_model(changed)
        self.assertEqual(rebuilt, changed)
        self.assertTrue(report["opaque_source_regions_preserved"])
        self.assertEqual(changed[at:at+4], b"\x01\x00\x80\x7f")

    def test_refuse_corrupted_zone_mask_and_zone_table(self):
        source, frame = synthetic_world()
        mutated = bytearray(source)
        mutated[frame["node_records"][0]["start"] + 16] = 0
        with self.assertRaises(ValueError):
            reassemble_original_world_model(bytes(mutated))
        mutated = bytearray(source)
        mutated[frame["candidate_zone_array_start"] + 33] = 0
        with self.assertRaises(ValueError):
            reassemble_original_world_model(bytes(mutated))
        mutated = bytearray(source)
        mutated[-1] = 1
        with self.assertRaises(ValueError):
            reassemble_original_world_model(bytes(mutated))

    def test_refuse_truncated_or_nonbytes_or_malformed_native_record(self):
        source, frame = synthetic_world()
        for bad in [source[:-1], source+b"\x00", b"", bytearray(source),
                    source[:50] + b"\x00" + source[51:]]:
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                reassemble_original_world_model(bad)
        bad = bytearray(source)
        struct.pack_into("<i", bad, frame["node_records"][-1]["start"]+109-16, 77)
        with self.assertRaises(ValueError):
            reassemble_original_world_model(bytes(bad))

    def test_rooted_model_exact_native_export_source_bounds_and_immutability(self):
        model, frame = synthetic_world()
        prefix, suffix = b"\x3b"*64, b"\x8c"*15
        raw = prefix + model + suffix
        exp = {"offset": len(prefix), "size": len(model)}
        class Package:
            data = raw
            exports = [exp]
            def class_name(self, export): return "Model"
            def payload(self, export):
                return self.data[export["offset"]:export["offset"]+export["size"]]
        class World:
            source = Path("Synthetic.gmp")
            source_sha256 = hashlib.sha256(raw).hexdigest()
            _package = Package()
            checks = 0
            def _check_original_unchanged(self): self.checks += 1
        world = World()
        validated = {
            "world_model_export": 1,
            "world_model_sha256": hashlib.sha256(model).hexdigest(),
            "node_count": frame["candidate_node_count"],
            "nodes": [{"plane": struct.unpack_from("<4f", model, row["start"])}
                      for row in frame["node_records"]],
        }
        with patch("dx2sdk.bsp_model_noop._load_model", return_value=validated):
            report = inspect_original_world_model_noop(world)
        self.assertEqual(world.checks, 2)
        self.assertEqual(report["original_world_model_absolute_offset_in_gmp"], len(prefix))
        self.assertEqual(report["original_world_model_export_length"], len(model))
        self.assertEqual(report["source_gmp_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(report["original_game_package_modified"])
        self.assertEqual(raw, Package.data)
        world.source_sha256 = "f"*64
        with patch("dx2sdk.bsp_model_noop._load_model", return_value=validated), \
                self.assertRaisesRegex(ValueError, "pinned source"):
            inspect_original_world_model_noop(world)

    def test_refuse_forged_export_payload_or_bounds(self):
        model, frame = synthetic_world()
        raw = b"X"*64 + model
        exp = {"offset": 64, "size": len(model)}
        class Package:
            data = raw
            exports = [exp]
            def class_name(self, e): return "Model"
            def payload(self, e): return model[:-1]+b"\x01"
        class World:
            source = Path("Synthetic.gmp")
            source_sha256 = hashlib.sha256(raw).hexdigest()
            _package = Package()
            def _check_original_unchanged(self): pass
        validated = {
            "world_model_export": 1,
            "world_model_sha256": hashlib.sha256(model).hexdigest(),
            "node_count": frame["candidate_node_count"],
            "nodes": [{"plane": struct.unpack_from("<4f", model, r["start"])}
                      for r in frame["node_records"]],
        }
        with patch("dx2sdk.bsp_model_noop._load_model", return_value=validated), \
                self.assertRaisesRegex(ValueError, "source GMP"):
            inspect_original_world_model_noop(World())
        Package.payload = lambda self, e: self.data[e["offset"]:e["offset"]+e["size"]]
        exp["offset"] = len(raw)
        with patch("dx2sdk.bsp_model_noop._load_model", return_value=validated), \
                self.assertRaisesRegex(ValueError, "envelope"):
            inspect_original_world_model_noop(World())


if __name__ == "__main__":
    unittest.main()
