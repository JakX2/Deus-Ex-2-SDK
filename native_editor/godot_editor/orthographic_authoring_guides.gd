extends RefCounted
## DX2Ed/T3Ed-style authoring camera guides.
## Editor viewport ONLY: not part of original GMP/BSP data, scene drafts,
## exported collision, native Save As or any source game map serializer.
const PERSPECTIVE := "Perspective"
const TOP := "Top (XZ)"
const FRONT := "Front (XY)"
const SIDE := "Side (ZY)"
const MODES := [PERSPECTIVE, TOP, FRONT, SIDE]
const VIEW_IDS := ["perspective", "top", "front", "side"]
const SINGLE_LAYOUT := "single"
const QUAD_LAYOUT := "quad"
const MAX_GRID_HALF_LINES := 64
const INTERACTION_LAYER_MASK := 1 << 5


static func valid_mode(mode: String) -> bool:
    return mode in MODES


static func apply_camera(camera: Camera3D, mode: String, target: Vector3,
                         distance: float, yaw: float, pitch: float) -> bool:
    if (not is_instance_valid(camera) or not valid_mode(mode)
        or not target.is_finite() or not is_finite(distance)
        or distance <= 0.0 or not is_finite(yaw) or not is_finite(pitch)):
        return false
    var d := clampf(distance, 0.15, 200000.0)
    if mode == PERSPECTIVE:
        camera.projection = Camera3D.PROJECTION_PERSPECTIVE
        var offset := Vector3(
            sin(yaw) * cos(pitch), sin(pitch),
            cos(yaw) * cos(pitch)) * d
        camera.global_position = target + offset
        camera.look_at(target, Vector3.UP)
    else:
        camera.projection = Camera3D.PROJECTION_ORTHOGONAL
        camera.size = clampf(d * 1.6, 0.25, 300000.0)
        var normal := Vector3.BACK
        var up := Vector3.UP
        if mode == TOP:
            normal = Vector3.UP
            up = Vector3.FORWARD
        elif mode == SIDE:
            normal = Vector3.RIGHT
        camera.global_position = target + normal * d
        camera.look_at(target, up)
    return true


static func grid_center(mode: String, target: Vector3, step: float) -> Vector3:
    if (not valid_mode(mode) or mode == PERSPECTIVE
        or not target.is_finite() or not is_finite(step)
        or step < 0.05 or step > 1024.0):
        return Vector3.ZERO
    return Vector3(
        snappedf(target.x, step), snappedf(target.y, step),
        snappedf(target.z, step))


static func snapped_preview_position(point: Vector3, step: float) -> Vector3:
    # The caller must keep all output in editor preview/draft transforms.
    # This is NOT an original Unreal unit or a source-GMP coordinate writer.
    if (not point.is_finite() or not is_finite(step)
        or step < 0.25 or step > 64.0):
        return point
    return Vector3(
        snappedf(point.x, step), snappedf(point.y, step),
        snappedf(point.z, step))


static func _grid_point(mode: String, origin: Vector3,
                        u: float, v: float) -> Vector3:
    match mode:
        TOP:
            return Vector3(u, origin.y, v)
        FRONT:
            return Vector3(u, v, origin.z)
        SIDE:
            return Vector3(origin.x, v, u)
        _:
            return origin


static func grid_segments(mode: String, target: Vector3, step: float,
                          half_lines: int = 24) -> Array:
    # Bounded preview-only lines, not source-native geometry.
    if (not valid_mode(mode) or mode == PERSPECTIVE
        or not target.is_finite() or not is_finite(step)
        or step < 0.05 or step > 1024.0
        or half_lines < 1 or half_lines > MAX_GRID_HALF_LINES):
        return []
    var center := grid_center(mode, target, step)
    var u := center.x
    var v := center.z
    if mode == FRONT:
        v = center.y
    elif mode == SIDE:
        u = center.z
        v = center.y
    var reach := float(half_lines) * step
    var lines: Array = []
    for index in range(-half_lines, half_lines + 1):
        var offset := float(index) * step
        var parallel_u := PackedVector3Array([
            _grid_point(mode, center, u - reach, v + offset),
            _grid_point(mode, center, u + reach, v + offset),
        ])
        var parallel_v := PackedVector3Array([
            _grid_point(mode, center, u + offset, v - reach),
            _grid_point(mode, center, u + offset, v + reach),
        ])
        lines.append(parallel_u)
        lines.append(parallel_v)
    return lines


