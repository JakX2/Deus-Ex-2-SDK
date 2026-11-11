import unittest
from copy import deepcopy
from dx2sdk.bsp_plane_impact import compare_plane_model

def model():
    return {"nodes": [
        {"plane": (1., 0., 0., 0.), "negative": 1, "positive": -1,
         "coplanar": -1, "zone_a": 0, "zone_b": 1, "subtree_zone_mask": 3},
        {"plane": (0., 1., 0., 0.), "negative": -1, "positive": -1,
         "coplanar": -1, "zone_a": 0, "zone_b": 1, "subtree_zone_mask": 3},
    ], "zone_count": 2}

def lights():
    return [
        {"export": 2, "location_unreal": (-1., -1., 0.),
         "region_leaf": 3, "region_zone_number_low": 0},
        {"export": 3, "location_unreal": (1., 1., 0.),
         "region_leaf": 5, "region_zone_number_low": 1},
    ]

class PlaneImpactTests(unittest.TestCase):
    def test_counterfactual_is_in_memory_and_deterministic(self):
        original = model()
        snapshot = deepcopy(original)
        source_lights = lights()
        rows = deepcopy(source_lights)
        result = compare_plane_model(original, source_lights, node=0,
                                     replacement=(1, 0, 0, -2))
        self.assertEqual(result, compare_plane_model(original, source_lights,
                          node=0, replacement=(1, 0, 0, -2)))
        self.assertEqual(result["changed_candidate_light_paths"], 1)
        self.assertEqual(result["sampled_original_lights"], 2)
        self.assertFalse(result["native_bsp_writer_enabled"])
        self.assertFalse(result["gameplay_runtime_verified"])
        self.assertEqual(original, snapshot)
        self.assertEqual(source_lights, rows)
        self.assertEqual(result["original_light_paths"][0]["original_region_leaf"], 3)

    def test_rejects_invalid_or_unchanged_planes_and_actors(self):
        for candidate in [(1,0,0,0), (2,0,0,0), (float("nan"),0,0,0),
                          (0,0,0,0), (1,0,0,1000001)]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                compare_plane_model(model(), lights(), node=0, replacement=candidate)
        with self.assertRaises(ValueError):
            compare_plane_model(model(), lights(), node=True, replacement=(1,0,0,-2))
        with self.assertRaises(ValueError):
            compare_plane_model(model(), lights()*2, node=0, replacement=(1,0,0,-2))
        with self.assertRaises(ValueError):
            compare_plane_model(model(), lights(), node=0, replacement=(1,0,0,-2), epsilon=2)
        with self.assertRaises(ValueError):
            compare_plane_model(model(), lights(), node=0, replacement=(1,0,0,-2), limit=0)

if __name__ == "__main__":
    unittest.main()
