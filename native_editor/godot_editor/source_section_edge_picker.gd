extends RefCounted
## Screen-space picking for the exact-weld MOPP-subset edge overlay.
## It is an editor-only selection aid, never a native BSP edge identity claim.

const MAX_EDGE_COUNT := 24576
const MAX_LOCAL_INCIDENCE := 8192
const MAX_EXTERNAL_INCIDENCE := 1024
const CELL_SIZE := 64.0
const MAX_CELLS_PER_EDGE := 64
const PICK_RADIUS_PIXELS := 18.0

const EDGE_CLASSES := [
    "subset_open_boundary",
    "within_section_shared",
    "cross_section_mopp_shared",
    "subset_nonmanifold",
]

static func _valid_number(value: Variant) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value)) and absf(float(value)) <= 1_000_000_000.0)


static func _point(value: Variant) -> Vector3:
    if typeof(value) != TYPE_ARRAY:
        return Vector3(INF, INF, INF)
    var coordinates: Array = value
    if coordinates.size() != 3:
        return Vector3(INF, INF, INF)
    for component in coordinates:
        if not _valid_number(component):
            return Vector3(INF, INF, INF)
    return Vector3(float(coordinates[0]), float(coordinates[1]), float(coordinates[2]))


static func _valid_record(record: Dictionary) -> bool:
    var raw_welds: Variant = record.get("source_weld_ids", null)
    if typeof(raw_welds) != TYPE_ARRAY:
        return false
    var welds: Array = raw_welds
    if (welds.size() != 2 or typeof(welds[0]) != TYPE_INT
        or typeof(welds[1]) != TYPE_INT):
        return false
    var low := int(welds[0])
    var high := int(welds[1])
    var edge_key := str(record.get("edge_key", ""))
    if low < 0 or high <= low or edge_key != "%d:%d" % [low, high]:
        return false
    var source_class: Variant = record.get("source_edge_class_code", null)
    if typeof(source_class) != TYPE_INT or int(source_class) < 0 or int(source_class) > 3:
        return false
    var local_count := int(record.get("section_incidence_count", -1))
    var external_count := int(record.get("cross_section_neighbor_count", -1))
    var representative := int(record.get("representative_cross_section_triangle_id", -2))
    if (local_count < 1 or local_count > MAX_LOCAL_INCIDENCE
        or external_count < 0 or external_count > MAX_EXTERNAL_INCIDENCE
        or (external_count == 0 and representative != -1)
        or (external_count > 0 and representative < 0)):
        return false
    var raw_triangles: Variant = record.get("section_triangle_ids", null)
    if typeof(raw_triangles) != TYPE_ARRAY:
        return false
    var triangle_ids: Array = raw_triangles
    if triangle_ids.size() != local_count:
        return false
    var seen_triangles: Dictionary = {}
    for raw_triangle_id in triangle_ids:
        if typeof(raw_triangle_id) != TYPE_INT or int(raw_triangle_id) < 0:
            return false
        if seen_triangles.has(int(raw_triangle_id)):
            return false
        seen_triangles[int(raw_triangle_id)] = true
    var classification := str(record.get("edge_classification", ""))
    if not EDGE_CLASSES.has(classification):
        return false
    var expected_classification := "subset_open_boundary"
    if local_count >= 3:
        expected_classification = "subset_nonmanifold"
    elif external_count > 0:
        expected_classification = "cross_section_mopp_shared"
    elif local_count == 2:
        expected_classification = "within_section_shared"
    if classification != expected_classification:
        return false
    var a := _point(record.get("a_godot_xyz", null))
    var b := _point(record.get("b_godot_xyz", null))
    return (a.is_finite() and b.is_finite()
        and a.distance_squared_to(b) > 1e-12)


