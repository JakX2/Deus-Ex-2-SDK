"""Synthetic-only DX2SDK v0.7 LightColor tagged-byte edit tests.

Uses invented GMP actor/GameSys data and original-schema research, without
redistributing any Ion Storm map bytes, scripts, or textures.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dx2sdk import DX2Map
from dx2sdk.light_colors import PROPERTY_ID, ENCODED_ID, SCHEMA
from test_dx2_gamesys_audit import fixture_with_gamesys
from tools.build_dx2sdk_source_release import build, ARCHIVE
from dx2inspect import Package as DX2Package
from upkg import Package as T3Package
from upkgwrite import ActorEdit, PackageWriter, enc_index


def synthetic_lightcolor_map(path: Path, *, bad: str = "") -> bytes:
    fixture_with_gamesys(path)
    t3 = T3Package(path)
    writer = PackageWriter(t3)
    name_indices = {n: writer.name_index(n) for n in (
        "None", "LightBrightness", "LightHue", "LightSaturation")}
    raw = b"".join(
        enc_index(name_indices[n]) + b"\x01" + bytes([v])
        for n, v in zip(
            ("LightBrightness", "LightHue", "LightSaturation"),
            (96, 150, 32))
    ) + enc_index(name_indices["None"])
    if len(raw) != 10:
        raise RuntimeError("Fixture requires one-byte compact name indices")
    actor = ActorEdit(writer, t3.exports[0])
    target = actor.block(237)
    if target is None:
        raise RuntimeError("Missing synthetic GameSys placeholder")
    target.id = ENCODED_ID | (0x40000000 if bad == "runtime" else 0)
    target.version = 2 if bad == "version" else 1
    if bad == "wrong-name":
        raw = (enc_index(name_indices["LightHue"]) + raw[1:])
    elif bad == "extra-byte":
        raw += b"\x00"
    elif bad == "nonbyte-tag":
        raw = raw[:1] + b"\x02" + raw[2:]
    elif bad == "duplicate":
        other = actor.block(43)
        other.id = ENCODED_ID
        other.data = raw
    target.data = raw
    actor.changes.append("invented exact LightColor data for SDK fixture")
    assert actor.commit()
    data = writer.write()
    path.write_bytes(data)
    return data


class LightColorSourceOnlySDKTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="dx2sdk_v07_lightcolor_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "Original" / "M1_Synthetic.gmp"
        self.source.parent.mkdir()
        self.original = synthetic_lightcolor_map(self.source)
        self.world = DX2Map.open(self.source)
        self.output = self.root / "Private" / self.source.name
        self.options = dict(
            export=1, actor="StaticMeshActor__1", expected=(96, 150, 32),
            changes={"brightness": 255, "saturation": 255}, output=self.output)

    def cli(self, *args, cwd=ROOT):
        return subprocess.run(
            [sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=cwd, capture_output=True, text=True, timeout=60)

    def test_scan_verified_original_nested_names_bytes_and_position(self):
        found = self.world.original_light_colors(limit=10)
        self.assertEqual(found["schema"], SCHEMA)
        self.assertEqual(found["eligible_actor_count"], 1)
        item = found["shown"][0]
        self.assertEqual(item["actor"], "StaticMeshActor__1")
        self.assertEqual(item["original_values"],
                         {"brightness": 96, "hue": 150, "saturation": 32})
        self.assertFalse(item["actual_gameplay_effect_for_this_actor_verified"])
        self.assertEqual(self.world.original_light_colors(limit=0)["shown"], [])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_candidate_listing_only_scans_original_level_members_once(self):
        source_reader = self.world._package.scene_actors
        with patch.object(self.world._package, "scene_actors", wraps=source_reader) as call:
            self.assertEqual(self.world.original_light_colors()["eligible_actor_count"], 1)
            self.assertEqual(call.call_count, 1)

    def test_dual_writer_mismatch_fails_before_creating_any_output(self):
        from dx2sdk.light_colors import PackageWriter as CorrectWriter
        class CorruptWriter(CorrectWriter):
            def write(self):
                raw = bytearray(super().write())
                raw[-1] ^= 0x20
                return bytes(raw)
        with patch("dx2sdk.light_colors.PackageWriter", CorruptWriter):
            with self.assertRaisesRegex(ValueError, "serializers disagree"):
                self.world.set_existing_light_color(**self.options, write=True)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix(".dx2sdk-lightcolor.json").exists())

    def test_dryrun_and_optin_write_differ_at_exact_original_fields(self):
        dry = self.world.set_existing_light_color(**self.options)
        self.assertEqual(dry["status"], "dry-run")
        self.assertEqual(dry["changed_bytes"], 2)
        self.assertTrue(dry["dual_serializer_full_package_match"])
        self.assertFalse(self.output.exists())
        saved = self.world.set_existing_light_color(**self.options, write=True)
        self.assertTrue(saved["verified_binary_structure"])
        verified = self.world.verify_saved_light_color(self.output)
        self.assertTrue(verified["verified_binary_structure"])
        self.assertEqual(verified["unapproved_bytes"], 0)
        self.assertEqual(self.source.read_bytes(), self.original)
        changed = [i for i, (a, b) in enumerate(zip(self.original,self.output.read_bytes()))
                   if a != b]
        self.assertEqual(sorted(changed), sorted(x["absolute_offset"] for x in dry["edits"]))
        self.assertEqual(len(changed), 2)
        updated = DX2Package(self.output)
        self.assertEqual(updated.exports, DX2Package(self.source).exports)
        with self.assertRaises(ValueError):
            self.world.set_existing_light_color(**self.options, write=True)

    def test_single_field_changes_and_input_strictness(self):
        for changes in ({"brightness": 0}, {"hue": 1}, {"saturation": 0}):
            with self.subTest(changes=changes):
                report = self.world.set_existing_light_color(
                    **{**self.options, "changes": changes})
                self.assertEqual(report["changed_bytes"], 1)
        for changes in ({}, {"brightness": 96}, {"hue": True},
                        {"hue": -1}, {"hue": 256}, {"madeup": 42},
                        {"brightness": 99.0}, {"hue": 3, "madeup": 5}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.world.set_existing_light_color(
                    **{**self.options, "changes": changes})
        for wrong in ((96, 150, 33), (96, 150), (True, 150, 32),
                      (96., 150, 32), [96, 150, 256]):
            with self.subTest(expected=wrong), self.assertRaises(ValueError):
                self.world.set_existing_light_color(
                    **{**self.options, "expected": wrong})
        with self.assertRaises(ValueError):
            self.world.original_light_colors(limit=1001)
        with self.assertRaises(ValueError):
            self.world.set_existing_light_color(
                **{**self.options, "actor": "Other"})
        with self.assertRaises(ValueError):
            self.world.set_existing_light_color(
                **{**self.options, "export": True})

    def test_reject_unsupported_original_struct_and_runtime_fields(self):
        for bad in ("wrong-name", "extra-byte", "nonbyte-tag",
                    "runtime", "version", "duplicate"):
            with self.subTest(bad=bad):
                original = synthetic_lightcolor_map(self.source, bad=bad)
                world = DX2Map.open(self.source)
                self.assertEqual(world.original_light_colors()["eligible_actor_count"], 0)
                with self.assertRaises((ValueError, IndexError)):
                    world.set_existing_light_color(**self.options)
                self.assertEqual(self.source.read_bytes(), original)
                self.assertFalse(self.output.exists())
        self.source.write_bytes(self.original)

    def test_refuses_other_games_maps_source_drift_and_forged_manifest(self):
        for unsafe in (
            self.source,
            self.source.parent / "Nested" / self.source.name,
            self.root / "OtherGame" / "Content" / "DX2" / "Maps" / self.source.name,
            self.root / "Wrong.gmp",
        ):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                self.world.set_existing_light_color(
                    **{**self.options, "output": unsafe})
        self.world.set_existing_light_color(**self.options, write=True)
        manifest = self.output.with_suffix(".dx2sdk-lightcolor.json")
        original_manifest = manifest.read_text()
        altered = json.loads(original_manifest)
        altered["visible_lighting_effect_verified"] = True
        manifest.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "Untrusted"):
            self.world.verify_saved_light_color(self.output)
        manifest.write_text(original_manifest)
        altered = json.loads(original_manifest)
        altered["edits"][0]["absolute_offset"] += 1
        manifest.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "source replay"):
            self.world.verify_saved_light_color(self.output)
        manifest.write_text(original_manifest)
        raw = bytearray(self.output.read_bytes())
        raw[-1] ^= 0x01
        self.output.write_bytes(raw)
        altered = json.loads(original_manifest)
        altered["output_sha256"] = hashlib.sha256(raw).hexdigest()
        manifest.write_text(json.dumps(altered))
        with self.assertRaises(ValueError):
            self.world.verify_saved_light_color(self.output)
        self.source.write_bytes(self.original + b"tampered")
        with self.assertRaises(ValueError):
            self.world.original_light_colors()

    def test_extracted_portable_has_full_color_workflow(self):
        zipped = self.root / "dx2sdk-v07.zip"
        build(ROOT, zipped)
        with ZipFile(zipped) as z:
            self.assertIn(f"{ARCHIVE}/dx2sdk/light_colors.py", z.namelist())
            z.extractall(self.root / "unpacked")
        sdk = self.root / "unpacked" / ARCHIVE
        listed = self.cli("light-colors", "--map", str(self.source), cwd=sdk)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout)["eligible_actor_count"], 1)
        args = ("set-light-color", "--map", str(self.source),
                "--export", "1", "--actor", "StaticMeshActor__1",
                "--expect", "96", "150", "32",
                "--brightness", "255", "--saturation", "255",
                "--output", str(self.output))
        dry = self.cli(*args, cwd=sdk)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["status"], "dry-run")
        self.assertFalse(self.output.exists())
        written = self.cli(*args, "--write", cwd=sdk)
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(json.loads(written.stdout)["verified_binary_structure"])
        verified = self.cli(
            "verify-light-color", "--map", str(self.source),
            "--output", str(self.output), cwd=sdk)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["changed_bytes"], 2)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
