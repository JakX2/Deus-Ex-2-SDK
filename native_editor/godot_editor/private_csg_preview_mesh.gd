extends RefCounted
## P102: turn a strict Python source-private CSG report into a disposable
## Godot MeshInstance3D preview. NO original actor, collision, or world
## serialization is created; private shells are not selectable native actors.
const MAX_PIECES = 14
const MAX_VERTICES = 64
const MAX_FACES = 28
const MAX_TRIANGLES = 100
const MAX_TOTAL_TRIANGLES = MAX_PIECES * MAX_TRIANGLES


static func _vector(raw: Variant) -> Vector3:
    if typeof(raw) != TYPE_ARRAY or raw.size() != 3:
        return Vector3(INF, INF, INF)
    for n in raw:
        if typeof(n) not in [TYPE_INT, TYPE_FLOAT]:
            return Vector3(INF, INF, INF)
        if is_nan(float(n)) or is_inf(float(n)):
            return Vector3(INF, INF, INF)
        if absf(float(n)) > 1000001.0:
            return Vector3(INF, INF, INF)
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))


static func _valid_number(value: Variant) -> bool:
    return typeof(value) in [TYPE_INT, TYPE_FLOAT] and (
        not is_nan(float(value)) and not is_inf(float(value)))


static func _one_piece(raw: Variant, index: int, material: Material) -> Dictionary:
    if typeof(raw) != TYPE_DICTIONARY:
        return {"ok": false, "reason": "non-dictionary-piece"}
    var points: Variant = raw.get("vertices", [])
    var faces: Variant = raw.get("faces", [])
    if (typeof(points) != TYPE_ARRAY or typeof(faces) != TYPE_ARRAY
        or points.size() < 4 or points.size() > MAX_VERTICES
        or faces.size() < 4 or faces.size() > MAX_FACES
        or raw.get("vertex_count", -1) != points.size()
        or raw.get("face_count", -1) != faces.size()
        or raw.get("euler_characteristic", -1) != 2
        or raw.get("all_edges_two_opposite_face_uses", false) != true
        or not _valid_number(raw.get("volume_m3", null))
        or float(raw["volume_m3"]) <= 0.0):
        return {"ok": false, "reason": "piece-count-or-volume"}
    var vertices: Array[Vector3] = []
    for source in points:
        var point := _vector(source)
        if not point.is_finite():
            return {"ok": false, "reason": "nonfinite-vertex"}
        vertices.append(point)
    var positions := PackedVector3Array()
    var normals := PackedVector3Array()
    var triangle_count := 0
    for face in faces:
        if typeof(face) != TYPE_DICTIONARY:
            return {"ok": false, "reason": "non-dictionary-face"}
        var ids: Variant = face.get("vertex_ids", [])
        var normal := _vector(face.get("outward_normal", null))
        if (typeof(ids) != TYPE_ARRAY or ids.size() < 3
            or ids.size() > 32 or not normal.is_finite()
            or absf(normal.length_squared()-1.0) > 0.0002
            or face.get("face_index", -1) != faces.find(face)):
            return {"ok": false, "reason": "face-index-or-normal"}
        var checked: Array[int] = []
        for vertex_id in ids:
            if (typeof(vertex_id) != TYPE_INT or vertex_id < 0
                or vertex_id >= vertices.size() or checked.has(vertex_id)):
                return {"ok": false, "reason": "face-vertex-id"}
            checked.append(vertex_id)
        for j in range(1, checked.size()-1):
            var a := vertices[checked[0]]
            var b := vertices[checked[j]]
            var c := vertices[checked[j+1]]
            if (b-a).cross(c-a).dot(normal) <= 1e-10:
                return {"ok": false, "reason": "incorrect-winding"}
            for vertex in [a, b, c]:
                positions.append(vertex)
                normals.append(normal)
            triangle_count += 1
            if triangle_count > MAX_TRIANGLES:
                return {"ok": false, "reason": "triangle-capacity"}
    if (triangle_count != int(raw.get("triangle_count", -1))
        or positions.size() != triangle_count*3):
        return {"ok": false, "reason": "triangle-count-disagreement"}
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = positions
    arrays[Mesh.ARRAY_NORMAL] = normals
    var geometry := ArrayMesh.new()
    geometry.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    if geometry.get_surface_count() != 1:
        return {"ok": false, "reason": "empty-godot-surface"}
    var node := MeshInstance3D.new()
    node.name = "Private_CSG_Preview_Piece_" + str(index)
    node.mesh = geometry
    node.material_override = material
    node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    node.set_meta("dx2sdk_private_csg_preview_only", true)
    return {"ok": true, "node": node, "triangle_count": triangle_count,
            "vertex_count": vertices.size()}


