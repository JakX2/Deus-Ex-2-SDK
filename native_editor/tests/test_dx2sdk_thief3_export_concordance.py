"""Invented DX2/T3 three-reader concordance tests; no retail package assets."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))
sys.path.insert(0, str(ROOT / "research" / "dx2"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dx2inspect import Package  # noqa: E402
from test_dx2sdk_export_boundary_audit import fixture  # noqa: E402
from export_reader_concordance import ReaderConcordanceError  # noqa: E402
from thief3_export_concordance import (  # noqa: E402
    SCHEMA, _source_module, compare_thief_reference, compare_local_thief_reference,
)


class Thief3ExportConcordanceTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix="invented_t3_concordance_")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "invented.gmp"
        self.source, self.bounds = fixture()
        self.digest = sha256(self.source).hexdigest()
        self.path.write_bytes(self.source)

    def package(self):
        return Package(self.path)

    def t3_proxy(self):
        path = ROOT / "third_party" / "t3sdk_assets" / "upkg.py"
        obj = _source_module(path, "_dx2sdk_test_t3_reference").Package(
            "invented-in-memory.gmp", data=self.source
        )
        rows = [
            SimpleNamespace(index=x.index, serial_offset=x.serial_offset,
                            serial_size=x.serial_size)
            for x in obj.exports
        ]
        return SimpleNamespace(
            file_version=obj.file_version, licensee_version=obj.licensee_version,
            names=list(obj.names), imports=list(obj.imports), exports=rows,
            name_offset=obj.name_offset, import_offset=obj.import_offset,
            export_offset=obj.export_offset, header_size=obj.header_size,
            import_end=obj.import_end, export_end=obj.export_end,
        )

    def test_three_readers_agree_on_invented_package_without_claiming_provenance(self):
        before = self.path.read_bytes()
        result = compare_thief_reference(self.package(), expected_sha256=self.digest)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["table_counts"], {"names": 5, "imports": 1, "exports": 2})
        self.assertEqual(result["matched_nonempty_exports"], 2)
        self.assertTrue(result["dx2_legacy_and_strict_concordant"])
        self.assertTrue(result["thief3_reference_table_concordant"])
        self.assertFalse(result["export_envelopes_independently_verified"])
        self.assertFalse(result["native_bsp_leaf_zone_decoded"])
        self.assertFalse(result["runtime_game_verified"])
        self.assertFalse(result["writable"])
        self.assertNotIn("candidate_export_envelopes", result)
        self.assertNotIn("TestActor", json.dumps(result))
        self.assertEqual(self.path.read_bytes(), before)

    def test_zero_size_exports_are_not_owners_for_all_three_readers(self):
        source, _ = fixture(payload_lengths=(0, 5))
        self.path.write_bytes(source)
        report = compare_local_thief_reference(
            self.path, expected_sha256=sha256(source).hexdigest())
        self.assertEqual(report["zero_length_exports_not_owners"], 1)
        self.assertEqual(report["matched_nonempty_exports"], 1)
        self.assertEqual(self.path.read_bytes(), source)

    def test_thief_reference_disagreements_fail_closed(self):
        mutations = (
            lambda o: setattr(o, "file_version", 94),
            lambda o: setattr(o, "licensee_version", 70),
            lambda o: o.imports.clear(),
            lambda o: o.names.pop(),
            lambda o: setattr(o, "name_offset", o.name_offset + 1),
            lambda o: setattr(o, "import_offset", o.import_offset + 1),
            lambda o: setattr(o, "export_offset", o.export_offset + 1),
            lambda o: setattr(o, "header_size", o.header_size + 1),
            lambda o: setattr(o, "import_end", o.import_end + 1),
            lambda o: setattr(o, "export_end", o.export_end + 1),
            lambda o: setattr(o.exports[0], "index", 1),
            lambda o: setattr(o.exports[0], "serial_offset", 513),
            lambda o: setattr(o.exports[0], "serial_size", 6),
            lambda o: setattr(o.exports[0], "serial_size", True),
            lambda o: setattr(o.exports[0], "serial_offset", -1),
        )
        for idx, mutate in enumerate(mutations):
            fake = self.t3_proxy()
            mutate(fake)
            with self.subTest(mutation=idx):
                with patch("thief3_export_concordance._source_module",
                           return_value=SimpleNamespace(Package=lambda *args, **kwargs: fake)):
                    with self.assertRaises(ReaderConcordanceError):
                        compare_thief_reference(self.package(), expected_sha256=self.digest)

    def test_strict_boundary_veto_applies_before_thief_reference_acceptance(self):
        source, _ = fixture(payload_offsets=(512, 511))
        self.path.write_bytes(source)
        with self.assertRaises(ReaderConcordanceError):
            compare_thief_reference(
                self.package(), expected_sha256=sha256(source).hexdigest())

    def test_hash_bad_source_and_missing_file_rejected(self):
        with self.assertRaises(ReaderConcordanceError):
            compare_thief_reference(self.package(), expected_sha256="0" * 64)
        with self.assertRaises(ReaderConcordanceError):
            compare_local_thief_reference(self.path, expected_sha256=self.digest.upper())
        with self.assertRaises(ReaderConcordanceError):
            compare_local_thief_reference(self.root / "missing.gmp", expected_sha256=self.digest)
        self.path.write_bytes(b"not a package")
        with self.assertRaises(ReaderConcordanceError):
            compare_local_thief_reference(
                self.path, expected_sha256=sha256(self.path.read_bytes()).hexdigest())

    def test_local_cli_report_does_not_expose_original_names_or_write_package(self):
        script = ROOT / "research" / "dx2" / "thief3_export_concordance.py"
        before = self.path.read_bytes()
        entries = set(self.root.iterdir())
        process = subprocess.run(
            [sys.executable, "-B", str(script), "--map", str(self.path),
             "--sha256", self.digest],
            cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertTrue(report["thief3_reference_table_concordant"])
        self.assertNotIn(str(self.path), process.stdout)
        self.assertNotIn("TestActor", process.stdout)
        self.assertNotIn("candidate_export_envelopes", process.stdout)
        self.assertEqual(set(self.root.iterdir()), entries)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
