"""Source-only guardrails for the bounded DX2 Ghidra reference collector.

These checks inspect Java source. They do not compile or execute Ghidra and
cannot establish any retail executable or engine behavior.
"""
from pathlib import Path
import re
import unittest

COLLECTOR = Path(__file__).resolve().parents[1] / "ghidra" / "DX2BoundedReferenceCollector.java"


class CollectorSourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = COLLECTOR.read_text(encoding="utf-8")

    def test_unverified_candidate_set(self):
        expected = {
            "005c56a0", "005c5c69", "005be1b0", "005febd0",
            "00606c50", "00623a00", "0060cdf0", "0060a690",
            "0060a900", "0060b9b0", "0060cbb0",
        }
        targets = re.search(r"String\[\] TARGETS\s*=\s*\{([^}]*)\}", self.source, re.S)
        self.assertIsNotNone(targets)
        self.assertEqual(set(re.findall(r'"([0-9a-f]{8})"', targets.group(1))), expected)

    def test_bounded_fail_closed_output(self):
        source = self.source
        self.assertRegex(source, r"MAX_EDGES\s*=\s*512\s*;")
        self.assertIn("edges.size() == MAX_EDGES", source)
        self.assertIn("throw new IllegalStateException", source)
        self.assertIn("json.getBytes(StandardCharsets.UTF_8).length > 131072", source)
        self.assertIn("if (output.exists())", source)
        self.assertLess(source.index("if (json.getBytes("), source.index("new FileOutputStream(output)"))

    def test_privacy_and_static_only_schema(self):
        source = self.source
        for field in ('executable_sha256', 'reference_kind', 'caller', 'callee'):
            self.assertIn(field, source)
        self.assertIn('runtime_verified\\":false', source)
        self.assertIn('native_writer_ready\\":false', source)
        self.assertIn('getReferencesTo(address)', source)
        self.assertIn('monitor.checkCancelled()', source)
        self.assertNotIn('getDecompiledFunction(', source)
        self.assertNotIn('getAllStrings(', source)

    def test_external_hash_is_not_claimed_as_self_verified(self):
        source = self.source
        self.assertIn("independently checked against owner-approved pins", source)
        self.assertIn('args.length != 2', source)
        self.assertIn('[0-9a-f]{64}', source)


if __name__ == "__main__":
    unittest.main()
