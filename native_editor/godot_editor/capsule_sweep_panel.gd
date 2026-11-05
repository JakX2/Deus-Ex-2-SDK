extends VBoxContainer
## Optional interactive capsule-sweep research panel. Everything is read-only.
## Host supplies only existing source-authenticated picker, private cache path,
## and validated PR #47 overlay loader. No editable map or gameplay physics.

const PickState = preload("res://capsule_sweep_picks.gd")
const ExactChord = preload("res://source_edge_capsule_chord.gd")
const HeightOverlay = preload("res://source_edge_capsule_height_overlay.gd")
const HeightReplay = preload("res://source_edge_capsule_height_replay.gd")
const PythonRuntime = preload("res://python_runtime.gd")

var editor_host: Control
var picks = PickState.new()
var start_button: Button
var end_button: Button
var run_button: Button
var start_offset: SpinBox
var end_offset: SpinBox
var radius: SpinBox
var half_axis: SpinBox
var note: Label
var worker: Thread = null
var pending_map := ""
var pending_hash := ""
var pending_folder := ""
var pending_output := ""
var pending_profile_offsets: Array = []
var profile_summary := ""
var height_overlay = HeightOverlay.new()
var height_overlay_marker: MeshInstance3D
var clear_profile_button: Button
var pending_profile_start := Vector3.ZERO
var pending_profile_end := Vector3.ZERO
var pending_profile_radius := 0.0
var pending_profile_half_axis := 0.0
var pending_profile_chord: Dictionary = {}
var profile_chord: Dictionary = {}
var pending_replay_plan: Dictionary = {}
var replay_checker = HeightReplay.new()
var replay_choice: OptionButton
var replay_button: Button

func initialize(host: Control) -> void:
    editor_host = host
    visible = false
    var title := Label.new()
    title.text = "INTERACTIVE CAPSULE SWEEP | RESEARCH ONLY"
    add_child(title)
    var actions := HFlowContainer.new()
    add_child(actions)
    start_button = Button.new()
    start_button.text = "Pick Start"
    start_button.pressed.connect(_begin.bind(1))
    actions.add_child(start_button)
    end_button = Button.new()
    end_button.text = "Pick End"
    end_button.pressed.connect(_begin.bind(2))
    actions.add_child(end_button)
    run_button = Button.new()
    run_button.text = "Run read-only sweep"
    run_button.pressed.connect(_run_research)
    actions.add_child(run_button)
    var clear_button := Button.new()
    clear_button.text = "Clear points"
    clear_button.pressed.connect(_clear_picks)
    actions.add_child(clear_button)
    clear_profile_button = Button.new()
    clear_profile_button.text = "Clear height paths"
    clear_profile_button.tooltip_text = (
        "Remove the editor-only multi-height lines; never changes source assets.")
    clear_profile_button.pressed.connect(clear_profile_display)
    actions.add_child(clear_profile_button)
    replay_choice = OptionButton.new()
    replay_choice.tooltip_text = "Choose a verified capsule height to replay at full contact detail."
    actions.add_child(replay_choice)
    replay_button = Button.new()
    replay_button.text = "Inspect selected height"
    replay_button.tooltip_text = (
        "Re-run the independent original-GMP capsule oracle for one height. "
        + "Show detailed first-contact wireframe; never Havok walkability.")
    replay_button.pressed.connect(_replay_selected_height)
    actions.add_child(replay_button)
    var controls := HFlowContainer.new()
    add_child(controls)
    start_offset = _number(controls, "Start offset", -100.0, 100.0, 2.0, .1)
    end_offset = _number(controls, "End offset", -100.0, 100.0, -2.0, .1)
    radius = _number(controls, "Radius", .01, 20.0, .2, .05)
    half_axis = _number(controls, "Half-axis", 0.0, 20.0, .5, .1)
    start_offset.tooltip_text = "Signed Level-unit offset along original triangle winding normal."
    end_offset.tooltip_text = "Signed Level-unit offset along original triangle winding normal."
    half_axis.tooltip_text = "Fixed original Level +Z axis, not authenticated DX2 player capsule."
    note = Label.new()
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)
    _refresh()

func _number(row: HFlowContainer, label: String,
             low: float, high: float, initial: float, increment: float) -> SpinBox:
    var field := SpinBox.new()
    field.prefix = label
    field.suffix = "Level u"
    field.min_value = low
    field.max_value = high
    field.step = increment
    field.value = initial
    row.add_child(field)
    return field

func _status(message: String) -> void:
    if editor_host != null:
        var label: Variant = editor_host.get("status_label")
        if label is Label:
            label.text = message

