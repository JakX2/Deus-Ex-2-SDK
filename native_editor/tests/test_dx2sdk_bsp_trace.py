"""Original-source-only DX2SDK BSP plane candidate/Light Region diagnostics.

Entire map, Model and Light are synthetic. No game bytes or assets copied.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "dx2"))
from dx2sdk import DX2Map
from dx2sdk.bsp_trace import SCHEMA, _point, _epsilon, _trace
from test_dx2_light_dependency_audit import _synthetic_light_map
from test_dx2_world_bsp_zone_relations import synthetic_world
from tools.build_dx2sdk_source_release import build, ARCHIVE
from upkg import Package
from upkgwrite import ImportEntry, PackageWriter, enc_index


def synthetic_map_with_bsp_and_light(path: Path) -> bytes:
    _synthetic_light_map(path)
    base = Package(path)
    w = PackageWriter(base)
    data, _frame = synthetic_world()
    class_idx = w.name_index("Class")
    model_name_idx = w.name_index("Model")
    w.imports.append(ImportEntry(
        0, class_idx, 0, model_name_idx, (b"", b"", b"")))
    new_model = w.add_export(0, "Model__0", data)
    w.exports[new_model].class_ref = -len(w.imports)
    w.exports[new_model].flags = 0
    level = (bytes(13) + struct.pack("<II", 1, 1) + enc_index(1)
             + bytes(5)  # FURL protocol, host, map, portal, options count
             + struct.pack("<II", 7777, 1)
             + enc_index(new_model + 1))
    w.set_object(1, level)
    result = w.write()
    path.write_bytes(result)
    world = DX2Map.open(path)
    assert world._package.class_name(world._package.exports[new_model]) == "Model"
    return result


class BSPPlaneTraceTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2sdk_bsp_plane_v09_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "Original" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        self.original = synthetic_map_with_bsp_and_light(self.source)
        self.world = DX2Map.open(self.source)
        self.report = self.root / "PrivateResearch" / "plane-audit.json"

    def cli(self, *arguments, cwd=ROOT):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *arguments],
            cwd=cwd, capture_output=True, text=True, timeout=75)

    def test_negative_positive_candidate_branch_without_inventing_leaf(self):
        for x, expected_child, zone in ((-2., 1, 1), (2., 2, 2)):
            with self.subTest(x=x):
                result = self.world.trace_bsp_point((x, 3., 4.))
                self.assertEqual(result["schema"], SCHEMA)
                self.assertTrue(result["graph_and_zone_relations_validated"])
                self.assertEqual(result["source_node_count"], 3)
                self.assertEqual(result["source_zone_record_count"], 3)
                self.assertEqual(result["candidate_terminal_count"], 1)
                self.assertEqual(result["visited_nodes"], 2)
                terminal = result["candidate_missing_branch_terminals"][0]
                self.assertEqual(terminal["parent_node"], expected_child)
                self.assertEqual(terminal["node_zone_a_u16"], zone if zone == 1 else 0)
                self.assertEqual(terminal["node_zone_b_u16"], zone)
                self.assertEqual(terminal["plane_path"][0]["node"], 0)
                self.assertEqual(terminal["plane_path"][1]["node"], expected_child)
                self.assertIsNone(terminal["source_region_leaf"])
                self.assertIsNone(terminal["source_region_zone_number_low"])
                self.assertFalse(terminal["native_leaf_or_zone_assignment_verified"])
                self.assertFalse(result["point_to_leaf_verified"])
                self.assertFalse(result["point_to_zone_verified"])
                self.assertFalse(result["native_light_placement_enabled"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_epsilon_fork_reports_ambiguous_terminal_without_guess(self):
        result = self.world.trace_bsp_point((0., 0., 0.), epsilon=.01)
        self.assertEqual(result["candidate_terminal_count"], 4)
        self.assertEqual(result["near_plane_forks"], 3)
        self.assertEqual(result["visited_nodes"], 3)
        self.assertTrue(result["diagnostic_only"])
        self.assertFalse(result["native_bsp_rebuild_supported"])
        self.assertEqual(
            set(x["parent_node"] for x in result["candidate_missing_branch_terminals"]),
            {1, 2})

    def test_existing_original_light_region_never_extrapolated_to_new_point(self):
        result = self.world.trace_original_light_regions(limit=1)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["original_lights_checked_by_native_reference_audit"], 1)
        self.assertEqual(result["original_lights_sampled"], 1)
        row = result["samples"][0]
        self.assertEqual(row["original_actor"], "Light__0")
        self.assertEqual(row["original_export"], 1)
        self.assertEqual(row["original_Region_iLeaf"], 20)
        self.assertEqual(row["original_Region_ZoneNumberLow"], 8)
        self.assertEqual(row["candidate_terminal_count"], 1)
        self.assertFalse(row["equivalence_with_engine_Region_proven"])
        self.assertFalse(row["native_light_relocation_or_spawn_enabled"])
        self.assertFalse(result["native_region_leaf_assignment_verified"])
        self.assertFalse(result["native_region_zone_assignment_verified"])
        self.assertEqual(result["source_zone_matches_terminal_node_fields"], 0)
        self.assertEqual(self.world.trace_original_light_regions(limit=0)["samples"], [])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_reject_nonfinite_wrong_type_and_out_of_bounds_without_output(self):
        cases = (
            (None, .01), ([1,2], .01), ([True,0,0], .01),
            ([float("nan"),0,0], .01),
            ([float("inf"),0,0], .01), ([1_000_001,0,0], .01),
            ([0,0,0], float("nan")), ([0,0,0], 0.),
            ([0,0,0], 2.), ([0,0,0], True),
        )
        for point, eps in cases:
            with self.subTest(point=point, epsilon=eps), self.assertRaises(ValueError):
                self.world.trace_bsp_point(point, epsilon=eps)
        with self.assertRaises(ValueError):
            self.world.trace_original_light_regions(limit=True)
        with self.assertRaises(ValueError):
            self.world.trace_original_light_regions(limit=1001)
        self.assertFalse(self.report.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_invalid_world_model_topology_refuses_source(self):
        pkg = Package(self.source)
        model = pkg.exports[-1]
        blob = bytearray(pkg.export_bytes(model))
        # Node 0: 50-byte Model prefix, compact count (1), 16 plane, 32 mask,
        # eight compact ints; column 3 is the negative child, make it point
        # at node zero (self link, forbidden).
        blob[50+1+48+3] = 0
        writer = PackageWriter(pkg)
        writer.set_object(model.index, bytes(blob))
        self.source.write_bytes(writer.write())
        new_world = DX2Map.open(self.source)
        with self.assertRaisesRegex(ValueError, "invalid linked index"):
            new_world.trace_bsp_point((-2., 0., 0.))
        with self.assertRaises(ValueError):
            self.world.trace_bsp_point((-2., 0., 0.))
        self.assertFalse(self.report.exists())

    def test_private_json_report_no_overwrite_no_retail_map_access(self):
        doc = self.world.trace_bsp_point((-2.,0.,0.))
        result = self.world.save_bsp_diagnostic_report(doc, self.report)
        self.assertEqual(result["status"], "private-read-only-diagnostic-saved")
        self.assertEqual(json.loads(self.report.read_text())["source_sha256"],
                         hashlib.sha256(self.original).hexdigest())
        with self.assertRaises(ValueError):
            self.world.save_bsp_diagnostic_report(doc, self.report)
        for path in (
            self.root / "Other" / "Content" / "DX2" / "Maps" / "research.json",
            self.source.parent / "research.json",
            self.root / "bad.gmp",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.world.save_bsp_diagnostic_report(doc, path)
        forged = {**doc, "point_to_leaf_verified": True}
        with self.assertRaises(ValueError):
            self.world.save_bsp_diagnostic_report(
                forged, self.root / "Another" / "forged.json")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_pure_trace_rejects_too_many_ambiguous_endpoints(self):
        # Deliberately overspecified rooted binary hypothesis, every plane
        # coincident with the point. Refusal protects bounded JSON outputs.
        n = 127
        nodes = [{
            "plane": (1.,0.,0.,0.),
            "negative": 2*i+1 if 2*i+1 < n else -1,
            "positive": 2*i+2 if 2*i+2 < n else -1,
            "coplanar": -1,
            "zone_a": 0, "zone_b": 1,
            "subtree_zone_mask": 2,
        } for i in range(n)]
        with self.assertRaisesRegex(ValueError, "64 diagnostic endpoints"):
            _trace({"nodes":nodes,"zone_count":2}, (0.,0.,0.), .01)

    def test_extracted_source_release_bsp_cli_without_retail_data(self):
        archive = self.root / "sdk-v09.zip"
        build(ROOT, archive)
        with ZipFile(archive) as zipf:
            names = zipf.namelist()
            self.assertIn(f"{ARCHIVE}/dx2sdk/bsp_trace.py", names)
            self.assertIn(
                f"{ARCHIVE}/research/dx2/inspect_world_bsp_zone_relations.py", names)
            zipf.extractall(self.root / "Extracted")
        sdk = self.root / "Extracted" / ARCHIVE
        a = self.cli(
            "bsp-trace-point", "--map", str(self.source),
            "--x", "-2", "--y", "3", "--z", "4",
            "--epsilon", ".01", cwd=sdk)
        self.assertEqual(a.returncode, 0, a.stdout + a.stderr)
        self.assertEqual(json.loads(a.stdout)["candidate_terminal_count"], 1)
        b = self.cli(
            "bsp-light-regions", "--map", str(self.source),
            "--limit", "1", "--output", str(self.report), cwd=sdk)
        self.assertEqual(b.returncode, 0, b.stdout + b.stderr)
        self.assertEqual(json.loads(b.stdout)["status"],
                         "private-read-only-diagnostic-saved")
        self.assertFalse(json.loads(self.report.read_text())["native_light_creation_enabled"])
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
