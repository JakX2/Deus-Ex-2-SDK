"""No game assets required for discovery and error-path tests."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map_exporter'))
from dx2_map_exporter import locate_maps_dir,list_levels,resolve_map,choose_bundles,_bundle_confidence


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.maps=self.root/'Content'/'DX2'/'Maps'
        self.maps.mkdir(parents=True)
        for name in ('M1_Seattle_Hub_Penthouse.gmp','M1_Seattle_Hub_Penthouse_Upper.gmp',
                     'm1_hub_penthouse.ibd','m1_hub_penthouse_upper.ibd','Kernel_GFXALL.ibd'):
            (self.maps/name).write_bytes(b'placeholder')

    def test_game_root_variants(self):
        for source in (self.root,self.root/'Content'/'DX2',self.maps,
                       self.maps/'M1_Seattle_Hub_Penthouse.gmp'):
            self.assertEqual(locate_maps_dir(source),self.maps)

    def test_two_maps_have_distinct_mission_bundles(self):
        rows=list_levels(self.root)
        self.assertEqual(len(rows),2)
        matches={r.path.name:r.mission_bundle.name for r in rows}
        self.assertEqual(matches['M1_Seattle_Hub_Penthouse.gmp'],'m1_hub_penthouse.ibd')
        self.assertEqual(matches['M1_Seattle_Hub_Penthouse_Upper.gmp'],'m1_hub_penthouse_upper.ibd')
        self.assertTrue(all(r.confidence >= .90 for r in rows))
        self.assertEqual(len(choose_bundles(rows[0],[])),2)

    def test_unrecognized_mission_is_not_silently_guessed(self):
        (self.maps/'M2_Cairo_Airport.gmp').write_bytes(b'placeholder')
        row=resolve_map(self.root,'M2_Cairo_Airport')
        self.assertIsNone(row.mission_bundle)

    def test_manual_bundle_override(self):
        row=resolve_map(self.root,'M1_Seattle_Hub_Penthouse')
        manual=self.maps/'m1_hub_penthouse_upper.ibd'
        bundles=choose_bundles(row,[manual])
        self.assertEqual(bundles[0],manual)
        self.assertIn(self.maps/'Kernel_GFXALL.ibd',bundles)

    def test_maps_without_valid_root_fail(self):
        with self.assertRaises(FileNotFoundError):list_levels(self.root/'missing')

if __name__=='__main__':unittest.main()