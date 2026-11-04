extends VBoxContainer
## Research-only original welded-edge neighbor viewer and geometric hinge overlay.
## Uses strictly source-validated v3 cache; does not construct game collision.

const Analyzer = preload("res://source_edge_transition_diagnostics.gd")

var analyzer = Analyzer.new()
var editor_host: Control
var world_root: Node3D
var source_picker: RefCounted
var current: Dictionary = {}
var selected_edge := 0
var last_id := -1
var note: Label
var edge_select: OptionButton
var follow_button: Button
var hinge_limit: SpinBox
var slope_limit: SpinBox
var overlay: MeshInstance3D

func initialize(host: Control, world: Node3D) -> void:
    editor_host = host
    world_root = world
    visible = false
    var header := Label.new()
    header.text = "EXACT SOURCE EDGE LINKS | RESEARCH ONLY"
    add_child(header)
    var row := HFlowContainer.new()
    add_child(row)
    edge_select = OptionButton.new()
    for item in ["AB", "BC", "CA"]:
        edge_select.add_item(item)
    edge_select.item_selected.connect(_on_select_edge)
    row.add_child(edge_select)
    follow_button = Button.new()
    follow_button.text = "Follow original neighbor"
    follow_button.tooltip_text = (
        "Navigate to the sole source-exact connected triangle when two faces"
        + " share the same welded original Level edge. NOT a Havok path.")
    follow_button.pressed.connect(follow_neighbor)
    row.add_child(follow_button)
    var limits := HFlowContainer.new()
    add_child(limits)
    hinge_limit = _spin(limits, "Max hinge", 0., 89.9, 15.)
    slope_limit = _spin(limits, "Max plane slope", 0., 89.9, 45.)
    hinge_limit.tooltip_text = "Geometric threshold only, NOT verified DX2 collision behavior."
    slope_limit.tooltip_text = "Unsigned source plane angle, NOT native walkability."
    note = Label.new()
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)
    _refresh()

func _spin(row: HFlowContainer, prefix: String,
           low: float, high: float, initial: float) -> SpinBox:
    var control := SpinBox.new()
    control.prefix = prefix
    control.suffix = "deg"
    control.min_value = low
    control.max_value = high
    control.step = 1.
    control.value = initial
    control.value_changed.connect(_on_threshold_changed)
    row.add_child(control)
    return control

func _active() -> bool:
    if editor_host == null or source_picker == null:
        return false
    if not bool(editor_host.get("source_collision_mode")) or not bool(source_picker.get("ready")):
        return false
    return (source_picker.get("source_map") == editor_host.get("current_source_map_name")
        and source_picker.get("source_sha256") == editor_host.get("source_gamesys_sha256"))

func activate(picker: RefCounted) -> void:
    reset()
    if picker == null or not bool(picker.get("ready")):
        return
    source_picker = picker
    visible = true
    _refresh()

func reset() -> void:
    source_picker = null
    current.clear()
    last_id = -1
    selected_edge = 0
    visible = false
    _clear_overlay()
    _refresh()

func observe_hit(hit: Dictionary) -> void:
    if not _active():
        reset()
        return
    var raw_id: Variant = hit.get("original_level_triangle_id")
    if typeof(raw_id) not in [TYPE_INT, TYPE_FLOAT]:
        current.clear()
        last_id = -1
        _refresh()
        return
    var tid := int(raw_id)
    if not source_picker.face_index_by_id.has(tid):
        current.clear()
        last_id = -1
        _refresh()
        return
    last_id = tid
    current = analyzer.inspect(source_picker, last_id,
        hinge_limit.value, slope_limit.value)
    selected_edge = 0
    if edge_select != null:
        edge_select.select(0)
    _refresh()

func _on_select_edge(index: int) -> void:
    selected_edge = clampi(index, 0, 2)
    _refresh()

func _on_threshold_changed(_value: float) -> void:
    if _active() and last_id >= 0:
        current = analyzer.inspect(source_picker, last_id,
            hinge_limit.value, slope_limit.value)
    _refresh()

func _selected() -> Dictionary:
    if current.is_empty() or not current.has("edges"):
        return {}
    var edges: Array = current["edges"]
    if selected_edge not in [0,1,2] or edges.size()!=3:
        return {}
    return edges[selected_edge]