func _picker() -> RefCounted:
    if editor_host == null:
        return null
    var obj: Variant = editor_host.get("source_collision_picker")
    return obj as RefCounted

func _active() -> bool:
    if editor_host == null or not bool(editor_host.get("source_collision_mode")):
        return false
    var selection := _picker()
    if selection == null or not bool(selection.get("ready")):
        return false
    var name := str(editor_host.get("current_source_map_name"))
    var sha := str(editor_host.get("source_gamesys_sha256"))
    return (selection.get("source_map") == name
        and selection.get("source_sha256") == sha
        and name.length() > 4 and sha.length() == 64)

func _refresh() -> void:
    if note != null:
        note.text = picks.description()
        if not profile_summary.is_empty():
            note.text += "\n\n" + profile_summary
    var disabled := not _active() or worker != null
    if start_button != null:
        start_button.disabled = disabled
    if end_button != null:
        end_button.disabled = disabled
    if run_button != null:
        run_button.disabled = disabled or not picks.can_run()
    if clear_profile_button != null:
        clear_profile_button.disabled = worker != null or not height_overlay.ready
    if replay_choice != null:
        replay_choice.disabled = disabled or not height_overlay.ready
    if replay_button != null:
        replay_button.disabled = disabled or not height_overlay.ready

func activate() -> void:
    clear_profile_display()
    picks.clear()
    visible = true
    _refresh()

func reset() -> void:
    clear_profile_display()
    picks.clear()
    visible = false
    _refresh()

func finish() -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null
    reset()

func _clear_picks() -> void:
    clear_profile_display()
    picks.clear()
    _refresh()

func _begin(which: int) -> void:
    if not _active() or worker != null:
        _status("Original source collision inspection must be active.")
        return
    clear_profile_display()
    if not picks.begin_pick(which,
        str(editor_host.get("current_source_map_name")),
        str(editor_host.get("source_gamesys_sha256"))):
        _status(picks.last_error)
        return
    _refresh()
    _status("Click an original collision surface to set capsule %s."
        % ("START" if which == 1 else "END"))

# Called only by source-exact edge transition Inspector after its geometric
# solver independently verifies a unique original shared edge and a finite
# crossing. Reuse the same private read-only Python worker as manual picks.
func prepare_exact_edge_chord(chord: Dictionary) -> bool:
    if not _active() or worker != null:
        _status("Original source collision inspector not authenticated for edge probe.")
        return false
    var selection := _picker()
    # Never trust an unchecked dictionary supplied from another UI panel:
    # reconstruct the selected edge chord from the authenticated v3 cache.
    var recomputed: Dictionary = ExactChord.new().build(
        selection, int(chord.get("source_original_triangle_id", -1)),
        int(chord.get("source_edge_slot", -1)),
        float(chord.get("interior_fraction", -1.)),
        float(chord.get("above_face_vertical_offset_level_units", -1.)),
        float(chord.get("radius_level_units", -1.)),
        float(chord.get("axis_half_length_level_units", -1.)),
        float(chord.get("bend_limit_degrees", 15.)),
        float(chord.get("slope_limit_degrees", 45.)))
    if (recomputed.is_empty()
        or recomputed["neighbor_original_triangle_id"] != chord.get("neighbor_original_triangle_id")
        or recomputed["source_sha256"] != chord.get("source_sha256")
        or not (chord.get("start_godot_xyz") is Vector3)
        or not (chord.get("end_godot_xyz") is Vector3)):
        _status("Edge crossing rejected: not reproducible from current exact source cache.")
        return false
    var original_start: Vector3 = chord["start_godot_xyz"]
    var original_end: Vector3 = chord["end_godot_xyz"]
    var expected_start: Vector3 = recomputed["start_godot_xyz"]
    var expected_end: Vector3 = recomputed["end_godot_xyz"]
    if (expected_start.distance_to(original_start) > .000001
        or expected_end.distance_to(original_end) > .000001):
        _status("Edge crossing rejected: not reproducible from current exact source cache.")
        return false
    var face_ids: Dictionary = selection.get("face_index_by_id")
    if not picks.load_exact_edge_chord(chord, face_ids,
        str(editor_host.get("current_source_map_name")),
        str(editor_host.get("source_gamesys_sha256"))):
        _status("Original edge probe refused: " + picks.last_error)
        return false
    radius.value = float(chord["radius_level_units"])
    half_axis.value = float(chord["axis_half_length_level_units"])
    clear_profile_display()
    _refresh()
    _status("Original source edge crossing prepared; no Havok or game map changes.")
    return true

