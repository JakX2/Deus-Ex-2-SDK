extends VBoxContainer
## Editor-only slope/edge/elevation measurements on source-authenticated triangles.
## No Havok, gameplay walkability or native collision changes.

const Diagnostics = preload("res://source_surface_diagnostics.gd")

var diagnostics = Diagnostics.new()
var source_picker: RefCounted
var current: Dictionary = {}
var reference: Dictionary = {}
var last_hit: Dictionary = {}
var note: Label
var pin_button: Button
var slope_limit: SpinBox
var max_step: SpinBox
var max_gap: SpinBox
var marker: MeshInstance3D
var world_root: Node3D

func initialize(world: Node3D) -> void:
    world_root = world
    visible = false
    var heading := Label.new()
    heading.text = "SOURCE SLOPE + STEP DIAGNOSTICS | RESEARCH"
    add_child(heading)
    var controls := HFlowContainer.new()
    add_child(controls)
    pin_button = Button.new()
    pin_button.text = "Pin surface reference"
    pin_button.disabled = true
    pin_button.tooltip_text = "Pin an actual original collision ray hit; select another surface to measure the vertical difference."
    pin_button.pressed.connect(pin_reference)
    controls.add_child(pin_button)
    var clear := Button.new()
    clear.text = "Clear reference"
    clear.pressed.connect(clear_reference)
    controls.add_child(clear)
    var limits := HFlowContainer.new()
    add_child(limits)
    slope_limit = _spin(limits, "Slope ≤", 0.0, 89.9, 45.0, 1.0)
    max_step = _spin(limits, "Step limit", 0.0, 100.0, .5, .1)
    max_gap = _spin(limits, "Max planar gap", .001, 100.0, 1.0, .1)
    slope_limit.tooltip_text = "Unsigned plane slope threshold relative to preview up; NOT a native DX2 walkable slope."
    max_step.tooltip_text = "Comparative vertical offset threshold in original Level units. NOT verified game step height."
    max_gap.tooltip_text = "Max horizontal separation between sampled points in original Level units."
    for field in [slope_limit, max_step, max_gap]:
        field.suffix = "deg" if field == slope_limit else "Level u"
        field.value_changed.connect(_limits_changed)
    note = Label.new()
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(note)
    _refresh()

func _spin(parent: HFlowContainer, prefix: String, lo: float, hi: float,
           value: float, inc: float) -> SpinBox:
    var input := SpinBox.new()
    input.prefix = prefix
    input.min_value = lo
    input.max_value = hi
    input.step = inc
    input.value = value
    parent.add_child(input)
    return input

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
    reference.clear()
    last_hit.clear()
    visible = false
    _clear_marker()
    _refresh()

func _valid_source() -> bool:
    return (source_picker != null and bool(source_picker.get("ready"))
        and str(source_picker.get("source_map")).to_lower().ends_with(".gmp")
        and str(source_picker.get("source_sha256")).length() == 64)

func observe_hit(hit: Dictionary) -> void:
    if not _valid_source():
        reset()
        return
    last_hit = hit.duplicate(true)
    current = diagnostics.inspect(source_picker, last_hit, slope_limit.value)
    if not current.is_empty() and not reference.is_empty():
        if (current["source_map"] != reference["source_map"]
            or current["source_sha256"] != reference["source_sha256"]):
            reference.clear()
    _refresh()

func pin_reference() -> void:
    if not _valid_source() or current.is_empty() or not bool(current.get("source_pick_is_ray_hit", false)):
        return
    reference = current.duplicate(true)
    _refresh()

func clear_reference() -> void:
    reference.clear()
    _refresh()

func _limits_changed(_value: float) -> void:
    if _valid_source() and not last_hit.is_empty():
        current = diagnostics.inspect(source_picker, last_hit, slope_limit.value)
    _refresh()

func _clear_marker() -> void:
    if is_instance_valid(marker):
        marker.queue_free()
    marker = null

func _line(mesh: ImmediateMesh, a: Vector3, b: Vector3, color: Color) -> void:
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(a)
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(b)