static func _valid_report(details: Dictionary) -> bool:
    if (details.get("schema", "") != "DX2Ed-source-section-topology-v1"
        or details.get("mopp_leaf_subset_only", false) != true
        or details.get("read_only", false) != true
        or details.get("native_map_written", true) != false
        or details.get("native_bsp_surface_verified", true) != false
        or details.get("edge_report_uses_original_float32_weld_ids", false) != true
        or details.get("edge_report_is_mopp_leaf_subset_only", false) != true
        or details.get("analysis_skipped_for_size", true)
        or details.get("analysis_skipped_for_edge_incidence", true)):
        return false
    var source_map := str(details.get("source_map", ""))
    var section_key := str(details.get("source_section_key", ""))
    var source_sha256 := str(details.get("source_sha256", ""))
    if source_map.is_empty() or section_key.is_empty() or source_sha256.length() != 64:
        return false
    for character in source_sha256.to_lower():
        if not "0123456789abcdef".contains(character):
            return false
    if int(details.get("edge_report_cap", -1)) != MAX_EDGE_COUNT:
        return false
    var raw_records: Variant = details.get("edge_records", null)
    if typeof(raw_records) != TYPE_ARRAY:
        return false
    var records: Array = raw_records
    if (records.is_empty() or records.size() > MAX_EDGE_COUNT
        or records.size() != int(details.get("edge_record_count", -1))
        or records.size() != int(details.get("unique_source_edge_count", -2))):
        return false
    var raw_counts: Variant = details.get("edge_classification_counts", null)
    if typeof(raw_counts) != TYPE_DICTIONARY:
        return false
    var expected_counts: Dictionary = raw_counts
    var counts := {
        "subset_open_boundary": 0,
        "within_section_shared": 0,
        "cross_section_mopp_shared": 0,
        "subset_nonmanifold": 0,
    }
    var seen_edges: Dictionary = {}
    var previous_key := ""
    for raw_record in records:
        if typeof(raw_record) != TYPE_DICTIONARY:
            return false
        var record: Dictionary = raw_record
        if not _valid_record(record):
            return false
        var edge_key := str(record.get("edge_key", ""))
        if (seen_edges.has(edge_key)
            or (not previous_key.is_empty() and edge_key < previous_key)):
            return false
        seen_edges[edge_key] = true
        previous_key = edge_key
        var classification := str(record.get("edge_classification", ""))
        counts[classification] = int(counts[classification]) + 1
    var total := 0
    for key in counts:
        total += int(counts[key])
        if int(expected_counts.get(key, -1)) != int(counts[key]):
            return false
    return total == records.size()


static func camera_signature_matches(index: Dictionary, camera: Camera3D,
        viewport_size: Vector2) -> bool:
    if not is_instance_valid(camera) or index.is_empty():
        return false
    return (
        index.get("camera_transform") == camera.global_transform
        and int(index.get("camera_projection", -1)) == int(camera.projection)
        and is_equal_approx(float(index.get("camera_size", -1.0)), camera.size)
        and is_equal_approx(float(index.get("camera_fov", -1.0)), camera.fov)
        and index.get("viewport_size", Vector2.ZERO) == viewport_size
    )


