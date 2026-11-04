#!/usr/bin/env python3
"""Source GMP read-only capsule first-contact audit, geometry and MOPP comparison.

No proprietary vertex coordinates or contact-point positions are exported.
Exact or compatible Havok time-of-impact/contact normals are NOT established.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

import export_level_mopp_triangle_debug_mesh as exporter
import audit_mopp_offsurface_segments as sampler
import inspect_mopp_point_triangle_oracle as geometry
import inspect_mopp_axis_point_candidates as spatial
import inspect_mopp_swept_capsule as prior
import inspect_mopp_capsule_first_contact as first

SCHEMA="DX2SDK-original-Level-capsule-first-contact-audit-v1"


def audit_source_level(level,blocks,*,bbox_random=16,triangle_aimed=16,
                       radius=.2,axis_half_length=.5,axis=(0.,0.,1.),
                       seed=20261104,tolerance_units=1.):
    sampler._validated_options(bbox_random,triangle_aimed,seed)
    r,unit,half=prior._shape(radius,axis,axis_half_length)
    atlas=exporter.inspect_mesh(level,blocks)
    oracle=geometry.original_atlas_oracle(atlas)
    checked=exporter.provenance.mopp.inspect_mopp_link(level,blocks)
    code_start=checked['mopp_code_start_in_level']
    walker=spatial.ConservativeMoppPointCandidates(
        level[code_start:checked['mopp_code_end_in_level']],
        atlas['source_triangle_count'],
        struct.unpack_from('<4f',level,code_start-20))
    if set(oracle.tris)!=walker.complete_leaf_set:
        raise ValueError('Original Level geometry IDs mismatch authenticated MOPP leaves')
    bounds=sampler._bbox(oracle)
    rng=random.Random(seed ^ int.from_bytes(hashlib.sha256(level).digest()[:8],'little'))
    source_ids=sorted(oracle.tris)
    counts=Counter();failed=[];sum_t=0.
    for category,n in [('bbox_random',bbox_random),('triangle_aimed',triangle_aimed)]:
        for i in range(n):
            if category=='bbox_random':
                a,b=sampler._random_bbox_segment(oracle,rng,bounds)
                target=None
            else:
                a,b,target=sampler._triangle_aimed_segment(oracle,rng,bounds,source_ids)
            result=first.compare_first_contact_with_full_sweep(
                oracle,a,b,r,unit,half)
            newids=set(result['contact_original_triangle_ids'])
            previousids=set(result['full_sweep_original_triangle_ids'])
            if target is not None and target not in newids:
                raise ValueError('Independent aimed source triangle absent at capsule first contact')
            counts[f'{category}_sweeps']+=1
            counts[f'{category}_sweeps_with_contact']+=bool(newids)
            counts[f'{category}_full_sweep_geometry_hit_ids']+=len(previousids)
            counts[f'{category}_first_contact_geometry_hit_ids']+=len(newids)
            counts[f'{category}_missing_previous_oracle_ids']+=len(previousids-newids)
            counts[f'{category}_extra_relative_to_previous_oracle_ids']+=len(newids-previousids)
            if previousids!=newids and len(failed)<12:
                failed.append({'category':category,'sample_index':i,
                    'missing_original_ids':sorted(previousids-newids)[:32],
                    'extra_original_ids':sorted(newids-previousids)[:32]})
            first_hit=result['first_contact']
            if first_hit is not None:
                counts[f'{category}_first_normal_resolved']+=bool(first_hit.contact_normal_resolved)
                counts[f'{category}_first_initial_overlap']+=bool(first_hit.initial_overlap)
                counts[f'{category}_first_grazing_uncertain']+=bool(first_hit.near_tangency)
                counts[f'{category}_first_numerical_margin_only']+=bool(first_hit.numerical_contact_only)
                sum_t+=first_hit.t_first_inside
            for mode in spatial.DIAGONAL_MODES:
                candidate=prior.swept_capsule_mopp_candidates(
                    walker,a,b,r,unit,half,diagonal_mode=mode,
                    tolerance_units=tolerance_units)
                missing=newids-set(candidate['candidate_original_triangle_ids'])
                counts[f'{category}_{mode}_comparisons']+=1
                counts[f'{category}_{mode}_missing_hit_queries']+=bool(missing)
                if missing and len(failed)<12:
                    failed.append({'category':category,'mode':mode,
                        'sample_index':i,'missing_MOPP_original_ids':sorted(missing)[:32]})
    return {'schema':SCHEMA,
        'source_level_sha256':hashlib.sha256(level).hexdigest(),
        'source_triangle_count':atlas['source_triangle_count'],
        'original_mopp_leaf_count':len(oracle.tris),
        'capsule_radius_level_units':r,
        'axis_unit_xyz':list(unit),
        'half_axis_length_level_units':half,
        'seed':seed,
        'random_seed_mixed_with_Level_source_sha':True,
        'time_bracket_tolerance':1e-8,
        'distance_tolerance_level_units':1e-7,
        'counts':dict(counts),
        'sum_first_hit_normalized_t':sum_t,
        'first_failure_original_IDs_without_coordinates':failed,
        'havok_runtime_contacts_verified':False,
        'original_gmp_bytes_modified':False}


def audit_map(path:Path,**opts):
    path=Path(path).resolve()
    if (not path.is_file() or path.suffix.lower()!='.gmp' or
            path.stat().st_size>exporter.provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError('Expected owner-supplied original DX2 GMP within bounds')
    atlas,meta=exporter.audit_map(path)
    package_root=Path(__file__).resolve().parents[2]/'map_exporter'
    if str(package_root) not in sys.path:sys.path.insert(0,str(package_root))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg=Package(path)
    sha=hashlib.sha256(pkg.data).hexdigest()
    if sha!=meta['sha256']:
        raise ValueError('Original source GMP changed between validations')
    levels=[e for e in pkg.exports if pkg.class_name(e)=='Level' and e['size']>0]
    if len(levels)!=1:raise ValueError('Expected exactly one source Level export')
    result=audit_source_level(pkg.payload(levels[0]),find_bsp(pkg),**opts)
    if result['source_triangle_count']!=atlas['source_triangle_count']:
        raise ValueError('Original Level triangle count changed between validations')
    return {'original_map':path.name,'original_gmp_sha256':sha,**result}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps',type=Path,nargs='+')
    parser.add_argument('--bbox-random',type=int,default=16)
    parser.add_argument('--triangle-aimed',type=int,default=16)
    parser.add_argument('--radius',type=float,default=.2)
    parser.add_argument('--axis-half-length',type=float,default=.5)
    parser.add_argument('--axis',type=float,nargs=3,default=(0.,0.,1.))
    parser.add_argument('--seed',type=int,default=20261104)
    parser.add_argument('--tolerance-units',type=float,default=1.)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv)
    try:
        sampler._validated_options(args.bbox_random,args.triangle_aimed,args.seed)
        prior._shape(args.radius,args.axis,args.axis_half_length)
        if not 1<=len(args.maps)<=64:
            raise ValueError('Expected 1..64 owner-supplied original GMP maps')
        paths=[p.resolve() for p in args.maps]
        if len(set(paths))!=len(paths):raise ValueError('Duplicate original GMP paths')
        rows=[audit_map(p,bbox_random=args.bbox_random,triangle_aimed=args.triangle_aimed,
            radius=args.radius,axis=args.axis,axis_half_length=args.axis_half_length,
            seed=args.seed,tolerance_units=args.tolerance_units) for p in paths]
        total=Counter()
        for row in rows:total.update(row['counts'])
        missing=sum(v for k,v in total.items() if k.endswith(('_missing_previous_oracle_ids',
                   '_extra_relative_to_previous_oracle_ids','_missing_hit_queries')))
        report={'schema':SCHEMA,'maps_checked':len(rows),'summary':dict(total),
                'geometry_disagreements_or_missing_candidates':missing,'per_map':rows,
                'original_assets_modified':False,'havok_runtime_verified':False}
        if args.report:
            dest=args.report.resolve()
            if dest.suffix.lower()!='.json' or any(
                    dest==s or dest.is_relative_to(s.parent) for s in paths):
                raise ValueError('Report must be a fresh JSON outside retail source Maps')
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('x',encoding='utf-8') as f:
                json.dump(report,f,indent=2,allow_nan=False)
                f.write('\n')
            print(json.dumps({'status':'ok','report':str(dest),'disagreements':missing}))
        else:print(json.dumps(report,indent=2,allow_nan=False))
        return int(missing>0)
    except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError,
            struct.error) as exc:
        print(json.dumps({'status':'refused','reason':str(exc)}),file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
