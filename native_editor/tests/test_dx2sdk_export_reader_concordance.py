"""Invented-package checks for the source-only two-reader concordance research."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))
sys.path.insert(0, str(ROOT / "research" / "dx2"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dx2inspect import Package  # noqa: E402
from test_dx2sdk_export_boundary_audit import fixture  # noqa: E402
from export_reader_concordance import (  # noqa: E402
    ReaderConcordanceError, SCHEMA, compare_export_readers, compare_local_package,
)


class ExportReaderConcordanceTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix="synthetic_dx2_concordance_")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "invented.gmp"
        self.source, self.bounds = fixture()
        self.path.write_bytes(self.source)
        self.digest = sha256(self.source).hexdigest()

    def legacy(self):
        return Package(self.path)

    def test_matching_readers_emit_only_bounded_non_authoritative_metadata(self):
        package = self.legacy()
        result = compare_export_readers(package, expected_sha256=self.digest)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["matched_nonempty_exports"], 2)
        self.assertEqual(result["zero_length_exports_not_owners"], 0)
        self.assertEqual(result["table_counts"], {"names": 5, "imports": 1, "exports": 2})
        self.assertTrue(result["strict_structure_passed"])
        self.assertTrue(result["legacy_reader_concordant"])
        self.assertFalse(result["export_envelopes_independently_verified"])
        self.assertFalse(result["native_bsp_leaf_zone_decoded"])
        self.assertFalse(result["runtime_game_verified"])
        self.assertFalse(result["writable"])
        self.assertFalse(result["source_original_modified"])
        self.assertNotIn("candidate_export_envelopes", result)
        self.assertNotIn("TestActor", json.dumps(result))
        self.assertEqual(self.path.read_bytes(), self.source)
        self.assertEqual(compare_export_readers(package, expected_sha256=self.digest), result)

    def test_zero_sized_export_excluded_and_local_file_untouched(self):
        source, _ = fixture(payload_lengths=(0, 5))
        self.path.write_bytes(source)
        digest = sha256(source).hexdigest()
        before = set(self.root.iterdir())
        report = compare_local_package(self.path, expected_sha256=digest)
        self.assertEqual(report["zero_length_exports_not_owners"], 1)
        self.assertEqual(report["matched_nonempty_exports"], 1)
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertEqual(self.path.read_bytes(), source)

    def test_reject_legacy_export_row_tampering_and_identity_conflicts(self):
        changes = [
            ("index", 3),
            ("offset", 511),
            ("size", 6),
            ("size", 0),
            ("offset", True),
            ("offset", -1),
        ]
        for name, value in changes:
            with self.subTest(field=name, value=value):
                package = self.legacy()
                package.exports[0][name] = value
                with self.assertRaises(ReaderConcordanceError):
                    compare_export_readers(package, expected_sha256=self.digest)

    def test_reject_legacy_table_and_version_mismatch(self):
        edits = (
            lambda p: setattr(p, "table_counts", (5, 2, 2)),
            lambda p: setattr(p, "table_counts", (True, 1, 2)),
            lambda p: p.names.pop(),
            lambda p: p.imports.clear(),
            lambda p: p.exports.pop(),
            lambda p: setattr(p, "version", True),
            lambda p: setattr(p, "licensee", 70),
            lambda p: setattr(p, "data", bytearray(p.data)),
        )
        for i, edit in enumerate(edits):
            package = self.legacy()
            edit(package)
            with self.subTest(i=i), self.assertRaises(ReaderConcordanceError):
                compare_export_readers(package, expected_sha256=self.digest)

    def test_strict_reader_can_veto_legacy_reader_acceptance(self):
        # The older Package reader accepts overlapping payloads; strict audit
        # must independently reject them rather than calling them verified.
        samples = [
            fixture(payload_offsets=(512, 511))[0],
            fixture(payload_offsets=(512, 512))[0],
        ]
        for source in samples:
            with self.subTest(source_hash=sha256(source).hexdigest()):
                self.path.write_bytes(source)
                package = self.legacy()
                with self.assertRaisesRegex(ReaderConcordanceError, "strict"):
                    compare_export_readers(package, expected_sha256=sha256(source).hexdigest())

    def test_bad_source_hash_and_unsupported_local_package_fail_closed(self):
        with self.assertRaisesRegex(ReaderConcordanceError, "hash"):
            compare_export_readers(self.legacy(), expected_sha256="0" * 64)
        with self.assertRaises(ReaderConcordanceError):
            compare_local_package(self.path, expected_sha256=self.digest.upper())
        self.path.write_bytes(b"not a package")
        with self.assertRaises(ReaderConcordanceError):
            compare_local_package(self.path, expected_sha256=sha256(self.path.read_bytes()).hexdigest())
        with self.assertRaises(ReaderConcordanceError):
            compare_local_package(self.root / "missing.gmp", expected_sha256=self.digest)

    def test_local_cli_opt_in_prints_no_names_bytes_or_file_paths(self):
        script = ROOT / "research" / "dx2" / "export_reader_concordance.py"
        original = self.path.read_bytes()
        before = set(self.root.iterdir())
        run = subprocess.run(
            [sys.executable, "-B", str(script), "--map", str(self.path),
             "--sha256", self.digest],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        summary = json.loads(run.stdout)
        self.assertTrue(summary["legacy_reader_concordant"])
        self.assertNotIn("TestActor", run.stdout)
        self.assertNotIn(str(self.path), run.stdout)
        self.assertNotIn("candidate_export_envelopes", run.stdout)
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertEqual(self.path.read_bytes(), original)
        denied = subprocess.run(
            [sys.executable, "-B", str(script), "--map", str(self.path),
             "--sha256", "0" * 64],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(denied.returncode, 2)
        self.assertEqual(denied.stdout, "")


if __name__ == "__main__":
    unittest.main()
