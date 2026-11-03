"""Fixture-only optional GameSys sidecar cache integration tests.

Never open retail source maps or write anything outside a temporary cache.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "godot_editor" / "backend"))
from dx2_native_backend import ensure_source_gamesys_sidecar


class OptionalGameSysCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.map = self.dir / "Retail" / "M1_Synthetic.gmp"
        self.map.parent.mkdir()
        self.map.write_bytes(b"unaltered synthetic source")
        self.actors = self.dir / "Cache" / "actors.json"
        self.actors.parent.mkdir()
        self.actors.write_text('{"actors":[]}')
        self.system = self.dir / "System"
        self.system.mkdir()
        self.output = self.actors.parent / "gamesys_inspector.json"
        self.sha = hashlib.sha256(self.map.read_bytes()).hexdigest()

    def test_no_system_source_skips_sidecar_without_touching_cache(self):
        result = ensure_source_gamesys_sidecar(self.map, self.actors, None, self.output)
        self.assertEqual(result["status"], "not_requested")
        self.assertFalse(self.output.exists())

    def test_existing_verified_sidecar_does_not_reprocess_source(self):
        self.output.write_text(json.dumps({
            "schema": "DX2Ed-gamesys-inspector-sidecar-v1",
            "source_map": self.map.name,
            "source_sha256": self.sha,
            "read_only": True,
            "matched_scene_actors": 12,
            "archetypes": [{"class":"D_1"}],
        }))
        with patch("dx2_native_backend.build_inspector_sidecar",
                   side_effect=AssertionError("Must not rebuild matching private cache")):
            status = ensure_source_gamesys_sidecar(self.map, self.actors, self.system, self.output)
        self.assertEqual(status["status"], "cached")
        self.assertEqual(status["actors"], 12)
        self.assertEqual(status["archetypes"], 1)

    def test_stale_sidecar_replaced_only_inside_private_cache(self):
        self.output.write_text(json.dumps({
            "schema": "DX2Ed-gamesys-inspector-sidecar-v1",
            "source_map": self.map.name, "source_sha256": "0" * 64,
            "read_only": True, "archetypes": [],
        }))
        def fake_builder(source, actors, system, output):
            self.assertEqual(source, self.map)
            self.assertFalse(output.exists())
            output.write_text(json.dumps({"schema":"DX2Ed-gamesys-inspector-sidecar-v1"}))
            return {"matched_scene_actors": 2, "archetypes": [1, 2, 3]}
        with patch("dx2_native_backend.build_inspector_sidecar", side_effect=fake_builder):
            result = ensure_source_gamesys_sidecar(self.map, self.actors, self.system, self.output)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["archetypes"], 3)
        self.assertEqual(self.map.read_bytes(), b"unaltered synthetic source")

    def test_failed_research_audit_never_breaks_standard_import(self):
        with patch("dx2_native_backend.build_inspector_sidecar",
                   side_effect=ValueError("Unknown GameSys layout in research parser")):
            status = ensure_source_gamesys_sidecar(self.map, self.actors, self.system, self.output)
        self.assertEqual(status["status"], "unavailable")
        self.assertIn("Unknown GameSys", status["reason"])
        self.assertFalse(self.output.exists())
        self.assertTrue(self.actors.exists())
        self.assertEqual(self.map.read_bytes(), b"unaltered synthetic source")


if __name__ == "__main__":
    unittest.main()