static func build_screen_index(details: Dictionary, camera: Camera3D,
        viewport_size: Vector2) -> Dictionary:
    if (not _valid_report(details) or not is_instance_valid(camera)
        or viewport_size.x <= 0.0 or viewport_size.y <= 0.0):
        return {}
    var cells: Dictionary = {}
    var large_edges: Array = []
    var projected_records: Array = []
    var records: Array = details["edge_records"]
    for raw_record in records:
        var record: Dictionary = raw_record
        var a := _point(record["a_godot_xyz"])
        var b := _point(record["b_godot_xyz"])
        if camera.is_position_behind(a) or camera.is_position_behind(b):
            continue
        var screen_a := camera.unproject_position(a)
        var screen_b := camera.unproject_position(b)
        if (not is_finite(screen_a.x) or not is_finite(screen_a.y)
            or not is_finite(screen_b.x) or not is_finite(screen_b.y)):
            continue
        var min_x := minf(screen_a.x, screen_b.x) - PICK_RADIUS_PIXELS
        var max_x := maxf(screen_a.x, screen_b.x) + PICK_RADIUS_PIXELS
        var min_y := minf(screen_a.y, screen_b.y) - PICK_RADIUS_PIXELS
        var max_y := maxf(screen_a.y, screen_b.y) + PICK_RADIUS_PIXELS
        if (max_x < 0.0 or max_y < 0.0
            or min_x > viewport_size.x or min_y > viewport_size.y):
            continue
        min_x = clampf(min_x, 0.0, viewport_size.x)
        max_x = clampf(max_x, 0.0, viewport_size.x)
        min_y = clampf(min_y, 0.0, viewport_size.y)
        max_y = clampf(max_y, 0.0, viewport_size.y)
        var cell_x0 := floori(min_x / CELL_SIZE)
        var cell_x1 := floori(max_x / CELL_SIZE)
        var cell_y0 := floori(min_y / CELL_SIZE)
        var cell_y1 := floori(max_y / CELL_SIZE)
        var cell_count := (cell_x1 - cell_x0 + 1) * (cell_y1 - cell_y0 + 1)
        var projected_index := projected_records.size()
        projected_records.append({
            "record": record.duplicate(true),
            "edge_key": str(record["edge_key"]),
            "a_screen": screen_a,
            "b_screen": screen_b,
            "a_world": a,
            "b_world": b,
            "depth": camera.global_position.distance_to((a + b) * 0.5),
        })
        if cell_count > MAX_CELLS_PER_EDGE:
            large_edges.append(projected_index)
            continue
        for cell_y in range(cell_y0, cell_y1 + 1):
            for cell_x in range(cell_x0, cell_x1 + 1):
                var cell_key := "%d:%d" % [cell_x, cell_y]
                var bucket: Array = cells.get(cell_key, [])
                bucket.append(projected_index)
                cells[cell_key] = bucket
    return {
        "schema": "DX2Ed-source-section-edge-screen-index-v1",
        "source_sha256": str(details["source_sha256"]),
        "source_section_key": str(details["source_section_key"]),
        "viewport_size": viewport_size,
        "camera_transform": camera.global_transform,
        "camera_projection": int(camera.projection),
        "camera_size": camera.size,
        "camera_fov": camera.fov,
        "cell_size": CELL_SIZE,
        "records": projected_records,
        "cells": cells,
        "large_edges": large_edges,
        "projected_edge_count": projected_records.size(),
        "mopp_leaf_subset_only": true,
        "native_bsp_surface_verified": false,
        "native_map_written": false,
    }


static func pick_edge(index: Dictionary, mouse_pixels: Vector2,
        radius_pixels: float = PICK_RADIUS_PIXELS) -> Dictionary:
    if (index.get("schema", "") != "DX2Ed-source-section-edge-screen-index-v1"
        or index.get("mopp_leaf_subset_only", false) != true
        or index.get("native_bsp_surface_verified", true) != false
        or index.get("native_map_written", true) != false
        or not is_finite(mouse_pixels.x) or not is_finite(mouse_pixels.y)
        or not is_finite(radius_pixels) or radius_pixels <= 0.0
        or radius_pixels > 64.0):
        return {}
    var cell_size := float(index.get("cell_size", 0.0))
    if not is_finite(cell_size) or cell_size <= 0.0:
        return {}
    var cells: Dictionary = index.get("cells", {})
    var key := "%d:%d" % [floori(mouse_pixels.x / cell_size), floori(mouse_pixels.y / cell_size)]
    var candidates: Array = cells.get(key, []).duplicate()
    for raw_index in index.get("large_edges", []):
        candidates.append(raw_index)
    var records: Array = index.get("records", [])
    var seen: Dictionary = {}
    var best: Dictionary = {}
    var best_distance := radius_pixels
    var best_depth := INF
    for raw_index in candidates:
        var record_index := int(raw_index)
        if record_index < 0 or record_index >= records.size() or seen.has(record_index):
            continue
        seen[record_index] = true
        var projected: Dictionary = records[record_index]
        var a_screen: Vector2 = projected["a_screen"]
        var b_screen: Vector2 = projected["b_screen"]
        var segment := b_screen - a_screen
        var denominator := segment.length_squared()
        if denominator <= 1e-12:
            continue
        var t := clampf((mouse_pixels - a_screen).dot(segment) / denominator, 0.0, 1.0)
        var nearest_screen := a_screen + segment * t
        var distance := nearest_screen.distance_to(mouse_pixels)
        var depth := float(projected["depth"])
        if (distance > radius_pixels
            or (distance > best_distance + 0.001)
            or (is_equal_approx(distance, best_distance) and depth >= best_depth)):
            continue
        var a_world: Vector3 = projected["a_world"]
        var b_world: Vector3 = projected["b_world"]
        best_distance = distance
        best_depth = depth
        best = {
            "record": projected["record"].duplicate(true),
            "edge_key": str(projected["edge_key"]),
            "screen_distance_px": distance,
            "screen_point": nearest_screen,
            "world_point": a_world.lerp(b_world, t),
            "a_world": a_world,
            "b_world": b_world,
            "depth_godot_units": depth,
            "source_sha256": str(index["source_sha256"]),
            "source_section_key": str(index["source_section_key"]),
            "mopp_leaf_subset_only": true,
            "native_bsp_surface_verified": false,
            "native_map_written": false,
        }
    return best


