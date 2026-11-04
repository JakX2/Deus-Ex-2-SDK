"""Asset-free DX2Ed capsule preview sidecar origin, hash and ID checks."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research'/'dx2'))
import export_capsule_first_contact_preview as preview
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_axis_point_candidates as mopp


SHA='b'*64


def synthetic():
    verts=[(0.,0.,0.),(2.,0.,0.),(0.,2.,0.)]
    faces=[(0,1,2,True)]
    oracle=geometry.LevelPointTriangleOracle(verts,faces)
    walker=mopp.ConservativeMoppPointCandidates(
        b'\x28\x00\xff\x30',1,(0.,0.,-10.,65536.))
    return oracle,walker


def document(*,start=(.5,.5,2.),end=(.5,.5,-2.),radius=.25,
             axis_half_length=0.,**options):
    oracle,walker=synthetic()
    return preview.build_document(
        oracle,walker,map_name='Fixture.gmp',source_hash=SHA,
        start=start,end=end,radius=radius,
        axis=(0.,0.,1.),axis_half_length=axis_half_length,**options)


class CapsulePreviewSidecarTests(unittest.TestCase):
    def test_sphere_first_entry_coordinate_transform_and_timing(self):
        doc=document()
        self.assertEqual(doc['schema'],preview.SCHEMA)
        self.assertTrue(doc['read_only'])
        self.assertFalse(doc['havok_runtime_contact_verified'])
        self.assertFalse(doc['not_a_native_collision_writer'] is False)
        self.assertFalse(doc['time_of_impact_exact_havok'])
        self.assertEqual(doc['capsule_start_godot_xyz'],[.05,.2,.05])
        self.assertEqual(doc['capsule_end_godot_xyz'],[.05,-.2,.05])
        self.assertEqual(doc['capsule_axis_unit_godot_xyz'],[0.,1.,0.])
        self.assertAlmostEqual(doc['capsule_radius_godot_units'],.025)
        hit=doc['first_hit']
        self.assertEqual(hit['original_level_triangle_id'],0)
        self.assertAlmostEqual(hit['t_first_inside'],.4375,places=5)
        self.assertAlmostEqual(hit['contact_normal_godot_xyz'][1],1.,places=5)
        self.assertTrue(hit['contact_normal_resolved'])
        self.assertTrue(hit['original_mopp_candidate_included'])
        self.assertIsNotNone(hit['t_last_outside'])
        self.assertLessEqual(hit['t_first_inside']-hit['t_last_outside'],1e-8+1e-12)

    def test_no_contact_is_explicit_and_does_not_invent_triangle_id(self):
        doc=document(start=(4.,4.,2.),end=(4.,4.,-2.))
        self.assertIsNone(doc['first_hit'])
        self.assertEqual(doc['geometric_source_triangle_hits'],0)

    def test_geometry_and_MOPP_are_checked_independently(self):
        verts=[(0,0,0),(2,0,0),(0,2,0),
               (0,0,0),(2,0,0),(0,2,0)]
        geom=geometry.LevelPointTriangleOracle(
            verts,[(0,1,2,True),(3,4,5,True)])
        wrong=mopp.ConservativeMoppPointCandidates(
            b'\x28\x00\xff\x20\x80\x01\x30\x31',2,
            (0.,0.,-10.,65536.))
        with self.assertRaisesRegex(ValueError,'MOPP.*omit'):
            preview.build_document(
                geom,wrong,map_name='Fixture.gmp',source_hash=SHA,
                start=(.3,.3,1.),end=(.3,.3,-1.),
                radius=.2,axis=(0,0,1),axis_half_length=0.)

    def test_invalid_source_identity_rejected(self):
        geom,walker=synthetic()
        for name,hash_ in [('../Fixture.gmp',SHA),
                           ('other.txt',SHA),
                           ('Fixture.gmp','x'*64)]:
            with self.subTest(name=name),self.assertRaises(ValueError):
                preview.build_document(
                    geom,walker,map_name=name,source_hash=hash_,
                    start=(.3,.3,1),end=(.3,.3,-1),
                    radius=.2,axis=(0,0,1),axis_half_length=0.)

    def test_stationary_and_invalid_shape_rejected(self):
        for opts in ({'start':(.5,.5,1),'end':(.5,.5,1)},
                     {'radius':-1},{'axis_half_length':-1},
                     {'start':(float('nan'),0,0)},
                     {'radius':float('inf')}):
            with self.subTest(opts=opts),self.assertRaises(ValueError):
                document(**opts)

    def test_document_json_safe_and_uses_no_original_raw_bytes(self):
        doc=document()
        rendered=json.dumps(doc,allow_nan=False)
        self.assertNotIn('mopp_code_bytes',rendered)
        self.assertNotIn('source_level_vertices',rendered)
        self.assertEqual(json.loads(rendered)['source_sha256'],SHA)

    def test_source_gmp_must_have_expected_hash_before_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'Maps'/'Fixture.gmp'
            src.parent.mkdir()
            src.write_bytes(b'not an original DX2 map')
            out=Path(tmp)/'PrivatePreview'/'contact.json'
            with self.assertRaisesRegex(ValueError,'SHA-256'):
                preview.build(
                    src,out,expected_sha256=SHA,
                    start=(0,0,1),end=(0,0,-1),
                    radius=.2,axis=(0,0,1),axis_half_length=.5)
            self.assertFalse(out.exists())

    def test_refuse_saving_inside_original_maps_and_existing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'Maps'/'Fixture.gmp'
            src.parent.mkdir()
            src.write_bytes(b'fake GMP')
            for dest in (src.parent/'contact.json',src.parent/'Subdir'/'contact.json'):
                with self.subTest(dest=dest),self.assertRaises(ValueError):
                    preview.build(src,dest,expected_sha256=SHA,
                        start=(0,0,1),end=(0,0,-1),
                        radius=.2,axis=(0,0,1),axis_half_length=.5)
                self.assertFalse(dest.exists())
            old=Path(tmp)/'existing.json'
            old.write_text('DO NOT OVERWRITE')
            with self.assertRaises(ValueError):
                preview.build(src,old,expected_sha256=SHA,
                    start=(0,0,1),end=(0,0,-1),
                    radius=.2,axis=(0,0,1),axis_half_length=.5)
            self.assertEqual(old.read_text(),'DO NOT OVERWRITE')

    def test_nonzero_capsule_half_axis_and_unresolved_normals(self):
        doc=document(start=(.5,.5,.15),end=(.5,.5,.7),
                     radius=.3,axis_half_length=0.)
        h=doc['first_hit']
        self.assertTrue(h['initial_overlap'])
        self.assertIsNone(h['t_last_outside'])
        self.assertEqual(h['t_first_inside'],0.)

    def test_level_to_godot_preview_is_explicit_axis_swap_and_scale(self):
        self.assertEqual(preview.preview_point((40.,50.,60.)),[4.,6.,5.])
        self.assertEqual(preview.preview_unit((0.,0.,1.)),[0.,1.,0.])


if __name__=='__main__':
    unittest.main()
