extends SceneTree
## DX2Ed v0.18: original actor name/export navigation with invented SHA bytes.
## No retail GMP, no Python writer, no package output.
const ActorNav = preload("res://workbench_actor_navigation.gd")
const Workbench = preload("res://multi_native_scalar_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.18 source actor navigator: " + message)
    quit(1)


func _list(map_name: String, sha: String, cache_sha: String) -> Dictionary:
    var records: Array = []
    for i in range(5):
        records.append({
            "actor":"StaticMeshActor__" + str(i + 1),
            "export":i + 1,
            "actor_class":"StaticMeshActor",
        })
    return {
        "bridge_schema":Workbench.BRIDGE_SCHEMA,
        "schema":Workbench.SDK_SCHEMA,
        "action":"list","status":"original_staticmeshactor_list",
        "source_map":map_name,"source_sha256":sha,
        "actors_sha256":cache_sha,
        "source_original_modified":false,
        "runtime_game_verified":false,
        "native_gamesys_or_script_writer_enabled":false,
        "native_new_actor_creation_enabled":false,
        "source_actor_cache_verified":true,
        "read_only":true,"actors":records,"shown_count":5,
    }


func _fields(map_name: String, sha: String, cache_sha: String,
             name: String, export: int) -> Dictionary:
    return {
        "bridge_schema":Workbench.BRIDGE_SCHEMA,
        "schema":Workbench.SDK_SCHEMA,
        "action":"fields","status":"original_scalar_field_inventory",
        "source_map":map_name,"source_sha256":sha,
        "actors_sha256":cache_sha,
        "source_original_modified":false,
        "runtime_game_verified":false,
        "native_gamesys_or_script_writer_enabled":false,
        "read_only":true,"original_map":map_name,"original_map_sha256":sha,
        "actor_name":name,"export":export,
        "fields":[{"property":"FixtureFlag","type":"int32","source_value":12}],
    }


