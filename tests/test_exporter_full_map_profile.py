"""Source-only safety/correctness for whole-map timing harness.

No game-owned files are needed or bundled. An injected synthetic exporter
proves determinism guards and temporary-output cleanup; it is NOT a
performance claim about any real map.
"""
from __future__ import annotations

import cProfile
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
sys.path.insert(0, str(ROOT/"map_exporter"))
import profile_dx2_map_export as profiler
from dx2level import Builder


class FullMapProfilerTests(unittest.TestCase):
    def _fixture(self, root: Path):
        source = root/"M1_synthetic.gmp"
        bundle = root/"mission_synthetic.ibd"
        source.write_bytes(b"SYNTHETIC_GMP_ONLY_NOT_RETAIL")
        bundle.write_bytes(b"SYNTHETIC_IBD_ONLY_NOT_RETAIL")
        return source, bundle

    @staticmethod
    def _fake_export(level, output, *, manual, transform_overrides=None):
        assert output.parent != level.path.parent
        assert manual
        assert transform_overrides is None
        output.write_bytes(b"glTF"+bytes(range(20)))
        output.with_suffix(".report.json").write_text(
            json.dumps({"placed_real_mesh_actors": 1, "source": "synthetic"}),
            encoding="utf-8")
        return {"placed_real_mesh_actors": 1}

    def _run(self, source, bundle, runner=None, **kwargs):
        with (patch.object(profiler, "resolve_map", return_value=SimpleNamespace(path=source)),
              patch.object(profiler, "choose_bundles", return_value=[bundle])):
            return profiler.profile_map_export(
                source.parent, source.name,
                runner=runner or self._fake_export, **kwargs)

    def test_repeated_outputs_deterministic_and_cleaned_with_separate_profile(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            source,bundle=self._fixture(root)
            paths=[]
            def export(level, output, *, manual, transform_overrides=None):
                paths.append(output)
                return self._fake_export(
                    level,output,manual=manual,
                    transform_overrides=transform_overrides)
            result=self._run(source,bundle,runner=export,repeats=2,top=8)
            self.assertEqual(result["schema"], "DX2SDK-exporter-full-map-profile-v1")
            self.assertEqual(result["status"], "test-runner-only")
            self.assertTrue(result["original_assets_unchanged_sha256"])
            self.assertTrue(result["glb_report_byte_determinism_verified"])
            self.assertTrue(result["temporary_glb_and_reports_deleted"])
            self.assertFalse(result["original_game_files_modified"])
            self.assertEqual(len(result["unprofiled_wall_ms"]),2)
            self.assertEqual(len(paths),3)  # two raw timings, one cProfile
            self.assertEqual(result["profile"]["label"],
                "SEPARATE cProfile run (instrumented, not wall-time baseline)")
            for output in paths:
                self.assertFalse(output.exists())
                self.assertFalse(output.with_suffix(".report.json").exists())
            self.assertTrue(source.exists())
            self.assertTrue(bundle.exists())

    def test_mismatched_glb_digests_refused_not_reported_as_deterministic(self):
        with TemporaryDirectory() as folder:
            source,bundle=self._fixture(Path(folder))
            calls=[0]
            def drift(level,output,*,manual,transform_overrides=None):
                self._fake_export(level,output,manual=manual)
                calls[0]+=1
                with output.open("ab") as f:
                    f.write(bytes([calls[0]]))
                return {"placed_real_mesh_actors":1}
            with self.assertRaisesRegex(ValueError, "bytes differ"):
                self._run(source,bundle,runner=drift,repeats=2,
                          collect_profile=False)
            self.assertEqual(calls[0],2)

    def test_changed_original_source_detected_by_hash(self):
        with TemporaryDirectory() as folder:
            source,bundle=self._fixture(Path(folder))
            def tamper(level,output,*,manual,transform_overrides=None):
                result=self._fake_export(level,output,manual=manual)
                level.path.write_bytes(b"CHANGED_ORIGINAL_ASSET")
                return result
            with self.assertRaisesRegex(ValueError, "Source map"):
                self._run(source,bundle,runner=tamper,repeats=1,
                          collect_profile=False)

    def test_profile_contains_only_exporter_functions_not_source_paths(self):
        counter=cProfile.Profile()
        counter.enable()
        b=Builder({}, {}, {})
        b.vectors([(0.0,0.0,0.0),(1.0,-2.0,3.0)],3)
        counter.disable()
        rows=profiler._profile_stats(counter, 20)
        self.assertTrue(any(x["function"]=="vectors"
                            and x["module"]=="dx2level.py" for x in rows))
        self.assertTrue(all("/" not in x["module"] and "\\" not in x["module"]
                            for x in rows))

    def test_profiler_flags_and_no_retail_directory_reports(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            source,bundle=self._fixture(root)
            profiler._assert_safe_report_path(root.parent/"standalone_benchmark.json",
                                               [source,bundle])
            with self.assertRaises(ValueError):
                profiler._assert_safe_report_path(root/"report.json", [source,bundle])
            with self.assertRaises(ValueError):
                profiler._assert_safe_report_path(root/"existing.gmp", [source,bundle])
            with self.assertRaises(ValueError):
                profiler._assert_safe_report_path(root/"new.json", [source,bundle])
            output=root.parent/"existing_report.json"
            # In a separate disposable parent directory, prove overwrite refusal.
            with TemporaryDirectory() as parent:
                report=Path(parent)/"report.json"
                report.write_text("PRESERVE",encoding="utf-8")
                with self.assertRaises(ValueError):
                    profiler._assert_safe_report_path(report,[source,bundle])
                self.assertEqual(report.read_text(), "PRESERVE")
            for repeats,top in ((0,2),(13,2),(1,0),(1,101)):
                with self.subTest(repeats=repeats,top=top), self.assertRaises(ValueError):
                    self._run(source,bundle,repeats=repeats,top=top)


if __name__=="__main__":
    unittest.main()
