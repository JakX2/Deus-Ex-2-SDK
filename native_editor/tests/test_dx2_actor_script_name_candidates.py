"""Synthetic cross-source evidence for DX2 GameSys 92 numeric name slots.

Tests do not assume the actor property is an FName-indexed array and
never import proprietary game files or synthesize native script writes.
"""
from __future__ import annotations

import sys
from pathlib import Path
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor/godot_editor/backend"))
from dx2_actor_script_name_candidates import inspect_name_candidates


def package(names=None):
    exports = [
        {"index": i, "name": "SyntheticActor__1" if i == 7 else "Other"}
        for i in range(1, 8)
    ]
    return SimpleNamespace(
        names=(names if names is not None
               else ["None", "TS_100", "GenericLightSwitch", "TS_200"]),
        exports=exports,
        version=95,
        licensee=68,
        class_name=lambda exp: "D_527" if exp["index"] == 7 else "OtherClass",
    )


def cache(items=None):
    return {
        "actor": "SyntheticActor__1",
        "class": "D_527",
        "export": 7,
        "raw_property": {
            "interpretation": "index",
            "items": [1, 2, 3, 4000, -2] if items is None else items,
        },
    }


def definitions():
    return [
        {"id": "TS_100"}, {"id": "TS_200"}, {"id": "Another"},
    ]


def ibd_entries():
    return [
        {"script_id": "TS_100", "status": "exact_payload"},
        {"script_id": "TS_200", "status": "different_payload"},
        {"script_id": "TS_LOCAL_ONLY", "status": "not_in_original_zip"},
    ]


def decoder(value=None, *, prop_count=1):
    def decode(_package, _export, _catalog):
        val = cache()["raw_property"] if value is None else value
        return {}, [{"id": 92, "value": val} for _ in range(prop_count)]
    return decode


class ActorScriptCandidateTests(unittest.TestCase):
    def report(self, actor=None, pkg=None, decode=None):
        return inspect_name_candidates(
            pkg if pkg is not None else package(),
            [actor if actor is not None else cache()],
            definitions(), ibd_entries(),
            decoder=decode if decode is not None else decoder(),
        )

    def test_source_redecoded_name_slot_and_ibd_match_is_candidate_not_binding(self):
        result = self.report()
        self.assertEqual(result["status"], "original_package_name_slots_inspected")
        self.assertTrue(result["read_only"])
        self.assertFalse(result["actor_to_script_binding_verified"])
        self.assertFalse(result["name_table_indices_semantics_verified"])
        self.assertFalse(result["native_script_writer_enabled"])
        self.assertEqual(result["counts"]["native_property_verified"], 1)
        self.assertEqual(result["counts"]["candidate_name_slots"], 3)
        self.assertEqual(result["counts"]["source_tsd_name_candidates"], 2)
        self.assertEqual(result["counts"]["ibd_exact_name_candidates"], 1)
        actor = result["actors"][0]
        self.assertTrue(actor["native_game_property_92_verified"])
        self.assertFalse(actor["numeric_slots_are_name_references_verified"])
        self.assertEqual(actor["status"], "numeric_array_redecoded")
        names = actor["candidates"]
        self.assertEqual(names[0]["raw_compact_integer"], 1)
        self.assertEqual(names[0]["name_at_same_numeric_slot"], "TS_100")
        self.assertTrue(names[0]["same_name_in_original_tsd_archive"])
        self.assertEqual(names[0]["ibd_resource_payload_status"], "exact_payload")
        self.assertFalse(names[0]["actor_runtime_link_verified"])
        self.assertEqual(names[1]["name_at_same_numeric_slot"], "GenericLightSwitch")
        self.assertFalse(names[1]["same_name_in_original_tsd_archive"])
        self.assertEqual(names[2]["ibd_resource_payload_status"], "different_payload")
        self.assertEqual(names[3]["name_at_same_numeric_slot"], None)
        self.assertEqual(names[4]["name_at_same_numeric_slot"], None)

    def test_forged_cache_actor_export_rejected(self):
        item = cache()
        item["export"] = 55
        result = self.report(actor=item)
        self.assertEqual(result["counts"]["native_property_verified"], 0)
        self.assertEqual(result["counts"]["candidate_name_slots"], 0)
        self.assertEqual(result["actors"][0]["candidates"], [])

    def test_forged_cache_actor_name_or_class_rejected(self):
        for key, value in (("actor", "Fake"), ("class", "Fake")):
            item = cache()
            item[key] = value
            result = self.report(actor=item)
            self.assertEqual(result["actors"][0]["status"],
                             "unverified_native_actor")

    def test_cache_script_list_must_match_original_game_property_92(self):
        mismatched = {"interpretation": "index", "items": [3]}
        result = self.report(decode=decoder(mismatched))
        self.assertEqual(result["actors"][0]["status"],
                         "native_cache_property_mismatch")
        self.assertEqual(result["counts"]["native_property_verified"], 0)

    def test_duplicate_native_game_property_92_rejected(self):
        result = self.report(decode=decoder(prop_count=2))
        self.assertFalse(result["actors"][0]["native_game_property_92_verified"])

    def test_opaque_or_string_array_not_interpreted_as_name_table(self):
        for value in ({"raw_hex": "fd", "byte_length": 1},
                      {"interpretation": "string", "items": ["TS_100"]},
                      {"interpretation": "index", "items": [True]},
                      {"interpretation": "index", "items": list(range(257))}):
            result = self.report(actor={**cache(), "raw_property": value},
                                 decode=decoder(value))
            self.assertEqual(result["counts"]["candidate_name_slots"], 0)
            # Malformed compact-index arrays are never promoted to names.
            if value.get("interpretation") == "index" and value.get("items") == [True]:
                self.assertFalse(result["actors"][0]["candidates"][0][
                    "slot_in_package_name_table"])
            else:
                self.assertEqual(result["actors"][0]["candidates"], [])

    def test_no_package_or_unsupported_licensee_returns_no_claims(self):
        for pkg in (None, SimpleNamespace(
                    names=["TS_100"], exports=[], version=95,
                    licensee=133)):
            # Passing None with the direct API emulates a failed Package read.
            result = inspect_name_candidates(
                pkg, [cache()], definitions(), ibd_entries(), decoder=decoder())
            self.assertEqual(result["status"], "source_package_unavailable")
            self.assertEqual(result["actors"], [])
            self.assertFalse(result["actor_to_script_binding_verified"])

    def test_case_folded_original_name_matching_but_no_script_assignment(self):
        item = cache([1])
        result = self.report(
            actor=item,
            pkg=package(["None", "ts_100"]),
            decode=decoder(item["raw_property"]),
        )
        name = result["actors"][0]["candidates"][0]
        self.assertEqual(name["name_at_same_numeric_slot"], "ts_100")
        self.assertTrue(name["same_name_in_original_tsd_archive"])
        self.assertFalse(name["actor_runtime_link_verified"])

    def test_empty_original_script_array_is_a_verified_empty_array(self):
        item = cache([])
        result = self.report(actor=item, decode=decoder(item["raw_property"]))
        self.assertTrue(result["actors"][0]["native_game_property_92_verified"])
        self.assertEqual(result["actors"][0]["candidates"], [])
        self.assertEqual(result["counts"]["native_property_verified"], 1)


if __name__ == "__main__":
    unittest.main()
