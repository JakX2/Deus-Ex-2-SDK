extends SceneTree
## Headless source-only Godot verification for IBD script provenance labels.
## A synthetic row is displayed without claiming a live actor binding.
## Real byte comparison is independently tested in Python synthetic fixtures.
const Main = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed original script IBD provenance panel: " + message)
    quit(1)

func _run() -> void:
    var editor = Main.new()
    editor.gameplay_filter = LineEdit.new()
    editor.gameplay_list = ItemList.new()
    editor.gameplay_details = TextEdit.new()
    editor.gameplay_catalog = {
        "script_definitions": [
            {"id": "TS_Synthetic", "title": "Synthetic switch",
             "archive_member": "Defs/TS_Synthetic.tsd",
             "format": "1FFE2FST",
             "conditions": ["kTCT_Synthetic"],
             "actions": ["kTAT_Synthetic"]},
            {"id": "TS_MissingInBundle", "title": "Other definition",
             "archive_member": "Defs/TS_MissingInBundle.tsd",
             "format": "1FFE2FST",
             "conditions": [], "actions": []}
        ]
    }
    editor.gameplay_ibd_evidence = {"ibd_name": "SyntheticMission.ibd"}
    editor.gameplay_ibd_by_id = {
        "ts_synthetic": {
            "script_id": "TS_Synthetic", "status": "exact_payload",
            "ibd_resource_index": 4,
            "source_payload_sha256": "a".repeat(64),
            "ibd_payload_sha256": "a".repeat(64),
        }
    }
    editor._refresh_gameplay_script_list()
    if editor.gameplay_list.item_count != 2:
        _fail("Script definitions disappeared after provenance comparison")
        return
    if not editor.gameplay_list.get_item_text(0).begins_with("[IBD exact]"):
        _fail("Byte-exact source IBD resource not indicated in Scripts tab")
        return
    if editor.gameplay_list.get_item_text(1).contains("[IBD exact]"):
        _fail("Source script not located in IBD falsely marked exact")
        return
    editor._gameplay_script_selected(0)
    var details: String = editor.gameplay_details.text
    if (not details.contains("ORIGINAL IBD RESOURCE EVIDENCE")
        or not details.contains("SyntheticMission.ibd")
        or not details.contains("Exact source TSD payload equality")
        or not details.contains("Not bound to a specific map actor")):
        _fail("Provenance detail lost the no-runtime-binding warning")
        return
    editor._gameplay_script_selected(1)
    if not editor.gameplay_details.text.contains(
            "No matching script ID found in selected original IBD"):
        _fail("Absent script did not retain explicit non-match semantics")
        return
    editor.gameplay_ibd_by_id["ts_synthetic"]["status"] = "different_payload"
    editor._refresh_gameplay_script_list()
    if not editor.gameplay_list.get_item_text(0).begins_with("[IBD differs]"):
        _fail("Content mismatch was incorrectly presented as exact evidence")
        return
    # The same Scripts tab also exposes original GameSys 92 compact-int
    # name-table-slot candidates, but explicitly refuses a runtime binding.
    editor.selected_actor = {
        "name": "SyntheticActor__1", "class": "D_527", "export": 7,
        "game_properties": [], "trigger_script_serialized": {
            "interpretation": "index", "items": [1, 2]}}
    editor.gameplay_actor_name_slots_by_export = {
        7: {
            "actor": "SyntheticActor__1", "class": "D_527",
            "export": 7, "status": "numeric_array_redecoded",
            "native_game_property_92_verified": true,
            "numeric_slots_are_name_references_verified": false,
            "candidates": [
                {"raw_compact_integer": 1,
                 "name_at_same_numeric_slot": "TS_Synthetic",
                 "same_name_in_original_tsd_archive": true,
                 "ibd_resource_payload_status": "exact_payload",
                 "actor_runtime_link_verified": false},
                {"raw_compact_integer": 2,
                 "name_at_same_numeric_slot": "NotAScript",
                 "same_name_in_original_tsd_archive": false,
                 "ibd_resource_payload_status": "not_found",
                 "actor_runtime_link_verified": false}
            ]
        }
    }
    editor._inspect_selected_actor_scripts()
    var evidence_text: String = editor.gameplay_details.text
    if (not evidence_text.contains("ORIGINAL GMP GAMEPROPERTY 92")
        or not evidence_text.contains("Raw integer 1")
        or not evidence_text.contains("TS_Synthetic")
        or not evidence_text.contains("ZIP name match")
        or not evidence_text.contains("IBD: exact_payload")
        or not evidence_text.contains("CANDIDATES, not proved FName references")
        or not evidence_text.contains("does NOT verify an actor executes")
        or not evidence_text.contains("No NPC spawning or script assignment")):
        _fail("Actor name-slot inference failed to preserve non-runtime-binding warnings")
        return
    editor.gameplay_actor_name_slots_by_export[7]["actor"] = "ForgedActor"
    editor._inspect_selected_actor_scripts()
    if editor.gameplay_details.text.contains(
            "ORIGINAL GMP GAMEPROPERTY 92"):
        _fail("Forged actor name leaked name-slot inference across source identities")
        return
    editor.free()
    print("DX2Ed original TriggerScript ZIP to IBD and actor name-slot evidence UI: PASS")
    quit(0)
