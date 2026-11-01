"""Synthetic ZIP tests for the Seattle Club audit and staging pipeline.

Uses entirely invented data, not retail game assets.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZipInfo

BACKEND = Path(__file__).resolve().parents[1] / "godot_editor" / "backend"
sys.path.insert(0, str(BACKEND))
import dx2_zip_stage as staging
import dx2_zip_audit as audit


class ZipWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.club = self.root / "club.zip"
        self.maps = self.root / "maps.zip"
        self.system = self.root / "System.zip"
        self.cache = self.root / "private_cache"
        with ZipFile(self.club, "w") as z:
            z.writestr("M1_Seattle_Club.gmp", b"fictional GMP sample")
            z.writestr("m1_club.ibd", b"fictional mission bundle")
        with ZipFile(self.maps, "w") as z:
            z.writestr("maps/Kernel_GFXALL.ibd", b"imagined shared gfx")
            z.writestr("maps/MainMenu_GFXALL.ibd", b"imagined mainmenu gfx")
            z.writestr("maps/Kernel_PHYALL.ibd", b"imagined physics")
        with ZipFile(self.system, "w") as z:
            z.writestr("System/DX2Gamesys.d2u", b"fictional gamesys")
            z.writestr("System/DX2UI.ini", b"[fictional]\n")
            z.writestr("System/UseBlockLoading.ini", b"root copy")
            z.writestr("System/Extra/UseBlockLoading.ini", b"nested copy")
            z.writestr("System/dx2.exe", b"never stage this executable")

    def test_preflight_target_lookup_and_crc(self):
        report = audit.audit_archives([self.club, self.maps, self.system], verify=True)
        self.assertTrue(report["named_pair_present"])
        self.assertEqual(len(report["targets"]["m1_seattle_club.gmp"]), 1)
        self.assertTrue(report["targets"]["m1_club.ibd"][0]["crc_checked"])

    def test_staging_preserves_nested_system_paths_and_excludes_exe(self):
        result = staging.prepare(self.club, self.maps, self.cache, self.system)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["cached"])
        base = Path(result["staging_directory"])
        self.assertEqual((base / "Maps" / "M1_Seattle_Club.gmp").read_bytes(),
                         b"fictional GMP sample")
        self.assertEqual((base / "Maps" / "Kernel_GFXALL.ibd").read_bytes(),
                         b"imagined shared gfx")
        self.assertEqual((base / "System" / "DX2Gamesys.d2u").read_bytes(),
                         b"fictional gamesys")
        self.assertEqual((base / "System" / "UseBlockLoading.ini").read_bytes(), b"root copy")
        self.assertEqual((base / "System" / "Extra" / "UseBlockLoading.ini").read_bytes(),
                         b"nested copy")
        self.assertFalse((base / "System" / "dx2.exe").exists())
        manifest = json.loads((base / "source_manifest.json").read_text())
        self.assertTrue(manifest["files"])
        self.assertEqual(len(manifest["files"]), 9)
        self.assertEqual(staging.prepare(self.club, self.maps, self.cache, self.system)
                         ["cached"], True)

    def test_cache_detects_corruption_without_replacing_game_assets(self):
        original = self.club.read_bytes()
        prepared = staging.prepare(self.club, self.maps, self.cache)
        source = Path(prepared["map"])
        source.write_bytes(b"x" * source.stat().st_size)
        with self.assertRaisesRegex(ValueError, "verification failed"):
            staging.prepare(self.club, self.maps, self.cache)
        self.assertEqual(self.club.read_bytes(), original)

    def test_source_change_changes_cache_key(self):
        first = staging.prepare(self.club, self.maps, self.cache)
        with ZipFile(self.club, "a") as z:
            z.writestr("NOTE.txt", b"a newly updated archive")
        second = staging.prepare(self.club, self.maps, self.cache)
        self.assertNotEqual(first["staging_directory"], second["staging_directory"])

    def test_missing_shared_bundle_is_rejected(self):
        with ZipFile(self.maps, "w") as z:
            z.writestr("Kernel_GFXALL.ibd", b"only one bundle")
        with self.assertRaisesRegex(ValueError, "Missing required shared"):
            staging.prepare(self.club, self.maps, self.cache)

    def test_zip_traversal_and_symlink_rejected(self):
        with ZipFile(self.system, "w") as z:
            z.writestr("System/../evil.ini", b"unsafe")
        with self.assertRaisesRegex(ValueError, "Unsafe ZIP member"):
            staging.prepare(self.club, self.maps, self.cache, self.system)

        with ZipFile(self.system, "w") as z:
            entry = ZipInfo("System/link.ini")
            entry.create_system = 3
            entry.external_attr = (0o120777 << 16)
            z.writestr(entry, b"System/foo")
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            staging.prepare(self.club, self.maps, self.cache, self.system)

    def test_duplicate_bundle_rejected(self):
        with ZipFile(self.maps, "a") as z:
            z.writestr("other/Kernel_GFXALL.ibd", b"duplicate")
        with self.assertRaisesRegex(ValueError, "Duplicate map-bundle"):
            staging.prepare(self.club, self.maps, self.cache)


if __name__ == "__main__":
    unittest.main()
