"""Asset-free contract tests for the private Ghidra ownership collector."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "DX2PrivateFunctionOwnership.java"

class PrivateOwnershipContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SOURCE.read_text(encoding="utf-8")

    def test_ownership_is_derived_from_reference_site(self):
        self.assertIn("getFunctionContaining(from)", self.code)
        self.assertIn("getFunctionContaining(destination)", self.code)
        self.assertIn("getEntryPoint().equals(destination)", self.code)
        self.assertIn("source_function_entry", self.code)
        self.assertIn("destination_containing_function_entry", self.code)
        self.assertIn("destination_is_function_entry", self.code)

    def test_private_evidence_is_bounded_and_non_overwriting(self):
        self.assertIn("MAX_EDGES = 512", self.code)
        self.assertIn("edges.size() >= MAX_EDGES", self.code)
        self.assertIn("196608", self.code)
        self.assertIn("StandardOpenOption.CREATE_NEW", self.code)
        self.assertIn("monitor.checkCancelled()", self.code)
        self.assertIn("if (!seen.add(key)) continue", self.code)

    def test_semantic_claims_remain_false(self):
        for marker in ('runtime_verified', 'loader_verified', 'actor_registration_verified'):
            self.assertIn('\\\"' + marker + '\\\"', self.code)
        self.assertIn("false", self.code)

if __name__ == "__main__":
    unittest.main()
