"""Asset-free guard against accidental private reference artifact publication.

This deliberately checks every upload-artifact step, not only steps whose name
contains 'reference'. Renaming an upload must not bypass the guard.
"""
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "dx2-ghidra-hosted.yml"
PRIVATE_NAMES = ("dx2_reference_edges.json", "dx2-owner-private", "dx2_reference_edges")
COVERAGE_NAME = "dx2_reference_coverage.json"


class ReferenceUploadAllowlistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.steps = cls.source.split("      - name: ")

    def test_all_artifact_uploads_exclude_private_evidence(self):
        uploads = [s for s in self.steps if re.search(
            r"(?m)^\s*uses:\s*actions/upload-artifact@v4\s*$", s)]
        self.assertTrue(uploads, "Workflow has no upload steps to audit")
        for step in uploads:
            # Scan the complete step, including path and artifact name.
            for private_name in PRIVATE_NAMES:
                self.assertNotIn(private_name, step)
            if COVERAGE_NAME in step:
                self.assertRegex(step, r"(?m)^\s*path:\s*\$\{\{ runner.temp \}\}/dx2-metadata/dx2_reference_coverage\.json\s*$")
                self.assertIn("if-no-files-found: error", step)

    def test_summary_is_generated_before_upload_and_cleanup_remains(self):
        generation = self.source.index("summarize_reference_coverage.py")
        upload = self.source.index("path: ${{ runner.temp }}/dx2-metadata/dx2_reference_coverage.json")
        cleanup = self.source.index('rm -rf -- "$RUNNER_TEMP/dx2-owner-private" "$RUNNER_TEMP/dx2-metadata"')
        self.assertLess(generation, upload)
        self.assertLess(upload, cleanup)
        self.assertIn("if: always()", self.source)


if __name__ == "__main__":
    unittest.main()
