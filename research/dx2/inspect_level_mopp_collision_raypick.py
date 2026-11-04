#!/usr/bin/env python3
"""DX2SDK read-only Level collision-triangle ray picker.

Builds a deterministic, *independent* CPU AABB tree over the triangles
prevalidated by DX2SDK's Level -> Flesh -> MOPP -> provenance -> topology
chain. This does NOT execute Havok MOPP, return game physics materials,
or infer collision filters or a runtime hit-test result.

From repo root, on an original user-owned retail map:
  python research/dx2/inspect_level_mopp_collision_raypick.py MAP.gmp \
    --origin 0 0 0 --direction 0 0 -1 --max-distance 1000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import inspect_level_mopp_collision_topology as topology

SCHEMA = 'DX2SDK-Level-MOPP-collision-geometric-ray-picking-v1'
MAX_TRIANGLES = 300_000
MAX_NODES = 100_000
MAX_HITS = 64
LEAF_FACE_LIMIT = 8
RAY_MIN_DISTANCE = 1e-7
BARYCENTRIC_TOLERANCE = 1e-9


def _valid_xyz(value: Any) -> bool:
    return (isinstance(value, (tuple, list)) and len(value) == 3
            and all(type(x) in (float, int) and math.isfinite(x)
                    and abs(x) <= 1_000_000_000 for x in value))


def _subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class CollisionRayPicker:
    """Strict geometric ray selector for an already validated Level atlas.

    A median-split BVH is deliberately independent of Havok's MOPP encoding:
    a hit is an original source triangle, but not a simulated Havok contact.
    """

    def __init__(self, atlas: dict):
        # Verify the entire source atlas before trusting its triangle/material
        # linkage. The caller must independently authenticate retail bytes via
        # the existing debug.audit_map(source) chain.
        if not isinstance(atlas, dict) or atlas.get('schema') != topology.debug.SCHEMA:
            raise ValueError('Expected source-validated MOPP debug atlas schema')
        self.topology = topology.inspect_topology(atlas)
        self.vertices = atlas['vertices']
        self.triangles = atlas['triangles']
        self.materials = atlas['materials']
        for i, material in enumerate(self.materials):
            if (not isinstance(material, dict) or material.get('id') != i
                    or not isinstance(material.get('render_material_name'), str)
                    or not material['render_material_name']
                    or material.get('physics_material_verified') is not False):
                raise ValueError(f'Invalid/untrusted render material at {i}')
        for tri in self.triangles:
            if (any(type(tri.get(key)) is not int or tri[key] < 0 for key in
                    ('source_block_id', 'render_block_ordinal', 'render_section_ordinal'))):
                raise ValueError('Triangle lacks original source render provenance')
        if len(self.triangles) > MAX_TRIANGLES:
            raise ValueError('Too many collision triangles for ray picking')
        self.face_ids = [t['triangle_id'] for t in self.triangles
                         if t['mopp_terminal_leaf']]
        if not self.face_ids:
            raise ValueError('No MOPP-linked triangles available for picking')
        self.boxes: dict[int, tuple[tuple[float, ...], tuple[float, ...]]] = {}
        self.centers = {}
        for tid in self.face_ids:
            ids = self.triangles[tid]['vertex_indices_zero_based']
            coords = [self.vertices[i] for i in ids]
            lo = tuple(min(p[axis] for p in coords) for axis in range(3))
            hi = tuple(max(p[axis] for p in coords) for axis in range(3))
            self.boxes[tid] = (lo, hi)
            self.centers[tid] = tuple((lo[axis] + hi[axis]) * 0.5
                                      for axis in range(3))
        self.nodes: list[dict] = []
        self.root = self._build(self.face_ids)

    def _build(self, face_ids: list[int]) -> int:
        if not face_ids or len(self.nodes) >= MAX_NODES:
            raise ValueError('BVH node safety limit exceeded')
        lo = tuple(min(self.boxes[tid][0][j] for tid in face_ids) for j in range(3))
        hi = tuple(max(self.boxes[tid][1][j] for tid in face_ids) for j in range(3))
        current = len(self.nodes)
        self.nodes.append({'bbox': (lo, hi), 'left': None, 'right': None,
                           'faces': None})
        if len(face_ids) <= LEAF_FACE_LIMIT:
            self.nodes[current]['faces'] = sorted(face_ids)
            return current
        axis = max(range(3), key=lambda j: (hi[j] - lo[j], -j))
        ordered = sorted(face_ids, key=lambda tid: (self.centers[tid][axis], tid))
        halfway = len(ordered) // 2
        self.nodes[current]['left'] = self._build(ordered[:halfway])
        self.nodes[current]['right'] = self._build(ordered[halfway:])
        return current

    @staticmethod
    def _ray_box(origin, direction, bbox, maximum: float) -> bool:
        lo, hi = bbox
        near, far = 0.0, maximum
        for axis in range(3):
            d = direction[axis]
            if d == 0.0:
                if origin[axis] < lo[axis] or origin[axis] > hi[axis]:
                    return False
                continue
            t0 = (lo[axis] - origin[axis]) / d
            t1 = (hi[axis] - origin[axis]) / d
            if t0 > t1:
                t0, t1 = t1, t0
            near = max(near, t0)
            far = min(far, t1)
            if far < near:
                return False
        return far >= RAY_MIN_DISTANCE

    def _ray_triangle(self, tid: int, origin, direction, maximum: float,
                      cull_backfaces: bool):
        tri = self.triangles[tid]
        a, b, c = [self.vertices[i] for i in tri['vertex_indices_zero_based']]
        e1 = _subtract(b, a)
        e2 = _subtract(c, a)
        pvec = _cross(direction, e2)
        det = _dot(e1, pvec)
        geometric_normal = _cross(e1, e2)
        length = math.sqrt(_dot(geometric_normal, geometric_normal))
        if length == 0:
            raise ValueError('MOPP leaf has zero geometric area')
        # This scaled determinant tolerance avoids exact-parallel division.
        epsilon = 1e-12 * max(1.0, length)
        if (det <= epsilon if cull_backfaces else abs(det) <= epsilon):
            return None
        inv_det = 1.0 / det
        tvec = _subtract(origin, a)
        u = _dot(tvec, pvec) * inv_det
        if not -BARYCENTRIC_TOLERANCE <= u <= 1 + BARYCENTRIC_TOLERANCE:
            return None
        qvec = _cross(tvec, e1)
        v = _dot(direction, qvec) * inv_det
        if v < -BARYCENTRIC_TOLERANCE or u + v > 1 + BARYCENTRIC_TOLERANCE:
            return None
        distance = _dot(e2, qvec) * inv_det
        if not RAY_MIN_DISTANCE <= distance <= maximum:
            return None
        hit_position = [float(origin[k] + distance * direction[k]) for k in range(3)]
        if not all(math.isfinite(v) for v in hit_position):
            raise ValueError('Nonfinite ray/triangle hit position')
        mat = self.materials[tri['render_material_id']]
        return {
            'original_level_triangle_id': tid,
            'distance_in_level_coordinate_units': distance,
            'hit_point_level_xyz': hit_position,
            'barycentric_abc': [1-u-v, u, v],
            'geometric_winding_normal_xyz': [float(x/length) for x in geometric_normal],
            'ray_hits_winding_front_face': det > 0,
            'original_level_vertex_indices': list(tri['vertex_indices_zero_based']),
            'source_block_id': tri['source_block_id'],
            'render_block_ordinal': tri['render_block_ordinal'],
            'render_section_ordinal': tri['render_section_ordinal'],
            'render_material_name': mat['render_material_name'],
            'render_material_is_physics_material': False,
        }

    def cast(self, origin, direction, *, max_distance: float = 1_000_000.0,
             max_hits: int = 8, cull_backfaces: bool = False) -> dict:
        if not _valid_xyz(origin) or not _valid_xyz(direction):
            raise ValueError('Ray origin/direction must be finite XYZ triples')
        if (type(cull_backfaces) is not bool or type(max_hits) is not int
                or not 1 <= max_hits <= MAX_HITS
                or type(max_distance) not in (float, int)
                or not math.isfinite(max_distance) or not 0 < max_distance <= 1e8):
            raise ValueError('Invalid ray query limits')
        length = math.sqrt(sum(d*d for d in direction))
        if not math.isfinite(length) or length == 0:
            raise ValueError('Zero-length or invalid ray direction')
        normalized = tuple(float(d / length) for d in direction)
        origin = tuple(float(x) for x in origin)
        max_distance = float(max_distance)
        todo = [self.root]
        tested_triangles = tested_boxes = 0
        hits = []
        while todo:
            node = self.nodes[todo.pop()]
            tested_boxes += 1
            if not self._ray_box(origin, normalized, node['bbox'], max_distance):
                continue
            if node['faces'] is not None:
                for tid in node['faces']:
                    tested_triangles += 1
                    hit = self._ray_triangle(tid, origin, normalized, max_distance,
                                             cull_backfaces)
                    if hit is not None:
                        hits.append(hit)
            else:
                todo.append(node['right'])
                todo.append(node['left'])
        hits.sort(key=lambda hit: (hit['distance_in_level_coordinate_units'],
                                   hit['original_level_triangle_id']))
        return {
            'schema': SCHEMA,
            'status': 'geometric_hits' if hits else 'geometric_miss',
            'origin_level_xyz': list(origin),
            'direction_normalized_level_xyz': list(normalized),
            'max_distance_in_level_coordinate_units': max_distance,
            'max_results': max_hits,
            'culled_winding_backfaces': cull_backfaces,
            'total_geometric_intersections': len(hits),
            'hits': hits[:max_hits],
            'results_truncated': len(hits) > max_hits,
            'candidate_mopp_leaf_triangles': len(self.face_ids),
            'ignored_zero_area_nonleaf_triangles': (len(self.triangles)-len(self.face_ids)),
            'cpu_bvh_nodes': len(self.nodes),
            'cpu_bvh_boxes_tested': tested_boxes,
            'cpu_triangles_tested': tested_triangles,
            'independent_havok_runtime_hit_test': False,
            'physics_materials_or_filters_decoded': False,
            'native_map_written': False,
        }


def probe_map(source: Path, origin, direction, *, max_distance=1_000_000.0,
              max_hits=8, cull_backfaces=False) -> dict:
    source = Path(source)
    if source.suffix.lower() != '.gmp' or not source.is_file():
        raise ValueError('Expected user-owned source GMP')
    atlas, meta = topology.debug.audit_map(source)
    picker = CollisionRayPicker(atlas)
    result = picker.cast(origin, direction, max_distance=max_distance,
                         max_hits=max_hits, cull_backfaces=cull_backfaces)
    return {
        'source_name': source.name,
        'source_sha256': meta['sha256'],
        'source_licensee': meta['licensee'],
        **result,
    }


def write_report(report: dict, source: Path, output: Path) -> Path:
    """Create a new JSON report only, away from original GMPs."""
    destination = Path(output).resolve()
    source = Path(source).resolve()
    if (destination.suffix.lower() != '.json' or destination == source
            or destination.is_relative_to(source.parent)):
        raise ValueError('Ray query JSON report must be outside source map directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return destination


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--origin', type=float, nargs=3, required=True,
                        metavar=('X', 'Y', 'Z'))
    parser.add_argument('--direction', type=float, nargs=3, required=True,
                        metavar=('DX', 'DY', 'DZ'))
    parser.add_argument('--max-distance', type=float, default=1_000_000.0)
    parser.add_argument('--max-hits', type=int, default=8)
    parser.add_argument('--cull-backfaces', action='store_true')
    parser.add_argument('--report', type=Path,
                        help='Create fresh JSON file outside source map directory')
    args = parser.parse_args(argv)
    try:
        result = probe_map(args.map, args.origin, args.direction,
                           max_distance=args.max_distance, max_hits=args.max_hits,
                           cull_backfaces=args.cull_backfaces)
        if args.report:
            path = write_report(result, args.map, args.report)
            print(json.dumps({'status': result['status'], 'report': str(path),
                              'hits': len(result['hits'])}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, IndexError, OSError, OverflowError) as error:
        print(json.dumps({'status': 'refused', 'reason': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