static func grid_mesh(mode: String, target: Vector3,
                      step: float, half_lines: int = 24) -> ImmediateMesh:
    var mesh := ImmediateMesh.new()
    var lines := grid_segments(mode, target, step, half_lines)
    if lines.is_empty():
        return mesh
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for index in range(lines.size()):
        var accent := ((index / 2) == half_lines)
        var color := Color(0.35, 0.80, 0.95, 0.66) if accent else Color(0.48, 0.57, 0.66, 0.32)
        for point in lines[index]:
            mesh.surface_set_color(color)
            mesh.surface_add_vertex(point)
    mesh.surface_end()
    return mesh


## Independent editor camera workspace. State is private UI metadata only.


static func valid_layout(layout: String) -> bool:
    return layout == SINGLE_LAYOUT or layout == QUAD_LAYOUT


static func view_id_for_mode(mode: String) -> String:
    match mode:
        PERSPECTIVE:
            return "perspective"
        TOP:
            return "top"
        FRONT:
            return "front"
        SIDE:
            return "side"
        _:
            return ""


static func mode_for_view_id(view_id: String) -> String:
    match view_id:
        "perspective":
            return PERSPECTIVE
        "top":
            return TOP
        "front":
            return FRONT
        "side":
            return SIDE
        _:
            return ""


static func grid_layer_mask(view_id: String) -> int:
    var index := VIEW_IDS.find(view_id)
    if index < 0:
        return 0
    # Bit zero is shared scene geometry; each view owns one isolated grid layer.
    return 1 << (index + 1)


static func make_view_state(target: Vector3, distance: float,
                            yaw: float, pitch: float) -> Dictionary:
    return {
        "target": [target.x, target.y, target.z],
        "distance": distance,
        "yaw": yaw,
        "pitch": pitch,
    }


static func default_view_states(target: Vector3, distance: float,
                                yaw: float, pitch: float) -> Dictionary:
    var state := make_view_state(target, distance, yaw, pitch)
    var result := {}
    for view_id in VIEW_IDS:
        result[view_id] = state.duplicate(true)
    return result


static func _is_number(value: Variant) -> bool:
    return typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT


static func target_from_state(state: Dictionary) -> Vector3:
    var target: Variant = state.get("target", [])
    if typeof(target) != TYPE_ARRAY or target.size() != 3:
        return Vector3.ZERO
    return Vector3(float(target[0]), float(target[1]), float(target[2]))


static func validate_view_states(value: Variant) -> Variant:
    if typeof(value) != TYPE_DICTIONARY or value.size() != VIEW_IDS.size():
        return null
    var result := {}
    for view_id in VIEW_IDS:
        if not value.has(view_id):
            return null
        var state: Variant = value[view_id]
        if (typeof(state) != TYPE_DICTIONARY or state.size() != 4
            or not state.has("target") or not state.has("distance")
            or not state.has("yaw") or not state.has("pitch")):
            return null
        var target: Variant = state["target"]
        if typeof(target) != TYPE_ARRAY or target.size() != 3:
            return null
        var coordinates: Array = []
        for component in target:
            if not _is_number(component):
                return null
            var coordinate := float(component)
            if not is_finite(coordinate) or absf(coordinate) > 1000000.0:
                return null
            coordinates.append(coordinate)
        for key in ["distance", "yaw", "pitch"]:
            if not _is_number(state[key]) or not is_finite(float(state[key])):
                return null
        var distance := float(state["distance"])
        var yaw := float(state["yaw"])
        var pitch := float(state["pitch"])
        if (distance < 0.15 or distance > 200000.0
            or absf(yaw) > 10000.0 or pitch < -1.5 or pitch > 1.5):
            return null
        result[view_id] = {
            "target": coordinates,
            "distance": distance,
            "yaw": yaw,
            "pitch": pitch,
        }
    return result


