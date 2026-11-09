extends SceneTree
## DX2Ed v0.53 independent quad camera/workspace smoke.
## Four SubViewports share the editor preview World3D; cameras and grid layers are isolated.
const Guides = preload("res://orthographic_authoring_guides.gd")
const Editor = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed v0.53 multi-view workspace: " + message)
    quit(1)

func _run() -> void:
    var defaults := Guides.default_view_states(Vector3(3, 4, 5), 25.0, 0.8, 0.37)
    if defaults.size() != 4 or Guides.validate_view_states(defaults) == null:
        _fail("Four independent bounded camera defaults were not produced")
        return
    var masks := {}
    for view_id in Guides.VIEW_IDS:
        var mask := Guides.grid_layer_mask(view_id)
        if mask == 0 or masks.has(mask) or Guides.mode_for_view_id(view_id).is_empty():
            _fail("Canonical view IDs or grid layers are not unique")
            return
        masks[mask] = true
    var invalid: Dictionary = defaults.duplicate(true)
    invalid["top"]["target"][0] = INF
    if Guides.validate_view_states(invalid) != null:
        _fail("Non-finite camera target was accepted")
        return
    invalid = defaults.duplicate(true)
    invalid["side"]["distance"] = 0.01
    if Guides.validate_view_states(invalid) != null:
        _fail("Out-of-range camera distance was accepted")
        return
    invalid = defaults.duplicate(true)
    invalid["front"]["extra"] = true
    if Guides.validate_view_states(invalid) != null:
        _fail("Unknown camera state field was accepted")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    if (editor.view_grid == null or editor.view_slots.size() != 4
        or editor.view_containers.size() != 4 or editor.world_views.size() != 4
        or editor.cameras_by_view.size() != 4 or editor.ortho_grid_nodes.size() != 4):
        _fail("Editor did not construct four viewport/camera/grid slots")
        return
    var shared_world: World3D = editor.world_views["perspective"].world_3d
    for view_id in Guides.VIEW_IDS:
        var viewport: SubViewport = editor.world_views[view_id]
        var view_camera: Camera3D = editor.cameras_by_view[view_id]
        var grid: MeshInstance3D = editor.ortho_grid_nodes[view_id]
        if (viewport.world_3d != shared_world
            or view_camera.cull_mask != Guides.viewport_cull_mask(view_id, editor.active_view_id)
            or grid.layers != Guides.grid_layer_mask(view_id)
            or not view_camera.current):
            _fail("Shared world, camera or isolated grid layer failed: " + view_id)
            return
    if (editor.view_layout != Guides.SINGLE_LAYOUT or editor.view_grid.columns != 1
        or not editor.view_slots["perspective"].visible
        or editor.view_slots["top"].visible or editor.view_slots["front"].visible
        or editor.view_slots["side"].visible):
        _fail("Single layout did not show only the active pane")
        return

    editor._set_view_layout(Guides.QUAD_LAYOUT)
    if (editor.view_grid.columns != 2
        or not editor.view_slots["perspective"].visible
        or not editor.view_slots["top"].visible
        or not editor.view_slots["front"].visible
        or not editor.view_slots["side"].visible):
        _fail("Quad layout did not expose all four panes")
        return
    if (editor.ortho_grid_nodes["perspective"].visible
        or not editor.ortho_grid_nodes["top"].visible
        or not editor.ortho_grid_nodes["front"].visible
        or not editor.ortho_grid_nodes["side"].visible):
        _fail("Quad layout did not isolate orthographic grids")
        return
    for view_id in Guides.VIEW_IDS:
        if editor.world_views[view_id].render_target_update_mode != SubViewport.UPDATE_ALWAYS:
            _fail("Visible quad viewport is not rendering: " + view_id)
            return

    editor._activate_view("top", false, false, true)
    for view_id in Guides.VIEW_IDS:
        if editor.cameras_by_view[view_id].cull_mask != Guides.viewport_cull_mask(view_id, "top"):
            _fail("Interactive overlay cull layer did not follow the active Top pane")
            return
    editor.camera_target = Vector3(12, 3, -8)
    editor.orbit_distance = 40.0
    editor._update_camera()
    var top_state: Dictionary = editor.view_states["top"].duplicate(true)
    var top_transform: Transform3D = editor.camera.global_transform
    editor._activate_view("front", true, false)
    editor.camera_target = Vector3(-5, 7, 14)
    editor.orbit_distance = 60.0
    editor._update_camera()
    var front_state: Dictionary = editor.view_states["front"].duplicate(true)
    editor._activate_view("top", true, false)
    if (editor.active_view_id != "top"
        or not editor.camera_target.is_equal_approx(Vector3(12, 3, -8))
        or not editor.camera.global_transform.is_equal_approx(top_transform)
        or editor.view_states["front"] != front_state):
        _fail("Top camera state was contaminated by Front pan/zoom")
        return
    editor._activate_view("front", true, false)
    if (editor.active_view_id != "front"
        or not editor.camera_target.is_equal_approx(Vector3(-5, 7, 14))
        or editor.view_states["top"] != top_state):
        _fail("Front camera state was contaminated by Top pan/zoom")
        return
    editor._set_editor_view_mode(Guides.SIDE)
    if editor.active_view_id != "side" or editor.camera.projection != Camera3D.PROJECTION_ORTHOGONAL:
        _fail("Mode selector did not activate the independent Side camera")
        return
    editor.camera_target = Vector3(21, 2, 9)
    editor.orbit_distance = 75.0
    editor._update_camera()

    editor._set_view_layout(Guides.SINGLE_LAYOUT)
    if (editor.view_grid.columns != 1 or not editor.view_slots["side"].visible
        or editor.view_slots["perspective"].visible or editor.view_slots["top"].visible
        or editor.view_slots["front"].visible):
        _fail("Single layout did not preserve the active Side camera")
        return
    if (editor.world_views["side"].render_target_update_mode != SubViewport.UPDATE_ALWAYS
        or editor.world_views["top"].render_target_update_mode != SubViewport.UPDATE_DISABLED):
        _fail("Hidden viewport rendering was not suspended")
        return

    var workspace := editor._capture_draft_workspace()
    var checked: Variant = editor._validated_draft_workspace(workspace)
    if (checked == null or checked["view_layout"] != Guides.SINGLE_LAYOUT
        or checked["active_view_id"] != "side" or checked["view_states"].size() != 4):
        _fail("Quad workspace camera state failed strict validation")
        return
    var legacy: Variant = editor._validated_draft_workspace({
        "view_mode": Guides.TOP, "grid_step": 2.0, "grid_enabled": false,
    })
    if legacy == null or legacy["view_layout"] != Guides.SINGLE_LAYOUT:
        _fail("Legacy v0.52 workspace migration failed")
        return
    var malicious: Dictionary = workspace.duplicate(true)
    malicious["active_view_id"] = "top"
    if editor._validated_draft_workspace(malicious) != null:
        _fail("Mismatched active view identity was accepted")
        return
    malicious = workspace.duplicate(true)
    malicious["view_states"]["front"]["target"][1] = INF
    if editor._validated_draft_workspace(malicious) != null:
        _fail("Malicious non-finite quad workspace was accepted")
        return

    var draft_dir := ProjectSettings.globalize_path("user://prop_drafts")
    if DirAccess.make_dir_recursive_absolute(draft_dir) != OK:
        _fail("Could not create private workspace smoke directory")
        return
    var draft_path := draft_dir.path_join("quad_workspace_smoke.json")
    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    if not editor._write_private_draft_transaction(
        draft_path, JSON.stringify({"workspace": workspace}, "  ")):
        _fail("Transactional quad workspace save failed")
        return
    var reopened: Variant = JSON.parse_string(FileAccess.get_file_as_string(draft_path))
    if typeof(reopened) != TYPE_DICTIONARY:
        _fail("Private quad workspace JSON could not be reopened")
        return
    var reopened_workspace: Variant = editor._validated_draft_workspace(reopened.get("workspace", {}))
    if reopened_workspace == null:
        _fail("Reopened quad workspace failed strict preflight")
        return
    editor._apply_draft_workspace(reopened_workspace)
    if (editor.view_layout != Guides.SINGLE_LAYOUT or editor.active_view_id != "side"
        or not editor.camera_target.is_equal_approx(Vector3(21, 2, 9))):
        _fail("Private workspace reopen lost independent camera state")
        return
    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor.queue_free()
    print("DX2Ed v0.53 independent quad cameras and private workspace round-trip PASS")
    quit(0)
