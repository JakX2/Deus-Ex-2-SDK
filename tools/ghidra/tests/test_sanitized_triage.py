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

    def test_rejects_duplicate_terms_instead_of_hiding_evidence(self):
        source = sample()
        source["reports"][0]["keyword_evidence"].append(
            {"term": "bsp", "defined_literal_hits": 999,
             "candidate_function_addresses": ["1234"]})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.triage(source)

    def test_rejects_malformed_or_unbounded_report_structure(self):
        for bad in (None, [], "not an object"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                module.triage(bad)
        source = sample()
        source["reports"].append(source["reports"][0])
        source["reports"].append(source["reports"][0])
        with self.assertRaises(ValueError):
            module.triage(source)
        source = sample()
        source["reports"][0]["keyword_evidence"] = "not a list"
        with self.assertRaises(ValueError):
            module.triage(source)

    def test_rejects_invalid_hit_counts(self):
        for hits in (-1, True, "3"):
            source = sample()
            source["reports"][0]["keyword_evidence"][0]["defined_literal_hits"] = hits
            with self.subTest(hits=hits), self.assertRaises(ValueError):
                module.triage(source)

    def test_unknown_terms_are_validated_before_ignored(self):
        source = sample()
        source["reports"][0]["keyword_evidence"].append(
            {"term": "untracked-topic", "defined_literal_hits": 1,
             "candidate_function_addresses": ["00ABCDEF"]})
        result = module.triage(source)
        self.assertNotIn("untracked-topic", result["targets"][0]["topics"])
        for field, value in (("defined_literal_hits", -1),
                             ("candidate_function_addresses", ["not-hex"])):
            bad = sample()
            bad["reports"][0]["keyword_evidence"].append(
                {"term": "untracked-topic", "defined_literal_hits": 1,
                 "candidate_function_addresses": ["00ABCDEF"]})
            bad["reports"][0]["keyword_evidence"][-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.triage(bad)

    def test_rejects_duplicate_untracked_terms(self):
        source = sample()
        item = {"term": "untracked-topic", "defined_literal_hits": 1,
                "candidate_function_addresses": ["00ABCDEF"]}
        source["reports"][0]["keyword_evidence"].extend([item, dict(item)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.triage(source)

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
