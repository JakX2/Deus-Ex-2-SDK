import unittest
from inspect_model_ancestor_constraints import ancestor_regressions,classify_plane_aliases,unique_owners


def node(x):return ((1.,0.,0.,x),(x,0.,0.,1.),3)

class ModelAncestorTests(unittest.TestCase):
    def test_descendant_not_just_direct_child(self):
        edges=[{'parent':0,'child':1,'compact_field':4},{'parent':1,'child':2,'compact_field':3}]
        old=[node(0.),node(3.),node(1.)]; new=[node(2.),node(3.),node(1.)]
        poly=[{'polygon':0,'vertices':[(1.,0.,0.),(1.,1.,0.),(1.,0.,1.)]}]
        c=ancestor_regressions(edges,old,new,poly,poly,[[2]])
        self.assertEqual(c['model_new_ancestor_center_violations'],1)
        self.assertEqual(c['model_new_ancestor_polygon_violations'],1)
    def test_stationary_alias_is_not_unresolved(self):
        a=[{'polygon':0,'vertices':[(0.,0.,0.)]},{'polygon':1,'vertices':[(0.,1.,0.)]}]
        b=[{'polygon':0,'vertices':[(1.,0.,0.)]},a[1]]
        self.assertEqual(classify_plane_aliases({1,2},{0},[[0],[1]],a,b,[node(0.)]*3,[node(1.),node(0.),node(0.)]),({1},{2}))
        self.assertEqual(unique_owners([[0],[0],[1,2]]),{})
    def test_missing_or_cyclic_graph_refused(self):
        with self.assertRaises(ValueError):ancestor_regressions([], [node(0.)]*2,[node(0.)]*2,[],[],[])
        edges=[{'parent':2,'child':1,'compact_field':4},{'parent':1,'child':2,'compact_field':4}]
        with self.assertRaises(ValueError):ancestor_regressions(edges,[node(0.)]*3,[node(0.)]*3,[],[],[])

if __name__=='__main__':unittest.main()
