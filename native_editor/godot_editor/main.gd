extends Control
## DX2Ed native viewer: a READ-ONLY Godot 4 GLB + GMP actor inspector.
## Can open an original DX2 .gmp using the bundled read-only Python backend.
## No runtime game assets bundled. Exports are cached outside the game folder.

var world_view: SubViewport
var view_container: SubViewportContainer
var world_root: Node3D
var scene_root: Node3D
var camera: Camera3D
var actor_list: ItemList
var search_box: LineEdit
var category_filter: OptionButton
var hierarchy_tree: Tree
var hierarchy_items: Dictionary = {}
var hierarchy_syncing := false
var inspector_title: Label
var inspector_details: Label
var inspector_transform_section: VBoxContainer
var inspector_spins: Dictionary = {}
var inspector_syncing := false
var inspector: TextEdit
var status_label: Label
var glb_dialog: FileDialog
var json_dialog: FileDialog
var gmp_dialog: FileDialog
var bundle_dialog: FileDialog
var club_zip_dialog: FileDialog
var shared_zip_dialog: FileDialog
var system_zip_dialog: FileDialog
var chosen_ibd: String = ""
var chosen_shared_zip: String = ""
var chosen_system_zip: String = ""
var chosen_system_path: String = ""
var preview_club_stairs := false
var last_gmp_path: String = ""
var prop_edit_step: SpinBox
var original_mesh_transforms: Dictionary = {}
var draft_prop_copies: Dictionary = {}
var draft_prop_sources: Dictionary = {}
var next_prop_copy_id := 1
# In-memory session history. Each operation stores only edited actor transforms
# and draft clones, never the large imported GLB or retail resources.
const HISTORY_LIMIT := 100
var undo_stack: Array[Dictionary] = []
var redo_stack: Array[Dictionary] = []
var gizmo_undo_before: Dictionary = {}
var undo_button: Button
var redo_button: Button
var restore_all_dialog: ConfirmationDialog
var build_thread: Thread = null
var actors: Array = []
var visible_actors: Array = []
var actors_by_name: Dictionary = {}
var meshes_by_actor: Dictionary = {}
var all_mesh_instances: Array[MeshInstance3D] = []
# Faces are shared by instances of the same imported mesh; cache per mesh resource.
var pick_faces_by_mesh: Dictionary = {}
var selected_diagnostic: String = ""
var selected_mesh: MeshInstance3D
# Multi-selection preserves each original material overlay independently.
var selected_meshes: Dictionary = {}   # name -> MeshInstance3D
var selection_original_overlays: Dictionary = {} # name -> Material or null
var gizmo_start_transforms: Dictionary = {} # name -> Transform3D
var selected_actor: Dictionary = {}
var selected_overlay_original: Material
var overlay_material: StandardMaterial3D
var current_folder: String = ""
var current_source_map_name: String = ""
var camera_target := Vector3.ZERO
var orbit_yaw := 0.8
var orbit_pitch := 0.37
var orbit_distance := 25.0
var dragging := false
var drag_mode := ""
var drag_distance := 0.0
var fly_looking := false
var fly_speed := 8.0
var editor_tool := "move"  # W/E/R
var gizmo_root: Node3D
var gizmo_handles: Array[MeshInstance3D] = []
var gizmo_drag_axis := Vector3.ZERO
var gizmo_drag_pivot := Vector3.ZERO
var gizmo_start_transform := Transform3D.IDENTITY
var gizmo_drag_start_scalar := 0.0
var gizmo_drag_start_screen := Vector2.ZERO
var gizmo_drag_active := false
var scene_bounds := AABB()
var scene_bounds_valid := false
var mesh_count := 0

func _ready() -> void:
    _make_ui()
    _make_world()
    _make_material()
    _update_camera()
    status_label.text = "Ready. Open an original DX2 .gmp map (Python 3 required) or an existing GLB."
    var args := OS.get_cmdline_user_args()
    if args.size() > 0:
        call_deferred("open_export_folder", str(args[0]))

