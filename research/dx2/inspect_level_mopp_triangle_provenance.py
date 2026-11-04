#!/usr/bin/env python3
"""Read-only DX2 collision-triangle to Flesh render-block/section provenance audit.

Source-observed Level array of 8-byte (block ID, render-section ID) records
precedes the PR27 flattened mesh header. The MOPP decoder from PR28 supplies
independently validated triangle leaves. Material strings are RENDER SECTION
names, not proven Havok physics materials or collision filter properties.
Original .gmp files are never modified or executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import inspect_level_mopp_triangle_tree as mopp

SCHEMA = 'DX2SDK-Level-MOPP-triangle-render-section-provenance-v1'
RECORD_SIZE = 8
FRAMING_U32 = (0, 0, 0, 0x6F000000, 0x013E4312)
FRAME_SIZE = 24
MAX_SOURCE_MATERIALS = 16384


def inspect_triangle_provenance(level: bytes, blocks: list[dict], *,
                                include_materials: bool = False) -> dict:
    """Verify every Level (block,section) pair against all source render sections.

    All structure offsets are independently anchored by the PR27 validated
    flattened index array and the source-observed u32 triangle count/marker.
    The MOPP terminal IDs must also cover all nondegenerate triangles.
    """
    if type(include_materials) is not bool:
        raise ValueError('include_materials must be boolean')
    validated = mopp.inspect_mopp_link(level, blocks)
    flat = mopp.flatcheck.inspect_level_flattened_mesh(level, blocks)
    triangle_count = flat['render_and_flat_triangle_count']
    count_at = flat['level_vertex_count_pair_offset']
    table_end = count_at - 4
    table_start = table_end - RECORD_SIZE * triangle_count
    prefix_start = table_start - FRAME_SIZE
    if prefix_start < 0:
        raise ValueError('Level lacks bounded triangle provenance framing')
    framing = struct.unpack_from('<6I', level, prefix_start)
    if framing != FRAMING_U32 + (triangle_count,):
        raise ValueError('Triangle provenance marker/count does not match validated flattened mesh')
    # The preceding flattened-mesh header embeds a NUL-terminated Level name
    # after 32 bytes. This check is layout evidence only, not asset ownership.
    name_length = struct.unpack_from('<I', level, table_end)[0]
    if not 1 <= name_length <= 1024 or count_at + 32 + name_length != flat['level_flat_vertex_array_offset']:
        raise ValueError('Unexpected subsequent flattened-geometry name/header boundary')
    name = level[count_at + 32:count_at + 32 + name_length]
    if not name.endswith(b'\x00') or b'\x00' in name[:-1] or not all(32 <= c < 127 for c in name[:-1]):
        raise ValueError('Unrecognized flattened-geometry source-name encoding')
    records = list(struct.iter_unpack('<II', level[table_start:table_end]))
    if len(records) != triangle_count:
        raise ValueError('Incomplete triangle provenance record array')
    triangle_materials = []
    section_refs = set()
    block_refs = []
    triangle_cursor = 0
    max_in_block = 0
    for bi, block in enumerate(blocks):
        sections = block.get('sections')
        if not isinstance(sections, list) or not sections:
            raise ValueError(f'Render block {bi} has invalid section table')
        ref = None
        triangles_this_block = 0
        for section_id, section in enumerate(sections):
            indices = section.get('indices')
            material = section.get('material')
            if (not isinstance(indices, (list, tuple)) or len(indices) % 3
                    or not isinstance(material, str) or not material):
                raise ValueError(f'Invalid render section {bi}:{section_id}')
            num_triangles = len(indices)//3
            if triangle_cursor + num_triangles > triangle_count:
                raise ValueError('Render sections exceed Level triangle mapping')
            for label_block, label_section in records[triangle_cursor:triangle_cursor+num_triangles]:
                if label_section != section_id:
                    raise ValueError(f'Triangle {triangle_cursor}: section ID disagrees with render section')
                if ref is None:
                    ref = label_block
                elif ref != label_block:
                    raise ValueError(f'Triangle {triangle_cursor}: block ID changes inside one render block')
                triangle_materials.append(material)
                triangle_cursor += 1
            if num_triangles:
                section_refs.add((ref, section_id))
                triangles_this_block += num_triangles
        if ref is None or triangles_this_block == 0:
            raise ValueError(f'Render block {bi} has no source triangles')
        if block_refs and ref <= block_refs[-1]:
            raise ValueError(f'Block ID {ref} not strictly increasing across render blocks')
        block_refs.append(ref)
        max_in_block = max(max_in_block, triangles_this_block)
    if triangle_cursor != triangle_count or len(triangle_materials) != triangle_count:
        raise ValueError('Triangle provenance does not cover every flattened triangle')
    if len(block_refs) > MAX_SOURCE_MATERIALS:
        raise ValueError('Excessive source block references')
    gap_count = block_refs[0] + sum(block_refs[i]-block_refs[i-1]-1 for i in range(1,len(block_refs)))
    if gap_count != block_refs[-1] + 1 - len(block_refs):
        raise ValueError('Inconsistent skipped native block reference accounting')
    code = level[validated['mopp_code_start_in_level']:validated['mopp_code_end_in_level']]
    tree = mopp.trace_mopp_code(code, triangle_count)
    leaves = tree['reachable_terminal_triangle_ids']
    if len(leaves) != validated['unique_valid_mopp_triangle_leaves']:
        raise ValueError('MOPP terminal-leaf count changed after provenance validation')
    material_counts = Counter(triangle_materials)
    covered_material_counts = Counter(triangle_materials[t] for t in leaves)
    result = {
        'status': 'all_level_triangles_map_to_render_block_and_section',
        'framing_six_u32_verified': True,
        'framing_constant_words_observed': [hex(v) for v in FRAMING_U32[-2:]],
        'triangle_provenance_record_size_bytes': RECORD_SIZE,
        'triangle_provenance_record_count': len(records),
        'triangle_provenance_start_in_level': table_start,
        'triangle_provenance_end_in_level': table_end,
        'verified_packed_render_blocks': len(blocks),
        'unique_monotone_block_ids': len(block_refs),
        'first_block_id': block_refs[0],
        'last_block_id': block_refs[-1],
        'skipped_nonnegative_block_ids': gap_count,
        'distinct_block_section_pairs': len(section_refs),
        'max_triangles_per_render_block': max_in_block,
        'distinct_render_material_name_strings': len(material_counts),
        'mopp_leaves_with_render_section_attribution': len(leaves),
        'non_mopp_leaf_triangle_count': triangle_count-len(leaves),
        'mopp_zero_area_triangle_exceptions_prevalidated': validated['zero_area_triangle_count'],
        'render_section_names_are_havok_physics_materials': False,
        'collision_shape_and_material_properties_decoded': False,
        'runtime_collision_instantiated': False,
        'native_writer_implemented': False,
    }
    if include_materials:
        result['render_materials'] = [
            {'material_string': name, 'all_triangles': count,
             'mopp_leaf_triangles': covered_material_counts[name]}
            for name, count in sorted(material_counts.items())
        ]
    return result


def audit_map(path: Path, *, include_materials: bool=False) -> dict:
    path = Path(path)
    if path.suffix.lower() != '.gmp' or not path.is_file() or path.stat().st_size > mopp.flatcheck.MAX_MAP_BYTES:
        raise ValueError('Expected user-owned UE95 DX2 .gmp within source size limit')
    root = Path(__file__).resolve().parents[2]
    exporter = root / 'map_exporter'
    if str(exporter) not in sys.path:
        sys.path.insert(0,str(exporter))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in mopp.flatcheck.OBSERVED_LICENSEES:
        raise ValueError('Expected UE95 DX2 licensee 65/67/68/69')
    levels = [e for e in pkg.exports if pkg.class_name(e)=='Level' and e['size']>0]
    if len(levels)!=1:
        raise ValueError('Expected a unique nonempty Level export')
    level = pkg.payload(levels[0])
    blocks = find_bsp(pkg)
    return {
        'file':path.name,
        'source_sha256':hashlib.sha256(pkg.data).hexdigest(),
        'licensee':pkg.licensee,
        **inspect_triangle_provenance(level,blocks,include_materials=include_materials),
    }


def audit_maps(paths, *, include_materials:bool=False) -> dict:
    if not 1 <= len(paths) <= mopp.flatcheck.MAX_MAPS:
        raise ValueError('Provide 1 to 64 user-owned GMPs')
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Duplicate GMP inputs')
    rows = [audit_map(path,include_materials=include_materials) for path in resolved]
    totals = Counter()
    for row in rows:
        totals['maps']+=1
        for key in ('triangle_provenance_record_count','verified_packed_render_blocks',
                    'distinct_block_section_pairs','skipped_nonnegative_block_ids',
                    'mopp_leaves_with_render_section_attribution',
                    'non_mopp_leaf_triangle_count'):
            totals[key]+=row[key]
    return {
        'schema':SCHEMA, 'read_only':True,'game_files_modified':False,
        'render_materials_not_proven_havok_physics_materials':True,
        'summary':dict(totals), 'maps':rows,
        'limitations':[
            'Pair fields are source-verified block/section provenance references, not Havok filter/material IDs.',
            'Skipped first-field IDs have unknown semantics; they are not necessarily missing geometry.',
            'MOPP leaves are resolved symbolically; this does not instantiate Havok collision.',
            'Full BSP Model vertex pool, native writer and successful DX2 runtime geometry cooking remain unknown.',
        ],
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps',nargs='+',type=Path)
    parser.add_argument('--report',type=Path,help='Write fresh JSON outside source map directories')
    parser.add_argument('--include-materials',action='store_true',help='Include source render-section strings in private JSON output')
    args=parser.parse_args(argv)
    try:
        report=audit_maps(args.maps,include_materials=args.include_materials)
        if args.report:
            output=args.report.resolve()
            inputs=[p.resolve() for p in args.maps]
            if output.suffix.lower()!='.json' or any(output==x or output.is_relative_to(x.parent) for x in inputs):
                raise ValueError('JSON report must be created outside all source map directories')
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('x',encoding='utf-8') as stream:
                json.dump(report,stream,indent=2,allow_nan=False)
                stream.write('\n')
            print(json.dumps({'status':'ok','report':str(output),'summary':report['summary']}))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,IndexError,struct.error,OverflowError) as error:
        print(json.dumps({'status':'refused','reason':str(error)}),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
