extends RefCounted
## One private authored Box plane may move along its normal in local metres.
## This helper is intentionally independent of retail DX2 source geometry,
## editor UI state, native BSP writes and game collision cooking.

const Brush = preload("res://brush_geometry.gd")
const MAX_OFFSET := 256.0


static func with_world_displacement(
        raw: Variant, plane_index: int, world: Transform3D,
        world_displacement: Vector3, grid_step: float) -> Dictionary:
    if (not world_displacement.is_finite() or not world.origin.is_finite()
        or not world.basis.x.is_finite() or not world.basis.y.is_finite()
        or not world.basis.z.is_finite()
        or absf(world.basis.determinant()) < 0.00000001
        or not is_finite(grid_step) or grid_step < 0.25
        or grid_step > 64.0):
        return {}
    var spec: Dictionary = Brush.validate(raw)
    if (spec.is_empty() or spec.get("kind", "") != "Box"
        or not spec.has("clip_plane") and not spec.has("clip_planes")):
        return {}
    var planes: Array = (
        spec["clip_planes"].duplicate(true) if spec.has("clip_planes")
        else [spec["clip_plane"].duplicate(true)])
    if plane_index < 0 or plane_index >= planes.size():
        return {}
    var plane: Dictionary = planes[plane_index].duplicate(true)
    var normal := Vector3(
        plane["normal"][0], plane["normal"][1], plane["normal"][2])
    var local_delta := world.affine_inverse().basis * world_displacement
    if not local_delta.is_finite():
        return {}
    # Snapping is RELATIVE to the original author-specified plane offset:
    # touching the cap must not jump it to a different grid position.
    var delta := snappedf(normal.dot(local_delta), grid_step)
    var candidate_distance := float(plane["distance"]) + delta
    if (not is_finite(candidate_distance)
        or absf(candidate_distance) > MAX_OFFSET):
        return {}
    if absf(delta) < 0.00001:
        return spec
    plane["distance"] = candidate_distance
    planes[plane_index] = plane
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
