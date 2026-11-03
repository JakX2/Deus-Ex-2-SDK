"""Synthetic, asset-free tests for one-byte DX2 GameSys bool editing.

The actual original WTO Terminal bool records are separately audited from
the user's owned map. This fixture never includes game-proprietary data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / "native_editor" / "package_writer",
               ROOT / "native_editor" / "tests"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from dx2_gamesys_bool_probe import (
    compare_existing_bool, exact_bool_byte, save_isolated_bool, main
)
from test_dx2_gamesys_audit import fixture_with_gamesys
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter


class GameSysExistingBoolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "Retail" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        fixture_with_gamesys(self.source)
        pkg = Package(self.source)
        writer = PackageWriter(pkg)
        actor = ActorEdit(writer, pkg.exports[0])
        block = actor.block(237)
        block.id = (0x80 << 16) | 237
        block.data = b"\x01"
        actor.changes.append("synthetic one-byte authored bool")
        self.assertTrue(actor.commit())
        self.original = writer.write()
        self.source.write_bytes(self.original)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.opts = {
            "source_sha256": self.sha,
            "actor_export": 1, "actor_name": "StaticMeshActor__1",
            "property_id": 237, "expected": True, "replacement": False,
        }

    def test_full_package_parity_existing_boolean(self):
        report = compare_existing_bool(self.source, **self.opts)
        self.assertEqual(report["schema"], "DX2Ed-Gamesys-existing-bool-parity-v1")
        self.assertEqual(report["status"], "in-memory-exact-parity")
        self.assertEqual(report["original_value_bytes"], "01")
        self.assertEqual(report["replacement_value_bytes"], "00")
        self.assertEqual(report["changed_bytes"], 1)
        self.assertEqual(report["encoded_property_id"], (0x80 << 16) | 237)
        self.assertEqual(report["changed_byte_offsets"], [report["original_payload_offset"]])
        self.assertTrue(report["independent_full_package_byte_match"])
        self.assertFalse(report["edited_package_written"])
        self.assertFalse(report["native_godot_gamesys_write_enabled"])
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(main([
            str(self.source), "--source-sha256", self.sha,
            "--actor-export", "1", "--actor-name", "StaticMeshActor__1",
            "--property-id", "237", "--expect", "true", "--replace", "false",
        ]), 0)

    def test_output_only_in_non_source_folder_and_native_reparse(self):
        output = self.root / "Isolated" / self.source.name
        report = save_isolated_bool(self.source, output, **self.opts)
        self.assertEqual(report["status"], "isolated-boolean-gmp-written-runtime-unverified")
        self.assertTrue(report["edited_package_written"])
        self.assertFalse(report["game_runtime_verified"])
        self.assertEqual(output.read_bytes(), self.original[:report["original_payload_offset"]] +
                         b"\x00" + self.original[report["original_payload_offset"]+1:])
        self.assertEqual(self.source.read_bytes(), self.original)
        manifest = json.loads(output.with_suffix(".dx2ed-gamesys-bool.json").read_text())
        self.assertEqual(manifest["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        with self.assertRaisesRegex(FileExistsError, "overwrite"):
            save_isolated_bool(self.source, output, **self.opts)

    def test_strict_bool_types_and_source_values(self):
        for b in (0, 1, "true", "false", None, 2):
            with self.subTest(b=b), self.assertRaises(ValueError):
                exact_bool_byte(b)
        self.assertEqual(exact_bool_byte(True), b"\x01")
        self.assertEqual(exact_bool_byte(False), b"\x00")
        with self.assertRaisesRegex(ValueError, "identical"):
            compare_existing_bool(self.source, **{**self.opts, "replacement": True})
        with self.assertRaisesRegex(ValueError, "source|original|Boolean"):
            compare_existing_bool(self.source, **{**self.opts, "expected": False})

    def test_reject_wrong_actor_source_and_non_boolean_type(self):
        for overrides, message in (
            ({"source_sha256": "0" * 64}, "SHA-256 mismatch"),
            ({"actor_name": "Other__12"}, "actor export/name mismatch"),
            ({"actor_export": 2}, "actor export/name mismatch|export index not found"),
            ({"property_id": 65534}, "exactly one"),
        ):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, message):
                compare_existing_bool(self.source, **{**self.opts, **overrides})
        # Change only the encoding to integer, where size remains one byte:
        # our bool parser must still reject it.
        pkg = Package(self.source)
        w = PackageWriter(pkg)
        a = ActorEdit(w, pkg.exports[0])
        a.block(237).id = (0x0200 << 16) | 237
        a.changes.append("synthetic byte field")
        a.commit()
        result = w.write()
        self.source.write_bytes(result)
        with self.assertRaisesRegex(ValueError, "not an authored one-byte Boolean"):
            compare_existing_bool(self.source, **{**self.opts,
                "source_sha256": hashlib.sha256(result).hexdigest()})

    def test_runtime_flag_and_bad_bool_bytes_are_denied(self):
        pkg = Package(self.source)
        w = PackageWriter(pkg)
        a = ActorEdit(w, pkg.exports[0])
        a.block(237).id |= 0x40000000
        a.changes.append("synthetic runtime flag")
        a.commit()
        data = w.write()
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "not an authored one-byte Boolean"):
            compare_existing_bool(self.source, **{**self.opts,
                "source_sha256": hashlib.sha256(data).hexdigest()})
        pkg = Package(self.source)
        w = PackageWriter(pkg)
        a = ActorEdit(w, pkg.exports[0])
        a.block(237).id &= ~0x40000000
        a.block(237).data = b"\x02"
        a.changes.append("bad bool byte")
        a.commit()
        data = w.write()
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "original Boolean value"):
            compare_existing_bool(self.source, **{**self.opts,
                "source_sha256": hashlib.sha256(data).hexdigest()})

    def test_wrong_folder_names_and_prior_manifest_blocked(self):
        for target in (
            self.source,
            self.source.parent / "nested" / self.source.name,
            self.root / "Isolated" / "AnotherMap.gmp",
        ):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "separate folder"):
                save_isolated_bool(self.source, target, **self.opts)
        target = self.root / "Isolated" / self.source.name
        manifest = target.with_suffix(".dx2ed-gamesys-bool.json")
        manifest.parent.mkdir()
        manifest.write_text("preexisting")
        with self.assertRaises(FileExistsError):
            save_isolated_bool(self.source, target, **self.opts)
        self.assertEqual(manifest.read_text(), "preexisting")
        self.assertFalse(target.exists())

    def test_intentionally_faulty_writer_cannot_pass_parity(self):
        from dx2_gamesys_bool_probe import PackageWriter as OriginalWriter
        class FaultWriter(OriginalWriter):
            def write(self):
                result = bytearray(super().write())
                result[-1] ^= 1
                return bytes(result)
        with patch("dx2_gamesys_bool_probe.PackageWriter", FaultWriter):
            with self.assertRaisesRegex(ValueError, "serializers disagree"):
                compare_existing_bool(self.source, **self.opts)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_bad_package_refused_and_no_output_file_created(self):
        self.source.write_bytes(b"not a valid DX2 GMP")
        with self.assertRaises((ValueError, IndexError, EOFError)):
            save_isolated_bool(self.source, self.root / "Isolated" / self.source.name,
                              **{**self.opts, "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()})
        self.assertFalse((self.root / "Isolated" / self.source.name).exists())


if __name__ == "__main__":
    unittest.main()
