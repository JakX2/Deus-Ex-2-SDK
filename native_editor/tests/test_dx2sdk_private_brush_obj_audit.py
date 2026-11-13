"""Asset-free regression for source-private OBJ round-trip audit."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dx2sdk.private_brush_obj import render_private_box_obj
from dx2sdk.private_brush_obj_audit import (
    SCHEMA, audit_private_box_obj, audit_private_box_obj_file,
)


def cut(normal, distance=0.0):
    return {"normal": list(normal), "distance": distance,
            "keep_positive": False}


def box(*cuts):
    spec = {"kind": "Box", "size": [2., 2., 2.], "steps": 1}
    if len(cuts) == 1:
        spec["clip_plane"] = cuts[0]
    else:
        spec["clip_planes"] = list(cuts)
    return spec


class PrivateOBJAuditTests(unittest.TestCase):
    def test_exact_half_cube_and_eight_corner_roundtrip(self):
        u = 1 / math.sqrt(3)
        corners = [cut((x*u, y*u, z*u), 1.4)
                   for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        for spec, counts in ((box(cut((1., 0., 0.))), (8, 6, 12)),
                             (box(*corners), (24, 14, 44))):
            original = deepcopy(spec)
            data, export = render_private_box_obj(spec)
            result = audit_private_box_obj(spec, data)
            self.assertEqual(spec, original)
            self.assertEqual(result["schema"], SCHEMA)
            self.assertTrue(result["exact_export_match"])
            self.assertEqual(tuple(result[field] for field in
                                   ("vertex_count", "face_count", "triangle_count")),
                             counts)
            self.assertEqual(result["obj_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(result["private_geometry_sha256"],
                             export["private_geometry_sha256"])
            self.assertFalse(result["native_world_model_writer_enabled"])
            self.assertFalse(result["original_game_files_modified"])

    def test_tampering_wrong_cut_and_unsupported_obj_are_refused(self):
        spec = box(cut((1., 0., 0.)))
        data, _ = render_private_box_obj(spec)
        invalid = (
            data.replace(b"v ", b"v 0.01 ", 1),
            data.replace(b"f 1//", b"f 1/", 1),
            data.replace(b"s off", b"s 1", 1),
            data.replace(b"o DX2Ed_Private_Box", b"o OriginalDX2Mesh", 1),
            data + b"usemtl game_material\n",
            data + b"g private_cut_cap_00\n",
            data.replace(b"vn 1 ", b"vn nan ", 1),
            data[:40],
            data + b"#" + b"x" * (128 * 1024),
        )
        for edited in invalid:
            with self.subTest(edited=edited[:60]):
                with self.assertRaises(ValueError):
                    audit_private_box_obj(spec, edited)
        with self.assertRaises(ValueError):
            audit_private_box_obj(box(cut((0., 1., 0.))), data)
        with self.assertRaises(ValueError):
            audit_private_box_obj({"kind": "StaticMeshActor"}, data)

    def test_readonly_cli_draft_and_original_sentinel(self):
        spec = box(cut((1., 0., 0.)), cut((0., 1., 0.)))
        data, _ = render_private_box_obj(spec)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            private_json = root / "private.json"
            private_obj = root / "private.obj"
            sentinel = root / "original.gmp"
            sentinel.write_bytes(b"DX2_ORIGINAL_STAYS_UNTOUCHED")
            original_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            private_json.write_text(json.dumps(spec), encoding="utf-8")
            private_obj.write_bytes(data)
            before = private_obj.read_bytes()
            report = audit_private_box_obj_file(private_json, private_obj)
            self.assertTrue(report["exact_export_match"])
            command = [sys.executable, "-m", "dx2sdk.private_brush_obj_audit",
                       str(private_json), str(private_obj)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)["exact_export_match"])
            draft = root / "draft.json"
            draft.write_text(json.dumps({
                "schema": "DX2Ed-prop-draft-v1", "read_only_source": True,
                "copies": [{"name": "DraftProp_7", "from_actor": "Brush::Box",
                            "brush": spec}],
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_private_box_obj_file(draft, private_obj)
            report = audit_private_box_obj_file(
                draft, private_obj, copy_name="DraftProp_7")
            self.assertTrue(report["exact_export_match"])
            rejected = subprocess.run(
                command[:3] + [str(draft), str(private_obj)],
                capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2)
            self.assertFalse(rejected.stdout.strip())
            for forbidden in ((sentinel, private_obj),
                              (private_json, sentinel)):
                with self.assertRaises(ValueError):
                    audit_private_box_obj_file(*forbidden)
            alias = root / "alias.obj"
            try:
                alias.symlink_to(private_obj)
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    audit_private_box_obj_file(private_json, alias)
            self.assertEqual(before, private_obj.read_bytes())
            self.assertEqual(original_hash,
                             hashlib.sha256(sentinel.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
