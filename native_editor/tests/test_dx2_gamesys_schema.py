"""Original DX2 GameSys property-declaration parser tests without retail assets."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor" / "package_writer"))
sys.path.insert(0, str(ROOT / "third_party" / "t3sdk_assets"))

from dx2_gamesys_audit import _read_declarations
from dx2_gamesys_schema import SCHEMA, build_gamesys_declarations, main
from t3props import parse_declarations


class DX2GameSysDeclarationTests(unittest.TestCase):
    def test_upstream_parser_reads_real_shape_dx2_property_declarations(self):
        src = """class Actor extends Object;
var(Scripts) inherited(92) array<name> TriggerScripts "Add trigger script definitions";
var(Events) inherited(79) name Tag "Event tag";
var runtimeinstantiated(43) StaticMesh StaticMesh;
var(Object) inherited(82) name Group;
"""
        found = parse_declarations("Engine", "Actor", src)
        by_id = {p.id: p for p in found}
        self.assertEqual(set(by_id), {43, 79, 82, 92})
        self.assertEqual(by_id[92].name, "TriggerScripts")
        self.assertEqual(by_id[92].type, "array<name>")
        self.assertEqual(by_id[92].category, "Scripts")
        self.assertEqual(by_id[43].kind, "runtimeinstantiated")
        self.assertEqual(by_id[79].type, "name")

    def test_declared_types_are_not_mistaken_for_verified_native_decoding(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "source-catalog.json"
            p.write_text(json.dumps({
                "schema": SCHEMA,
                "properties": {
                    "92": {"name": "TriggerScripts", "type": "array<name>",
                           "category": "Scripts", "declared_in": "Engine.Actor"},
                    "43": {"name": "StaticMesh", "type": "StaticMesh",
                           "declared_in": "Engine.Actor"},
                },
                "warnings": [],
                "conflicting_property_ids": [],
            }))
            table, meta = _read_declarations(p)
            self.assertEqual(table["92"]["type"], "array<name>")
            self.assertTrue(meta["source_property_labels_only"])
            self.assertTrue(meta["source_read_only"])

    def test_conflicting_source_ids_rejected_not_silently_overwritten(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "conflict.json"
            p.write_text(json.dumps({
                "schema": SCHEMA, "properties": {"92": {"name": "TriggerScripts"}},
                "conflicting_property_ids": [{"id": 92}],
            }))
            with self.assertRaisesRegex(ValueError, "conflicting"):
                _read_declarations(p)

    def test_unknown_schema_and_missing_archives_fail_closed(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(json.dumps({"schema": "other"}))
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                _read_declarations(p)
            with self.assertRaises((FileNotFoundError, ValueError)):
                build_gamesys_declarations(Path(d) / "missing.zip")

    def test_declaration_writer_never_overwrites_existing_source(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "System.zip"
            p.write_bytes(b"not a zip")
            self.assertEqual(main([str(p), "--output", str(p)]), 1)
            self.assertEqual(p.read_bytes(), b"not a zip")


if __name__ == "__main__":
    unittest.main()
