"""Synthetic DX2 original TSD -> IBD resource identity bridge tests.

No proprietary game resources; all fixtures are constructed in memory.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor/godot_editor/backend"))
sys.path.insert(0, str(ROOT / "tools/scripts"))
from dx2_script_ibd_provenance import build_evidence, export_report, SCHEMA
from dx2_script_bundle_probe import MAGIC, HEADER_SIZE, ENTRY_SIZE


def tsd(name="TS_TEST"):
    symbols = (name + "\x00Synthetic source-only door action\x00"
               + "kTCT_ReceivePropagateMsgLink\x00kTAT_SendMsg\x00")
    return b"1FFE2FST" + b"\x00" * 8 + symbols.encode("utf-16le")


def ibd_resource(payload: bytes, name="TS_TEST", *, kind=21):
    start, align = 2048, 2048
    if len(payload) > align:
        raise ValueError("Fixture bigger than one partition")
    result = bytearray(start + align)
    struct.pack_into("<8I", result, 0, MAGIC, align, start, align, 1, 1, 1, 1)
    struct.pack_into("<5I", result, HEADER_SIZE, start,
                     len(payload), align - len(payload), 0, 1)
    result[HEADER_SIZE+0x28] = kind
    result[HEADER_SIZE+0x29:HEADER_SIZE+0x29+len(name)] = name.encode("ascii")
    struct.pack_into("<I", result, HEADER_SIZE+ENTRY_SIZE, len(payload))
    result[start:start+len(payload)] = payload
    return bytes(result)


class ScriptIbdResourceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="dx2ed_source_ibd_synthetic_")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.game = self.root / "Content" / "DX2"
        self.maps = self.game / "Maps"
        self.maps.mkdir(parents=True)
        self.map = self.maps / "Synthetic.gmp"
        self.map.write_bytes(b"SYNTHETIC MAP IDENTITY ONLY")
        self.actors = self.root / "DX2EdCache" / "actors.json"
        self.actors.parent.mkdir()
        self.actors.write_text(json.dumps({
            "meta": {"source_map": self.map.name,
                     "source_sha256": hashlib.sha256(self.map.read_bytes()).hexdigest()},
            "actors": [{"name": "SyntheticActor__1", "export": 5,
                        "class": "Trigger", "game_properties": []}],
        }), encoding="utf8")
        self.zip = self.game / "TriggerScript.zip"
        self.raw = tsd()
        with ZipFile(self.zip, "w") as archive:
            archive.writestr("Defs/TS_TEST.tsd", self.raw)
        self.ibd = self.maps / "Mission.ibd"
        self.ibd.write_bytes(ibd_resource(self.raw[12:]))
        self.output = self.root / "DX2EdPrivate" / "ibd_verified.json"

    def _evidence(self):
        return build_evidence(self.map, self.actors, self.zip, self.ibd)

    def test_exact_native_ibd_payload_match_without_actor_binding_claims(self):
        originals = [self.map, self.actors, self.zip, self.ibd]
        before = [hashlib.sha256(f.read_bytes()).hexdigest() for f in originals]
        evidence = self._evidence()
        self.assertEqual(evidence["schema"], SCHEMA)
        self.assertTrue(evidence["read_only"])
        self.assertEqual(evidence["ibd_name"], "Mission.ibd")
        self.assertEqual(evidence["counts"]["exact_payload"], 1)
        self.assertEqual(evidence["counts"]["different_payload"], 0)
        self.assertEqual(evidence["counts"]["not_in_original_zip"], 0)
        self.assertEqual(evidence["counts"]["source_definitions_not_in_ibd"], 0)
        row = evidence["entries"][0]
        self.assertEqual(row["script_id"], "TS_TEST")
        self.assertEqual(row["ibd_resource_index"], 0)
        self.assertEqual(row["source_payload_sha256"],
                         hashlib.sha256(self.raw[12:]).hexdigest())
        self.assertEqual(row["ibd_payload_sha256"], row["source_payload_sha256"])
        self.assertEqual(row["status"], "exact_payload")
        for key in ("actor_to_script_binding_verified",
                    "native_actor_script_indices_resolved",
                    "native_script_writer_enabled",
                    "original_game_assets_modified",
                    "gameplay_runtime_verified"):
            self.assertFalse(evidence[key], key)
        self.assertEqual([hashlib.sha256(f.read_bytes()).hexdigest()
                          for f in originals], before)

    def test_same_resource_id_but_tampered_payload_is_not_exact(self):
        changed = bytearray(self.raw[12:])
        changed[-1] ^= 0x01
        self.ibd.write_bytes(ibd_resource(changed))
        doc = self._evidence()
        self.assertEqual(doc["counts"]["exact_payload"], 0)
        self.assertEqual(doc["counts"]["different_payload"], 1)
        self.assertEqual(doc["entries"][0]["status"], "different_payload")

    def test_other_ibd_resource_is_not_promoted_to_zip_definition(self):
        self.ibd.write_bytes(ibd_resource(b"unrelated", "TS_UNKNOWN"))
        doc = self._evidence()
        self.assertEqual(doc["counts"]["not_in_original_zip"], 1)
        self.assertEqual(doc["counts"]["source_definitions_not_in_ibd"], 1)
        self.assertFalse(doc["entries"][0]["standalone_source_name_matched"])

    def test_not_script_resource_does_not_fake_a_match(self):
        self.ibd.write_bytes(ibd_resource(self.raw[12:], kind=4))
        doc = self._evidence()
        self.assertEqual(doc["entries"], [])
        self.assertEqual(doc["counts"]["source_definitions_not_in_ibd"], 1)

    def test_modified_source_gmp_or_cached_actor_sha_is_rejected(self):
        self.map.write_bytes(self.map.read_bytes() + b"TAMPER")
        with self.assertRaisesRegex(ValueError, "cache does not match"):
            self._evidence()

    def test_wrong_ibd_header_or_partition_is_rejected(self):
        broken = bytearray(self.ibd.read_bytes())
        broken[0] ^= 1
        self.ibd.write_bytes(broken)
        with self.assertRaisesRegex(ValueError, "magic"):
            self._evidence()
        broken[0] ^= 1
        struct.pack_into("<I", broken, HEADER_SIZE+ENTRY_SIZE, 0)
        self.ibd.write_bytes(broken)
        with self.assertRaisesRegex(ValueError, "invalid layout"):
            self._evidence()

    def test_private_report_and_fail_closed_source_write_rules(self):
        original_hash = hashlib.sha256(self.ibd.read_bytes()).hexdigest()
        report = export_report(self.map, self.actors, self.zip, self.ibd,
                               self.output)
        self.assertTrue(self.output.exists())
        self.assertEqual(json.loads(self.output.read_text("utf8")), report)
        self.assertEqual(original_hash, hashlib.sha256(self.ibd.read_bytes()).hexdigest())
        with self.assertRaises(ValueError):
            export_report(self.map, self.actors, self.zip, self.ibd, self.output)
        with self.assertRaises(ValueError):
            export_report(self.map, self.actors, self.zip, self.ibd,
                          self.maps / "should_not_write.json")
        self.assertFalse((self.maps / "should_not_write.json").exists())
        with self.assertRaises(ValueError):
            export_report(self.map, self.actors, self.zip, self.ibd,
                          self.game / "also_protected.json")
        with self.assertRaises(ValueError):
            export_report(self.map, self.actors, self.zip, self.ibd,
                          self.game.parent / "install_root_protected.json")
        self.assertFalse((self.game / "also_protected.json").exists())
        self.assertFalse((self.game.parent / "install_root_protected.json").exists())

    def test_cli_outputs_aggregate_report_without_original_paths_or_bytes(self):
        exe = ROOT / "native_editor/godot_editor/backend/dx2_script_ibd_provenance.py"
        p = subprocess.run([
            sys.executable, str(exe), "--map", str(self.map),
            "--actors", str(self.actors), "--scripts", str(self.zip),
            "--ibd", str(self.ibd), "--output", str(self.output),
        ], capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        summary = json.loads(p.stdout)
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["counts"]["exact_payload"], 1)
        for private in (str(self.map), str(self.zip), str(self.ibd),
                        self.map.name, self.ibd.name):
            self.assertNotIn(private, p.stdout)
        p2 = subprocess.run([
            sys.executable, str(exe), "--map", str(self.map),
            "--actors", str(self.actors), "--scripts", str(self.zip),
            "--ibd", str(self.ibd), "--output", str(self.output),
        ], capture_output=True, text=True, check=False)
        self.assertEqual(p2.returncode, 2)
        self.assertEqual(json.loads(p2.stdout)["status"], "refused")
        self.assertNotIn(str(self.ibd), p2.stdout)


if __name__ == "__main__":
    unittest.main()
