"""Source-only guard for cached hosted Ghidra execution order.

Original inputs must be hash-verified on EVERY run; never trust a
cached report without rechecking its fingerprints. Java and Ghidra
should be skipped if the strict research summary already exists.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "dx2-ghidra-hosted.yml"


class HostedCachePolicyTests(unittest.TestCase):
    def test_cache_after_verified_inputs_and_before_expensive_ghidra(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        job = content.split("\n  hosted-original:\n", 1)[1]
        preflight = job.index("Verify all original full-file SHA256s before analysis")
        cache = job.index("id: safe-report-cache")
        install = job.index("Install verified Ghidra only when new analysis is necessary")
        run = job.index("Run private Ghidra only if verified metadata is not already cached")
        check = job.index("Revalidate full pinned fingerprint set and strict metadata allowlist")
        upload = job.index("Upload sanitized metadata only")
        self.assertLess(preflight, cache)
        self.assertLess(cache, install)
        self.assertLess(install, run)
        self.assertLess(run, check)
        self.assertLess(check, upload)
        self.assertIn("if: steps.safe-report-cache.outputs.cache-hit != 'true'", job)
        # The explicit save action is also guarded against cache hits.
        self.assertEqual(
            job.count("if: steps.safe-report-cache.outputs.cache-hit != 'true'"), 5
        )
        save = job.index("Save validated sanitized research cache before cleanup")
        cleanup = job.index("Delete owner original PE images and temporary findings")
        self.assertLess(upload, save)
        self.assertLess(save, cleanup)
        self.assertIn("uses: actions/cache/save@v4", job)
        self.assertIn("key: ${{ steps.safe-report-cache.outputs.cache-primary-key }}", job)
        self.assertNotIn("DX2_ORIGINAL_PE_MANIFEST_JSON", job)
        self.assertNotIn("DX2_HOSTED_GHIDRA_ENABLED", job)

    def test_unconfigured_owner_job_never_starts_analysis(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        gate = content.split("\n  owner-input-gate:\n", 1)[1].split(
            "\n  hosted-original:\n", 1
        )[0]
        self.assertIn("DX2_ORIGINAL_SYSTEM_ZIP_ID", gate)
        self.assertIn('echo "ready=false"', gate)
        self.assertIn("steps.detect.outputs.ready", gate)


if __name__ == "__main__":
    unittest.main()
