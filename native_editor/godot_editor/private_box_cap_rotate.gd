extends RefCounted
## DX2Ed v0.88: rotate one authored private Box cut about its visible cap
## centroid. Preview only, no native DX2 BSP, GMP/IBD or collision writes.

const Brush = preload("res://brush_geometry.gd")
const Picker = preload("res://private_box_cap_picker.gd")
const MAX_ANGLE_DEG := 30.0
const MAX_OFFSET := 256.0
const MIN_CAP_AREA := 0.000001


static func cap_area_centroid(raw: Variant, index: int) -> Dictionary:
    var spec: Dictionary = Picker._checked_spec(raw)
    if spec.is_empty():
        return {}
    var planes: Array = Picker._planes(spec)
    if index < 0 or index >= planes.size():
        return {}
    var triangles: PackedVector3Array = Picker._vertices(spec)
    if triangles.is_empty():
        return {}
    var weighted := Vector3.ZERO
    var area := 0.0
    for t in range(0, triangles.size(), 3):
        var a: Vector3 = triangles[t]
        var b: Vector3 = triangles[t + 1]
        var c: Vector3 = triangles[t + 2]
        if Picker._cap_index(a, b, c, planes) != index:
            continue
        var piece := 0.5 * (b - a).cross(c - a).length()
        if not is_finite(piece) or piece < MIN_CAP_AREA:
            return {}
        weighted += (a + b + c) * (piece / 3.0)
        area += piece
    if not is_finite(area) or area <= MIN_CAP_AREA:
        return {}
    var center := weighted / area
    if not center.is_finite():
        return {}
    var plane: Dictionary = planes[index]
    var normal := Vector3(
        plane["normal"][0], plane["normal"][1], plane["normal"][2])
    if absf(normal.dot(center) - float(plane["distance"])) > 0.00015:
        return {}
    return {"center": center, "area": area}


static func rotated_about_cap(
        raw: Variant, index: int,
        axis: Vector3, degrees: float) -> Dictionary:
    if (not axis.is_finite() or axis.length_squared() < 0.00000001
        or not is_finite(degrees)
        or absf(degrees) < 0.0001
        or absf(degrees) > MAX_ANGLE_DEG):
        return {}
    var spec: Dictionary = Picker._checked_spec(raw)
    if spec.is_empty():
        return {}
    var planes: Array = Picker._planes(spec).duplicate(true)
    if index < 0 or index >= planes.size():
        return {}
    var pivot := cap_area_centroid(spec, index)
    if pivot.is_empty():
        return {}
    var plane: Dictionary = planes[index].duplicate(true)
    var original := Vector3(
        plane["normal"][0], plane["normal"][1], plane["normal"][2])
    var turned := (Basis(axis.normalized(), deg_to_rad(degrees))
        * original).normalized()
    if (not turned.is_finite()
        or turned.distance_to(original) < 0.00001):
        return {}
    # The old visible cap's area centroid remains on the rotated plane.
    # This is an anchor, not a change to the Box object transform.
    var new_distance := turned.dot(pivot["center"])
    if not is_finite(new_distance) or absf(new_distance) > MAX_OFFSET:
        return {}
    plane["normal"] = [turned.x, turned.y, turned.z]
    plane["distance"] = new_distance
    planes[index] = plane
    spec.erase("clip_plane")
    spec.erase("clip_planes")
    if planes.size() == 1:
        spec["clip_plane"] = planes[0]
    else:
        spec["clip_planes"] = planes
    var verified: Dictionary = Brush.validate(spec)
    if verified.is_empty() or Brush.build_mesh(verified) == null:
        return {}
    return verified
