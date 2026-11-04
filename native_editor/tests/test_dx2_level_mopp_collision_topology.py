"""Fixture-only DX2 MOPP triangle-soup topology tests; no retail assets."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import inspect_level_mopp_collision_topology as topology


def atlas(vertices=None, faces=((0,1,2),(0,2,3)), *, materials=(0,1), leaves=None):
    if vertices is None:
        vertices = [(0.,0.,0.),(1.,0.,0.),(1.,1.,0.),(0.,1.,0.)]
    if leaves is None:
        leaves = [True] * len(faces)
    return {
        'source_vertex_count': len(vertices),
        'source_triangle_count': len(faces),
        'mopp_leaf_triangle_count': sum(leaves),
        'zero_area_nonleaf_triangle_count': len(faces)-sum(leaves),
        'vertices': list(vertices),
        'triangles': [
            {'triangle_id':i,'vertex_indices_zero_based':list(face),
             'render_material_id':materials[i], 'mopp_terminal_leaf':leaves[i]}
            for i,face in enumerate(faces)
        ],
        'materials': [{'id':i,'render_material_name':f'Surface_{i}'} for i in range(max(materials)+1)],
    }


class TopologyTests(unittest.TestCase):
    def test_two_triangle_quad_counts_and_material_seam(self):
        r = topology.inspect_topology(atlas())
        self.assertEqual(r['mopp_linked_triangles_audited'],2)
        self.assertEqual(r['unique_exact_position_edges'],5)
        self.assertEqual(r['one_triangle_boundary_edges'],4)
        self.assertEqual(r['two_triangle_shared_edges'],1)
        self.assertEqual(r['two_triangle_same_winding_direction_edges'],0)
        self.assertEqual(r['two_triangle_different_render_material_edges'],1)
        self.assertEqual(r['edge_connected_triangle_components'],1)
        self.assertEqual(r['largest_edge_connected_component_faces'],2)
        self.assertTrue(r['all_edges_accounted_for'])
        self.assertFalse(r['physical_materials_verified'])

    def test_exactly_equal_duplicate_positions_weld_across_sections(self):
        raw=atlas(vertices=[(0.,0.,0.),(1.,0.,0.),(1.,1.,0.),(0.,1.,0.),
                            (0.,0.,0.),(1.,1.,0.)], faces=((0,1,2),(4,5,3)))
        r=topology.inspect_topology(raw)
        self.assertEqual(r['distinct_exact_xyz_positions'],4)
        self.assertEqual(r['duplicated_flat_vertex_positions'],2)
        self.assertEqual(r['two_triangle_shared_edges'],1)

    def test_almost_equal_positions_are_not_welded(self):
        raw=atlas(vertices=[(0.,0.,0.),(1.,0.,0.),(1.,1.,0.),(0.,1.,0.),
                            (0.000001,0.,0.),(1.,1.000001,0.)],
                  faces=((0,1,2),(4,5,3)))
        r=topology.inspect_topology(raw)
        self.assertEqual(r['distinct_exact_xyz_positions'],6)
        self.assertEqual(r['one_triangle_boundary_edges'],6)
        self.assertEqual(r['edge_connected_triangle_components'],2)

    def test_same_direction_winding_conflict_is_reported_not_rejected(self):
        raw=atlas(faces=((0,1,2),(3,1,2)))
        r=topology.inspect_topology(raw)
        self.assertEqual(r['two_triangle_same_winding_direction_edges'],1)
        self.assertEqual(r['two_triangle_shared_edges'],1)

    def test_nonmanifold_three_faces_connected_by_one_edge(self):
        vertices=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,-1.,0.),(0.,0.,1.)]
        raw=atlas(vertices=vertices,faces=((0,1,2),(1,0,3),(0,1,4)),materials=(0,0,0))
        out=topology.inspect_topology(raw,include_examples=True)
        self.assertEqual(out['three_or_more_triangle_nonmanifold_edges'],1)
        self.assertEqual(out['one_triangle_boundary_edges'],6)
        self.assertEqual(out['max_triangles_using_one_edge'],3)
        self.assertEqual(out['edge_connected_triangle_components'],1)
        self.assertEqual(out['nonmanifold_examples'][0]['triangle_ids'],[0,1,2])

    def test_disconnected_faces_have_two_islands(self):
        vertices=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(5.,0.,0.),(6.,0.,0.),(5.,1.,0.)]
        out=topology.inspect_topology(atlas(vertices=vertices,faces=((0,1,2),(3,4,5))))
        self.assertEqual(out['edge_connected_triangle_components'],2)
        self.assertEqual(out['single_triangle_components'],2)

    def test_zero_area_triangle_can_be_excluded_only_when_nonleaf(self):
        vertices=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(2.,0.,0.)]
        raw=atlas(vertices=vertices,faces=((0,1,2),(0,1,3)), leaves=[True,False])
        out=topology.inspect_topology(raw)
        self.assertEqual(out['mopp_linked_triangles_audited'],1)
        self.assertEqual(out['non_mopp_leaf_triangles_excluded'],1)
        self.assertEqual(out['unique_exact_position_edges'],3)

    def test_zero_area_mopp_leaf_rejected(self):
        raw=atlas(faces=((0,0,2),),materials=(0,))
        with self.assertRaisesRegex(ValueError,'collapsed geometric edge'):
            topology.inspect_topology(raw)

    def test_non_mopp_nonzero_area_rejected(self):
        raw=atlas(leaves=[False,True])
        with self.assertRaisesRegex(ValueError,'Non-MOPP triangle'):
            topology.inspect_topology(raw)

    def test_bad_triangle_order_and_range_rejected(self):
        raw=atlas();raw['triangles'][0]['triangle_id']=4
        with self.assertRaisesRegex(ValueError,'Out-of-order'):
            topology.inspect_topology(raw)
        raw=atlas();raw['triangles'][0]['vertex_indices_zero_based'][0]=100
        with self.assertRaisesRegex(ValueError,'invalid flattened vertex'):
            topology.inspect_topology(raw)

    def test_bad_material_and_input_count_rejected(self):
        raw=atlas();raw['triangles'][0]['render_material_id']=999
        with self.assertRaisesRegex(ValueError,'render material ID'):
            topology.inspect_topology(raw)
        raw=atlas();raw['source_triangle_count']=1
        with self.assertRaisesRegex(ValueError,'counts disagree'):
            topology.inspect_topology(raw)

    def test_nonfinite_and_invalid_flag_rejected(self):
        raw=atlas();raw['vertices'][1]=(float('nan'),0.,0.)
        with self.assertRaisesRegex(ValueError,'Invalid flattened vertex'):
            topology.inspect_topology(raw)
        with self.assertRaisesRegex(ValueError,'include_examples'):
            topology.inspect_topology(atlas(),include_examples='yes')

    def test_input_data_remains_unchanged(self):
        raw=atlas();snapshot=copy.deepcopy(raw)
        topology.inspect_topology(raw)
        self.assertEqual(raw,snapshot)

    def test_duplicate_map_paths_fail_before_io(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'sample.gmp'
            source.write_bytes(b'not game data')
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                topology.audit_maps([source,source])
            self.assertEqual(source.read_bytes(),b'not game data')


if __name__=='__main__':
    unittest.main()