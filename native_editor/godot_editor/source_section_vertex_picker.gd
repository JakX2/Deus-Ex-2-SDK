extends RefCounted
## Exact-weld MOPP-subset vertex handles and screen-space picking.
## These are original Level float32 position identities, not native BSP vertex IDs.

const SourceSectionEdgePicker = preload("res://source_section_edge_picker.gd")
const MAX_EDGE_COUNT := 24576
const MAX_VERTEX_COUNT := 49152
const MAX_EDGES_PER_VERTEX := 4096
const MAX_TRIANGLES_PER_VERTEX := 8192
const MAX_EXTERNAL_REPRESENTATIVES_PER_VERTEX := 1024
const CELL_SIZE := 32.0
const PICK_RADIUS_PIXELS := 12.0

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

static func _valid_vertex_report(report: Dictionary) -> bool:
    if (report.get("schema", "") != "DX2Ed-source-section-vertex-report-v1"
        or report.get("mopp_leaf_subset_only", false) != true
        or report.get("exact_original_float32_weld_ids", false) != true
        or report.get("native_bsp_vertex_verified", true) != false
        or report.get("native_map_written", true) != false
        or int(report.get("max_edge_count", -1)) != MAX_EDGE_COUNT
        or int(report.get("max_vertex_count", -1)) != MAX_VERTEX_COUNT
        or int(report.get("max_edges_per_vertex", -1)) != MAX_EDGES_PER_VERTEX
        or int(report.get("max_triangles_per_vertex", -1)) != MAX_TRIANGLES_PER_VERTEX
        or int(report.get("max_external_representatives_per_vertex", -1)) != MAX_EXTERNAL_REPRESENTATIVES_PER_VERTEX):
        return false
    var source_map := str(report.get("source_map", ""))
    var section_key := str(report.get("source_section_key", ""))
    var source_sha256 := str(report.get("source_sha256", ""))
    if source_map.is_empty() or section_key.is_empty() or source_sha256.length() != 64:
        return false
    for character in source_sha256.to_lower():
        if not "0123456789abcdef".contains(character):
            return false
    var raw_edge_count: Variant = report.get("source_edge_report_count", null)
    if (typeof(raw_edge_count) != TYPE_INT or int(raw_edge_count) < 1
        or int(raw_edge_count) > MAX_EDGE_COUNT):
        return false
    for key in ["source_block_id", "render_block_ordinal", "render_section_ordinal"]:
        var raw_tuple_value: Variant = report.get(key, null)
        if typeof(raw_tuple_value) != TYPE_INT or int(raw_tuple_value) < 0:
            return false
    var raw_records: Variant = report.get("vertex_records", null)
    if typeof(raw_records) != TYPE_ARRAY:
        return false
    var records: Array = raw_records
    if (records.is_empty() or records.size() > MAX_VERTEX_COUNT
        or records.size() != int(report.get("vertex_record_count", -1))
        or records.size() != int(report.get("unique_source_vertex_count", -2))):
        return false
    var seen_ids: Dictionary = {}
    var previous_id := -1
    for raw_record in records:
        if typeof(raw_record) != TYPE_DICTIONARY:
            return false
        var record: Dictionary = raw_record
        var raw_id: Variant = record.get("weld_id", null)
        if typeof(raw_id) != TYPE_INT:
            return false
        var weld_id := int(raw_id)
        if (weld_id < 0 or weld_id <= previous_id
            or str(record.get("vertex_key", "")) != str(weld_id)
            or seen_ids.has(weld_id)):
            return false
        seen_ids[weld_id] = true
        previous_id = weld_id
        if not _point(record.get("godot_xyz", null)).is_finite():
            return false
        var raw_edges: Variant = record.get("incident_edge_keys", null)
        if typeof(raw_edges) != TYPE_ARRAY:
            return false
        var edge_keys: Array = raw_edges
        if edge_keys.is_empty() or edge_keys.size() > MAX_EDGES_PER_VERTEX:
            return false
        var seen_edges: Dictionary = {}
        var previous_edge := ""
        for raw_edge_key in edge_keys:
            if typeof(raw_edge_key) != TYPE_STRING:
                return false
            var edge_key := str(raw_edge_key)
            var parts := edge_key.split(":")
            if (parts.size() != 2
                or edge_key != "%d:%d" % [int(parts[0]), int(parts[1])]
                or int(parts[0]) < 0 or int(parts[1]) <= int(parts[0])
                or (int(parts[0]) != weld_id and int(parts[1]) != weld_id)
                or seen_edges.has(edge_key)
                or (not previous_edge.is_empty() and edge_key < previous_edge)):
                return false
            seen_edges[edge_key] = true
            previous_edge = edge_key
        var raw_triangles: Variant = record.get("incident_level_triangle_ids", null)
        if typeof(raw_triangles) != TYPE_ARRAY:
            return false
        var triangle_ids: Array = raw_triangles
        if triangle_ids.is_empty() or triangle_ids.size() > MAX_TRIANGLES_PER_VERTEX:
            return false
        var previous_triangle := -1
        for raw_triangle in triangle_ids:
            if typeof(raw_triangle) != TYPE_INT or int(raw_triangle) < 0 or int(raw_triangle) <= previous_triangle:
                return false
            previous_triangle = int(raw_triangle)
        var raw_external: Variant = record.get("external_section_representative_triangle_ids", null)
        if typeof(raw_external) != TYPE_ARRAY:
            return false
        var external_ids: Array = raw_external
        if external_ids.size() > MAX_EXTERNAL_REPRESENTATIVES_PER_VERTEX:
            return false
        var previous_external := -1
        for raw_external_id in external_ids:
            if typeof(raw_external_id) != TYPE_INT or int(raw_external_id) < 0 or int(raw_external_id) <= previous_external:
                return false
            previous_external = int(raw_external_id)
    return true