# The profile preview never enters the imported GLB, actor drafts, or collision.
func clear_profile_display() -> void:
    height_overlay.clear()
    profile_chord.clear()
    if replay_choice != null:
        replay_choice.clear()
    if is_instance_valid(height_overlay_marker):
        height_overlay_marker.queue_free()
    height_overlay_marker = null
    profile_summary = ""
    _refresh()

func _show_height_overlay() -> bool:
    if not _active() or not height_overlay.ready:
        return false
    var parent: Variant = editor_host.get("world_root")
    if not (parent is Node3D):
        return false
    var mesh: ImmediateMesh = height_overlay.make_mesh()
    if mesh == null:
        return false
    var marker := MeshInstance3D.new()
    marker.name = "ResearchOnly_SourceEdgeCapsuleHeightPaths_NOT_GamePhysics"
    marker.mesh = mesh
    var ink := StandardMaterial3D.new()
    ink.vertex_color_use_as_albedo = true
    ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    ink.cull_mode = BaseMaterial3D.CULL_DISABLED
    ink.no_depth_test = true
    marker.material_override = ink
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    (parent as Node3D).add_child(marker)
    height_overlay_marker = marker
    return true

func _replay_selected_height() -> void:
    if (replay_choice == null or not height_overlay.ready
        or replay_choice.get_selected_id() < 0):
        _status("No authenticated capsule profile elevation is selected.")
        return
    _run_research([], replay_choice.get_selected_id())

# The profile path must still be reproducible from current authenticated
# original source-edge connectivity. No UI-selected or JSON-supplied chord is trusted.
func prepare_height_replay(index: int, output: String) -> Dictionary:
    if (not _active() or worker != null or not height_overlay.ready
        or profile_chord.is_empty() or not picks.can_run()
        or picks.source_map != height_overlay.source_map
        or picks.source_sha256 != height_overlay.source_sha256
        or picks.start_preview.distance_to(height_overlay.start) > .00001
        or picks.end_preview.distance_to(height_overlay.finish) > .00001):
        return {}
    var source := str(editor_host.get("last_gmp_path"))
    var selection := _picker()
    var current: Dictionary = ExactChord.new().build(
        selection, int(profile_chord.get("source_original_triangle_id", -1)),
        int(profile_chord.get("source_edge_slot", -1)),
        float(profile_chord.get("interior_fraction", -1.)),
        float(profile_chord.get("above_face_vertical_offset_level_units", -1.)),
        float(profile_chord.get("radius_level_units", -1.)),
        float(profile_chord.get("axis_half_length_level_units", -1.)),
        float(profile_chord.get("bend_limit_degrees", -1.)),
        float(profile_chord.get("slope_limit_degrees", -1.)))
    if (current.is_empty()
        or current.get("neighbor_original_triangle_id") != profile_chord.get("neighbor_original_triangle_id")
        or current.get("source_sha256") != height_overlay.source_sha256
        or (current["start_godot_xyz"] as Vector3).distance_to(height_overlay.start) > .000001
        or (current["end_godot_xyz"] as Vector3).distance_to(height_overlay.finish) > .000001):
        return {}
    return replay_checker.plan(
        height_overlay, index, source, output,
        str(editor_host.get("current_source_map_name")),
        str(editor_host.get("source_gamesys_sha256")), current)

func run_exact_edge_chord(chord: Dictionary) -> void:
    if prepare_exact_edge_chord(chord):
        _run_research()

# Height samples are strictly upward translations of the exact source
# reconstructed chord, not a player-controller step-height test.
func profile_height_offsets(base_level: float, count: int, step: float) -> Array:
    if (not is_finite(base_level) or base_level < 0. or base_level > 100.
        or count < 2 or count > 9
        or not is_finite(step) or step < .1 or step > 10.
        or base_level + float(count-1) * step > 100.):
        return []
    var offsets: Array = []
    for i in count:
        offsets.append(float(i) * step)
    return offsets

func run_exact_edge_profile(chord: Dictionary, count: int, step: float) -> void:
    if not prepare_exact_edge_chord(chord):
        return
    var offsets := profile_height_offsets(
        float(chord["above_face_vertical_offset_level_units"]), count, step)
    if offsets.is_empty():
        _status("Profile refused: height range must remain inside source chord bounds.")
        return
    _run_research(offsets, -1, chord)


func capture_pending() -> bool:
    return picks.picking != 0

