"""Optional genuine retail map regression tests. No assets ship with the SDK.

Set DX2_TEST_MAPS to the Maps folder holding two original Penthouse GMPs,
mission IBDs and Kernel_GFXALL.ibd; otherwise test is skipped.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map_exporter'))
from dx2_map_exporter import resolve_map,run_export


@unittest.skipUnless(os.getenv('DX2_TEST_MAPS'),'set DX2_TEST_MAPS to original Penthouse Maps directory')
class RealGameIntegration(unittest.TestCase):
    def test_upper_and_lower_scene_counts_and_no_source_mutation(self):
        maps=Path(os.environ['DX2_TEST_MAPS'])
        for name,actors,triangles,images in (
                ('M1_Seattle_Hub_Penthouse_Upper.gmp',471,36365,88),
                ('M1_Seattle_Hub_Penthouse.gmp',1000,71800,113)):
            level=resolve_map(maps,name)
            before=hashlib.sha256(level.path.read_bytes()).hexdigest()
            with tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/(level.path.stem+'.glb')
                result=run_export(level,out)
                self.assertEqual(result['placed_real_mesh_actors'],actors)
                self.assertEqual(result['total_scene_triangles'],triangles)
                self.assertEqual(result['embedded_diffuse_images'],images)
                self.assertFalse(result['missing_mesh_actors'])
                self.assertTrue(out.is_file())
                self.assertEqual(json.loads(out.with_suffix('.report.json').read_text()),result)
            self.assertEqual(hashlib.sha256(level.path.read_bytes()).hexdigest(),before)

if __name__=='__main__':unittest.main()