"""Fixture-only tests for the private reference harness (no retail input)."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "ghidra" / "run_private_reference_collection.py"
spec = importlib.util.spec_from_file_location("private_refs", SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class PrivateReferenceHarnessTests(unittest.TestCase):
    def test_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "DX2Main.exe"
            image.write_bytes(b"synthetic fixture")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            pin = {"name": image.name, "size": image.stat().st_size, "sha256": digest}
            self.assertEqual(harness.authenticate(image, [pin]), digest)
            for pins in ([], [pin, pin], [dict(pin, size=0)], [dict(pin, sha256="0"*64)]):
                with self.subTest(pins=pins), self.assertRaises(ValueError):
                    harness.authenticate(image, pins)
            image.write_bytes(b"synthetic fixturE")
            with self.assertRaises(ValueError):
                harness.authenticate(image, [pin])

    def test_scope(self):
        digest = "a"*64
        def report(caller="005c5000", callee="005c56a0", fingerprint=digest):
            return {"executable_sha256": fingerprint,
                    "edges": [{"caller": caller, "callee": callee}]}
        harness.check_scope(report(), digest)
        for doc in (report(callee="005c56a1"), report(caller="0001:005c5000"),
                    report(caller="100000000"), report(caller="-1"),
                    report(fingerprint="b"*64)):
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                harness.check_scope(doc, digest)


if __name__ == "__main__":
    unittest.main()