func accept_source_hit(hit: Dictionary) -> bool:
    if not _active() or picks.picking == 0 or worker != null:
        return false
    var selection := _picker()
    var which: int = int(picks.picking)
    var offset := start_offset.value if which == 1 else end_offset.value
    if not picks.capture_hit(hit, selection.get("face_index_by_id"),
        str(editor_host.get("current_source_map_name")),
        str(editor_host.get("source_gamesys_sha256")), offset):
        _status("Capsule point rejected: " + picks.last_error)
        return false
    _refresh()
    _status("Capsule %s captured on original Level triangle #%d (read-only)."
        % [("START" if which == 1 else "END"),
           int(hit.get("original_level_triangle_id", -1))])
    return true

func _run_research(height_offsets: Array = [], replay_index: int = -1,
                   original_chord: Dictionary = {}) -> void:
    if not _active() or worker != null or not picks.can_run():
        _status("Pick two distinct source collision points before running a sweep.")
        return
    var source := str(editor_host.get("last_gmp_path"))
    var folder := str(editor_host.get("current_folder"))
    var sha := str(editor_host.get("source_gamesys_sha256"))
    var maps_folder := source.get_base_dir().simplify_path()
    var dest_folder := folder.simplify_path()
    if (not FileAccess.file_exists(source) or
        folder.is_empty() or dest_folder == maps_folder
        or dest_folder.begins_with(maps_folder + "/")):
        _status("Research output refused: private cache must be outside retail Maps.")
        return
    var exporter := ProjectSettings.globalize_path(
        "res://../../research/dx2/export_capsule_first_contact_preview.py").simplify_path()
    if not FileAccess.file_exists(exporter):
        _status("Research exporter unavailable. Use the full DX2SDK checkout.")
        return
    var output := ""
    for attempt in 20:
        var candidate := folder.path_join(
            "capsule_live_%d_%d.json" % [Time.get_ticks_usec(), attempt])
        if not FileAccess.file_exists(candidate):
            output = candidate
            break
    if output.is_empty():
        _status("Unable to allocate a fresh private capsule preview JSON.")
        return
    var replay_plan: Dictionary = {}
    var options := PackedStringArray()
    if replay_index >= 0:
        replay_plan = prepare_height_replay(replay_index, output)
        if replay_plan.is_empty():
            _status("Height replay refused: source edge, hash, path or sample changed.")
            return
        options = replay_plan["arguments"]
    else:
        options = picks.export_arguments(source, output, radius.value, half_axis.value)
    if options.is_empty():
        _status("Capsule shape/path rejected: " + picks.last_error)
        return
    var args := PackedStringArray([exporter])
    args.append_array(options)
    if not height_offsets.is_empty():
        args.append("--height-offsets")
        for offset in height_offsets:
            args.append(str(offset))
    pending_map = source
    pending_hash = sha
    pending_folder = folder
    pending_output = output
    if replay_index < 0:
        clear_profile_display()
    pending_replay_plan = replay_plan.duplicate(true)
    pending_profile_chord = original_chord.duplicate(true)
    pending_profile_offsets = height_offsets.duplicate()
    pending_profile_start = picks.start_preview
    pending_profile_end = picks.end_preview
    pending_profile_radius = radius.value
    pending_profile_half_axis = half_axis.value
    worker = Thread.new()
    var code := worker.start(
        _worker_run.bind(args, output, source, sha, folder))
    if code != OK:
        worker = null
        _status("Research worker could not start: " + error_string(code))
        _refresh()
        return
    _refresh()
    _status("Running source-Level capsule contact research on original map...")

func _worker_run(args: PackedStringArray, output: String,
                 source: String, sha: String, folder: String) -> void:
    var results: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, results, true)
    if code == -1:
        var windows := PackedStringArray(["-3"])
        windows.append_array(args)
        results.clear()
        code = OS.execute("py", windows, results, true)
    call_deferred("_research_finished", code, "\n".join(results),
        output, source, sha, folder)

