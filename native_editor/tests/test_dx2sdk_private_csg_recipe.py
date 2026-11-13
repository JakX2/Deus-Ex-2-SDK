"""Source-isolated P103 private CSG recipe write/replay tests."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dx2sdk.private_csg_recipe import (
    SCHEMA, make_private_csg_recipe,
    write_private_csg_recipe, read_private_csg_recipe,
)


def box(size=(2., 2., 2.), distance=0.):
    return {
        "kind": "Box", "size": list(size), "steps": 1,
        "clip_plane": {
            "normal": [1., 0., 0.], "distance": distance,
            "keep_positive": False,
        },
    }


def pose(x=0., y=0., z=0.):
    return {
        "basis": [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
        "origin": [x, y, z],
    }


class PrivateCSGRecipeTests(unittest.TestCase):
    def setUp(self):
        self.a = box()
        self.b = box()
        self.ta = pose()
        self.tb = pose(.5)

    def test_new_file_roundtrip_exact_recomputed_result_and_stable_digest(self):
        original = (deepcopy(self.a), deepcopy(self.b),
                    deepcopy(self.ta), deepcopy(self.tb))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/"cut.dx2csg.json"
            created = write_private_csg_recipe(
                self.a, self.b, self.ta, self.tb, "subtraction",
                "DraftProp_1", "DraftProp_2", path)
            recipe, regenerated = read_private_csg_recipe(path)
            self.assertEqual(recipe["schema"], SCHEMA)
            self.assertEqual(created["computed_result_sha256"],
                             recipe["computed_result_sha256"])
            self.assertEqual(recipe["piece_count"], 1)
            self.assertAlmostEqual(recipe["remaining_volume_m3"], 2.)
            self.assertAlmostEqual(regenerated["remaining_volume_m3"], 2.)
            self.assertEqual(regenerated["piece_count"], 1)
            self.assertEqual(regenerated["original_gmp_or_ibd_modified"], False)
            self.assertEqual(recipe["read_only_source"], True)
            self.assertEqual(recipe["native_world_bsp_writer_enabled"], False)
            self.assertEqual(recipe["native_havok_mopp_collision_enabled"], False)
            self.assertEqual(recipe["retail_game_runtime_verified"], False)
            first = path.read_bytes()
            self.assertLess(len(first), 256*1024)
            with self.assertRaises(ValueError):
                write_private_csg_recipe(
                    self.a, self.b, self.ta, self.tb, "subtraction",
                    "DraftProp_1", "DraftProp_2", path)
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(
                (self.a, self.b, self.ta, self.tb), original)

    def test_intersection_and_six_piece_cavity_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            intersect = root/"intersect.dx2csg.json"
            write_private_csg_recipe(
                self.a, self.b, self.ta, self.tb, "intersection",
                "DraftProp_1", "DraftProp_8", intersect)
            record, result = read_private_csg_recipe(intersect)
            self.assertEqual(record["piece_count"], 1)
            self.assertAlmostEqual(result["volume_m3"], 2.)
            self.assertTrue(result["has_volume"])
            cavity = root/"cavity.dx2csg.json"
            write_private_csg_recipe(
                box((4., 4., 4.), 1.0), self.b,
                self.ta, pose(-.5), "subtraction",
                "DraftProp_3", "DraftProp_4", cavity)
            record, result = read_private_csg_recipe(cavity)
            self.assertEqual(record["piece_count"], 6)
            self.assertEqual(result["piece_count"], 6)
            self.assertAlmostEqual(result["remaining_volume_m3"], 44.)
            self.assertTrue(result["volume_partition_verified"])
            self.assertTrue(result["all_pieces_individually_closed"])
            self.assertEqual(sorted(p["piece_index"] for p in result["pieces"]),
                             list(range(6)))

    def test_refuse_tampering_missing_unsafe_and_malformed_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root/"base.dx2csg.json"
            write_private_csg_recipe(
                self.a, self.b, self.ta, self.tb, "subtraction",
                "DraftProp_1", "DraftProp_2", original)
            basis = json.loads(original.read_text())
            alterations = [
                {"remaining_volume_m3": 10.0},
                {"piece_count": 6},
                {"computed_result_sha256": "f"*64},
                {"source_payload_sha256": "0"*64},
                {"operation": "intersection"},
                {"read_only_source": False},
                {"native_world_bsp_writer_enabled": True},
                {"native_havok_mopp_collision_enabled": True},
                {"retail_game_runtime_verified": True},
                {"schema": "DX2-original-BSP"},
                {"extra_game_actor": "StaticMeshActor"},
                {"source_private_a": "StaticMeshActor_1"},
            ]
            for i, changes in enumerate(alterations):
                with self.subTest(changes=changes):
                    copy = root/f"tamper_{i}.dx2csg.json"
                    record = deepcopy(basis)
                    record.update(changes)
                    copy.write_text(json.dumps(record), encoding="utf-8")
                    with self.assertRaises((ValueError, TypeError)):
                        read_private_csg_recipe(copy)
            duplicate = root/"duplicate.dx2csg.json"
            duplicate.write_text(
                '{"schema":"DX2Ed-private-CSG-recipe-v1",'
                '"schema":"DX2Ed-private-CSG-recipe-v1"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_private_csg_recipe(duplicate)
            nonfinite = root/"nan.dx2csg.json"
            nonfinite.write_text('{"schema":NaN}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_private_csg_recipe(nonfinite)
            unrelated = root/"original.gmp"
            unrelated.write_bytes(b"RETAIL_MAP_SENTINEL_UNTOUCHED")
            before = hashlib.sha256(unrelated.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                read_private_csg_recipe(unrelated)
            with self.assertRaises(ValueError):
                read_private_csg_recipe(root/"missing.dx2csg.json")
            with self.assertRaises(ValueError):
                write_private_csg_recipe(
                    self.a, self.b, self.ta, self.tb, "subtraction",
                    "DraftProp_1", "DraftProp_2", unrelated)
            parent = root/"Content"/"DX2"/"Maps"
            parent.mkdir(parents=True)
            with self.assertRaises(ValueError):
                write_private_csg_recipe(
                    self.a, self.b, self.ta, self.tb, "subtraction",
                    "DraftProp_1", "DraftProp_2", parent/"no.dx2csg.json")
            with self.assertRaises(ValueError):
                read_private_csg_recipe(parent/"not_here.dx2csg.json")
            alias = root/"alias.dx2csg.json"
            try:
                alias.symlink_to(original)
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    read_private_csg_recipe(alias)
                with self.assertRaises(ValueError):
                    write_private_csg_recipe(
                        self.a, self.b, self.ta, self.tb, "subtraction",
                        "DraftProp_1", "DraftProp_2", alias)
            self.assertEqual(
                hashlib.sha256(unrelated.read_bytes()).hexdigest(), before)
            self.assertEqual(original.read_bytes(),
                             (json.dumps(basis, sort_keys=True,
                                         separators=(",", ":"))+"\n").encode())

    def test_invalid_inputs_refused_without_new_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            name = root/"bad.dx2csg.json"
            bad_cases = [
                (self.a, self.b, self.ta, self.tb, "union",
                 "DraftProp_1", "DraftProp_2"),
                (self.a, self.b, self.ta, self.tb, "subtraction",
                 "DraftProp_1", "DraftProp_1"),
                (self.a, self.b, self.ta, self.tb, "subtraction",
                 "StaticMeshActor_1", "DraftProp_2"),
                (self.a, {"kind": "StaticMeshActor"}, self.ta, self.tb,
                 "subtraction", "DraftProp_1", "DraftProp_2"),
                ({"kind": "Box", "source_gmp": "original.gmp"},
                 self.b, self.ta, self.tb, "intersection",
                 "DraftProp_1", "DraftProp_2"),
                (self.a, self.b,
                 {"basis": [[2,0,0],[0,1,0],[0,0,1]],
                  "origin": [0,0,0]}, self.tb,
                 "subtraction", "DraftProp_1", "DraftProp_2"),
                (self.a, self.b, self.ta,
                 {"basis": self.tb["basis"], "origin": [float("nan"),0,0]},
                 "intersection", "DraftProp_1", "DraftProp_2"),
            ]
            for test in bad_cases:
                with self.subTest(test=test), self.assertRaises(
                        (ValueError, TypeError)):
                    write_private_csg_recipe(*test, name)
                self.assertFalse(name.exists())

    def test_python_cli_save_load_error_exit_no_game_file_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = []
            for i, payload in enumerate((self.a, self.b,
                                         self.ta, self.tb)):
                file = root/f"src_{i}.json"
                file.write_text(json.dumps(payload), encoding="utf-8")
                src.append(file)
            target = root/"generated.dx2csg.json"
            sentinel = root/"original.gmp"
            sentinel.write_bytes(b"IMMUTABLE_ORIGINAL_GAME_SOURCE")
            original_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            command = [sys.executable, "-m", "dx2sdk.private_csg_recipe"]
            saving = subprocess.run(
                command+["save", "subtraction", "DraftProp_1",
                         "DraftProp_2", *[str(x) for x in src], str(target)],
                capture_output=True, text=True)
            self.assertEqual(saving.returncode, 0, saving.stderr)
            self.assertEqual(json.loads(saving.stdout)["piece_count"], 1)
            before = target.read_bytes()
            loading = subprocess.run(command+["load", str(target)],
                                     capture_output=True, text=True)
            self.assertEqual(loading.returncode, 0, loading.stderr)
            report = json.loads(loading.stdout)
            self.assertEqual(report["operation"], "subtraction")
            self.assertEqual(report["result"]["piece_count"], 1)
            self.assertEqual(report["result"]["original_gmp_or_ibd_modified"],
                             False)
            repeated = subprocess.run(
                command+["save", "subtraction", "DraftProp_1",
                         "DraftProp_2", *[str(x) for x in src], str(target)],
                capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertFalse(repeated.stdout.strip())
            self.assertEqual(target.read_bytes(), before)
            refusal = subprocess.run(command+["load", str(sentinel)],
                                     capture_output=True, text=True)
            self.assertEqual(refusal.returncode, 2)
            self.assertFalse(refusal.stdout.strip())
            self.assertEqual(hashlib.sha256(sentinel.read_bytes()).hexdigest(),
                             original_hash)


if __name__ == "__main__":
    unittest.main()
