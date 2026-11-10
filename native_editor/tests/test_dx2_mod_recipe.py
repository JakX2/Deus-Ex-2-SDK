"""Asset-free tests for portable, source-SHA-pinned DX2 static prop mod recipes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for folder in (
    ROOT / "native_editor/tests",
    ROOT / "native_editor/package_writer",
    ROOT / "third_party/t3sdk_assets",
):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from dx2_mod_recipe import SCHEMA, export_recipe, read_recipe, reconstruct
from dx2_native_prop_plan import SCHEMA as PLAN_SCHEMA, compile_in_memory


class PortableNativePropRecipeTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "Original" / "M1_RecipeExample.gmp"
        self.source.parent.mkdir(parents=True)
        initial = level_fixture(self.source)
        _, prepared = clone_in_memory(
            self.source, source_sha256=hashlib.sha256(initial).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            delta=(100.0, 0.0, 0.0))
        self.source.write_bytes(prepared)
        self.original = self.source.read_bytes()
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.plan = {
            "schema": PLAN_SCHEMA,
            "moves": [{"actor": "StaticMeshActor__1", "export": 1,
                       "delta": [20.0, 0.0, 0.0]}],
            "copies": [{"actor": "StaticMeshActor__1", "export": 1,
                        "delta": [50.0, 10.0, 0.0]}],
            "unplaces": [],
        }
        self.recipe = self.root / "Shared" / "TestLayout.dx2edmod.json"
        self.output = self.root / "Isolated" / self.source.name

    def _export(self):
        return export_recipe(
            self.source, self.recipe, source_sha256=self.sha, plan=self.plan)

    def test_recipe_contains_only_authoring_metadata_no_proprietary_map(self):
        result = self._export()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertFalse(result["includes_retail_assets"])
        self.assertFalse(result["gmp_output_written"])
        self.assertFalse(result["game_installation_modified"])
        self.assertEqual(result["status"], "source-verified-mod-recipe-created")
        self.assertTrue(self.recipe.exists())
        self.assertFalse(self.output.exists())
        doc = read_recipe(self.recipe)
        self.assertEqual(doc["source_file"], self.source.name)
        self.assertEqual(doc["source_sha256"], self.sha)
        self.assertEqual(doc["source_size"], len(self.original))
        self.assertEqual(doc["operation_counts"],
                         {"moves": 1, "copies": 1, "unplaces": 0})
        self.assertFalse(doc["includes_retail_assets"])
        self.assertFalse(doc["automatic_game_installation"])
        self.assertNotIn(str(self.source), self.recipe.read_text("utf-8"))
        self.assertLess(self.recipe.stat().st_size, 4096)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_reconstruct_read_only_and_apply_to_new_isolated_gmp(self):
        self._export()
        trial = reconstruct(self.source, self.recipe)
        self.assertFalse(trial["gmp_output_written"])
        self.assertFalse(self.output.exists())
        result = reconstruct(self.source, self.recipe, output=self.output)
        self.assertEqual(result["status"],
                         "isolated-GMP-rebuilt-from-portable-recipe-runtime-unverified")
        self.assertTrue(result["all_candidate_bytes_replayed"])
        self.assertFalse(result["runtime_game_verified"])
        self.assertFalse(result["game_installation_modified"])
        expected, raw = compile_in_memory(
            self.source, source_sha256=self.sha, plan=self.plan)
        self.assertEqual(self.output.read_bytes(), raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result["candidate_sha256"])
        self.assertTrue(self.output.with_suffix(".dx2ed-native-prop-plan.json").exists())
        self.assertEqual(self.source.read_bytes(), self.original)
        with self.assertRaises(FileExistsError):
            reconstruct(self.source, self.recipe, output=self.output)

    def test_recipe_copy_is_reproducible_on_second_copy_of_same_source(self):
        self._export()
        other = self.root / "OtherOwner" / self.source.name
        other.parent.mkdir(parents=True)
        other.write_bytes(self.original)
        result = reconstruct(other, self.recipe)
        self.assertEqual(result["candidate_sha256"],
                         read_recipe(self.recipe)["candidate_sha256"])
        self.assertFalse(result["gmp_output_written"])

    def test_refuse_modified_source_wrong_basename_and_malicious_hash(self):
        self._export()
        for bad in (
            self.root / "OtherOwner" / self.source.name,
            self.root / "OtherOwner" / "WrongMap.gmp",
        ):
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_bytes(self.original + b"test corruption")
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    ValueError, "basename|SHA/size"):
                reconstruct(bad, self.recipe)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuse_forged_plan_or_checksum_even_if_recipe_is_rewritten(self):
        self._export()
        original_doc = json.loads(self.recipe.read_text())
        modifications = [
            {"candidate_sha256": "f" * 64},
            {"native_plan": {
                **original_doc["native_plan"],
                "moves": [{"actor": "StaticMeshActor__1", "export": 1,
                           "delta": [21.0, 0.0, 0.0]}]}},
            {"operation_counts": {"moves": 0, "copies": 1, "unplaces": 0}},
            {"includes_retail_assets": True},
            {"automatic_game_installation": True},
            {"runtime_game_verified": True},
            {"source_file": "../M1_RecipeExample.gmp"},
            {"source_sha256": "0" * 64},
            {"unknown_field": "unsupported"},
        ]
        for patch in modifications:
            with self.subTest(patch=patch):
                self.recipe.write_text(json.dumps({**original_doc, **patch}))
                with self.assertRaises(ValueError):
                    reconstruct(self.source, self.recipe)
        self.recipe.write_text(json.dumps(original_doc))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_refuse_unsafe_recipe_and_gmp_paths_without_overwriting(self):
        for file in (
            self.root / "Bad.json",
            self.source.parent / "Original.dx2edmod.json",
            self.source.parent / "nested" / "Original.dx2edmod.json",
            self.root / "Content" / "DX2" / "Maps" / "Original.dx2edmod.json",
        ):
            with self.subTest(file=file), self.assertRaises(ValueError):
                export_recipe(self.source, file, source_sha256=self.sha,
                              plan=self.plan)
        self._export()
        with self.assertRaises(FileExistsError):
            self._export()
        for file in (
            self.source,
            self.source.parent / "nested" / self.source.name,
            self.root / "Content" / "DX2" / "Maps" / self.source.name,
            self.root / "wrong.gmp",
        ):
            with self.subTest(file=file), self.assertRaises((ValueError, FileExistsError)):
                reconstruct(self.source, self.recipe, output=file)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_json_cli_export_check_and_rebuild(self):
        tool = ROOT / "native_editor" / "package_writer" / "dx2_mod_recipe.py"
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(self.plan))
        export = subprocess.run([
            sys.executable, str(tool), str(self.source),
            "--source-sha256", self.sha,
            "--plan-json", str(plan_path),
            "--export-recipe", str(self.recipe),
        ], capture_output=True, text=True)
        self.assertEqual(export.returncode, 0, export.stdout + export.stderr)
        self.assertFalse(json.loads(export.stdout)["gmp_output_written"])
        check = subprocess.run([
            sys.executable, str(tool), str(self.source),
            "--recipe", str(self.recipe),
        ], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)["status"],
                         "recipe-recompiled-runtime-unverified")
        rebuilt = subprocess.run([
            sys.executable, str(tool), str(self.source),
            "--recipe", str(self.recipe), "--output", str(self.output)
        ], capture_output=True, text=True)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout + rebuilt.stderr)
        self.assertTrue(json.loads(rebuilt.stdout)["all_candidate_bytes_replayed"])
        refused = subprocess.run([
            sys.executable, str(tool), str(self.source),
            "--recipe", str(self.recipe), "--output", str(self.source),
        ], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)["status"], "refused")
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
