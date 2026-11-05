"""Synthetic-only tests of private GMP revalidation and redacted public audit.

A mocked source loader exercises contract boundaries without distributing real
DX2 maps. One negative test invokes the actual exporter on forged non-GMP bytes
and verifies that it cannot produce a public audit report.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import audit_private_capsule_height_profiles as audit
import export_capsule_first_contact_preview as preview
import inspect_mopp_axis_point_candidates as mopp
import inspect_mopp_point_triangle_oracle as geometry


class PrivateOriginalGmpHeightAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dx2sdk_synthetic_audit_")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.maps = base / "OwnerPrivateRetail" / "Maps"
        self.private = base / "OwnerPrivateResearch"
        self.reports = base / "RedactedReports"
        for folder in (self.maps, self.private, self.reports):
            folder.mkdir(parents=True)
        self.manifest = self.private / "original_gmp_manifest.json"
        self.output = self.reports / "report.json"
        self.cases = []
        for index in range(3):
            source = self.maps / f"PrivateOriginalSecretName{index}.gmp"
            source.write_bytes(("INVENTED_NOT_RETAIL_GMP_" + str(index)).encode())
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            document = self._source_profile(source.name, sha)
            path = self.private / f"private_profile_{index}.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.cases.append({"map_file": str(source),
                               "private_profile": str(path)})
        self._manifest()

    def _source_profile(self, map_name, sha, *,
                        offsets=(0., .5, 1.), start=(.5, .5, .2),
                        end=(.6, .5, .2), radius=.15, half=.1):
        vertices = [(0., 0., 0.), (2., 0., 0.), (0., 2., 0.)]
        oracle = geometry.LevelPointTriangleOracle(vertices, [(0,1,2,True)])
        walker = mopp.ConservativeMoppPointCandidates(
            b"\x28\x00\xff\x30", 1, (0., 0., -10., 65536.))
        return preview.build_profile_document(
            oracle, walker, map_name=map_name, source_hash=sha,
            start=start, end=end, radius=radius, axis=(0.,0.,1.),
            axis_half_length=half, height_offsets=offsets)

    def _manifest(self, cases=None):
        value = {"schema": audit.MANIFEST_SCHEMA,
                 "cases": self.cases if cases is None else cases}
        self.manifest.write_text(json.dumps(value), encoding="utf-8")

    def _mock_authenticated_replay(self, source, destination, **kwargs):
        source = Path(source)
        # The mock models the worker's SHA authentication, synthetic original
        # triangle geometry and fresh exclusive private-sidecar output.
        if hashlib.sha256(source.read_bytes()).hexdigest() != kwargs["expected_sha256"]:
            raise ValueError("SENSITIVE original source map path should never escape")
        doc = self._source_profile(
            source.name, kwargs["expected_sha256"],
            start=kwargs["start"], end=kwargs["end"], radius=kwargs["radius"],
            half=kwargs["axis_half_length"], offsets=kwargs["height_offsets"])
        with Path(destination).open("x", encoding="utf-8") as f:
            json.dump(doc, f)
        return {"status":"ok"}

    def _run_mock(self, **kwargs):
        with patch.object(audit.preview, "build",
                          side_effect=self._mock_authenticated_replay) as worker:
            result = audit.audit(self.manifest, self.output, **kwargs)
        return result, worker.call_count

    def _assert_no_output_or_private_staging(self):
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.reports.glob("dx2sdk_private_audit_*")), [])

    def test_full_three_distinct_original_source_replays_produce_counts_only(self):
        report, called = self._run_mock()
        self.assertEqual(called, 3)
        self.assertEqual(report["schema"], audit.REPORT_SCHEMA)
        self.assertEqual(report["verified_original_gmp_count"], 3)
        self.assertEqual(report["verified_private_profile_count"], 3)
        self.assertEqual(report["total_capsule_height_samples"], 9)
        self.assertEqual(report["height_samples_with_source_triangle_contact"], 3)
        self.assertEqual(report["height_samples_without_source_triangle_contact"], 6)
        self.assertEqual(report["profiles_with_any_source_triangle_contact"], 3)
        self.assertEqual(report["contact_triangle_count_buckets"],
                         {"none":6, "one":3, "two_to_four":0, "five_or_more":0})
        self.assertFalse(report["havok_runtime_contact_verified"])
        self.assertTrue(report["aggregate_counts_can_still_be_sensitive"])
        raw = self.output.read_text()
        self.assertEqual(json.loads(raw), report)
        for case in self.cases:
            original = Path(case["map_file"])
            private = Path(case["private_profile"])
            self.assertNotIn(original.name, raw)
            self.assertNotIn(str(original), raw)
            self.assertNotIn(str(private), raw)
            self.assertNotIn(hashlib.sha256(original.read_bytes()).hexdigest(), raw)
        self.assertNotIn("original_level_triangle_id", raw)
        self.assertNotIn("baseline_capsule_start", raw)
        self.assertNotIn("first_contact_path_t", raw)
        self.assertNotIn(".gmp", raw)
        self.assertEqual(list(self.reports.glob("dx2sdk_private_audit_*")), [])

    def test_source_sha_change_refuses_without_report_or_private_leak(self):
        Path(self.cases[2]["map_file"]).write_bytes(b"UNEXPECTED PRIVATE MUTATION")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(audit.preview, "build",
                          side_effect=self._mock_authenticated_replay):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = audit.main(["--manifest", str(self.manifest),
                                     "--output", str(self.output)])
        self.assertEqual(result, 1)
        self.assertEqual(json.loads(stderr.getvalue())["code"],
                         "source_recomputation_refused")
        combined = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("PrivateOriginalSecretName", combined)
        self.assertNotIn(str(self.maps), combined)
        self._assert_no_output_or_private_staging()

    def test_private_first_contact_tamper_refuses_all_aggregation(self):
        entry = Path(self.cases[1]["private_profile"])
        doc = json.loads(entry.read_text())
        doc["profile_samples"][0]["first_hit_original_triangle_id"] = 9876
        entry.write_text(json.dumps(doc))
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "original_profile_replay_mismatch"):
            self._run_mock()
        self._assert_no_output_or_private_staging()

    def test_private_contact_count_tamper_is_not_published(self):
        entry = Path(self.cases[0]["private_profile"])
        doc = json.loads(entry.read_text())
        doc["profile_samples"][0]["geometric_source_triangle_hits"] = 55
        entry.write_text(json.dumps(doc))
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "original_profile_replay_mismatch"):
            self._run_mock()
        self._assert_no_output_or_private_staging()

    def test_wrong_height_or_coordinate_refuses_replay(self):
        for field, value in [
            ("relative_height_level_units", .01),
            ("first_contact_path_t", .4),
            ("first_contact_initial_overlap", False),
        ]:
            source = Path(self.cases[0]["private_profile"])
            before = source.read_bytes()
            doc = json.loads(before)
            doc["profile_samples"][0 if field != "relative_height_level_units" else 1][field] = value
            source.write_text(json.dumps(doc))
            with self.subTest(field=field), self.assertRaises(audit.AuditRefusal):
                self._run_mock()
            self._assert_no_output_or_private_staging()
            source.write_bytes(before)
        source = Path(self.cases[0]["private_profile"])
        doc = json.loads(source.read_text())
        doc["baseline_capsule_start_godot_xyz"] = [999.,999.,999.]
        source.write_text(json.dumps(doc))
        with self.assertRaises(audit.AuditRefusal):
            self._run_mock()
        self._assert_no_output_or_private_staging()

    def test_malformed_private_profile_rejected_before_worker(self):
        path = Path(self.cases[0]["private_profile"])
        doc = json.loads(path.read_text())
        doc["profile_samples"][1]["relative_height_level_units"] = float("nan")
        path.write_text(json.dumps(doc))
        with patch.object(audit.preview, "build") as worker:
            with self.assertRaisesRegex(audit.AuditRefusal, "invalid_private_profile"):
                audit.audit(self.manifest, self.output)
            worker.assert_not_called()
        self._assert_no_output_or_private_staging()

    def test_duplicate_and_small_cohort_do_not_release_by_default(self):
        self._manifest([self.cases[0], self.cases[0], self.cases[2]])
        with self.assertRaisesRegex(audit.AuditRefusal, "unsafe_private_path"):
            self._run_mock()
        self._assert_no_output_or_private_staging()
        self._manifest(self.cases[:2])
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "too_few_distinct_source_maps_for_aggregate"):
            self._run_mock()
        self._assert_no_output_or_private_staging()
        report, called = self._run_mock(allow_small_cohort=True)
        self.assertEqual(called, 2)
        self.assertEqual(report["verified_original_gmp_count"], 2)
        self.assertEqual(report["verified_private_profile_count"], 2)

    def test_output_in_retail_maps_or_checkout_or_existing_file_refused(self):
        bad = self.maps / "bad_aggregate.json"
        with patch.object(audit.preview, "build",
                          side_effect=self._mock_authenticated_replay):
            with self.assertRaisesRegex(audit.AuditRefusal, "unsafe_private_path"):
                audit.audit(self.manifest, bad)
        self.assertFalse(bad.exists())
        self.output.write_text("DO_NOT_OVERWRITE")
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "unsafe_report_or_manifest_path"):
            self._run_mock()
        self.assertEqual(self.output.read_text(), "DO_NOT_OVERWRITE")
        self.output.unlink()
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "unsafe_report_or_manifest_path"):
            audit.audit(self.manifest, ROOT / "do_not_commit_audit.json")
        self._assert_no_output_or_private_staging()

    def test_real_source_parser_rejects_fake_game_assets(self):
        # The mock-positive tests above are NOT game-asset evidence. On actual
        # exporter path, invented bytes must refuse and write no public data.
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "source_recomputation_refused"):
            audit.audit(self.manifest, self.output)
        self._assert_no_output_or_private_staging()

    def test_unexpected_decoder_error_suppresses_sensitive_traceback(self):
        captured_stdout, captured_stderr = io.StringIO(), io.StringIO()
        with patch.object(audit.preview, "build",
                          side_effect=RuntimeError("SECRET full retail GMP path and triangle data")):
            with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
                rc = audit.main(["--manifest", str(self.manifest),
                                 "--output", str(self.output)])
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(captured_stderr.getvalue()),
                         {"status":"refused", "code":"source_recomputation_refused"})
        self.assertEqual(captured_stdout.getvalue(), "")
        self.assertNotIn("SECRET", captured_stderr.getvalue())
        self._assert_no_output_or_private_staging()

    def test_incomplete_aggregate_write_is_removed_and_error_redacted(self):
        original_open = Path.open

        class BrokenWrite:
            def __init__(self, inner):
                self.inner = inner

            def __enter__(self):
                self.inner.__enter__()
                return self

            def __exit__(self, *args):
                return self.inner.__exit__(*args)

            def write(self, data):
                self.inner.write(data[:10])
                raise OSError("SECRET original GMP path: simulated disk full")

        def broken_open(path, mode="r", *args, **kwargs):
            f = original_open(path, mode, *args, **kwargs)
            if Path(path) == self.output and mode == "x":
                return BrokenWrite(f)
            return f

        stderr = io.StringIO()
        with patch.object(audit.preview, "build",
                          side_effect=self._mock_authenticated_replay):
            with patch.object(Path, "open", new=broken_open):
                with redirect_stderr(stderr):
                    result = audit.main(["--manifest", str(self.manifest),
                                         "--output", str(self.output)])
        self.assertEqual(result, 1)
        self.assertEqual(json.loads(stderr.getvalue()),
                         {"status":"refused", "code":"audit_failed"})
        self.assertNotIn("SECRET", stderr.getvalue())
        self._assert_no_output_or_private_staging()

    def test_private_manifest_size_and_invalid_json_refused(self):
        self.manifest.write_text("not JSON at all")
        with self.assertRaisesRegex(audit.AuditRefusal, "invalid_private_json"):
            audit.audit(self.manifest, self.output)
        self.manifest.write_text(" " * (audit.MAX_MANIFEST_BYTES + 1))
        with self.assertRaisesRegex(audit.AuditRefusal,
                                    "private_input_size_refused"):
            audit.audit(self.manifest, self.output)
        self._assert_no_output_or_private_staging()


if __name__ == "__main__":
    unittest.main()