static func record_belongs_to_report(details: Dictionary, record: Dictionary) -> bool:
    if not _valid_report(details) or not _valid_record(record):
        return false
    var key := str(record.get("edge_key", ""))
    for raw_record in details.get("edge_records", []):
        var candidate: Dictionary = raw_record
        if (str(candidate.get("edge_key", "")) == key
            and candidate.get("source_weld_ids", []) == record.get("source_weld_ids", [])
            and candidate.get("section_triangle_ids", []) == record.get("section_triangle_ids", [])
            and str(candidate.get("edge_classification", "")) == str(record.get("edge_classification", ""))):
            return true
    return false


static func build_highlight(pick: Dictionary, camera: Camera3D,
        viewport_height: float, color: Color) -> Node3D:
    if (not is_instance_valid(camera) or viewport_height <= 0.0
        or pick.get("mopp_leaf_subset_only", false) != true
        or pick.get("native_bsp_surface_verified", true) != false
        or pick.get("native_map_written", true) != false):
        return null
    var a: Vector3 = pick.get("a_world", Vector3(INF, INF, INF))
    var b: Vector3 = pick.get("b_world", Vector3(INF, INF, INF))
    var point: Vector3 = pick.get("world_point", Vector3(INF, INF, INF))
    if (not a.is_finite() or not b.is_finite() or not point.is_finite()
        or a.distance_squared_to(b) <= 1e-12):
        return null
    var midpoint := (a + b) * 0.5
    var depth := maxf(0.001, camera.global_position.distance_to(midpoint))
    var world_per_pixel := camera.size / viewport_height
    if camera.projection == Camera3D.PROJECTION_PERSPECTIVE:
        world_per_pixel = (2.0 * depth * tan(deg_to_rad(camera.fov * 0.5))
            / viewport_height)
    if not is_finite(world_per_pixel) or world_per_pixel <= 0.0:
        return null
    var direction := (b - a).normalized()
    var view_direction := camera.global_position - midpoint
    if view_direction.length_squared() <= 1e-12:
        view_direction = camera.global_basis.z
    var side := direction.cross(view_direction.normalized())
    if side.length_squared() <= 1e-12:
        side = camera.global_basis.x
    side = side.normalized() * clampf(world_per_pixel * 2.2, 0.0001, 0.25)
    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
    mesh.surface_add_vertex(a - side)
    mesh.surface_add_vertex(b - side)
    mesh.surface_add_vertex(b + side)
    mesh.surface_add_vertex(a - side)
    mesh.surface_add_vertex(b + side)
    mesh.surface_add_vertex(a + side)
    mesh.surface_end()
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.render_priority = 3
    var root := Node3D.new()
    root.name = "SourceCollision_EditorOnly_SelectedEdgeHighlight"
    root.set_meta("editor_only", true)
    var line := MeshInstance3D.new()
    line.name = "ScreenWidthEdgeRibbon_EDITOR_ONLY"
    line.mesh = mesh
    line.material_override = material
    line.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    root.add_child(line)
    var sphere_mesh := SphereMesh.new()
    sphere_mesh.radius = clampf(world_per_pixel * 4.0, 0.0005, 0.5)
    sphere_mesh.height = sphere_mesh.radius * 2.0
    sphere_mesh.radial_segments = 12
    sphere_mesh.rings = 6
    var point_marker := MeshInstance3D.new()
    point_marker.name = "SelectedEdgeScreenPoint_EDITOR_ONLY"
    point_marker.mesh = sphere_mesh
    point_marker.position = point
    point_marker.material_override = material
    point_marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    root.add_child(point_marker)
    return root