func _research_finished(code: int, output_text: String, output: String,
                        source: String, sha: String, folder: String) -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null
    _refresh()
    if (not _active() or source != str(editor_host.get("last_gmp_path"))
        or sha != str(editor_host.get("source_gamesys_sha256"))
        or folder != str(editor_host.get("current_folder"))
        or pending_map != source or pending_hash != sha
        or pending_folder != folder or pending_output != output):
        clear_profile_display()
        _status("Stale capsule result discarded after source map change.")
        return
    var result: Variant = null
    for line in output_text.strip_edges().split("\n"):
        var decoded: Variant = JSON.parse_string(line.strip_edges())
        if typeof(decoded) == TYPE_DICTIONARY and decoded.has("status"):
            result = decoded
    if code != 0 or typeof(result) != TYPE_DICTIONARY or result.get("status") != "ok":
        _status("Capsule research solver refused: " +
            (str(result.get("reason", "Python unavailable")).left(180)
                if typeof(result) == TYPE_DICTIONARY else "Python unavailable"))
        return
    if not FileAccess.file_exists(output):
        _status("Research solver reported success without producing a sidecar.")
        return
    if not pending_replay_plan.is_empty():
        var raw: Variant = JSON.parse_string(FileAccess.get_file_as_string(output))
        if (typeof(raw) != TYPE_DICTIONARY or not height_overlay.ready
            or height_overlay.source_map != str(editor_host.get("current_source_map_name"))
            or height_overlay.source_sha256 != sha
            or not replay_checker.verify_replay_document(
                raw, pending_replay_plan, _picker().get("face_index_by_id"))):
            _status("Detailed replay refused: geometry differs from original profile.")
            return
        editor_host.call("_load_capsule_research_preview", output)
        _refresh()
        _status("Original source capsule height replay verified; NOT Havok gameplay.")
        return
    if not pending_profile_offsets.is_empty():
        var document: Variant = JSON.parse_string(
            FileAccess.get_file_as_string(output))
        if (typeof(document) != TYPE_DICTIONARY
            or document.get("schema") != "DX2Ed-source-edge-capsule-height-profile-v1"
            or document.get("source_map") != str(editor_host.get("current_source_map_name"))
            or document.get("source_sha256") != sha
            or document.get("read_only") != true
            or document.get("original_game_assets_modified") != false
            or document.get("havok_runtime_contact_verified") != false
            or document.get("contact_is_not_a_blocking_classifier") != true
            or document.get("no_contact_is_not_proof_of_walkability") != true):
            _status("Height profile refused: wrong schema, source hash or research flags.")
            return
        var samples: Variant = document.get("profile_samples", [])
        if typeof(samples) != TYPE_ARRAY or samples.size() != pending_profile_offsets.size():
            _status("Height profile refused: incomplete original source samples.")
            return
        if not height_overlay.load_document(
            document, str(editor_host.get("current_source_map_name")), sha,
            pending_profile_start, pending_profile_end, pending_profile_offsets,
            pending_profile_radius, pending_profile_half_axis,
            _picker().get("face_index_by_id")):
            _status("Height profile overlay refused: " + height_overlay.last_error)
            return
        var summary := "CAPSULE HEIGHT PROFILE | geometric contacts only\n"
        summary += "Offsets relative to authenticated baseline (original Level +Z):\n"
        var valid_ids: Dictionary = _picker().get("face_index_by_id")
        for i in samples.size():
            var sample: Variant = samples[i]
            if typeof(sample) != TYPE_DICTIONARY:
                _status("Height profile refused: malformed sample.")
                return
            var height: Variant = sample.get("relative_height_level_units")
            var number: Variant = sample.get("geometric_source_triangle_hits")
            var hit: Variant = sample.get("first_hit_original_triangle_id")
            if (typeof(height) not in [TYPE_INT,TYPE_FLOAT]
                or not is_finite(float(height))
                or absf(float(height)-float(pending_profile_offsets[i])) > .0001
                or typeof(number) not in [TYPE_INT,TYPE_FLOAT]
                or not is_finite(float(number)) or float(number) != float(int(number))
                or int(number) < 0
                or (hit != null and (typeof(hit) not in [TYPE_INT,TYPE_FLOAT]
                    or not is_finite(float(hit)) or float(hit) != float(int(hit))
                    or not valid_ids.has(int(hit))))
                or (int(number) == 0 and hit != null)
                or (int(number) > 0 and hit == null)):
                _status("Height profile refused: invalid offset or source triangle ID.")
                return
            var contact := "no geometric contact" if int(number) == 0 else (
                "%d source contacts; first triangle #%d" % [int(number), int(hit)])
            summary += "+%.2f Level u: %s\n" % [float(height), contact]
        summary += "Floor support may count as contact; no Havok walkability inferred."
        profile_summary = summary + "\n" + height_overlay.description()
        profile_chord = pending_profile_chord.duplicate(true)
        if replay_choice != null:
            replay_choice.clear()
            for row in height_overlay.profile_rows:
                var desc := ("+%.2f Level u | %d source contacts"
                    % [float(row["offset"]), int(row["count"])])
                replay_choice.add_item(desc)
            replay_choice.select(0)
        if not _show_height_overlay():
            clear_profile_display()
            _status("Height profile lines unavailable: no authenticated 3D editor scene.")
            return
        _refresh()
        _status("Read-only height profile and 3D contact-path comparison loaded.")
        return
    editor_host.call("_load_capsule_research_preview", output)
    _refresh()
