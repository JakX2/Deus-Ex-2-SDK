#!/usr/bin/env python3
"""Independent f32 Level-space point/triangle geometric oracle for DX2 research.

AABB BVH and double-precision projected barycentric predicate are independent
of MOPP opcode traversal, output bases, filtering and Havok runtime. This
module identifies EVERY source triangle geometrically containing a test point
within declared tolerances, not just the triangle from which it was sampled.
No game-file writer and no physical-material semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

SCHEMA = "DX2SDK-source-Level-geometric-point-triangle-oracle-v1"
MAX_VERTICES = 300_000
MAX_TRIANGLES = 300_000
MAX_BVH_NODES = 2 * MAX_TRIANGLES


def _point(value, *, label):
    if (not isinstance(value, (tuple, list)) or len(value) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   or abs(x) > 1_000_000 for x in value)):
        raise ValueError(f"{label} requires three finite bounded XYZ values")
    return tuple(float(x) for x in value)


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _dot(a, b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def _orient(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


@dataclass(frozen=True)
class _Tri:
    id: int
    a: tuple[float, float, float]
    b: tuple[float, float, float]
    c: tuple[float, float, float]
    normal: tuple[float, float, float]
    normal_len: float
    dominant: int
    box_lo: tuple[float, float, float]
    box_hi: tuple[float, float, float]


class LevelPointTriangleOracle:
    """Pure geometric truth oracle. Inputs retain original Level triangle IDs.

    Faces are (i0, i1, i2, is_mopp_terminal_leaf) in original order.
    Nonleaf zero-area faces are skipped. Never epsilon-weld vertex indices.
    """

    def __init__(self, vertices, faces, *, leaf_ids=None):
        if (not isinstance(vertices, (tuple, list)) or
                not isinstance(faces, (tuple, list)) or
                not 3 <= len(vertices) <= MAX_VERTICES or
                not 1 <= len(faces) <= MAX_TRIANGLES):
            raise ValueError("Source mesh vertex/triangle count outside bounds")
        self.vertices = [_point(v, label="Source Level vertex") for v in vertices]
        self.original_triangle_count = len(faces)
        self.tris: dict[int, _Tri] = {}
        active = []
        for original_id, face in enumerate(faces):
            if (not isinstance(face, (tuple, list)) or len(face) != 4 or
                    any(type(i) is not int or not 0 <= i < len(vertices)
                        for i in face[:3]) or type(face[3]) is not bool):
                raise ValueError(f"Malformed original Level triangle {original_id}")
            a, b, c = (self.vertices[i] for i in face[:3])
            n = _cross(_sub(b, a), _sub(c, a))
            length = math.hypot(*n)
            if not math.isfinite(length):
                raise ValueError("Source triangle normal outside finite range")
            if length == 0:
                if face[3]:
                    raise ValueError("Degenerate MOPP terminal-leaf triangle")
                continue
            if not face[3]:
                raise ValueError("Nondegenerate source triangle missing MOPP terminal leaf")
            lo = tuple(min(a[k], b[k], c[k]) for k in range(3))
            hi = tuple(max(a[k], b[k], c[k]) for k in range(3))
            t = _Tri(original_id, a, b, c, n, length,
                     max(range(3), key=lambda k: abs(n[k])), lo, hi)
            self.tris[original_id] = t
            active.append(original_id)
        if not active:
            raise ValueError("No nondegenerate MOPP-linked source triangles")
        if leaf_ids is not None:
            if (not isinstance(leaf_ids, (list, tuple, set)) or
                    any(type(x) is not int for x in leaf_ids) or
                    set(active) != set(leaf_ids) or len(leaf_ids) != len(active)):
                raise ValueError("Independent MOPP leaf-ID set differs from Level geometry")
        self.nodes = []
        self.root = self._build(active)

    def _build(self, ids):
        if len(self.nodes) >= MAX_BVH_NODES:
            raise ValueError("Too many source geometry BVH nodes")
        lo = tuple(min(self.tris[i].box_lo[a] for i in ids) for a in range(3))
        hi = tuple(max(self.tris[i].box_hi[a] for i in ids) for a in range(3))
        slot = len(self.nodes)
        self.nodes.append(None)
        if len(ids) <= 8:
            self.nodes[slot] = (lo, hi, -1, -1, tuple(ids))
            return slot
        axis = max(range(3), key=lambda a: hi[a]-lo[a])
        ids.sort(key=lambda i: ((self.tris[i].box_lo[axis] +
                                 self.tris[i].box_hi[axis]) / 2, i))
        mid = len(ids)//2
        left = self._build(ids[:mid])
        right = self._build(ids[mid:])
        self.nodes[slot] = (lo, hi, left, right, ())
        return slot

    @staticmethod
    def _contains(t, p, plane_tolerance, barycentric_tolerance):
        """World-length plane tolerance plus unitless 2D barycentric tolerance."""
        if any(p[k] < t.box_lo[k] - plane_tolerance or
               p[k] > t.box_hi[k] + plane_tolerance for k in range(3)):
            return False
        if abs(_dot(t.normal, _sub(p, t.a))) > plane_tolerance*t.normal_len:
            return False
        axes = tuple(k for k in range(3) if k != t.dominant)
        a, b, c, q = (tuple(v[k] for k in axes)
                       for v in (t.a, t.b, t.c, p))
        denom = _orient(a, b, c)
        if denom == 0:
            raise ValueError("Numerically invalid projected source triangle")
        w0 = _orient(b, c, q)/denom
        w1 = _orient(c, a, q)/denom
        w2 = _orient(a, b, q)/denom
        return (min(w0, w1, w2) >= -barycentric_tolerance and
                max(w0, w1, w2) <= 1 + barycentric_tolerance and
                abs(w0+w1+w2-1) <= 10*barycentric_tolerance+1e-10)

    def containing_triangle_ids(self, xyz, *, plane_tolerance=1e-5,
                                barycentric_tolerance=1e-8):
        p = _point(xyz, label="Geometric probe")
        if (type(plane_tolerance) not in (float, int) or
                type(barycentric_tolerance) not in (float, int) or
                not math.isfinite(plane_tolerance) or
                not math.isfinite(barycentric_tolerance) or
                not 0 <= plane_tolerance <= 1 or
                not 0 <= barycentric_tolerance <= 0.01):
            raise ValueError("Invalid declared geometric tolerances")
        hits = []
        todo = [self.root]
        while todo:
            lo, hi, left, right, ids = self.nodes[todo.pop()]
            if any(p[k] < lo[k]-plane_tolerance or
                   p[k] > hi[k]+plane_tolerance for k in range(3)):
                continue
            if ids:
                for tid in ids:
                    if self._contains(self.tris[tid], p,
                                      plane_tolerance, barycentric_tolerance):
                        hits.append(tid)
            else:
                todo.extend((left, right))
        return sorted(hits)

    def sample_triangle(self, original_id, barycentric):
        if type(original_id) is not int or original_id not in self.tris:
            raise ValueError("Unknown original MOPP triangle ID")
        if (not isinstance(barycentric, (list, tuple)) or len(barycentric) != 3 or
                any(type(w) not in (int, float) or not math.isfinite(w) or
                    w < 0 or w > 1 for w in barycentric) or
                abs(sum(barycentric)-1) > 1e-12):
            raise ValueError("Barycentric sample must be valid and sum to one")
        t = self.tris[original_id]
        return tuple(sum(barycentric[j]*v[k] for j, v in enumerate((t.a,t.b,t.c)))
                     for k in range(3))


def compare_point_to_mopp(oracle, walker, xyz, *, diagonal_mode="conservative",
                          tolerance_units=1.0):
    """Compare all geometric hits, not only the seed source triangle ID."""
    if not isinstance(oracle, LevelPointTriangleOracle):
        raise ValueError("Expected independent Level-space geometry oracle")
    truth = oracle.containing_triangle_ids(xyz)
    result = walker.point(xyz, diagonal_mode=diagonal_mode,
                          tolerance_units=tolerance_units)
    candidates = result["candidate_triangle_ids"]
    if (not isinstance(candidates, list) or any(type(i) is not int
            or i not in oracle.tris for i in candidates)):
        raise ValueError("MOPP candidates contain unverified original source triangle IDs")
    missing = sorted(set(truth).difference(candidates))
    extra = sorted(set(candidates).difference(truth))
    return {
        "schema": SCHEMA,
        "point_xyz": list(_point(xyz, label="Probe point")),
        "geometric_hit_original_triangle_ids": truth,
        "mopp_candidate_original_triangle_ids": candidates,
        "geometrically_intersecting_triangles_missing_from_mopp": missing,
        "mopp_candidates_not_at_this_exact_point": extra,
        "all_geometric_hits_retained": not missing,
        "geometric_hit_count": len(truth),
        "candidate_count": len(candidates),
        "diagonal_mode": diagonal_mode,
        "mopp_output_is_havok_runtime_contact": False,
        "geometry_oracle_is_independent_of_mopp_opcode_traversal": True,
        "collision_shape_builder_available": False,
        "game_files_modified": False,
    }


def original_atlas_oracle(atlas):
    """Accept the verified PR30 original-index atlas, preserving missing leaf IDs."""
    if not isinstance(atlas, dict):
        raise ValueError("Expected source-verified triangle atlas")
    verts, triangles = atlas.get("vertices"), atlas.get("triangles")
    if not isinstance(verts, list) or not isinstance(triangles, list):
        raise ValueError("Atlas lacks original Level geometry")
    faces = []
    for expected_id, row in enumerate(triangles):
        if (not isinstance(row, dict) or row.get("triangle_id") != expected_id):
            raise ValueError("Atlas triangle IDs are out of original Level order")
        idx = row.get("vertex_indices_zero_based")
        leaf = row.get("mopp_terminal_leaf")
        if not isinstance(idx, (list, tuple)) or type(leaf) is not bool:
            raise ValueError("Missing original triangle index or MOPP leaf flag")
        faces.append((*idx, leaf))
    if (len(verts) != atlas.get("source_vertex_count") or
            len(triangles) != atlas.get("source_triangle_count")):
        raise ValueError("Unverified source atlas geometry count")
    return LevelPointTriangleOracle(verts, faces)
