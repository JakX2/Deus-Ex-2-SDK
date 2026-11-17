"""Source-only tests: no original game files or Ghidra required."""
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "triage_sanitized_summary.py"
spec = importlib.util.spec_from_file_location("dx2_triage", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    return {"schema": "DX2-GhidraPrivateSummary-v1", "game_assets_included": False,
            "reports": [{"game_assets_included": False, "pe_sha256": "a" * 64,
                         "function_count": 42, "native_writer_ready": False,
                         "retail_runtime_verified": False,
                         "keyword_evidence": [
                             {"term": "bsp", "defined_literal_hits": 2,
                              "candidate_function_addresses": ["0060EB20"]},
                             {"term": "havok", "defined_literal_hits": 1,
                              "candidate_function_addresses": ["0060eb20"]},
                             {"term": ".ibd", "defined_literal_hits": 0,
                              "candidate_function_addresses": []}]}]}


class TriageTests(unittest.TestCase):
    def test_overlap_is_correlation_not_api(self):
        result = module.triage(sample())
        target = result["targets"][0]
        self.assertEqual(target["overlaps"],
                         [{"address": "0060eb20", "terms": ["bsp", "havok"]}])
        self.assertEqual(target["topics"][".ibd"]["candidate_function_addresses"], [])
        self.assertFalse(target["native_writer_ready"])
        self.assertIn("no verified calls", result["disclaimer"])

    def test_refuses_unsanitized(self):
        source = sample()
        source["game_assets_included"] = True
        with self.assertRaises(ValueError):
            module.triage(source)

    def test_refuses_nonhex_address(self):
        source = sample()
        source["reports"][0]["keyword_evidence"][0]["candidate_function_addresses"] = ["0x0060eb20"]
        with self.assertRaises(ValueError):
            module.triage(source)

    def test_refuses_unbounded_candidates(self):
        source = sample()
        source["reports"][0]["keyword_evidence"][0]["candidate_function_addresses"] = ["abcd"] * 65
        with self.assertRaises(ValueError):
            module.triage(source)


if __name__ == "__main__":
    unittest.main()
