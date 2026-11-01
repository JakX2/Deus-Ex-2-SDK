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
var selected_actor: Dictionary = {}
var selected_overlay_original: Material
var overlay_material: StandardMaterial3D
var current_folder: String = ""
var camera_target := Vector3.ZERO
var orbit_yaw := 0.8
var orbit_pitch := 0.37
var orbit_distance := 25.0
var dragging := false
var drag_mode := ""
var drag_distance := 0.0
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
    hint.text = "  Left drag orbit  |  Right drag pan  |  Wheel zoom  |  Click select"
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
    club_zip_btn.text = "Open Seattle Club ZIP..."
    club_zip_btn.tooltip_text = "Safely stage the Club ZIP with the selected shared resources and open the GMP"
    club_zip_btn.pressed.connect(func(): club_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(club_zip_btn)
    var stairs_toggle := CheckBox.new()
    stairs_toggle.text = "Experimental stair Roll"
    stairs_toggle.tooltip_text = "Compare the unmodified retail transform preview with a reversible Seattle Club-only test. Reloads the level."
    stairs_toggle.button_pressed = false
    stairs_toggle.toggled.connect(_set_stair_preview)
    zip_bar.add_child(stairs_toggle)
    var zip_hint := Label.new()
    zip_hint.text = "  Select shared resources, optional System, then Club ZIP"
    zip_bar.add_child(zip_hint)

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
    actor_list = ItemList.new()
    actor_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    actor_list.item_selected.connect(_actor_list_selected)
    actor_list.item_activated.connect(func(_index): focus_selected())
    sidebar.add_child(actor_list)

    var right := VSplitContainer.new()
    right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    horizontal.add_child(right)
    view_container = SubViewportContainer.new()
    view_container.stretch = true
    view_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
    view_container.custom_minimum_size = Vector2(400, 360)
    right.add_child(view_container)
    inspector = TextEdit.new()
    inspector.editable = false
    inspector.custom_minimum_size = Vector2(0, 160)
    inspector.size_flags_vertical = Control.SIZE_EXPAND_FILL
    inspector.text = "Select an actor to inspect its original DX2 properties."
    right.add_child(inspector)
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
    status_label.text = "Preparing Seattle Club source archives in a private, read-only cache..."
    var result := build_thread.start(_run_zip_stage.bind(backend, path, chosen_shared_zip, chosen_system_zip, cache_root))
    if result != OK:
        build_thread = null
        status_label.text = "Could not start ZIP worker: " + error_string(result)

func _run_zip_stage(script: String, club: String, shared: String, system_zip: String, cache_root: String) -> void:
    var args := PackedStringArray([script, "--club", club, "--maps", shared, "--output-root", cache_root])
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
    else:
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
    all_mesh_instances.clear()
    pick_faces_by_mesh.clear()
    visible_actors.clear()
    actor_list.clear()
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

func _refresh_actor_list() -> void:
    actor_list.clear()
    visible_actors.clear()
    var query := search_box.text.strip_edges().to_lower()
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var name := str(actor.get("name", ""))
        var kind := str(actor.get("class", ""))
        var meshname := ""
        var mesh_metadata: Variant = actor.get("mesh")
        if typeof(mesh_metadata) == TYPE_DICTIONARY:
            meshname = str(mesh_metadata.get("name", ""))
        elif typeof(mesh_metadata) == TYPE_STRING:
            meshname = str(mesh_metadata)
        if query != "" and query not in (name + " " + kind + " " + meshname).to_lower():
            continue
        visible_actors.append(actor)
        actor_list.add_item(name + "  [" + kind + "]")
    if visible_actors.is_empty() and not actors.is_empty():
        status_label.text = "No actors match search."

func _actor_list_selected(index: int) -> void:
    if index >= 0 and index < visible_actors.size():
        select_actor(visible_actors[index])

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
        "Class: " + str(actor.get("class", "Unknown")),
        "GMP export index: " + str(actor.get("export", "?")),
        "Mesh resource: " + mesh_name,
        "GMP position (UE units): " + str(source_location),
        "GMP rotation [Pitch, Yaw, Roll] (UE rotator units): " + str(rotation),
        "Rotation degrees [Pitch, Yaw, Roll]: " + degrees_text,
        "Mesh local bounds (UE units): " + bounds_text,
    ]
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

func _select_mesh_only(mesh_instance: MeshInstance3D) -> void:
    _clear_selection()
    selected_mesh = mesh_instance
    selected_overlay_original = mesh_instance.material_overlay
    selected_mesh.material_overlay = overlay_material
    selected_diagnostic = _format_mesh_diagnostic(mesh_instance)
    inspector.text = selected_diagnostic
    status_label.text = "Selected scene geometry: " + str(mesh_instance.name) + " (not an actor)"

func select_actor(actor: Dictionary) -> void:
    _clear_selection()
    selected_actor = actor
    var name := str(actor.get("name", ""))
    if meshes_by_actor.has(name):
        selected_mesh = meshes_by_actor[name]
        selected_overlay_original = selected_mesh.material_overlay
        selected_mesh.material_overlay = overlay_material
    selected_diagnostic = _format_actor_diagnostic(actor)
    inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(actor, "  ")
    status_label.text = "Selected " + name + " | " + str(actor.get("class", "Unknown"))

func _clear_selection() -> void:
    if is_instance_valid(selected_mesh):
        selected_mesh.material_overlay = selected_overlay_original
    selected_mesh = null
    selected_overlay_original = null
    selected_diagnostic = ""
    selected_actor = {}

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

func _input(event: InputEvent) -> void:
    if view_container == null or not view_container.visible:
        return
    var mouse_inside := view_container.get_global_rect().has_point(get_global_mouse_position())
    if event is InputEventMouseButton:
        var button := event as InputEventMouseButton
        if button.pressed and not mouse_inside:
            return
        if button.button_index == MOUSE_BUTTON_WHEEL_UP and button.pressed:
            orbit_distance *= 0.88
            _update_camera()
            get_viewport().set_input_as_handled()
        elif button.button_index == MOUSE_BUTTON_WHEEL_DOWN and button.pressed:
            orbit_distance *= 1.13
            _update_camera()
            get_viewport().set_input_as_handled()
        elif button.button_index == MOUSE_BUTTON_LEFT:
            dragging = button.pressed
            drag_mode = "orbit"
            if button.pressed:
                drag_distance = 0.0
            elif mouse_inside and drag_distance < 3.0:
                _pick_actor()
        elif button.button_index == MOUSE_BUTTON_RIGHT:
            dragging = button.pressed
            drag_mode = "pan"
    if event is InputEventMouseMotion and dragging:
        var motion := event as InputEventMouseMotion
        drag_distance += motion.relative.length()
        if drag_mode == "orbit":
            orbit_yaw -= motion.relative.x * 0.006
            orbit_pitch += motion.relative.y * 0.006
        elif drag_mode == "pan":
            var pan := (camera.global_basis.x * -motion.relative.x + camera.global_basis.y * motion.relative.y) * (orbit_distance * 0.0015)
            camera_target += pan
        _update_camera()
        get_viewport().set_input_as_handled()

func _pick_actor() -> void:
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
    if actors_by_name.has(chosen_name):
        select_actor(actors_by_name[chosen_name])
        for index in range(visible_actors.size()):
            if str(visible_actors[index].get("name", "")) == chosen_name:
                actor_list.select(index)
                actor_list.ensure_current_is_visible()
                break
    else:
        # Report the original render node for BSP or otherwise unlinked geometry.
        _select_mesh_only(closest_mesh)
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
