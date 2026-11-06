"""Asset-free source Light / hypothetical BSP terminal atlas regression.

Synthetic UE95 Model, Level and original native Light actors. No game bytes,
art, textures, compiled scripts, runtime binaries or retail test fixtures.
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
from dx2sdk import DX2Map
from dx2sdk.bsp_anchors import (
    SCHEMA, _epsilons, _groups, DEFAULT_EPSILONS,
)
from test_dx2sdk_bsp_trace import synthetic_map_with_bsp_and_light
from tools.build_dx2sdk_source_release import ARCHIVE, build
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter, parse_fields, enc_index


def _add_second_original_light(path: Path, *, leaf: int = 21, zone: int = 9) -> bytes:
    """Add a second *authored* Light to an invented native Level actor list."""
    pkg = Package(path)
    writer = PackageWriter(pkg)
    model_ref = next(x.index + 1 for x in pkg.exports
                     if pkg.export_class(x) == "Model")
    light = writer.add_export(0, "Light__second", writer.object_data(0))
    exp = writer.export_view(light)
    edit = ActorEdit(writer, exp)
    region = next(x for x in edit.layout.props.tags if x.name == "Region")
    fields = {x.name: x for x in parse_fields(region, writer.name_text).tags}
    fields["iLeaf"].value = struct.pack("<i", leaf)
    fields["ZoneNumberLow"].value = bytes([zone])
    edit.changes.append("invented second original Light Region evidence")
    if not edit.commit():
        raise RuntimeError("Synthetic actor fixture was not committed")
    # Original synthetic FURL has four empty string tokens, zero URL
    # options, port=7777, valid=1, and native Model export ref.
    level = (bytes(13) + struct.pack("<II", 2, 2) +
             enc_index(1) + enc_index(light + 1) +
             bytes(5) + struct.pack("<II", 7777, 1) +
             enc_index(model_ref))
    writer.set_object(1, level)
    data = writer.write()
    path.write_bytes(data)
    reread = Package(path)
    if reread.level_actors() != [1, light + 1]:
        raise RuntimeError("Synthetic extra Light Level membership mismatch")
    return data


class OriginalBSPAnchorAtlasTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2sdk_bsp_atlas_v010_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "Original" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        self.original = synthetic_map_with_bsp_and_light(self.source)
        self.world = DX2Map.open(self.source)
        self.output = self.root / "Private" / "source_atlas.json"

    def cli(self, *args, cwd=ROOT):
        return subprocess.run([sys.executable, "-B", "-m", "dx2sdk", *args],
                              cwd=cwd, text=True, capture_output=True, timeout=100)

    def test_one_original_light_has_stable_candidate_not_proven_region(self):
        doc = self.world.original_light_bsp_anchor_atlas(limit=1)
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["source_original_native_light_count"], 1)
        self.assertEqual(doc["sampled_existing_native_lights"], 1)
        self.assertEqual(doc["stable_single_terminal_source_lights"], 1)
        self.assertEqual(doc["ambiguous_source_light_candidate_paths"], 0)
        self.assertEqual(doc["epsilon_sensitive_source_lights"], 0)
        self.assertEqual(doc["hypothetical_terminal_group_count"], 1)
        self.assertEqual(doc["hypothetical_terminal_groups_with_original_Region_conflicts"], 0)
        sample = doc["source_lights"][0]
        self.assertEqual(sample["original_actor"], "Light__0")
        self.assertEqual(sample["original_Region_iLeaf"], 20)
        self.assertEqual(sample["original_Region_ZoneNumberLow"], 8)
        self.assertEqual(sample["classification"], "single-terminal-stable-across-epsilons")
        self.assertEqual(len(sample["candidate_sweeps"]), 3)
        self.assertEqual(sample["single_terminal_key_if_stable"],
                         "node:2:missing-positive")
        group = doc["source_terminal_groups"][0]
        self.assertEqual(group["original_native_light_exports"], [1])
        self.assertEqual(group["observed_original_Region_pairs_on_existing_Lights"],
                         [{"iLeaf":20, "ZoneNumberLow":8}])
        self.assertFalse(group["native_leaf_or_zone_inference_supported"])
        self.assertFalse(doc["native_Region_iLeaf_solver_verified"])
        self.assertFalse(doc["native_Region_ZoneNumberLow_solver_verified"])
        self.assertFalse(doc["native_new_Light_actor_creation_enabled"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_arbitrary_point_overlap_never_predicts_native_region(self):
        new_point = (250., 200., 300.)
        report = self.world.compare_point_with_original_light_anchors(new_point)
        self.assertEqual(report["status"],
                         "read-only-point-vs-original-Light-terminal-observations")
        self.assertEqual(report["point_unreal_xyz"], list(new_point))
        self.assertEqual(report["candidate_point_sweep"]["classification"],
                         "single-terminal-stable-across-epsilons")
        self.assertEqual(len(report["overlapping_existing_Light_terminal_groups"]), 1)
        self.assertEqual(report["identical_coordinates_of_existing_original_Lights"], [])
        self.assertIsNone(report["point_native_Region_iLeaf_assignment"])
        self.assertIsNone(report["point_native_Region_ZoneNumberLow_assignment"])
        self.assertFalse(report["native_Region_iLeaf_solver_verified"])
        known = self.world.compare_point_with_original_light_anchors((100., 200., 300.))
        self.assertEqual(len(known["identical_coordinates_of_existing_original_Lights"]), 1)
        self.assertEqual(known["identical_coordinates_of_existing_original_Lights"][0]
                         ["existing_original_Region_iLeaf"], 20)
        self.assertIsNone(known["point_native_Region_iLeaf_assignment"])
        other = self.world.compare_point_with_original_light_anchors((-3., 0., 5.))
        self.assertEqual(other["overlapping_existing_Light_terminal_groups"], [])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_source_authored_region_conflicts_are_reported_not_smoothed(self):
        changed_source = _add_second_original_light(self.source, leaf=23, zone=9)
        world = DX2Map.open(self.source)
        report = world.original_light_bsp_anchor_atlas(limit=2)
        self.assertEqual(report["source_original_native_light_count"], 2)
        self.assertEqual(report["stable_single_terminal_source_lights"], 2)
        self.assertEqual(report["hypothetical_terminal_group_count"], 1)
        self.assertEqual(report["hypothetical_terminal_groups_with_original_Region_conflicts"], 1)
        group = report["source_terminal_groups"][0]
        self.assertTrue(group["conflicting_original_iLeaf"])
        self.assertTrue(group["conflicting_original_zone_number_low"])
        self.assertTrue(group["multiple_authored_Region_pairs_at_same_hypothetical_terminal"])
        self.assertEqual(group["original_native_light_exports"], [1, 6])
        self.assertEqual(group["observed_original_Region_pairs_on_existing_Lights"],
                         [{"iLeaf":20, "ZoneNumberLow":8},
                          {"iLeaf":23, "ZoneNumberLow":9}])
        report2 = world.compare_point_with_original_light_anchors((250.,200.,300.), limit=2)
        observed = report2["overlapping_existing_Light_terminal_groups"]
        self.assertTrue(observed[0]["multiple_authored_Region_pairs_at_same_hypothetical_terminal"])
        self.assertIsNone(report2["point_native_Region_ZoneNumberLow_assignment"])
        self.assertEqual(self.source.read_bytes(), changed_source)

    def test_near_plane_query_forks_and_must_remain_ambiguous(self):
        report = self.world.compare_point_with_original_light_anchors((0.,0.,0.))
        query = report["candidate_point_sweep"]
        self.assertEqual(query["classification"], "ambiguous-plane-fork")
        self.assertIsNone(query["single_terminal_key_if_stable"])
        self.assertTrue(all(x["candidate_terminal_count"] > 1
                            for x in query["candidate_sweeps"]))
        self.assertIsNone(report["point_native_Region_iLeaf_assignment"])
        self.assertFalse(report["native_new_Light_actor_creation_enabled"])

    def test_pure_grouping_flags_conflicts_and_rejects_fake_stable_samples(self):
        sample = self.world.original_light_bsp_anchor_atlas()["source_lights"][0]
        replica = {**sample, "source_actor_export": 2,
                   "original_Region_iLeaf": 21,
                   "original_Region_ZoneNumberLow": 8}
        groups = _groups([sample, replica])
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]["conflicting_original_iLeaf"])
        self.assertFalse(groups[0]["conflicting_original_zone_number_low"])
        with self.assertRaises(ValueError):
            _groups([sample,sample])
        with self.assertRaises(ValueError):
            _groups([sample,{**replica, "classification":"ambiguous-plane-fork"}])
        with self.assertRaises(ValueError):
            _groups([sample,{**replica, "original_Region_iLeaf":False}])

    def test_strict_epsilons_limit_and_nonfinite_point_refusals(self):
        for eps in (
            None, [], [.01], [.01,.01], [.1,.01],
            [True,.01], [float("nan"),.01], [.0,.01],
            [.001,.01,.1,1.01], list(range(6)),
        ):
            with self.subTest(eps=eps), self.assertRaises(ValueError):
                self.world.original_light_bsp_anchor_atlas(epsilons=eps)
        self.assertEqual(_epsilons([.00001,1.]), (.00001,1.))
        for limit in (False,0,1001,2.5,None):
            with self.subTest(limit=limit),self.assertRaises(ValueError):
                self.world.original_light_bsp_anchor_atlas(limit=limit)
        for point in ([0.,0.], [True,0,0],
                      [float("inf"),0,0], [1000001,0,0]):
            with self.subTest(point=point), self.assertRaises(ValueError):
                self.world.compare_point_with_original_light_anchors(point)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_private_json_exact_source_replay_rejects_forgery_and_bad_paths(self):
        doc = self.world.original_light_bsp_anchor_atlas(limit=1)
        result = self.world.save_light_bsp_anchor_report(doc, self.output)
        self.assertEqual(result["status"], "private-source-replayed-BSP-atlas-JSON-written")
        self.assertEqual(json.loads(self.output.read_text()), doc)
        with self.assertRaises(ValueError):
            self.world.save_light_bsp_anchor_report(doc, self.output)
        for unsafe in (
            self.source.parent / "nested" / "bad.json",
            self.root / "Game" / "Content" / "DX2" / "Maps" / "bad.json",
            self.root / "wrong.gmp",
        ):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                self.world.save_light_bsp_anchor_report(doc, unsafe)
        for changes in (
            {"stable_single_terminal_source_lights":99},
            {"native_Region_iLeaf_solver_verified":True},
            {"native_Region_ZoneNumberLow_solver_verified":True},
            {"native_new_Light_actor_creation_enabled":True},
            {"source_terminal_groups":[]},
            {"status":"forged"},
            {"source_sha256":"0"*64},
        ):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.world.save_light_bsp_anchor_report(
                    {**doc,**changes},self.root/"Private"/"forged.json")
        comparison = self.world.compare_point_with_original_light_anchors(
            (250.,200.,300.), limit=1)
        with self.assertRaises(ValueError):
            self.world.save_light_bsp_anchor_report(
                {**comparison,"point_native_Region_ZoneNumberLow_assignment":8},
                self.root/"Private"/"forged-comparison.json")
        good_comp = self.world.save_light_bsp_anchor_report(
            comparison, self.root/"Private"/"comparison.json")
        self.assertEqual(good_comp["status"],
                         "private-source-replayed-BSP-atlas-JSON-written")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_source_changed_since_open_is_refused(self):
        doc = self.world.original_light_bsp_anchor_atlas(limit=1)
        self.source.write_bytes(self.original + b"tampered")
        with self.assertRaises(ValueError):
            self.world.original_light_bsp_anchor_atlas()
        with self.assertRaises(ValueError):
            self.world.save_light_bsp_anchor_report(doc, self.output)
        self.assertFalse(self.output.exists())

    def test_extracted_standalone_linux_windows_cli_surface(self):
        archive = self.root / "sdk-v010.zip"
        build(ROOT, archive)
        with ZipFile(archive) as z:
            self.assertIn(f"{ARCHIVE}/dx2sdk/bsp_anchors.py", z.namelist())
            z.extractall(self.root / "Extracted")
        sdk = self.root / "Extracted" / ARCHIVE
        sample = self.cli("bsp-light-atlas", "--map", str(self.source),
                          "--limit","1","--epsilon",".001","--epsilon",".01",
                          "--epsilon",".1", cwd=sdk)
        self.assertEqual(sample.returncode, 0, sample.stderr)
        parsed = json.loads(sample.stdout)
        self.assertEqual(parsed["stable_single_terminal_source_lights"],1)
        self.assertFalse(parsed["native_Region_iLeaf_solver_verified"])
        query = self.cli(
            "bsp-compare-point", "--map", str(self.source),
            "--x","250", "--y","200", "--z","300",
            "--limit","1", "--output",str(self.output), cwd=sdk)
        self.assertEqual(query.returncode, 0, query.stderr)
        self.assertEqual(json.loads(query.stdout)["status"],
                         "private-source-replayed-BSP-atlas-JSON-written")
        self.assertEqual(json.loads(self.output.read_text())["point_native_Region_iLeaf_assignment"],None)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
