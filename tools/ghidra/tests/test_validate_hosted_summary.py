"""Strict offline tests of hosted Ghidra summary reuse: no game binaries."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_private_survey import SUMMARY_SCHEMA, TERMS
from validate_hosted_summary import EvidenceError, validate


class HostedSummaryTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.pins = root / "original-pins.json"
        self.pins.write_text(json.dumps([
            {"name": "DX2TestA.exe", "size": 256, "sha256": "a" * 64},
            {"name": "DX2TestB.exe", "size": 1024, "sha256": "b" * 64},
        ]))
        self.summary = root / "metadata.json"
        self.body = {
            "schema": SUMMARY_SCHEMA,
            "target_count": 2,
            "reports": [self._entry("a" * 64), self._entry("b" * 64)],
            "game_assets_included": False,
            "retail_runtime_verified": False,
            "source_assets_modified": False,
        }
        self._save()

    def _entry(self, digest):
        return {
            "schema": SUMMARY_SCHEMA,
            "pe_sha256": digest,
            "pe_role": "EXE",
            "processor": "x86:LE:32:default",
            "function_count": 100,
            "defined_data_scanned": 90,
            "scan_limit_reached": False,
            "keyword_evidence": [
                {"term": term, "defined_literal_hits": 1,
                 "candidate_function_addresses": ["00401000"]}
                for term in TERMS
            ],
            "native_writer_ready": False,
            "retail_runtime_verified": False,
            "game_assets_included": False,
        }

    def _save(self):
        self.summary.write_text(json.dumps(self.body))

    def test_strict_exact_original_fingerprints_pass(self):
        self.assertEqual(validate(self.summary, self.pins)["module_count"], 2)

    def test_refuse_missing_or_extra_binary(self):
        self.body["reports"].pop()
        self._save()
        with self.assertRaises(EvidenceError):
            validate(self.summary, self.pins)
        self.body["reports"].append(self._entry("b" * 64))
        self.body["reports"][1]["pe_sha256"] = "c" * 64
        self._save()
        with self.assertRaisesRegex(EvidenceError, "untrusted"):
            validate(self.summary, self.pins)

    def test_refuse_duplicate_sha_and_unexpected_raw_fields(self):
        self.body["reports"][1]["pe_sha256"] = "a" * 64
        self._save()
        with self.assertRaisesRegex(EvidenceError, "fingerprint"):
            validate(self.summary, self.pins)
        self.body["reports"][1]["pe_sha256"] = "b" * 64
        self.body["reports"][0]["original_disassembly"] = "private executable bytes"
        self._save()
        with self.assertRaisesRegex(EvidenceError, "untrusted"):
            validate(self.summary, self.pins)

    def test_refuse_runtime_claims_and_bad_keyword_evidence(self):
        self.body["retail_runtime_verified"] = True
        self._save()
        with self.assertRaisesRegex(EvidenceError, "root"):
            validate(self.summary, self.pins)
        self.body["retail_runtime_verified"] = False
        self.body["reports"][0]["keyword_evidence"][0]["candidate_function_addresses"] = [
            "C:\\Owner\\private\\executable"]
        self._save()
        with self.assertRaisesRegex(EvidenceError, "addresses"):
            validate(self.summary, self.pins)

    def test_refuse_malformed_address_segments(self):
        # Colons alone and repeated separators previously passed the broad
        # character allowlist, despite not being Ghidra address strings.
        for malformed in (":", "::::", "00401000:", ":00401000",
                          "00401000::00402000", "0" * 17):
            with self.subTest(address=malformed):
                self.body["reports"][0]["keyword_evidence"][0][
                    "candidate_function_addresses"] = [malformed]
                self._save()
                with self.assertRaisesRegex(EvidenceError, "addresses"):
                    validate(self.summary, self.pins)

    def test_allow_single_segment_and_segmented_ghidra_addresses(self):
        for address in ("005c56a0", "0001:005c56a0"):
            with self.subTest(address=address):
                self.body["reports"][0]["keyword_evidence"][0][
                    "candidate_function_addresses"] = [address]
                self._save()
                self.assertEqual(validate(self.summary, self.pins)["module_count"], 2)

    def test_refuse_stale_schema_and_symlinked_summary(self):
        self.body["schema"] = "older-v0"
        self._save()
        with self.assertRaises(EvidenceError):
            validate(self.summary, self.pins)
        self.body["schema"] = SUMMARY_SCHEMA
        self._save()
        link = self.summary.parent / "link.json"
        try:
            link.symlink_to(self.summary)
        except (OSError, NotImplementedError):
            return
        with self.assertRaisesRegex(EvidenceError, "symlinked"):
            validate(link, self.pins)


if __name__ == "__main__":
    unittest.main()
