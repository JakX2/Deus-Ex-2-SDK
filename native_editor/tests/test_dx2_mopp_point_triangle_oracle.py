"""No-retail-data tests of independent geometry versus MOPP candidate coverage."""
from __future__ import annotations

from pathlib import Path
import copy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import inspect_mopp_point_triangle_oracle as oracle
import inspect_mopp_axis_point_candidates as mopp


class _FakeWalker:
    def __init__(self, ids):
        self.ids = ids

    def point(self, xyz, *, diagonal_mode="conservative", tolerance_units=1.0):
        return {"candidate_triangle_ids": self.ids}


def square_faces():
    verts = [(0.,0.,0.),(2.,0.,0.),(0.,2.,0.),(2.,2.,0.)]
    faces = [(0,1,2,True),(1,3,2,True)]
    return verts, faces


class LevelPointTriangleOracleTests(unittest.TestCase):
    def test_two_triangles_in_one_square_boundary_and_interior(self):
        vertices, faces = square_faces()
        o = oracle.LevelPointTriangleOracle(vertices, faces)
        self.assertEqual(o.containing_triangle_ids((0.25,0.25,0)),[0])
        self.assertEqual(o.containing_triangle_ids((1.75,1.75,0)),[1])
        self.assertEqual(o.containing_triangle_ids((1,1,0)),[0,1])
        self.assertEqual(o.containing_triangle_ids((3,3,0)),[])

    def test_duplicate_vertex_indices_and_reversed_winding_count_both(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),
           (0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        f=[(0,1,2,True),(5,4,3,True)]
        o=oracle.LevelPointTriangleOracle(v,f)
        self.assertEqual(o.containing_triangle_ids((0.2,0.3,0)),[0,1])

    def test_geometry_oracle_catches_synthetically_bad_mopp_pruning(self):
        verts=[(0,0,100),(1,0,100),(0,1,100),
               (0,0,100),(1,0,100),(0,1,100)]
        faces=[(0,1,2,True),(3,4,5,True)]
        o=oracle.LevelPointTriangleOracle(verts, faces)
        hit=oracle.compare_point_to_mopp(o,_FakeWalker([0]),(.25,.25,100.))
        self.assertEqual(hit["geometric_hit_original_triangle_ids"],[0,1])
        self.assertEqual(hit["geometrically_intersecting_triangles_missing_from_mopp"],[1])
        self.assertFalse(hit["all_geometric_hits_retained"])
        self.assertFalse(hit["mopp_output_is_havok_runtime_contact"])

    def test_real_synthetic_mopp_walker_can_lose_overlap(self):
        verts=[(0,0,100),(1,0,100),(0,1,100),
               (0,0,100),(1,0,100),(0,1,100)]
        faces=[(0,1,2,True),(3,4,5,True)]
        o=oracle.LevelPointTriangleOracle(verts, faces)
        # Structurally correct split with both triangles on same side of X=128.
        code=b"\x28\x00\xff\x20\x80\x01\x30\x31"
        walker=mopp.ConservativeMoppPointCandidates(
            code,2,(0.,0.,0.,65536.))
        hit=oracle.compare_point_to_mopp(o,walker,(.2,.3,100.))
        self.assertEqual(hit["geometric_hit_original_triangle_ids"],[0,1])
        self.assertEqual(hit["mopp_candidate_original_triangle_ids"],[0])
        self.assertEqual(hit["geometrically_intersecting_triangles_missing_from_mopp"],[1])

    def test_3d_nonparallel_triangles_intersect_on_shared_line(self):
        verts=[(-1.,-1.,0.),(1.,-1.,0.),(0.,1.,0.),
               (0.,-1.,-1.),(0.,-1.,1.),(0.,1.,0.)]
        faces=[(0,1,2,True),(3,4,5,True)]
        o=oracle.LevelPointTriangleOracle(verts,faces)
        self.assertEqual(o.containing_triangle_ids((0,0,0)),[0,1])
        self.assertEqual(o.containing_triangle_ids((.1,0,0)),[0])
        self.assertEqual(o.containing_triangle_ids((0,0,.1)),[1])

    def test_plane_tolerance_does_not_turn_parallel_off_plane_into_hit(self):
        v=[(0,0,0),(2,0,0),(0,2,0),
           (0,0,.025),(2,0,.025),(0,2,.025)]
        o=oracle.LevelPointTriangleOracle(v,[(0,1,2,True),(3,4,5,True)])
        self.assertEqual(o.containing_triangle_ids((.25,.25,0)),[0])
        self.assertEqual(o.containing_triangle_ids((.25,.25,.025)),[1])
        self.assertEqual(o.containing_triangle_ids((.25,.25,.0125)),[])

    def test_zero_area_nonleaf_gaps_preserve_original_ids(self):
        v=[(0,0,0),(1,0,0),(2,0,0),(0,1,0)]
        o=oracle.LevelPointTriangleOracle(v,[(0,1,2,False),(0,1,3,True)],leaf_ids=[1])
        self.assertEqual(o.containing_triangle_ids((.2,.2,0)),[1])
        self.assertNotIn(0,o.tris)
        self.assertEqual(o.original_triangle_count,2)

    def test_wrong_mopp_leaf_set_and_degenerate_leaf_refused(self):
        v=[(0,0,0),(1,0,0),(2,0,0),(0,1,0)]
        with self.assertRaisesRegex(ValueError,"leaf-ID set"):
            oracle.LevelPointTriangleOracle(v,[(0,1,2,False),(0,1,3,True)],leaf_ids=[0])
        with self.assertRaisesRegex(ValueError,"Degenerate"):
            oracle.LevelPointTriangleOracle(v,[(0,1,2,True)])
        with self.assertRaisesRegex(ValueError,"missing MOPP"):
            oracle.LevelPointTriangleOracle(v,[(0,1,3,False)])

    def test_bvh_matches_brute_triangle_predicate_for_random_grid(self):
        verts, faces=square_faces()
        o=oracle.LevelPointTriangleOracle(verts,faces)
        for ix in range(-1,9):
            for iy in range(-1,9):
                p=(ix/4.,iy/4.,0.)
                brute=sorted(tid for tid,t in o.tris.items()
                             if o._contains(t,p,1e-5,1e-8))
                self.assertEqual(o.containing_triangle_ids(p),brute)

    def test_missing_geometry_and_out_of_range_source_indices_refused(self):
        v,f=square_faces()
        for faces in ([(-1,1,2,True)],[(0,1,999,True)],[(0,1,2,1)],
                      [(0,1,2)],[(0,1,True,True)]):
            with self.subTest(faces=faces),self.assertRaises(ValueError):
                oracle.LevelPointTriangleOracle(v,faces)

    def test_nonfinite_coordinates_and_boolean_weights_refused(self):
        v,f=square_faces()
        bad=copy.deepcopy(v)
        bad[0]=(float('nan'),0,0)
        with self.assertRaises(ValueError):
            oracle.LevelPointTriangleOracle(bad,f)
        o=oracle.LevelPointTriangleOracle(v,f)
        with self.assertRaises(ValueError):
            o.sample_triangle(0,(True,0,0))
        with self.assertRaises(ValueError):
            o.containing_triangle_ids((0,0,0),plane_tolerance=-1)
        with self.assertRaises(ValueError):
            o.containing_triangle_ids((0,0,0),barycentric_tolerance=float('inf'))

    def test_original_atlas_source_id_mapping(self):
        v,f=square_faces()
        atlas={"vertices":v,"source_vertex_count":len(v),"source_triangle_count":len(f),
               "triangles":[{"triangle_id":i,"vertex_indices_zero_based":list(face[:3]),
                            "mopp_terminal_leaf":face[3]} for i,face in enumerate(f)]}
        o=oracle.original_atlas_oracle(atlas)
        self.assertEqual(o.containing_triangle_ids((1,1,0)),[0,1])
        atlas["triangles"][1]["triangle_id"]=123
        with self.assertRaisesRegex(ValueError,"out of original"):
            oracle.original_atlas_oracle(atlas)

    def test_source_data_and_sampling_are_nonmutating(self):
        v,f=square_faces()
        original=(copy.deepcopy(v),copy.deepcopy(f))
        o=oracle.LevelPointTriangleOracle(v,f)
        p=o.sample_triangle(0,(.2,.3,.5))
        self.assertEqual(o.containing_triangle_ids(p),[0])
        self.assertEqual((v,f),original)

    def test_compare_rejects_foreign_triangle_id(self):
        v,f=square_faces()
        o=oracle.LevelPointTriangleOracle(v,f)
        with self.assertRaisesRegex(ValueError,"unverified"):
            oracle.compare_point_to_mopp(o,_FakeWalker([999]),(.2,.2,0))


if __name__ == '__main__':
    unittest.main()
