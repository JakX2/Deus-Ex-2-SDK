"""Synthetic unchanged MOPP candidate regression and sample locations."""
import unittest
from inspect_vbsp_candidate_collision import compare_triangle,triangle_samples


class FakeWalker:
    complete_leaf_set={0}
    def point(self,p):
        return {"candidate_triangle_ids":[0] if p[0]<=1 else []}


class CandidateCollisionTests(unittest.TestCase):
    def test_original_samples_and_translated_miss(self):
        old=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        self.assertEqual(len(triangle_samples(old)),7)
        self.assertEqual(triangle_samples(old)[-1],(1/3,1/3,0.))
        same=compare_triangle(FakeWalker(),0,old,old)
        self.assertEqual(same["collision_point_comparisons"],7)
        self.assertEqual(same["collision_candidate_sample_misses"],0)
        new=[(x+2,y,z) for x,y,z in old]
        moved=compare_triangle(FakeWalker(),0,old,new)
        self.assertEqual(moved["collision_new_sample_misses"],7)
        self.assertEqual(moved["collision_triangles_with_new_sample_misses"],1)

    def test_degeneracy_and_inversion(self):
        old=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        deg=compare_triangle(FakeWalker(),0,old,[old[0],old[1],old[0]])
        self.assertEqual(deg["collision_zero_area_candidate_triangles"],1)
        rev=compare_triangle(FakeWalker(),0,old,list(reversed(old)))
        self.assertEqual(rev["collision_reversed_candidate_triangles"],1)
        nonleaf=compare_triangle(FakeWalker(),1,old,old)
        self.assertEqual(nonleaf["collision_affected_nonleaf_triangles"],1)


if __name__=="__main__":
    unittest.main()