func _draw_pair() -> void:
    _clear_marker()
    if world_root == null or reference.is_empty() or current.is_empty():
        return
    var report: Dictionary = diagnostics.compare(
        reference, current, max_gap.value, max_step.value, slope_limit.value)
    if report.is_empty() or not bool(report["nearby_sampled_footprints"]):
        return
    var a: Vector3 = reference["point_godot"]
    var b: Vector3 = current["point_godot"]
    var elbow := Vector3(b.x, a.y, b.z)
    var ink := ImmediateMesh.new()
    ink.surface_begin(Mesh.PRIMITIVE_LINES)
    var cyan := Color(.15, .85, 1.0)
    var amber := Color(1.0, .68, .16)
    _line(ink, a, elbow, cyan)
    _line(ink, elbow, b, amber)
    var size := 0.025
    for pos in [a, b]:
        _line(ink, pos - Vector3.RIGHT * size, pos + Vector3.RIGHT * size, amber)
        _line(ink, pos - Vector3.FORWARD * size, pos + Vector3.FORWARD * size, amber)
    ink.surface_end()
    marker = MeshInstance3D.new()
    marker.name = "ResearchOnly_SourceSurfaceElevation_NOT_Havok"
    marker.mesh = ink
    var material := StandardMaterial3D.new()
    material.albedo_color = Color.WHITE
    material.vertex_color_use_as_albedo = true
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    marker.material_override = material
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    world_root.add_child(marker)

func _refresh() -> void:
    if pin_button != null:
        pin_button.disabled = (not _valid_source() or current.is_empty()
            or not bool(current.get("source_pick_is_ray_hit", false)))
    if note == null:
        return
    if not _valid_source():
        note.text = "Enable original source collision inspection to measure triangle geometry."
        _clear_marker()
        return
    var text := "Unsigned triangle plane slopes; never inferred walkability or collision response.\n"
    if current.is_empty():
        text += "Click an original MOPP-linked triangle to inspect its geometry."
    else:
        text += "Original Level triangle #%d | unsigned slope: %.2f° (limit %.2f°)\n" % [
            int(current["original_level_triangle_id"]),
            float(current["unsigned_plane_slope_degrees"]),
            slope_limit.value]
        text += "Within user slope threshold: %s (geometry only)\n" % str(
            current["unsigned_plane_slope_degrees"] <= slope_limit.value)
        text += "Nearest source edge: %s | %.4f original Level units away\n" % [
            ["AB", "BC", "CA"][int(current["nearest_edge_ab_bc_ca"])],
            float(current["nearest_edge_distance_level_units"])]
        var names: Array = current["edge_classes"]
        var rises: Array = current["edge_unsigned_rise_level_units"]
        var grades: Array = current["edge_incline_degrees"]
        for i in 3:
            text += "  %s: %s | rise %.4f Level u | incline %.1f°\n" % [
                ["AB", "BC", "CA"][i], names[i], float(rises[i]), float(grades[i])]
        if not bool(current["source_pick_is_ray_hit"]):
            text += "Section navigation uses a centroid; pinning requires a real ray click.\n"
    if not reference.is_empty():
        text += "Pinned original Level triangle #%d.\n" % int(
            reference["original_level_triangle_id"])
        if not current.is_empty():
            var report: Dictionary = diagnostics.compare(
                reference, current, max_gap.value, max_step.value, slope_limit.value)
            if not report.is_empty():
                text += "Selected relative elevation: %+.4f Level u | planar gap %.4f Level u.\n" % [
                    float(report["signed_height_difference_level_units"]),
                    float(report["horizontal_gap_level_units"])]
                if bool(report["same_original_triangle"]):
                    text += "Same triangle: plane rise, NOT a separate step.\n"
                elif not bool(report["nearby_sampled_footprints"]):
                    text += "Samples too far apart in plan view; no local step inference.\n"
                elif not bool(report["both_unsigned_slopes_within_limit"]):
                    text += "One or both planes exceed chosen slope threshold.\n"
                elif bool(report["vertical_discontinuity_proxy_only"]):
                    text += "Vertical-offset proxy %s chosen height limit; NO topology/walkability proof.\n" % (
                        "within" if bool(report["within_user_step_height_threshold"]) else "exceeds")
                else:
                    text += "No significant measured vertical offset.\n"
    text += "Render seams are NOT physics materials. Real DX2/Havok steps not verified."
    note.text = text
    _draw_pair()
