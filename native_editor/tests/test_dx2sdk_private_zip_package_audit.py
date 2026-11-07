"""Synthetic-only safeguards for private aggregate-only ZIP package auditing."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import warnings
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
sys.path.insert(0, str(ROOT / "map_exporter"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_dx2sdk_export_boundary_audit import fixture  # noqa: E402
from dx2inspect import Package  # noqa: E402
from private_zip_package_audit import (  # noqa: E402
    SCHEMA, PrivateZipAuditError, inspect_private_zip_bytes,
    inspect_private_zip_file,
)


def make_zip(rows, *, compression=ZIP_STORED):
    output = BytesIO()
    with ZipFile(output, "w", compression=compression) as archive:
        for filename, data in rows:
            archive.writestr(filename, data)
    return output.getvalue()


class PrivateZipPackageAuditTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="synthetic_private_zip_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "private-testing-only.zip"
        self.good = fixture()[0]
        self.zero = fixture(payload_lengths=(0, 5))[0]
        self.overlap = fixture(payload_offsets=(512, 511))[0]

    def test_in_memory_legacy_reader_no_file_access_and_immutable_source(self):
        before = self.good
        self.assertEqual(len(Package(self.root / "not_present.gmp", data=before).exports), 2)
        self.assertEqual(self.good, before)
        for bad in (bytearray(self.good), "invalid", 17):
            with self.subTest(type=type(bad)), self.assertRaises(ValueError):
                Package(self.root / "not_present.gmp", data=bad)

    def test_aggregate_only_three_reader_results_and_source_invariance(self):
        data = make_zip([
            ("maps/invented_a.gmp", self.good),
            ("maps/invented_b.D2U", self.zero),
            ("maps/bad_native.gmp", b"bad"),
            ("maps/overlapping.gmp", self.overlap),
            ("textures/not_a_map.ibd", b"hidden native bytes"),
        ])
        before = data
        report = inspect_private_zip_bytes(data)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["status"], "aggregate-only")
        self.assertEqual(report["counts"]["eligible_packages"], 4)
        self.assertEqual(report["counts"]["three_reader_concordant"], 2)
        self.assertEqual(report["counts"]["legacy_reader_rejected"], 1)
        self.assertEqual(report["counts"]["cross_reader_rejected"], 1)
        self.assertEqual(report["archive_entries_total"], 5)
        self.assertFalse(report["archive_sha256_independently_supplied"])
        self.assertTrue(report["package_source_bytes_verified_per_reader"])
        self.assertFalse(report["zip_member_payloads_written_to_disk"])
        self.assertFalse(report["package_names_and_offsets_emitted"])
        self.assertFalse(report["export_envelopes_independently_verified"])
        self.assertFalse(report["native_bsp_leaf_zone_decoded"])
        self.assertFalse(report["runtime_game_verified"])
        self.assertFalse(report["writable"])
        report_json = json.dumps(report)
        for forbidden in ("invented_a.gmp", "overlapping.gmp", "bad_native.gmp",
                          "hidden native bytes", "maps/", str(self.root),
                          "candidate_export_envelopes"):
            self.assertNotIn(forbidden, report_json)
        self.assertEqual(data, before)
        self.assertEqual(inspect_private_zip_bytes(data), report)

    def test_external_zip_hash_must_match_identical_in_memory_bytes(self):
        data = make_zip([("Test.gmp", self.good)])
        digest = sha256(data).hexdigest()
        report = inspect_private_zip_bytes(data, expected_sha256=digest)
        self.assertTrue(report["archive_sha256_independently_supplied"])
        with self.assertRaisesRegex(PrivateZipAuditError, "SHA-256"):
            inspect_private_zip_bytes(data, expected_sha256="0" * 64)
        with self.assertRaises(PrivateZipAuditError):
            inspect_private_zip_bytes(data, expected_sha256=digest.upper())
        with self.assertRaises(PrivateZipAuditError):
            inspect_private_zip_bytes(bytearray(data))

    def test_reject_duplicate_zip_members_and_explicit_file_count_cap(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            data = make_zip([("MAP.gmp", self.good), ("map.GMP", self.zero)])
        with self.assertRaisesRegex(PrivateZipAuditError, "duplicate"):
            inspect_private_zip_bytes(data)
        data = make_zip([("first.gmp", self.good), ("second.gmp", self.good)])
        with self.assertRaisesRegex(PrivateZipAuditError, "count"):
            inspect_private_zip_bytes(data, max_files=1)
        for count in (0, 513, True, -1):
            with self.subTest(count=count), self.assertRaises(PrivateZipAuditError):
                inspect_private_zip_bytes(data, max_files=count)

    def test_unsafe_member_names_and_symlinks_are_counted_without_extraction(self):
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
            archive.writestr("maps/good.gmp", self.good)
            archive.writestr("../escape.gmp", self.good)
            symlink = ZipInfo("maps/symlink.gmp")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(symlink, b"../secret.gmp")
        report = inspect_private_zip_bytes(buffer.getvalue())
        self.assertEqual(report["counts"]["eligible_packages"], 3)
        self.assertEqual(report["counts"]["three_reader_concordant"], 1)
        self.assertEqual(report["counts"]["unsafe_entry_rejected"], 2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_reject_corrupt_zip_no_packages_and_unsupported_entry(self):
        with self.assertRaises(PrivateZipAuditError):
            inspect_private_zip_bytes(b"Not a ZIP")
        with self.assertRaisesRegex(PrivateZipAuditError, "no explicit"):
            inspect_private_zip_bytes(make_zip([("foo.txt", b"data")]))
        encrypted = make_zip([("maps/good.gmp", self.good)])
        # Produce a supported but very compressible package candidate to
        # exercise the high expansion-ratio filter (never decompress it).
        bomb = make_zip([("maps/huge.gmp", b"\0" * 1000000)],
                        compression=ZIP_DEFLATED)
        self.assertEqual(inspect_private_zip_bytes(bomb)[
            "counts"]["oversized_or_high_ratio_rejected"], 1)
        self.assertEqual(inspect_private_zip_bytes(encrypted)[
            "counts"]["three_reader_concordant"], 1)

    def test_preflight_counts_nonpackage_uncompressed_budget(self):
        # The budget applies to the entire central directory, not just
        # eligible map packages. No decompression or extraction is needed.
        from unittest.mock import patch
        data = make_zip([
            ("maps/good.gmp", self.good),
            ("other/large-unrelated.bin", b"z" * 128),
        ])
        with patch("private_zip_package_audit.MAX_TOTAL_UNCOMPRESSED",
                   len(self.good) + 64):
            with self.assertRaisesRegex(PrivateZipAuditError, "total ZIP"):
                inspect_private_zip_bytes(data)

    def test_preflight_still_allows_bounded_unrelated_members(self):
        data = make_zip([
            ("maps/good.gmp", self.good),
            ("other/metadata.txt", b"synthetic only"),
        ])
        result = inspect_private_zip_bytes(data)
        self.assertEqual(result["counts"]["eligible_packages"], 1)
        self.assertEqual(result["counts"]["three_reader_concordant"], 1)
        self.assertEqual(result["archive_entries_total"], 2)

    def test_cli_readonly_no_paths_names_or_asset_bytes_even_when_denied(self):
        data = make_zip([("private/SourceIdentity.gmp", self.good)])
        self.path.write_bytes(data)
        before = self.path.read_bytes()
        entries = set(self.root.iterdir())
        script = ROOT / "research" / "dx2" / "private_zip_package_audit.py"
        args = [sys.executable, "-B", str(script), "--archive", str(self.path)]
        run = subprocess.run(args, cwd=ROOT, text=True,
                             capture_output=True, timeout=35)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["counts"]["three_reader_concordant"], 1)
        self.assertNotIn("SourceIdentity", run.stdout)
        self.assertNotIn(str(self.path), run.stdout)
        self.assertNotIn("package bytes", run.stdout)
        self.assertEqual(set(self.root.iterdir()), entries)
        self.assertEqual(self.path.read_bytes(), before)
        fail = subprocess.run(args + ["--sha256", "0" * 64],
                              cwd=ROOT, text=True,
                              capture_output=True, timeout=35)
        self.assertEqual(fail.returncode, 2)
        self.assertEqual(fail.stdout, "")
        self.assertNotIn(str(self.path), fail.stderr)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
