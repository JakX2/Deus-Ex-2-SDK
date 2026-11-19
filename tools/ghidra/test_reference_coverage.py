"""Asset-free regression tests for address-free private reference coverage."""
import copy
import unittest

from summarize_reference_coverage import summarize


class CoverageTests(unittest.TestCase):
    def fixture(self):
        return {
            "schema": "DX2-SanitizedCallEdges-v1",
            "executable_sha256": "a" * 64,
            "ghidra_version": "12.2",
            "runtime_verified": False,
            "native_writer_ready": False,
            "edges": [],
        }

    def test_empty_is_not_evidence(self):
        result = summarize(self.fixture())
        self.assertEqual(result["targets_with_references"], 0)
        self.assertEqual(result["targets_without_references"], 11)
        self.assertFalse(result["function_ownership_verified"])
        self.assertFalse(result["loader_or_actor_registration_verified"])

    def test_equivalent_destination_spellings_group_together(self):
        doc = self.fixture()
        doc["edges"] = [
            {"caller": "100", "callee": "005c56a0", "reference_kind": "CALL"},
            {"caller": "101", "callee": "5C56A0", "reference_kind": "DATA"},
            {"caller": "102", "callee": "abcdef", "reference_kind": "JUMP"},
        ]
        result = summarize(doc)
        self.assertEqual(result["targets_with_references"], 1)
        self.assertEqual(result["out_of_scope_destinations"], 1)
        self.assertEqual(result["reference_kinds"], {"CALL": 1, "JUMP": 1, "DATA": 1})
        self.assertNotIn("005c56a0", str(result))
        self.assertNotIn("abcdef", str(result))
        self.assertNotIn("a" * 64, str(result))

    def test_reject_unvalidated_private_fields(self):
        doc = self.fixture()
        doc["raw_strings"] = "must never appear"
        with self.assertRaises(ValueError):
            summarize(doc)

    def test_reject_false_runtime_claim(self):
        doc = self.fixture()
        doc["runtime_verified"] = True
        with self.assertRaises(ValueError):
            summarize(doc)


if __name__ == "__main__":
    unittest.main()
