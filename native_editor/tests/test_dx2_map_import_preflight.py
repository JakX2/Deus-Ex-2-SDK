"""Retail-asset-free tests for the packaged DX2Ed owner GMP/IBD preflight."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "native_editor" / "godot_editor" / "backend"))
sys.path.insert(0, str(ROOT / "map_exporter"))
import map_import_preflight as ready
import dx2_native_backend as backend
from dx2_map_exporter import LevelChoice


class DX2EdMapImportReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dx2ed_resource_discovery_only_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.maps = self.root / "Retail" / "Content" / "DX2" / "Maps"
        self.maps.mkdir(parents=True)
        self.gmp = self.maps / "M1_Synthetic_Original.gmp"
        self.ibd = self.maps / "m1_synthetic_original.ibd"
        self.gmp.write_bytes(b"NOT A REAL GMP, RESOURCE DISCOVERY ONLY")
        self.ibd.write_bytes(b"NOT A REAL IBD")
        self.level = LevelChoice(self.gmp, self.ibd, (), 1.0)

    def _run(self, *, map_path=None, bundles=None, levels=None, choose=None):
        chosen = [self.ibd] if choose is None else choose
        with patch.object(backend, "list_levels", return_value=(
                    [self.level] if levels is None else levels)):
            with patch.object(backend, "choose_bundles", return_value=chosen):
                return ready.preflight(map_path or self.gmp, bundles)

    def test_original_resource_candidates_only_are_redacted(self):
        original_map = self.gmp.read_bytes()
        original_ibd = self.ibd.read_bytes()
        result = self._run()
        self.assertEqual(result["schema"], ready.SCHEMA)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["code"], "bundle_paths_found")
        self.assertEqual(result["selected_ibd_bundle_count"], 1)
        self.assertTrue(result["mission_ibd_or_override_found"])
        self.assertTrue(result["read_only"])
        for key in ("original_game_assets_modified", "original_map_package_parsed",
                    "rendered_godot_scene_verified", "ibd_contents_verified",
                    "native_havok_or_gameplay_verified"):
            self.assertFalse(result[key], key)
        public = json.dumps(result)
        for secret in (str(self.gmp), str(self.ibd), self.gmp.name, self.ibd.name):
            self.assertNotIn(secret, public)
        self.assertEqual(self.gmp.read_bytes(), original_map)
        self.assertEqual(self.ibd.read_bytes(), original_ibd)
        self.assertEqual(sorted(p.name for p in self.maps.iterdir()),
                         sorted([self.gmp.name, self.ibd.name]))

    def test_missing_and_empty_gmp_files_are_refused_without_import(self):
        missing = ready.preflight(self.maps / "Absent.gmp")
        self.assertEqual(missing["code"], "missing_original_gmp")
        self.assertNotIn(str(self.maps), json.dumps(missing))
        self.gmp.write_bytes(b"")
        result = self._run()
        self.assertEqual(result["code"], "source_size_refused")

    def test_missing_ibd_bundle_hides_private_source_path(self):
        no_mission = LevelChoice(self.gmp, None, (), 1.0)
        with patch.object(backend, "list_levels", return_value=[no_mission]):
            report = ready.preflight(self.gmp)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["code"], "mission_ibd_missing")
        self.assertNotIn(self.gmp.name, json.dumps(report))

    def test_invalid_override_refused_before_source_reader(self):
        with patch.object(backend, "list_levels") as loaded:
            report = ready.preflight(self.gmp, [self.maps / "DoesNotExist.ibd"])
            loaded.assert_not_called()
        self.assertEqual(report["code"], "invalid_ibd_override")

    def test_source_lookup_errors_never_export_path_or_exception_details(self):
        with patch.object(backend, "list_levels",
                          side_effect=OSError("SECRET_X original private location")):
            result = ready.preflight(self.gmp)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["code"], "resource_discovery_failed")
        self.assertNotIn("SECRET_X", json.dumps(result))

    def test_incomplete_resource_selection_refused(self):
        self.assertEqual(self._run(choose=[])["code"],
                         "ibd_resource_discovery_incomplete")

    def test_cli_prints_one_redacted_json_record(self):
        captured = io.StringIO()
        with patch.object(backend, "list_levels", return_value=[self.level]):
            with patch.object(backend, "choose_bundles", return_value=[self.ibd]):
                with redirect_stdout(captured):
                    rc = ready.main(["--map", str(self.gmp)])
        self.assertEqual(rc, 0)
        obj = json.loads(captured.getvalue())
        self.assertEqual(obj["status"], "ready")
        self.assertNotIn(str(self.gmp), captured.getvalue())
        self.assertNotIn(self.gmp.name, captured.getvalue())


if __name__ == "__main__":
    unittest.main()
