"""P105 original DX2 BSP node provenance tests; synthetic source-only."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from dx2sdk.bsp_node_dossier import (
    inspect_model_node_bytes, inspect_original_bsp_node_dossier, SCHEMA,
)
from inspect_world_bsp_node_boundaries import parse_world_model
from test_dx2_world_bsp_zone_relations import synthetic_world


def synthetic_gmp_world():
    model, frame = synthetic_world()
    original = b"\xe5"*64 + model + b"\xf2"*11
    exp = {"offset": 64, "size": len(model)}
    class Package:
        data = original
        exports = [exp]
        def class_name(self, e): return "Model"
        def payload(self, e):
            return self.data[e["offset"]:e["offset"]+e["size"]]
    class World:
        _package = Package()
        source = Path("Synthetic.gmp")
        source_sha256 = hashlib.sha256(original).hexdigest()
        checks = 0
        def _check_original_unchanged(self): self.checks += 1
        def inspect_original_bsp_node_dossier(self, index):
            return inspect_original_bsp_node_dossier(self, index)
    reference = {
        "world_model_export": 1,
        "world_model_sha256": hashlib.sha256(model).hexdigest(),
        "node_count": frame["candidate_node_count"],
        "nodes": [{"plane": struct.unpack_from("<4f",model,n["start"])}
                  for n in frame["node_records"]],
    }
    return World(), model, frame, reference


class BSPNodeDossierTests(unittest.TestCase):
    def test_source_original_node_plane_compact_spans_and_no_writer(self):
        source, frame = synthetic_world()
        original = bytes(source)
        first = inspect_model_node_bytes(source, 0)
        self.assertEqual(source, original)
        self.assertEqual(first["schema"], SCHEMA)
        self.assertEqual(first["original_node_count"], 3)
        self.assertEqual(first["original_zone_record_count"], 3)
        self.assertEqual(first["original_node_ordinal"], 0)
        self.assertEqual(first["native_model_node_record_bytes"], 109)
        self.assertEqual(first["candidate_plane_source_f32"],
                         list(struct.unpack_from("<4f",source,frame["node_records"][0]["start"])))
        self.assertEqual(len(first["raw_compact_fields"]),8)
        self.assertEqual(len(first["raw_compact_offsets_in_model"]),8)
        self.assertEqual(len(first["node_source_spans"]),19)
        self.assertEqual(sum(x["byte_count"] for x in first["node_source_spans"]),109)
        self.assertEqual(first["raw_compact_offsets_in_model"][2],
                         frame["node_records"][0]["start"]+50)
        self.assertEqual(first["raw_compact_offsets_in_model"],
            [x["original_model_relative_offset"] for x in first["node_source_spans"][2:10]])
        self.assertFalse(first["compact_field2_native_surface_id_authenticated"])
        self.assertFalse(first["native_vertex_xyz_pool_recovered"])
        self.assertFalse(first["native_surface_material_uv_binding_verified"])
        self.assertFalse(first["native_BSP_or_Havok_collision_writer_enabled"])
        self.assertFalse(first["retail_runtime_verified"])
        self.assertTrue(first["original_model_exact_noop_verified"])
        self.assertTrue(first["original_model_full_span_ledger_verified"])
        self.assertEqual(first, inspect_model_node_bytes(source,0))
        for ordinal in (1,2):
            one = inspect_model_node_bytes(source,ordinal)
            self.assertEqual(one["original_node_ordinal"],ordinal)
            self.assertEqual(one["original_model_sha256"],first["original_model_sha256"])

    def test_noncanonical_compact_index_retains_original_source_width_and_positions(self):
        source, frame = synthetic_world()
        expanded=source[:99] + b"\x40\x00" + source[100:]
        row=inspect_model_node_bytes(expanded,0)
        self.assertEqual(row["native_model_node_record_bytes"],110)
        self.assertEqual(row["raw_compact_byte_widths"][0],2)
        self.assertEqual(row["raw_compact_offsets_in_model"][2],
                         frame["node_records"][0]["start"]+51)
        self.assertEqual(sum(x["byte_count"] for x in row["node_source_spans"]),110)
        row2=inspect_model_node_bytes(expanded,1)
        self.assertEqual(row2["native_model_node_record_bytes"],109)

    def test_refuse_bad_indices_corruption_or_nonbytes(self):
        source, frame = synthetic_world()
        for invalid in (-1,3,20000,True,1.0,None,"0"):
            with self.subTest(index=invalid),self.assertRaises(ValueError):
                inspect_model_node_bytes(source,invalid)
        for invalid in (b"",bytearray(source),source[:-1],source+b"\0"):
            with self.subTest(size=len(invalid)),self.assertRaises(ValueError):
                inspect_model_node_bytes(invalid,0)
        bad=bytearray(source)
        bad[frame["node_records"][0]["start"]+16] ^= 1
        with self.assertRaises(ValueError):
            inspect_model_node_bytes(bytes(bad),0)

    def test_gmp_source_sha_and_original_absolute_offsets(self):
        world,model,frame,ref = synthetic_gmp_world()
        original = bytes(world._package.data)
        with patch("dx2sdk.bsp_node_dossier._load_model",return_value=ref):
            out=world.inspect_original_bsp_node_dossier(1)
        self.assertEqual(world.checks,2)
        self.assertEqual(world._package.data,original)
        self.assertEqual(out["source_map"],"Synthetic.gmp")
        self.assertEqual(out["source_gmp_sha256"],hashlib.sha256(original).hexdigest())
        self.assertEqual(out["source_gmp_model_absolute_offset"],64)
        self.assertEqual(out["source_gmp_node_absolute_offset"],
                         64+frame["node_records"][1]["start"])
        self.assertFalse(out["original_source_gmp_modified"])
        self.assertEqual(out["world_model_export"],1)
        world.source_sha256="f"*64
        with patch("dx2sdk.bsp_node_dossier._load_model",return_value=ref),self.assertRaises(ValueError):
            world.inspect_original_bsp_node_dossier(1)

    def test_cli_sha_pin_valid_report_and_refusal_without_output_files(self):
        import inspect_bsp_node_dossier as cli
        world,model,frame,ref = synthetic_gmp_world()
        with patch("dx2sdk.bsp_node_dossier._load_model",return_value=ref),\
             patch.object(cli.DX2Map,"open",return_value=world),\
             redirect_stdout(StringIO()) as out:
            code=cli.main([
                "--gmp","Synthetic.gmp","--source-sha256",
                world.source_sha256,"--node","2"])
        self.assertEqual(code,0)
        doc=json.loads(out.getvalue())
        self.assertEqual(doc["schema"],SCHEMA)
        self.assertEqual(doc["original_node_ordinal"],2)
        self.assertFalse(doc["original_source_gmp_modified"])
        for args in [
            ["--gmp","Synthetic.gmp","--source-sha256","bad","--node","0"],
            ["--gmp","Synthetic.gmp","--source-sha256","0"*64,"--node","0"],
            ["--gmp","Synthetic.ibd","--source-sha256",world.source_sha256,"--node","0"],
            ["--gmp","Synthetic.gmp","--source-sha256",world.source_sha256,"--node","20000"],
        ]:
            with self.subTest(args=args),\
                 patch.object(cli.DX2Map,"open",return_value=world),\
                 redirect_stderr(StringIO()) as err:
                code=cli.main(args)
            self.assertEqual(code,2)
            refusal=json.loads(err.getvalue())
            self.assertEqual(refusal["status"],"refused")
            self.assertIs(refusal["native_BSP_or_Havok_collision_writer_enabled"],False)


if __name__=="__main__":
    unittest.main()
