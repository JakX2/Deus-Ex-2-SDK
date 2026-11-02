"""Fixture-only DX2 ConText.eng indexing and text-edit preview tests.

No licensed game dialogue is checked into this repository.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "dialogue"))
from dx2_dialogue_library import (
    SCHEMA, DRAFT_SCHEMA, cli, digest, index_source, load_source,
    new_draft, preview_changes, render_html, write_distinct,
)


TEXT = b'1\r\nAvaJohnson: "Hello."\r\n// Scene note, not a spoken line\r\nChoice: "Stay."\r\n'
ALT = b'1\nStandardPlayer: "A test."\n'


class DialogueLibraryTests(unittest.TestCase):
    def test_original_archive_path_and_source_line_numbers(self):
        with TemporaryDirectory() as folder:
            archive_path = Path(folder) / "DX2mr.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("Conversations/English/ConText.eng", TEXT)
                archive.writestr("Conversations/English/M1_Seattle_Club.con", b"\x00\x01")
            source = load_source(archive_path)
            doc = index_source(source)
            self.assertEqual(doc["schema"], SCHEMA)
            self.assertEqual(doc["source_line_count"], 4)
            self.assertEqual(doc["counts_by_kind"]["spoken"], 1)
            self.assertEqual(doc["counts_by_kind"]["choice"], 1)
            self.assertEqual(doc["counts_by_kind"]["comment"], 1)
            self.assertEqual(doc["lines"][1]["speaker"], "AvaJohnson")
            self.assertEqual(doc["lines"][1]["line"], 2)
            self.assertEqual(doc["lines"][3]["text"], "Stay.")
            self.assertFalse(doc["compiled_con_graph_decoded"])
            self.assertEqual(len(doc["compiled_con_files"]), 1)
            self.assertFalse(doc["compiled_con_files"][0]["recognized_container_header"])
            self.assertFalse(doc["compiled_con_files"][0]["graph_decoded"])
            self.assertEqual(source["sha256"], hashlib.sha256(TEXT).hexdigest())

    def test_nested_zip_layout_and_ambiguous_archives_are_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "data.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("DX2/Conversations/English/ConText.eng", TEXT)
            self.assertEqual(len(load_source(path)["lines"]), 4)
            with ZipFile(path, "a") as archive:
                archive.writestr("Conversations/English/ConText.eng", ALT)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                load_source(path)

    def test_original_con_headers_are_inventory_only(self):
        with TemporaryDirectory() as folder:
            archive_path = Path(folder) / "DX2mr.zip"
            original = b"1FFE1NOC" + b"\x00" * 4 + (20).to_bytes(4, "little") + b"X" * 20
            variant = b"0FFE1NOC" + b"\x00" * 4 + (1).to_bytes(4, "little") + b"Y"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("Conversations/English/ConText.eng", TEXT)
                archive.writestr("Conversations/English/M1_Seattle_Club.con", original)
                archive.writestr("Conversations/English/TestOld.con", variant)
            records = index_source(load_source(archive_path))["compiled_con_files"]
            self.assertEqual(len(records), 2)
            self.assertTrue(all(r["declared_size_matches_file"] for r in records))
            self.assertTrue(all(r["recognized_container_header"] for r in records))
            self.assertTrue(all(not r["map_link_verified"] for r in records))
            self.assertEqual(records[0]["map_filename_hint"], "M1_Seattle_Club.gmp")

    def test_draft_preview_changes_only_text_and_preserves_crlf(self):
        with TemporaryDirectory() as folder:
            src = Path(folder) / "ConText.eng"
            src.write_bytes(TEXT)
            original = load_source(src)
            index = index_source(original)
            draft = new_draft(original)
            self.assertEqual(draft["schema"], DRAFT_SCHEMA)
            draft["edits"] = [{
                "line": 2,
                "original_sha256": index["lines"][1]["raw_sha256"],
                "replacement_text": "Hello, Alex.",
            }, {
                "line": 4,
                "original_sha256": index["lines"][3]["raw_sha256"],
                "replacement_text": "Leave.",
            }]
            preview, report = preview_changes(original, draft)
            self.assertEqual(
                preview,
                b'1\r\nAvaJohnson: "Hello, Alex."\r\n// Scene note, not a spoken line\r\nChoice: "Leave."\r\n',
            )
            self.assertEqual(report["preview_edit_count"], 2)
            self.assertFalse(report["native_con_compiled"])
            self.assertEqual(src.read_bytes(), TEXT)

    def test_stale_source_and_line_edits_fail_closed(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ConText.eng"
            path.write_bytes(TEXT)
            source = load_source(path)
            draft = new_draft(source)
            draft["source_sha256"] = "incorrect"
            with self.assertRaisesRegex(ValueError, "identity/hash"):
                preview_changes(source, draft)
            draft["source_sha256"] = source["sha256"]
            draft["edits"] = [{"line":2, "original_sha256":"bad", "replacement_text":"Test"}]
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                preview_changes(source, draft)
            correct = digest(source["lines"][1].encode("utf-8"))
            draft["edits"] = [{"line":2, "original_sha256":correct, "replacement_text":"Test\nNext"}]
            with self.assertRaisesRegex(ValueError, "Invalid replacement"):
                preview_changes(source, draft)
            draft["edits"] = [
                {"line":2, "original_sha256":correct, "replacement_text":"A"},
                {"line":2, "original_sha256":correct, "replacement_text":"B"},
            ]
            with self.assertRaisesRegex(ValueError, "repeated"):
                preview_changes(source, draft)

    def test_comments_and_header_cannot_be_edited_as_speech(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ConText.eng"
            path.write_bytes(TEXT)
            source = load_source(path)
            draft = new_draft(source)
            draft["edits"] = [{"line":3,
                "original_sha256":digest(source["lines"][2].encode()),
                "replacement_text":"Changed"}]
            with self.assertRaisesRegex(ValueError, "not a supported"):
                preview_changes(source, draft)

    def test_cli_preview_and_inplace_write_guard(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ConText.eng"
            path.write_bytes(TEXT)
            index_path = Path(folder) / "index.json"
            draft_path = Path(folder) / "draft.json"
            preview_path = Path(folder) / "preview.eng"
            self.assertEqual(cli(["index",str(path),"--output",str(index_path)]),0)
            self.assertEqual(cli(["new-draft",str(path),"--output",str(draft_path)]),0)
            draft = json.loads(draft_path.read_text())
            doc = json.loads(index_path.read_text())
            draft["edits"] = [{"line":2,
                "original_sha256":doc["lines"][1]["raw_sha256"],
                "replacement_text":"New line"}]
            draft_path.write_text(json.dumps(draft))
            self.assertEqual(cli(["preview",str(path),"--draft",str(draft_path),
                                  "--output",str(preview_path)]),0)
            self.assertIn(b'New line',preview_path.read_bytes())
            self.assertEqual(path.read_bytes(),TEXT)
            self.assertEqual(cli(["preview",str(path),"--draft",str(draft_path),
                                  "--output",str(path)]),1)
            self.assertEqual(path.read_bytes(),TEXT)
            self.assertEqual(cli(["preview",str(path),"--draft",str(draft_path),
                                  "--output",str(Path(folder)/"ConText.eng")]),1)
            with self.assertRaisesRegex(ValueError,"in-place"):
                write_distinct(path,[path],b"corruption")

    def test_searchable_html_safe_for_embedded_script_tags(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "ConText.eng"
            source.write_text('1\nAva: "</script><script>alert(1)</script>"\n')
            doc = index_source(load_source(source))
            html = render_html(doc)
            self.assertEqual(html.count("</script>"), 2)
            self.assertIn("\\u003c/script>", html)
            self.assertIn("counts_by_speaker", html)
            output = Path(folder) / "dialogue.html"
            self.assertEqual(cli(["html",str(source),"--output",str(output)]),0)
            self.assertIn("DX2Ed Dialogue Source Browser",output.read_text())
            self.assertEqual(source.read_text(),'1\nAva: "</script><script>alert(1)</script>"\n')

    def test_default_utf8_is_strict_and_can_choose_legacy_encoding(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ConText.eng"
            path.write_bytes(b'1\nAva: "caf\xe9"\n')
            with self.assertRaises(UnicodeDecodeError):
                load_source(path)
            source = load_source(path, encoding="cp1252")
            self.assertEqual(index_source(source)["lines"][1]["text"], "café")


if __name__ == "__main__":
    unittest.main()
