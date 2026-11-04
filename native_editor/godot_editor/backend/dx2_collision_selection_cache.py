#!/usr/bin/env python3
"""Build an optional, read-only DX2Ed original-collision selection sidecar.

The sidecar is *not* a Havok shape/collision writer, original physics material,
or an input to GMP Save As. All source GMP bytes are read-only; files are
created exclusively in DX2Ed's separate private cache directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "research" / "dx2"
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))
import export_level_mopp_triangle_debug_mesh as debug

SCHEMA = "DX2Ed-source-MOPP-collision-selection-cache-v1"
# Original DX2 render coordinates -> Godot world: x,z,y * 0.01905.
# Level flattened coordinates = original render XYZ * 0.1905, therefore
# Level flattened XYZ -> Godot scene preview XYZ = (x,z,y) / 10.
LEVEL_TO_GODOT = 0.1
MAX_SOURCE_BYTES = 250 * 1024 * 1024
MAX_VERTICES = 300_000
MAX_TRIANGLES = 300_000


def _sha256(s: str) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def prepare_doc(atlas: dict, *, source_name: str, source_sha256: str) -> dict:
    """Prepare minimal, order-preserving collision triangle references for Godot."""
    if (not isinstance(source_name, str) or not source_name.lower().endswith('.gmp')
            or not _sha256(source_sha256) or not isinstance(atlas, dict)
            or atlas.get('schema') != debug.SCHEMA
            or atlas.get('render_material_names_are_physics_materials') is not False):
        raise ValueError('Invalid verified source metadata or atlas schema')
    vertices = atlas.get('vertices')
    faces = atlas.get('triangles')
    materials = atlas.get('materials')
    if (not isinstance(vertices, list) or not 3 <= len(vertices) <= MAX_VERTICES
            or not isinstance(faces, list) or not 1 <= len(faces) <= MAX_TRIANGLES
            or not isinstance(materials, list) or not materials
            or len(vertices) != atlas.get('source_vertex_count')
            or len(faces) != atlas.get('source_triangle_count')):
        raise ValueError('Source atlas geometry is missing or exceeds safety limits')
    verts = []
    for p in vertices:
        if (not isinstance(p, (tuple, list)) or len(p) != 3 or
                any(type(x) not in (int, float) or not math.isfinite(x) for x in p)):
            raise ValueError('Invalid Level flat XYZ')
        converted = [p[0]*LEVEL_TO_GODOT, p[2]*LEVEL_TO_GODOT, p[1]*LEVEL_TO_GODOT]
        if any(not math.isfinite(v) or abs(v) > 100_000 for v in converted):
            raise ValueError('Converted coordinate outside conservative bounds')
        verts.append(converted)
    names = []
    for i, mat in enumerate(materials):
        if (not isinstance(mat, dict) or mat.get('id') != i
                or mat.get('physics_material_verified') is not False
                or not isinstance(mat.get('render_material_name'), str)
                or not mat['render_material_name']):
            raise ValueError('Unverified render material provenance')
        names.append(mat['render_material_name'])
    leaf_faces = []
    for i, tri in enumerate(faces):
        if not isinstance(tri, dict) or tri.get('triangle_id') != i:
            raise ValueError('Original Level triangle ID order mismatch')
        ids = tri.get('vertex_indices_zero_based')
        mat = tri.get('render_material_id')
        if (not isinstance(ids, list) or len(ids) != 3
                or any(type(v) is not int or not 0 <= v < len(verts) for v in ids)
                or type(mat) is not int or not 0 <= mat < len(names)
                or any(type(tri.get(k)) is not int or tri[k] < 0 for k in
                       ('source_block_id', 'render_block_ordinal', 'render_section_ordinal'))
                or type(tri.get('mopp_terminal_leaf')) is not bool):
            raise ValueError('Malformed source triangle provenance')
        if tri['mopp_terminal_leaf']:
            leaf_faces.append({
                'triangle_id': i,
                'vertex_indices': ids,
                'source_block_id': tri['source_block_id'],
                'render_block_ordinal': tri['render_block_ordinal'],
                'render_section_ordinal': tri['render_section_ordinal'],
                'render_material_id': mat,
            })
    if (not leaf_faces or len(leaf_faces) != atlas.get('mopp_leaf_triangle_count')
            or len(faces)-len(leaf_faces) != atlas.get('zero_area_nonleaf_triangle_count')):
        raise ValueError('Missing or mismatched validated MOPP leaves')
    return {
        'schema': SCHEMA,
        'source_map': source_name,
        'source_sha256': source_sha256,
        'read_only': True,
        'not_a_native_collision_writer': True,
        'physics_materials_verified': False,
        'coordinate_system': 'Godot preview (Level.x/10, Level.z/10, Level.y/10)',
        'source_flat_vertex_count': len(verts),
        'source_triangle_count': len(faces),
        'mopp_leaf_triangle_count': len(leaf_faces),
        'vertices_godot_xyz': verts,
        'render_material_names': names,
        'leaf_triangles': leaf_faces,
    }


def build(source: Path, destination: Path, *, expected_sha256: str) -> dict:
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (not source.is_file() or source.suffix.lower() != '.gmp'
            or source.stat().st_size > MAX_SOURCE_BYTES or
            not _sha256(expected_sha256)):
        raise ValueError('Expected original DX2 GMP and valid source SHA-256')
    if (destination.suffix.lower() != '.json' or destination == source
            or destination.parent == source.parent
            or destination.is_relative_to(source.parent)):
        raise ValueError('Selection sidecar must be outside original map directory')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Source GMP hash differs from the open editor scene')
    if destination.exists():
        # Stale cache is never silently adopted: authenticate its file provenance.
        doc = json.loads(destination.read_text(encoding='utf-8'))
        if (not isinstance(doc, dict) or doc.get('schema') != SCHEMA
                or doc.get('source_sha256') != digest or
                doc.get('source_map') != source.name or
                doc.get('read_only') is not True or
                doc.get('physics_materials_verified') is not False):
            raise ValueError('Untrusted or stale collision selection cache; refuse reuse')
        return {'status': 'ok', 'cache': 'existing', 'output': str(destination),
                'triangles': doc.get('mopp_leaf_triangle_count')}
    atlas, meta = debug.audit_map(source)  # complete verified Level -> MOPP chain
    if meta.get('sha256') != digest:
        raise ValueError('Source hash changed during geometry verification')
    doc = prepare_doc(atlas, source_name=source.name, source_sha256=digest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
        f.write('\n')
    return {'status': 'ok', 'cache': 'created', 'output': str(destination),
            'triangles': len(doc['leaf_triangles']),
            'source_sha256': digest}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--map', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--expected-sha256', required=True)
    args = ap.parse_args(argv)
    try:
        print(json.dumps(build(args.map, args.output, expected_sha256=args.expected_sha256)))
        return 0
    except (ValueError, OSError, KeyError, IndexError, TypeError,
            OverflowError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'refused', 'reason': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())