extends SceneTree
## Synthetic original mission/KERNEL resource diff and sanitized clipboard view.
## No actual retail DX2 binaries or native gameplay script writes.
const View = preload("res://mission_kernel_script_view.gd")
const Main = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(reason: String) -> void:
    push_error("DX2Ed mission/Kernel original script resource comparison: " + reason)
    quit(1)

func _profile(equal: bool, offset: int = -1, source_bytes: int = 20,
        target_bytes: int = 20) -> Dictionary:
    return {
        "byte_equal": equal,
        "left_size": source_bytes, "right_size": target_bytes,
        "same_size": source_bytes == target_bytes,
        "first_difference_offset": null if equal else offset,
        "common_prefix_bytes": source_bytes if equal else offset,
        "common_suffix_bytes": source_bytes if equal else 2,
        "overlapping_different_bytes": 0 if equal else 1,
        "different_byte_runs_in_overlap": 0 if equal else 1,
        "size_difference_bytes": target_bytes - source_bytes,
    }

func _sample() -> Dictionary:
    return {
        "schema": View.SCHEMA, "read_only": true,
        "source_map": "C:/SENSITIVE/OwnerMap.gmp",
        "source_map_sha256": "source-private-sha",
        "script_archive_name": "TriggerScript.zip",
        "script_archive_sha256": "secret-zip-sha",
        "mission_ibd_name": "m1_seattle_club.ibd",
        "mission_ibd_sha256": "secret-mission-sha",
        "kernel_ibd_name": "Kernel_TSDALL.ibd",
        "kernel_ibd_sha256": "secret-kernel-sha",
        "native_actor_script_indices_resolved": false,
        "runtime_actor_script_binding_verified": false,
        "native_script_writer_enabled": false,
        "original_game_assets_modified": false,
        "gameplay_runtime_verified": false,
        "counts": {
            "mission_script_resources": 3, "kernel_script_resources": 3,
            "shared_script_ids": 2, "shared_payload_exact": 1,
            "shared_payload_different": 1, "mission_only": 1,
            "kernel_only": 1, "mission_vs_standalone_exact": 1,
            "mission_vs_standalone_different": 2,
            "kernel_vs_standalone_exact": 2,
            "kernel_vs_standalone_different": 1,
        },
        "source_status_transitions": {
            "exact_payload_to_exact_payload": 1,
            "different_payload_to_exact_payload": 1,
            "different_payload_to_absent": 1,
            "absent_to_different_payload": 1,
        },
        "actor_name_slot_candidates": {
            "status": "verified_original_name_slot_candidates_not_runtime_bindings",
            "native_actor_script_semantics_verified": false,
            "original_actor_script_runtime_links_verified": false,
            "actors_with_verified_numeric_arrays": 3,
            "raw_name_slot_candidate_occurrences": 4,
            "transition_counts": {
                "different_payload_to_exact_payload": 4,
            },
        },
        "script_rows": [
            {
                "script_id": "TS_A",
                "mission_original_tsd_status": "exact_payload",
                "kernel_original_tsd_status": "exact_payload",
                "mission_vs_standalone": _profile(true),
                "kernel_vs_standalone": _profile(true),
                "mission_vs_kernel": _profile(true),
            },
            {
                "script_id": "TS_B",
                "mission_original_tsd_status": "different_payload",
                "kernel_original_tsd_status": "exact_payload",
                "mission_vs_standalone": _profile(false, 4),
                "kernel_vs_standalone": _profile(true),
                "mission_vs_kernel": _profile(false, 4),
            },
            {
                "script_id": "TS_C",
                "mission_original_tsd_status": "different_payload",
                "kernel_original_tsd_status": "absent",
                "mission_vs_standalone": _profile(false, 18, 20, 18),
                "kernel_vs_standalone": null,
                "mission_vs_kernel": null,
            },
            {
                "script_id": "TS_D",
                "mission_original_tsd_status": "absent",
                "kernel_original_tsd_status": "different_payload",
                "mission_vs_standalone": null,
                "kernel_vs_standalone": _profile(false, 16, 20, 18),
                "mission_vs_kernel": null,
            },
        ],
    }

func _run() -> void:
    var sample := _sample()
    var summary := View.summary(sample)
    if (summary.is_empty()
        or not summary.contains("ORIGINAL CLUB / KERNEL TRIGGERSCRIPT COMPARISON")
        or not summary.contains("Shared scripts with different mission/kernel payloads: 1")
        or not summary.contains("byte 4: 1 scripts")
        or not summary.contains("different lengths: 1")
        or not summary.contains("Runtime actor-to-script bindings remain UNVERIFIED")):
        _fail("Original resource diff summary or byte-offset histogram incorrect")
        return
    for secret in ["SENSITIVE", "OwnerMap.gmp", "TS_A", "TS_B",
            "TS_C", "TS_D", "secret-mission-sha"]:
        if summary.contains(secret):
            _fail("Aggregate comparison leaked private original source identity")
            return
    var details := View.script_details(sample, "TS_B")
    if (not details.contains("Script ID: TS_B")
        or not details.contains("First differing payload byte: 4")
        or not details.contains("Different overlapping bytes: 1")
        or not details.contains("do NOT prove runtime actor bindings")):
        _fail("Per-script source diff metadata / runtime warning missing")
        return
    var forged: Dictionary = sample.duplicate(true)
    forged["runtime_actor_script_binding_verified"] = true
    if not View.summary(forged).is_empty():
        _fail("Forged actor runtime claim was rendered")
        return
    forged = sample.duplicate(true)
    forged["counts"]["shared_payload_exact"] = 12
    if not View.summary(forged).is_empty():
        _fail("Contradictory shared resource counts rendered")
        return
    forged = sample.duplicate(true)
    forged["counts"]["mission_only"] = 12
    if not View.summary(forged).is_empty():
        _fail("Contradictory mission-only counts rendered")
        return
    forged = sample.duplicate(true)
    forged["actor_name_slot_candidates"]["original_actor_script_runtime_links_verified"] = true
    if not View.summary(forged).is_empty():
        _fail("Forged native actor name-slot assertion rendered")
        return
    forged = sample.duplicate(true)
    forged["source_status_transitions"]["unknown_to_exact_payload"] = 1
    if not View.summary(forged).is_empty():
        _fail("Unknown source resource status rendered")
        return
    var editor = Main.new()
    editor.gameplay_kernel_comparison = sample
    editor.gameplay_details = TextEdit.new()
    editor.gameplay_list = ItemList.new()
    editor.gameplay_visible = [{"id": "TS_B"}]
    editor.gameplay_list.add_item("TS_B")
    editor.gameplay_list.select(0)
    editor._show_selected_mission_kernel_script_diff()
    if not editor.gameplay_details.text.contains("First differing payload byte: 4"):
        _fail("Godot Scripts panel failed selected original script difference")
        return
    editor.gameplay_kernel_comparison.clear()
    editor._show_selected_mission_kernel_script_diff()
    if not editor.gameplay_details.text.contains(
        "No verified mission/Kernel script comparison"):
        _fail("Stale private Club/Kernel evidence was displayed")
        return
    editor.free()
    print("DX2Ed original Club/mission vs Kernel TSD payload comparison UI: PASS")
    quit(0)
