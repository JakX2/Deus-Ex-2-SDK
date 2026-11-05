"""Synthetic source-only DX2 mission-vs-Kernel TriggerScript comparison.

No proprietary map or IBD bytes. Confirm real buffer comparisons,
byte-difference metadata, identity binding and fail-closed write policies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor/godot_editor/backend"))
sys.path.insert(0, str(ROOT / "tools/scripts"))
from dx2_mission_kernel_script_diff import (
    SCHEMA, byte_difference, build_comparison, write_private_comparison,
    _actor_reference_summary,
)
from dx2_script_bundle_probe import MAGIC, HEADER_SIZE, ENTRY_SIZE


def tsd(name: str) -> bytes:
    symbols = name + "\x00" + "Synthetic research trigger\x00" + "kTAT_SendMsg\x00"
    return b"1FFE2FST" + b"\x00" * 8 + symbols.encode("utf-16le")


def ibd_pack(pairs: list[tuple[str, bytes]]) -> bytes:
    align = 2048
    data_start = align
    assert len(pairs) < 6
    output = bytearray(data_start + len(pairs) * align)
    count = len(pairs)
    struct.pack_into("<8I", output, 0, MAGIC, align, data_start,
                     len(pairs) * align, count, 1, count, count)
    for i, (name, payload) in enumerate(pairs):
        assert 0 < len(payload) <= align and len(name) < ENTRY_SIZE - 0x29
        p = HEADER_SIZE + i * ENTRY_SIZE
        where = data_start + i * align
        struct.pack_into("<5I", output, p, where,
                         len(payload), align - len(payload), i, 1)
        output[p + 0x28] = 21
        output[p + 0x29:p + 0x29 + len(name)] = name.encode("ascii")
        struct.pack_into("<I", output,
                         HEADER_SIZE + count * ENTRY_SIZE + 4 * i, len(payload))
        output[where:where + len(payload)] = payload
    return bytes(output)


class MissionKernelComparisonTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dx2ed_mission_kernel_synthetic_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.game = self.root / "OriginalGame" / "Content" / "DX2"
        self.maps = self.game / "Maps"
        self.maps.mkdir(parents=True)
        self.map = self.maps / "M1_Seattle_Club.gmp"
        self.map.write_bytes(b"synthetic original GMP identity, NOT retail")
        self.actors = self.root / "DX2EdPrivateActorCache" / "actors.json"
        self.actors.parent.mkdir()
        self.actors.write_text(json.dumps({
            "meta": {
                "source_map": self.map.name,
                "source_sha256": hashlib.sha256(self.map.read_bytes()).hexdigest(),
            },
            "actors": [],
        }), encoding="utf-8")
        self.zip = self.game / "TriggerScript.zip"
        self.sources = {name: tsd(name) for name in
                        ("TS_A", "TS_B", "TS_C", "TS_D", "TS_E")}
        with ZipFile(self.zip, "w") as archive:
            for name, raw in self.sources.items():
                archive.writestr("Defs/" + name + ".tsd", raw)
        m_b = bytearray(self.sources["TS_B"][12:])
        m_b[4] ^= 0x7f
        self.mission = self.maps / "m1_seattle_club.ibd"
        self.mission.write_bytes(ibd_pack([
            ("TS_A", self.sources["TS_A"][12:]),
            ("TS_B", bytes(m_b)),
            ("TS_C", self.sources["TS_C"][12:-2]),
            ("TS_MISSING", b"unknown script resource not in original ZIP"),
        ]))
        self.kernel = self.maps / "Kernel_TSDALL.ibd"
        self.kernel.write_bytes(ibd_pack([
            ("TS_A", self.sources["TS_A"][12:]),
            ("TS_B", self.sources["TS_B"][12:]),
            ("TS_C", self.sources["TS_C"][12:-2]),
            ("TS_D", self.sources["TS_D"][12:]),
        ]))
        self.out = self.root / "PrivateReports" / "club_vs_kernel.json"

    def compare(self):
        return build_comparison(
            self.map, self.actors, self.zip, self.mission, self.kernel)

    def test_disjoint_and_shared_provenance_with_actual_changed_byte_offsets(self):
        original_files = [self.map, self.actors, self.zip, self.mission, self.kernel]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files]
        report = self.compare()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["runtime_actor_script_binding_verified"])
        self.assertFalse(report["native_script_writer_enabled"])
        self.assertFalse(report["original_game_assets_modified"])
        c = report["counts"]
        self.assertEqual(c["mission_script_resources"], 4)
        self.assertEqual(c["kernel_script_resources"], 4)
        self.assertEqual(c["shared_script_ids"], 3)
        self.assertEqual(c["shared_payload_exact"], 2)
        self.assertEqual(c["shared_payload_different"], 1)
        self.assertEqual(c["mission_only"], 1)
        self.assertEqual(c["kernel_only"], 1)
        self.assertEqual(c["mission_vs_standalone_exact"], 1)
        self.assertEqual(c["mission_vs_standalone_different"], 2)
        self.assertEqual(c["kernel_vs_standalone_exact"], 3)
        self.assertEqual(c["kernel_vs_standalone_different"], 1)
        self.assertEqual(report["actor_name_slot_candidates"]["status"],
                         "source_actor_name_slots_unavailable")
        rows = {r["script_id"]: r for r in report["script_rows"]}
        self.assertEqual(rows["TS_A"]["mission_vs_kernel"]["byte_equal"], True)
        self.assertEqual(rows["TS_A"]["mission_vs_standalone"]["byte_equal"], True)
        self.assertEqual(rows["TS_B"]["mission_vs_kernel"]["first_difference_offset"], 4)
        self.assertEqual(rows["TS_B"]["mission_vs_kernel"]["overlapping_different_bytes"], 1)
        self.assertEqual(rows["TS_B"]["mission_vs_kernel"]["different_byte_runs_in_overlap"], 1)
        self.assertEqual(rows["TS_B"]["mission_vs_standalone"]["first_difference_offset"], 4)
        self.assertTrue(rows["TS_B"]["kernel_vs_standalone"]["byte_equal"])
        self.assertFalse(rows["TS_C"]["mission_vs_standalone"]["same_size"])
        self.assertTrue(rows["TS_C"]["mission_vs_kernel"]["byte_equal"])
        self.assertEqual(rows["TS_D"]["mission_original_tsd_status"], "absent")
        self.assertIsNone(rows["TS_D"]["mission_vs_kernel"])
        self.assertEqual(rows["TS_MISSING"]["mission_original_tsd_status"],
                         "not_in_original_zip")
        self.assertEqual(rows["TS_MISSING"]["kernel_original_tsd_status"], "absent")
        self.assertEqual(report["source_status_transitions"]["different_payload_to_exact_payload"], 1)
        self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in original_files], before)

    def test_byte_profile_same_length_different_length_common_prefix_and_suffix(self):
        same = byte_difference(b"abcdef", b"abcxef")
        self.assertEqual(same["first_difference_offset"], 3)
        self.assertEqual(same["common_prefix_bytes"], 3)
        self.assertEqual(same["common_suffix_bytes"], 2)
        self.assertEqual(same["overlapping_different_bytes"], 1)
        self.assertEqual(same["different_byte_runs_in_overlap"], 1)
        shorter = byte_difference(b"abcdef", b"abc")
        self.assertEqual(shorter["first_difference_offset"], 3)
        self.assertEqual(shorter["size_difference_bytes"], -3)
        self.assertEqual(shorter["overlapping_different_bytes"], 0)
        identical = byte_difference(b"abcdef", b"abcdef")
        self.assertTrue(identical["byte_equal"])
        self.assertIsNone(identical["first_difference_offset"])

    def test_reject_modified_gmp_cache_identity(self):
        self.map.write_bytes(self.map.read_bytes() + b"CHANGED")
        with self.assertRaisesRegex(ValueError, "cache does not match"):
            self.compare()

    def test_reject_wrong_kernel_path_or_same_bundle(self):
        bad = self.maps / "another_original.ibd"
        bad.write_bytes(self.kernel.read_bytes())
        with self.assertRaisesRegex(ValueError, "Choose separate original"):
            build_comparison(self.map, self.actors, self.zip, self.mission, bad)
        with self.assertRaisesRegex(ValueError, "Choose separate original"):
            build_comparison(self.map, self.actors, self.zip, self.kernel, self.kernel)

    def test_corrupt_kernel_resource_table_rejected(self):
        corrupted = bytearray(self.kernel.read_bytes())
        corrupted[0] = 0
        self.kernel.write_bytes(corrupted)
        with self.assertRaises(ValueError):
            self.compare()

    def test_private_report_refuses_existing_output_and_game_source_paths(self):
        report = write_private_comparison(
            self.map, self.actors, self.zip, self.mission, self.kernel, self.out)
        loaded = json.loads(self.out.read_text("utf8"))
        self.assertEqual(loaded, report)
        with self.assertRaises(ValueError):
            write_private_comparison(
                self.map, self.actors, self.zip, self.mission, self.kernel, self.out)
        for folder in (self.maps, self.game, self.root / "OriginalGame"):
            with self.subTest(folder=folder), self.assertRaises(ValueError):
                write_private_comparison(
                    self.map, self.actors, self.zip, self.mission, self.kernel,
                    folder / "unsafe_report.json")
            self.assertFalse((folder / "unsafe_report.json").exists())

    def test_cli_redacts_local_original_paths_and_original_bytes(self):
        cli = ROOT / "native_editor/godot_editor/backend/dx2_mission_kernel_script_diff.py"
        arguments = [sys.executable, str(cli),
                     "--map", str(self.map), "--actors", str(self.actors),
                     "--scripts", str(self.zip),
                     "--mission-ibd", str(self.mission),
                     "--kernel-ibd", str(self.kernel), "--output", str(self.out)]
        run = subprocess.run(arguments, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        reply = json.loads(run.stdout)
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["counts"]["shared_script_ids"], 3)
        for private in ("OriginalGame", str(self.mission), str(self.kernel),
                        "TS_A", "M1_Seattle_Club", "Synthetic research trigger"):
            self.assertNotIn(private, run.stdout)
        second = subprocess.run(arguments, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["status"], "refused")
        self.assertNotIn(str(self.map), second.stdout)

    def test_actor_name_slot_candidate_counts_are_explicitly_nonruntime(self):
        def probe(status):
            return {
                "status": "original_package_name_slots_inspected",
                "actors": [{
                    "actor": "Synthetic", "class": "D_1", "export": 7,
                    "status": "numeric_array_redecoded",
                    "native_game_property_92_verified": True,
                    "candidates": [{
                        "raw_compact_integer": 5,
                        "name_at_same_numeric_slot": "TS_B",
                        "same_name_in_original_tsd_archive": True,
                        "slot_in_package_name_table": True,
                        "ibd_resource_payload_status": status,
                        "actor_runtime_link_verified": False,
                    }]
                }]
            }
        m = {"ts_b": {"status": "different_payload"}}
        k = {"ts_b": {"status": "exact_payload"}}
        result = _actor_reference_summary(
            probe("different_payload"), probe("exact_payload"), m, k)
        self.assertEqual(result["raw_name_slot_candidate_occurrences"], 1)
        self.assertEqual(result["transition_counts"],
                         {"different_payload_to_exact_payload": 1})
        self.assertFalse(result["original_actor_script_runtime_links_verified"])
        forged = probe("exact_payload")
        refused = _actor_reference_summary(forged, probe("exact_payload"), m, k)
        self.assertEqual(refused["status"], "source_actor_name_slots_unavailable")


if __name__ == "__main__":
    unittest.main()
