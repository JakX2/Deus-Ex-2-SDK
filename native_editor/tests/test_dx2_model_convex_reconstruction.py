"""Synthetic, retail-asset-free tests for DX2 candidate convex hull reconstruction."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
import reconstruct_model_convex_candidates as recon


def face(normal, w, center, vertices, actual_count=None):
    radius = 1.001 * max(recon.length(recon.sub(p, center)) for p in vertices)
    return {
        "candidate_normal_xyz": list(normal), "candidate_plane_w": float(w),
        "candidate_point_on_plane": list(center), "candidate_face_radius": radius,
        "vertex_slot_count": len(vertices) if actual_count is None else actual_count,
    }


def box(half=(2.,3.,4.), shift=(0.,0.,0.), offcenter=0.):
    corners = [
        tuple(shift[i] + sign[i]*half[i] for i in range(3))
        for sign in ((x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1))
    ]
    result = []
    for axis in range(3):
        for sign in (-1,1):
            normal = [0.,0.,0.]
            normal[axis] = float(sign)
            side = shift[axis]+sign*half[axis]
            pts = [p for p in corners if abs(p[axis]-side)<1e-8]
            point = [sum(p[i] for p in pts)/4 for i in range(3)]
            point[(axis+1)%3] += offcenter
            result.append(face(normal, sign*side, point, pts))
    return result


class ConvexCandidateTests(unittest.TestCase):
    def test_box_watertight_faces_edges_and_corners(self):
        hull = recon.reconstruct_faces(box())
        self.assertEqual(hull["status"], "validated_candidate_convex_hull")
        self.assertEqual((hull["corner_count"], hull["edge_count"], hull["face_count"]), (8,12,6))
        self.assertEqual(hull["vertex_slots_checked"], 24)
        self.assertEqual(
            sorted(tuple(v) for v in hull["corner_xyz"]),
            sorted((x,y,z) for x in (-2.,2.) for y in (-3.,3.) for z in (-4.,4.)))
        self.assertFalse(hull["native_vertex_coordinates_decoded"])
        self.assertFalse(hull["native_bsp_or_collision_decoded"])
        for poly in hull["polygons_outward"]:
            self.assertEqual(len(poly["vertex_indices"]), 4)
            self.assertLess(poly["radius_absolute_error"], 1e-6)
        json.dumps(hull, allow_nan=False)

    def test_offset_model_and_source_point_not_face_centroid(self):
        hull = recon.reconstruct_faces(box(half=(16.,32.,7.), shift=(99.,-117.,35.),
                                          offcenter=4.))
        self.assertEqual(hull["status"], "validated_candidate_convex_hull")
        self.assertEqual(hull["corner_count"], 8)
        self.assertLess(hull["max_source_radius_error"], 1e-5)

    def test_chamfered_cube_triangle_and_pentagons(self):
        corners = [(x,y,z) for x in (-1.,1.) for y in (-1.,1.) for z in (-1.,1.)]
        corners = [p for p in corners if p != (1.,1.,1.)]
        corners.extend(((1.,1.,.5),(1.,.5,1.),(.5,1.,1.)))
        normals = [(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)]
        source_faces = []
        for normal in normals:
            points = [p for p in corners if abs(recon.dot(normal,p)-1) < 1e-6]
            center = [sum(p[i] for p in points)/len(points) for i in range(3)]
            source_faces.append(face(normal,1,center,points))
        unit = 1/math.sqrt(3)
        points = [p for p in corners if abs(sum(p)-2.5)<1e-6]
        source_faces.append(face((unit,unit,unit),2.5*unit,
                                 [sum(p[i] for p in points)/3 for i in range(3)],
                                 points))
        hull = recon.reconstruct_faces(source_faces)
        self.assertEqual(hull["status"], "validated_candidate_convex_hull")
        self.assertEqual((hull["corner_count"],hull["edge_count"],hull["face_count"]),
                         (10,15,7))
        self.assertEqual(sorted(p["source_vertex_slot_count"] for p in hull["polygons_outward"]),
                         [3,4,4,4,5,5,5])

    def test_source_vertex_count_and_face_radius_checks(self):
        faces = box()
        faces[0]["vertex_slot_count"] = 3
        self.assertEqual(recon.reconstruct_faces(faces)["status"], "source_vertex_count_mismatch")
        faces = box()
        faces[0]["candidate_face_radius"] += 30
        self.assertEqual(recon.reconstruct_faces(faces)["status"], "source_face_radius_mismatch")

    def test_missing_flipped_and_nonfinite_source_planes_rejected(self):
        self.assertNotEqual(recon.reconstruct_faces(box()[:-1])["status"],
                            "validated_candidate_convex_hull")
        faces = box()
        faces[0]["candidate_normal_xyz"] = [-x for x in faces[0]["candidate_normal_xyz"]]
        faces[0]["candidate_plane_w"] *= -1
        self.assertNotEqual(recon.reconstruct_faces(faces)["status"],
                            "validated_candidate_convex_hull")
        faces = box()
        faces[0]["candidate_normal_xyz"] = [float("nan"),0.,0.]
        self.assertEqual(recon.reconstruct_faces(faces)["status"],"unsupported_face_fields")

    def test_degenerate_plane_triplets_and_bad_types(self):
        a = ([1.,0.,0.],1.)
        b = ([1.,0.,0.],2.)
        c = ([0.,1.,0.],1.)
        self.assertIsNone(recon.triple_intersection(a,b,c))
        self.assertEqual(recon.reconstruct_faces([])["status"],"unsupported_plane_count")
        self.assertEqual(recon.reconstruct_faces(None)["status"],"unsupported_plane_count")
        faces = box()
        faces[0]["vertex_slot_count"] = True
        self.assertEqual(recon.reconstruct_faces(faces)["status"],"unsupported_face_fields")

    def test_obj_preview_triangulated_and_exclusive(self):
        hull = recon.reconstruct_faces(box())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/"game"/"Test.gmp"
            source.parent.mkdir()
            source.write_bytes(b"synthetic input must remain intact")
            output = root/"reports"/"preview.obj"
            recon.write_candidate_obj(hull, output, source, 7)
            text = output.read_text()
            self.assertEqual(len([row for row in text.splitlines() if row.startswith("v ")]),8)
            self.assertEqual(len([row for row in text.splitlines() if row.startswith("f ")]),12)
            self.assertIn("NOT native vertex data",text)
            with self.assertRaises(FileExistsError):
                recon.write_candidate_obj(hull,output,source,7)
            with self.assertRaisesRegex(ValueError,"outside the original game map"):
                recon.write_candidate_obj(hull,source.parent/"wrong.obj",source,7)
            self.assertEqual(source.read_bytes(),b"synthetic input must remain intact")

    def test_synthetic_package_integration_and_private_obj(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/"game"/"Test.gmp"
            source.parent.mkdir()
            source.write_bytes(b"fixture-only source")
            class FakePackage:
                def __init__(self,path):
                    self.data=Path(path).read_bytes()
                    self.version=95
                    self.licensee=68
                    self.exports=[{"index":1,"name":"Model__Test"}]
                def class_name(self,_record):
                    return "Model"
                def payload(self,_record):
                    return b"fake payload"
            with patch.object(recon.face_reader.header,"Package",side_effect=FakePackage), \
                 patch.object(recon.face_reader,"inspect_model_faces",
                              return_value={"status":"decoded_candidate_face_records",
                                            "faces":box()}):
                summary=recon.audit_maps([source])
                self.assertEqual(summary["totals"]["validated_candidate_convex_hull"],1)
                self.assertEqual(summary["totals"]["reconstructed_corners"],8)
                self.assertFalse(summary["native_model_vertices_decoded"])
                preview=root/"output"/"one.obj"
                report=recon.export_single_model(source,1,preview)
                self.assertEqual(report["candidate_vertices"],8)
                self.assertTrue(preview.is_file())
                with self.assertRaisesRegex(ValueError,"outside source package"):
                    recon.export_single_model(source,99,root/"output"/"bad.obj")
            self.assertEqual(source.read_bytes(),b"fixture-only source")

    def test_reject_duplicate_source_inputs(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            recon.audit_maps([Path("same.gmp"),Path("same.gmp")])


if __name__ == "__main__":
    unittest.main()
