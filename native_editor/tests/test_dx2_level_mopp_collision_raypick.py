"""Synthetic, asset-free tests for read-only DX2 collision triangle ray selection."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research' / 'dx2'))
import inspect_level_mopp_collision_raypick as ray


def fixture(*, flat_nonleaf=True, count=2):
    vertices = []
    triangles = []
    names = ['Flesh/A', 'Flesh/B']
    materials = [{'id': i, 'render_material_name': name,
                  'obj_material':f'debug_{i:04d}', 'physics_material_verified':False}
                 for i, name in enumerate(names)]
    for i in range(count):
        base = len(vertices)
        z = (2.0 if i == 0 else 0.0) if count == 2 else float(i * 2)
        # All triangles are CCW from +Z; two projected faces can overlap.
        vertices.extend([(0.0, 0.0, z), (2.0, 0.0, z), (0.0, 2.0, z)])
        triangles.append({'triangle_id':i,'source_block_id':i+10,
                          'render_block_ordinal':i,
                          'render_section_ordinal':i%2,
                          'render_material_id':i%2,
                          'vertex_indices_zero_based':[base,base+1,base+2],
                          'mopp_terminal_leaf':True})
    if flat_nonleaf:
        base = len(vertices)
        vertices += [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (2.0, 0.0, 1.0)]
        triangles.append({'triangle_id':len(triangles),'source_block_id':100,
                          'render_block_ordinal':3, 'render_section_ordinal':0,
                          'render_material_id':0,
                          'vertex_indices_zero_based':[base,base+1,base+2],
                          'mopp_terminal_leaf':False})
    return {
        'schema':ray.topology.debug.SCHEMA,
        'source_vertex_count':len(vertices),
        'source_triangle_count':len(triangles),
        'mopp_leaf_triangle_count':count,
        'zero_area_nonleaf_triangle_count':int(flat_nonleaf),
        'vertices':vertices,'triangles':triangles,'materials':materials,
    }


class CollisionRayPickerTests(unittest.TestCase):
    def test_two_hits_sorted_and_original_material_provenance_preserved(self):
        index=ray.CollisionRayPicker(fixture())
        result=index.cast((0.5,0.5,4),(0,0,-2))
        self.assertEqual(result['status'],'geometric_hits')
        self.assertEqual([h['original_level_triangle_id'] for h in result['hits']],[0,1])
        self.assertEqual([h['distance_in_level_coordinate_units'] for h in result['hits']],[2.,4.])
        self.assertEqual(result['hits'][0]['render_material_name'],'Flesh/A')
        self.assertEqual(result['hits'][1]['source_block_id'],11)
        self.assertEqual(result['hits'][1]['render_section_ordinal'],1)
        self.assertEqual(result['ignored_zero_area_nonleaf_triangles'],1)
        self.assertFalse(result['independent_havok_runtime_hit_test'])
        self.assertFalse(result['physics_materials_or_filters_decoded'])

    def test_exact_barycentric_position_and_winding_normal(self):
        result=ray.CollisionRayPicker(fixture()).cast((0.5,0.5,3),(0,0,-1))
        hit=result['hits'][0]
        self.assertEqual(hit['hit_point_level_xyz'],[.5,.5,2.0])
        self.assertEqual(hit['barycentric_abc'],[.5,.25,.25])
        self.assertEqual(hit['geometric_winding_normal_xyz'],[0.,0.,1.])
        self.assertTrue(hit['ray_hits_winding_front_face'])
        self.assertFalse(hit['render_material_is_physics_material'])

    def test_backface_culling_and_double_sided_selection(self):
        pick=ray.CollisionRayPicker(fixture())
        a=pick.cast((.5,.5,-1),(0,0,1),cull_backfaces=False)
        self.assertEqual(a['total_geometric_intersections'],2)
        self.assertFalse(a['hits'][0]['ray_hits_winding_front_face'])
        b=pick.cast((.5,.5,-1),(0,0,1),cull_backfaces=True)
        self.assertEqual(b['status'],'geometric_miss')

    def test_distance_capping_truncation_and_order(self):
        pick=ray.CollisionRayPicker(fixture())
        self.assertEqual(pick.cast((.5,.5,4),(0,0,-1),max_distance=2.5)[
            'total_geometric_intersections'],1)
        result=pick.cast((.5,.5,4),(0,0,-1),max_hits=1)
        self.assertEqual(len(result['hits']),1)
        self.assertEqual(result['total_geometric_intersections'],2)
        self.assertTrue(result['results_truncated'])

    def test_outside_bounds_pruned_and_zero_component_is_supported(self):
        pick=ray.CollisionRayPicker(fixture())
        result=pick.cast((100.,100.,4.),(0,0,-1))
        self.assertEqual(result['status'],'geometric_miss')
        self.assertEqual(result['cpu_triangles_tested'],0)
        self.assertEqual(result['cpu_bvh_boxes_tested'],1)

    def test_many_faces_build_median_bvh_deterministically(self):
        data=fixture(count=17,flat_nonleaf=False)
        first=ray.CollisionRayPicker(data)
        second=ray.CollisionRayPicker(data)
        self.assertGreater(len(first.nodes),1)
        self.assertEqual(first.nodes,second.nodes)
        result=first.cast((.5,.5,40),(0,0,-1),max_hits=32)
        self.assertEqual(result['total_geometric_intersections'],17)
        self.assertEqual(result['hits'][0]['original_level_triangle_id'],16)
        self.assertLessEqual(result['cpu_triangles_tested'],17)

    def test_tied_geometric_hits_sort_by_original_triangle_id(self):
        source=fixture(flat_nonleaf=False)
        source['vertices'][3:6]=list(source['vertices'][0:3])
        first=ray.CollisionRayPicker(source).cast((.5,.5,5),(0,0,-1))
        self.assertEqual([h['original_level_triangle_id'] for h in first['hits']],[0,1])

    def test_ray_input_errors_are_rejected(self):
        pick=ray.CollisionRayPicker(fixture())
        bad=[((0,0,0),(0,0,0),{}), ((0,0,0),(0,float('nan'),1),{}),
             ((0,0,0),(0,0,1),{'max_distance':-1}),
             ((0,0,0),(0,0,1),{'max_hits':0}),
             ((0,0,0),(0,0,1),{'cull_backfaces':'yes'}),
             ((True,0,0),(0,0,1),{})]
        for origin,direction,opts in bad:
            with self.subTest(origin=origin,direction=direction,opts=opts):
                with self.assertRaises(ValueError): pick.cast(origin,direction,**opts)

    def test_invalid_atlas_is_refused_before_bvh_construction(self):
        atlas=fixture()
        atlas['triangles'][0]['vertex_indices_zero_based'][2]=10_000
        with self.assertRaises(ValueError):ray.CollisionRayPicker(atlas)
        atlas=fixture()
        atlas['triangles'][2]['mopp_terminal_leaf']=True
        atlas['mopp_leaf_triangle_count']+=1
        atlas['zero_area_nonleaf_triangle_count']=0
        with self.assertRaises(ValueError):ray.CollisionRayPicker(atlas)

    def test_unverified_material_metadata_is_refused(self):
        atlas=fixture()
        atlas['materials'][0]['physics_material_verified']=True
        with self.assertRaisesRegex(ValueError,'Invalid/untrusted render material'):
            ray.CollisionRayPicker(atlas)
        atlas=fixture()
        atlas['triangles'][0]['source_block_id']='not-an-ID'
        with self.assertRaisesRegex(ValueError,'provenance'):
            ray.CollisionRayPicker(atlas)

    def test_missing_authentic_atlas_schema_refused(self):
        atlas=fixture()
        atlas.pop('schema')
        with self.assertRaisesRegex(ValueError,'schema'):
            ray.CollisionRayPicker(atlas)

    def test_original_atlas_is_not_modified(self):
        atlas=fixture()
        before=hashlib.sha256(json.dumps(atlas,sort_keys=True).encode()).hexdigest()
        ray.CollisionRayPicker(atlas).cast((.5,.5,3),(0,0,-1))
        after=hashlib.sha256(json.dumps(atlas,sort_keys=True).encode()).hexdigest()
        self.assertEqual(before,after)

    def test_report_outside_source_directory_exclusive(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)
            srcdir=base/'GameMaps';srcdir.mkdir()
            source=srcdir/'map.gmp';source.write_bytes(b'unchanged synthetic game map')
            report={'schema':ray.SCHEMA, 'status':'geometric_miss'}
            with self.assertRaises(ValueError):
                ray.write_report(report,source,srcdir/'report.json')
            target=base/'Reports'/'pick.json'
            ray.write_report(report,source,target)
            self.assertEqual(json.loads(target.read_text()),report)
            with self.assertRaises(FileExistsError):ray.write_report(report,source,target)
            self.assertEqual(source.read_bytes(),b'unchanged synthetic game map')

    def test_ray_starting_on_surface_does_not_self_hit(self):
        pick=ray.CollisionRayPicker(fixture())
        result=pick.cast((.5,.5,2),(0,0,-1))
        self.assertEqual([h['original_level_triangle_id'] for h in result['hits']],[1])
        self.assertEqual(result['hits'][0]['distance_in_level_coordinate_units'],2.)


if __name__=='__main__':
    unittest.main()
