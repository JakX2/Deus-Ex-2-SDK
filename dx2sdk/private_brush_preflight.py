"""Independent, read-only geometry preflight for Godot-private clipped Box brushes.

Creates a synthetic convex polygon/triangle representation from private
DX2Ed-prop-draft-v1 Box brush metadata. No game file, BSP index, GMP/IBD
writer, collision cooker, or retail engine geometry is ever involved.

This is deliberately an independent halfspace-intersection implementation,
not a port of the Godot triangle clipping code. A passing preflight is
supporting evidence, NOT proof of identical Godot triangulation or DX2
runtime compatibility.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
import hashlib
import json
import math
from typing import Any

SCHEMA = "DX2SDK-private-Box-independent-convex-preflight-v1"
MIN_SIZE, MAX_SIZE = 0.05, 256.0
MAX_PLANES, MAX_FACES, MAX_TRIANGLES = 8, 14, 44
MIN_CLEARANCE = 0.05
PLANE_TOLERANCE = 0.00006
VERTEX_TOLERANCE = 0.00002
MIN_CUT_VOLUME = 0.0001


def _number(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Only finite numeric private brush coordinates accepted")
    return float(value)


def _vec(value: Any) -> tuple[float, float, float]:
    if type(value) is not list or len(value) != 3:
        raise ValueError("Expected exactly three local coordinates")
    return (_number(value[0]), _number(value[1]), _number(value[2]))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def _mul(a, k):
    return tuple(x*k for x in a)


def _unit(a):
    length = math.sqrt(_dot(a, a))
    if length < 1e-10 or not math.isfinite(length):
        raise ValueError("Degenerate private plane normal")
    return _mul(a, 1.0/length)


def _distance(a, b):
    return math.sqrt(_dot(_sub(a, b), _sub(a, b)))


def _normalized_spec(raw: Any) -> tuple[dict, list[tuple]]:
    if type(raw) is not dict:
        raise ValueError("Expected one private Box brush specification")
    if "clip_plane" in raw and "clip_planes" in raw:
        raise ValueError("A private Box cannot use both clip JSON encodings")
    clip_key = "clip_planes" if "clip_planes" in raw else "clip_plane"
    if set(raw) != {"kind", "size", "steps", clip_key}:
        raise ValueError("Unexpected or missing fields in private Box specification")
    if raw["kind"] != "Box" or type(raw["steps"]) not in (int, float):
        raise ValueError("Only an authored private Brush::Box is accepted")
    if _number(raw["steps"]) != 1.0:
        raise ValueError("A Box cannot contain stair steps")
    size = _vec(raw["size"])
    if any(not MIN_SIZE <= n <= MAX_SIZE for n in size):
        raise ValueError("Private Box size outside Godot editor limits")
    sources = raw[clip_key] if clip_key == "clip_planes" else [raw[clip_key]]
    if type(sources) is not list or not 1 <= len(sources) <= MAX_PLANES:
        raise ValueError("Expected one to eight local cut planes")
    cuts = []
    for source in sources:
        if type(source) is not dict or set(source) != {
            "normal", "distance", "keep_positive"}:
            raise ValueError("Private clip record has unsupported fields")
        normal = _vec(source["normal"])
        length2 = _dot(normal, normal)
        if abs(length2 - 1.0) > 0.0001:
            raise ValueError("Private clip normal must be unit length")
        normal = _unit(normal)
        distance = _number(source["distance"])
        if abs(distance) > 256.0 or type(source["keep_positive"]) is not bool:
            raise ValueError("Clip offset or kept side outside private limits")
        # All source-plane validation also checks a cut against the WHOLE
        # original Box, not just its current intermediate convex polyhedron.
        signed = [
            _dot(normal, (sx*size[0]/2, sy*size[1]/2, sz*size[2]/2)) - distance
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
        ]
        if min(signed) >= -MIN_CLEARANCE or max(signed) <= MIN_CLEARANCE:
            raise ValueError("Plane is empty, redundant or near tangent to Box")
        cuts.append({
            "normal": list(normal),
            "distance": distance,
            "keep_positive": source["keep_positive"],
        })
    normalized = {
        "kind": "Box", "size": list(size), "steps": 1,
        clip_key: cuts if clip_key == "clip_planes" else cuts[0],
    }
    # Model every halfspace with OUTWARD normals, n*x <= d.
    normals = [
        (tuple(c["normal"]), c["distance"]) if not c["keep_positive"]
        else (_mul(c["normal"], -1.0), -c["distance"])
        for c in cuts
    ]
    return normalized, normals


def _box_planes(size):
    x, y, z = (n/2 for n in size)
    return [
        ((1., 0., 0.), x, "box", 0),
        ((-1., 0., 0.), x, "box", 1),
        ((0., 1., 0.), y, "box", 2),
        ((0., -1., 0.), y, "box", 3),
        ((0., 0., 1.), z, "box", 4),
        ((0., 0., -1.), z, "box", 5),
    ]


def _triple_intersection(a, b, c):
    n1, d1 = a[:2]
    n2, d2 = b[:2]
    n3, d3 = c[:2]
    c23, c31, c12 = _cross(n2, n3), _cross(n3, n1), _cross(n1, n2)
    determinant = _dot(n1, c23)
    if abs(determinant) <= 1e-9:
        return None
    p = _mul(_add(_add(_mul(c23, d1), _mul(c31, d2)),
                  _mul(c12, d3)), 1.0/determinant)
    if not all(math.isfinite(x) for x in p):
        return None
    return p


def _polyhedron(planes):
    vertices = []
    # Each true convex vertex is the intersection of at least three
    # boundary planes. This method is independent of Godot polygon clipping.
    for triple in combinations(planes, 3):
        p = _triple_intersection(*triple)
        if p is None:
            continue
        if any(_dot(n, p) - d > PLANE_TOLERANCE for n, d, *_ in planes):
            continue
        if not any(_distance(p, q) <= VERTEX_TOLERANCE for q in vertices):
            vertices.append(p)
    if len(vertices) < 4 or len(vertices) > 64:
        raise ValueError("Clipped private Box has missing or excess vertices")
    # Canonical ordering independent of the cut insertion order.
    vertices.sort(key=lambda p: tuple(round(x, 8) for x in p))
    faces = []
    all_triangle_edges = defaultdict(list)
    all_boundary_edges = defaultdict(list)
    triangles = []
    for n, d, kind, slot in planes:
        ids = [i for i, p in enumerate(vertices)
               if abs(_dot(n, p) - d) <= PLANE_TOLERANCE]
        if len(ids) < 3:
            continue
        if len(ids) > 16:
            raise ValueError("Unbounded clipping cap perimeter")
        centre = _mul(tuple(sum(vertices[i][k] for i in ids) for k in range(3)),
                      1.0/len(ids))
        helper = (0., 1., 0.) if abs(n[1]) < 0.85 else (1., 0., 0.)
        u = _unit(_cross(helper, n))
        v = _cross(n, u)
        ids.sort(key=lambda i: math.atan2(
            _dot(_sub(vertices[i], centre), v),
            _dot(_sub(vertices[i], centre), u)))
        for x, y in zip(ids, ids[1:] + ids[:1]):
            all_boundary_edges[tuple(sorted((x, y)))].append((x, y))
        for j in range(1, len(ids)-1):
            a, b, c = (vertices[ids[k]] for k in (0, j, j+1))
            area2 = _dot(_cross(_sub(b, a), _sub(c, a)), n)
            if area2 <= 1e-10:
                raise ValueError("Degenerate or inward polygon triangulation")
            triangle = (ids[0], ids[j], ids[j+1])
            triangles.append(triangle)
            for x, y in ((triangle[0], triangle[1]),
                         (triangle[1], triangle[2]),
                         (triangle[2], triangle[0])):
                all_triangle_edges[tuple(sorted((x, y)))].append((x, y))
        faces.append({
            "kind": "private_cut_cap" if kind == "cut" else "private_box_side",
            "slot": slot, "normal": list(n), "distance": d,
            "vertices": [list(vertices[i]) for i in ids],
            "vertex_ids": ids,
        })
    if not 4 <= len(faces) <= MAX_FACES or not 4 <= len(vertices) <= 64:
        raise ValueError("Clipped Box face count exceeds convex capacity")
    if not 4 <= len(triangles) <= MAX_TRIANGLES:
        raise ValueError("Private Box triangle count exceeds bounded capacity")
    for ledger in (all_triangle_edges, all_boundary_edges):
        if any(len(v) != 2 or v[0] != tuple(reversed(v[1]))
               for v in ledger.values()):
            raise ValueError("Open, T-junction or inconsistently oriented mesh")
    if len(vertices) - len(all_boundary_edges) + len(faces) != 2:
        raise ValueError("Convex Box fails Euler characteristic")
    volume = sum(_dot(vertices[a],
                      _cross(vertices[b], vertices[c])) / 6.0
                 for a, b, c in triangles)
    if not math.isfinite(volume) or volume <= 0.0:
        raise ValueError("Nonpositive oriented convex volume")
    return {
        "vertices": vertices, "faces": faces, "triangle_count": len(triangles),
        "edge_count": len(all_boundary_edges), "volume": volume,
    }


def inspect_private_box_convex(raw: Any) -> dict:
    """Validate private authored halfspaces and report local polygon geometry.

    Raises ValueError on unsupported, unsafe, degenerate or redundant input.
    This function never opens source files and never generates native BSP.
    """
    spec, cuts = _normalized_spec(raw)
    original_volume = math.prod(spec["size"])
    planes = _box_planes(spec["size"])
    previous = _polyhedron(planes)
    previous_volume = original_volume
    floor = max(MIN_CUT_VOLUME, original_volume*0.00001)
    for i, (outward, d) in enumerate(cuts):
        # Order matters to the private editor: every cut must remove
        # meaningful volume from the immediate preceding convex solid.
        distances = [_dot(outward, vertex)-d
                     for vertex in previous["vertices"]]
        if min(distances) >= -MIN_CLEARANCE or max(distances) <= MIN_CLEARANCE:
            raise ValueError(f"Private cut {i} is redundant or near tangent")
        planes.append((outward, d, "cut", i))
        current = _polyhedron(planes)
        if not any(f["kind"] == "private_cut_cap" and f["slot"] == i
                   for f in current["faces"]):
            raise ValueError(f"Private cut {i} has no visible new cap")
        if (current["volume"] <= floor
                or current["volume"] >= previous_volume-floor):
            raise ValueError(f"Private cut {i} does not shrink enclosed volume")
        previous, previous_volume = current, current["volume"]
    faces = previous["faces"]
    geom_key = sorted(sorted(tuple(round(x, 6) for x in v)
                             for v in f["vertices"]) for f in faces)
    geom_sha = hashlib.sha256(json.dumps(
        geom_key, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    record_sha = hashlib.sha256(json.dumps(
        spec, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "independent-source-private-convex-preview-verified",
        "coordinate_system": "Godot-local-metres-Y-up",
        "private_brush_spec_sha256": record_sha,
        "private_geometry_sha256_quantized_1e-6m": geom_sha,
        "input_clip_plane_count": len(cuts),
        "active_cut_cap_count": sum(f["kind"] == "private_cut_cap" for f in faces),
        "face_count": len(faces),
        "vertex_count": len(previous["vertices"]),
        "edge_count": previous["edge_count"],
        "triangle_count": previous["triangle_count"],
        "euler_characteristic": (len(previous["vertices"])
                                 - previous["edge_count"] + len(faces)),
        "original_box_volume_m3": original_volume,
        "enclosed_private_volume_m3": previous_volume,
        "local_faces_not_native_bsp": faces,
        "native_bsp_surface_indices_known": False,
        "native_world_model_writer_enabled": False,
        "collision_rebuild_verified": False,
        "runtime_verified": False,
        "original_gmp_or_ibd_modified": False,
    }