func _run() -> void:
    var dir := ProjectSettings.globalize_path("user://v018_actor_navigation_original")
    if DirAccess.make_dir_recursive_absolute(dir) != OK:
        _fail("Synthetic original source folder not available")
        return
    var source := dir.path_join("M1_NavInvented.gmp")
    var cache := dir.path_join("actors.json")
    var output := ProjectSettings.globalize_path(
        "user://v018_actor_navigation_private/M1_NavInvented.gmp")
    if DirAccess.make_dir_recursive_absolute(output.get_base_dir()) != OK:
        _fail("Synthetic isolated output folder missing")
        return
    var file := FileAccess.open(source, FileAccess.WRITE)
    if file == null:
        _fail("Cannot build synthetic source identity")
        return
    file.store_buffer(PackedByteArray([11,13,17,19,23]))
    file.close()
    file = FileAccess.open(cache, FileAccess.WRITE)
    if file == null:
        _fail("Cannot build synthetic cache identity")
        return
    file.store_string("invented source actor cache")
    file.close()
    var sha := FileAccess.get_sha256(source).to_lower()
    var cache_sha := FileAccess.get_sha256(cache).to_lower()
    var bridge := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_multi_scalar_worker.py")
    var panel := Workbench.new()
    get_root().add_child(panel)
    if not panel.configure_original(source,cache,sha,bridge):
        _fail("Original SHA-pinned synthetic map/cache identity not accepted")
        return
    if not panel.accept_actor_inventory(_list(source.get_file(),sha,cache_sha)):
        _fail("Original source-positioned actor inventory refused")
        return
    if (panel.visible_actor_indices != [0,1,2,3,4]
        or panel.actor_list.item_count != 5
        or panel.actor_navigation_status.text.find("5/5") < 0):
        _fail("Unfiltered original actor list did not retain original indices")
        return
    if ActorNav.original_index_for_export(
            panel.original_actors,"StaticMeshActor__3",3) != 2:
        _fail("Original actor name+export lookup returned wrong identity")
        return
    if (ActorNav.original_index_for_export(
            panel.original_actors,"StaticMeshActor__3",4) != -1
        or ActorNav.original_index_for_export(
            panel.original_actors,"ForeignActor",3) != -1):
        _fail("Foreign name or mismatched export was accepted")
        return
    panel.actor_search.text = "ACTOR__4"
    panel._actor_search_changed(panel.actor_search.text)
    if (panel.visible_actor_indices != [3]
        or panel._original_index_at(0) != 3
        or panel._original_index_at(1) != -1
        or panel._original_index_at(-1) != -1):
        _fail("Case-insensitive search changed original export/index mapping")
        return
    panel.actor_search.text = "5"
    panel._actor_search_changed(panel.actor_search.text)
    if panel.visible_actor_indices != [4]:
        _fail("Export-number actor search did not identify actor export 5")
        return
    panel.actor_search.text = ""
    panel._actor_search_changed("")
    # Synthetic original field evidence, without starting Python/native writer.
    panel.chosen_actor_index = 0
    if not panel.accept_original_fields(
            _fields(source.get_file(),sha,cache_sha,"StaticMeshActor__1",1)):
        _fail("Original first actor numeric tag source rejected")
        return
    panel._pick_field(0)
    panel.field_value.value = 21
    if not panel.stage_selected():
        _fail("First source-authenticated actor edit could not be staged")
        return
    panel.chosen_actor_index = 3
    if not panel.accept_original_fields(
            _fields(source.get_file(),sha,cache_sha,"StaticMeshActor__4",4)):
        _fail("Fourth original actor numeric field refused")
        return
    panel._pick_field(0)
    panel.field_value.value = 99
    if not panel.stage_selected() or panel.staged.size() != 2:
        _fail("Cross-actor original staged numeric records lost")
        return
    var rows := ActorNav.projected(
        panel.original_actors,panel.staged,"",ActorNav.MODE_STAGED)
    if (rows["visible"] != 2 or rows["rows"][0]["original_index"] != 0
        or rows["rows"][1]["original_index"] != 3
        or rows["rows"][1]["staged_count"] != 1):
        _fail("Staged actor view failed original source index projection")
        return
    panel.actor_mode.select(1)
    panel._actor_mode_changed(1)
    if (panel.visible_actor_indices != [0,3]
        or panel._original_index_at(1) != 3
        or panel.actor_navigation_status.text.find("2/5") < 0):
        _fail("Staged-only list mapped display rows to wrong source actors")
        return
    panel.actor_mode.select(2)
    panel._actor_mode_changed(2)
    if panel.visible_actor_indices != [1,2,4]:
        _fail("Unstaged actor filter included a source actor with staged edits")
        return
    panel.actor_mode.select(0)
    panel._actor_mode_changed(0)
    if (panel._staged_actor_target(panel.staged[1]) != 3
        or panel._staged_actor_target({
            "actor":"StaticMeshActor__4","export":3}) != -1):
        _fail("Jump to staged property accepted wrong original name/export")
        return
    # Filtering never edits any source or clears cross-actor staged data.
    if (panel.staged.size() != 2 or panel.batch_request(output).get(
        "rows",[]).size() != 2 or FileAccess.file_exists(output)):
        _fail("Actor filters changed original staged data or wrote a GMP")
        return
    var forgery := _list(source.get_file(),sha,cache_sha)
    forgery["actors_sha256"] = "0".repeat(64)
    if panel.accept_actor_inventory(forgery):
        _fail("Forged source cache SHA accepted to replace navigation records")
        return
    if panel.staged.size() != 2:
        _fail("Rejected source inventory erased authenticated staged edits")
        return
    file = FileAccess.open(cache,FileAccess.WRITE)
    file.store_string("changed original source actor cache")
    file.close()
    if panel._staged_actor_target(panel.staged[1]) != -1:
        _fail("Stale actors.json permitted jump to source actor")
        return
    if not panel.batch_request(output).is_empty():
        _fail("Stale actor cache permitted output")
        return
    panel.reset_context()
    if (not panel.visible_actor_indices.is_empty()
        or not panel.original_actors.is_empty()
        or not panel.staged.is_empty()
        or panel.actor_list.item_count != 0
        or not panel.batch_button.disabled):
        _fail("Original actor navigation or staging survived source reset")
        return
    panel.queue_free()
    DirAccess.remove_absolute(source)
    DirAccess.remove_absolute(cache)
    print("DX2Ed v0.18 invented actor navigation/export mapping and staged jump PASS")
    quit(0)
