"""Fixture-only tests for a restricted, NON-runtime MOPP control-flow emitter."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import emit_synthetic_mopp_fixture as emitter
import inspect_mopp_bytecode_roundtrip as roundtrip
import inspect_level_mopp_triangle_tree as mopp


def mesh(n: int = 4):
    return emitter._make_disconnected_triangles(n)


class SyntheticMoppEmitterTests(unittest.TestCase):
    def test_one_leaf_source_observed_root_grammar(self):
        verts, faces = mesh(1)
        out = emitter.build_synthetic_envelope(verts, faces)
        self.assertEqual(out["code"], b"\x28\x00\xff\x30")
        self.assertEqual(out["nondegenerate_source_triangle_ids"], [0])
        self.assertEqual(len(out["envelope"]), 4 + 36)
        self.assertFalse(out["report"]["runtime_havok_compatible"])
        self.assertFalse(out["report"]["actual_spatial_branch_conditions_implemented"])

    def test_two_leaf_short_relocation_is_exact(self):
        verts, faces = mesh(2)
        out = emitter.build_synthetic_envelope(verts, faces)
        self.assertEqual(out["code"], b"\x28\x00\xff\x20\x80\x01\x30\x31")
        self.assertEqual(out["report"]["synthetic_code_bytes"], 8)
        self.assertEqual(mopp.trace_mopp_code(out["code"], 2)[
            "reachable_terminal_triangle_ids"], [0,1])

    def test_four_leaves_balanced_displacements_and_no_gaps(self):
        verts, faces = mesh(4)
        out = emitter.build_synthetic_envelope(verts, faces)
        self.assertEqual(out["code"][:6], b"\x28\x00\xff\x20\x80\x05")
        check = roundtrip.inspect_code_roundtrip(out["code"], 4)
        self.assertEqual(check["reachable_instruction_bytes"], len(out["code"]))
        self.assertEqual(check["unvisited_bytes_preserved_opaque"], 0)
        self.assertEqual(check["reachable_triangle_leaves"], 4)
        self.assertEqual(out["code"], emitter.build_synthetic_envelope(verts, faces)["code"])

    def test_relocation_promotes_to_16bit_split_and_wide_leaf(self):
        verts, faces = mesh(260)
        out = emitter.build_synthetic_envelope(verts, faces)
        code = out["code"]
        self.assertEqual(code[3], 0x23)  # root branch longer than 255 bytes
        self.assertIn(b"\x50\x20", code)  # immediate leaf 32
        self.assertIn(b"\x51\x01\x00", code)  # immediate leaf 256
        proof = roundtrip.inspect_code_roundtrip(code, 260)
        self.assertEqual(proof["reachable_triangle_leaves"],260)
        self.assertEqual(proof["reachable_instruction_bytes"],len(code))
        self.assertEqual(proof["unvisited_bytes_preserved_opaque"],0)

    def test_sparse_24bit_ids_use_full_width_without_changing_source(self):
        ids = [0, 31, 32, 255, 256, 65535, 65536, 69999]
        original = ids[:]
        code, proof = emitter.encode_leaf_graph(ids, 70000)
        self.assertEqual(ids, original)
        self.assertIn(b"\x52\x01\x00\x00", code)
        self.assertEqual(proof["reachable_triangle_leaves"],len(ids))
        self.assertEqual(mopp.trace_mopp_code(code,70000)[
            "reachable_terminal_triangle_ids"],ids)

    def test_level_export_fixture_passes_independent_legacy_validators(self):
        verts, faces = mesh(6)
        level, blocks, report = emitter.make_synthetic_level_fixture(verts,faces)
        old = roundtrip.inspect_level_envelope(level,blocks)
        self.assertTrue(old["envelope_byte_identical"])
        self.assertEqual(old["reachable_instruction_bytes"],old["code_length_bytes"])
        self.assertEqual(old["reachable_triangle_leaves"],6)
        self.assertEqual(report["source_triangle_count"],6)
        self.assertTrue(report["synthetic_only"])

    def test_zero_area_source_triangle_omitted_without_id_renumbering(self):
        verts = [(0.,0.,0.), (1.,0.,0.), (2.,0.,0.), (0.,1.,0.)]
        tris = [(0,1,2), (0,1,3)]
        out = emitter.build_synthetic_envelope(verts,tris)
        self.assertEqual(out["nondegenerate_source_triangle_ids"],[1])
        self.assertEqual(out["omitted_zero_area_triangle_ids"],[0])
        self.assertEqual(out["code"],b"\x28\x00\xff\x31")
        level, blocks, _ = emitter.make_synthetic_level_fixture(verts,tris)
        verified = mopp.inspect_mopp_link(level,blocks)
        self.assertEqual(verified["omitted_zero_area_triangle_ids"],[0])

    def test_only_degenerate_geometry_fails_closed(self):
        verts = [(0.,0.,0.),(1.,0.,0.),(2.,0.,0.)]
        with self.assertRaisesRegex(ValueError,"no nonzero-area"):
            emitter.build_synthetic_envelope(verts,[(0,1,2)])

    def test_invalid_vertices_and_f32_values_refused(self):
        verts,faces=mesh(1)
        for bad in (float("nan"),float("inf"),True,1_000_001):
            clone=list(verts)
            clone[0]=(bad,0.,0.)
            with self.subTest(value=bad),self.assertRaises(ValueError):
                emitter.build_synthetic_envelope(clone,faces)
        with self.assertRaisesRegex(ValueError, "exactly three"):
            emitter.build_synthetic_envelope([(0,0),(1,0,0),(0,1,0)],faces)

    def test_bad_triangle_index_boolean_and_out_of_range_refused(self):
        verts,faces=mesh(1)
        for indices in ((0,1,999),(0,True,2),(0,-1,2),(0,1),("0",1,2)):
            with self.subTest(indices=indices), self.assertRaisesRegex(ValueError,"triangle"):
                emitter.build_synthetic_envelope(verts,[indices])

    def test_unsorted_duplicate_or_missing_graph_ids_refused(self):
        for ids,count in [([1,0],2),([0,0],2),([-1],1),([1],1),([],1),([0],0)]:
            with self.subTest(ids=ids),self.assertRaises(ValueError):
                emitter.encode_leaf_graph(ids,count)

    def test_changed_branch_relocation_is_refused_by_independent_decoder(self):
        code,_=emitter.encode_leaf_graph([0,1],2)
        bad=bytearray(code)
        bad[5]=255
        with self.assertRaisesRegex(ValueError,"jump"):
            roundtrip.inspect_code_roundtrip(bytes(bad),2)

    def test_spatial_parameters_are_source_formula_and_float32(self):
        verts,faces=mesh(2)
        out=emitter.build_synthetic_envelope(verts,faces)
        origin=struct.unpack_from("<4f",out["envelope"],4)
        self.assertAlmostEqual(origin[0],-0.05,places=5)
        self.assertAlmostEqual(origin[1],-0.05,places=5)
        self.assertAlmostEqual(origin[2],-0.05,places=5)
        self.assertAlmostEqual(origin[3],254*65536/(3+0.1),delta=1)
        self.assertEqual(struct.unpack_from("<I",out["envelope"],0)[0],len(out["code"])+20)
        self.assertEqual(struct.unpack_from("<I",out["envelope"],20)[0],len(out["code"]))
        self.assertEqual(out["envelope"][-12:],bytes(12))

    def test_original_python_inputs_never_mutated(self):
        vertices,triangles=mesh(16)
        original_vertices=copy.deepcopy(vertices)
        original_triangles=copy.deepcopy(triangles)
        out=emitter.build_synthetic_envelope(vertices,triangles)
        self.assertEqual(vertices,original_vertices)
        self.assertEqual(triangles,original_triangles)
        self.assertEqual(out["report"]["synthetic_code_sha256"],
                         hashlib.sha256(out["code"]).hexdigest())

    def test_cli_exclusive_binary_and_json_are_not_game_packages(self):
        with tempfile.TemporaryDirectory() as d:
            prefix=Path(d)/"test_synthetic"
            self.assertEqual(emitter.main(["--triangles","3","--output-prefix",str(prefix)]),0)
            binpath=Path(d)/"test_synthetic.synthetic-mopp.bin"
            jsonpath=Path(d)/"test_synthetic.synthetic-mopp.json"
            self.assertTrue(binpath.is_file())
            self.assertTrue(jsonpath.is_file())
            self.assertNotEqual(binpath.suffix.lower(),".gmp")
            envelope=binpath.read_bytes()
            self.assertEqual(len(envelope),
                             struct.unpack_from("<I",envelope,20)[0] + 36)
            self.assertEqual(emitter.main(["--triangles","3","--output-prefix",str(prefix)]),1)
            self.assertEqual(binpath.read_bytes(),envelope)

    def test_cli_rejects_paths_inside_retail_maps_and_package_names(self):
        with tempfile.TemporaryDirectory() as d:
            mapsdir=Path(d)/"Maps"
            mapsdir.mkdir()
            self.assertEqual(emitter.main(["--triangles","2","--output-prefix",
                                            str(mapsdir/"unsafe")]),1)
            self.assertEqual(emitter.main(["--triangles","2","--output-prefix",
                                            str(Path(d)/"unsafe.gmp")]),1)
            self.assertEqual(list(mapsdir.iterdir()),[])


if __name__=="__main__":
    unittest.main()
