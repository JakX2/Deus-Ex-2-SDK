import copy
import unittest
from unittest.mock import patch

from dx2sdk.bsp_plane_preflight import _join, preflight_original_bsp_plane


def evidence():
    plane = {
        "source_package_sha256": "a"*64,
        "source_model_sha256": "b"*64,
        "original_world_model_export": 9,
        "original_node_ordinal": 2,
        "original_plane_float32": [1., 0., 0., 0.],
        "hypothetical_plane_float32": [1., 0., 0., 2.],
        "original_bytes_unchanged": True,
        "native_writer_enabled": False,
        "original_plane_absolute_offset": 512,
        "original_plane_sha256": "c"*64,
        "hypothetical_plane_sha256": "d"*64,
        "changed_byte_offsets_relative_to_plane": [14, 15],
    }
    impact = {
        "source_sha256": "a"*64,
        "world_model_sha256": "b"*64,
        "world_model_export": 9,
        "node": 2,
        "original_plane_float32": [1., 0., 0., 0.],
        "hypothetical_plane_float32": [1., 0., 0., 2.],
        "native_bsp_writer_enabled": False,
        "original_gmp_modified": False,
        "sampled_original_lights": 1,
        "changed_candidate_light_paths": 1,
        "original_light_paths": [{"source_light_export": 3, "candidate_path_changed": True}],
    }
    return plane, impact


class PlanePreflightTests(unittest.TestCase):
    def test_exact_original_source_join_and_disabled_writer(self):
        plane, impact = evidence()
        original = copy.deepcopy((plane, impact))
        report = _join(plane, impact)
        self.assertEqual(report["absolute_plane_byte_offset"], 512)
        self.assertEqual(report["changed_candidate_light_paths"], 1)
        self.assertFalse(report["native_write_authorized"])
        self.assertFalse(report["retail_runtime_verified"])
        self.assertEqual((plane, impact), original)
        self.assertEqual(report, _join(plane, impact))

    def test_reject_independent_source_disagreements(self):
        for field, value in [
            ("source_package_sha256", "0"*64),
            ("source_model_sha256", "0"*64),
            ("original_world_model_export", 8),
            ("original_node_ordinal", 3),
            ("original_plane_float32", [0., 1., 0., 0.]),
            ("hypothetical_plane_float32", [1., 0., 0., 3.]),
            ("native_writer_enabled", True),
            ("original_bytes_unchanged", False),
        ]:
            with self.subTest(field=field):
                plane, impact = evidence()
                plane[field] = value
                with self.assertRaises(ValueError):
                    _join(plane, impact)
        for field, value in [
            ("native_bsp_writer_enabled", True),
            ("original_gmp_modified", True),
            ("world_model_export", 10),
            ("node", 3),
        ]:
            with self.subTest(field=field):
                plane, impact = evidence()
                impact[field] = value
                with self.assertRaises(ValueError):
                    _join(plane, impact)

    def test_source_checked_before_and_after_independent_audits(self):
        class Source:
            calls = 0
            def _check_original_unchanged(self):
                self.calls += 1
        world = Source()
        plane, impact = evidence()
        with patch("dx2sdk.bsp_plane_preflight.inspect_original_plane_bytes", return_value=plane) as bytes_check, patch(
            "dx2sdk.bsp_plane_preflight.compare_original_plane_impact", return_value=impact
        ) as impact_check:
            report = preflight_original_bsp_plane(world, node=2, replacement=(1,0,0,2))
        self.assertEqual(world.calls, 2)
        self.assertEqual(report["world_model_export"], 9)
        bytes_check.assert_called_once()
        impact_check.assert_called_once()

if __name__ == "__main__":
    unittest.main()
