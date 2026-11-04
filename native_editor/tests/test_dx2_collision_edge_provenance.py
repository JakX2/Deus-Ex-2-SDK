"""Synthetic, asset-free geometric edge diagnostics tests for DX2Ed."""
from __future__ import annotations
import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'native_editor' / 'godot_editor' / 'backend'))
import dx2_collision_edge_provenance as edge


def atlas(vertices=None, faces=None, material_count=2):
    if vertices is None:
        vertices = [(0., 0., 0.), (2.,0.,0.), (0.,2.,0.), (2.,2.,0.)]
    if faces is None:
        faces = [([0,1,2],0,True),([1,3,2],1,True)]
    return {
        'vertices': vertices, 'source_vertex_count': len(vertices),
        'triangles': [dict(triangle_id=i, vertex_indices_zero_based=v,
                           render_material_id=m, mopp_terminal_leaf=leaf)
                      for i,(v,m,leaf) in enumerate(faces)],
        'source_triangle_count': len(faces),
        'mopp_leaf_triangle_count': sum(leaf for _,_,leaf in faces),
        'zero_area_nonleaf_triangle_count': sum(not leaf for _,_,leaf in faces),
        'materials': [{'id':i,'render_material_name':str(i), 'physics_material_verified':False}
                      for i in range(material_count)],
    }


class SourceEdgeDiagnosticsTests(unittest.TestCase):
    def test_two_triangles_different_render_materials(self):
        result = edge.classify_source_edges(atlas())
        self.assertEqual(result['open_boundary_edges'],4)
        self.assertEqual(result['two_triangle_render_material_seams'],1)
        self.assertEqual(result['two_triangle_same_material_edges'],0)
        self.assertEqual(result['unique_source_edges'],5)
        self.assertEqual(result['edge_codes_by_original_triangle_id'],[[1,2,1],[1,1,2]])
        self.assertFalse(result['physical_materials_verified'])

    def test_identical_material_shared_edge_is_not_seam(self):
        a=atlas()
        a['triangles'][1]['render_material_id']=0
        result=edge.classify_source_edges(a)
        self.assertEqual(result['two_triangle_same_material_edges'],1)
        self.assertEqual(result['two_triangle_render_material_seams'],0)
        self.assertEqual(result['edge_codes_by_original_triangle_id'],[[1,0,1],[1,1,0]])

    def test_exact_xyz_welding_across_duplicate_vertex_indices(self):
        a=atlas(vertices=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),
                          (2.,0.,0.),(2.,2.,0.),(0.,2.,0.)],
                faces=[([0,1,2],0,True),([3,4,5],1,True)])
        result=edge.classify_source_edges(a)
        self.assertEqual(result['source_exact_welded_vertex_count'],4)
        self.assertEqual(result['two_triangle_render_material_seams'],1)
        self.assertEqual(result['unique_source_edges'],5)

    def test_no_epsilon_welding_of_nearby_separate_vertices(self):
        a=atlas(vertices=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),
                          (2.000001,0.,0.),(2.,2.,0.),(0.,2.,0.)],
                faces=[([0,1,2],0,True),([3,4,5],1,True)])
        result=edge.classify_source_edges(a)
        self.assertEqual(result['two_triangle_render_material_seams'],0)
        self.assertEqual(result['open_boundary_edges'],6)

    def test_nonmanifold_three_incident_triangles(self):
        a=atlas(vertices=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),(0.,-2.,0.),(0.,0.,2.)],
                faces=[([0,1,2],0,True),([1,0,3],0,True),([0,1,4],1,True)])
        result=edge.classify_source_edges(a)
        self.assertEqual(result['three_or_more_triangle_edges'],1)
        self.assertEqual(result['max_triangles_using_one_edge'],3)
        for row in result['edge_codes_by_original_triangle_id']:
            self.assertIn(3,row)

    def test_ignored_zero_area_nonleaf_does_not_add_boundary(self):
        a=atlas(vertices=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),(4.,0.,0.)],
                faces=[([0,1,2],0,True),([0,1,3],1,False)])
        result=edge.classify_source_edges(a)
        self.assertEqual(result['edge_codes_by_original_triangle_id'],[[1,1,1],None])
        self.assertEqual(result['open_boundary_edges'],3)

    def test_mopp_leaf_zero_area_refused(self):
        a=atlas(vertices=[(0.,0.,0.),(2.,0.,0.),(4.,0.,0.)],faces=[([0,1,2],0,True)])
        with self.assertRaisesRegex(ValueError, 'Degenerate'):
            edge.classify_source_edges(a)

    def test_collapsed_mopp_edge_refused(self):
        a=atlas(vertices=[(0.,0.,0.),(2.,0.,0.),(2.,0.,0.)],faces=[([0,1,2],0,True)])
        with self.assertRaisesRegex(ValueError,'Collapsed'):
            edge.classify_source_edges(a)

    def test_corrupt_source_vertex_index_refused(self):
        a=atlas()
        a['triangles'][0]['vertex_indices_zero_based'][1]=999
        with self.assertRaisesRegex(ValueError,'Malformed'):
            edge.classify_source_edges(a)

    def test_wrong_original_triangle_order_refused(self):
        a=atlas()
        a['triangles'][1]['triangle_id']=8
        with self.assertRaisesRegex(ValueError,'Out-of-order'):
            edge.classify_source_edges(a)

    def test_wrong_leaf_count_refused(self):
        a=atlas()
        a['mopp_leaf_triangle_count']=999
        with self.assertRaisesRegex(ValueError,'MOPP leaf counts'):
            edge.classify_source_edges(a)

    def test_input_not_mutated(self):
        a=atlas()
        before=copy.deepcopy(a)
        edge.classify_source_edges(a)
        self.assertEqual(a,before)


if __name__ == '__main__':
    unittest.main()
