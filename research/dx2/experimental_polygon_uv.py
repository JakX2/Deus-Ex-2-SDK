#!/usr/bin/env python3
"""Source-pinned experimental fixed-width Level polygon UV translation.

Only the primary UV and its three identical expanded copies are changed.
No geometry, topology, Model node, packed secondary UV, material, collision
or game installation changes. A runtime visual effect is not yet verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from inspect_level_expanded_polygons import (
    parse_expanded_polygons, match_expanded_render, validate_counted_render_array,
    STRIDE, UV_REPEAT_TOL,
)
import inspect_level_world_model as world
import inspect_world_bsp_node_boundaries as boundaries
import inspect_world_bsp_zone_relations as zones
from dx2scene import find_bsp

SCHEMA = "DX2SDK-experimental-expanded-polygon-uv-translation-v1"
MAX_GMP = 128 * 1024 * 1024
UV_PAIR_OFFSETS = (24, 68, 76, 84)
PACKED_UV_OFFSET = 16
MAX_DELTA = 16.


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _delta(delta):
    if (not isinstance(delta, (tuple,list)) or len(delta)!=2
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or abs(x)>MAX_DELTA for x in delta)
            or not any(delta)):
        raise ValueError("Expected nonzero finite UV delta, each axis within +/-16")
    return tuple(float(x) for x in delta)


def _shift_pair(old,delta):
    values=struct.unpack("<2f",old)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite original UV")
    new=struct.pack("<2f",*(v+d for v,d in zip(values,delta)))
    actual=struct.unpack("<2f",new)
    if (not all(math.isfinite(v) for v in actual)
            or any(abs((a-v)-d)>UV_REPEAT_TOL or (d!=0 and a==v)
                   for a,v,d in zip(actual,values,delta))):
        raise ValueError("Requested UV delta is not representable at source float32 precision")
    return new


def _patch_level(level,row,link,blocks,delta):
    """Pure fixed-size patch on a previously validated polygon crosswalk.

    Raw original pairs are retained only in memory for byte-exact reversal.
    """
    delta=_delta(delta)
    n=len(row["vertices"])
    if (not 3<=n<=64 or link["polygon"]!=row["polygon"]
            or link["packed_vertex_count"]!=n):
        raise ValueError("Expanded polygon/link count or identity mismatch")
    block=blocks[link["packed_block"]]
    packed_start=link["packed_vertex_start"]
    if not 0<=packed_start<=len(block["vertices"])-n:
        raise ValueError("Packed polygon vertex span out of bounds")
    spans=[]
    expanded_start=row["start"]+2
    if (row["start"]<0 or row["end"]>len(level)
            or expanded_start+n*STRIDE+4>row["end"]
            or struct.unpack_from("<H",level,row["start"])[0]!=n):
        raise ValueError("Expanded polygon envelope mismatch")
    for i,v in enumerate(row["vertices"]):
        a=expanded_start+i*STRIDE
        b=block["offset"]+80+(packed_start+i)*32
        if b<0 or b+32>block["end"] or b+32>len(level):
            raise ValueError("Packed vertex envelope mismatch")
        if (struct.unpack_from("<23f",level,a)!=v
                or struct.unpack_from("<3f",level,b)!=v[:3]
                or struct.unpack_from("<2f",level,b+16)!=block["vertices"][packed_start+i][2]):
            raise ValueError("Polygon decoded vertex differs from original bytes")
        old=level[a+24:a+32]
        if (level[a+32:a+68]!=bytes(36)
                or any(level[a+j:a+j+8]!=old for j in UV_PAIR_OFFSETS)):
            raise ValueError("Expanded UV duplicate/zero profile not supported")
        packed=level[b+16:b+24]
        shift=_shift_pair(old,delta)
        packed_shift=_shift_pair(packed,delta)
        old_delta=link["packed_uv_integer_delta"]
        if any(abs(x-y-d)>UV_REPEAT_TOL for x,y,d in
               zip(struct.unpack("<2f",packed_shift),struct.unpack("<2f",shift),old_delta)):
            raise ValueError("UV translation would break expanded/packed integer-repeat association")
        for j in UV_PAIR_OFFSETS:
            spans.append((a+j,old,shift))
        spans.append((b+PACKED_UV_OFFSET,packed,packed_shift))
    spans.sort()
    out=bytearray(level)
    end=-1
    for at,old,new in spans:
        if at<end or level[at:at+8]!=old:
            raise ValueError("UV byte spans overlap or differ from original")
        out[at:at+8]=new
        end=at+8
    restored=bytearray(out)
    for at,old,new in spans:
        if restored[at:at+8]!=new:
            raise ValueError("UV patch readback mismatch")
        restored[at:at+8]=old
    if bytes(restored)!=level or len(out)!=len(level) or bytes(out)==level:
        raise ValueError("UV patch reversibility or fixed-width gate failed")
    return bytes(out),spans


def _read_context(path,raw):
    from dx2sdk.bsp_mopp_plane_impact import _source_triangle_rows
    pkg=world.Package(path,data=raw)
    if pkg.version!=95 or pkg.licensee not in world.OBSERVED_LICENSEES:
        raise ValueError("Expected source-observed DX2 UE95 licensee")
    ref=world._parse_world_model(pkg)["world_model_export_ref"]
    model=pkg.payload(pkg.exports[ref-1])
    frame=boundaries.parse_world_model(model,include_nodes=True)
    zones.inspect_zone_relations(model,frame)
    levels=[e for e in pkg.exports if pkg.class_name(e)=="Level" and e["size"]>0]
    if len(levels)!=1:
        raise ValueError("Expected unique nonempty Level export")
    exp=levels[0]
    level=pkg.payload(exp)
    blocks=find_bsp(pkg)
    if not blocks or any(b["offset"]<4 or b["end"]>len(level)
                         or b["id"]!=b["end"]-b["offset"] for b in blocks):
        raise ValueError("Invalid original packed render block framing")
    if any(a["end"]>b["offset"]-4 for a,b in zip(blocks,blocks[1:])):
        raise ValueError("Overlapping render block envelopes")
    collision,prov=_source_triangle_rows(level,blocks)
    block_frame=validate_counted_render_array(level,blocks,collision)
    start=block_frame["render_block_array_end"]
    end=prov["triangle_provenance_start_in_level"]-24
    polygons,framing=parse_expanded_polygons(level,start,end,sum(
        len(b["vertices"]) for b in blocks))
    counts,links=match_expanded_render(polygons,blocks)
    counts.update({k:v for k,v in block_frame.items() if k.startswith("native_render_")})
    seen=[tuple(k) for link in links for k in link["triangle_locators"]]
    expected={tuple(r["render_locator"]) for r in collision}
    if len(seen)!=len(expected) or set(seen)!=expected:
        raise ValueError("Incomplete original polygon collision attribution")
    return pkg,exp,level,model,blocks,polygons,links,collision,counts,end


def translate_polygon_uv(path,raw,*,expected_sha256,polygon,delta):
    """Return isolated candidate package bytes and an aggregate verification.

    The source pin is mandatory. Full source and modified packages are
    reparsed independently of the byte-patch construction. No disk writes.
    """
    if (type(raw) is not bytes or not 0<len(raw)<=MAX_GMP
            or type(expected_sha256) is not str or sha(raw)!=expected_sha256):
        raise ValueError("Original package SHA-256 pin mismatch or invalid size")
    delta=_delta(delta)
    before=_read_context(path,raw)
    pkg,exp,level,model,blocks,rows,links,collision,counts,end=before
    if type(polygon) is not int or not 0<=polygon<len(rows):
        raise ValueError("Original expanded polygon ordinal out of bounds")
    modified,spans=_patch_level(level,rows[polygon],links[polygon],blocks,delta)
    at=exp["offset"]
    if raw[at:at+exp["size"]]!=level or len(modified)!=exp["size"]:
        raise ValueError("Level export source bytes or length mismatch")
    edited=raw[:at]+modified+raw[at+len(level):]
    after=_read_context(path,edited)
    pkg2,exp2,level2,model2,blocks2,rows2,links2,collision2,counts2,end2=after
    if (pkg.names!=pkg2.names or pkg.imports!=pkg2.imports
            or pkg.exports!=pkg2.exports or exp!=exp2 or level2!=modified
            or model!=model2 or end!=end2 or level[end:]!=level2[end:]
            or collision!=collision2 or links!=links2):
        raise ValueError("Reparsed package metadata, Model, collision or polygon links changed")
    # Original UV equality may change only through source float32 rounding.
    # Every other aggregate crosswalk count must remain identical.
    if {k:v for k,v in counts.items() if k!="exact_uv_polygons"}!={
            k:v for k,v in counts2.items() if k!="exact_uv_polygons"}:
        raise ValueError("Reparsed expanded polygon inventory changed")
    restored=bytearray(edited)
    changed=0
    for offset,old,new in spans:
        absolute=at+offset
        if restored[absolute:absolute+8]!=new:
            raise ValueError("Reparsed UV source span does not match candidate")
        restored[absolute:absolute+8]=old
        changed+=sum(a!=b for a,b in zip(old,new))
    if bytes(restored)!=raw or len(edited)!=len(raw):
        raise ValueError("Full package restoration or size gate failed")
    return edited,{"schema":SCHEMA,"source_sha256":expected_sha256,
        "candidate_sha256":sha(edited),"polygon":polygon,"delta":list(delta),
        "polygon_vertex_count":len(rows[polygon]["vertices"]),
        "expanded_uv_pairs_updated":len(rows[polygon]["vertices"])*4,
        "packed_primary_uv_pairs_updated":len(rows[polygon]["vertices"]),
        "verified_patch_span_count":len(spans),"changed_bytes":changed,
        "full_package_byte_exact_reversal":True,
        "package_tables_unchanged":True,"world_model_unchanged":True,
        "collision_tail_byte_identical":True,"collision_provenance_unchanged":True,
        "all_other_bytes_unchanged":True,"native_geometry_writer_enabled":False,
        "retail_runtime_verified":False}


def _isolated_path(source,target):
    source=source.resolve()
    target=target.resolve()
    parts=tuple(x.casefold() for x in target.parent.parts)
    if (target.name.casefold()!=source.name.casefold()
            or target==source or source.parent==target.parent
            or source.parent in target.parents or target.exists()
            or any(parts[i:i+3]==("content","dx2","maps")
                   for i in range(max(0,len(parts)-2)))):
        raise ValueError("Output must be a fresh isolated private GMP with original basename")
    return target


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path)
    p.add_argument("--expected-sha256",required=True)
    p.add_argument("--polygon",type=int,required=True)
    p.add_argument("--delta",type=float,nargs=2,required=True,metavar=("DU","DV"))
    p.add_argument("--output",type=Path,help="Explicit isolated output; otherwise dry-run")
    a=p.parse_args(argv)
    try:
        if (a.source.suffix.casefold()!=".gmp" or not a.source.is_file()
                or a.source.is_symlink() or a.source.stat().st_size>MAX_GMP):
            raise ValueError("Expected bounded user-owned original GMP")
        raw=a.source.read_bytes()
        out,report=translate_polygon_uv(a.source,raw,expected_sha256=a.expected_sha256,
                                      polygon=a.polygon,delta=a.delta)
        if sha(a.source.read_bytes())!=a.expected_sha256:
            raise ValueError("Original source changed during verification")
        report["candidate_written"]=False
        if a.output:
            target=_isolated_path(a.source,a.output)
            # The directory must already exist. Never write to game installation.
            with target.open("xb") as f:
                f.write(out)
            if sha(target.read_bytes())!=report["candidate_sha256"]:
                raise ValueError("Isolated candidate readback SHA mismatch")
            report["candidate_written"]=True
        print(json.dumps(report,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,KeyError,struct.error,OverflowError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
