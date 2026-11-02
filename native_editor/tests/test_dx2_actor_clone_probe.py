"""Asset-free native DX2 prop-clone gate tests using a synthetic v95 Level.

This package is built from scratch. No proprietary DX2 files or binaries.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "native_editor" / "tests",
          ROOT / "native_editor" / "package_writer",
          ROOT / "third_party" / "t3sdk_assets"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_native_save_as import fixture_gmp
from upkg import Package, RF_HasStack
from upkgwrite import PackageWriter, ImportEntry, enc_index
from dx2_actor_clone_probe import clone_in_memory, find_candidates, write_isolated


def level_fixture(path: Path) -> bytes:
    path.write_bytes(fixture_gmp())
    original = Package(path)
    w = PackageWriter(original)
    # Convert the initial synthetic actor to a legitimate idle state-framed
    # actor with a zero-terminated GameSys list and no object links.
    w.exports[0].flags |= RF_HasStack
    actor_bytes = original.export_bytes(original.exports[0])
    # Real DX2 retail static props contain the -2/-2 state sentinel,
    # a full probe mask, latent=0, offset=-1 and a four-byte zero tail.
    neutral_frame = (bytes([0x82, 0x82]) + b"\\xff" * 8
                     + struct.pack("<I", 0) + bytes([0x81]))
    w.set_object(0, neutral_frame + actor_bytes + struct.pack("<II", 0, 0)
                 + b"\\x00" * 4)
    level_name = w.name_index("Level")
    class_name = w.name_index("Class")
    w.imports.append(ImportEntry(0, class_name, 0, level_name, (b"", b"", b"")))
    level_body = (b"\0" * 13 + struct.pack("<II", 3, 3)
                  + enc_index(2) + enc_index(0) + enc_index(1))
    # Zero is the synthetic placeholder for the builder slot. This is a
    # parser-only fixture; the source prop is the third list entry.
    index = w.add_export(0, "MyLevel", level_body)
    assert index == 1
    w.exports[index].class_ref = -2
    w.exports[index].flags = 0
    raw = w.write()
    path.write_bytes(raw)
    parsed = Package(path)
    assert parsed.level_actors() == [2, 0, 1]
    assert parsed.read_actor(parsed.exports[0]).tail == b"\\x00" * 4
    return raw


class ExperimentalSingleCloneTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Original" / "M1_Test.gmp"
        self.source.parent.mkdir(parents=True)
        self.original = level_fixture(self.source)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.opts = dict(source_sha256=self.sha,
                         actor_export=1, actor_name="StaticMeshActor__1",
                         delta=(100.0, 0.0, 0.0))

    def test_listing_is_read_only_and_only_eligible_actor_is_shown(self):
        data = find_candidates(self.source, self.sha)
        self.assertEqual(len(data["candidates"]), 1)
        self.assertEqual(data["candidates"][0]["actor"], "StaticMeshActor__1")
        self.assertEqual(data["candidates"][0]["location"], [100, 200, 300])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_append_one_export_and_level_reference_without_original_edits(self):
        report, encoded = clone_in_memory(self.source, **self.opts)
        self.assertEqual(report["status"], "binary-reparsed-runtime-unverified")
        self.assertFalse(report["runtime_game_verified"])
        self.assertEqual(report["original_export_count"], 2)
        self.assertEqual(report["new_export_count"], 3)
        self.assertEqual(report["source_location"], [100, 200, 300])
        self.assertEqual(report["new_location"], [200, 200, 300])
        self.assertEqual(report["level_actor_count_after"], 4)
        self.assertEqual(self.source.read_bytes(), self.original)
        # Independently read candidate via vendored package parser.
        candidate = self.root / "memory-candidate.gmp"
        candidate.write_bytes(encoded)
        newer = Package(candidate)
        self.assertEqual(newer.level_actors(), [2, 0, 1, 3])
        self.assertEqual(newer.export_class(newer.exports[-1]), "StaticMeshActor")
        self.assertNotEqual(newer.exports[-1].name, newer.exports[0].name)
        self.assertEqual(newer.export_bytes(newer.exports[0]),
                         Package(self.source).export_bytes(Package(self.source).exports[0]))

    def test_save_as_never_overwrites_source_or_existing_candidate(self):
        output = self.root / "ResearchOutput" / self.source.name
        report = write_isolated(self.source, output, **self.opts)
        self.assertEqual(report["status"], "isolated-GMP-created-runtime-unverified")
        self.assertEqual(report["new_export_count"], 3)
        self.assertEqual(self.source.read_bytes(), self.original)
        manifest = json.loads(output.with_suffix(".dx2ed-prop-clone.json").read_text())
        self.assertEqual(manifest["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            write_isolated(self.source, output, **self.opts)

    def test_disallow_in_place_source_descendant_and_game_folder(self):
        for output in (self.source,
                       self.source.parent / "Output" / self.source.name,
                       self.root / "Content" / "DX2" / "Maps" / self.source.name):
            with self.subTest(output=output), self.assertRaises(ValueError):
                write_isolated(self.source, output, **self.opts)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_reject_bad_hash_identity_and_zero_delta(self):
        for changes in (
            {"source_sha256": "0" * 64},
            {"actor_name": "StaticMeshActor__9"},
            {"actor_export": 2},
            {"delta": (0.0, 0.0, 0.0)},
            {"delta": (1000000.0, 0.0, 0.0)},
            {"delta": (float("nan"), 0.0, 0.0)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                clone_in_memory(self.source, **(self.opts | changes))

    def test_refuse_linked_or_stateful_source_actor(self):
        pkg = Package(self.source)
        w = PackageWriter(pkg)
        start = pkg.export_bytes(pkg.exports[0])
        # Override just state frame state node, leaving package valid.
        modified = bytearray(start)
        modified[1] = 1
        w.set_object(0, bytes(modified))
        self.source.write_bytes(w.write())
        current = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "active native/script state"):
            clone_in_memory(self.source, **(self.opts | {"source_sha256": current}))


if __name__ == "__main__":
    unittest.main()
