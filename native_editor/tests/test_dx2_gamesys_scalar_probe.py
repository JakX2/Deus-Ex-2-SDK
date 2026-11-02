"""Asset-free native DX2 GameSys scalar dual-writer compatibility tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for source in (ROOT / "native_editor" / "package_writer",
               ROOT / "native_editor" / "tests"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

from test_dx2_gamesys_audit import fixture_with_gamesys
from dx2_gamesys_scalar_probe import compare_gamesys_scalar, save_verified_scalar_copy, scalar_bytes, main
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter


class NativeGameSysScalarDualWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "M1_OriginalFixture.gmp"
        self.raw = fixture_with_gamesys(self.source)
        self.sha = hashlib.sha256(self.raw).hexdigest()

    def probe(self, **kwargs):
        arguments = {
            "source": self.source, "source_sha256": self.sha,
            "actor_export": 1, "actor_name": "StaticMeshActor__1",
            "property_id": 237, "kind": "float",
            "expected": 2.5, "replacement": 4.25,
        }
        arguments.update(kwargs)
        return compare_gamesys_scalar(**arguments)

    def test_original_existing_float_game_property_agrees_exactly(self):
        result = self.probe()
        self.assertEqual(result["schema"], "DX2Ed-Gamesys-scalar-dual-writer-v1")
        self.assertTrue(result["full_package_byte_match"])
        self.assertEqual(result["encoded_property_id"], (0x10 << 16) | 237)
        self.assertEqual(result["original_value_bytes"], struct.pack("<f", 2.5).hex())
        self.assertEqual(result["proposed_value_bytes"], struct.pack("<f", 4.25).hex())
        self.assertGreater(result["changed_bytes"], 0)
        self.assertLessEqual(result["changed_bytes"], 4)
        self.assertFalse(result["edited_package_written"])
        self.assertFalse(result["native_gamesys_save_enabled"])
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertEqual(main([
            str(self.source), "--source-sha256", self.sha,
            "--actor-export", "1", "--actor-name", "StaticMeshActor__1",
            "--property-id", "237", "--kind", "float",
            "--expect", "2.5", "--replace", "4.25",
        ]), 0)

    def test_int32_uses_same_native_block_validation_without_float_coercion(self):
        # Synthetic int block created using T3SDK first, then the dual
        # writer must independently reconstruct EXACT four-byte delta.
        pkg = Package(self.source)
        writer = PackageWriter(pkg)
        edit = ActorEdit(writer, pkg.exports[0])
        target = edit.block(237)
        self.assertIsNotNone(target)
        target.id = (0x20 << 16) | 237
        target.data = struct.pack("<i", 40)
        edit.changes.append("synthetic int fixture")
        edit.commit()
        self.raw = writer.write()
        self.source.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()
        result = self.probe(kind="int", expected=40, replacement=-5)
        self.assertEqual(result["original_value_bytes"], struct.pack("<i", 40).hex())
        self.assertEqual(result["proposed_value_bytes"], struct.pack("<i", -5).hex())
        self.assertEqual(result["kind"], "int")
        self.assertTrue(result["full_package_byte_match"])
        self.assertEqual(self.raw, self.source.read_bytes())

    def test_wrong_actor_hash_value_type_and_missing_property_are_denied(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.probe(source_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "identity"):
            self.probe(actor_name="OtherActor")
        with self.assertRaisesRegex(ValueError, "exactly once"):
            self.probe(property_id=999)
        with self.assertRaisesRegex(ValueError, "not a unique"):
            self.probe(kind="int", expected=2, replacement=3)
        with self.assertRaisesRegex(ValueError, "Pinned scalar"):
            self.probe(expected=1.5)
        with self.assertRaisesRegex(ValueError, "identical"):
            self.probe(replacement=2.5)
        self.assertEqual(self.raw, self.source.read_bytes())

    def test_object_and_unknown_or_struct_blocks_cannot_be_guessed_scalars(self):
        with self.assertRaisesRegex(ValueError, "not a unique"):
            self.probe(property_id=43, expected=0.0, replacement=1.0)
        with self.assertRaisesRegex(ValueError, "not a unique"):
            self.probe(property_id=175, expected=1.0, replacement=2.0)
        self.assertEqual(self.raw, self.source.read_bytes())

    def test_scalar_bounds(self):
        for bad in [True, 2 ** 32, -(2 ** 40), 3.25]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                scalar_bytes("int", bad)
        for bad in [True, "4.0", float("nan"), float("inf"),
                    float("-inf"), 1e38]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                scalar_bytes("float", bad)
        self.assertEqual(scalar_bytes("int", -(2**31)),
                         struct.pack("<i", -(2**31)))

    def test_faulty_structured_writer_fails_without_creating_file(self):
        from dx2_gamesys_scalar_probe import PackageWriter as RealWriter

        class FaultWriter(RealWriter):
            def write(self):
                b = bytearray(super().write())
                b[-1] ^= 1
                return bytes(b)

        # The original no-op baseline is also strict, and a malicious
        # writer cannot bypass either full-package compare.
        with patch("dx2_gamesys_scalar_probe.PackageWriter", FaultWriter):
            with self.assertRaisesRegex(ValueError, "serializers disagree"):
                self.probe()
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertEqual(list(self.source.parent.glob("*.gmp")),
                         [self.source])

    def test_explicit_isolated_save_as_writes_only_verified_single_scalar(self):
        output = self.source.parent.parent / "IsolatedEdited" / self.source.name
        result = save_verified_scalar_copy(
            self.source, output, source_sha256=self.sha,
            actor_export=1, actor_name="StaticMeshActor__1",
            property_id=237, kind="float", expected=2.5, replacement=4.25)
        self.assertEqual(result["status"], "written-isolated-runtime-unverified")
        self.assertTrue(result["edited_package_written"])
        self.assertTrue(result["experimental_single_scalar_save_as"])
        self.assertFalse(result["native_gamesys_save_enabled"])
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),
                         result["reconstructed_sha256"])
        expected_changed = (self.raw[:result["original_payload_offset"]] +
                            struct.pack("<f", 4.25) +
                            self.raw[result["original_payload_offset"]+4:])
        self.assertEqual(output.read_bytes(), expected_changed)
        manifest = output.with_suffix(".dx2ed-gamesys-scalar.json")
        self.assertEqual(__import__("json").loads(manifest.read_text())["status"],
                         "written-isolated-runtime-unverified")
        with self.assertRaisesRegex(FileExistsError, "overwrite"):
            save_verified_scalar_copy(
                self.source, output, source_sha256=self.sha,
                actor_export=1, actor_name="StaticMeshActor__1",
                property_id=237, kind="float", expected=2.5, replacement=4.25)

    def test_isolated_save_as_rejects_retail_folder_nested_and_wrong_name(self):
        sources = [
            self.source,
            self.source.parent / self.source.name,
            self.source.parent / "Nested" / self.source.name,
            self.source.parent.parent / "Isolated" / "WrongMap.gmp",
        ]
        for output in sources:
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "separate folder"):
                    save_verified_scalar_copy(
                        self.source, output, source_sha256=self.sha,
                        actor_export=1, actor_name="StaticMeshActor__1",
                        property_id=237, kind="float",
                        expected=2.5, replacement=4.25)
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_existing_manifest_is_never_overwritten_or_deleted(self):
        output = self.source.parent.parent / "Isolated" / self.source.name
        manifest = output.with_suffix(".dx2ed-gamesys-scalar.json")
        manifest.parent.mkdir()
        manifest.write_text("precious file", encoding="utf8")
        with self.assertRaises(FileExistsError):
            save_verified_scalar_copy(
                self.source, output, source_sha256=self.sha,
                actor_export=1, actor_name="StaticMeshActor__1",
                property_id=237, kind="float", expected=2.5, replacement=4.25)
        self.assertEqual(manifest.read_text(), "precious file")
        self.assertFalse(output.exists())

    def test_no_output_written_on_hash_mismatch(self):
        output = self.source.parent.parent / "Isolated" / self.source.name
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            save_verified_scalar_copy(
                self.source, output, source_sha256="0" * 64,
                actor_export=1, actor_name="StaticMeshActor__1",
                property_id=237, kind="float", expected=2.5, replacement=4.25)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".dx2ed-gamesys-scalar.json").exists())

    def test_bad_source_or_nonoriginal_name_does_not_write(self):
        self.source.write_bytes(b"broken original package")
        self.sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaises((ValueError, IndexError, EOFError)):
            self.probe()
        self.assertEqual(list(self.source.parent.glob("*.gmp")), [self.source])


if __name__ == "__main__":
    unittest.main()
