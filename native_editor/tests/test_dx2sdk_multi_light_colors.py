"""Synthetic 2..8-source-authored DX2SDK LightColor batch regression.

No proprietary retail bytes, original color assets or shipped maps.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dx2sdk import DX2Map
from dx2sdk.light_colors import ENCODED_ID
from dx2sdk.multi_light_colors import PLAN_SCHEMA, SCHEMA
from test_dx2_actor_clone_probe import level_fixture
from dx2_actor_clone_probe import clone_in_memory
from tools.build_dx2sdk_source_release import build, ARCHIVE
from upkg import Package
from upkgwrite import ActorEdit, PackageWriter, enc_index


def original_two_lightcolors(path: Path) -> tuple[bytes, str]:
    level_fixture(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    _, cloned = clone_in_memory(
        path, source_sha256=digest, actor_export=1,
        actor_name="StaticMeshActor__1", delta=(100.0, 0.0, 0.0))
    path.write_bytes(cloned)
    pkg = Package(path)
    second = pkg.exports[2].name
    w = PackageWriter(pkg)
    name_ids = {name: w.name_index(name) for name in
                ("None", "LightBrightness", "LightHue", "LightSaturation")}
    for i, values in ((0, (96, 150, 32)), (2, (80, 90, 100))):
        payload = b"".join(
            enc_index(name_ids[name]) + b"\x01" + bytes([value])
            for name, value in zip(
                ("LightBrightness", "LightHue", "LightSaturation"), values)
        ) + enc_index(name_ids["None"])
        if len(payload) != 10:
            raise RuntimeError("Synthetic LightColor fixture needs one-byte name tags")
        actor = ActorEdit(w, pkg.exports[i])
        actor.set_block(116, payload, "invented_10_byte_LightColor",
                        insert_id=ENCODED_ID)
        if not actor.commit():
            raise RuntimeError("Synthetic LightColor block insertion failed")
    raw = w.write()
    path.write_bytes(raw)
    return raw, second


class MultiLightColorSDKTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dx2sdk_v08_multi_colors_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "OriginalMap" / "M1_Test.gmp"
        self.source.parent.mkdir()
        self.original, second = original_two_lightcolors(self.source)
        self.world = DX2Map.open(self.source)
        self.plan = self.root / "PrivatePlan" / "lights.json"
        self.output = self.root / "IsolatedNative" / self.source.name
        self.edits = [
            {"actor": "StaticMeshActor__1", "export": 1,
             "expected": [96, 150, 32],
             "changes": {"brightness": 255, "hue": 0, "saturation": 255}},
            {"actor": second, "export": 3,
             "expected": [80, 90, 100],
             "changes": {"brightness": 255}},
        ]

    def cli(self, *args, cwd=ROOT):
        return subprocess.run([sys.executable, "-B", "-m", "dx2sdk", *args],
            cwd=cwd, capture_output=True, text=True, timeout=75)

    def test_private_plan_and_source_full_package_parity(self):
        doc = self.world.build_lightcolor_plan(self.edits)
        self.assertEqual(doc["schema"], PLAN_SCHEMA)
        self.assertEqual(doc["source_sha256"],
                         hashlib.sha256(self.original).hexdigest())
        self.assertEqual(len(doc["actors"]), 2)
        self.assertFalse(doc["native_bsp_or_zone_rebuild_enabled"])
        self.assertFalse(self.plan.exists())
        self.assertFalse(self.output.exists())
        self.assertEqual(self.world.write_lightcolor_plan(self.edits, self.plan), doc)
        self.assertEqual(self.world.load_lightcolor_plan(self.plan), doc["actors"])
        dry = self.world.apply_lightcolor_plan(self.plan, self.output)
        self.assertEqual(dry["status"], "dry-run")
        self.assertEqual(dry["changed_bytes"], 4)
        self.assertTrue(dry["independent_full_package_byte_match"])
        self.assertFalse(self.output.exists())
        written = self.world.apply_lightcolor_plan(self.plan, self.output, write=True)
        self.assertEqual(written["status"], "isolated-GMP-written-runtime-unverified")
        self.assertTrue(written["verified_binary_structure"])
        verified = self.world.verify_saved_multi_lightcolor(self.output)
        self.assertEqual(verified["changed_bytes"], 4)
        self.assertEqual(verified["edited_actor_count"], 2)
        self.assertEqual(verified["unapproved_bytes"], 0)
        self.assertEqual(self.source.read_bytes(), self.original)
        before, after = self.original, self.output.read_bytes()
        changed = {i for i,(a,b) in enumerate(zip(before,after)) if a != b}
        self.assertEqual(changed, {e["absolute_offset"] for e in dry["field_edits"]})
        self.assertEqual(len(before), len(after))
        with self.assertRaises(ValueError):
            self.world.apply_lightcolor_plan(self.plan, self.output, write=True)

    def test_invalid_plan_rows_and_identity_never_write(self):
        for edits in (
            [],
            self.edits[:1],
            self.edits * 5,
            [self.edits[0], self.edits[0]],
            [{**self.edits[0], "actor": "Wrong"}, self.edits[1]],
            [{**self.edits[0], "export": True}, self.edits[1]],
            [{**self.edits[0], "expected": [97, 150, 32]}, self.edits[1]],
            [{**self.edits[0], "changes": {"hue": False}}, self.edits[1]],
            [{**self.edits[0], "changes": {"hue": 150}}, self.edits[1]],
            [{**self.edits[0], "added": True}, self.edits[1]],
        ):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                self.world.build_lightcolor_plan(edits)
        self.assertFalse(self.plan.exists())
        self.assertFalse(self.output.exists())

    def test_reject_game_paths_and_tampered_plan_flags(self):
        for path in (self.source.parent / "nested" / "lightcolors.json",
                     self.root / "OtherGame" / "Content" / "DX2" / "Maps" /
                     "colors.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.world.write_lightcolor_plan(self.edits, path)
        self.world.write_lightcolor_plan(self.edits, self.plan)
        saved = json.loads(self.plan.read_text("utf8"))
        for key,value in (
            ("schema", "wrong"), ("source_sha256", "0"*64),
            ("gameplay_runtime_verified", True),
            ("native_light_spawn_enabled", True),
            ("native_bsp_or_zone_rebuild_enabled", True),
            ("source_only_plan", False),
        ):
            with self.subTest(key=key):
                tampered = {**saved, key:value}
                self.plan.write_text(json.dumps(tampered))
                with self.assertRaises(ValueError):
                    self.world.load_lightcolor_plan(self.plan)
        injected = json.loads(json.dumps(saved))
        injected["actors"][0]["changes"]["hue"] = 150
        self.plan.write_text(json.dumps(injected))
        with self.assertRaises(ValueError):
            self.world.load_lightcolor_plan(self.plan)
        self.assertFalse(self.output.exists())

    def test_saved_manifest_forgery_extra_output_bytes_and_source_drift(self):
        self.world.write_lightcolor_plan(self.edits, self.plan)
        self.world.apply_lightcolor_plan(self.plan, self.output, write=True)
        manifest = self.output.with_suffix(".dx2sdk-multi-lightcolor.json")
        original_doc = manifest.read_text()
        forged = json.loads(original_doc)
        forged["native_bsp_or_zone_rebuild_enabled"] = True
        manifest.write_text(json.dumps(forged))
        with self.assertRaisesRegex(ValueError, "untrusted"):
            self.world.verify_saved_multi_lightcolor(self.output)
        manifest.write_text(original_doc)
        raw = bytearray(self.output.read_bytes())
        raw[-1] ^= 0x01
        self.output.write_bytes(raw)
        forged = json.loads(original_doc)
        forged["output_sha256"] = hashlib.sha256(raw).hexdigest()
        manifest.write_text(json.dumps(forged))
        with self.assertRaises(ValueError):
            self.world.verify_saved_multi_lightcolor(self.output)
        self.source.write_bytes(self.original + b"modified")
        with self.assertRaises(ValueError):
            self.world.load_lightcolor_plan(self.plan)

    def test_extracted_portable_multi_color_workflow(self):
        archive = self.root / "release.zip"
        build(ROOT, archive)
        with ZipFile(archive) as zipf:
            self.assertIn(f"{ARCHIVE}/dx2sdk/multi_light_colors.py", zipf.namelist())
            zipf.extractall(self.root / "unpack")
        sdk = self.root / "unpack" / ARCHIVE
        second = self.edits[1]["actor"]
        args = (
            "make-lightcolor-plan", "--map", str(self.source),
            "--edit", "1", "96", "150", "32", "255", "0", "255",
            "--edit", "3", "80", "90", "100", "255", "90", "100",
            "--plan", str(self.plan),
        )
        result = self.cli(*args, cwd=sdk)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["planned_actor_edits"], 2)
        self.assertEqual(self.world.load_lightcolor_plan(self.plan)["actors"] if
                         isinstance(self.world.load_lightcolor_plan(self.plan), dict)
                         else len(self.world.load_lightcolor_plan(self.plan)), 2)
        apply = ("apply-lightcolor-plan", "--map", str(self.source),
                 "--plan", str(self.plan), "--output", str(self.output))
        dry = self.cli(*apply, cwd=sdk)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["status"], "dry-run")
        self.assertFalse(self.output.exists())
        wrote = self.cli(*apply, "--write", cwd=sdk)
        self.assertEqual(wrote.returncode, 0, wrote.stderr)
        self.assertTrue(json.loads(wrote.stdout)["verified_binary_structure"])
        verify = self.cli("verify-multi-lightcolor", "--map", str(self.source),
                          "--output", str(self.output), cwd=sdk)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertEqual(json.loads(verify.stdout)["edited_actor_count"], 2)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
