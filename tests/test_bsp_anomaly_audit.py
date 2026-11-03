"""Asset-free regression checks for read-only BSP source geometry auditing."""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"map_exporter"))
from dx2_bsp_anomaly_audit import bounds, triangle_properties, block_report, audit


def block(points, sections, block_id=77, off=0x1234):
    return {
        "id":block_id,
        "offset":off,
        "vertices":[(tuple(p),(0,0,1),(0,0)) for p in points],
        "sections":sections
    }


class BspSourceAuditTests(unittest.TestCase):
    def test_vertical_two_triangle_floor_material_is_reported_not_silently_removed(self):
        raw=block([(10,0,0),(10,0,100),(10,60,100),(10,60,0)],
                  [{"material":"M1WTO_hangerfloor1","indices":[0,1,2,0,2,3]}])
        original=repr(raw)
        report=block_report(raw,218)
        self.assertEqual(report["block_index"],218)
        self.assertEqual(report["source_block_id"],77)
        self.assertEqual(report["total_triangles"],2)
        self.assertEqual(report["sections"][0]["near_planar_axis_godot"],"X")
        self.assertEqual(report["sections"][0]["degenerate_triangles"],0)
        self.assertFalse(report["sections"][0]["hidden_by_current_exporter"])
        self.assertEqual(report["sections"][0]["material"],"M1WTO_hangerfloor1")
        self.assertEqual(original,repr(raw))

    def test_special_bf_material_visibility_note_and_invalid_triangle(self):
        raw=block([(0,0,0),(10,0,0),(0,10,0)],
                  [{"material":"bf","indices":[0,0,0]}])
        report=block_report(raw,0)
        self.assertTrue(report["sections"][0]["hidden_by_current_exporter"])
        self.assertEqual(report["sections"][0]["degenerate_triangles"],1)
        self.assertEqual(report["sections"][0]["total_triangle_area_source_units2"],0.0)

    def test_audit_indexes_original_sorted_blocks_and_nearest_neighbor(self):
        a=block([(0,0,0),(1,0,0),(0,1,0)],
                [{"material":"floor","indices":[0,1,2]}],off=0x20)
        b=block([(0,0,1),(1,0,1),(0,1,1)],
                [{"material":"wall","indices":[0,1,2]}],off=0x40)
        with patch("dx2_bsp_anomaly_audit.find_bsp",return_value=[a,b]):
            result=audit(object(),0)
            self.assertEqual(result["validated_source_block_count"],2)
            self.assertEqual(result["nearest_aabb_blocks"][0]["index"],1)
            with self.assertRaisesRegex(ValueError,"invalid"):
                audit(object(),218)

    def test_cross_product_area(self):
        area, normal=triangle_properties([0,0,0],[2,0,0],[0,3,0])
        self.assertAlmostEqual(area,3.0)
        self.assertEqual(normal,[0.0,0.0,1.0])


if __name__=="__main__":
    unittest.main()
