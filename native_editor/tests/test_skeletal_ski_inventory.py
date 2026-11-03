"""Asset-free tests for DX2 original v2-v5 skeletal descriptor inventory."""
from __future__ import annotations
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"godot_editor"/"backend"))
from dx2_skeletal_ski_inventory import SCHEMA, catalog_from_zip, parse_ski

HEADER = [
    "0.000000 0.000000 0.000000",
    "0.000000 0.000000 0.000000",
    "1.000000 1.000000 1.000000",
    "1 0 10 0",
    "10 1.000000 0.300000 0.000000 0.000000",
]


def ski(version: str, name: str, animation: str) -> bytes:
    lines=[version,name,*HEADER]
    if version in ("v3","v4","v5"):
        lines.append("MeshFlags=N")
    if version=="v5":
        lines.extend(["3","0.000000","150.000000","75.000000"])
    lines.extend(["1",animation])
    if version in ("v3","v4","v5"):
        lines.append("Flags=")
    lines.append("0")
    return ("\r\n".join(lines)+"\r\n").encode("utf8")


class SkeletonSourceTests(unittest.TestCase):
    def test_versions_and_animation_references(self):
        for version in ("v2","v3","v4","v5"):
            with self.subTest(version=version):
                record=parse_ski(ski(version,"generic_male","wto"),
                                 "SkeletalMeshes/generic_male.ski")
                self.assertEqual(record["name"],"generic_male")
                self.assertEqual(record["animation_sets"],["wto"])
                self.assertFalse(record["geometry_decoded"])
                self.assertFalse(record["npc_class_mapping_verified"])

    def test_v2_windows_animation_resource_reference(self):
        record=parse_ski(ski("v2","baton",r"\content\dx2\skeletalanimations\baton"),
                         "SkeletalMeshes/baton.ski")
        self.assertEqual(record["animation_sets"],["baton"])

    def test_archive_provenance_and_never_unpacks_assets(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"SkeletalMeshes.zip"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("SkeletalMeshes/generic_male.ski",
                           ski("v5","generic_male","wto"))
                z.writestr("SkeletalMeshes/generic_male.pro",b"unparsed private geometry")
                z.writestr("SkeletalMeshes/chad_def.ski",
                           ski("v5","chad_def","wto"))
            data=catalog_from_zip(path)
            self.assertEqual(data["schema"],SCHEMA)
            self.assertEqual(data["record_count"],2)
            self.assertEqual(data["pro_count"],1)
            self.assertTrue(data["records"][1]["pro_present"])
            self.assertFalse(data["records"][0]["pro_present"])
            self.assertEqual(data["source_sha256"],hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(data["npc_spawn_enabled"])
            self.assertFalse(data["geometry_decoded"])

    def test_fail_closed_identity_and_invalid_archive(self):
        with self.assertRaisesRegex(ValueError,"identity"):
            parse_ski(ski("v5","other_model","wto"),
                      "SkeletalMeshes/generic_male.ski")
        with self.assertRaisesRegex(ValueError,"Wrong number"):
            parse_ski(ski("v5","generic_male","wto").replace(
                b"0.000000 0.000000 0.000000",
                b"0.000000",1), "SkeletalMeshes/generic_male.ski")
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"SkeletalMeshes.zip"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("../escape.ski",ski("v4","escape","wto"))
            with self.assertRaisesRegex(ValueError,"Unsafe"):
                catalog_from_zip(path)

if __name__=="__main__":
    unittest.main()
