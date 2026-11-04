"""Asset-free DX2 Level MOPP triangle provenance and material-name tests."""
from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
import inspect_level_mopp_triangle_provenance as prov

DEFAULT_CODE=b'\x28\x00\xff\x27\x00\xff\x26\x00\xff\x20\x80\x01\x30\x31'


def fixture(*, separate_blocks=False, labels=None, code=DEFAULT_CODE,
            degenerate=False):
    if separate_blocks:
        coords=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),
                (3.,0.,0.),(5.,0.,0.),(3.,2.,0.)]
        groups=[([0,1,2],'MatA'),([0,1,2],'MatB')]
        blocks=[{'vertices':[(tuple(v/0.1905 for v in xyz), None, None)
                             for xyz in coords[bi*3:(bi+1)*3]],
                 'sections':[{'indices':g,'material':name}]}
                for bi,(g,name) in enumerate(groups)]
        global_idx=(0,1,2,3,4,5)
        if labels is None:labels=[(0,0),(2,0)]
    else:
        if degenerate:
            coords=[(0.,0.,0.),(2.,0.,0.),(4.,0.,0.),(0.,2.,0.),(2.,2.,0.)]
            global_idx=(0,1,2,0,3,4)
        else:
            coords=[(0.,0.,0.),(2.,0.,0.),(2.,2.,0.),(0.,2.,0.)]
            global_idx=(0,1,2,0,2,3)
        blocks=[{'vertices':[(tuple(v/0.1905 for v in xyz), None, None) for xyz in coords],
                 'sections':[{'indices':list(global_idx[:3]),'material':'MatA'},
                             {'indices':list(global_idx[3:]),'material':'MatB'}]}]
        if labels is None:labels=[(0,0),(0,1)]
    nverts,ntri=len(coords),len(global_idx)//3
    title=b'Test\x00'
    prefix=(bytes([255])*128+struct.pack('<6I',0,0,0,0x6f000000,0x013e4312,ntri)
            +b''.join(struct.pack('<II',*pair) for pair in labels)
            +struct.pack('<I',len(title)))
    header=struct.pack('<II6I',nverts,ntri,1,0,3,0,3,0)+title
    verts=b''.join(struct.pack('<3fI',*xyz,0) for xyz in coords)
    idx=struct.pack('<'+str(len(global_idx))+'I',*global_idx)
    mins=[min(x[a] for x in coords) for a in range(3)]
    maxs=[max(x[a] for x in coords) for a in range(3)]
    largest=max(maxs[a]-mins[a] for a in range(3))
    spatial=struct.pack('<4f',*(x-0.05 for x in mins),254*65536/(largest+0.1))
    tail=struct.pack('<I',len(code)+20)+spatial+struct.pack('<I',len(code))+code+bytes(12)
    return prefix+header+verts+idx+tail,blocks, len(prefix)-len(labels)*8-4-24


class TriangleProvenanceTests(unittest.TestCase):
    def test_full_chain_exact_two_sections(self):
        level,blocks,_=fixture()
        result=prov.inspect_triangle_provenance(level,blocks)
        self.assertEqual(result['triangle_provenance_record_count'],2)
        self.assertEqual(result['distinct_block_section_pairs'],2)
        self.assertEqual(result['mopp_leaves_with_render_section_attribution'],2)
        self.assertEqual(result['skipped_nonnegative_block_ids'],0)
        self.assertFalse(result['render_section_names_are_havok_physics_materials'])

    def test_distinct_material_names_opt_in_only(self):
        level,blocks,_=fixture()
        public=prov.inspect_triangle_provenance(level,blocks)
        private=prov.inspect_triangle_provenance(level,blocks,include_materials=True)
        self.assertNotIn('render_materials',public)
        self.assertEqual(private['render_materials'],[
            {'material_string':'MatA','all_triangles':1,'mopp_leaf_triangles':1},
            {'material_string':'MatB','all_triangles':1,'mopp_leaf_triangles':1},
        ])

    def test_gap_in_first_field_is_legal_and_accounted_for(self):
        level,blocks,_=fixture(separate_blocks=True)
        out=prov.inspect_triangle_provenance(level,blocks)
        self.assertEqual(out['unique_monotone_block_ids'],2)
        self.assertEqual(out['skipped_nonnegative_block_ids'],1)
        self.assertEqual((out['first_block_id'],out['last_block_id']),(0,2))

    def test_wrong_marker_rejected(self):
        level,blocks,at=fixture()
        bad=bytearray(level)
        struct.pack_into('<I',bad,at+16,0xDEADBEEF)
        with self.assertRaisesRegex(ValueError,'marker/count'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)

    def test_wrong_embedded_triangle_count_rejected(self):
        level,blocks,at=fixture()
        bad=bytearray(level)
        struct.pack_into('<I',bad,at+20,400)
        with self.assertRaisesRegex(ValueError,'marker/count'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)

    def test_corrupted_section_id_rejected(self):
        level,blocks,at=fixture()
        bad=bytearray(level)
        struct.pack_into('<I',bad,at+24+8+4,7)
        with self.assertRaisesRegex(ValueError,'section ID'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)

    def test_block_id_change_inside_block_rejected(self):
        level,blocks,at=fixture()
        bad=bytearray(level)
        struct.pack_into('<I',bad,at+24+8,1)
        with self.assertRaisesRegex(ValueError,'block ID changes'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)

    def test_duplicate_or_reordered_block_ids_rejected(self):
        level,blocks,at=fixture(separate_blocks=True)
        bad=bytearray(level)
        struct.pack_into('<I',bad,at+24+8,0)
        with self.assertRaisesRegex(ValueError,'strictly increasing'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)

    def test_header_name_length_and_terminator_fail_closed(self):
        level,blocks,at=fixture()
        bad=bytearray(level)
        label_end=at+24+16
        struct.pack_into('<I',bad,label_end,500)
        with self.assertRaisesRegex(ValueError,'name/header'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)
        bad=bytearray(level)
        title_at=label_end+4+32
        bad[title_at+4]=0x41
        with self.assertRaisesRegex(ValueError,'source-name encoding'):
            prov.inspect_triangle_provenance(bytes(bad),blocks)

    def test_mopp_corruption_still_rejected(self):
        level,blocks,_=fixture()
        bad=level[:-1]+b'\xff'
        with self.assertRaisesRegex(ValueError,'envelope'):
            prov.inspect_triangle_provenance(bad,blocks)

    def test_one_zero_area_triangle_without_leaf(self):
        level,blocks,_=fixture(code=b'\x28\x00\xff\x31',degenerate=True)
        out=prov.inspect_triangle_provenance(level,blocks,include_materials=True)
        self.assertEqual(out['mopp_leaves_with_render_section_attribution'],1)
        self.assertEqual(out['non_mopp_leaf_triangle_count'],1)
        self.assertEqual(out['render_materials'][0]['mopp_leaf_triangles'],0)
        self.assertEqual(out['render_materials'][1]['mopp_leaf_triangles'],1)

    def test_no_bytes_modified_and_bad_types_refused(self):
        level,blocks,_=fixture()
        digest=hashlib.sha256(level).digest()
        prov.inspect_triangle_provenance(level,blocks)
        self.assertEqual(hashlib.sha256(level).digest(),digest)
        with self.assertRaises(ValueError):
            prov.inspect_triangle_provenance(level,blocks,include_materials='yes')

    def test_repeated_map_paths_refused_before_input_parse(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.gmp';path.write_bytes(b'synthetic')
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                prov.audit_maps([path,path])

if __name__=='__main__':
    unittest.main()
