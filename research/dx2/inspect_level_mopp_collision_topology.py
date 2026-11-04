#!/usr/bin/env python3
"""DX2 Level MOPP-linked triangle topology audit (read-only, asset-free reports).

Uses verified DX2 Level flattened vertices, MOPP leaves, and render provenance.
Welds only exactly equal f32 XYZ positions. Never infers game Havok shape
semantics, physical materials, airtight collision, or native BSP geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import export_level_mopp_triangle_debug_mesh as debug

SCHEMA = 'DX2SDK-Level-MOPP-edge-topology-v1'
MAX_VERTICES = 300_000
MAX_FACES = 300_000
MAX_INPUT_MAPS = 64
MAX_EXAMPLES = 12


class UnionFind:
    def __init__(self, count: int):
        self.parent = list(range(count))
        self.size = [1] * count

    def root(self, item: int) -> int:
        parent = self.parent
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def join(self, a: int, b: int) -> None:
        a, b = self.root(a), self.root(b)
        if a != b:
            if self.size[a] < self.size[b]:
                a, b = b, a
            self.parent[b] = a
            self.size[a] += self.size[b]


def inspect_topology(atlas: dict, *, include_examples: bool = False) -> dict:
    """Audit topology over *MOPP-linked* triangles using exact-position welding.

    Boundary, material-seam and manifold labels are geometric diagnostics only:
    Havok collision contact behavior and physical materials are unverified.
    """
    if type(include_examples) is not bool or not isinstance(atlas, dict):
        raise ValueError('Invalid atlas or include_examples flag')
    vertices = atlas.get('vertices')
    triangles = atlas.get('triangles')
    materials = atlas.get('materials')
    if (not isinstance(vertices, list) or not isinstance(triangles, list)
            or not 3 <= len(vertices) <= MAX_VERTICES
            or not 1 <= len(triangles) <= MAX_FACES
            or not isinstance(materials, list) or not materials):
        raise ValueError('Invalid source geometry dimensions')
    if (atlas.get('source_vertex_count') != len(vertices)
            or atlas.get('source_triangle_count') != len(triangles)):
        raise ValueError('Source atlas counts disagree with arrays')

    point_to_welded: dict[tuple[float, float, float], int] = {}
    index_to_welded = []
    for i, xyz in enumerate(vertices):
        if (not isinstance(xyz, (tuple, list)) or len(xyz) != 3
                or any(type(v) not in (float, int) or not math.isfinite(v)
                       or abs(v) > 1_000_000 for v in xyz)):
            raise ValueError(f'Invalid flattened vertex {i}')
        # Python numeric equality deliberately canonicalizes signed zero,
        # without tolerance-based welding of distinct original coordinates.
        key = tuple(float(v) for v in xyz)
        if key not in point_to_welded:
            point_to_welded[key] = len(point_to_welded)
        index_to_welded.append(point_to_welded[key])

    # Edge references contain only verified source triangle IDs (no XYZ leak).
    uses: dict[tuple[int, int], list[tuple[int, int, int, int]]] = defaultdict(list)
    mopp_ids = []
    area_sum = 0.0
    area_max = 0.0
    by_material = Counter()
    for tid, triangle in enumerate(triangles):
        if not isinstance(triangle, dict) or triangle.get('triangle_id') != tid:
            raise ValueError(f'Out-of-order or malformed original triangle ID {tid}')
        ids = triangle.get('vertex_indices_zero_based')
        if (not isinstance(ids, (tuple, list)) or len(ids) != 3
                or any(type(v) is not int or v < 0 or v >= len(vertices) for v in ids)):
            raise ValueError(f'Triangle {tid} references invalid flattened vertex')
        linked = triangle.get('mopp_terminal_leaf')
        if type(linked) is not bool:
            raise ValueError(f'Triangle {tid} lacks verified MOPP-leaf status')
        mat = triangle.get('render_material_id')
        if type(mat) is not int or not 0 <= mat < len(materials):
            raise ValueError(f'Triangle {tid} lacks source render material ID')
        a, b, c = (index_to_welded[i] for i in ids)
        if linked and len({a, b, c}) != 3:
            raise ValueError(f'MOPP-linked triangle {tid} has collapsed geometric edge')
        pa, pb, pc = (vertices[i] for i in ids)
        u = [pb[k] - pa[k] for k in range(3)]
        v = [pc[k] - pa[k] for k in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1],
                 u[2]*v[0]-u[0]*v[2],
                 u[0]*v[1]-u[1]*v[0])
        sq = sum(x*x for x in cross)
        if not math.isfinite(sq):
            raise ValueError(f'Triangle {tid} has nonfinite area')
        if not linked:
            if sq != 0:
                raise ValueError(f'Non-MOPP triangle {tid} has nonzero area')
            continue
        if sq <= 0:
            raise ValueError(f'MOPP-linked triangle {tid} has zero area')
        area = math.sqrt(sq)*0.5
        area_sum += area
        area_max = max(area_max, area)
        mopp_ids.append(tid)
        by_material[mat] += 1
        for x, y in ((a, b), (b, c), (c, a)):
            key = (min(x, y), max(x, y))
            uses[key].append((tid, x, y, mat))

    if not mopp_ids or len(mopp_ids) != atlas.get('mopp_leaf_triangle_count'):
        raise ValueError('MOPP triangle coverage disagrees with source atlas')
    if len(triangles)-len(mopp_ids) != atlas.get('zero_area_nonleaf_triangle_count'):
        raise ValueError('MOPP omission count differs from source atlas')
    uf = UnionFind(len(triangles))
    boundary = paired = overfull = same_direction = cross_material = 0
    max_uses = 0
    examples = []
    for key, adjacent in uses.items():
        n = len(adjacent)
        max_uses = max(max_uses, n)
        if n == 1:
            boundary += 1
        else:
            base_tid = adjacent[0][0]
            for tid, *_ in adjacent[1:]:
                uf.join(base_tid, tid)
            if n == 2:
                paired += 1
                same_direction += int(adjacent[0][1:3] == adjacent[1][1:3])
                cross_material += int(adjacent[0][3] != adjacent[1][3])
            else:
                overfull += 1
                if include_examples and len(examples) < MAX_EXAMPLES:
                    examples.append({'welded_edge': list(key),
                                     'triangle_ids': [v[0] for v in adjacent[:MAX_EXAMPLES]],
                                     'incident_triangle_count': n})
    if 3*len(mopp_ids) != sum(len(x) for x in uses.values()):
        raise ValueError('Triangle-edge accounting failure')
    sizes = Counter(uf.root(x) for x in mopp_ids)
    component_sizes = Counter(sizes.values())
    if sum(size*freq for size,freq in component_sizes.items()) != len(mopp_ids):
        raise ValueError('Connected component coverage failure')
    result = {
        'schema': SCHEMA,
        'status': 'read_only_exact_position_welded_triangle_topology',
        'input_flat_vertices': len(vertices),
        'distinct_exact_xyz_positions': len(point_to_welded),
        'duplicated_flat_vertex_positions': len(vertices)-len(point_to_welded),
        'source_flat_triangles': len(triangles),
        'mopp_linked_triangles_audited': len(mopp_ids),
        'non_mopp_leaf_triangles_excluded': len(triangles)-len(mopp_ids),
        'total_triangle_edge_uses': 3*len(mopp_ids),
        'unique_exact_position_edges': len(uses),
        'one_triangle_boundary_edges': boundary,
        'two_triangle_shared_edges': paired,
        'three_or_more_triangle_nonmanifold_edges': overfull,
        'max_triangles_using_one_edge': max_uses,
        'two_triangle_same_winding_direction_edges': same_direction,
        'two_triangle_different_render_material_edges': cross_material,
        'edge_connected_triangle_components': len(sizes),
        'largest_edge_connected_component_faces': max(sizes.values()),
        'single_triangle_components': component_sizes[1],
        'component_size_histogram': dict(sorted((str(s),cnt) for s,cnt in component_sizes.items())),
        'distinct_render_material_ids_in_mopp_leaves': len(by_material),
        'render_material_triangles': {str(k):v for k,v in sorted(by_material.items())},
        'total_level_coordinate_surface_area_squared_units': area_sum,
        'max_triangle_surface_area_squared_units': area_max,
        'all_edges_accounted_for': boundary+2*paired+sum(
            len(x) for x in uses.values() if len(x)>=3) == 3*len(mopp_ids),
        'physical_materials_verified': False,
        'watertight_or_valid_havok_shape_asserted': False,
        'native_collision_writer_available': False,
        'exact_float_welding_only': True,
    }
    if not result['all_edges_accounted_for']:
        raise ValueError('Edge incidences do not balance')
    if include_examples:
        result['nonmanifold_examples'] = examples
    return result


def audit_map(path: Path, *, include_examples: bool=False) -> dict:
    source = Path(path)
    if (source.suffix.lower() != '.gmp' or not source.is_file()
            or source.stat().st_size > debug.provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError('Expected user-owned original DX2 GMP within safety limits')
    atlas, meta = debug.audit_map(source)
    return {**meta, **inspect_topology(atlas, include_examples=include_examples)}


def audit_maps(paths, *, include_examples: bool=False) -> dict:
    if not 1 <= len(paths) <= MAX_INPUT_MAPS:
        raise ValueError('Supply between 1 and 64 maps')
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Duplicate original GMP paths')
    rows = [audit_map(p, include_examples=include_examples) for p in resolved]
    counter = Counter()
    for row in rows:
        counter['maps'] += 1
        for key in ('input_flat_vertices','distinct_exact_xyz_positions',
                    'duplicated_flat_vertex_positions','source_flat_triangles',
                    'mopp_linked_triangles_audited','non_mopp_leaf_triangles_excluded',
                    'total_triangle_edge_uses','unique_exact_position_edges',
                    'one_triangle_boundary_edges','two_triangle_shared_edges',
                    'three_or_more_triangle_nonmanifold_edges',
                    'two_triangle_same_winding_direction_edges',
                    'two_triangle_different_render_material_edges',
                    'edge_connected_triangle_components'):
            counter[key] += row[key]
    return {
        'schema': SCHEMA,
        'read_only': True,
        'original_gmps_modified': False,
        'summary': dict(counter),
        'maps': rows,
        'limitations': [
            'Only exact duplicate positions are welded; no proximity/tolerance merge is performed.',
            'Open edges and multiple incident triangles are diagnostic, not evidence of invalid runtime collision.',
            'Render material groups are not proven Havok physics materials.',
            'The compiled-world BSP Model vertex and surface pools remain unknown.',
            'No native Havok collision builder or DX2 GMP writer is implemented.',
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps', type=Path, nargs='+')
    parser.add_argument('--report', type=Path, help='New JSON outside all original GMP directories')
    parser.add_argument('--include-examples', action='store_true',
                        help='Include up to 12 triangle-ID-only nonmanifold edge examples')
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps,include_examples=args.include_examples)
        if args.report:
            dest = args.report.resolve()
            inputs = [p.resolve() for p in args.maps]
            if dest.suffix.lower() != '.json' or any(
                    dest == p or dest.is_relative_to(p.parent) for p in inputs):
                raise ValueError('JSON output must be newly created outside original map dirs')
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('x',encoding='utf8') as f:
                json.dump(report, f,indent=2,allow_nan=False)
                f.write('\n')
            print(json.dumps({'status':'ok','summary':report['summary'],'report':str(dest)}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return 0
    except (ValueError,OSError,KeyError,IndexError,OverflowError,struct.error) as exc:
        print(json.dumps({'status':'refused','reason':str(exc)}),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())