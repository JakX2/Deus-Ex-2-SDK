"""DX2SDK v0.11 synthetic source-authored Level Actor Region atlas tests.

Uses only locally invented UE95 GMP, Level/Model/Light actors. Cross-class
Region observation deliberately contains two contradictory original values.
No retail game, proprietary package contents or runtime engine test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dx2sdk import DX2Map
from dx2sdk.actor_regions import SCHEMA, _group_regions
from test_dx2sdk_bsp_trace import synthetic_map_with_bsp_and_light
from test_dx2sdk_bsp_anchors import _add_second_original_light
from tools.build_dx2sdk_source_release import ARCHIVE, build
from upkg import Package
from upkgwrite import ActorEdit, ImportEntry, PackageWriter


def mixed_original_region_fixture(path: Path, *, second_region: bool = True) -> bytes:
    """Two original Level actors, second StaticMeshActor with conflicting Region."""
    _add_second_original_light(path, leaf=23, zone=9)
    t3 = Package(path)
    writer = PackageWriter(t3)
    import_name = writer.name_index("StaticMeshActor")
    class_index = writer.name_index("Class")
    writer.imports.append(ImportEntry(
        0, class_index, 0, import_name, (b"", b"", b"")))
    second = writer.exports[5]
    second.class_ref = -len(writer.imports)
    if not second_region:
        actor = ActorEdit(writer, writer.export_view(5))
        before = len(actor.layout.props.tags)
        actor.layout.props.tags = [
            prop for prop in actor.layout.props.tags if prop.name != "Region"]
        if len(actor.layout.props.tags) == before:
            raise RuntimeError("Missing original synthetic Region to remove")
        actor.changes.append("omit second original Region for read-only coverage test")
        if not actor.commit():
            raise RuntimeError("Failed to omit test Region")
    raw = writer.write()
    path.write_bytes(raw)
    check = Package(path)
    assert check.export_class(check.exports[0]) == "Light"
    assert check.export_class(check.exports[5]) == "StaticMeshActor"
    assert check.level_actors() == [1, 6]
    return raw


class OriginalActorRegionAtlasTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_v011_region_atlas_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "Original" / "M1_Atlas.gmp"
        self.source.parent.mkdir()
        self.original = synthetic_map_with_bsp_and_light(self.source)
        self.world = DX2Map.open(self.source)
        self.private = self.root / "Private" / "native-regions.json"

    def cli(self, *args, cwd=ROOT):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=cwd, text=True, capture_output=True, timeout=90)

    def test_original_light_region_is_read_and_model_branch_only_hypothetical(self):
        doc = self.world.original_actor_region_bsp_atlas()
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["original_level_actor_members"], 1)
        self.assertEqual(doc["class_filtered_level_members"], 1)
        self.assertEqual(doc["eligible_explicit_original_region_actors"], 1)
        self.assertEqual(doc["sampled_explicit_region_actors"], 1)
        self.assertEqual(doc["actor_classes_in_filtered_level_members"], {"Light":1})
        row = doc["source_original_actor_observations"][0]
        self.assertEqual(row["source_actor_export"], 1)
        self.assertEqual(row["original_actor"], "Light__0")
        self.assertEqual(row["original_actor_class"], "Light")
        self.assertEqual(row["original_Region_iLeaf"], 20)
        self.assertEqual(row["original_Region_ZoneNumberLow"], 8)
        self.assertEqual(row["original_LevelInfo_export"], 3)
        self.assertEqual(row["original_Region_Zone_LevelInfo_export"], 3)
        self.assertEqual(row["classification"], "single-terminal-stable-across-epsilons")
        self.assertEqual(row["single_terminal_key_if_stable"], "node:2:missing-positive")
        self.assertFalse(doc["point_to_leaf_verified"])
        self.assertFalse(doc["point_to_zone_verified"])
        self.assertFalse(doc["native_Light_actor_spawn_enabled"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_authored_cross_class_conflict_is_kept_even_on_stable_terminal(self):
        original = mixed_original_region_fixture(self.source)
        world = DX2Map.open(self.source)
        doc = world.original_actor_region_bsp_atlas(limit=2)
        self.assertEqual(doc["original_level_actor_members"], 2)
        self.assertEqual(doc["eligible_explicit_original_region_actors"], 2)
        self.assertEqual(doc["sampled_explicit_region_actors"], 2)
        self.assertEqual(doc["actor_classes_in_filtered_level_members"],
                         {"Light":1,"StaticMeshActor":1})
        self.assertEqual(doc["group_count"], 1)
        self.assertEqual(doc["group_count_with_conflicting_source_Region"], 1)
        self.assertEqual(doc["group_count_with_multiple_native_actor_classes"], 1)
        group = doc["hypothetical_terminal_groups"][0]
        self.assertEqual(group["original_actor_exports"], [1,6])
        self.assertEqual(group["authored_classes"], {"Light":1,"StaticMeshActor":1})
        self.assertTrue(group["original_iLeaf_conflict"])
        self.assertTrue(group["original_zone_number_low_conflict"])
        self.assertTrue(group["multi_class_observations"])
        self.assertEqual(group["original_region_pairs"], [
            {"iLeaf":20,"ZoneNumberLow":8},
            {"iLeaf":23,"ZoneNumberLow":9}])
        self.assertFalse(group["native_point_to_Region_equivalence_verified"])
        queried = world.compare_point_to_original_actor_regions(
            (250.,200.,300.), limit=2)
        self.assertEqual(len(queried["overlapping_existing_actor_terminal_groups"]),1)
        self.assertIsNone(queried["new_point_Region_iLeaf"])
        self.assertIsNone(queried["new_point_Region_ZoneNumberLow"])
        exact = world.compare_point_to_original_actor_regions(
            (100.,200.,300.), limit=2)
        self.assertEqual(len(exact["exact_coordinate_matches_to_original_actors"]),2)
        self.assertIsNone(exact["new_point_Region_iLeaf"])
        cls_only = world.original_actor_region_bsp_atlas(
            actor_class="StaticMeshActor", limit=2)
        self.assertEqual(cls_only["eligible_explicit_original_region_actors"],1)
        self.assertEqual(cls_only["sampled_explicit_region_actors"],1)
        self.assertEqual(cls_only["original_level_actor_members"],2)
        self.assertEqual(cls_only["actor_classes_in_filtered_level_members"],
                         {"StaticMeshActor":1})
        cls_empty = world.original_actor_region_bsp_atlas(
            actor_class="Engine.Actor", limit=2)
        self.assertEqual(cls_empty["eligible_explicit_original_region_actors"],0)
        self.assertEqual(cls_empty["group_count"],0)
        self.assertEqual(self.source.read_bytes(),original)

    def test_source_missing_region_excluded_with_count_not_invented(self):
        original = mixed_original_region_fixture(self.source, second_region=False)
        world = DX2Map.open(self.source)
        report = world.original_actor_region_bsp_atlas(limit=2)
        self.assertEqual(report["class_filtered_level_members"],2)
        self.assertEqual(report["eligible_explicit_original_region_actors"],1)
        self.assertEqual(
            report["excluded_authored_region_actors"][
                "missing_or_unusable_explicit_Region_or_source_links"], 1)
        self.assertEqual(report["sampled_explicit_region_actors"],1)
        only_second = world.original_actor_region_bsp_atlas(
            actor_class="StaticMeshActor")
        self.assertEqual(only_second["eligible_explicit_original_region_actors"],0)
        self.assertEqual(only_second["sampled_explicit_region_actors"],0)
        self.assertEqual(self.source.read_bytes(),original)

    def test_ambiguous_query_never_extrapolates_original_region(self):
        report = self.world.compare_point_to_original_actor_regions(
            (0.,0.,0.))
        self.assertEqual(
            report["candidate_point_sweep"]["classification"],"ambiguous-plane-fork")
        self.assertIsNone(report["new_point_Region_iLeaf"])
        self.assertIsNone(report["new_point_Region_ZoneNumberLow"])
        self.assertFalse(report["gameplay_runtime_verified"])

    def test_pure_cross_class_grouping_and_duplicate_export_refusal(self):
        base = self.world.original_actor_region_bsp_atlas()[
            "source_original_actor_observations"][0]
        another = {**base,"source_actor_export":6,
                   "original_actor_class":"StaticMeshActor",
                   "original_Region_iLeaf":21,
                   "original_Region_ZoneNumberLow":8}
        groups = _group_regions([base,another])
        self.assertEqual(groups[0]["original_actor_count"],2)
        self.assertTrue(groups[0]["original_iLeaf_conflict"])
        self.assertFalse(groups[0]["original_zone_number_low_conflict"])
        with self.assertRaises(ValueError):
            _group_regions([base,base])
        with self.assertRaises(ValueError):
            _group_regions([base,{**another,"classification":"ambiguous-plane-fork"}])

    def test_reject_invalid_class_limit_epsilon_and_point(self):
        for bad in ("",True,3,"x"*129):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.world.original_actor_region_bsp_atlas(actor_class=bad)
        for bad in (True,0,1001,None,-5):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.world.original_actor_region_bsp_atlas(limit=bad)
        for bad in ([.1,.01],[.01],[True,.1],[.01,float("inf")]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.world.original_actor_region_bsp_atlas(epsilons=bad)
        for bad in ((float("nan"),0.,0.),(1000001,0,0),("x",0,0)):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.world.compare_point_to_original_actor_regions(bad)
        self.assertFalse(self.private.exists())

    def test_private_json_replay_tampering_and_game_paths_refused(self):
        doc = self.world.original_actor_region_bsp_atlas()
        ret = self.world.save_original_actor_region_atlas(doc,self.private)
        self.assertEqual(ret["status"],
                         "private-replayed-original-Actor-Region-JSON-written")
        self.assertEqual(json.loads(self.private.read_text()),doc)
        with self.assertRaises(ValueError):
            self.world.save_original_actor_region_atlas(doc,self.private)
        for bad in (
            self.source.parent / "local" / "regions.json",
            self.root / "Content" / "DX2" / "Maps" / "regions.json",
            self.root / "wrong.gmp",
        ):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.world.save_original_actor_region_atlas(doc,bad)
        for edits in (
            {"point_to_leaf_verified":True},
            {"native_Light_actor_spawn_enabled":True},
            {"group_count_with_conflicting_source_Region":40},
            {"source_original_actor_observations":[]},
            {"source_sha256":"0"*64},
            {"status":"forged"},
        ):
            with self.subTest(edits=edits),self.assertRaises(ValueError):
                self.world.save_original_actor_region_atlas(
                    {**doc,**edits},self.root/"Private"/"forged.json")
        point = self.world.compare_point_to_original_actor_regions((250.,200.,300.))
        saved = self.world.save_original_actor_region_atlas(
            point, self.root/"Private"/"point.json")
        self.assertTrue(Path(saved["output"]).exists())
        with self.assertRaises(ValueError):
            self.world.save_original_actor_region_atlas(
                {**point,"new_point_Region_ZoneNumberLow":8},
                self.root/"Private"/"forged-point.json")
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_stale_original_source_refused_even_with_cached_atlas(self):
        doc = self.world.original_actor_region_bsp_atlas()
        self.source.write_bytes(self.original + b"tamper")
        with self.assertRaises(ValueError):
            self.world.original_actor_region_bsp_atlas()
        with self.assertRaises(ValueError):
            self.world.save_original_actor_region_atlas(doc,self.private)
        self.assertFalse(self.private.exists())

    def test_extracted_portable_source_cli_covers_class_filter_and_private_json(self):
        archive=self.root/"v011.zip"
        build(ROOT,archive)
        with ZipFile(archive) as zipf:
            self.assertIn(f"{ARCHIVE}/dx2sdk/actor_regions.py",zipf.namelist())
            zipf.extractall(self.root/"Unpacked")
        sdk=self.root/"Unpacked"/ARCHIVE
        result=self.cli("bsp-actor-regions","--map",str(self.source),
                        "--class","Light","--limit","1",
                        "--epsilon","0.001","--epsilon","0.01",
                        "--epsilon","0.1",cwd=sdk)
        self.assertEqual(result.returncode,0,result.stderr)
        doc=json.loads(result.stdout)
        self.assertEqual(doc["sampled_explicit_region_actors"],1)
        self.assertEqual(doc["source_actor_class_filter"],"Light")
        self.assertFalse(doc["point_to_leaf_verified"])
        result=self.cli("bsp-compare-actor-regions","--map",str(self.source),
                        "--x","250","--y","200","--z","300",
                        "--output",str(self.private),cwd=sdk)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"],
                         "private-replayed-original-Actor-Region-JSON-written")
        self.assertIsNone(json.loads(self.private.read_text())["new_point_Region_iLeaf"])
        self.assertEqual(self.source.read_bytes(),self.original)


if __name__=="__main__":
    unittest.main()