static func apply_view_camera(camera: Camera3D, view_id: String,
                              state: Dictionary) -> bool:
    if mode_for_view_id(view_id).is_empty():
        return false
    var checked: Variant = validate_view_states(default_view_states(
        target_from_state(state),
        float(state.get("distance", 25.0)),
        float(state.get("yaw", 0.8)),
        float(state.get("pitch", 0.37))))
    if checked == null:
        return false
    return apply_camera(
        camera, mode_for_view_id(view_id), target_from_state(state),
        float(state.get("distance", 25.0)),
        float(state.get("yaw", 0.8)),
        float(state.get("pitch", 0.37)))


## Active-pane editor overlays and orthographic transform constraints.

static func interaction_layer_mask(view_id: String, active_view_id: String) -> int:
    if not VIEW_IDS.has(view_id) or view_id != active_view_id:
        return 0
    return INTERACTION_LAYER_MASK


static func viewport_cull_mask(view_id: String, active_view_id: String) -> int:
    var grid_mask := grid_layer_mask(view_id)
    if grid_mask == 0:
        return 0
    return 1 | grid_mask | interaction_layer_mask(view_id, active_view_id)


static func gizmo_plane_axes(mode: String) -> Array[Vector3]:
    match mode:
        TOP:
            return [Vector3.RIGHT, Vector3.BACK]
        FRONT:
            return [Vector3.RIGHT, Vector3.UP]
        SIDE:
            return [Vector3.UP, Vector3.BACK]
        _:
            return []


static func gizmo_view_normal(mode: String) -> Vector3:
    match mode:
        TOP:
            return Vector3.UP
        FRONT:
            return Vector3.BACK
        SIDE:
            return Vector3.RIGHT
        _:
            return Vector3.ZERO


static func gizmo_axes(mode: String, tool: String) -> Array[Vector3]:
    # Build the typed result explicitly. A ternary expression containing an
    # untyped array literal is inferred as Array and cannot satisfy the
    # Array[Vector3] return contract on Godot 4.3.
    var result: Array[Vector3] = []
    if tool not in ["move", "rotate", "scale"]:
        return result
    if mode == PERSPECTIVE:
        result.append(Vector3.RIGHT)
        result.append(Vector3.UP)
        result.append(Vector3.BACK)
        return result
    if tool == "rotate":
        var normal := gizmo_view_normal(mode)
        if normal != Vector3.ZERO:
            result.append(normal)
        return result
    return gizmo_plane_axes(mode)


static func plane_drag_delta(pivot: Vector3, start_point: Vector3,
                             current_point: Vector3, axes: Array,
                             step: float, snap_enabled: bool) -> Variant:
    if (not pivot.is_finite() or not start_point.is_finite()
        or not current_point.is_finite() or axes.size() != 2):
        return null
    if typeof(axes[0]) != TYPE_VECTOR3 or typeof(axes[1]) != TYPE_VECTOR3:
        return null
    var axis_a: Vector3 = axes[0]
    var axis_b: Vector3 = axes[1]
    if (not axis_a.is_finite() or not axis_b.is_finite()
        or absf(axis_a.length_squared() - 1.0) > 0.001
        or absf(axis_b.length_squared() - 1.0) > 0.001
        or absf(axis_a.dot(axis_b)) > 0.001):
        return null
    if snap_enabled and (not is_finite(step) or step < 0.25 or step > 64.0):
        return null
    var raw_delta := current_point - start_point
    var result := Vector3.ZERO
    for axis in [axis_a, axis_b]:
        var amount := raw_delta.dot(axis)
        if snap_enabled:
            var pivot_coordinate := pivot.dot(axis)
            amount = snappedf(pivot_coordinate + amount, step) - pivot_coordinate
        result += axis * amount
    if not result.is_finite() or result.length() > 1000000.0:
        return null
    return result


static func axis_drag_delta(pivot: Vector3, raw_change: float, axis: Vector3,
                            step: float, snap_enabled: bool) -> Variant:
    if (not pivot.is_finite() or not is_finite(raw_change)
        or not axis.is_finite()
        or absf(axis.length_squared() - 1.0) > 0.001):
        return null
    if snap_enabled and (not is_finite(step) or step < 0.25 or step > 64.0):
        return null
    var amount := raw_change
    if snap_enabled:
        var pivot_coordinate := pivot.dot(axis)
        amount = snappedf(pivot_coordinate + amount, step) - pivot_coordinate
    var result := axis * amount
    if not result.is_finite() or result.length() > 1000000.0:
        return null
    return result
