extends RefCounted
## Translucent editor-only rendering of a selected original section's MOPP leaf subset.
## The small normal offset is visual-only and never changes source or preview geometry.

const PREVIEW_CAP := 8192
const DISPLAY_OFFSET_GODOT_UNITS := 0.0015
const FILL_COLOR := Color(0.04, 0.72, 0.94, 0.22)

static func build_marker(picker: RefCounted, original_id: int) -> Dictionary:
    if picker == null or original_id < 0 or not bool(picker.get("ready")):
        return {}
    var details: Dictionary = picker.call(
        "section_surface_preview_details", original_id, PREVIEW_CAP)
    if details.is_empty():
        return {}
    if bool(details.get("preview_skipped_for_size", false)):
        return {"marker": null, "details": details}
    if (details.get("mopp_leaf_subset_only", false) != true
        or details.get("read_only", false) != true
        or details.get("native_map_written", true) != false
        or details.get("native_bsp_surface_verified", true) != false
        or details.get("full_render_section_geometry_verified", true) != false):
        return {}
    var points: PackedVector3Array = details.get(
        "triangle_vertices_godot", PackedVector3Array())
    var triangle_count := int(details.get("triangle_count", 0))
    if points.is_empty() or points.size() != triangle_count * 3:
        return {}

    # Validate every triangle before opening the ImmediateMesh surface, so a
    # malformed final triangle cannot leave a partial overlay.
    var display_points := PackedVector3Array()
    for index in range(0, points.size(), 3):
        var a := points[index]
        var b := points[index + 1]
        var c := points[index + 2]
        var face_normal := (b - a).cross(c - a)
        if not face_normal.is_finite() or face_normal.length_squared() <= 1e-12:
            return {}
        var offset := face_normal.normalized() * DISPLAY_OFFSET_GODOT_UNITS
        display_points.append(a + offset)
        display_points.append(b + offset)
        display_points.append(c + offset)
    if display_points.size() != points.size():
        return {}

    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
    for point in display_points:
        mesh.surface_add_vertex(point)
    mesh.surface_end()

    var material := StandardMaterial3D.new()
    material.albedo_color = FILL_COLOR
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.no_depth_test = false
    material.render_priority = 1

    var marker := MeshInstance3D.new()
    marker.name = "SourceCollision_EditorOnly_SectionFill"
    marker.mesh = mesh
    marker.material_override = material
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    return {
        "marker": marker,
        "details": details,
        "display_offset_godot_units": DISPLAY_OFFSET_GODOT_UNITS,
        "preview_vertex_count": display_points.size(),
    }
