"""Source-only P106 original UE95 licensee 65/67 BSP dossier tests."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from dx2sdk.bsp_legacy_licensee_readonly import (
    inspect_legacy_original_bsp_node, SCHEMA,
)
from inspect_world_bsp_node_boundaries import parse_world_model
from test_dx2_world_bsp_zone_relations import synthetic_world


def fake_legacy(path, original, payload, licensee=65):
    export = {"offset": 64, "size": len(payload)}
    class FakePackage:
        version = 95
        def __init__(self, source):
            self.data = Path(source).read_bytes()
            self.licensee = licensee
            self.exports = [export]
        def class_name(self, _): return "Model"
        def payload(self, exp):
            return self.data[exp["offset"]:exp["offset"]+exp["size"]]
    direct = {
        "world_model_initial_9_zero_bytes": True,
        "world_model_zero_bounds_and_sphere": True,
        "world_model_first_plane_normal_unit": True,
        "direct_model_ref_not_in_actor_list": True,
        "world_model_export_ref": 1,
        "world_model_payload_bytes": len(payload),
        "world_model_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "world_model_compact_node_count_at_50": 3,
    }
    return FakePackage, direct


class LegacyBSPLicenseeTests(unittest.TestCase):
    def test_readonly_legacy_node_dossier_with_full_model_source_proof(self):
        model, frame = synthetic_world()
        original = b"\xe5"*64 + model + b"\xf2"*11
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"Synthetic_licensee65.gmp"
            source.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            for licensee in (65,67):
                with self.subTest(licensee=licensee):
                    pkg, direct = fake_legacy(source, original, model, licensee)
                    with patch("dx2sdk.bsp_legacy_licensee_readonly.Package", pkg),\
                         patch("dx2sdk.bsp_legacy_licensee_readonly._parse_world_model",return_value=direct):
                        result = inspect_legacy_original_bsp_node(source, sha, 2)
                    self.assertEqual(result["schema"],SCHEMA)
                    self.assertEqual(result["original_node_ordinal"],2)
                    self.assertEqual(result["original_node_count"],3)
                    self.assertEqual(result["source_original_licensee"],licensee)
                    self.assertEqual(result["source_gmp_sha256"],sha)
                    self.assertEqual(result["source_gmp_model_absolute_offset"],64)
                    self.assertEqual(result["source_gmp_node_absolute_offset"],
                                     64+frame["node_records"][2]["start"])
                    self.assertTrue(result["read_only_legacy_research_adapter"])
                    self.assertFalse(result["general_DX2Map_writer_licensee_allowlist_extended"])
                    self.assertFalse(result["native_BSP_or_Havok_collision_writer_enabled"])
                    self.assertFalse(result["compact_field2_native_surface_id_authenticated"])
                    self.assertTrue(result["original_model_full_span_ledger_verified"])
                    self.assertTrue(result["original_model_exact_noop_verified"])
                    self.assertEqual(source.read_bytes(),original)

    def test_invalid_source_sha_licensee_and_boundary_refused(self):
        model, frame = synthetic_world()
        original = b"\xe5"*64 + model + b"\xf2"*11
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"Synthetic.gmp"
            source.write_bytes(original)
            sha = hashlib.sha256(original).hexdigest()
            pkg, direct = fake_legacy(source, original, model, 65)
            with patch("dx2sdk.bsp_legacy_licensee_readonly.Package",pkg),\
                 patch("dx2sdk.bsp_legacy_licensee_readonly._parse_world_model",return_value=direct):
                for bad_sha in ("0"*64, "bad", "g"*64):
                    with self.subTest(hash=bad_sha),self.assertRaises(ValueError):
                        inspect_legacy_original_bsp_node(source,bad_sha,0)
                for invalid in (-1,3,True,20000):
                    with self.subTest(index=invalid),self.assertRaises(ValueError):
                        inspect_legacy_original_bsp_node(source,sha,invalid)
            for licensee in (64,68,69):
                fake, other = fake_legacy(source,original,model,licensee)
                with patch("dx2sdk.bsp_legacy_licensee_readonly.Package",fake),\
                     patch("dx2sdk.bsp_legacy_licensee_readonly._parse_world_model",return_value=other),\
                     self.assertRaisesRegex(ValueError,"65/67 only"):
                    inspect_legacy_original_bsp_node(source,sha,0)
            fake, wrong = fake_legacy(source,original,model,67)
            wrong["world_model_payload_sha256"] = "f"*64
            with patch("dx2sdk.bsp_legacy_licensee_readonly.Package",fake),\
                 patch("dx2sdk.bsp_legacy_licensee_readonly._parse_world_model",return_value=wrong),\
                 self.assertRaises(ValueError):
                inspect_legacy_original_bsp_node(source,sha,0)
            self.assertEqual(source.read_bytes(),original)

    def test_cli_exact_sdk_allowlist_fallback_only(self):
        import inspect_bsp_node_dossier as cli
        original = "b"*64
        minimal = {
            "schema": SCHEMA,
            "source_gmp_sha256": original,
            "original_source_gmp_modified": False,
            "native_BSP_or_Havok_collision_writer_enabled": False,
            "original_model_full_span_ledger_verified": True,
        }
        with patch.object(cli.DX2Map,"open",side_effect=ValueError(
                "DX2SDK supports DX2 Ion Storm GMP v95 licensee 68/69 only")),\
             patch.object(cli,"inspect_legacy_original_bsp_node",return_value=minimal) as fallback,\
             redirect_stdout(StringIO()) as stdout:
            code=cli.main(["--gmp","Synthetic.gmp",
                           "--source-sha256",original,"--node","1"])
        self.assertEqual(code,0)
        fallback.assert_called_once_with(Path("Synthetic.gmp"),original,1)
        self.assertEqual(json.loads(stdout.getvalue())["source_gmp_sha256"],original)
        with patch.object(cli.DX2Map,"open",side_effect=ValueError(
                "Original package malformed (not an allowlist refusal)")),\
             patch.object(cli,"inspect_legacy_original_bsp_node") as fallback,\
             redirect_stderr(StringIO()) as stderr:
            code=cli.main(["--gmp","Synthetic.gmp",
                           "--source-sha256",original,"--node","1"])
        self.assertEqual(code,2)
        fallback.assert_not_called()
        self.assertEqual(json.loads(stderr.getvalue())["status"],"refused")


if __name__=="__main__":
    unittest.main()
