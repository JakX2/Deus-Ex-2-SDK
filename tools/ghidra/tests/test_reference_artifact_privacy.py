"""Asset-free regression for owner-original reference artifact privacy.

This checks workflow source only; it cannot verify a private hosted run.
"""
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "dx2-ghidra-hosted.yml"


class ReferenceArtifactPrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_only_address_free_reference_summary_uploaded(self):
        source = self.source
        self.assertIn("summarize_reference_coverage.py", source)
        self.assertIn("dx2_reference_coverage.json", source)
        self.assertNotIn("path: ${{ runner.temp }}/dx2-metadata/dx2_reference_edges.json", source)
        self.assertNotIn("name: dx2-static-reference-edges-", source)
        artifact_steps = re.findall(
            r"(?ms)^      - name: ([^\\n]+)\\n(?:(?!^      - name: ).)*?uses: actions/upload-artifact@v4\\n(?:(?!^      - name: ).)*?path: ([^\\n]+)",
            source,
        )
        reference_uploads = [(name, path) for name, path in artifact_steps
                             if "reference" in name.lower() or "reference" in path.lower()]
        self.assertEqual(len(reference_uploads), 1)
        self.assertIn("dx2_reference_coverage.json", reference_uploads[0][1])

    def test_private_evidence_deleted_on_all_outcomes(self):
        self.assertIn("if: always()", self.source)
        self.assertIn('rm -rf -- "$RUNNER_TEMP/dx2-owner-private" "$RUNNER_TEMP/dx2-metadata"', self.source)


if __name__ == "__main__":
    unittest.main()
