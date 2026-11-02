"""No-retail-assets tests for independent preflight of an isolated DX2 GMP."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "native_editor" / "package_writer",
             ROOT / "native_editor" / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_dx2_gamesys_audit import fixture_with_gamesys
from dx2_gamesys_scalar_probe import save_verified_scalar_copy
from dx2_gamesys_runtime_preflight import (
    verify_isolated_scalar, main, SCHEMA
)


class IsolatedGameSysBinaryPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "OriginalMaps" / "M1_Synthetic.gmp"
        self.original.parent.mkdir()
        self.source_data = fixture_with_gamesys(self.original)
        self.candidate = self.root / "IsolatedTest" / self.original.name
        self.manifest = self.candidate.with_suffix(".dx2ed-gamesys-scalar.json")
        self.kw = dict(
            source_sha256=hashlib.sha256(self.source_data).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            property_id=237, kind="float", expected=2.5, replacement=4.25,
        )
        self.saved = save_verified_scalar_copy(self.original, self.candidate, **self.kw)

    def test_preflight_original_and_candidate_match_exact_byte_diff(self):
        checked = verify_isolated_scalar(self.original, self.candidate)
        self.assertEqual(checked["schema"], SCHEMA)
        self.assertEqual(checked["status"], "binary-preflight-passed-runtime-not-tested")
        self.assertEqual(checked["original_sha256"], self.kw["source_sha256"])
        self.assertEqual(checked["edited_sha256"], self.saved["output_sha256"])
        self.assertEqual(checked["original_value"], 2.5)
        self.assertEqual(checked["edited_value"], 4.25)
        self.assertEqual(checked["property_id"], 237)
        self.assertEqual(checked["actor"], "StaticMeshActor__1")
        self.assertTrue(checked["source_and_edited_blocks_verified"])
        self.assertFalse(checked["game_runtime_tested"])
        self.assertFalse(checked["gameplay_effect_confirmed"])
        self.assertTrue(all(
            checked["original_payload_offset"] <= n < checked["original_payload_offset"]+4
            for n in checked["changed_byte_offsets"]))
        self.assertEqual(self.source_data, self.original.read_bytes())

    def test_refuse_modified_byte_outside_declared_game_property(self):
        raw = bytearray(self.candidate.read_bytes())
        raw[-1] ^= 0x80
        self.candidate.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "reconstructed_sha256|output_sha256"):
            verify_isolated_scalar(self.original, self.candidate)
        self.assertEqual(self.original.read_bytes(), self.source_data)

    def test_forged_updated_hashes_still_cannot_hide_other_changed_bytes(self):
        raw = bytearray(self.candidate.read_bytes())
        # Alter a byte outside the original four-byte scalar payload.
        # The checker must not rely only on manifest SHA claims.
        raw[-1] ^= 1
        self.candidate.write_bytes(raw)
        manifest = json.loads(self.manifest.read_text())
        hash2 = hashlib.sha256(raw).hexdigest()
        manifest["reconstructed_sha256"] = hash2
        manifest["output_sha256"] = hash2
        manifest["changed_bytes"] = self.saved["changed_bytes"] + 1
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "outside its four-byte"):
            verify_isolated_scalar(self.original, self.candidate)
        self.assertEqual(self.original.read_bytes(), self.source_data)

    def test_manifest_cannot_shift_writable_offset_or_actor_identity(self):
        for key, value, message in (
            ("original_payload_offset", self.saved["original_payload_offset"]+1, "Recorded scalar bytes"),
            ("actor", "WrongActor", "actor export identity"),
            ("property_version", 999, "property framing"),
            ("changed_bytes", 3, "diff count"),
            ("original_sha256", "0"*64, "original_sha256"),
            ("runtime_verified", True, "runtime-unverified"),
            ("encoded_property_id", 0, "property framing"),
        ):
            with self.subTest(key=key):
                src = json.loads(self.manifest.read_text())
                src[key] = value
                self.manifest.write_text(json.dumps(src))
                with self.assertRaisesRegex(ValueError, message):
                    verify_isolated_scalar(self.original, self.candidate)
                self.manifest.write_text(json.dumps(self.saved))
        self.assertEqual(self.source_data, self.original.read_bytes())

    def test_reject_wrong_input_files_and_relocated_manifest(self):
        with self.assertRaisesRegex(ValueError, "outside the original"):
            verify_isolated_scalar(self.original, self.original)
        wrong = self.root / "IsolatedTest" / "Renamed.gmp"
        wrong.write_bytes(self.candidate.read_bytes())
        with self.assertRaisesRegex(ValueError, "same-named"):
            verify_isolated_scalar(self.original, wrong)
        with self.assertRaisesRegex(ValueError, "adjacent exact-name"):
            verify_isolated_scalar(self.original, self.candidate,
                                   manifest_path=self.root / "bad.json")

    def test_read_only_cli_can_emit_separate_new_report(self):
        report = self.root / "Research" / "preflight.json"
        result = main([
            "--original", str(self.original),
            "--candidate", str(self.candidate),
            "--report", str(report),
        ])
        self.assertEqual(result, 0)
        saved = json.loads(report.read_text())
        self.assertEqual(saved["status"], "binary-preflight-passed-runtime-not-tested")
        self.assertFalse(saved["game_runtime_tested"])
        self.assertEqual(main([
            "--original", str(self.original), "--candidate", str(self.candidate),
            "--report", str(report)]), 1)
        self.assertEqual(self.original.read_bytes(), self.source_data)

    def test_corrupted_manifest_never_writes_or_overwrites_any_source(self):
        self.manifest.write_text("{ corrupt json")
        with self.assertRaises(ValueError):
            verify_isolated_scalar(self.original, self.candidate)
        self.assertEqual(self.original.read_bytes(), self.source_data)
        self.assertTrue(self.candidate.is_file())

    def test_preflight_accepts_negative_existing_int32(self):
        from upkg import Package
        from upkgwrite import PackageWriter, ActorEdit
        import shutil
        int_original = self.root / "Other" / "M1_Int.gmp"
        int_original.parent.mkdir()
        shutil.copyfile(self.original, int_original)
        pkg = Package(int_original)
        writer = PackageWriter(pkg)
        actor = ActorEdit(writer, pkg.exports[0])
        target = actor.block(237)
        target.id = (0x20 << 16) | 237
        target.data = struct.pack("<i", -5)
        actor.changes.append("int fixture")
        actor.commit()
        original_int = writer.write()
        int_original.write_bytes(original_int)
        new = self.root / "OtherEdited" / int_original.name
        saved = save_verified_scalar_copy(
            int_original, new, source_sha256=hashlib.sha256(original_int).hexdigest(),
            actor_export=1, actor_name="StaticMeshActor__1",
            property_id=237, kind="int", expected=-5, replacement=42)
        verified = verify_isolated_scalar(int_original, new)
        self.assertEqual(verified["scalar_type"], "int")
        self.assertEqual(verified["original_value"], -5)
        self.assertEqual(verified["edited_value"], 42)
        self.assertEqual(verified["edited_sha256"], saved["output_sha256"])


if __name__ == "__main__":
    unittest.main()
