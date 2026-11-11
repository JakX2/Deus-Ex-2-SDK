"""Asset-free source MOPP terminal opcode provenance tests for DX2Ed v0.73."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from unittest.mock import patch
import unittest

from dx2sdk.mopp_leaf_bytes import (
    index_mopp_terminal_instructions, inspect_level_mopp_terminal_bytes,
    inspect_original_mopp_terminal_bytes, inspect_original_plane_affected_terminal_bytes,
)
from test_dx2_level_mopp_triangle_provenance import fixture

ROOT14 = b"\x28\x00\xff\x27\x00\xff\x26\x00\xff\x20\x80\x01\x30\x31"


class MoppTerminalByteProvenanceTests(unittest.TestCase):
    def test_original_two_branch_leaf_offsets_and_level_offsets(self):
        level, blocks, _ = fixture()
        original = deepcopy((level, blocks))
        report = inspect_level_mopp_terminal_bytes(
            level, blocks, [1, 0], level_export_offset=100)
        self.assertEqual(report["original_terminal_instruction_count"], 2)
        self.assertEqual(report["original_flat_triangle_count"], 2)
        self.assertEqual(report["selected_flat_triangle_ids"], [1, 0])
        self.assertEqual(report["mopp_code_sha256"], hashlib.sha256(ROOT14).hexdigest())
        start = report["original_code_start_in_level"]
        for row, tid, pc, section in zip(report["selected"], [1, 0], [13, 12], [1, 0]):
            self.assertEqual(row["flattened_triangle_id"], tid)
            self.assertEqual(row["source_provenance_section_field_b"], section)
            self.assertEqual(row["source_terminal"]["instruction_offset_in_code"], pc)
            self.assertEqual(row["source_terminal"]["instruction_size_bytes"], 1)
            self.assertEqual(row["source_terminal"]["leaf_encoding"], "leaf_inline")
            self.assertEqual(row["mopp_opcode_offset_in_level"], start + pc)
            self.assertEqual(row["mopp_opcode_absolute_offset_in_gmp"], 100 + start + pc)
            self.assertEqual(row["mopp_encoded_delta_absolute_offset_in_gmp"],
                             100 + start + pc)
            self.assertEqual(row["provenance_pair_absolute_offset_in_gmp"],
                             100 + row["provenance_pair_offset_in_level"])
            self.assertFalse(row["source_terminal"]["native_mopp_leaf_patch_authorized"])
        self.assertFalse(report["native_BSP_or_MOPP_writer_enabled"])
        self.assertFalse(report["retail_runtime_verified"])
        self.assertEqual((level, blocks), original)
        self.assertEqual(report, inspect_level_mopp_terminal_bytes(
            level, blocks, [1, 0], level_export_offset=100))

    def test_big_endian_immediate_leaf_and_output_base_offset(self):
        samples = [
            (b"\x28\x00\xff\x09\x01\x50\x00", 5, 1, 1, 1),
            (b"\x28\x00\xff\x0a\x00\x01\x51\x00\x00", 6, 1, 2, 1),
            (b"\x28\x00\xff\x0b\x00\x00\x00\x01\x52\x00\x00\x00", 8, 1, 3, 1),
        ]
        for code, pc, tid, width, base in samples:
            with self.subTest(code=code.hex()):
                indexed = index_mopp_terminal_instructions(code, 2)
                self.assertEqual(set(indexed), {tid})
                row = indexed[tid]
                self.assertEqual(row["instruction_offset_in_code"], pc)
                self.assertEqual(row["encoded_delta_offset_in_code"], pc + 1)
                self.assertEqual(row["encoded_delta_size_bytes"], width)
                self.assertEqual(row["source_output_base"], base)
                self.assertEqual(row["source_encoded_delta"], 0)
                self.assertTrue(row["source_operand_big_endian"])

    def test_degenerate_triangle_has_no_terminal_or_fake_byte_offset(self):
        level, blocks, _ = fixture(code=b"\x28\x00\xff\x31", degenerate=True)
        report = inspect_level_mopp_terminal_bytes(
            level, blocks, [0, 1], level_export_offset=40)
        self.assertEqual(report["original_terminal_instruction_count"], 1)
        missing, present = report["selected"]
        self.assertTrue(missing["missing_terminal_is_source_degenerate_triangle"])
        self.assertIsNone(missing["source_terminal"])
        self.assertIsNone(missing["mopp_opcode_absolute_offset_in_gmp"])
        self.assertFalse(present["missing_terminal_is_source_degenerate_triangle"])
        self.assertEqual(present["source_terminal"]["instruction_offset_in_code"], 3)

    def test_refuse_truncated_or_invalid_mopp_code(self):
        for code, count in [
            (b"\x28\x00\xff\xee", 1),
            (b"\x28\x00\xff\x05\xff\x30", 1),
            (b"\x28\x00\xff\x20\x80\x01\x30\x30", 1),
        ]:
            with self.subTest(code=code.hex()), self.assertRaises(ValueError):
                index_mopp_terminal_instructions(code, count)

    def test_refuse_duplicate_out_of_range_boolean_and_bad_export_offset(self):
        level, blocks, _ = fixture()
        for ids in ([0, 0], [2], [True], [], range(2), [-1], [0]*33):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                inspect_level_mopp_terminal_bytes(level, blocks, ids)
        for offset in (-1, True, 1.5):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                inspect_level_mopp_terminal_bytes(
                    level, blocks, [0], level_export_offset=offset)

    def test_refuse_corrupted_source_level_or_mopp_footer(self):
        level, blocks, _ = fixture()
        for payload in (level[:-1] + b"\x01", level[:-2], level + b"\x00"):
            with self.subTest(length=len(payload)), self.assertRaises(ValueError):
                inspect_level_mopp_terminal_bytes(payload, blocks, [0])

    def test_real_gmp_envelope_offset_and_sha_are_checked(self):
        level, blocks, _ = fixture()
        prefix = bytes([0xAB])*64
        suffix = bytes([0xFE])*12
        class Package:
            data = prefix + level + suffix
            exports = [{"offset": 64, "size": len(level), "kind": "Level"}]
            def class_name(self, export):
                return export["kind"]
            def payload(self, export):
                return self.data[export["offset"]:export["offset"]+export["size"]]
        class World:
            _package = Package()
            source = Path("Synthetic.gmp")
            source_sha256 = hashlib.sha256(Package.data).hexdigest()
            checks = 0
            def _check_original_unchanged(self):
                self.checks += 1
        world = World()
        with patch("dx2sdk.mopp_leaf_bytes.find_bsp", return_value=blocks):
            result = inspect_original_mopp_terminal_bytes(world, [1])
        self.assertEqual(world.checks, 2)
        self.assertEqual(result["source_sha256"], world.source_sha256)
        self.assertEqual(result["original_level_export"], 1)
        self.assertEqual(result["original_level_export_size_bytes"], len(level))
        self.assertEqual(result["selected"][0]["mopp_opcode_absolute_offset_in_gmp"],
                         64 + result["original_code_start_in_level"] + 13)
        self.assertFalse(result["original_package_bytes_modified"])
        world.source_sha256 = "f"*64
        with self.assertRaisesRegex(ValueError, "differs"):
            inspect_original_mopp_terminal_bytes(world, [1])

    def test_bsp_candidate_samples_join_exact_source_leaf_byte_locations(self):
        source = "a"*64
        class World:
            checks = 0
            def _check_original_unchanged(self):
                self.checks += 1
        world = World()
        candidate = {
            "flattened_triangle_id": 1, "render_locator": [0, 1, 0],
            "source_provenance_block_field_a": 0,
            "source_provenance_section_field_b": 1,
            "original_mopp_terminal_leaf_present": True,
        }
        impact = {
            "source_sha256": source,
            "lost_candidate_mopp_id_examples": [candidate],
            "gained_candidate_mopp_id_examples": [],
        }
        index = {
            "source_sha256": source, "mopp_code_sha256": "b"*64,
            "selected": [{
                **candidate, "mopp_opcode_absolute_offset_in_gmp": 2048,
                "mopp_encoded_delta_absolute_offset_in_gmp": 2048,
                "source_terminal": {"instruction_offset_in_code": 13},
            }],
        }
        with patch("dx2sdk.mopp_leaf_bytes.compare_original_plane_mopp_impact",
                   return_value=impact), patch(
                "dx2sdk.mopp_leaf_bytes.inspect_original_mopp_terminal_bytes",
                return_value=index) as indexed:
            report = inspect_original_plane_affected_terminal_bytes(
                world, node=4, replacement=(0., 0., 1., 2.))
        self.assertEqual(world.checks, 2)
        indexed.assert_called_once_with(world, [1])
        self.assertEqual(report["lost_candidate_mopp_id_examples"][0][
            "terminal_instruction"]["mopp_opcode_absolute_offset_in_gmp"], 2048)
        self.assertFalse(report["native_BSP_or_MOPP_writer_enabled"])
        self.assertFalse(report["retail_runtime_verified"])
        for tweak in ("source", "locator"):
            bad = deepcopy(index)
            if tweak == "source":
                bad["source_sha256"] = "0"*64
            else:
                bad["selected"][0]["render_locator"] = [9, 9, 9]
            with self.subTest(tweak=tweak), patch(
                    "dx2sdk.mopp_leaf_bytes.compare_original_plane_mopp_impact",
                    return_value=impact), patch(
                    "dx2sdk.mopp_leaf_bytes.inspect_original_mopp_terminal_bytes",
                    return_value=bad), self.assertRaises(ValueError):
                inspect_original_plane_affected_terminal_bytes(
                    World(), node=4, replacement=(0., 0., 1., 2.))


if __name__ == "__main__":
    unittest.main()
