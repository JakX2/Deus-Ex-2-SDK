"""Synthetic, asset-free TriggerScript source and map actor reference checks."""
from __future__ import annotations
import io
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "scripts"))
from dx2_trigger_script_index import (
    SCHEMA, ACTOR_SCHEMA, actor_script_reference_report,
    build_report, index_script_archive, main, parse_tsd, render_html,
)


def tsd(name="TS_42", *, old=False, title="Door opens"):
    content = (name + "\x00" + title + "\x00" + "kTCT_FrobByPlayer\x00"
               + "kTPT_String\x00" + "kTAT_OpenDoorLink\x00").encode("utf-16le")
    if old:
        return b"0FFE2FST" + struct.pack("<II",len(content)+4,16) + content
    return b"1FFE2FST" + struct.pack("<III",0,len(content)+4,16) + content


def archive(folder: Path, *, outer=True) -> Path:
    raw = io.BytesIO()
    with ZipFile(raw, "w") as z:
        z.writestr("Defs/TS_42.tsd", tsd())
        z.writestr("Defs/GenericDoor.tsd", tsd("GenericDoor", old=True))
        z.writestr("DeletedScripts/TS_17.tsd", tsd("TS_17"))
    path = folder / ("game_resources.zip" if outer else "TriggerScript.zip")
    if outer:
        with ZipFile(path, "w") as z:
            z.writestr("TriggerScript.zip", raw.getvalue())
    else:
        path.write_bytes(raw.getvalue())
    return path


