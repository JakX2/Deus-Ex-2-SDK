extends SceneTree
## v0.19 DX2Ed: invented original scene handoff + guarded workbench identity.
## No retail GMP bytes, no native actor writes and no renderer game assertion.
const Bridge = preload("res://scene_actor_workbench_bridge.gd")
const Workbench = preload("res://multi_native_scalar_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.19 viewport source-actor handoff: " + message)
    quit(1)


func _inventory(map_name: String, sha: String, cache_sha: String) -> Dictionary:
    return {
        "bridge_schema": Workbench.BRIDGE_SCHEMA,
        "schema": Workbench.SDK_SCHEMA,
        "action": "list", "status": "original_staticmeshactor_list",
        "source_map": map_name, "source_sha256": sha,
        "actors_sha256": cache_sha,
        "source_original_modified": false,
        "runtime_game_verified": false,
        "native_gamesys_or_script_writer_enabled": false,
        "native_new_actor_creation_enabled": false,
        "source_actor_cache_verified": true, "read_only": true,
        "shown_count": 2,
        "actors": [
            {"actor":"StaticMeshActor__1", "export":1,
             "actor_class":"StaticMeshActor"},
            {"actor":"StaticMeshActor__7", "export":7,
             "actor_class":"StaticMeshActor"},
        ],
    }


func _run() -> void:
    var source_dir := ProjectSettings.globalize_path("user://v019_viewport_original")
    if DirAccess.make_dir_recursive_absolute(source_dir) != OK:
        _fail("Cannot create invented source identity directory")
        return
    var map := source_dir.path_join("M1_ViewportInvented.gmp")
    var cache := source_dir.path_join("actors.json")
    var file := FileAccess.open(map, FileAccess.WRITE)
    if file == null:
        _fail("Cannot create invented map identity bytes")
        return
    file.store_buffer(PackedByteArray([31, 41, 59, 26]))
    file.close()
    file = FileAccess.open(cache, FileAccess.WRITE)
    if file == null:
        _fail("Cannot create invented source cache identity bytes")
        return
    file.store_string("invented original actor cache, no game data")
    file.close()
    var sha := FileAccess.get_sha256(map).to_lower()
    var cache_sha := FileAccess.get_sha256(cache).to_lower()
    var actor := {
        "name":"StaticMeshActor__7", "export":7, "class":"StaticMeshActor",
    }
    var valid := Bridge.candidate(
        actor, actor.duplicate(true), "StaticMeshActor__7", 1,
        map.get_file(), map.get_file(), sha, sha, cache, cache)
    if (valid.get("actor") != "StaticMeshActor__7"
        or valid.get("export") != 7
        or valid.get("source_sha256") != sha
        or valid.get("source_map") != map.get_file()):
        _fail("Single original scene actor did not produce a strict source identity")
        return
    var panel := Workbench.new()
    get_root().add_child(panel)
    var worker := ProjectSettings.globalize_path(
        "res://backend/dx2_sdk_multi_scalar_worker.py")
    if not panel.configure_original(map, cache, sha, worker):
        _fail("Pinned invented owner GMP and actors cache were refused")
        return
    if not panel.accept_actor_inventory(_inventory(map.get_file(),sha,cache_sha)):
        _fail("Source-authenticated actor inventory refused")
        return
    if (panel._original_viewport_index(valid) != 1
        or panel._original_viewport_index({
            **valid, "export":1}) != -1
        or panel._original_viewport_index({
            **valid, "source_sha256":"0".repeat(64)}) != -1):
        _fail("Original name/export/SHA was not enforced at Workbench destination")
        return
    panel.actor_search.text = "Original not listed"
    panel._actor_search_changed(panel.actor_search.text)
    if not panel.visible_actor_indices.is_empty():
        _fail("Actor filter did not hide source selection")
        return
    if panel._original_viewport_index(valid) != 1:
        _fail("Filtered actor list falsely changed authenticated source index")
        return
    var foreign := actor.duplicate(true)
    var candidates := [
        [foreign, foreign, "StaticMeshActor__7", 2, sha, sha],
        [foreign, foreign, "StaticMeshActor__7", 0, sha, sha],
        [foreign, foreign, "BSP_mesh", 1, sha, sha],
        [foreign, foreign, "StaticMeshActor__7", 1, "0".repeat(64), sha],
        [foreign, foreign, "StaticMeshActor__7", 1, sha, "f".repeat(64)],
    ]
    for args in candidates:
        var got := Bridge.candidate(
            args[0], args[1], args[2], args[3],
            map.get_file(), map.get_file(), args[4], args[5], cache, cache)
        if not got.is_empty():
            _fail("Unverified viewport actor/selection/source hash accepted")
            return
    for key in ["draft", "is_draft", "draft_clone", "is_clone", "new_actor"]:
        var fake := actor.duplicate(true)
        fake[key] = true
        if not Bridge.candidate(
            fake, actor, "StaticMeshActor__7", 1, map.get_file(),
            map.get_file(), sha, sha, cache, cache).is_empty():
            _fail("Draft scene actor marker accepted: " + key)
            return
    var wrong := actor.duplicate(true)
    wrong["class"] = "Light"
    if not Bridge.candidate(
        wrong, actor, "StaticMeshActor__7", 1, map.get_file(),
        map.get_file(), sha, sha, cache, cache).is_empty():
        _fail("Native Light selection gained unauthorized StaticMesh scalar editing")
        return
    wrong = actor.duplicate(true)
    wrong["export"] = 1
    if not Bridge.candidate(
        wrong, actor, "StaticMeshActor__7", 1, map.get_file(),
        map.get_file(), sha, sha, cache, cache).is_empty():
        _fail("Scene actor export mismatch accepted")
        return
    wrong = actor.duplicate(true)
    wrong["name"] = "StaticMeshActor__1"
    if not Bridge.candidate(
        wrong, actor, "StaticMeshActor__7", 1, map.get_file(),
        map.get_file(), sha, sha, cache, cache).is_empty():
        _fail("Scene actor name mismatch accepted")
        return
    if not Bridge.candidate(
        actor, actor, "StaticMeshActor__7", 1, map.get_file(),
        "Different.gmp", sha, sha, cache, cache).is_empty():
        _fail("Wrong owner GMP basename accepted")
        return
    if not Bridge.candidate(
        actor, actor, "StaticMeshActor__7", 1, map.get_file(),
        map.get_file(), sha, sha, cache, source_dir.path_join("other.json")).is_empty():
        _fail("Wrong private actors.json owner accepted")
        return
    if not panel.request_viewport_actor({
        "actor":"ForeignActor", "export":7,
        "source_map":map.get_file(), "source_sha256":"0".repeat(64)}):
        pass # Correctly refused; tests no actor field import or native write.
    else:
        _fail("Foreign source-SHA actor request unexpectedly queued")
        return
    file = FileAccess.open(cache, FileAccess.WRITE)
    file.store_string("invented modified cache bytes")
    file.close()
    if (panel._original_viewport_index(valid) != -1
        or panel.request_viewport_actor(valid)):
        _fail("Stale original cache permitted scene-to-workbench navigation")
        return
    panel.reset_context()
    if (not panel.pending_viewport_request.is_empty()
        or not panel.original_actors.is_empty()
        or not panel.visible_actor_indices.is_empty()):
        _fail("Map context reset did not invalidate viewport navigation")
        return
    panel.queue_free()
    DirAccess.remove_absolute(map)
    DirAccess.remove_absolute(cache)
    print("DX2Ed v0.19 invented viewport source actor/export Workbench SHA handoff PASS")
    quit(0)
