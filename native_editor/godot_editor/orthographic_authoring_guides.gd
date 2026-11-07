extends RefCounted
## DX2Ed/T3Ed-style authoring camera guides.
## Editor viewport ONLY: not part of original GMP/BSP data, scene drafts,
## exported collision, native Save As or any source game map serializer.
const PERSPECTIVE := "Perspective"
const TOP := "Top (XZ)"
const FRONT := "Front (XY)"
const SIDE := "Side (ZY)"
const MODES := [PERSPECTIVE, TOP, FRONT, SIDE]
const MAX_GRID_HALF_LINES := 64


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
