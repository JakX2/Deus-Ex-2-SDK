extends SceneTree
## P105: independent Godot BSP node Inspector source provenance UI smoke.
## Synthetic GMP bytes only. No retail asset, map writer, BSP edit or collision.
const BSPPanel = preload("res://source_bsp_node_dossier_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(reason: String) -> void:
    push_error("DX2Ed P105 original BSP node panel: " + reason)
    quit(1)


func _synthetic_spans(start: int) -> Array:
    var rows: Array = []
    var positions := start
    var pieces := [
        ["node.candidate_plane_f32_bits", 16],
        ["node.subtree_zone_mask_bits", 32],
        ["node.compact_field_0", 1],
        ["node.compact_field_1", 1],
        ["node.compact_field_2", 1],
        ["node.compact_field_3", 1],
        ["node.compact_field_4", 1],
        ["node.compact_field_5", 1],
        ["node.compact_field_6", 1],
        ["node.compact_field_7", 1],
        ["node.opaque_spatial_f32_bits", 16],
        ["node.opaque_spatial_reserved", 16],
        ["node.zone_candidate_a_u16", 2],
        ["node.zone_candidate_b_u16", 2],
        ["node.vertex_slot_count_u8", 1],
        ["node.opaque_bounded_i32_0", 4],
        ["node.opaque_bounded_i32_1", 4],
        ["node.observed_zero_u32", 4],
        ["node.opaque_last_u32", 4],
    ]
    for item in pieces:
        rows.append({
            "role": item[0], "original_model_relative_offset": positions,
            "byte_count": int(item[1]),
            "source_span_sha256": "a".repeat(64),
            "native_writer_permission": false,
        })
        positions += int(item[1])
    return rows


func _fixture(path: String, sha: String) -> Dictionary:
    var start := 51
    return {
        "schema": "DX2SDK-original-BSP-source-node-dossier-v1",
        "status": "source-original-read-only-node-structure",
        "source_map": path.get_file(), "source_gmp_sha256": sha,
        "original_model_sha256": "b".repeat(64),
        "original_node_count": 3, "original_zone_record_count": 3,
        "original_node_ordinal": 0, "world_model_export": 1,
        "native_model_node_offset": start,
        "native_model_node_record_bytes": 109,
        "source_gmp_model_absolute_offset": 64,
        "source_gmp_node_absolute_offset": 64 + start,
        "candidate_plane_source_f32": [0.0, 0.0, 1.0, 0.0],
        "raw_compact_fields": [0, 0, 0, -1, -1, 2, -1, 0],
        "raw_compact_offsets_in_model": [99, 100, 101, 102, 103, 104, 105, 106],
        "raw_compact_byte_widths": [1,1,1,1,1,1,1,1],
        "source_candidate_zone_u16": [0, 1],
        "source_polygon_vertex_slot_count_u8": 4,
        "node_source_spans": _synthetic_spans(start),
        "original_source_gmp_modified": false,
        "native_BSP_or_Havok_collision_writer_enabled": false,
        "native_surface_material_uv_binding_verified": false,
        "compact_field2_native_surface_id_authenticated": false,
        "native_vertex_xyz_pool_recovered": false,
        "retail_runtime_verified": false,
        "original_model_exact_noop_verified": true,
        "original_model_full_span_ledger_verified": true,
    }


func _run() -> void:
    var scratch := ProjectSettings.globalize_path("user://p105_bsp_node_fixture")
    if DirAccess.make_dir_recursive_absolute(scratch) != OK:
        _fail("Source-only synthetic fixture folder cannot be created")
        return
    var gmp := scratch.path_join("Synthetic_original.gmp")
    var file := FileAccess.open(gmp, FileAccess.WRITE)
    if file == null:
        _fail("Cannot stage synthetic immutable GMP sentinel")
        return
    file.store_buffer("SOURCE_ONLY_SYNTHETIC_GMP_SENTINEL".to_utf8_buffer())
    file.close()
    var sha := FileAccess.get_sha256(gmp)
    var panel := BSPPanel.new()
    root.add_child(panel)
    panel.initialize()
    if panel.visible or not panel.last_report.is_empty():
        _fail("Original BSP panel opened without a pinned source")
        return
    if not panel.configure_original(gmp, sha):
        _fail("Valid synthetic original-GMP SHA context refused")
        return
    var record := _fixture(gmp, sha)
    if (not panel.visible or not panel.accept_verified_report(record)
        or not panel.details.text.contains("Node #0 / 3")
        or not panel.details.text.contains("surface ID candidate ONLY")
        or not panel.details.text.contains("UNAVAILABLE")
        or panel.inspect_button.disabled):
        _fail("Verified source-only BSP node dossier was not displayed")
        return
    var saved := panel.last_report.duplicate(true)
    for changes in [
        {"source_gmp_sha256": "0".repeat(64)},
        {"native_BSP_or_Havok_collision_writer_enabled": true},
        {"compact_field2_native_surface_id_authenticated": true},
        {"native_surface_material_uv_binding_verified": true},
        {"original_model_full_span_ledger_verified": false},
        {"source_map": "Other.gmp"},
        {"native_model_node_record_bytes": 121},
        {"original_node_ordinal": 30},
        {"candidate_plane_source_f32": [0.0, 0.0, 2.0, 0.0]},
    ]:
        var bad := saved.duplicate(true)
        bad.merge(changes, true)
        if panel.accept_verified_report(bad) or not panel.last_report.is_empty():
            _fail("Unsafe BSP source evidence or native capability accepted: "
                + str(changes))
            return
    var bad_spans := saved.duplicate(true)
    bad_spans["node_source_spans"][4]["byte_count"] = 13
    if panel.accept_verified_report(bad_spans):
        _fail("Overlapping native BSP Model source spans were accepted")
        return
    if not panel.accept_verified_report(saved):
        _fail("Valid dossier could not be reaccepted after refusal")
        return
    panel.node_spin.set_value_no_signal(0)
    panel.inspect_button.pressed.emit()
    if (not panel.last_report.is_empty()
        or panel.last_error.is_empty()
        or FileAccess.get_sha256(gmp) != sha):
        _fail("Fake GMP passed source-original Python BSP parser, or changed file")
        return
    panel.reset_context()
    if panel.visible or not panel.inspect_button.disabled:
        _fail("Original GMP inspector did not clear after source change")
        return
    if panel.configure_original(gmp, "0".repeat(64)):
        _fail("Incorrect original map SHA was accepted")
        return
    panel.queue_free()
    DirAccess.remove_absolute(gmp)
    DirAccess.remove_absolute(scratch)
    print("DX2Ed P105 native original World BSP node inspector SHA/spans/UI PASS")
    quit(0)
