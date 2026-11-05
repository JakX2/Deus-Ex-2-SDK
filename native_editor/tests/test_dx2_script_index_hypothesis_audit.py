"""Source-free map-wide hypotheses for native DX2 GameSys 92 numeric arrays.

These are exploratory offset controls, NOT a machine-learning confidence
score and NOT proof that these are FName references or executable bindings.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "native_editor/godot_editor/backend"))
from dx2_script_index_hypothesis_audit import (
    SCHEMA, OFFSETS, audit_name_offset_hypotheses, unavailable,
)
from dx2_actor_script_name_candidates import inspect_name_candidates


NAMES = [
    "None", "TS_A", "NotAScript", "TS_B", "TS_C",
    "Bad", "TS_A", "", "TS_D",
]
DEFS = [{"id": "TS_A"}, {"id": "TS_B"}, {"id": "TS_C"}, {"id": "TS_D"}]
IBD = [
    {"script_id": "TS_A", "status": "exact_payload"},
    {"script_id": "TS_B", "status": "different_payload"},
    {"script_id": "TS_C", "status": "not_in_original_zip"},
]


def candidate(index, names=NAMES, defs=DEFS, ibd=IBD):
    mapped = names[index] if 0 <= index < len(names) and names[index] else None
    by_ibd = {row["script_id"].casefold(): row["status"] for row in ibd}
    return {
        "raw_compact_integer": index,
        "name_at_same_numeric_slot": mapped,
        "slot_in_package_name_table": mapped is not None,
        "same_name_in_original_tsd_archive":
            bool(mapped and mapped.casefold() in
                 {row["id"].casefold() for row in defs}),
        "ibd_resource_payload_status":
            by_ibd.get(mapped.casefold(), "not_found")
            if mapped is not None else "not_found",
        "actor_runtime_link_verified": False,
    }


def row(export, indices):
    return {
        "actor": "Synthetic_%d" % export,
        "class": "D_1",
        "export": export,
        "native_game_property_92_verified": True,
        "numeric_slots_are_name_references_verified": False,
        "status": "numeric_array_redecoded",
        "candidates": [candidate(n) for n in indices],
    }


class MapWideScriptReferenceAuditTests(unittest.TestCase):
    def test_five_offsets_preserve_denominators_and_no_winner(self):
        doc = audit_name_offset_hypotheses(
            NAMES, [row(3, [1, 3, 20]), row(7, [6, -10])],
            DEFS, IBD)
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["status"], "original_name_offset_controls_computed")
        self.assertFalse(doc["name_table_integer_semantics_verified"])
        self.assertFalse(doc["runtime_actor_script_binding_verified"])
        self.assertFalse(doc["native_script_writer_enabled"])
        self.assertIsNone(doc["preferred_index_offset"])
        self.assertEqual(doc["counts"]["verified_numeric_array_actors"], 2)
        self.assertEqual(doc["counts"]["raw_value_occurrences"], 5)
        self.assertEqual(doc["counts"]["distinct_raw_values"], 5)
        self.assertEqual([r["name_table_index_delta"] for r in doc["offsets"]],
                         list(OFFSETS))
        indexed = {entry["name_table_index_delta"]: entry
                   for entry in doc["offsets"]}
        direct = indexed[0]
        self.assertEqual(direct["positions_with_nonempty_names"], 3)
        self.assertEqual(direct["original_zip_script_name_hits"], 3)
        self.assertEqual(direct["distinct_original_zip_scripts"], 2)
        self.assertEqual(direct["original_ibd_exact_payload_name_hits"], 2)
        self.assertEqual(direct["distinct_original_ibd_exact_scripts"], 1)
        self.assertEqual(direct["original_ibd_different_payload_name_hits"], 1)
        self.assertEqual(direct["actors_with_zip_script_name_hits"], 2)
        self.assertEqual(direct["actors_with_ibd_exact_script_hits"], 2)
        self.assertEqual(direct["repeated_name_slot_occurrences"], 1)
        self.assertFalse(direct["name_table_mapping_proven"])
        self.assertFalse(direct["actor_script_runtime_binding_proven"])
        # Shifted controls can match real TSD names too. They deliberately
        # do not establish a winning runtime encoding.
        self.assertEqual(indexed[-2]["original_zip_script_name_hits"], 2)
        self.assertEqual(indexed[-1]["original_zip_script_name_hits"], 0)
        self.assertEqual(indexed[1]["original_zip_script_name_hits"], 1)
        self.assertEqual(indexed[2]["original_zip_script_name_hits"], 2)

    def test_partial_audit_counts_unverified_actors_without_guessing(self):
        missing = row(9, [1])
        missing["native_game_property_92_verified"] = False
        missing["status"] = "native_cache_property_mismatch"
        missing["candidates"] = []
        doc = audit_name_offset_hypotheses(
            NAMES, [row(3, [1]), missing], DEFS, IBD)
        self.assertEqual(doc["status"], "partial_original_actor_verification")
        self.assertEqual(doc["counts"]["actors_considered"], 2)
        self.assertEqual(doc["counts"]["verified_numeric_array_actors"], 1)
        self.assertEqual(doc["counts"]["actors_skipped_unverified_or_opaque"], 1)
        self.assertFalse(doc["runtime_actor_script_binding_verified"])

    def test_no_verified_actors_does_not_fabricate_hypotheses(self):
        opaque = row(1, [1])
        opaque["status"] = "opaque_native_array"
        opaque["candidates"] = []
        doc = audit_name_offset_hypotheses(NAMES, [opaque], DEFS, IBD)
        self.assertEqual(doc["status"], "no_independently_verified_numeric_arrays")
        self.assertFalse(doc["source_actor_values_redecoded"])
        self.assertEqual(doc["offsets"], [])
        self.assertEqual(doc["counts"]["actors_skipped_unverified_or_opaque"], 1)

    def test_empty_valid_numeric_array_is_not_an_absent_source(self):
        doc = audit_name_offset_hypotheses(NAMES, [row(5, [])], DEFS, IBD)
        self.assertEqual(doc["status"], "original_name_offset_controls_computed")
        self.assertTrue(doc["source_actor_values_redecoded"])
        self.assertEqual(doc["counts"]["raw_value_occurrences"], 0)
        self.assertEqual(len(doc["offsets"]), 5)

    def test_forged_direct_slot_name_or_tsd_match_is_rejected(self):
        for mutation in (
            {"name_at_same_numeric_slot": "TS_B"},
            {"slot_in_package_name_table": False},
            {"same_name_in_original_tsd_archive": False},
            {"ibd_resource_payload_status": "different_payload"},
            {"actor_runtime_link_verified": True},
        ):
            forged = row(2, [1])
            forged["candidates"][0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(
                    ValueError, "Forged"):
                audit_name_offset_hypotheses(NAMES, [forged], DEFS, IBD)

    def test_ambiguous_source_tsd_or_ibd_identity_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            audit_name_offset_hypotheses(
                NAMES, [row(1, [1])], DEFS + [{"id": "ts_a"}], IBD)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            audit_name_offset_hypotheses(
                NAMES, [row(1, [1])], DEFS,
                IBD + [{"script_id": "ts_a", "status": "exact_payload"}])

    def test_noninteger_raw_index_is_not_silently_rounded(self):
        for value in (True, 1.0, None, "1"):
            corrupted = row(4, [1])
            corrupted["candidates"][0]["raw_compact_integer"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_name_offset_hypotheses(NAMES, [corrupted], DEFS, IBD)

    def test_untrusted_malformed_source_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_name_offset_hypotheses(NAMES, [row(1, [1])],
                                         DEFS, [{"script_id": "TS_A",
                                                "status": "invented"}])
        with self.assertRaises(ValueError):
            audit_name_offset_hypotheses(["None", 12], [], DEFS, IBD)
        with self.assertRaises(ValueError):
            audit_name_offset_hypotheses(NAMES,
                                         [{"status": "numeric_array_redecoded",
                                           "native_game_property_92_verified": True,
                                           "numeric_slots_are_name_references_verified": False,
                                           "candidates": [{}], "export": 1}],
                                         DEFS, IBD)

    def test_public_contract_never_reports_supported_native_writes(self):
        doc = unavailable("source_package_unavailable")
        for key in ("source_actor_values_redecoded",
                    "name_table_integer_semantics_verified",
                    "runtime_actor_script_binding_verified",
                    "native_script_writer_enabled"):
            self.assertFalse(doc[key])
        self.assertIsNone(doc["preferred_index_offset"])
        self.assertEqual(doc["offsets"], [])

    def test_original_actor_probe_integration_keeps_audit_fail_closed(self):
        class Dummy:
            version, licensee = 95, 68
            names = NAMES
            exports = [{"index": 1, "name": "A"}]
            def class_name(self, _actor):
                return "D_1"
        original_cache = [{
            "actor": "A", "class": "D_1", "export": 1,
            "raw_property": {"interpretation": "index", "items": [1, 3]},
        }]
        def decoder(_pkg, _exp, _cat):
            return {}, [{"id": 92, "value": original_cache[0]["raw_property"]}]
        result = inspect_name_candidates(
            Dummy(), original_cache, DEFS, IBD, decoder=decoder)
        audit = result["map_wide_index_audit"]
        self.assertEqual(audit["counts"]["original_zip_script_name_hits"]
                         if "original_zip_script_name_hits" in audit["counts"]
                         else audit["offsets"][2]["original_zip_script_name_hits"], 2)
        self.assertFalse(audit["runtime_actor_script_binding_verified"])
        self.assertFalse(result["actor_to_script_binding_verified"])


if __name__ == "__main__":
    unittest.main()