static func build_vertex_report(details: Dictionary) -> Dictionary:
    if not SourceSectionEdgePicker._valid_report(details):
        return {}
    var vertices: Dictionary = {}
    var edge_records: Array = details.get("edge_records", [])
    for raw_edge in edge_records:
        if typeof(raw_edge) != TYPE_DICTIONARY:
            return {}
        var edge: Dictionary = raw_edge
        var welds: Array = edge.get("source_weld_ids", [])
        if welds.size() != 2:
            return {}
        var points := [
            _point(edge.get("a_godot_xyz", null)),
            _point(edge.get("b_godot_xyz", null)),
        ]
        if not points[0].is_finite() or not points[1].is_finite():
            return {}
        var edge_key := str(edge.get("edge_key", ""))
        var triangles: Array = edge.get("section_triangle_ids", [])
        var external_count := int(edge.get("cross_section_neighbor_count", -1))
        var external_representative := int(edge.get("representative_cross_section_triangle_id", -1))
        for endpoint in range(2):
            var weld_id := int(welds[endpoint])
            var point: Vector3 = points[endpoint]
            if not vertices.has(weld_id):
                vertices[weld_id] = {
                    "weld_id": weld_id,
                    "vertex_key": str(weld_id),
                    "godot_xyz": [point.x, point.y, point.z],
                    "incident_edge_keys": [],
                    "incident_level_triangle_ids": [],
                    "external_section_representative_triangle_ids": [],
                }
            var record: Dictionary = vertices[weld_id]
            var previous_point := _point(record.get("godot_xyz", null))
            if previous_point != point:
                return {}
            var incident_edges: Array = record["incident_edge_keys"]
            if not incident_edges.has(edge_key):
                incident_edges.append(edge_key)
            var incident_triangles: Array = record["incident_level_triangle_ids"]
            for raw_triangle_id in triangles:
                var triangle_id := int(raw_triangle_id)
                if not incident_triangles.has(triangle_id):
                    incident_triangles.append(triangle_id)
            var external_representatives: Array = record["external_section_representative_triangle_ids"]
            if external_count > 0:
                if external_representative < 0:
                    return {}
                if not external_representatives.has(external_representative):
                    external_representatives.append(external_representative)
            if (incident_edges.size() > MAX_EDGES_PER_VERTEX
                or incident_triangles.size() > MAX_TRIANGLES_PER_VERTEX
                or external_representatives.size() > MAX_EXTERNAL_REPRESENTATIVES_PER_VERTEX):
                return {}
            record["incident_edge_keys"] = incident_edges
            record["incident_level_triangle_ids"] = incident_triangles
            record["external_section_representative_triangle_ids"] = external_representatives
            vertices[weld_id] = record
    if vertices.is_empty() or vertices.size() > MAX_VERTEX_COUNT:
        return {}
    var weld_ids: Array = vertices.keys()
    weld_ids.sort()
    var records: Array = []
    for raw_weld_id in weld_ids:
        var record: Dictionary = vertices[int(raw_weld_id)]
        record["incident_edge_keys"].sort()
        record["incident_level_triangle_ids"].sort()
        record["external_section_representative_triangle_ids"].sort()
        records.append(record)
    var report := {
        "schema": "DX2Ed-source-section-vertex-report-v1",
        "source_map": str(details.get("source_map", "")),
        "source_sha256": str(details.get("source_sha256", "")),
        "source_section_key": str(details.get("source_section_key", "")),
        "source_block_id": int(details.get("source_block_id", -1)),
        "render_block_ordinal": int(details.get("render_block_ordinal", -1)),
        "render_section_ordinal": int(details.get("render_section_ordinal", -1)),
        "source_edge_report_count": edge_records.size(),
        "vertex_record_count": records.size(),
        "unique_source_vertex_count": records.size(),
        "vertex_records": records,
        "max_edge_count": MAX_EDGE_COUNT,
        "max_vertex_count": MAX_VERTEX_COUNT,
        "max_edges_per_vertex": MAX_EDGES_PER_VERTEX,
        "max_triangles_per_vertex": MAX_TRIANGLES_PER_VERTEX,
        "max_external_representatives_per_vertex": MAX_EXTERNAL_REPRESENTATIVES_PER_VERTEX,
        "exact_original_float32_weld_ids": true,
        "mopp_leaf_subset_only": true,
        "native_bsp_vertex_verified": false,
        "native_map_written": false,
    }
    return report if _valid_vertex_report(report) else {}

