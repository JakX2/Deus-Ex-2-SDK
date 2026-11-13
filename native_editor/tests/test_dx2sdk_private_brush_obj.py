"""Source-private OBJ export is deterministic, closed and never writes GMP/IBD."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dx2sdk.private_brush_obj import (
    SCHEMA, render_private_box_obj, export_private_box_obj,
)
from dx2sdk.private_brush_preflight import inspect_private_box_convex


def box(*cuts):
    spec = {"kind": "Box", "size": [2.0, 2.0, 2.0], "steps": 1}
    if len(cuts) == 1:
        spec["clip_plane"] = cuts[0]
    else:
        spec["clip_planes"] = list(cuts)
    return spec


def cut(normal, distance=0.0):
    return {"normal": list(normal), "distance": distance, "keep_positive": False}


def decode_obj(obj: bytes):
    source = obj.decode("ascii")
    vertices, normals, triangles, groups = [], [], [], []
    current_group = None
    for line in source.splitlines():
        parts = line.split()
        if not parts or line.startswith("#"):
            continue
        if parts[0] == "v":
            vertices.append(tuple(map(float, parts[1:])))
        elif parts[0] == "vn":
            normals.append(tuple(map(float, parts[1:])))
        elif parts[0] == "g":
            current_group = parts[1]
            groups.append(current_group)
        elif parts[0] == "f":
            indices = []
            normal_indices = []
            for word in parts[1:]:
                a, b = word.split("//")
                indices.append(int(a)-1)
                normal_indices.append(int(b)-1)
            if len(indices) != 3 or len(set(normal_indices)) != 1:
                raise AssertionError("Private OBJ not uniformly triangulated")
            triangles.append((tuple(indices), normal_indices[0], current_group))
        elif parts[0] not in ("o", "s"):
            raise AssertionError(f"Untrusted OBJ token: {parts[0]}")
    return vertices, normals, triangles, groups


def verify_closed_winding(test, vertices, normals, triangles):
    ledger = defaultdict(list)
    volume = 0.0
    for (a, b, c), normal_index, group in triangles:
        test.assertTrue(group.startswith("private_box_side_")
                        or group.startswith("private_cut_cap_"))
        test.assertTrue(all(0 <= i < len(vertices) for i in (a, b, c)))
        test.assertTrue(0 <= normal_index < len(normals))
        x, y, z = (vertices[i] for i in (a, b, c))
        ab = [y[i]-x[i] for i in range(3)]
        ac = [z[i]-x[i] for i in range(3)]
        cross = (ab[1]*ac[2]-ab[2]*ac[1],
                 ab[2]*ac[0]-ab[0]*ac[2],
                 ab[0]*ac[1]-ab[1]*ac[0])
        test.assertGreater(sum(cross[i]*normals[normal_index][i]
                               for i in range(3)), 1e-8)
        volume += sum(x[i] * (
            (y[(i+1)%3]*z[(i+2)%3])
            -(y[(i+2)%3]*z[(i+1)%3]))
            for i in range(3))/6.0
        for start, end in ((a,b), (b,c), (c,a)):
            ledger[tuple(sorted((start, end)))].append((start, end))
    for edge_occurrences in ledger.values():
        test.assertEqual(len(edge_occurrences), 2)
        test.assertEqual(edge_occurrences[0],
                         tuple(reversed(edge_occurrences[1])))
    return volume


class PrivateOBJTests(unittest.TestCase):
    def test_private_half_cube_obj_is_deterministic_manifold_and_non_native(self):
        spec = box(cut((1., 0., 0.)))
        original = deepcopy(spec)
        data, report = render_private_box_obj(spec)
        same, again = render_private_box_obj(spec)
        self.assertEqual(spec, original)
        self.assertEqual(data, same)
        self.assertEqual(report, again)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["vertex_count"], 8)
        self.assertEqual(report["face_count"], 6)
        self.assertEqual(report["cut_cap_count"], 1)
        self.assertEqual(report["triangle_count"], 12)
        self.assertEqual(report["obj_sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse(report["native_world_model_writer_enabled"])
        self.assertFalse(report["bsp_surface_indices_included"])
        self.assertFalse(report["original_materials_included"])
        self.assertFalse(report["native_collision_generated"])
        self.assertFalse(report["original_game_files_modified"])
        self.assertNotIn(b"source_gmp", data)
        self.assertNotIn(b"usemtl", data)
        vertices, normals, triangles, groups = decode_obj(data)
        self.assertEqual((len(vertices), len(normals), len(triangles),
                          len(groups)), (8, 6, 12, 6))
        self.assertAlmostEqual(
            verify_closed_winding(self, vertices, normals, triangles),
            4.0, places=7)

    def test_eight_corner_cut_obj_exact_geometry_and_orientation(self):
        u = 1/math.sqrt(3)
        corners = [cut((x*u,y*u,z*u), 1.4)
                   for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        spec = box(*corners)
        obj, r = render_private_box_obj(spec)
        vertices, normals, triangles, groups = decode_obj(obj)
        self.assertEqual((r["face_count"], r["vertex_count"], r["triangle_count"]),
                         (14, 24, 44))
        self.assertEqual((len(vertices), len(normals), len(triangles), len(groups)),
                         (24, 14, 44, 14))
        self.assertEqual(sum(g.startswith("private_cut_cap_") for g in groups), 8)
        analytic = 8 - 8*(3-math.sqrt(3)*1.4)**3/6
        self.assertAlmostEqual(
            verify_closed_winding(self, vertices, normals, triangles),
            analytic, places=6)
        self.assertEqual(r["private_geometry_sha256"],
            inspect_private_box_convex(spec)[
                "private_geometry_sha256_quantized_1e-6m"])

    def test_reversed_cut_order_still_same_volume_but_different_cap_groups(self):
        u = 1/math.sqrt(3)
        planes = [cut((x*u,y*u,z*u),1.4)
                  for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        first_obj, first = render_private_box_obj(box(*planes))
        second_obj, second = render_private_box_obj(box(*reversed(planes)))
        self.assertEqual(first["private_geometry_sha256"],
                         second["private_geometry_sha256"])
        self.assertNotEqual(first["source_private_spec_sha256"],
                            second["source_private_spec_sha256"])
        self.assertNotEqual(first_obj, second_obj)
        self.assertEqual(first["triangle_count"], second["triangle_count"])

    def test_refuse_malformed_non_private_and_ninth_planes(self):
        valid = box(cut((1.,0.,0.)))
        for invalid in (
            None, {}, {"kind":"StaticMeshActor", "mesh":"Original.gmp"},
            box(*[cut((1.,0.,0.)) for _ in range(9)]),
            box(cut((0.,0.,0.))), box(cut((1.,0.,0.),1.0)),
        ):
            with self.subTest(input=invalid), self.assertRaises(ValueError):
                render_private_box_obj(invalid)
        with self.assertRaises(ValueError):
            render_private_box_obj(valid, copy_name="DraftProp_1")

    def test_safe_new_obj_and_readonly_draft_cli(self):
        spec = box(cut((1.,0.,0.)), cut((0.,1.,0.)))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root/"GAME.gmp"
            original.write_bytes(b"DO_NOT_MUTATE_DX2_ORIGINAL")
            payload_before = original.read_bytes()
            private = root/"private_box.json"
            private.write_text(json.dumps(spec), encoding="utf-8")
            out = root/"new_preview.obj"
            report = export_private_box_obj(spec, out, input_path=private)
            self.assertEqual(report["status"], "new-source-private-OBJ-written")
            self.assertEqual(out.stat().st_size, report["obj_bytes"])
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(),
                             report["obj_sha256"])
            self.assertEqual(original.read_bytes(), payload_before)
            with self.assertRaises((OSError, ValueError)):
                export_private_box_obj(spec, out, input_path=private)
            with self.assertRaises(ValueError):
                export_private_box_obj(spec, original, input_path=private)
            draft = root/"project.json"
            draft.write_text(json.dumps({
                "schema":"DX2Ed-prop-draft-v1", "read_only_source": True,
                "copies":[{"name":"DraftProp_7", "from_actor":"Brush::Box",
                           "brush": spec}],
            }), encoding="utf-8")
            run = [sys.executable, "-m", "dx2sdk.private_brush_obj"]
            no_copy = subprocess.run(run+[str(draft),str(root/"none.obj")],
                                     capture_output=True, text=True)
            self.assertEqual(no_copy.returncode, 2)
            self.assertFalse((root/"none.obj").exists())
            exported = root/"from_saved_draft.obj"
            run_draft = subprocess.run(
                run + [str(draft), str(exported), "--copy", "DraftProp_7"],
                capture_output=True, text=True)
            self.assertEqual(run_draft.returncode, 0, run_draft.stderr)
            self.assertEqual(json.loads(run_draft.stdout)["triangle_count"], 12)
            self.assertTrue(exported.is_file())
            original_input = subprocess.run(
                run + [str(original), str(root/"bad.obj")],
                capture_output=True, text=True)
            self.assertEqual(original_input.returncode, 2)
            self.assertFalse((root/"bad.obj").exists())
            self.assertEqual(original.read_bytes(), payload_before)
            self.assertEqual(sorted(x.name for x in root.iterdir()), [
                "GAME.gmp", "from_saved_draft.obj", "new_preview.obj",
                "private_box.json", "project.json",
            ])

    def test_no_overwrite_symlink_or_empty_output(self):
        spec = box(cut((1.,0.,0.)))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root/"existing.obj"
            target.write_bytes(b"ORIGINAL_OBJ_SENTINEL")
            with self.assertRaises(ValueError):
                export_private_box_obj(spec, target)
            self.assertEqual(target.read_bytes(), b"ORIGINAL_OBJ_SENTINEL")
            link = root/"alias.obj"
            try:
                link.symlink_to(target)
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    export_private_box_obj(spec, link)
            for wrong in (root/"not_game.gmp", root/"bad.ibd", root/"file.json"):
                with self.assertRaises(ValueError):
                    export_private_box_obj(spec, wrong)
                self.assertFalse(wrong.exists())


if __name__ == "__main__":
    unittest.main()