func _make_ui() -> void:
    var base := VBoxContainer.new()
    base.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    add_child(base)
    var toolbar := HBoxContainer.new()
    base.add_child(toolbar)
    var gmp_btn := Button.new()
    gmp_btn.text = "Open DX2 map (.gmp)"
    gmp_btn.tooltip_text = "Automatically convert the original DX2 map and matching IBD resources to a private cache"
    gmp_btn.pressed.connect(func(): gmp_dialog.popup_centered_ratio(0.78))
    toolbar.add_child(gmp_btn)
    var bundle_btn := Button.new()
    bundle_btn.text = "IBD override..."
    bundle_btn.tooltip_text = "Optional: select a matching .ibd bundle when the automatic lookup cannot find it"
    bundle_btn.pressed.connect(func(): bundle_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(bundle_btn)
    var demo_btn := Button.new()
    demo_btn.text = "Load demo cubes"
    demo_btn.pressed.connect(func(): load_glb(ProjectSettings.globalize_path("res://demo/scene.glb")))
    toolbar.add_child(demo_btn)
    var load_btn := Button.new()
    load_btn.text = "Open exported GLB"
    load_btn.pressed.connect(func(): glb_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(load_btn)
    var data_btn := Button.new()
    data_btn.text = "Load actors.json"
    data_btn.pressed.connect(func(): json_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(data_btn)
    var frame_btn := Button.new()
    frame_btn.text = "Frame scene"
    frame_btn.pressed.connect(frame_whole_scene)
    toolbar.add_child(frame_btn)
    var focus_btn := Button.new()
    focus_btn.text = "Focus actor"
    focus_btn.pressed.connect(focus_selected)
    toolbar.add_child(focus_btn)
    var copy_btn := Button.new()
    copy_btn.text = "Copy mesh info"
    copy_btn.tooltip_text = "Copy selected DX2 actor/mesh name, original rotation and world bounds for reporting an export issue"
    copy_btn.pressed.connect(_copy_selection_details)
    toolbar.add_child(copy_btn)
    var hint := Label.new()
    hint.text = "  Ctrl+click multi-select  |  RMB+WASD fly  |  Alt+LMB orbit  |  F focus"
    toolbar.add_child(hint)

    var zip_bar := HBoxContainer.new()
    base.add_child(zip_bar)
    var shared_zip_btn := Button.new()
    shared_zip_btn.text = "Shared ZIP..."
    shared_zip_btn.tooltip_text = "Select maps.zip containing Kernel_GFXALL and MainMenu_GFXALL bundles"
    shared_zip_btn.pressed.connect(func(): shared_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(shared_zip_btn)
    var system_zip_btn := Button.new()
    system_zip_btn.text = "System ZIP... (optional)"
    system_zip_btn.tooltip_text = "Select System.zip for game-system actor metadata"
    system_zip_btn.pressed.connect(func(): system_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(system_zip_btn)
    var club_zip_btn := Button.new()
    club_zip_btn.text = "Open DX2 map ZIP..."
    club_zip_btn.tooltip_text = "Safely stage any ZIP with exactly one GMP and one mission IBD (Seattle Hub/Club), then import the map"
    club_zip_btn.pressed.connect(func(): club_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(club_zip_btn)
    var stairs_toggle := CheckBox.new()
    stairs_toggle.text = "Experimental stair Roll"
    stairs_toggle.tooltip_text = "Compare the unmodified retail transform preview with a reversible Seattle Club-only test. Reloads the level."
    stairs_toggle.button_pressed = false
    stairs_toggle.toggled.connect(_set_stair_preview)
    zip_bar.add_child(stairs_toggle)
    var zip_hint := Label.new()
    zip_hint.text = "  Select shared resources, optional System, then a mission ZIP"
    zip_bar.add_child(zip_hint)

    var prop_bar := HBoxContainer.new()
    base.add_child(prop_bar)
    var draft_label := Label.new()
    draft_label.text = "Prop drafts:"
    prop_bar.add_child(draft_label)
    var transform_heading := Label.new()
    transform_heading.text = "  Tools:"
    prop_bar.add_child(transform_heading)
    for definition in [["Move W", "move"], ["Rotate E", "rotate"], ["Scale R", "scale"]]:
        var tool_button := Button.new()
        tool_button.text = definition[0]
        tool_button.tooltip_text = "Choose 3D axis gizmo; keyboard shortcut " + definition[0].right(1)
        tool_button.pressed.connect(_set_editor_tool.bind(definition[1]))
        prop_bar.add_child(tool_button)
    var duplicate_button := Button.new()
    duplicate_button.text = "Duplicate"
    duplicate_button.tooltip_text = "Clone selected rendered prop in the viewer. Does not write the GMP."
    duplicate_button.pressed.connect(_duplicate_selected_prop)
    prop_bar.add_child(duplicate_button)
    prop_edit_step = SpinBox.new()
    prop_edit_step.min_value = 0.05
    prop_edit_step.max_value = 10.0
    prop_edit_step.step = 0.05
    prop_edit_step.value = 0.25
    prop_edit_step.custom_minimum_size.x = 83
    prop_edit_step.tooltip_text = "Distance for X/Y/Z buttons, in Godot metres"
    prop_bar.add_child(prop_edit_step)
    for entry in [
        ["X-", Vector3(-1, 0, 0)], ["X+", Vector3(1, 0, 0)],
        ["Y-", Vector3(0, -1, 0)], ["Y+", Vector3(0, 1, 0)],
        ["Z-", Vector3(0, 0, -1)], ["Z+", Vector3(0, 0, 1)]
    ]:
        var move_button := Button.new()
        move_button.text = str(entry[0])
        move_button.tooltip_text = "Move selected prop along Godot world axis"
        move_button.pressed.connect(_move_selected_prop.bind(entry[1]))
        prop_bar.add_child(move_button)
    for angle in [-15.0, 15.0]:
        var rotate_button := Button.new()
        rotate_button.text = "Turn " + str(int(angle)) + "°"
        rotate_button.pressed.connect(_rotate_selected_prop.bind(angle))
        prop_bar.add_child(rotate_button)
    var reset_button := Button.new()
    reset_button.text = "Reset / Delete copy"
    reset_button.pressed.connect(_reset_selected_prop)
    prop_bar.add_child(reset_button)
    undo_button = Button.new()
    undo_button.text = "Undo"
    undo_button.tooltip_text = "Undo the last prop edit (Ctrl+Z)"
    undo_button.pressed.connect(_undo_edit)
    prop_bar.add_child(undo_button)
    redo_button = Button.new()
    redo_button.text = "Redo"
    redo_button.tooltip_text = "Redo the last undone edit (Ctrl+Y or Ctrl+Shift+Z)"
    redo_button.pressed.connect(_redo_edit)
    prop_bar.add_child(redo_button)
    var restore_all_button := Button.new()
    restore_all_button.text = "Restore All"
    restore_all_button.tooltip_text = "Restore every original prop transform and delete draft copies. Also clears saved draft edits."
    restore_all_button.pressed.connect(func(): restore_all_dialog.popup_centered())
    prop_bar.add_child(restore_all_button)
    _refresh_history_buttons()
    var save_button := Button.new()
    save_button.text = "Save draft"
    save_button.tooltip_text = "Save only the preview changes as JSON in user://. Never write the game files."
    save_button.pressed.connect(_save_prop_draft)
    prop_bar.add_child(save_button)
    var reload_button := Button.new()
    reload_button.text = "Load draft"
    reload_button.pressed.connect(_load_prop_draft)
    prop_bar.add_child(reload_button)

    var horizontal := HSplitContainer.new()
    horizontal.size_flags_vertical = Control.SIZE_EXPAND_FILL
    base.add_child(horizontal)
    var sidebar := VBoxContainer.new()
    sidebar.custom_minimum_size = Vector2(250, 0)
    horizontal.add_child(sidebar)
    var actor_heading := Label.new()
    actor_heading.text = "DX2 Actors"
    sidebar.add_child(actor_heading)
    search_box = LineEdit.new()
    search_box.placeholder_text = "Filter name, class, mesh..."
    search_box.text_changed.connect(func(_value): _refresh_actor_list())
    sidebar.add_child(search_box)
    category_filter = OptionButton.new()
    for choice in [
        "All actors", "Static meshes", "Brushes", "Lights",
        "Volumes / triggers", "Item candidates", "Physics candidates",
        "Gameplay / other"
    ]:
        category_filter.add_item(choice)
    category_filter.selected = 0
    category_filter.item_selected.connect(func(_index): _refresh_actor_list())
    sidebar.add_child(category_filter)
    hierarchy_tree = Tree.new()
    hierarchy_tree.columns = 1
    hierarchy_tree.hide_root = false
    hierarchy_tree.select_mode = Tree.SELECT_MULTI
    hierarchy_tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
    hierarchy_tree.multi_selected.connect(_hierarchy_multi_selected)
    hierarchy_tree.item_activated.connect(func(): focus_selected())
    sidebar.add_child(hierarchy_tree)
    # Retain the old list as a hidden compatibility model for existing picker
    # diagnostics; the new Hierarchy is the visible selection surface.
    actor_list = ItemList.new()
    actor_list.visible = false
    actor_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    actor_list.select_mode = ItemList.SELECT_MULTI
    actor_list.multi_selected.connect(_actor_list_multi_selected)
    actor_list.item_activated.connect(func(_index): focus_selected())
    sidebar.add_child(actor_list)

    var scene_pane := VBoxContainer.new()
    scene_pane.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    scene_pane.custom_minimum_size.x = 440
    horizontal.add_child(scene_pane)
    var scene_label := Label.new()
    scene_label.text = "Scene  |  Godot preview, read-only source assets"
    scene_pane.add_child(scene_label)
    view_container = SubViewportContainer.new()
    view_container.stretch = true
    view_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
    view_container.custom_minimum_size = Vector2(400, 360)
    scene_pane.add_child(view_container)

    var inspector_pane := VBoxContainer.new()
    inspector_pane.custom_minimum_size.x = 285
    inspector_pane.size_flags_vertical = Control.SIZE_EXPAND_FILL
    horizontal.add_child(inspector_pane)
    var heading := Label.new()
    heading.text = "Inspector"
    inspector_pane.add_child(heading)
    inspector_title = Label.new()
    inspector_title.text = "Nothing selected"
    inspector_pane.add_child(inspector_title)
    inspector_details = Label.new()
    inspector_details.text = "Select an actor or rendered mesh in the Scene or Hierarchy."
    inspector_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    inspector_pane.add_child(inspector_details)
    inspector_transform_section = VBoxContainer.new()
    inspector_pane.add_child(inspector_transform_section)
    var transform_heading := Label.new()
    transform_heading.text = "Transform  |  Preview only"
    inspector_transform_section.add_child(transform_heading)
    var transform_grid := GridContainer.new()
    transform_grid.columns = 4
    inspector_transform_section.add_child(transform_grid)
    for mode in ["Position", "Rotation", "Scale"]:
        var label := Label.new()
        label.text = mode
        transform_grid.add_child(label)
        for axis in range(3):
            var spin := SpinBox.new()
            spin.min_value = -1000000.0
            spin.max_value = 1000000.0
            spin.step = 0.01 if mode != "Rotation" else 1.0
            spin.custom_minimum_size.x = 67
            spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
            spin.tooltip_text = mode + " " + ["X", "Y", "Z"][axis] + " (Godot coordinates)"
            spin.value_changed.connect(_inspector_transform_changed.bind(mode, axis))
            transform_grid.add_child(spin)
            inspector_spins[mode + str(axis)] = spin
    var property_heading := Label.new()
    property_heading.text = "Source actor details (read-only)"
    inspector_pane.add_child(property_heading)
    inspector = TextEdit.new()
    inspector.editable = false
    inspector.size_flags_vertical = Control.SIZE_EXPAND_FILL
    inspector.text = "Select an actor to inspect original DX2 properties."
    inspector_pane.add_child(inspector)
    inspector_transform_section.visible = false
    restore_all_dialog = ConfirmationDialog.new()
    restore_all_dialog.title = "Restore all prop edits?"
    restore_all_dialog.dialog_text = "Restore all original prop transforms and remove every draft copy?\nThis also clears the saved draft for this map.\nYou can undo during this session."
    restore_all_dialog.confirmed.connect(_restore_all_edits)
    add_child(restore_all_dialog)
    var bottom := PanelContainer.new()
    base.add_child(bottom)
    status_label = Label.new()
    status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    bottom.add_child(status_label)

    gmp_dialog = FileDialog.new()
    gmp_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gmp_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    gmp_dialog.filters = PackedStringArray(["*.gmp ; Deus Ex Invisible War map"])
    gmp_dialog.file_selected.connect(_open_gmp_file)
    add_child(gmp_dialog)
    bundle_dialog = FileDialog.new()
    bundle_dialog.access = FileDialog.ACCESS_FILESYSTEM
    bundle_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    bundle_dialog.filters = PackedStringArray(["*.ibd ; Invisible War resource bundle"])
    bundle_dialog.file_selected.connect(_select_ibd)
    add_child(bundle_dialog)
    glb_dialog = FileDialog.new()
    glb_dialog.access = FileDialog.ACCESS_FILESYSTEM
    glb_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    glb_dialog.filters = PackedStringArray(["*.glb ; DX2Ed glTF binary scene"])
    glb_dialog.file_selected.connect(load_glb)
    add_child(glb_dialog)
    json_dialog = FileDialog.new()
    json_dialog.access = FileDialog.ACCESS_FILESYSTEM
    json_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    json_dialog.filters = PackedStringArray(["*.json ; DX2Ed actor metadata"])
    json_dialog.file_selected.connect(load_actors)
    add_child(json_dialog)

    shared_zip_dialog = FileDialog.new()
    shared_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    shared_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    shared_zip_dialog.filters = PackedStringArray(["*.zip ; DX2 shared map resources ZIP"])
    shared_zip_dialog.file_selected.connect(_select_shared_zip)
    add_child(shared_zip_dialog)
    system_zip_dialog = FileDialog.new()
    system_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    system_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    system_zip_dialog.filters = PackedStringArray(["*.zip ; DX2 System ZIP"])
    system_zip_dialog.file_selected.connect(_select_system_zip)
    add_child(system_zip_dialog)
    club_zip_dialog = FileDialog.new()
    club_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    club_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    club_zip_dialog.filters = PackedStringArray(["*.zip ; DX2 Seattle Club ZIP"])
    club_zip_dialog.file_selected.connect(_open_club_zip)
    add_child(club_zip_dialog)

func _select_ibd(path: String) -> void:
    chosen_ibd = path
    status_label.text = "Optional IBD selected: " + path.get_file()

func _open_gmp_file(path: String) -> void:
    # Direct GMP load should not accidentally reuse a System path from a
    # previous ZIP staging session.
    chosen_system_path = ""
    open_gmp(path)

func _set_stair_preview(enabled: bool) -> void:
    preview_club_stairs = enabled
    if build_thread != null:
        status_label.text = "Stair preview changed. Reopen the map after the current import completes."
    elif last_gmp_path != "" and FileAccess.file_exists(last_gmp_path):
        open_gmp(last_gmp_path)
    else:
        status_label.text = "Stair Roll preview: " + ("experimental" if enabled else "original") + ". Open a DX2 map."

func _select_shared_zip(path: String) -> void:
    chosen_shared_zip = path
    status_label.text = "Shared map resources selected: " + path.get_file()

func _select_system_zip(path: String) -> void:
    chosen_system_zip = path
    status_label.text = "Optional System ZIP selected: " + path.get_file()

func _open_club_zip(path: String) -> void:
    if build_thread != null:
        status_label.text = "Already processing a map or archive."
        return
    if chosen_shared_zip.is_empty() or not FileAccess.file_exists(chosen_shared_zip):
        status_label.text = "Choose Shared ZIP (maps.zip) before opening the Club ZIP."
        return
    if not FileAccess.file_exists(path):
        status_label.text = "Club ZIP not found: " + path
        return
    var backend := ProjectSettings.globalize_path("res://backend/dx2_zip_stage.py")
    if not FileAccess.file_exists(backend):
        status_label.text = "ZIP staging script is missing: " + backend
        return
    var cache_root := OS.get_user_data_dir().path_join("zip_staging")
    build_thread = Thread.new()
    status_label.text = "Preparing DX2 mission archives in a private cache..."
    var result := build_thread.start(_run_zip_stage.bind(backend, path, chosen_shared_zip, chosen_system_zip, cache_root))
    if result != OK:
        build_thread = null
        status_label.text = "Could not start ZIP worker: " + error_string(result)

func _run_zip_stage(script: String, club: String, shared: String, system_zip: String, cache_root: String) -> void:
    var args := PackedStringArray([script, "--club", club, "--maps", shared, "--map-name", "auto", "--mission-name", "auto", "--output-root", cache_root])
    if system_zip != "":
        args.append_array(PackedStringArray(["--system", system_zip]))
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(args)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_zip_stage_finished", code, "\n".join(output))

func _zip_stage_finished(code: int, output: String) -> void:
    if build_thread != null:
        build_thread.wait_to_finish()
        build_thread = null
    var parsed: Variant = null
    for line in output.strip_edges().split("\n"):
        var candidate: Variant = JSON.parse_string(line.strip_edges())
        if typeof(candidate) == TYPE_DICTIONARY and candidate.has("status"):
            parsed = candidate
    if code != 0 or typeof(parsed) != TYPE_DICTIONARY or parsed.get("status") != "ok":
        var description := "ZIP staging failed. Verify source ZIP files and Python installation."
        if typeof(parsed) == TYPE_DICTIONARY:
            description = str(parsed.get("message", description))
        status_label.text = description
        return
    var map_path := str(parsed.get("map", ""))
    if not FileAccess.file_exists(map_path):
        status_label.text = "ZIP staging completed but the map is missing: " + map_path
        return
    chosen_ibd = ""
    var system_value: Variant = parsed.get("system", null)
    chosen_system_path = str(system_value) if typeof(system_value) == TYPE_STRING else ""
    # The existing GMP importer now sees the original Club IBD and the shared
    # IBD packages side by side. Source ZIPs remain untouched.
    open_gmp(map_path)

func open_gmp(path: String) -> void:
    if build_thread != null:
        status_label.text = "Already processing a map. Please finish this load first."
        return
    if not FileAccess.file_exists(path):
        status_label.text = "Map not found: " + path
        return
    var backend := ProjectSettings.globalize_path("res://backend/dx2_native_backend.py")
    if not FileAccess.file_exists(backend):
        status_label.text = "Missing Python backend: " + backend
        return
    last_gmp_path = path
    var cache_root := OS.get_user_data_dir().path_join("map_cache")
    status_label.text = "Processing " + path.get_file() + " ... First load creates a cached 3D scene and actor metadata."
    build_thread = Thread.new()
    var result := build_thread.start(_run_backend.bind(backend, path, cache_root, chosen_ibd, chosen_system_path, preview_club_stairs))
    if result != OK:
        build_thread = null
        status_label.text = "Could not start map worker: " + error_string(result)

func _run_backend(script: String, gmp_path: String, cache_root: String, ibd_path: String, system_path: String, stair_preview: bool) -> void:
    var args := PackedStringArray([script, "--map", gmp_path, "--output-root", cache_root])
    if ibd_path != "":
        args.append_array(PackedStringArray(["--bundle", ibd_path]))
    if system_path != "":
        args.append_array(PackedStringArray(["--system", system_path]))
    if stair_preview:
        args.append("--preview-club-stairs")
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        # On Windows the Python launcher may be on PATH even if python.exe isn't.
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(args)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_backend_finished", code, "\n".join(output))

func _backend_finished(code: int, output: String) -> void:
    if build_thread != null:
        build_thread.wait_to_finish()
        build_thread = null
    var message := ""
    var parsed: Variant = null
    for line in output.strip_edges().split("\n"):
        var record := line.strip_edges()
        if record.begins_with("{"):
            var candidate: Variant = JSON.parse_string(record)
            if typeof(candidate) == TYPE_DICTIONARY and candidate.has("status"):
                parsed = candidate
    if typeof(parsed) == TYPE_DICTIONARY and parsed.get("status") == "ok" and code == 0:
        var scene_path := str(parsed.get("glb", ""))
        var actor_path := str(parsed.get("actors_json", ""))
        if not FileAccess.file_exists(scene_path) or not FileAccess.file_exists(actor_path):
            status_label.text = "Map backend succeeded but output files are missing."
            return
        load_glb(scene_path)
        if scene_root == null:
            return # Keep the descriptive GLB error instead of reporting success.
        # load_glb automatically loads the adjacent actors.json.
        status_label.text = "%s: %d actors, %d meshes (%s). Read-only." % [str(parsed.get("map", "DX2 map")), int(parsed.get("actors", 0)), mesh_count, "cached" if parsed.get("cached", false) else "new export"]
        return
    if typeof(parsed) == TYPE_DICTIONARY and parsed.has("message"):
        message = str(parsed.get("message", ""))
    elif output.strip_edges() != "":
        message = output.strip_edges().substr(0, 400)
    else:
        message = "Python not available. Install Python 3 and ensure python or py is on PATH."
    status_label.text = "Could not open DX2 map: " + message
    push_warning("DX2Ed map importer: " + message)

func _make_world() -> void:
    world_view = SubViewport.new()
    world_view.transparent_bg = false
    world_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    view_container.add_child(world_view)
    world_root = Node3D.new()
    world_root.name = "Scene"
    world_view.add_child(world_root)
    camera = Camera3D.new()
    camera.current = true
    camera.near = 0.05
    camera.far = 100000.0
    world_root.add_child(camera)
    gizmo_root = Node3D.new()
    gizmo_root.name = "EditorGizmo"
    world_root.add_child(gizmo_root)
    _create_transform_gizmo()
    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-45, 25, 0)
    light.light_energy = 1.6
    world_root.add_child(light)
    var env := WorldEnvironment.new()
    var world_environment := Environment.new()
    world_environment.background_mode = Environment.BG_COLOR
    world_environment.background_color = Color(0.12, 0.16, 0.2)
    world_environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    world_environment.ambient_light_color = Color(0.75, 0.8, 0.9)
    world_environment.ambient_light_energy = 1.1
    env.environment = world_environment
    world_root.add_child(env)

func _make_material() -> void:
    overlay_material = StandardMaterial3D.new()
    overlay_material.albedo_color = Color(1.0, 0.55, 0.05, 0.28)
    overlay_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    overlay_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    overlay_material.cull_mode = BaseMaterial3D.CULL_DISABLED

func open_export_folder(folder: String) -> void:
    var path := folder.simplify_path().path_join("scene.glb")
    if not FileAccess.file_exists(path):
        status_label.text = "No scene.glb in: " + folder
        return
    load_glb(path)

func load_glb(path: String) -> void:
    if not FileAccess.file_exists(path):
        status_label.text = "File not found: " + path
        return
    _clear_current_scene()
    var document := GLTFDocument.new()
    var gltf_state := GLTFState.new()
    var error := document.append_from_file(path, gltf_state)
    if error != OK:
        status_label.text = "GLB import failed: " + error_string(error) + " | " + path
        return
    var imported := document.generate_scene(gltf_state)
    if imported == null:
        status_label.text = "GLB parsed but scene generation failed: " + path
        return
    scene_root = imported
    world_root.add_child(scene_root)
    _index_meshes(scene_root)
    frame_whole_scene()
    current_folder = path.get_base_dir()
    var actor_path := current_folder.path_join("actors.json")
    if FileAccess.file_exists(actor_path):
        load_actors(actor_path)
    _load_prop_draft(true)
    if not FileAccess.file_exists(actor_path):
        status_label.text = "3D loaded (%d meshes). Open its actors.json to inspect entities." % mesh_count
    print("DX2Ed native: GLB loaded with ", mesh_count, " mesh instances")

func load_actors(path: String) -> void:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        status_label.text = "Cannot open actor metadata: " + path
        return
    var result: Variant = JSON.parse_string(file.get_as_text())
    if typeof(result) != TYPE_DICTIONARY or not result.has("actors") or typeof(result["actors"]) != TYPE_ARRAY:
        status_label.text = "Invalid actor JSON: " + path
        return
    actors = result["actors"]
    var metadata: Variant = result.get("meta", {})
    current_source_map_name = str(metadata.get("source_map", "")) if typeof(metadata) == TYPE_DICTIONARY else ""
    actors_by_name.clear()
    for actor in actors:
        if typeof(actor) == TYPE_DICTIONARY and actor.has("name"):
            actors_by_name[str(actor["name"])] = actor
    _refresh_actor_list()
    status_label.text = "Loaded %d actors, %d meshes. Click a mesh or select an actor." % [actors.size(), mesh_count]

func _clear_current_scene() -> void:
    _clear_selection()
    actors.clear()
    actors_by_name.clear()
    meshes_by_actor.clear()
    current_source_map_name = ""
    original_mesh_transforms.clear()
    draft_prop_copies.clear()
    draft_prop_sources.clear()
    next_prop_copy_id = 1
    undo_stack.clear()
    redo_stack.clear()
    gizmo_undo_before.clear()
    gizmo_drag_active = false
    _refresh_history_buttons()
    all_mesh_instances.clear()
    pick_faces_by_mesh.clear()
    visible_actors.clear()
    actor_list.clear()
    if hierarchy_tree != null:
        hierarchy_tree.clear()
        hierarchy_items.clear()
    scene_bounds_valid = false
    mesh_count = 0
    if scene_root != null:
        scene_root.queue_free()
        scene_root = null

func _index_meshes(node: Node) -> void:
    if node is MeshInstance3D:
        var mesh_node := node as MeshInstance3D
        mesh_count += 1
        all_mesh_instances.append(mesh_node)
        if mesh_node.mesh != null:
            var box := _mesh_world_aabb(mesh_node)
            if not scene_bounds_valid:
                scene_bounds = box
                scene_bounds_valid = true
            else:
                scene_bounds = scene_bounds.merge(box)
            var actor_name := str(mesh_node.name)
            if not original_mesh_transforms.has(actor_name):
                original_mesh_transforms[actor_name] = mesh_node.global_transform
            if not meshes_by_actor.has(actor_name):
                meshes_by_actor[actor_name] = mesh_node
    for child in node.get_children():
        _index_meshes(child)

func _mesh_world_aabb(instance: MeshInstance3D) -> AABB:
    var local := instance.get_aabb()
    var first := instance.global_transform * local.get_endpoint(0)
    var result := AABB(first, Vector3.ZERO)
    for i in range(1, 8):
        result = result.expand(instance.global_transform * local.get_endpoint(i))
    return result

func _actor_category(actor: Dictionary) -> String:
    # This is class-name *discovery*, NOT proof of rigid-body physics,
    # inventory behavior, or final in-game script inheritance.
    var raw := str(actor.get("class", ""))
    var kind := raw.to_lower()
    if kind == "staticmeshactor": return "Static mesh"
    if kind == "brush": return "Brush"
    if kind == "light" or kind.ends_with("light"): return "Light"
    if "volume" in kind or "trigger" in kind: return "Volume / trigger"
    if "pickup" in kind or "inventory" in kind or "item" in kind: return "Item candidate"
    if "physicsprop" in kind or "rigidbody" in kind or "kactor" in kind or "pushable" in kind:
        return "Physics candidate"
    return "Gameplay / other"


func _category_visible(category: String) -> bool:
    if category_filter == null or category_filter.selected <= 0:
        return true
    var values := [
        "All actors", "Static mesh", "Brush", "Light",
        "Volume / trigger", "Item candidate", "Physics candidate", "Gameplay / other"
    ]
    return category == values[category_filter.selected]


func _refresh_actor_list() -> void:
    actor_list.clear()
    visible_actors.clear()
    var query := search_box.text.strip_edges().to_lower()
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var name := str(actor.get("name", ""))
        var kind := str(actor.get("class", ""))
        var group := _actor_category(actor)
        if not _category_visible(group):
            continue
        var meshname := ""
        var mesh_metadata: Variant = actor.get("mesh")
        if typeof(mesh_metadata) == TYPE_DICTIONARY:
            meshname = str(mesh_metadata.get("name", ""))
        elif typeof(mesh_metadata) == TYPE_STRING:
            meshname = str(mesh_metadata)
        if query != "" and query not in (name + " " + kind + " " + meshname + " " + group).to_lower():
            continue
        visible_actors.append(actor)
        actor_list.add_item(name + "  [" + kind + " | " + group + "]")
    _sync_actor_list_selection()
    _refresh_hierarchy()
    if visible_actors.is_empty() and not actors.is_empty():
        status_label.text = "No actors match search."

func _refresh_hierarchy() -> void:
    if hierarchy_tree == null:
        return
    hierarchy_syncing = true
    hierarchy_tree.clear()
    hierarchy_items.clear()
    var scene_item := hierarchy_tree.create_item()
    scene_item.set_text(0, "DX2 Scene  (" + str(actors.size()) + " actors)")
    scene_item.set_selectable(0, false)
    var categories: Dictionary = {}
    # These are editor folders by decoded class, NOT invented Unreal ownership.
    for actor in visible_actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var group := _actor_category(actor)
        if not categories.has(group):
            var folder := hierarchy_tree.create_item(scene_item)
            folder.set_text(0, group)
            folder.set_selectable(0, false)
            folder.collapsed = group == "Brush" or group == "Gameplay / other"
            categories[group] = folder
        var name := str(actor.get("name", ""))
        var leaf := hierarchy_tree.create_item(categories[group])
        leaf.set_text(0, name)
        leaf.set_tooltip_text(0, str(actor.get("class", "?")))
        leaf.set_metadata(0, name)
        hierarchy_items[name] = leaf

    var query := search_box.text.strip_edges().to_lower()
    if category_filter.selected <= 1:
        var drafts := hierarchy_tree.create_item(scene_item)
        drafts.set_text(0, "Draft copies (" + str(draft_prop_copies.size()) + ")")
        drafts.set_selectable(0, false)
        for name in draft_prop_copies:
            if query != "" and query not in str(name).to_lower() and query not in str(draft_prop_sources.get(name, "")).to_lower():
                continue
            var leaf := hierarchy_tree.create_item(drafts)
            leaf.set_text(0, str(name) + "  [draft]")
            leaf.set_tooltip_text(0, "Preview copy of " + str(draft_prop_sources.get(name, "")))
            leaf.set_metadata(0, str(name))
            hierarchy_items[str(name)] = leaf

    if category_filter.selected == 0:
        var unlinked := hierarchy_tree.create_item(scene_item)
        unlinked.set_text(0, "Unlinked geometry (BSP / render nodes)")
        unlinked.set_selectable(0, false)
        unlinked.collapsed = true
        for node in all_mesh_instances:
            if not is_instance_valid(node):
                continue
            var name := str(node.name)
            if actors_by_name.has(name) or draft_prop_copies.has(name):
                continue
            if query != "" and query not in name.to_lower():
                continue
            var leaf := hierarchy_tree.create_item(unlinked)
            leaf.set_text(0, name)
            leaf.set_metadata(0, name)
            hierarchy_items[name] = leaf

    _sync_hierarchy_selection()
    hierarchy_syncing = false


func _sync_hierarchy_selection() -> void:
    if hierarchy_tree == null or hierarchy_syncing:
        return
    hierarchy_syncing = true
    hierarchy_tree.deselect_all()
    for name in selected_meshes:
        if hierarchy_items.has(name):
            var item: TreeItem = hierarchy_items[name]
            item.get_parent().collapsed = false
            item.select(0)
    if selected_meshes.is_empty() and not selected_actor.is_empty():
        var name := str(selected_actor.get("name", ""))
        if hierarchy_items.has(name):
            var item: TreeItem = hierarchy_items[name]
            item.get_parent().collapsed = false
            item.select(0)
    hierarchy_syncing = false


func _hierarchy_multi_selected(_item: TreeItem, _column: int, _selected: bool) -> void:
    if not hierarchy_syncing:
        call_deferred("_apply_hierarchy_selection")


func _apply_hierarchy_selection() -> void:
    if hierarchy_tree == null or hierarchy_syncing:
        return
    var chosen_names: Array[String] = []
    var cursor: TreeItem = hierarchy_tree.get_next_selected(null)
    while cursor != null:
        var meta: Variant = cursor.get_metadata(0)
        if typeof(meta) == TYPE_STRING and not str(meta).is_empty():
            chosen_names.append(str(meta))
        cursor = hierarchy_tree.get_next_selected(cursor)
    if chosen_names.is_empty():
        return
    _clear_selection()
    var logical_actor: Dictionary = {}
    for name in chosen_names:
        var node: MeshInstance3D = null
        if draft_prop_copies.has(name):
            node = draft_prop_copies[name]
        elif meshes_by_actor.has(name):
            node = meshes_by_actor[name]
        else:
            for mesh_node in all_mesh_instances:
                if is_instance_valid(mesh_node) and str(mesh_node.name) == name:
                    node = mesh_node
                    break
        if is_instance_valid(node):
            _add_selection_mesh(node)
        elif actors_by_name.has(name):
            logical_actor = actors_by_name[name]
    if selected_meshes.is_empty() and not logical_actor.is_empty():
        selected_actor = logical_actor
        selected_diagnostic = _format_actor_diagnostic(logical_actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(logical_actor, "  ")
        status_label.text = "Selected logical actor: " + str(logical_actor.get("name", ""))
        _refresh_inspector_panel()
    else:
        _refresh_selection_inspector()
    _sync_actor_list_selection()


func _actor_list_selected(index: int) -> void:
    # Backward compatibility with the single-selection signal.
    if index >= 0 and index < visible_actors.size():
        select_actor(visible_actors[index])


func _actor_list_multi_selected(_index: int, _is_selected: bool) -> void:
    # The list emits an event per changed row (including Shift range selection).
    # Defer rebuilding until the control finishes applying the complete gesture.
    call_deferred("_apply_list_multi_selection")


func _apply_list_multi_selection() -> void:
    var rows := actor_list.get_selected_items()
    if rows.is_empty():
        _clear_selection()
        inspector.text = "No actors selected."
        return
    var choices: Array[MeshInstance3D] = []
    var last_actor: Dictionary = {}
    for row in rows:
        if row < 0 or row >= visible_actors.size():
            continue
        var actor: Dictionary = visible_actors[row]
        last_actor = actor
        var name := str(actor.get("name", ""))
        if meshes_by_actor.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if is_instance_valid(node) and not choices.has(node):
                choices.append(node)
    _clear_selection()
    for node in choices:
        _add_selection_mesh(node)
    if choices.is_empty() and not last_actor.is_empty():
        # Logical-only actors remain inspectable, but not transformable.
        selected_actor = last_actor
        selected_diagnostic = _format_actor_diagnostic(last_actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(last_actor, "  ")
        status_label.text = "Selected logical actor: " + str(last_actor.get("name", "?"))
    else:
        _refresh_selection_inspector()


func _sync_actor_list_selection() -> void:
    if actor_list == null:
        return
    actor_list.deselect_all()
    for index in range(visible_actors.size()):
        if selected_meshes.has(str(visible_actors[index].get("name", ""))):
            actor_list.select(index, false)
    _sync_hierarchy_selection()



func _format_actor_diagnostic(actor: Dictionary) -> String:
    var name := str(actor.get("name", "Unknown"))
    # Actor Explorer emits a string mesh name plus separate mesh_bounds, whereas
    # the authored demo fixture uses {"name": ..., "bounds": ...}.
    # Support both without losing the original retail actor metadata.
    var mesh_data: Variant = actor.get("mesh", null)
    var mesh_name := "(no static mesh)"
    var bounds: Variant = actor.get("mesh_bounds", null)
    if typeof(mesh_data) == TYPE_DICTIONARY:
        mesh_name = str(mesh_data.get("name", "(unknown)"))
        if mesh_data.has("bounds"):
            bounds = mesh_data["bounds"]
    elif typeof(mesh_data) == TYPE_STRING and not str(mesh_data).is_empty():
        mesh_name = str(mesh_data)
    var bounds_text := str(bounds) if bounds != null else "(unavailable)"

    # Both the retail actor explorer and demo fixture use location: [x,y,z].
    # Keep a compatibility fallback for older exports containing x/y/z keys.
    var source_location: Variant = actor.get("location", null)
    if typeof(source_location) != TYPE_ARRAY or source_location.size() < 3:
        source_location = [actor.get("x", null), actor.get("y", null), actor.get("z", null)]

    var rotation: Variant = actor.get("rotation", [0, 0, 0])
    var degrees_text := "(unavailable)"
    if typeof(rotation) == TYPE_ARRAY and rotation.size() >= 3:
        degrees_text = "[%0.3f, %0.3f, %0.3f]" % [float(rotation[0]) * 360.0 / 65536.0, float(rotation[1]) * 360.0 / 65536.0, float(rotation[2]) * 360.0 / 65536.0]
    var lines := [
        "DX2Ed map geometry diagnostic (read-only)",
        "Actor: " + name,
        "Source map: " + (current_source_map_name if not current_source_map_name.is_empty() else "(not recorded)"),
        "Class: " + str(actor.get("class", "Unknown")),
        "Editor category (class hint): " + _actor_category(actor),
        "Physics / inventory semantics: not validated by this classification",
        "GMP export index: " + str(actor.get("export", "?")),
        "Mesh resource: " + mesh_name,
        "GMP position (UE units): " + str(source_location),
        "GMP rotation [Pitch, Yaw, Roll] (UE rotator units): " + str(rotation),
        "Rotation degrees [Pitch, Yaw, Roll]: " + degrees_text,
        "Mesh local bounds (UE units): " + bounds_text,
    ]
    var render_skin: Variant = actor.get("render_skin", null)
    if typeof(render_skin) == TYPE_DICTIONARY:
        lines.append("Requested skin: " + str(render_skin.get("requested", "(none)")))
        lines.append("Exported skin: " + str(render_skin.get("selected", "(none)")))
        lines.append("Skin resolution: " + str(render_skin.get("status", "unknown")))
        var material_rows: Variant = render_skin.get("materials", [])
        if typeof(material_rows) == TYPE_ARRAY:
            for material_row in material_rows:
                if typeof(material_row) == TYPE_DICTIONARY:
                    lines.append("Skin material: " + str(material_row.get("name", "?")) + " | " + str(material_row.get("resolution", "unknown")))
    else:
        for prop in actor.get("game_properties", []):
            if typeof(prop) == TYPE_DICTIONARY and int(prop.get("id", -1)) == 56:
                var details: Variant = prop.get("value", null)
                if typeof(details) == TYPE_DICTIONARY and details.has("Skin"):
                    lines.append("Requested skin: " + str(details["Skin"]) + " (export selection not recorded)")
                    break
    if meshes_by_actor.has(name) and is_instance_valid(meshes_by_actor[name]):
        var instance: MeshInstance3D = meshes_by_actor[name]
        var box := _mesh_world_aabb(instance)
        lines.append("Godot mesh node: " + str(instance.name))
        lines.append("Godot global transform: " + str(instance.global_transform))
        lines.append("Godot world AABB: " + str(box.position) + " size " + str(box.size))
    else:
        lines.append("Matching rendered mesh node: not found (may be logical-only or have an unresolved resource)")
    return "\n".join(lines)

func _format_mesh_diagnostic(mesh_instance: MeshInstance3D) -> String:
    var box := _mesh_world_aabb(mesh_instance)
    return "\n".join([
        "DX2Ed map geometry diagnostic (read-only)",
        "Rendered mesh node: " + str(mesh_instance.name),
        "Editor category: " + ("BSP render geometry" if str(mesh_instance.name).begins_with("BSP_") else "Unlinked rendered geometry"),
        "Original DX2 actor metadata: not matched; may be BSP or imported geometry",
        "Godot global transform: " + str(mesh_instance.global_transform),
        "Godot world AABB: " + str(box.position) + " size " + str(box.size),
    ])

func _copy_selection_details() -> void:
    if selected_diagnostic.is_empty():
        status_label.text = "Select an actor or click a rendered mesh first."
        return
    DisplayServer.clipboard_set(selected_diagnostic)
    status_label.text = "Copied selection diagnostic to clipboard. Paste it into your bug report."

func _selection_nodes() -> Array[MeshInstance3D]:
    var nodes: Array[MeshInstance3D] = []
    for node in selected_meshes.values():
        if is_instance_valid(node):
            nodes.append(node)
    return nodes


func _selection_pivot() -> Vector3:
    var nodes := _selection_nodes()
    if nodes.is_empty():
        return Vector3.ZERO
    var pivot := Vector3.ZERO
    for node in nodes:
        pivot += node.global_position
    return pivot / float(nodes.size())


func _add_selection_mesh(mesh_instance: MeshInstance3D) -> void:
    if not is_instance_valid(mesh_instance):
        return
    var name := str(mesh_instance.name)
    if selected_meshes.has(name):
        selected_mesh = mesh_instance
        return
    selected_meshes[name] = mesh_instance
    selection_original_overlays[name] = mesh_instance.material_overlay
    mesh_instance.material_overlay = overlay_material
    selected_mesh = mesh_instance
    selected_actor = actors_by_name.get(name, {})


func _remove_selection_mesh(mesh_instance: MeshInstance3D) -> void:
    if not is_instance_valid(mesh_instance):
        return
    var name := str(mesh_instance.name)
    if not selected_meshes.has(name):
        return
    mesh_instance.material_overlay = selection_original_overlays.get(name, null)
    selected_meshes.erase(name)
    selection_original_overlays.erase(name)
    var survivors := _selection_nodes()
    selected_mesh = survivors.back() if not survivors.is_empty() else null
    selected_actor = actors_by_name.get(str(selected_mesh.name), {}) if is_instance_valid(selected_mesh) else {}


func _refresh_selection_inspector() -> void:
    var nodes := _selection_nodes()
    if nodes.is_empty():
        selected_diagnostic = ""
        inspector.text = "No rendered objects selected."
        status_label.text = "No objects selected."
        return
    if nodes.size() == 1:
        var node := nodes[0]
        var name := str(node.name)
        if actors_by_name.has(name):
            selected_actor = actors_by_name[name]
            selected_diagnostic = _format_actor_diagnostic(selected_actor)
            inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(selected_actor, "  ")
        else:
            selected_actor = {}
            selected_diagnostic = _format_mesh_diagnostic(node)
            inspector.text = selected_diagnostic
        status_label.text = "Selected " + name
        return
    var lines := ["DX2Ed multi-selection (preview only)",
        "Selected objects: " + str(nodes.size()),
        "Group pivot (Godot world): " + str(_selection_pivot()),
        "Move, Rotate and Scale use the group pivot.",
        "Original GMP/IBD files remain unchanged.", ""]
    for node in nodes:
        lines.append(str(node.name) + " | " + str(node.global_position))
    selected_diagnostic = "\n".join(lines)
    inspector.text = selected_diagnostic
    status_label.text = str(nodes.size()) + " objects selected. Group gizmo active."


func _select_mesh_only(mesh_instance: MeshInstance3D) -> void:
    _clear_selection()
    _add_selection_mesh(mesh_instance)
    _refresh_selection_inspector()
    _sync_actor_list_selection()


func _toggle_selection_mesh(mesh_instance: MeshInstance3D) -> void:
    var name := str(mesh_instance.name)
    # Only editable placed meshes and draft clones can join a group selection.
    if not (actors_by_name.has(name) and meshes_by_actor.has(name)) and not draft_prop_copies.has(name):
        status_label.text = "Ctrl-click supports static mesh actors and draft copies, not BSP geometry."
        return
    if selected_meshes.has(name):
        _remove_selection_mesh(mesh_instance)
    else:
        _add_selection_mesh(mesh_instance)
    _refresh_selection_inspector()
    _sync_actor_list_selection()


func select_actor(actor: Dictionary) -> void:
    _clear_selection()
    selected_actor = actor
    var name := str(actor.get("name", ""))
    if meshes_by_actor.has(name):
        _add_selection_mesh(meshes_by_actor[name])
        _refresh_selection_inspector()
    else:
        selected_diagnostic = _format_actor_diagnostic(actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(actor, "  ")
        status_label.text = "Selected " + name + " | " + str(actor.get("class", "Unknown"))
    _sync_actor_list_selection()


func _clear_selection() -> void:
    for name in selected_meshes:
        var node: MeshInstance3D = selected_meshes[name]
        if is_instance_valid(node):
            node.material_overlay = selection_original_overlays.get(name, null)
    selected_meshes.clear()
    selection_original_overlays.clear()
    selected_mesh = null
    selected_overlay_original = null
    selected_diagnostic = ""
    selected_actor = {}



## Editable *preview* operations. Native GMP/IBD save remains intentionally disabled.
## Drafts live in user:// and are never written next to retail files.

func _draft_selected_is_prop() -> bool:
    var nodes := _selection_nodes()
    if nodes.is_empty():
        return false
    for node in nodes:
        var name := str(node.name)
        if not draft_prop_copies.has(name) and not (meshes_by_actor.has(name) and actors_by_name.has(name)):
            return false
    return true


## History snapshots contain only preview edits and selected names.
## Native DX2 objects remain represented by the original imported GLB.
func _capture_edit_state() -> Dictionary:
    var moved: Dictionary = {}
    for name in original_mesh_transforms:
        if not meshes_by_actor.has(name) or not actors_by_name.has(name):
            continue
        var node: MeshInstance3D = meshes_by_actor[name]
        if is_instance_valid(node) and node.global_transform != original_mesh_transforms[name]:
            moved[name] = node.global_transform
    var copies: Dictionary = {}
    for name in draft_prop_copies:
        var copy: MeshInstance3D = draft_prop_copies[name]
        if is_instance_valid(copy):
            copies[name] = {
                "source": str(draft_prop_sources.get(name, "")),
                "transform": copy.global_transform
            }
    return {
        "moved": moved,
        "copies": copies,
        "selected": selected_meshes.keys().duplicate(),
        "next_id": next_prop_copy_id
    }


func _apply_edit_state(state: Dictionary) -> void:
    _clear_selection()
    # Restore baseline first. A reverted move must not linger if absent
    # from the snapshot.
    for name in original_mesh_transforms:
        if meshes_by_actor.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if is_instance_valid(node):
                node.global_transform = original_mesh_transforms[name]
    # Free synchronously so undoing and immediately redoing a duplicate never
    # hits Godot's auto-renamed Node3D names from queued deletions.
    for copy in draft_prop_copies.values():
        if is_instance_valid(copy):
            all_mesh_instances.erase(copy)
            copy.free()
    draft_prop_copies.clear()
    draft_prop_sources.clear()
    next_prop_copy_id = 1
    var moved: Dictionary = state.get("moved", {})
    for name in moved:
        if meshes_by_actor.has(name) and actors_by_name.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if is_instance_valid(node):
                node.global_transform = moved[name]
    var copies: Dictionary = state.get("copies", {})
    for name in copies:
        var info: Dictionary = copies[name]
        if not str(name).begins_with("DraftProp_"):
            continue
        var source := str(info.get("source", ""))
        if actors_by_name.has(source):
            _new_draft_copy(source, str(name), info["transform"])
    next_prop_copy_id = max(1, int(state.get("next_id", 1)))
    for name in state.get("selected", []):
        var node: MeshInstance3D = null
        if draft_prop_copies.has(name):
            node = draft_prop_copies[name]
        elif meshes_by_actor.has(name) and actors_by_name.has(name):
            node = meshes_by_actor[name]
        if is_instance_valid(node):
            _add_selection_mesh(node)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _update_gizmo_pose()


func _refresh_history_buttons() -> void:
    if undo_button != null:
        undo_button.disabled = undo_stack.is_empty()
        undo_button.tooltip_text = "Ctrl+Z" if undo_stack.is_empty() else "Ctrl+Z: " + str(undo_stack.back()["label"])
    if redo_button != null:
        redo_button.disabled = redo_stack.is_empty()
        redo_button.tooltip_text = "Ctrl+Y / Ctrl+Shift+Z" if redo_stack.is_empty() else "Ctrl+Y: " + str(redo_stack.back()["label"])


func _record_edit(label: String, before: Dictionary) -> void:
    var after := _capture_edit_state()
    # Selection changes alone do not count as edits.
    if before.get("moved") == after.get("moved") and before.get("copies") == after.get("copies"):
        return
    undo_stack.append({"label": label, "before": before, "after": after})
    if undo_stack.size() > HISTORY_LIMIT:
        undo_stack.pop_front()
    redo_stack.clear()
    _refresh_history_buttons()


func _undo_edit() -> void:
    if gizmo_drag_active:
        _finish_gizmo_drag()
    if undo_stack.is_empty():
        return
    var item: Dictionary = undo_stack.pop_back()
    _apply_edit_state(item["before"])
    redo_stack.append(item)
    _refresh_history_buttons()
    status_label.text = "Undo: " + str(item["label"]) + " (preview draft only)."


func _redo_edit() -> void:
    if gizmo_drag_active:
        _finish_gizmo_drag()
    if redo_stack.is_empty():
        return
    var item: Dictionary = redo_stack.pop_back()
    _apply_edit_state(item["after"])
    undo_stack.append(item)
    _refresh_history_buttons()
    status_label.text = "Redo: " + str(item["label"]) + " (preview draft only)."


func _restore_all_edits() -> void:
    if scene_root == null:
        status_label.text = "Load a map before restoring edits."
        return
    var before := _capture_edit_state()
    _apply_edit_state({"moved": {}, "copies": {}, "selected": [], "next_id": 1})
    _record_edit("Restore All", before)
    # Overwrite the sidecar with an empty draft. Undo restores the session's
    # preview state, but the user must Save draft to persist the undo.
    _save_prop_draft()
    status_label.text = "All prop edits restored to the imported map. Saved draft cleared. Ctrl+Z can undo this session."


func _finish_gizmo_drag() -> void:
    if not gizmo_drag_active:
        return
    gizmo_drag_active = false
    _record_edit("Drag " + editor_tool, gizmo_undo_before)
    gizmo_undo_before.clear()


func _draft_source_name(instance: MeshInstance3D) -> String:
    var name := str(instance.name)
    if draft_prop_sources.has(name):
        return str(draft_prop_sources[name])
    if meshes_by_actor.has(name) and actors_by_name.has(name):
        return name
    return ""

func _new_draft_copy(source_name: String, copy_name: String, world_transform: Transform3D) -> MeshInstance3D:
    if not meshes_by_actor.has(source_name) or draft_prop_copies.has(copy_name):
        return null
    var source: MeshInstance3D = meshes_by_actor[source_name]
    if not is_instance_valid(source) or source.mesh == null:
        return null
    var duplicate := MeshInstance3D.new()
    duplicate.name = copy_name
    duplicate.mesh = source.mesh
    duplicate.material_override = source.material_override
    duplicate.cast_shadow = source.cast_shadow
    world_root.add_child(duplicate)
    duplicate.global_transform = world_transform
    draft_prop_copies[copy_name] = duplicate
    draft_prop_sources[copy_name] = source_name
    all_mesh_instances.append(duplicate)
    return duplicate

func _duplicate_selected_prop() -> void:
    if not _draft_selected_is_prop():
        status_label.text = "Select a rendered static mesh actor first (BSP cannot be duplicated)."
        return
    var history_before := _capture_edit_state()
    var originals := _selection_nodes()
    var copies: Array[MeshInstance3D] = []
    for node in originals:
        var source := _draft_source_name(node)
        if source.is_empty():
            continue
        var name := "DraftProp_" + str(next_prop_copy_id)
        next_prop_copy_id += 1
        var new_copy := _new_draft_copy(source, name, node.global_transform)
        if is_instance_valid(new_copy):
            copies.append(new_copy)
    if copies.is_empty():
        return
    _clear_selection()
    for node in copies:
        _add_selection_mesh(node)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _record_edit("Duplicate " + str(copies.size()) + " prop(s)", history_before)
    status_label.text = "Duplicated " + str(copies.size()) + " prop(s). Move the copies, then Save draft."


func _refresh_prop_inspection() -> void:
    _refresh_selection_inspector()
    if not _selection_nodes().is_empty():
        inspector.text += "\n\n--- PREVIEW EDIT ---\nGroup pivot: " + str(_selection_pivot())
        status_label.text = "Preview modified " + str(_selection_nodes().size()) + " prop(s). Save draft to keep changes."


func _move_selected_prop(axis: Vector3) -> void:
    if not _draft_selected_is_prop():
        status_label.text = "Select one or more rendered props (not BSP)."
        return
    var history_before := _capture_edit_state()
    var delta := axis * float(prop_edit_step.value)
    for node in _selection_nodes():
        node.global_position += delta
    _refresh_prop_inspection()
    _record_edit("Move " + str(_selection_nodes().size()) + " prop(s)", history_before)


func _rotate_selected_prop(angle: float) -> void:
    if not _draft_selected_is_prop():
        status_label.text = "Select one or more rendered props to rotate."
        return
    var history_before := _capture_edit_state()
    var pivot := _selection_pivot()
    var turn := Basis(Vector3.UP, deg_to_rad(angle))
    for node in _selection_nodes():
        var pose := node.global_transform
        pose.origin = pivot + turn * (pose.origin - pivot)
        pose.basis = turn * pose.basis
        node.global_transform = pose
    _refresh_prop_inspection()
    _record_edit("Rotate " + str(_selection_nodes().size()) + " prop(s)", history_before)


func _reset_selected_prop() -> void:
    if not _draft_selected_is_prop():
        return
    var history_before := _capture_edit_state()
    var nodes := _selection_nodes()
    _clear_selection()
    var restored: Array[MeshInstance3D] = []
    var removed := 0
    for node in nodes:
        var name := str(node.name)
        if draft_prop_copies.has(name):
            draft_prop_copies.erase(name)
            draft_prop_sources.erase(name)
            all_mesh_instances.erase(node)
            node.free()
            removed += 1
        elif original_mesh_transforms.has(name):
            node.global_transform = original_mesh_transforms[name]
            restored.append(node)
    for node in restored:
        _add_selection_mesh(node)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _record_edit("Reset " + str(restored.size()) + " / delete " + str(removed), history_before)
    status_label.text = "Restored " + str(restored.size()) + " original(s), deleted " + str(removed) + " copy/copies. Save draft to persist."



func _draft_file_path() -> String:
    if current_folder.is_empty():
        return ""
    var folder := ProjectSettings.globalize_path("user://prop_drafts")
    var result := DirAccess.make_dir_recursive_absolute(folder)
    if result != OK:
        return ""
    return folder.path_join(current_folder.sha256_text() + ".json")

func _transform_to_array(xform: Transform3D) -> Array:
    return [
        xform.basis.x.x, xform.basis.x.y, xform.basis.x.z,
        xform.basis.y.x, xform.basis.y.y, xform.basis.y.z,
        xform.basis.z.x, xform.basis.z.y, xform.basis.z.z,
        xform.origin.x, xform.origin.y, xform.origin.z
    ]

func _array_to_transform(values: Variant) -> Variant:
    if typeof(values) != TYPE_ARRAY or values.size() != 12:
        return null
    var safe: Array = []
    for value in values:
        if typeof(value) not in [TYPE_FLOAT, TYPE_INT]:
            return null
        var number := float(value)
        if not is_finite(number) or abs(number) > 1000000.0:
            return null
        safe.append(number)
    return Transform3D(
        Vector3(safe[0], safe[1], safe[2]),
        Vector3(safe[3], safe[4], safe[5]),
        Vector3(safe[6], safe[7], safe[8]),
        Vector3(safe[9], safe[10], safe[11])
    )

func _save_prop_draft() -> void:
    var path := _draft_file_path()
    if path.is_empty() or scene_root == null:
        status_label.text = "Load a GLB map before saving a prop draft."
        return
    var moved := []
    for name in original_mesh_transforms:
        if not meshes_by_actor.has(name) or not actors_by_name.has(name):
            continue
        var mesh: MeshInstance3D = meshes_by_actor[name]
        if is_instance_valid(mesh) and mesh.global_transform != original_mesh_transforms[name]:
            moved.append({"actor": name, "transform": _transform_to_array(mesh.global_transform)})
    var copies := []
    for name in draft_prop_copies:
        var duplicate: MeshInstance3D = draft_prop_copies[name]
        if is_instance_valid(duplicate):
            copies.append({"name": name, "from_actor": draft_prop_sources[name],
                           "transform": _transform_to_array(duplicate.global_transform)})
    var document := {
        "schema": "DX2Ed-prop-draft-v1",
        "map_cache": current_folder,
        "coordinate_space": "Godot world metres (X=UE X, Y=UE Z, Z=UE Y)",
        "read_only_source": true,
        "moved": moved,
        "copies": copies
    }
    var output := FileAccess.open(path, FileAccess.WRITE)
    if output == null:
        status_label.text = "Unable to write private draft: " + path
        return
    output.store_string(JSON.stringify(document, "  "))
    output.close()
    status_label.text = "Saved " + str(moved.size()) + " moved props and " + str(copies.size()) + " copies in private draft JSON (not GMP)."

func _load_prop_draft(silent_if_absent: bool = false) -> void:
    var path := _draft_file_path()
    if path.is_empty() or not FileAccess.file_exists(path):
        if not silent_if_absent:
            status_label.text = "No saved prop draft for this map cache."
        return
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        status_label.text = "Unable to read prop draft."
        return
    var doc: Variant = JSON.parse_string(file.get_as_text())
    if typeof(doc) != TYPE_DICTIONARY or doc.get("schema") != "DX2Ed-prop-draft-v1" or doc.get("map_cache") != current_folder:
        status_label.text = "Prop draft did not match the current map."
        return
    var moved: Variant = doc.get("moved", [])
    var copies: Variant = doc.get("copies", [])
    if typeof(moved) != TYPE_ARRAY or typeof(copies) != TYPE_ARRAY or moved.size() > 10000 or copies.size() > 10000:
        status_label.text = "Prop draft contains invalid record arrays."
        return
    # Validate every transform before applying any of the saved changes.
    for entry in moved + copies:
        if typeof(entry) != TYPE_DICTIONARY or _array_to_transform(entry.get("transform")) == null:
            status_label.text = "Prop draft contains an invalid transform."
            return
    var history_before := _capture_edit_state()
    _clear_selection()
    for name in original_mesh_transforms:
        if meshes_by_actor.has(name) and is_instance_valid(meshes_by_actor[name]):
            meshes_by_actor[name].global_transform = original_mesh_transforms[name]
    for node in draft_prop_copies.values():
        if is_instance_valid(node):
            all_mesh_instances.erase(node)
            node.free()
    draft_prop_copies.clear()
    draft_prop_sources.clear()
    next_prop_copy_id = 1
    for entry in moved:
        var name := str(entry.get("actor", ""))
        if meshes_by_actor.has(name) and actors_by_name.has(name):
            meshes_by_actor[name].global_transform = _array_to_transform(entry["transform"])
    for entry in copies:
        var from_actor := str(entry.get("from_actor", ""))
        var name := str(entry.get("name", ""))
        if not name.begins_with("DraftProp_") or not actors_by_name.has(from_actor):
            continue
        var instance := _new_draft_copy(from_actor, name, _array_to_transform(entry["transform"]))
        if is_instance_valid(instance):
            var suffix := name.trim_prefix("DraftProp_")
            if suffix.is_valid_int():
                next_prop_copy_id = max(next_prop_copy_id, int(suffix) + 1)
    if not silent_if_absent:
        _record_edit("Load draft", history_before)
    status_label.text = "Loaded private prop draft. Original GMP unchanged."

func focus_selected() -> void:
    if is_instance_valid(selected_mesh):
        var aabb := _mesh_world_aabb(selected_mesh)
        camera_target = aabb.get_center()
        orbit_distance = max(1.0, aabb.size.length() * 2.4)
        _update_camera()

func frame_whole_scene() -> void:
    if scene_bounds_valid:
        camera_target = scene_bounds.get_center()
        orbit_distance = max(5.0, scene_bounds.size.length() * 1.2)
        _update_camera()

func _update_camera() -> void:
    orbit_pitch = clamp(orbit_pitch, -1.50, 1.50)
    orbit_distance = clamp(orbit_distance, 0.15, 200000.0)
    var offset := Vector3(sin(orbit_yaw) * cos(orbit_pitch), sin(orbit_pitch), cos(orbit_yaw) * cos(orbit_pitch)) * orbit_distance
    camera.global_position = camera_target + offset
    camera.look_at(camera_target, Vector3.UP)

## The gizmo lives outside the imported GLB and is never included in
## actor selection, scene exports, or the original game data.
func _gizmo_color(axis: Vector3) -> Color:
    if axis.x > 0.5: return Color(0.98, 0.26, 0.24)
    if axis.y > 0.5: return Color(0.29, 0.94, 0.32)
    return Color(0.28, 0.52, 1.0)


func _create_transform_gizmo() -> void:
    _refresh_gizmo_shape()


func _refresh_gizmo_shape() -> void:
    if gizmo_root == null:
        return
    for old_handle in gizmo_handles:
        if is_instance_valid(old_handle):
            old_handle.queue_free()
    gizmo_handles.clear()
    var axes := [Vector3.RIGHT, Vector3.UP, Vector3.BACK]
    for axis in axes:
        var handle := MeshInstance3D.new()
        handle.name = editor_tool + "_axis_" + str(gizmo_handles.size())
        handle.set_meta("axis", axis)
        var tint := StandardMaterial3D.new()
        tint.albedo_color = _gizmo_color(axis)
        tint.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        tint.cull_mode = BaseMaterial3D.CULL_DISABLED
        tint.no_depth_test = true
        handle.material_override = tint
        handle.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        if editor_tool == "rotate":
            var torus := TorusMesh.new()
            torus.inner_radius = 0.80
            torus.outer_radius = 0.90
            handle.mesh = torus
            handle.quaternion = Quaternion(Vector3.UP, axis)
        elif editor_tool == "scale":
            var cube := BoxMesh.new()
            cube.size = Vector3(0.23, 0.23, 0.23)
            handle.mesh = cube
            handle.position = axis * 0.92
        else:
            var shaft := CylinderMesh.new()
            shaft.top_radius = 0.025
            shaft.bottom_radius = 0.095
            shaft.height = 1.18
            handle.mesh = shaft
            handle.position = axis * 0.68
            handle.quaternion = Quaternion(Vector3.UP, axis)
        gizmo_root.add_child(handle)
        gizmo_handles.append(handle)
    _update_gizmo_pose()


func _update_gizmo_pose() -> void:
    if gizmo_root == null:
        return
    var show := _draft_selected_is_prop()
    gizmo_root.visible = show
    if not show:
        return
    gizmo_root.global_position = _selection_pivot()
    # Keep the handles about the same apparent size while zooming.
    var distance := camera.global_position.distance_to(gizmo_root.global_position)
    # Unity-sized move handle: 75% larger on screen than the old preview.
    var size_ratio := 0.19 if editor_tool == "move" else 0.13
    var scale_size: float = clampf(distance * size_ratio, 0.22, 15.0)
    gizmo_root.scale = Vector3.ONE * scale_size


func _gizmo_axis_scalar(mouse_position: Vector2, pivot: Vector3, axis: Vector3) -> Variant:
    var ray := _mouse_ray(mouse_position)
    if ray.is_empty():
        return null
    var look := camera.global_position - pivot
    var normal := look - axis * look.dot(axis)
    if normal.length_squared() < 0.0001:
        var fallback := Vector3.UP if abs(axis.dot(Vector3.UP)) < 0.9 else Vector3.RIGHT
        normal = fallback - axis * fallback.dot(axis)
    normal = normal.normalized()
    var plane := Plane(normal, normal.dot(pivot))
    var point: Variant = plane.intersects_ray(ray["origin"], ray["direction"])
    if point == null:
        return null
    return (point - pivot).dot(axis)


func _begin_gizmo_drag() -> bool:
    if not _draft_selected_is_prop():
        return false
    _update_gizmo_pose()
    var ray := _mouse_ray(view_container.get_local_mouse_position())
    if ray.is_empty():
        return false
    var best_distance := INF
    var best_axis := Vector3.ZERO
    for handle in gizmo_handles:
        if not is_instance_valid(handle):
            continue
        var hit := _ray_mesh_triangles(handle, ray["origin"], ray["direction"])
        if not hit.is_empty() and float(hit["distance"]) < best_distance:
            best_distance = float(hit["distance"])
            best_axis = handle.get_meta("axis")
    if best_axis == Vector3.ZERO:
        return false
    gizmo_drag_axis = best_axis
    gizmo_drag_pivot = _selection_pivot()
    gizmo_start_transforms.clear()
    for node in _selection_nodes():
        gizmo_start_transforms[str(node.name)] = node.global_transform
    gizmo_start_transform = selected_mesh.global_transform
    gizmo_drag_start_screen = view_container.get_local_mouse_position()
    var scalar: Variant = _gizmo_axis_scalar(gizmo_drag_start_screen, gizmo_drag_pivot, best_axis)
    gizmo_drag_start_scalar = float(scalar) if scalar != null else 0.0
    gizmo_undo_before = _capture_edit_state()
    gizmo_drag_active = true
    return true


func _apply_gizmo_drag() -> void:
    if not gizmo_drag_active or not _draft_selected_is_prop():
        return
    var distance := camera.global_position.distance_to(gizmo_drag_pivot)
    var mouse := view_container.get_local_mouse_position()
    var rotate := Basis.IDENTITY
    var scale_factor := 1.0
    var movement := Vector3.ZERO
    if editor_tool == "rotate":
        var angle := (mouse.x - gizmo_drag_start_screen.x) * 0.012
        if Input.is_key_pressed(KEY_CTRL):
            angle = snapped(angle, deg_to_rad(15.0))
        rotate = Basis(gizmo_drag_axis, angle)
    else:
        var scalar: Variant = _gizmo_axis_scalar(mouse, gizmo_drag_pivot, gizmo_drag_axis)
        if scalar == null:
            return
        var change := float(scalar) - gizmo_drag_start_scalar
        if editor_tool == "move":
            if Input.is_key_pressed(KEY_CTRL):
                change = snapped(change, float(prop_edit_step.value))
            movement = gizmo_drag_axis * change
        elif editor_tool == "scale":
            scale_factor = clampf(1.0 + change / maxf(0.5, distance * 0.18), 0.05, 100.0)
            if Input.is_key_pressed(KEY_CTRL):
                scale_factor = maxf(0.05, snapped(scale_factor, 0.1))
    for node in _selection_nodes():
        var name := str(node.name)
        if not gizmo_start_transforms.has(name):
            continue
        var pose: Transform3D = gizmo_start_transforms[name]
        if editor_tool == "move":
            pose.origin += movement
        elif editor_tool == "rotate":
            pose.origin = gizmo_drag_pivot + rotate * (pose.origin - gizmo_drag_pivot)
            pose.basis = rotate * pose.basis
        elif editor_tool == "scale":
            var offset := pose.origin - gizmo_drag_pivot
            pose.origin = gizmo_drag_pivot + offset + gizmo_drag_axis * offset.dot(gizmo_drag_axis) * (scale_factor - 1.0)
            # Apply scale along the *world* gizmo axis to all three basis columns.
            for axis_index in range(3):
                var vector: Vector3 = pose.basis[axis_index]
                pose.basis[axis_index] = vector + gizmo_drag_axis * vector.dot(gizmo_drag_axis) * (scale_factor - 1.0)
        node.global_transform = pose
    _update_gizmo_pose()
    _refresh_prop_inspection()


func _camera_offset() -> Vector3:
    return Vector3(
        sin(orbit_yaw) * cos(orbit_pitch), sin(orbit_pitch),
        cos(orbit_yaw) * cos(orbit_pitch)) * orbit_distance


func _process(delta: float) -> void:
    if fly_looking and is_instance_valid(camera):
        var local := Vector3.ZERO
        if Input.is_key_pressed(KEY_W): local.z -= 1.0
        if Input.is_key_pressed(KEY_S): local.z += 1.0
        if Input.is_key_pressed(KEY_A): local.x -= 1.0
        if Input.is_key_pressed(KEY_D): local.x += 1.0
        if Input.is_key_pressed(KEY_Q): local.y -= 1.0
        if Input.is_key_pressed(KEY_E): local.y += 1.0
        if local != Vector3.ZERO:
            var multiplier := 4.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0
            var step := camera.global_basis * local.normalized() * fly_speed * multiplier * delta
            camera_target += step
            _update_camera()
    _update_gizmo_pose()


func _mouse_ray(view_mouse_position: Vector2) -> Dictionary:
    if view_container.size.x <= 0 or view_container.size.y <= 0:
        return {}
    var screen := view_mouse_position * Vector2(world_view.size) / view_container.size
    return {"origin": camera.project_ray_origin(screen),
            "direction": camera.project_ray_normal(screen).normalized()}


func _set_editor_tool(tool: String) -> void:
    if tool not in ["move", "rotate", "scale"]:
        return
    _finish_gizmo_drag()
    editor_tool = tool
    _refresh_gizmo_shape()
    status_label.text = "Transform tool: " + tool.capitalize() + " (W/E/R). Preview edits only."


func _set_fly_mode(enabled: bool) -> void:
    fly_looking = enabled
    if enabled:
        # Preserve camera position while turning the view.
        drag_mode = "fly"
    else:
        drag_mode = ""


func _text_input_focused() -> bool:
    # Do not steal Ctrl+Z from a focused search/filter or numeric spinbox.
    var focused := get_viewport().gui_get_focus_owner()
    while focused != null:
        if focused is LineEdit or focused is TextEdit or focused is SpinBox:
            return true
        focused = focused.get_parent() as Control
    return false


func _input(event: InputEvent) -> void:
    if event is InputEventKey:
        var shortcut := event as InputEventKey
        if shortcut.pressed and not shortcut.echo and (shortcut.ctrl_pressed or shortcut.meta_pressed) and not shortcut.alt_pressed and not _text_input_focused():
            if shortcut.keycode == KEY_Z:
                if shortcut.shift_pressed:
                    _redo_edit()
                else:
                    _undo_edit()
                get_viewport().set_input_as_handled()
                return
            elif shortcut.keycode == KEY_Y:
                _redo_edit()
                get_viewport().set_input_as_handled()
                return
    if view_container == null or not view_container.visible:
        return
    var mouse_inside := view_container.get_global_rect().has_point(get_global_mouse_position())
    if event is InputEventKey:
        var ke := event as InputEventKey
        if ke.pressed and not ke.echo and not fly_looking and mouse_inside:
            if ke.keycode == KEY_W: _set_editor_tool("move")
            elif ke.keycode == KEY_E: _set_editor_tool("rotate")
            elif ke.keycode == KEY_R: _set_editor_tool("scale")
            elif ke.keycode == KEY_F: focus_selected()
            else: return
            get_viewport().set_input_as_handled()
        return
    if event is InputEventMouseButton:
        var button := event as InputEventMouseButton
        # Always handle release, including outside the embedded viewport.
        if button.pressed and not mouse_inside:
            return
        if button.button_index == MOUSE_BUTTON_RIGHT:
            _set_fly_mode(button.pressed)
            get_viewport().set_input_as_handled()
            return
        if button.button_index == MOUSE_BUTTON_WHEEL_UP and button.pressed:
            if fly_looking:
                fly_speed = min(250.0, fly_speed * 1.2)
            else:
                orbit_distance *= 0.88
                _update_camera()
            get_viewport().set_input_as_handled()
        elif button.button_index == MOUSE_BUTTON_WHEEL_DOWN and button.pressed:
            if fly_looking:
                fly_speed = max(0.1, fly_speed / 1.2)
            else:
                orbit_distance *= 1.13
                _update_camera()
            get_viewport().set_input_as_handled()
        elif button.button_index == MOUSE_BUTTON_MIDDLE:
            dragging = button.pressed
            drag_mode = "pan" if button.pressed else ""
        elif button.button_index == MOUSE_BUTTON_LEFT:
            if button.pressed:
                drag_distance = 0.0
                if button.alt_pressed:
                    dragging = true
                    drag_mode = "orbit"
                elif _begin_gizmo_drag():
                    dragging = true
                    drag_mode = "gizmo"
                else:
                    dragging = true
                    drag_mode = "select"
            else:
                if drag_mode == "select" and mouse_inside and drag_distance < 3.0:
                    _pick_actor(button.ctrl_pressed or button.shift_pressed)
                if drag_mode == "gizmo":
                    _finish_gizmo_drag()
                dragging = false
                drag_mode = ""
        return
    if event is InputEventMouseMotion:
        var motion := event as InputEventMouseMotion
        if fly_looking:
            var previous := camera.global_position
            orbit_yaw -= motion.relative.x * 0.006
            orbit_pitch += motion.relative.y * 0.006
            orbit_pitch = clamp(orbit_pitch, -1.50, 1.50)
            camera_target = previous - _camera_offset()
            _update_camera()
            get_viewport().set_input_as_handled()
        elif dragging:
            drag_distance += motion.relative.length()
            if drag_mode == "orbit":
                orbit_yaw -= motion.relative.x * 0.006
                orbit_pitch += motion.relative.y * 0.006
                _update_camera()
            elif drag_mode == "pan":
                var pan := (camera.global_basis.x * -motion.relative.x + camera.global_basis.y * motion.relative.y) * (orbit_distance * 0.0015)
                camera_target += pan
                _update_camera()
            elif drag_mode == "gizmo":
                _apply_gizmo_drag()
            get_viewport().set_input_as_handled()


func _pick_actor(additive: bool = false) -> void:
    # AABB is a broad-phase filter only. Actual visible triangles decide the pick:
    # a huge BSP box must not swallow a smaller prop, nor select an empty area.
    if all_mesh_instances.is_empty() or view_container.size.x <= 0.0 or view_container.size.y <= 0.0:
        return
    var local := view_container.get_local_mouse_position()
    var screen := local * Vector2(world_view.size) / view_container.size
    var origin := camera.project_ray_origin(screen)
    var direction := camera.project_ray_normal(screen).normalized()
    var candidates: Array = []
    for instance in all_mesh_instances:
        if not is_instance_valid(instance) or instance.mesh == null or not instance.is_visible_in_tree():
            continue
        var entry := _ray_aabb(origin, direction, _mesh_world_aabb(instance))
        if entry >= 0.0:
            candidates.append({"entry": entry, "instance": instance})
    candidates.sort_custom(func(a, b): return a["entry"] < b["entry"])

    var closest_mesh: MeshInstance3D = null
    var closest_distance := INF
    var closest_position := Vector3.ZERO
    for candidate in candidates:
        # If the closest face is in front of the box, no farther box can win.
        if float(candidate["entry"]) > closest_distance:
            break
        var instance: MeshInstance3D = candidate["instance"]
        var hit := _ray_mesh_triangles(instance, origin, direction)
        if hit.is_empty():
            continue
        var distance := float(hit["distance"])
        var this_is_actor := actors_by_name.has(str(instance.name))
        var previous_is_actor := is_instance_valid(closest_mesh) and actors_by_name.has(str(closest_mesh.name))
        if distance < closest_distance - 0.00001 or (abs(distance - closest_distance) <= 0.00001 and this_is_actor and not previous_is_actor):
            closest_distance = distance
            closest_position = hit["point"]
            closest_mesh = instance

    if not is_instance_valid(closest_mesh):
        status_label.text = "No rendered triangle under cursor (bounding boxes alone are not selectable)."
        return
    var chosen_name := str(closest_mesh.name)
    if additive:
        _toggle_selection_mesh(closest_mesh)
    elif actors_by_name.has(chosen_name):
        select_actor(actors_by_name[chosen_name])
    else:
        # Imported BSP geometry remains inspectable but cannot join prop groups.
        _select_mesh_only(closest_mesh)
    if selected_meshes.has(chosen_name) and not selected_diagnostic.is_empty():
        var hit_note := "Pick method: rendered triangle (not AABB)\nGodot hit (world): " + str(closest_position) + "\nRay distance (Godot units): " + str(closest_distance)
        selected_diagnostic += "\n" + hit_note
        inspector.text += "\n\n--- PICK DETAILS ---\n" + hit_note


func _ray_mesh_triangles(instance: MeshInstance3D, origin: Vector3, direction: Vector3) -> Dictionary:
    # Transform the ray into mesh space, avoiding recalculating vertices for
    # every rotated/scaled actor instance. World distance remains comparable.
    var mesh: Mesh = instance.mesh
    if mesh == null or abs(instance.global_transform.basis.determinant()) < 0.00000001:
        return {}
    var mesh_id := mesh.get_instance_id()
    var faces: PackedVector3Array
    if pick_faces_by_mesh.has(mesh_id):
        faces = pick_faces_by_mesh[mesh_id]
    else:
        faces = mesh.get_faces()
        pick_faces_by_mesh[mesh_id] = faces
    if faces.is_empty():
        return {}
    var inverse := instance.global_transform.affine_inverse()
    var local_origin := inverse * origin
    var local_direction := inverse.basis * direction
    if local_direction.length_squared() < 0.000000000001:
        return {}

    var closest := INF
    var best_point := Vector3.ZERO
    for i in range(0, faces.size() - 2, 3):
        var hit: Variant = Geometry3D.ray_intersects_triangle(
            local_origin, local_direction, faces[i], faces[i + 1], faces[i + 2])
        # The original exporter uses double-sided materials. Pick backfaces too.
        if hit == null:
            hit = Geometry3D.ray_intersects_triangle(
                local_origin, local_direction, faces[i + 2], faces[i + 1], faces[i])
        if hit is Vector3:
            var world_hit: Vector3 = instance.global_transform * hit
            var distance := (world_hit - origin).dot(direction)
            if distance >= 0.0 and distance < closest:
                closest = distance
                best_point = world_hit
    if closest == INF:
        return {}
    return {"distance": closest, "point": best_point}


func _ray_aabb(origin: Vector3, direction: Vector3, box: AABB) -> float:
    var entry := -INF
    var exit := INF
    var start := box.position
    var finish := box.end
    for axis in range(3):
        var d := direction[axis]
        var o := origin[axis]
        if abs(d) < 0.000001:
            if o < start[axis] or o > finish[axis]:
                return -1.0
            continue
        var t1 := (start[axis] - o) / d
        var t2 := (finish[axis] - o) / d
        entry = max(entry, min(t1, t2))
        exit = min(exit, max(t1, t2))
        if entry > exit:
            return -1.0
    if exit < 0.0:
        return -1.0
    return max(entry, 0.0)