static func record_belongs_to_report(report: Dictionary, record: Dictionary) -> bool:
    if not _valid_vertex_report(report):
        return false
    var raw_id: Variant = record.get("weld_id", null)
    if typeof(raw_id) != TYPE_INT:
        return false
    var weld_id := int(raw_id)
    for raw_candidate in report.get("vertex_records", []):
        var candidate: Dictionary = raw_candidate
        if int(candidate.get("weld_id", -1)) == weld_id:
            return (
                str(candidate.get("vertex_key", "")) == str(record.get("vertex_key", ""))
                and candidate.get("godot_xyz", []) == record.get("godot_xyz", [])
                and candidate.get("incident_edge_keys", []) == record.get("incident_edge_keys", [])
                and candidate.get("incident_level_triangle_ids", []) == record.get("incident_level_triangle_ids", [])
                and candidate.get("external_section_representative_triangle_ids", []) == record.get("external_section_representative_triangle_ids", [])
            )
    return false

static func camera_signature_matches(index: Dictionary, camera: Camera3D,
        viewport_size: Vector2) -> bool:
    if not is_instance_valid(camera) or index.is_empty():
        return false
    return (
        index.get("schema", "") == "DX2Ed-source-section-vertex-screen-index-v1"
        and index.get("mopp_leaf_subset_only", false) == true
        and index.get("native_bsp_vertex_verified", true) == false
        and index.get("native_map_written", true) == false
        and index.get("camera_transform") == camera.global_transform
        and int(index.get("camera_projection", -1)) == int(camera.projection)
        and is_equal_approx(float(index.get("camera_size", -1.0)), camera.size)
        and is_equal_approx(float(index.get("camera_fov", -1.0)), camera.fov)
        and is_equal_approx(float(index.get("camera_near", -1.0)), camera.near)
        and is_equal_approx(float(index.get("camera_far", -1.0)), camera.far)
        and int(index.get("camera_keep_aspect", -1)) == int(camera.keep_aspect)
        and is_equal_approx(float(index.get("camera_h_offset", INF)), camera.h_offset)
        and is_equal_approx(float(index.get("camera_v_offset", INF)), camera.v_offset)
        and index.get("camera_frustum_offset", Vector2(INF, INF)) == camera.frustum_offset
        and index.get("viewport_size", Vector2.ZERO) == viewport_size
    )

