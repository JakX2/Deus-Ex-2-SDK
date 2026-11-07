extends SceneTree
## DX2Ed v0.16 original Actor Property Workbench UI metadata smoke.
## Uses invented identity bytes and strictly synthetic source-type records.
## No original retail GMP, native writer, actual game file, or runtime run.
const WorkbenchPanel = preload("res://multi_native_scalar_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(why: String) -> void:
    push_error("DX2Ed v0.16 original Actor Workbench smoke: " + why)
    quit(1)


func _inventory(sha: String, cache_sha: String, map_name: String) -> Dictionary:
    return {
        "bridge_schema": WorkbenchPanel.BRIDGE_SCHEMA,
        "schema": WorkbenchPanel.SDK_SCHEMA,
        "action": "list",
        "status": "original_staticmeshactor_list",
        "source_map": map_name, "source_sha256": sha,
        "actors_sha256": cache_sha, "source_original_modified": false,
        "runtime_game_verified": false, "native_gamesys_or_script_writer_enabled": false,
        "native_new_actor_creation_enabled": false,
        "source_actor_cache_verified": true, "read_only": true,
        "actors": [
            {"actor": "StaticMeshActor__1", "export": 1, "actor_class": "StaticMeshActor"},
        ],
        "shown_count": 1,
    }


func _fields(sha: String, cache_sha: String, map_name: String) -> Dictionary:
    return {
        "bridge_schema": WorkbenchPanel.BRIDGE_SCHEMA,
        "schema": WorkbenchPanel.SDK_SCHEMA, "action": "fields",
        "status": "original_scalar_field_inventory",
        "source_map": map_name, "source_sha256": sha,
        "actors_sha256": cache_sha, "source_original_modified": false,
        "runtime_game_verified": false, "native_gamesys_or_script_writer_enabled": false,
        "read_only": true, "original_map": map_name, "original_map_sha256": sha,
        "actor_name": "StaticMeshActor__1", "export": 1,
        "fields": [
            {"property": "FixtureFlag", "type": "int32", "source_value": 98765},
            {"property": "FixtureFloat", "type": "float32", "source_value": 12.5},
        ],
    }


func _tag(name: String, ordinal: int, kind: int, size: int,
          category: String, original: Variant = null, editable: bool = false) -> Dictionary:
    return {
        "property": name, "tag_ordinal": ordinal,
        "native_kind": kind,
        "native_kind_label": "IntProperty" if kind == 2 else "FloatProperty" if kind == 4 else "uninterpreted",
        "serialized_payload_size": size,
        "source_byte_offset": 12 + ordinal * 4,
        "indexed_or_special": false,
        "original_value": original,
        "editable_existing_tag": editable,
        "runtime_effect_verified": false,
        "can_insert_property": false,
        "category": category,
    }


func _catalog(sha: String, cache_sha: String, map_name: String) -> Dictionary:
    var categories := []
    var group_fields := [
        [
            _tag("FixtureFlag", 1, 2, 4, "eligible-original-numeric", 98765, true),
            _tag("FixtureFloat", 2, 4, 4, "eligible-original-numeric", 12.5, true),
        ],
        [_tag("Location", 0, 10, 18, "protected-original")],
        [],
        [],
        [],
        [_tag("OpaqueSourceBlock", 3, 12, 9, "opaque-uninterpreted")],
    ]
    for i in range(WorkbenchPanel.WORKBENCH_CATEGORY_ORDER.size()):
        var fields: Array = group_fields[i]
        categories.append({
            "key": WorkbenchPanel.WORKBENCH_CATEGORY_ORDER[i],
            "label": [
                "Original editable numeric",
                "Protected",
                "Duplicate names",
                "Indexed/special",
                "Unsupported numeric",
                "Opaque",
            ][i],
            "count": fields.size(), "fields": fields,
        })
    return {
        "bridge_schema": WorkbenchPanel.BATCH_BRIDGE_SCHEMA,
        "schema": WorkbenchPanel.WORKBENCH_SCHEMA,
        "action": "catalog", "status": "source-original-actor-property-catalog",
        "source_map": map_name, "source_sha256": sha, "actors_sha256": cache_sha,
        "actor": "StaticMeshActor__1", "export": 1,
        "actor_class": "StaticMeshActor",
        "source_actor_cache_verified": true, "read_only": true,
        "no_map_or_cache_mutation": true,
        "new_tag_insertion_enabled": false,
        "arbitrary_gamesys_editing_enabled": false,
        "gameplay_runtime_verified": false,
        "source_top_level_tag_count": 4,
        "eligible_original_numeric_count": 2,
        "read_only_original_tag_count": 2,
        "categories": categories,
    }


func _run() -> void:
    var srcdir := ProjectSettings.globalize_path("user://actor_workbench_v016_source")
    var privdir := ProjectSettings.globalize_path("user://actor_workbench_v016_private")
    if (DirAccess.make_dir_recursive_absolute(srcdir) != OK or
        DirAccess.make_dir_recursive_absolute(privdir) != OK):
        _fail("Cannot create synthetic source identity area")
        return
    var map := srcdir.path_join("M1_WorkbenchSynthetic.gmp")
    var cache := srcdir.path_join("actors.json")
    var output := privdir.path_join("M1_WorkbenchSynthetic.gmp")
    if FileAccess.file_exists(output):
        DirAccess.remove_absolute(output)
    var a := FileAccess.open(map, FileAccess.WRITE)
    if a == null:
        _fail("Cannot create synthetic original map identity")
        return
    a.store_buffer(PackedByteArray([13, 21, 34, 55]))
    a.close()
    a = FileAccess.open(cache, FileAccess.WRITE)
    a.store_string("invented cache, never retail")
    a.close()
    var sha := FileAccess.get_sha256(map).to_lower()
    var cache_sha := FileAccess.get_sha256(cache).to_lower()
    var worker_script := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_multi_scalar_worker.py")
    var panel := WorkbenchPanel.new()
    get_root().add_child(panel)
    if not panel.configure_original(map, cache, sha, worker_script):
        _fail("Original source+cache identity cannot be pinned")
        return
    if not panel.accept_actor_inventory(_inventory(sha, cache_sha, map.get_file())):
        _fail("Original positioned source actor inventory rejected")
        return
    panel.chosen_actor_index = 0
    if not panel.accept_original_fields(_fields(sha, cache_sha, map.get_file())):
        _fail("Original 4-byte numeric tag inventory rejected")
        return
    var doc := _catalog(sha, cache_sha, map.get_file())
    if not panel.accept_original_property_catalog(doc):
        _fail("Valid category grouped original tag catalog rejected")
        return
    if (panel.property_catalog.get("source_top_level_tag_count") != 4
        or panel.source_property_tree.get_root() == null):
        _fail("Source-only original property tree was not created")
        return
    var root := panel.source_property_tree.get_root()
    var first_section := root.get_first_child()
    if first_section == null or first_section.get_child_count() != 2:
        _fail("Original editable native numeric tags not present in category")
        return
    var first_field := first_section.get_first_child()
    if (first_field.get_text(0).find("FixtureFlag") < 0
        or first_field.get_text(2).find("Eligible original") < 0):
        _fail("Source-authored numeric source value or eligibility not displayed")
        return
    first_field.select(0)
    panel._property_tree_selected()
    if panel.chosen_field_index != 0:
        _fail("Clicking original eligible numeric tag did not select a typed editor")
        return
    panel.field_value.value = 123456
    if not panel.stage_selected():
        _fail("Original numeric source field could not stage from the workbench")
        return
    root = panel.source_property_tree.get_root()
    first_field = root.get_first_child().get_first_child()
    if first_field.get_text(2) != "STAGED -> 123456":
        _fail("Source-vs-staged comparison did not reflect the selected property")
        return
    # Unrecognized or protected native tags must NEVER grant edit eligibility.
    for action in ("wrong-sha", "claim-new-tags", "protected-editable",
                   "wrong-original", "duplicate-ordinal", "wrong-count"):
        var forged := doc.duplicate(true)
        match action:
            "wrong-sha":
                forged["source_sha256"] = "0".repeat(64)
            "claim-new-tags":
                forged["new_tag_insertion_enabled"] = true
            "protected-editable":
                forged["categories"][1]["fields"][0]["editable_existing_tag"] = true
            "wrong-original":
                forged["categories"][0]["fields"][0]["original_value"] = 99999
            "duplicate-ordinal":
                forged["categories"][0]["fields"][1]["tag_ordinal"] = 1
            "wrong-count":
                forged["source_top_level_tag_count"] = 3
        if panel.accept_original_property_catalog(forged):
            _fail("Forged original native tag catalog accepted: " + action)
            return
        if panel.property_catalog.get("source_top_level_tag_count") != 4:
            _fail("Rejected native catalog corrupted prior source-authenticated data")
            return
    if panel.batch_request(output) != {}:
        _fail("One native staged numeric field enabled 2–8 batch GMP writing")
        return
    a = FileAccess.open(cache, FileAccess.WRITE)
    a.store_string("invented altered cache")
    a.close()
    if panel.batch_request(output) != {}:
        _fail("Tampered actors.json failed to disarm batch GMP output")
        return
    panel.reset_context()
    if (not panel.property_catalog.is_empty() or
        panel.source_property_tree.get_root() != null or
        not panel.staged.is_empty() or
        not panel.batch_button.disabled):
        _fail("Reset left stale original source Actor tag evidence available")
        return
    if FileAccess.file_exists(output):
        _fail("Read-only property browser wrote a native GMP")
        return
    panel.queue_free()
    DirAccess.remove_absolute(map)
    DirAccess.remove_absolute(cache)
    print("DX2Ed v0.16 source-original Actor Workbench property tree/staged comparison PASS")
    quit(0)
