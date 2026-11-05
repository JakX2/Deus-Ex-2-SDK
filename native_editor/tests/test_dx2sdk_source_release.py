"""DX2SDK stand-alone source ZIP tests: no Godot, no game data or installs.

The same portable ZIP is later extracted by Linux and Windows CI and
tested with the real Python -m dx2sdk module. No user retail data is used.
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
from tools.build_dx2sdk_source_release import build, SCHEMA, ARCHIVE, RETAIL_EXT


class SDKStandaloneSourceReleaseTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="dx2sdk_release_source_test_")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.first = self.root / "DX2SDK_Portable_1.zip"
        self.second = self.root / "DX2SDK_Portable_2.zip"

    def test_standalone_source_zip_includes_all_runtime_modules_but_no_assets(self):
        report = build(ROOT, self.first)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["version"], "0.1.0")
        self.assertFalse(report["includes_original_dx2_assets"])
        self.assertFalse(report["gameplay_runtime_verified"])
        self.assertGreater(report["file_count"], 12)
        self.assertGreater(self.first.stat().st_size, 1000)
        with ZipFile(self.first) as z:
            names = z.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIsNone(z.testzip())
            self.assertIn(f"{ARCHIVE}/dx2sdk/api.py", names)
            self.assertIn(f"{ARCHIVE}/dx2sdk/projects.py", names)
            self.assertIn(f"{ARCHIVE}/dx2sdk/__main__.py", names)
            self.assertIn(f"{ARCHIVE}/RUN_DX2SDK.cmd", names)
            self.assertIn(f"{ARCHIVE}/third_party/t3sdk_assets/LICENSE", names)
            self.assertNotIn(f"{ARCHIVE}/runtime/Godot_v4.3-stable_win64.exe", names)
            self.assertFalse(any(Path(n).suffix.casefold() in RETAIL_EXT
                                 for n in names))
            manifest = json.loads(z.read(f"{ARCHIVE}/sdk-manifest.json"))
            self.assertFalse(manifest["includes_original_dx2_assets"])
            self.assertFalse(manifest["retail_game_runtime_tested"])
            self.assertFalse(manifest["bsp_mopp_or_native_script_writer"])
            for name, digest in manifest["source_sha256"].items():
                self.assertEqual(
                    hashlib.sha256(z.read(f"{ARCHIVE}/{name}")).hexdigest(),
                    digest)
            self.assertEqual(len(manifest["source_sha256"]), report["file_count"])

    def test_extracted_portable_python_sdk_imports_without_repo_or_godot(self):
        build(ROOT, self.first)
        with ZipFile(self.first) as z:
            z.extractall(self.root / "unpacked")
        extracted = self.root / "unpacked" / ARCHIVE
        for cmd in (["--help"], ["--version"]):
            with self.subTest(command=cmd):
                result = subprocess.run(
                    [sys.executable, "-B", "-m", "dx2sdk", *cmd],
                    cwd=extracted, capture_output=True, text=True, timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stdout)
        self.assertIn("Deus Ex: Invisible War", subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", "--help"],
            cwd=extracted, capture_output=True, text=True).stdout)

    def test_deterministic_zip_source_hashes(self):
        build(ROOT, self.first)
        build(ROOT, self.second)
        self.assertEqual(self.first.read_bytes(), self.second.read_bytes())

    def test_refuse_existing_zip_and_source_tree_destination(self):
        build(ROOT, self.first)
        with self.assertRaisesRegex(ValueError, "new SDK ZIP"):
            build(ROOT, self.first)
        # Prevent generating source release directly inside the checkout:
        with self.assertRaisesRegex(ValueError, "new SDK ZIP"):
            build(ROOT, ROOT / "test_output_not_created.zip")
        self.assertFalse((ROOT / "test_output_not_created.zip").exists())

    def test_missing_required_sources_are_rejected(self):
        empty = self.root / "EmptyCheckout"
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, "required"):
            build(empty, self.first)
        self.assertFalse(self.first.exists())


if __name__ == "__main__":
    unittest.main()