static func build_screen_index(report: Dictionary, camera: Camera3D,
        viewport_size: Vector2) -> Dictionary:
    if (not _valid_vertex_report(report) or not is_instance_valid(camera)
        or viewport_size.x <= 0.0 or viewport_size.y <= 0.0):
        return {}
    var cells: Dictionary = {}
    var projected_records: Array = []
    for raw_record in report["vertex_records"]:
        var record: Dictionary = raw_record
        var point := _point(record.get("godot_xyz", null))
        if not point.is_finite() or camera.is_position_behind(point):
            continue
        var depth := -camera.global_basis.z.dot(point - camera.global_position)
        if not is_finite(depth) or depth < camera.near or depth > camera.far:
            continue
        var screen := camera.unproject_position(point)
        if (not is_finite(screen.x) or not is_finite(screen.y)
            or screen.x < -PICK_RADIUS_PIXELS or screen.y < -PICK_RADIUS_PIXELS
            or screen.x > viewport_size.x + PICK_RADIUS_PIXELS
            or screen.y > viewport_size.y + PICK_RADIUS_PIXELS):
            continue
        var projected_index := projected_records.size()
        projected_records.append({
            "record": record.duplicate(true),
            "vertex_key": str(record["vertex_key"]),
            "screen": screen,
            "world": point,
            "depth": depth,
        })
        var cell_x := floori(screen.x / CELL_SIZE)
        var cell_y := floori(screen.y / CELL_SIZE)
        var cell_key := "%d:%d" % [cell_x, cell_y]
        var bucket: Array = cells.get(cell_key, [])
        bucket.append(projected_index)
        cells[cell_key] = bucket
    if projected_records.is_empty():
        return {}
    return {
        "schema": "DX2Ed-source-section-vertex-screen-index-v1",
        "source_sha256": str(report["source_sha256"]),
        "source_section_key": str(report["source_section_key"]),
        "viewport_size": viewport_size,
        "camera_transform": camera.global_transform,
        "camera_projection": int(camera.projection),
        "camera_size": camera.size,
        "camera_fov": camera.fov,
        "camera_near": camera.near,
        "camera_far": camera.far,
        "camera_keep_aspect": int(camera.keep_aspect),
        "camera_h_offset": camera.h_offset,
        "camera_v_offset": camera.v_offset,
        "camera_frustum_offset": camera.frustum_offset,
        "cell_size": CELL_SIZE,
        "records": projected_records,
        "cells": cells,
        "projected_vertex_count": projected_records.size(),
        "mopp_leaf_subset_only": true,
        "native_bsp_vertex_verified": false,
        "native_map_written": false,
    }

static func pick_vertex(index: Dictionary, mouse_pixels: Vector2,
        radius_pixels: float = PICK_RADIUS_PIXELS) -> Dictionary:
    if (index.get("schema", "") != "DX2Ed-source-section-vertex-screen-index-v1"
        or index.get("mopp_leaf_subset_only", false) != true
        or index.get("native_bsp_vertex_verified", true) != false
        or index.get("native_map_written", true) != false
        or not is_finite(mouse_pixels.x) or not is_finite(mouse_pixels.y)
        or not is_finite(radius_pixels) or radius_pixels <= 0.0
        or radius_pixels > PICK_RADIUS_PIXELS):
        return {}
    var cell_size := float(index.get("cell_size", 0.0))
    if not is_finite(cell_size) or cell_size <= 0.0:
        return {}
    var min_cell_x := floori((mouse_pixels.x - radius_pixels) / cell_size)
    var max_cell_x := floori((mouse_pixels.x + radius_pixels) / cell_size)
    var min_cell_y := floori((mouse_pixels.y - radius_pixels) / cell_size)
    var max_cell_y := floori((mouse_pixels.y + radius_pixels) / cell_size)
    var cells: Dictionary = index.get("cells", {})
    var candidates: Array = []
    for cell_y in range(min_cell_y, max_cell_y + 1):
        for cell_x in range(min_cell_x, max_cell_x + 1):
            var cell_key := "%d:%d" % [cell_x, cell_y]
            for raw_index in cells.get(cell_key, []):
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
        var screen: Vector2 = projected["screen"]
        var distance := screen.distance_to(mouse_pixels)
        var depth := float(projected["depth"])
        if (distance > radius_pixels
            or distance > best_distance + 0.001
            or (is_equal_approx(distance, best_distance) and depth >= best_depth)):
            continue
        best_distance = distance
        best_depth = depth
        best = {
            "record": projected["record"].duplicate(true),
            "vertex_key": str(projected["vertex_key"]),
            "source_weld_id": int(projected["record"].get("weld_id", -1)),
            "screen_distance_px": distance,
            "screen_point": screen,
            "world_point": projected["world"],
            "depth_godot_units": depth,
            "source_sha256": str(index["source_sha256"]),
            "source_section_key": str(index["source_section_key"]),
            "mopp_leaf_subset_only": true,
            "native_bsp_vertex_verified": false,
            "native_map_written": false,
        }
    return best

