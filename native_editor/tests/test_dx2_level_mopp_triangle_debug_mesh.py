"""Asset-free tests of DX2 MOPP-linked Level collision-triangle debug OBJ exporter."""
from __future__ import annotations
import hashlib
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
from test_dx2_level_mopp_triangle_provenance import fixture
import export_level_mopp_triangle_debug_mesh as exporter


class MoppTriangleDebugMeshTests(unittest.TestCase):
    def test_synthetic_two_materials_with_original_triangle_ids(self):
        level, blocks, _ = fixture()
        r = exporter.inspect_mesh(level, blocks)
        self.assertEqual((r["source_vertex_count"],r["source_triangle_count"]),(4,2))
        self.assertEqual((r["mopp_leaf_triangle_count"],r["source_render_section_count"]),(2,2))
        self.assertEqual([t["render_material_id"] for t in r["triangles"]], [0,1])
        self.assertEqual([t["triangle_id"] for t in r["triangles"]], [0,1])
        self.assertFalse(r["render_material_names_are_physics_materials"])
        obj,mtl,info=exporter.render_obj(r)
        self.assertEqual([s for s in obj.splitlines() if s.startswith("f ")],
                         ["f 1 2 3", "f 1 3 4"])
        self.assertIn("# original_level_triangle_id 1",obj)
        self.assertIn("usemtl debug_0000",obj)
        self.assertIn("usemtl debug_0001",obj)
        self.assertIn("newmtl debug_0000",mtl)
        self.assertEqual(info["obj_faces_written"],2)
        self.assertEqual(info["obj_face_to_level_triangle_id"],[0,1])

    def test_multiple_blocks_unique_material_attribution(self):
        level, blocks, _ = fixture(separate_blocks=True)
        r=exporter.inspect_mesh(level,blocks)
        self.assertEqual([t["source_block_id"] for t in r["triangles"]],[0,2])
        self.assertEqual([t["render_block_ordinal"] for t in r["triangles"]],[0,1])
        obj,_,info=exporter.render_obj(r)
        self.assertIn("g block_0001_section_000",obj)
        self.assertEqual(info["obj_faces_written"],2)

    def test_zero_area_excluded_by_default_but_preserved_in_manifest(self):
        level,blocks,_=fixture(code=b'\x28\x00\xff\x31',degenerate=True)
        r=exporter.inspect_mesh(level,blocks)
        self.assertEqual([t["mopp_terminal_leaf"] for t in r["triangles"]],[False,True])
        obj,_,info=exporter.render_obj(r)
        self.assertEqual(info["obj_faces_written"],1)
        self.assertEqual(info["obj_face_to_level_triangle_id"],[1])
        self.assertEqual(info["zero_area_faces_not_in_mopp_omitted_from_obj"],1)
        self.assertNotIn("# original_level_triangle_id 0 ",obj)
        self.assertIn("# original_level_triangle_id 1 ",obj)
        included,_,in_info=exporter.render_obj(r,include_zero_area=True)
        self.assertEqual(in_info["obj_faces_written"],2)
        self.assertEqual(in_info["obj_face_to_level_triangle_id"],[0,1])
        self.assertIn("# original_level_triangle_id 0 ",included)

    def test_does_not_mutate_synthetic_level(self):
        level,blocks,_=fixture()
        before=hashlib.sha256(level).digest()
        exporter.inspect_mesh(level,blocks)
        self.assertEqual(hashlib.sha256(level).digest(),before)

    def test_corrupt_mopp_rejected(self):
        level,blocks,_=fixture()
        with self.assertRaisesRegex(ValueError,"MOPP envelope"):
            exporter.inspect_mesh(level[:-1]+b'\xff',blocks)

    def test_corrupt_provenance_rejected(self):
        level,blocks,at=fixture()
        data=bytearray(level);data[at+24+8+4]=10
        with self.assertRaises(ValueError):
            exporter.inspect_mesh(bytes(data),blocks)

    def test_deterministic_debug_material_color_and_not_physical(self):
        self.assertEqual(exporter._rgb("M1HUB_wall"),exporter._rgb("M1HUB_wall"))
        self.assertNotEqual(exporter._rgb("M1HUB_wall"),exporter._rgb("M1HUB_cement"))
        level,blocks,_=fixture()
        r=exporter.inspect_mesh(level,blocks)
        self.assertTrue(all(not m["physics_material_verified"] for m in r["materials"]))

    def test_bad_include_flag_refused(self):
        level,blocks,_=fixture()
        r=exporter.inspect_mesh(level,blocks)
        with self.assertRaisesRegex(ValueError,"boolean"):
            exporter.render_obj(r,include_zero_area="yes")
        with self.assertRaisesRegex(ValueError,"boolean"):
            exporter.export_map("invalid.gmp","fake",include_zero_area="yes")

    def test_outdir_in_original_maps_dir_refused_before_map_load(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"original.gmp"
            source.write_bytes(b"original synthetic fixture")
            with self.assertRaisesRegex(ValueError,"source map directory"):
                exporter.export_map(source,Path(d)/"preview")
            self.assertEqual(source.read_bytes(),b"original synthetic fixture")
            self.assertFalse((Path(d)/"preview").exists())

    def test_existing_destination_refused_before_map_load(self):
        with tempfile.TemporaryDirectory() as d:
            srcdir=Path(d)/"maps";srcdir.mkdir()
            source=srcdir/"original.gmp"
            source.write_bytes(b"original synthetic fixture")
            target=Path(d)/"reports";target.mkdir()
            with self.assertRaisesRegex(FileExistsError,"Destination exists"):
                exporter.export_map(source,target)
            self.assertEqual(source.read_bytes(),b"original synthetic fixture")

    def test_writer_on_disposable_destination_with_manifest(self):
        level,blocks,_=fixture()
        atlas=exporter.inspect_mesh(level,blocks)
        with tempfile.TemporaryDirectory() as d:
            maps=Path(d)/"maps";maps.mkdir()
            source=maps/"synthetic.gmp"
            source.write_bytes(b"fixture, not retail DX2")
            report=Path(d)/"reports"/"first_preview"
            meta={"file":source.name,"sha256":"fixture-only","licensee":69}
            with patch.object(exporter,"audit_map",return_value=(atlas,meta)):
                result=exporter.export_map(source,report)
            self.assertEqual(result["obj_faces_written"],2)
            self.assertEqual(source.read_bytes(),b"fixture, not retail DX2")
            obj=(report/"collision_triangles.obj").read_text()
            mtl=(report/"collision_triangles.mtl").read_text()
            manifest=json.loads((report/"triangle_provenance.json").read_text())
            self.assertEqual(obj.count("\nf "),2)
            self.assertEqual(mtl.count("newmtl"),2)
            self.assertEqual(len(manifest["triangles"]),2)
            self.assertEqual(manifest["export"]["obj_face_to_level_triangle_id"],[0,1])
            self.assertEqual(manifest["materials"][0]["render_material_name"],"MatA")
            self.assertFalse(manifest["render_material_names_are_physics_materials"])

    def test_writer_preserves_zero_area_triangle_in_manifest(self):
        level,blocks,_=fixture(code=b"\x28\x00\xff\x31",degenerate=True)
        atlas=exporter.inspect_mesh(level,blocks)
        with tempfile.TemporaryDirectory() as d:
            maps=Path(d)/"maps";maps.mkdir()
            source=maps/"synthetic.gmp";source.write_bytes(b"fixture")
            report=Path(d)/"report"
            with patch.object(exporter,"audit_map",return_value=(atlas,{"file":source.name})):
                result=exporter.export_map(source,report)
            obj=(report/"collision_triangles.obj").read_text()
            manifest=json.loads((report/"triangle_provenance.json").read_text())
            self.assertEqual(result["obj_faces_written"],1)
            self.assertEqual(obj.count("\nf "),1)
            self.assertEqual([tri["mopp_terminal_leaf"] for tri in manifest["triangles"]],
                             [False,True])
            self.assertEqual(manifest["export"]["zero_area_faces_not_in_mopp_omitted_from_obj"],1)
            self.assertEqual(manifest["export"]["obj_face_to_level_triangle_id"],[1])

    def test_missing_source_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"maps"/"nonexistent.gmp"
            with self.assertRaisesRegex(ValueError,"Expected existing"):
                exporter.audit_map(src)

if __name__=="__main__":
    unittest.main()