func follow_neighbor() -> void:
    var entry := _selected()
    if not _active() or entry.is_empty() or not bool(entry["one_unique_neighbor"]):
        return
    var linked: Array = entry["original_neighbor_triangle_ids"]
    if linked.size()!=1:
        return
    var next_id: int = int(linked[0])
    if not source_picker.face_index_by_id.has(next_id):
        return
    var face: Dictionary = source_picker.triangle_details(next_id)
    if face.is_empty() or bool(face.get("selection_is_ray_hit", true)):
        return
    # Source section navigation has always used centroids, not fabricated ray
    # hits. Keep that property so the step-comparison panel cannot pin one.
    editor_host.call("_show_source_collision_hit", face)

func _clear_overlay() -> void:
    if is_instance_valid(overlay):
        overlay.queue_free()
    overlay = null

func _line(mesh: ImmediateMesh, a: Vector3, b: Vector3, color: Color) -> void:
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(a)
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(b)

func _draw() -> void:
    _clear_overlay()
    var entry := _selected()
    if not _active() or world_root == null or entry.is_empty():
        return
    var ink := ImmediateMesh.new()
    ink.surface_begin(Mesh.PRIMITIVE_LINES)
    var a: Vector3 = entry["edge_start_godot"]
    var b: Vector3 = entry["edge_end_godot"]
    _line(ink, a, b, Color(.15, 1., .4))
    if bool(entry["one_unique_neighbor"]):
        var linked: Array = entry["original_neighbor_triangle_ids"]
        var face: Dictionary = source_picker.triangle_details(int(linked[0]))
        var corners: Array = face.get("vertices_godot", [])
        if corners.size() == 3:
            for i in 3:
                _line(ink, corners[i], corners[(i+1)%3], Color(.95,.42,.98))
    ink.surface_end()
    overlay = MeshInstance3D.new()
    overlay.name = "ResearchOnly_SourceExactEdgeLink_NOT_Havok"
    overlay.mesh = ink
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color.WHITE
    mat.vertex_color_use_as_albedo = true
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.no_depth_test = true
    mat.cull_mode = BaseMaterial3D.CULL_DISABLED
    overlay.material_override = mat
    overlay.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    world_root.add_child(overlay)

func _refresh() -> void:
    var enabled := _active() and not current.is_empty()
    if edge_select != null:
        edge_select.disabled = not enabled
    var selected := _selected()
    if follow_button != null:
        follow_button.disabled = (not enabled or selected.is_empty()
            or not bool(selected.get("one_unique_neighbor", false)))
    if note == null:
        return
    if not enabled:
        note.text = "Select an original collision triangle to inspect exact source edge links."
        _clear_overlay()
        return
    var body := (
        "Original triangle #%d | exact original Level XYZ welding, no epsilon.\n"
        % int(current["original_level_triangle_id"]))
    var codes := ["two-face interior", "open boundary",
        "render-material seam", "non-manifold"]
    for row in current["edges"]:
        var code: int = int(row["source_edge_class_code"])
        var ids: Array = row["original_neighbor_triangle_ids"]
        body += "%s: %s | neighbor IDs %s\n" % [
            row["source_edge_name"], codes[code], str(ids)]
    if not selected.is_empty():
        body += "Selected edge %s, length %.4f original Level units.\n" % [
            selected["source_edge_name"], selected["edge_length_level_units"]]
        if bool(selected["one_unique_neighbor"]):
            body += "Source neighbor #%d | unsigned hinge %.2f°\n" % [
                int(selected["original_neighbor_triangle_ids"][0]),
                float(selected["preview_normal_bend_degrees"])]
            body += "Neighbor plane slope %.2f° | planar sides: %s\n" % [
                float(selected["preview_unsigned_neighbor_slope_degrees"]),
                str(selected["horizontal_opposite_side_test"])]
            body += ("Within chosen smooth/floorlike geometry proxy: %s.\n"
                % str(selected["smooth_floorlike_geometric_proxy"]))
        elif int(selected["original_incident_count"])==1:
            body += "Open source edge: no other MOPP-leaf triangle shares exact endpoints.\n"
        else:
            body += "Non-manifold: multiple incident faces, no unique next triangle.\n"
    body += "No step continuity, clearance, character walkability or Havok runtime verified."
    note.text = body
    _draw()