static func build_overlay(report: Dictionary, camera: Camera3D,
        viewport_size: Vector2) -> Dictionary:
    if (not _valid_vertex_report(report) or not is_instance_valid(camera)
        or viewport_size.x <= 0.0 or viewport_size.y <= 0.0):
        return {}
    var sphere := SphereMesh.new()
    sphere.radius = 1.0
    sphere.height = 2.0
    sphere.radial_segments = 8
    sphere.rings = 4
    var transforms: Array = []
    for raw_record in report["vertex_records"]:
        var record: Dictionary = raw_record
        var point := _point(record.get("godot_xyz", null))
        if not point.is_finite() or camera.is_position_behind(point):
            continue
        var depth := -camera.global_basis.z.dot(point - camera.global_position)
        if not is_finite(depth) or depth < camera.near or depth > camera.far:
            continue
        var screen := camera.unproject_position(point)
        if (not is_finite(screen.x) or not is_finite(screen.y)
            or screen.x < -PICK_RADIUS_PIXELS or screen.y < -PICK_RADIUS_PIXELS
            or screen.x > viewport_size.x + PICK_RADIUS_PIXELS
            or screen.y > viewport_size.y + PICK_RADIUS_PIXELS):
            continue
        var depth := -camera.global_basis.z.dot(point - camera.global_position)
        if not is_finite(depth) or depth < camera.near or depth > camera.far:
            continue
        var world_per_pixel := camera.size / viewport_size.y
        if camera.projection == Camera3D.PROJECTION_PERSPECTIVE:
            world_per_pixel = 2.0 * depth * tan(deg_to_rad(camera.fov * 0.5)) / viewport_size.y
        if not is_finite(world_per_pixel) or world_per_pixel <= 0.0:
            return {}
        var radius := clampf(world_per_pixel * 3.0, 0.0002, 0.12)
        transforms.append(Transform3D(
            Basis.IDENTITY.scaled(Vector3.ONE * radius), point))
    if transforms.is_empty():
        return {}
    var multimesh := MultiMesh.new()
    multimesh.transform_format = MultiMesh.TRANSFORM_3D
    multimesh.mesh = sphere
    multimesh.instance_count = transforms.size()
    for index in range(transforms.size()):
        multimesh.set_instance_transform(index, transforms[index])
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.15, 0.92, 1.0, 1.0)
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.render_priority = 2
    var marker := MultiMeshInstance3D.new()
    marker.name = "SourceCollision_EditorOnly_SectionVertexHandles"
    marker.multimesh = multimesh
    marker.material_override = material
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    marker.set_meta("editor_only", true)
    return {
        "marker": marker,
        "vertex_count": int(report["vertex_record_count"]),
        "visible_vertex_count": transforms.size(),
        "mopp_leaf_subset_only": true,
        "native_bsp_vertex_verified": false,
        "native_map_written": false,
    }

static func build_highlight(pick: Dictionary, camera: Camera3D,
        viewport_height: float, color: Color) -> Node3D:
    if (not is_instance_valid(camera) or viewport_height <= 0.0
        or pick.get("mopp_leaf_subset_only", false) != true
        or pick.get("native_bsp_vertex_verified", true) != false
        or pick.get("native_map_written", true) != false):
        return null
    var point: Vector3 = pick.get("world_point", Vector3(INF, INF, INF))
    if not point.is_finite():
        return null
    var depth := -camera.global_basis.z.dot(point - camera.global_position)
    if not is_finite(depth) or depth < camera.near or depth > camera.far:
        return null
    var world_per_pixel := camera.size / viewport_height
    if camera.projection == Camera3D.PROJECTION_PERSPECTIVE:
        world_per_pixel = 2.0 * depth * tan(deg_to_rad(camera.fov * 0.5)) / viewport_height
    if not is_finite(world_per_pixel) or world_per_pixel <= 0.0:
        return null
    var radius := clampf(world_per_pixel * 5.0, 0.0003, 0.25)
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.render_priority = 4
    var sphere := SphereMesh.new()
    sphere.radius = 1.0
    sphere.height = 2.0
    sphere.radial_segments = 16
    sphere.rings = 8
    var root := Node3D.new()
    root.name = "SourceCollision_EditorOnly_SelectedVertexHighlight"
    root.set_meta("editor_only", true)
    var marker := MeshInstance3D.new()
    marker.name = "SelectedSourceVertexHandle_EDITOR_ONLY"
    marker.mesh = sphere
    marker.position = point
    marker.scale = Vector3.ONE * radius
    marker.material_override = material
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    root.add_child(marker)
    var cross_mesh := ImmediateMesh.new()
    cross_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    var side := camera.global_basis.x * radius * 2.0
    var up := camera.global_basis.y * radius * 2.0
    cross_mesh.surface_add_vertex(point - side)
    cross_mesh.surface_add_vertex(point + side)
    cross_mesh.surface_add_vertex(point - up)
    cross_mesh.surface_add_vertex(point + up)
    cross_mesh.surface_end()
    var cross := MeshInstance3D.new()
    cross.name = "SelectedSourceVertexCrosshair_EDITOR_ONLY"
    cross.mesh = cross_mesh
    cross.material_override = material
    cross.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    root.add_child(cross)
    return root
