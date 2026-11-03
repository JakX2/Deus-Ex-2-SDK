"""Fixture-only tests for DX2 Level flattened geometry cross-reference."""
from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_level_flattened_mesh_crossref as cross

SRC_VERTICES = [(0.,0.,0.), (32.,0.,0.), (32.,16.,-8.), (0.,16.,-8.)]


def synthetic(*, verts=SRC_VERTICES, sections=None, header_name=b"Index.unr"):
    if sections is None:
        sections = [(0,1,2,0,2,3)]
    assert sum(len(s) for s in sections) % 3 == 0
    blocks = [{"vertices":[(v, [0.,0.,1.], (0.,0.)) for v in verts],
               "sections":[{"indices":list(s)} for s in sections]}]
    indices = [i for group in sections for i in group]
    nv, nt = len(verts), len(indices)//3
    prefix = bytes([255])*180
    header = struct.pack("<II6I",nv,nt,1,0,2,0,2,0)+header_name+b"\0"
    xyz = b"".join(struct.pack("<3fI",*(x*0.1905 for x in v),0) for v in verts)
    idx = struct.pack("<"+str(len(indices))+"I",*indices)
    return prefix+header+xyz+idx+b"trailing unknown data", blocks


class FlattenedLevelMeshTests(unittest.TestCase):
    def test_exact_global_index_and_scaled_xyz_crossref(self):
        raw, blocks = synthetic()
        out = cross.inspect_level_flattened_mesh(raw,blocks)
        self.assertEqual(out["status"],"exact_global_triangle_indices_and_scaled_vertex_xyz")
        self.assertEqual(out["validated_render_blocks"],1)
        self.assertEqual(out["render_and_flat_vertex_count"],4)
        self.assertEqual(out["render_and_flat_triangle_count"],2)
        self.assertEqual(out["verified_global_u32_triangle_indices"],6)
        self.assertEqual(out["verified_scaled_float_components"],12)
        self.assertFalse(out["collision_semantics_verified"])
        self.assertFalse(out["native_world_model_vertex_pool_link_verified"])

    def test_alternate_header_and_split_render_sections(self):
        raw, blocks = synthetic(header_name=b"Autoplay",sections=[(0,1,2),(0,2,3)])
        self.assertEqual(cross.inspect_level_flattened_mesh(raw,blocks)[
            "verified_global_u32_triangle_indices"],6)

    def test_global_index_bases_across_multiple_blocks(self):
        _, original=synthetic()
        second = {"vertices":[((64.,0.,0.),None,None),((80.,0.,0.),None,None),
                              ((64.,16.,0.),None,None)],
                  "sections":[{"indices":[0,1,2]}]}
        blocks=[original[0],second]
        verts=SRC_VERTICES+[x[0] for x in second["vertices"]]
        indices=[0,1,2,0,2,3,4,5,6]
        header=struct.pack("<II6I",len(verts),3,1,0,2,0,2,0)+b"Index.unr\0"
        coords=b"".join(struct.pack("<3fI",*(x*0.1905 for x in v),0) for v in verts)
        data=bytes([255])*180+header+coords+struct.pack("<9I",*indices)+b"remaining"
        out=cross.inspect_level_flattened_mesh(data,blocks)
        self.assertEqual(out["render_and_flat_vertex_count"],7)
        self.assertEqual(out["render_and_flat_triangle_count"],3)
        self.assertEqual(out["validated_render_blocks"],2)

    def test_mutated_flat_index_array_rejected(self):
        data,blocks=synthetic()
        bad=bytearray(data)
        p=bad.find(struct.pack("<6I",0,1,2,0,2,3))
        struct.pack_into("<I",bad,p+4,3)
        with self.assertRaisesRegex(ValueError,"exactly one full flattened index array"):
            cross.inspect_level_flattened_mesh(bytes(bad),blocks)

    def test_scaled_vertex_mutation_rejected(self):
        data,blocks=synthetic()
        p=data.find(struct.pack("<6I",0,1,2,0,2,3))
        bad=bytearray(data)
        struct.pack_into("<f",bad,p-16*4+20,40.)
        with self.assertRaisesRegex(ValueError,"scaled render position"):
            cross.inspect_level_flattened_mesh(bytes(bad),blocks)

    def test_nonzero_vertex_fourth_word_rejected(self):
        data,blocks=synthetic()
        p=data.find(struct.pack("<6I",0,1,2,0,2,3))
        bad=bytearray(data)
        struct.pack_into("<I",bad,p-16*4+12,1)
        with self.assertRaisesRegex(ValueError,"nonzero padding"):
            cross.inspect_level_flattened_mesh(bytes(bad),blocks)

    def test_missing_and_duplicate_counts_rejected(self):
        data,blocks=synthetic()
        needle=struct.pack("<II",4,2)
        p=data.find(needle)
        bad=bytearray(data);bad[p:p+8]=bytes(8)
        with self.assertRaisesRegex(ValueError,"count pair"):
            cross.inspect_level_flattened_mesh(bytes(bad),blocks)
        duplicated=data[:p-20]+needle+data[p-12:]
        with self.assertRaisesRegex(ValueError,"count pair"):
            cross.inspect_level_flattened_mesh(duplicated,blocks)

    def test_duplicate_full_index_stream_rejected(self):
        data,blocks=synthetic()
        duplicate=data+struct.pack("<6I",0,1,2,0,2,3)
        with self.assertRaisesRegex(ValueError,"exactly one full flattened index array"):
            cross.inspect_level_flattened_mesh(duplicate,blocks)

    def test_invalid_inputs_rejected_without_source_mutation(self):
        data,blocks=synthetic()
        digest=hashlib.sha256(data).digest()
        with self.assertRaises(ValueError):
            cross.inspect_level_flattened_mesh(data,[])
        altered=[{"vertices":blocks[0]["vertices"],
                  "sections":[{"indices":[0,1,7]}]}]
        with self.assertRaisesRegex(ValueError,"out of range"):
            cross.inspect_level_flattened_mesh(data,altered)
        with self.assertRaises(ValueError):
            cross.inspect_level_flattened_mesh(b"tiny",blocks)
        self.assertEqual(hashlib.sha256(data).digest(),digest)

    def test_duplicate_map_paths_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"fixture.gmp"
            path.write_bytes(b"synthetic fixture, never a retail map")
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                cross.audit_maps([path,path])
            self.assertEqual(path.read_bytes(),b"synthetic fixture, never a retail map")


if __name__ == "__main__":
    unittest.main()
