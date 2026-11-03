#!/usr/bin/env python3
"""Inspect a suspect DX2 BSP render block using ORIGINAL GMP data, read-only.

Example (Seattle WTO/Needle view):
    python map_exporter/dx2_bsp_anomaly_audit.py "C:/DX2/Content/DX2/Maps/M1_Seattle_Hub.gmp" --index 218

This reports evidence. It does not remove geometry or infer retail visibility.
Never include a retail GMP, full triangle dump or exported GLB in public commits.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from dx2scene import Package, find_bsp, unreal_to_world


def bounds(vectors):
    if not vectors:
        return None
    return {"min": [min(p[i] for p in vectors) for i in range(3)],
            "max": [max(p[i] for p in vectors) for i in range(3)]}


def sizes(box):
    return [b-a for a,b in zip(box["min"],box["max"])] if box else [0.0]*3


def triangle_properties(a,b,c):
    ab=[b[i]-a[i] for i in range(3)]
    ac=[c[i]-a[i] for i in range(3)]
    cross=(ab[1]*ac[2]-ab[2]*ac[1],
           ab[2]*ac[0]-ab[0]*ac[2],
           ab[0]*ac[1]-ab[1]*ac[0])
    length=math.sqrt(sum(v*v for v in cross))
    return length/2.0, [v/length for v in cross] if length>1e-10 else [0.0]*3


def block_report(block, index):
    sections=[]
    positions=[]
    for sec in block["sections"]:
        indices=sec["indices"]
        coords=[block["vertices"][i][0] for i in indices]
        positions.extend(coords)
        areas=[]
        normals=[]
        for i in range(0,len(coords)-2,3):
            area, normal=triangle_properties(*coords[i:i+3])
            areas.append(area)
            normals.append(normal)
        box=bounds(coords)
        scaled=bounds([unreal_to_world(x) for x in coords])
        spans=sizes(scaled)
        axis=min(range(3), key=lambda v:spans[v]) if box else -1
        dominant_normal=[sum(abs(n[i])*a for n,a in zip(normals,areas)) / max(sum(areas),1e-12)
                         for i in range(3)]
        sections.append({
            "material":sec["material"],
            "hidden_by_current_exporter":sec["material"].casefold()=="bf",
            "triangles":len(indices)//3,
            "degenerate_triangles":sum(a<1e-10 for a in areas),
            "max_triangle_area_source_units2":max(areas,default=0.0),
            "total_triangle_area_source_units2":sum(areas),
            "bounds_unreal_xyz":box,
            "bounds_godot_xyz":scaled,
            "spans_godot_metres":spans,
            "near_planar_axis_godot":("X","Y","Z")[axis] if axis>=0 and spans[axis]<0.01*max(max(spans),1e-8) else None,
            "area_weighted_absolute_normal_xyz_unreal":dominant_normal
        })
    return {"block_index":index,"source_block_id":block["id"],
            "level_payload_offset":block["offset"],
            "vertex_count":len(block["vertices"]),
            "total_triangles":sum(s["triangles"] for s in sections),
            "materials":list(dict.fromkeys(s["material"] for s in sections)),
            "bounds_unreal_xyz":bounds(positions),
            "bounds_godot_xyz":bounds([unreal_to_world(p) for p in positions]),
            "sections":sections}


def audit(package, index):
    blocks=find_bsp(package)
    if index<0 or index>=len(blocks):
        raise ValueError("BSP index %d invalid: source has %d validated render blocks" % (index,len(blocks)))
    target=block_report(blocks[index],index)
    box=target["bounds_godot_xyz"]
    neighborhood=[]
    if box:
        for i,block in enumerate(blocks):
            if i==index:
                continue
            pts=[unreal_to_world(block["vertices"][v][0])
                 for sec in block["sections"] for v in sec["indices"]]
            bb=bounds(pts)
            if bb is None:
                continue
            gaps=[max(0.0,box["min"][k]-bb["max"][k],bb["min"][k]-box["max"][k])
                  for k in range(3)]
            gap=math.sqrt(sum(g*g for g in gaps))
            neighborhood.append((gap,i,[s["material"] for s in block["sections"]]))
    neighborhood.sort(key=lambda row:(row[0],row[1]))
    target.update({
        "validated_source_block_count":len(blocks),
        "nearest_aabb_blocks":[{"index":i,"aabb_gap_godot_m":round(gap,5),
                                "materials":materials[:5]}
                               for gap,i,materials in neighborhood[:12]],
        "interpretation_note":(
            "This proves which raw triangles the current exporter reads. "
            "It does NOT establish whether DX2 renders the block in-game, "
            "whether it is an editor/portal surface, or whether native visibility "
            "flags were missed. Do not delete source BSP based only on this report.")
    })
    return target


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gmp",type=Path,help="Original map .gmp, never modified")
    ap.add_argument("--index",type=int,default=218,help="DX2Ed's BSP_NNN node index (default: 218)")
    ap.add_argument("--output",type=Path,help="Optional new report JSON (cannot overwrite)")
    args=ap.parse_args(argv)
    if args.gmp.suffix.lower()!=".gmp" or not args.gmp.is_file():
        ap.error("Select a readable original .gmp")
    pkg=Package(args.gmp)
    raw_sha=hashlib.sha256(pkg.data).hexdigest()
    report={"schema":"dx2ed-readonly-bsp-source-audit-v1",
            "map":args.gmp.name,"source_gmp_sha256":raw_sha,
            "source_modified":False,"render_visibility_verified":False,
            "target":audit(pkg,args.index)}
    if args.output:
        output=args.output.resolve()
        if output==args.gmp.resolve() or (
            args.gmp.parent.resolve() == output.parent and
            output.suffix.lower() in (".gmp",".ibd")):
            ap.error("Refusing to overwrite retail map data")
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open("x",encoding="utf8") as f:
            json.dump(report,f,indent=2)
        print("Read-only report:",output)
    else:
        print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
