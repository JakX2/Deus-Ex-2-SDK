"""Exact-source-coordinate edge provenance for MOPP-linked DX2 Level triangles.

Geometric diagnostics only. Does not infer Havok contact response, original
physics materials, native BSP polygon boundaries, or writable game geometry.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math

SCHEMA = 'DX2Ed-MOPP-source-exact-edge-provenance-v1'
# 0: two incident triangles, same render-material ID
# 1: one incident triangle (open boundary)
# 2: two incident triangles, different render-material IDs
# 3: three or more incident triangles (non-manifold)
EDGE_INTERIOR = 0
EDGE_BOUNDARY = 1
EDGE_RENDER_SEAM = 2
EDGE_NONMANIFOLD = 3
CODE_NAMES = ('interior', 'open_boundary', 'render_material_seam', 'nonmanifold')
MAX_VERTICES = 300_000
MAX_TRIANGLES = 300_000
MAX_MATERIALS = 100_000


def classify_source_edges(atlas: dict) -> dict:
    """Return per-triangle-edge labels in original source Level triangle order.

    Source XYZ is *not rounded* and no epsilon welding is performed.
    Only validated MOPP terminal-leaf triangles participate. Nonleaf
    zero-area triangles are excluded and retain null codes.
    """
    if not isinstance(atlas, dict):
        raise ValueError('Expected verified original collision atlas')
    verts, triangles, materials = (atlas.get(k) for k in ('vertices', 'triangles', 'materials'))
    if (not isinstance(verts, list) or not isinstance(triangles, list)
            or not isinstance(materials, list) or not materials
            or not 3 <= len(verts) <= MAX_VERTICES
            or not 1 <= len(triangles) <= MAX_TRIANGLES
            or not 1 <= len(materials) <= MAX_MATERIALS
            or len(verts) != atlas.get('source_vertex_count')
            or len(triangles) != atlas.get('source_triangle_count')):
        raise ValueError('Atlas counts, geometry or material array invalid')
    exact_welds: dict[tuple[float, float, float], int] = {}
    weld_id = []
    for p in verts:
        if (not isinstance(p, (list, tuple)) or len(p) != 3
                or any(type(x) not in (int, float) or not math.isfinite(x)
                       or abs(x) > 1_000_000 for x in p)):
            raise ValueError('Invalid original Level vertex coordinate')
        xyz = tuple(float(x) for x in p)
        if xyz not in exact_welds:
            exact_welds[xyz] = len(exact_welds)
        weld_id.append(exact_welds[xyz])
    incident: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    codes: list[list[int] | None] = [None] * len(triangles)
    active = 0
    for tid, face in enumerate(triangles):
        if (not isinstance(face, dict) or type(face.get('triangle_id')) is not int
                or face['triangle_id'] != tid):
            raise ValueError('Out-of-order original Level triangle ID order mismatch')
        ids = face.get('vertex_indices_zero_based')
        mat = face.get('render_material_id')
        linked = face.get('mopp_terminal_leaf')
        if (not isinstance(ids, (tuple, list)) or len(ids) != 3
                or any(type(i) is not int or not 0 <= i < len(verts) for i in ids)
                or type(mat) is not int or not 0 <= mat < len(materials)
                or type(linked) is not bool):
            raise ValueError('Malformed original source triangle')
        if not linked:
            continue
        welded = [weld_id[i] for i in ids]
        if len(set(welded)) != 3:
            raise ValueError('Collapsed MOPP source triangle edge')
        a, b, c = [verts[i] for i in ids]
        v = [b[i]-a[i] for i in range(3)]
        w = [c[i]-a[i] for i in range(3)]
        cross = (v[1]*w[2]-v[2]*w[1], v[2]*w[0]-v[0]*w[2], v[0]*w[1]-v[1]*w[0])
        squared = sum(x*x for x in cross)
        if not math.isfinite(squared) or squared <= 0:
            raise ValueError('Degenerate MOPP source triangle')
        active += 1
        codes[tid] = [-1, -1, -1]
        for slot, (p, q) in enumerate(((welded[0], welded[1]),
                                        (welded[1], welded[2]),
                                        (welded[2], welded[0]))):
            incident[min(p, q), max(p, q)].append((tid, slot, mat))
    if not active or active != atlas.get('mopp_leaf_triangle_count'):
        raise ValueError('MOPP leaf counts incompatible with source atlas')
    if len(triangles)-active != atlas.get('zero_area_nonleaf_triangle_count'):
        raise ValueError('Nonleaf triangle counts incompatible with source atlas')
    counts = Counter()
    max_incidents = 0
    for adjacent in incident.values():
        n = len(adjacent)
        max_incidents = max(max_incidents, n)
        if n == 1:
            code = EDGE_BOUNDARY
        elif n == 2:
            code = EDGE_RENDER_SEAM if adjacent[0][2] != adjacent[1][2] else EDGE_INTERIOR
        else:
            code = EDGE_NONMANIFOLD
        counts[CODE_NAMES[code]] += 1
        for tid, slot, _ in adjacent:
            if codes[tid][slot] != -1:
                raise ValueError('Source triangle edge assigned twice')
            codes[tid][slot] = code
    if (any(row is not None and (-1 in row or len(row) != 3) for row in codes)
            or sum(counts.values()) != len(incident)
            or sum(len(row) for row in codes if row is not None)
            != sum(len(e) for e in incident.values())):
        raise ValueError('Incomplete exact source edge accounting')
    return {
        'schema': SCHEMA,
        'edge_codes_by_original_triangle_id': codes,
        # Stable exact-original-Level-XYZ weld IDs, independent of preview f32 rounding.
        'exact_source_weld_id_by_vertex_index': weld_id,
        'source_exact_welded_vertex_count': len(exact_welds),
        'unique_source_edges': len(incident),
        'open_boundary_edges': counts[CODE_NAMES[EDGE_BOUNDARY]],
        'two_triangle_same_material_edges': counts[CODE_NAMES[EDGE_INTERIOR]],
        'two_triangle_render_material_seams': counts[CODE_NAMES[EDGE_RENDER_SEAM]],
        'three_or_more_triangle_edges': counts[CODE_NAMES[EDGE_NONMANIFOLD]],
        'max_triangles_using_one_edge': max_incidents,
        'mopp_leaf_triangles': active,
        'physical_materials_verified': False,
        'source_coordinate_welding': 'exact_float32_values_no_epsilon',
        'native_map_written': False,
    }
