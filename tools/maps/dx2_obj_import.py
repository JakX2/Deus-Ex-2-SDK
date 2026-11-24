#!/usr/bin/env python3
"""Convert a strict triangulated OBJ subset to the DX2 native mesh JSON format.

All faces require positive position/UV/normal indices. Split corner tuples
at seams, preserve native winding, or explicitly convert from the SDK's
GLB preview coordinate convention. No external files/materials are loaded.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re

from dx2_mesh_writer import parse_geometry, MAX_JSON_BYTES, MAX_VERTICES, MAX_INDICES

MAX_OBJ_BYTES=16*1024*1024
PREVIEW_SCALE=0.01905


def convert_obj(text, *, coordinates="native"):
    if coordinates not in ("native","sdk-preview"):
        raise ValueError("Unknown coordinate convention")
    if len(text.encode("utf-8"))>MAX_OBJ_BYTES:
        raise ValueError("OBJ exceeds input limit")
    positions=[];uv=[];normals=[];triangles=[]
    materials=set()
    for number,line in enumerate(text.splitlines(),1):
        fields=line.split("#",1)[0].split()
        if not fields:continue
        tag,values=fields[0],fields[1:]
        if tag in ("v","vt","vn"):
            count=2 if tag=="vt" else 3
            if len(values)!=count:
                raise ValueError(f"OBJ line {number}: unsupported vector layout")
            row=tuple(float(x) for x in values)
            if not all(math.isfinite(x) and abs(x)<1e6 for x in row):
                raise ValueError(f"OBJ line {number}: nonfinite or oversized component")
            target={"v":positions,"vt":uv,"vn":normals}[tag]
            target.append(row)
            if len(target)>MAX_VERTICES:
                raise ValueError("OBJ attribute limit exceeded")
        elif tag=="f":
            if len(values)!=3:
                raise ValueError(f"OBJ line {number}: triangulate faces before export")
            triangle=[]
            for corner in values:
                if not re.fullmatch(r"[1-9][0-9]{0,5}/[1-9][0-9]{0,5}/[1-9][0-9]{0,5}",corner):
                    raise ValueError(f"OBJ line {number}: expected positive v/vt/vn indices")
                a,b,c=(int(x)-1 for x in corner.split("/"))
                if a>=len(positions) or b>=len(uv) or c>=len(normals):
                    raise ValueError(f"OBJ line {number}: index outside defined attributes")
                triangle.append((a,b,c))
            triangles.append(triangle)
            if len(triangles)*3>MAX_INDICES:
                raise ValueError("OBJ index limit exceeded")
        elif tag=="usemtl":
            if len(values)!=1:raise ValueError("Unsupported material name")
            materials.add(values[0])
            if len(materials)>1:raise ValueError("Only one material section supported")
        elif tag in ("o","g","s","mtllib"):
            # Metadata only; the original native material is preserved.
            continue
        else:
            raise ValueError(f"OBJ line {number}: unsupported directive {tag}")
    result={"positions":[],"normals":[],"uv":[],"indices":[]}
    lookup={}
    for triangle in triangles:
        if coordinates=="sdk-preview":
            triangle=[triangle[0],triangle[2],triangle[1]]
        for corner in triangle:
            if corner not in lookup:
                if len(lookup)>=MAX_VERTICES:raise ValueError("Split vertex limit exceeded")
                a,b,c=corner
                p=positions[a];n=normals[c]
                if coordinates=="sdk-preview":
                    p=(p[0]/PREVIEW_SCALE,p[2]/PREVIEW_SCALE,p[1]/PREVIEW_SCALE)
                    n=(n[0],n[2],n[1])
                lookup[corner]=len(lookup)
                result["positions"].append(list(p))
                result["normals"].append(list(n))
                result["uv"].append(list(uv[b]))
            result["indices"].append(lookup[corner])
    parse_geometry(result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--coordinates",choices=("native","sdk-preview"),required=True)
    args=p.parse_args(argv)
    try:
        if args.source.is_symlink() or not args.source.is_file() or args.source.stat().st_size>MAX_OBJ_BYTES:
            raise ValueError("Invalid or oversized OBJ")
        if args.output.exists() or args.output.is_symlink() or args.output.suffix.lower()!=".json":
            raise ValueError("Output must be a new JSON file")
        with args.source.open("rb") as stream:
            raw=stream.read(MAX_OBJ_BYTES+1)
        if len(raw)>MAX_OBJ_BYTES:raise ValueError("OBJ exceeds input limit")
        doc=convert_obj(raw.decode("utf-8"),coordinates=args.coordinates)
        data=json.dumps(doc,separators=(",",":"),allow_nan=False).encode()
        if len(data)>MAX_JSON_BYTES:raise ValueError("Geometry JSON exceeds writer limit")
        with args.output.open("xb") as stream:stream.write(data)
        print(json.dumps({"vertices":len(doc["positions"]),"triangles":len(doc["indices"])//3,
                          "runtime_verified":False,"collision_generated":False}))
        return 0
    except (OSError,ValueError,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":raise SystemExit(main())
