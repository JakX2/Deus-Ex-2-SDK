extends SceneTree
## Source-only map-wide GameSys 92 numeric index controls.
## Tests an exploratory report; no proprietary map, no actor bindings.
const View = preload("res://script_index_audit_view.gd")
const Main = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(reason: String) -> void:
    push_error("DX2Ed map-wide script index hypothesis audit: " + reason)
    quit(1)

func _audit() -> Dictionary:
    var offsets: Array = []
    for delta in [-2, -1, 0, 1, 2]:
        offsets.append({
            "name_table_index_delta": delta,
            "source_numeric_values": 5,
            "positions_with_nonempty_names": 3,
            "original_zip_script_name_hits": 2 if delta == 0 else 1,
            "distinct_original_zip_scripts": 2 if delta == 0 else 1,
            "original_ibd_exact_payload_name_hits": 1 if delta == 0 else 0,
            "distinct_original_ibd_exact_scripts": 1 if delta == 0 else 0,
            "original_ibd_different_payload_name_hits": 1 if delta == 0 else 0,
            "actors_with_zip_script_name_hits": 2 if delta == 0 else 1,
            "actors_with_ibd_exact_script_hits": 1 if delta == 0 else 0,
            "repeated_name_slot_occurrences": 0,
            "name_table_mapping_proven": false,
            "actor_script_runtime_binding_proven": false,
        })
    return {
        "schema": View.SCHEMA,
        "status": "original_name_offset_controls_computed",
        "read_only": true,
        "source_actor_values_redecoded": true,
        "name_table_integer_semantics_verified": false,
        "runtime_actor_script_binding_verified": false,
        "native_script_writer_enabled": false,
        "preferred_index_offset": null,
        "counts": {
            "actors_considered": 2,
            "verified_numeric_array_actors": 2,
            "distinct_raw_values": 4,
            "raw_value_occurrences": 5,
            "actors_skipped_unverified_or_opaque": 0,
        },
        "offsets": offsets,
    }

func _run() -> void:
    var source := _audit()
    var result := View.format_audit(source)
    if (result.is_empty()
        or not result.contains("MAP-WIDE ORIGINAL GAMEPROPERTY 92")
        or not result.contains("OFFSET")
        or not result.contains("0 | 3 | 2 | 1 | 1")
        or not result.contains("No preferred offset is chosen")
        or not result.contains("does NOT prove")
        or not result.contains("Native TriggerScript editing")):
        _fail("Original map offset control counts not safely presented")
        return
    var altered: Dictionary = source.duplicate(true)
    altered["preferred_index_offset"] = 0
    if not View.format_audit(altered).is_empty():
        _fail("Forged winner offset was accepted")
        return
    altered = source.duplicate(true)
    altered["runtime_actor_script_binding_verified"] = true
    if not View.format_audit(altered).is_empty():
        _fail("Forged runtime semantics were accepted")
        return
    altered = source.duplicate(true)
    altered["offsets"][0]["actor_script_runtime_binding_proven"] = true
    if not View.format_audit(altered).is_empty():
        _fail("One offset row falsely claiming runtime binding accepted")
        return
    altered = source.duplicate(true)
    altered["offsets"][2]["original_ibd_exact_payload_name_hits"] = 3
    if not View.format_audit(altered).is_empty():
        _fail("Overcounted exact resource matches were accepted")
        return
    altered = source.duplicate(true)
    altered["offsets"][3]["name_table_index_delta"] = 0
    if not View.format_audit(altered).is_empty():
        _fail("Duplicated index offset was accepted")
        return
    altered = source.duplicate(true)
    altered["counts"]["verified_numeric_array_actors"] = 200
    if not View.format_audit(altered).is_empty():
        _fail("Unbounded source actor verification count was accepted")
        return
    altered = source.duplicate(true)
    altered["status"] = "partial_original_actor_verification"
    altered["counts"]["actors_considered"] = 3
    altered["counts"]["actors_skipped_unverified_or_opaque"] = 1
    if not View.format_audit(altered).contains(
        "Unverified/opaque actors excluded: 1"):
        _fail("Partial original map source evidence was not labeled")
        return
    var no_evidence := {
        "schema": View.SCHEMA,
        "status": "source_package_unavailable",
        "read_only": true,
        "source_actor_values_redecoded": false,
        "name_table_integer_semantics_verified": false,
        "runtime_actor_script_binding_verified": false,
        "native_script_writer_enabled": false,
        "preferred_index_offset": null,
        "counts": {
            "actors_considered": 0,
            "verified_numeric_array_actors": 0,
            "distinct_raw_values": 0,
            "raw_value_occurrences": 0,
            "actors_skipped_unverified_or_opaque": 0,
        },
        "offsets": [],
    }
    if not View.format_audit(no_evidence).contains(
        "No verified numeric-array hypotheses could be computed"):
        _fail("Unavailable original actor source incorrectly claims offset results")
        return
    var editor = Main.new()
    editor.gameplay_details = TextEdit.new()
    editor.gameplay_ibd_evidence = {
        "original_actor_name_slot_probe": {
            "map_wide_index_audit": source,
        },
    }
    editor._show_original_map_script_index_audit()
    if editor.gameplay_details.text != result:
        _fail("Scripts tab did not display original map-wide index audit")
        return
    editor.gameplay_ibd_evidence.clear()
    editor._show_original_map_script_index_audit()
    if not editor.gameplay_details.text.contains(
        "No source-validated map-wide TriggerScripts array audit"):
        _fail("Scripts tab synthesized missing original index evidence")
        return
    editor.free()
    print("DX2Ed map-wide original GameSys 92 index-offset audit: PASS")
    quit(0)
