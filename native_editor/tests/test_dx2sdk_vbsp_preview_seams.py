"""Synthetic exact-position seam and original triangle provenance gates."""
import unittest
from inspect_vbsp_preview_seams import (
    source_seam_inventory,inspect_preview_seams,attach_original_triangle_provenance,
)


class PreviewSeamTests(unittest.TestCase):
    def setUp(self):
        self.polys=[
            {"polygon":0,"vertices":[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]},
            {"polygon":1,"vertices":[(0.,0.,0.),(0.,1.,0.),(0.,0.,1.)]},
        ]
        self.owners=[0,1]
        self.counts,self.points=source_seam_inventory(self.polys,self.owners)

    def face(self,i,shift=0.,omit=()):
        return {"source_polygon":i,"owner_leaf":i,"vertices":[
            {"source_corner":j,"xyz":(v[0]+shift,v[1],v[2])}
            for j,v in enumerate(self.polys[i]["vertices"]) if j not in omit]}

    def test_source_inventory_and_separation(self):
        self.assertEqual(self.counts["source_seam_xyz_groups"],4)
        self.assertEqual(self.counts["source_seam_cross_leaf_xyz_groups"],2)
        self.assertEqual(self.counts["source_seam_cross_leaf_edge_groups"],1)
        counts,issues=inspect_preview_seams(self.polys,self.owners,self.points,
            [self.face(0,1.)],{0:"preview_passed"})
        self.assertEqual(counts["preview_shared_xyz_groups_separated"],2)
        self.assertEqual(len(issues),2)
        counts,_=inspect_preview_seams(self.polys,self.owners,self.points,
            [self.face(0,1.),self.face(1,1.)],{0:"preview_passed",1:"preview_passed"})
        self.assertEqual(counts["preview_shared_xyz_groups_agree"],2)

    def test_removed_and_unresolved_are_not_agreement(self):
        counts,_=inspect_preview_seams(self.polys,self.owners,self.points,
            [self.face(0,omit=(0,))],{0:"preview_passed",1:"source_gate_refused"})
        self.assertEqual(counts["preview_shared_xyz_groups_unresolved"],2)
        self.assertEqual(counts.get("preview_shared_xyz_groups_agree",0),0)
        counts,_=inspect_preview_seams(self.polys,self.owners,self.points,
            [self.face(0,omit=(0,))],{0:"preview_passed"})
        self.assertEqual(counts["preview_shared_xyz_groups_removed_with_survivors"],1)
        with self.assertRaises(ValueError):
            inspect_preview_seams(self.polys,self.owners,self.points,[],{0:"preview_passed"})

    def test_original_triangle_provenance(self):
        preview={"faces":[self.face(0)],"face_states":[{"source_polygon":0,"state":"preview_passed"},
                                                     {"source_polygon":1,"state":"source_gate_refused"}]}
        links=[{"polygon":i,"triangle_locators":[(i,0,0)],"packed_block":i,
                "packed_vertex_start":0} for i in range(2)]
        rows=[{"render_locator":(i,0,0),"flattened_triangle_id":i,
               "original_mopp_terminal_leaf_present":i==0} for i in range(2)]
        counts=attach_original_triangle_provenance(preview,links,rows)
        self.assertEqual(counts["affected_original_render_triangles"],2)
        self.assertEqual(counts["affected_original_mopp_leaves"],1)
        self.assertEqual(preview["faces"][0]["original_mopp_leaf_ids"],[0])
        self.assertEqual(preview["face_states"][1]["original_mopp_leaf_ids"],[])


if __name__=="__main__":
    unittest.main()