static func build_preview(report: Variant, operation: String) -> Dictionary:
    if typeof(report) != TYPE_DICTIONARY or operation not in [
        "intersection", "subtraction",
    ]:
        return {"ok": false, "message": "Unsupported private CSG report."}
    if (report.get("original_gmp_or_ibd_modified", true) != false
        or report.get("retail_game_runtime_verified", true) != false):
        return {"ok": false, "message": "Private CSG report is not source-isolated."}
    var pieces: Array = []
    var volume := 0.0
    if operation == "intersection":
        if (str(report.get("schema", "")) !=
            "DX2SDK-private-convex-CSG-intersection-preview-v1"):
            return {"ok": false, "message": "Unexpected intersection preview schema."}
        if bool(report.get("has_volume", false)):
            pieces = [report]
            volume = float(report.get("volume_m3", -1.0))
        elif report.get("vertex_count", -1) != 0:
            return {"ok": false, "message": "Invalid empty intersection preview."}
    else:
        if (str(report.get("schema", "")) !=
            "DX2SDK-source-private-convex-CSG-difference-decomposition-v1"
            or report.get("volume_partition_verified", false) != true
            or report.get("all_pieces_individually_closed", false) != true):
            return {"ok": false, "message": "Invalid private subtraction proof."}
        var supplied: Variant = report.get("pieces", null)
        if typeof(supplied) != TYPE_ARRAY:
            return {"ok": false, "message": "Missing private subtraction shells."}
        pieces = supplied
        if (report.get("piece_count", -1) != pieces.size()
            or not _valid_number(report.get("remaining_volume_m3", null))):
            return {"ok": false, "message": "Subtraction piece census mismatch."}
        volume = float(report["remaining_volume_m3"])
    if (pieces.size() > MAX_PIECES or not _valid_number(volume)
        or volume < 0.0):
        return {"ok": false, "message": "Private CSG volume or piece limit exceeded."}
    var root := Node3D.new()
    root.name = "DX2Ed_Private_CSG_Visual_Only"
    root.set_meta("dx2sdk_private_csg_preview_only", true)
    var material := StandardMaterial3D.new()
    material.albedo_color = (
        Color(0.15, 0.98, 0.48, 0.67) if operation == "intersection"
        else Color(1.0, 0.58, 0.14, 0.67))
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    var vertices := 0
    var triangles := 0
    var total_volume := 0.0
    for i in range(pieces.size()):
        var part := _one_piece(pieces[i], i, material)
        if not bool(part.get("ok", false)):
            root.free()
            return {"ok": false, "message": "Invalid CSG preview shell geometry: " + str(part.get("reason", "unknown")) + " in piece " + str(i)}
        root.add_child(part["node"])
        triangles += int(part["triangle_count"])
        vertices += int(part["vertex_count"])
        total_volume += float(pieces[i]["volume_m3"])
    if (triangles > MAX_TOTAL_TRIANGLES
        or not is_equal_approx(total_volume, volume)):
        root.free()
        return {"ok": false, "message": "Private CSG preview volume/count mismatch."}
    return {
        "ok": true, "root": root, "pieces": pieces.size(),
        "triangles": triangles, "vertices": vertices,
        "volume_m3": volume, "operation": operation,
        "message": "Visual preview only. No native DX2 BSP, GMP/IBD, "
            + "materials, collision, actors, or Undo changes.",
    }