class TriggerScriptIndexTests(unittest.TestCase):
    def test_valid_new_and_old_declarations(self):
        for blob in (tsd(), tsd(old=True)):
            item = parse_tsd(blob,"Defs/TS_42.tsd",deleted=False)
            self.assertEqual(item["source_name"],"TS_42")
            self.assertTrue(item["embedded_name_matches_filename"])
            self.assertEqual(item["condition_symbols"][0]["text"],"kTCT_FrobByPlayer")
            self.assertEqual(item["action_symbols"][0]["text"],"kTAT_OpenDoorLink")
            self.assertEqual(item["parameter_type_symbols"][0]["text"],"kTPT_String")
            self.assertFalse(item["symbol_graph_decoded"])

    def test_truncated_corrupt_size_rejected(self):
        with self.assertRaisesRegex(ValueError,"header"):
            parse_tsd(b"random","Defs/X.tsd",deleted=False)
        with self.assertRaisesRegex(ValueError,"length mismatch"):
            parse_tsd(tsd()[:-2],"Defs/X.tsd",deleted=False)

    def test_original_and_nested_zip_index_without_guessing_graph_edges(self):
        with TemporaryDirectory() as temp:
            for outer in (True,False):
                path=archive(Path(temp),outer=outer)
                index=index_script_archive(path)
                self.assertEqual(index["schema"],SCHEMA)
                self.assertEqual(index["definitions_count"],3)
                self.assertEqual(index["counts"]["active_source_definitions"],2)
                self.assertEqual(index["counts"]["deleted_sources"],1)
                self.assertIn("kTAT_OpenDoorLink",index["unique_symbols"]["action"])
                self.assertFalse(index["event_graph_decoded"])
                self.assertFalse(index["native_script_editing_supported"])
                record=next(x for x in index["definitions"] if x["member"]=="DeletedScripts/TS_17.tsd")
                self.assertTrue(record["deleted_source"])

    def test_indices_in_cached_actor_property_not_equated_to_ts_names(self):
        actors={"meta":{"source_map":"M1_Seattle_Hub_WTOterminal.gmp",
                        "source_map_sha256":"fixture"},
                "actors":[
                    {"name":"D_527__0","class":"D_527","export":5,
                     "game_properties":[{"id":92,"value":{"items":[432,424,438],"interpretation":"index"}}]},
                    {"name":"StaticMeshActor__119","class":"StaticMeshActor","export":554,"game_properties":[]},
                    {"name":"Other__0","class":"Other","export":15,
                     "game_properties":[{"id":92,"value":{"items":[0]}}]},
                ]}
        summary=actor_script_reference_report(actors)
        self.assertEqual(summary["schema"],ACTOR_SCHEMA)
        self.assertEqual(summary["actors_with_property_92"],2)
        self.assertEqual(summary["serialized_indices_total"],4)
        self.assertEqual(summary["actors"][0]["serialized_indices"],[432,424,438])
        self.assertEqual(summary["actors"][0]["status"],"unresolved_script_index_array")
        self.assertFalse(summary["native_script_binding_verified"])
        self.assertEqual(summary["source_map_sha256"],"fixture")


    def test_original_organizer_three_trees_and_active_source_join(self):
        from dx2_script_organizer import parse_organizer, attach_organizer_index
        organizer = ("2\r\nHeaderBegin\r\n2\r\n"
                     "0\r\nM1_Seattle\r\n2\r\n"
                     "1\r\nTS_42\r\n1\r\nGenericDoor\r\n"
                     "1\r\nTS_42\r\n"
                     "HeaderBegin\r\n1\r\n0\r\nAI\r\n1\r\n"
                     "1\r\nkTCT_FrobByPlayer\r\n"
                     "HeaderBegin\r\n1\r\n0\r\nActions\r\n1\r\n"
                     "1\r\nkTAT_OpenDoorLink\r\n").encode("ascii")
        parsed = parse_organizer(organizer)
        self.assertEqual(parsed["trees"]["scripts"]["entry_count"], 3)
        self.assertEqual(parsed["trees"]["scripts"]["unique_entry_count"], 2)
        self.assertEqual(parsed["trees"]["scripts"]["duplicate_entry_names"],
                         [{"name":"TS_42", "count":2}])
        self.assertEqual(parsed["trees"]["scripts"]["paths_by_name"]["ts_42"],
                         [["M1_Seattle"], []])
        index = {"definitions":[
            {"filename_stem":"TS_42", "deleted_source":False},
            {"filename_stem":"GenericDoor", "deleted_source":False},
            {"filename_stem":"Deleted", "deleted_source":True},
        ]}
        attach_organizer_index(index, parsed)
        self.assertEqual(index["organizer"]["unlisted_active_definitions"],[])
        self.assertEqual(index["organizer"]["orphan_script_organizer_entries"],[])
        self.assertEqual(index["definitions"][0]["organizer_paths"],
                         [["M1_Seattle"], []])
        self.assertEqual(index["definitions"][2]["organizer_status"],
                         "historical_deleted_source")
        self.assertTrue(index["organizer"]["categories_are_source_metadata_only"])

    def test_organizer_bad_counts_and_extra_trailing_data_are_rejected(self):
        from dx2_script_organizer import parse_organizer
        good = ("2\nHeaderBegin\n1\n1\nTS_42\n"
                "HeaderBegin\n0\nHeaderBegin\n0\n")
        with self.assertRaisesRegex(ValueError,"trailing"):
            parse_organizer((good+"UNEXPECTED\n").encode())
        with self.assertRaisesRegex(ValueError,"Truncated"):
            parse_organizer(b"2\nHeaderBegin\n1\n0\n")
        with self.assertRaisesRegex(ValueError,"Unsupported"):
            parse_organizer(good.replace("2\n","3\n",1).encode())

    def test_original_tso_can_be_read_from_nested_archive(self):
        with TemporaryDirectory() as d:
            path=Path(d)/"TriggerScript.zip"
            with ZipFile(path,"w") as z:
                z.writestr("Defs/TS_42.tsd", tsd())
                z.writestr("Organize/ScriptOrganizer.tso",
                    "2\r\nHeaderBegin\r\n1\r\n"
                    "0\r\nM1_Seattle\r\n1\r\n1\r\nTS_42\r\n"
                    "HeaderBegin\r\n0\r\nHeaderBegin\r\n0\r\n")
            idx=index_script_archive(path)
            self.assertEqual(idx["organizer"]["counts"]["scripts"]["folder_count"],1)
            self.assertEqual(idx["definitions"][0]["organizer_paths"],[["M1_Seattle"]])

    def test_invalid_serialized_property_not_falsely_resolved(self):
        report=actor_script_reference_report({"actors":[
            {"name":"NPC","export":1,"class":"NPC","game_properties":[{"id":92,"value":{"items":[True,3]}}]},
        ]})
        self.assertEqual(report["actors"][0]["status"],"unparsed_serialized_value")
        self.assertEqual(report["serialized_indices_total"],0)

    def test_offline_html_escapes_dangerous_actor_names_and_lists_unknown_indices(self):
        with TemporaryDirectory() as d:
            src=archive(Path(d))
            actors=Path(d)/"actors.json"
            actors.write_text(json.dumps({"actors":[{
                "name":"</script><script>alert(1)</script>", "class":"NPC",
                "export":1, "game_properties":[{"id":92,"value":{"items":[424]}}]
            }]}))
            document=build_report(src,actors)
            html=render_html(document)
            self.assertEqual(html.count("</script>"),2)
            self.assertIn("\\u003c/script>",html)
            self.assertIn("actor_script_references",html)
            self.assertIn("Condition palette",html)
            self.assertIn("Action palette",html)
            self.assertIn("All original categories",html)
            html_path=Path(d)/"triggers.html"
            self.assertEqual(main([str(src),"--actors",str(actors),
                                   "--format","html","--output",str(html_path)]),0)
            self.assertIn("DX2Ed Mission Logic Source Browser",html_path.read_text())

    def test_cli_writes_separate_json_without_mutating_sources(self):
        with TemporaryDirectory() as d:
            folder=Path(d)
            src=archive(folder)
            actors=folder/"actors.json"
            actors.write_text(json.dumps({"actors":[
                {"name":"NPC","class":"NPC","export":1,
                 "game_properties":[{"id":92,"value":{"items":[42]}}]}
            ]}))
            original=src.read_bytes()
            output=folder/"logic_index.json"
            self.assertEqual(main([str(src),"--actors",str(actors),"--output",str(output)]),0)
            doc=json.loads(output.read_text())
            self.assertEqual(doc["actor_script_references"]["serialized_indices_total"],1)
            self.assertEqual(src.read_bytes(),original)
            with self.assertRaises(SystemExit):
                main([str(src),"--output",str(src)])
            self.assertEqual(src.read_bytes(),original)


if __name__=="__main__":
    unittest.main()
