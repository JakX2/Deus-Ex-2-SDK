#!/usr/bin/env python3
"""Private aggregate audit of original DX2 materials and clone/rebind candidates.

Optionally corroborate standalone material-library records by full source
path and material name. No paths, material names, source bytes or candidate
archives are emitted. Full clone verification is opt-in and may be slow.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile

from dx2_ibd_integrity import (
    MAX_BUNDLE_BYTES, MAX_ZIP_BYTES, MAX_ZIP_MEMBERS, MAX_ZIP_EXPANDED,
    verify_bundle, sha256,
)
from dx2_material_writer import inspect_material, select_texture, clone_and_bind, reverse_clone_trial
from dx2_texture_writer import inspect_layout

MLB_RECORD_SIZE = 788
MLB_HEADER_SIZE = 12
MAX_MLB_SIZE = 32 * 1024 * 1024


def members(path, suffix, limit):
    """Yield bounded members without extracting or printing archive names."""
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_ZIP_BYTES:
        raise ValueError("Invalid or oversized source ZIP")
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if len(entries) > MAX_ZIP_MEMBERS:
            raise ValueError("ZIP member count exceeds limit")
        total = 0
        seen = set()
        for info in entries:
            if info.is_dir() or not info.filename.lower().endswith(suffix):
                continue
            path_name = info.filename.replace("\\","/").casefold()
            parts = PurePosixPath(path_name).parts
            if (not parts or path_name.startswith("/") or ".." in parts or
                    ":" in parts[0] or path_name in seen):
                raise ValueError("Unsafe or duplicate ZIP member")
            seen.add(path_name)
            total += info.file_size
            if not 0 < info.file_size <= limit or total > MAX_ZIP_EXPANDED:
                raise ValueError("Expanded ZIP member exceeds limit")
            with z.open(info) as src:
                raw = src.read(info.file_size+1)
            if len(raw) != info.file_size:
                raise ValueError("ZIP member length mismatch")
            yield path_name, raw


def fixed_string(data, *, require_zero_tail=False):
    n = data.find(b"\0")
    if n < 0 or (require_zero_tail and any(data[n+1:])):
        raise ValueError("Invalid fixed string field")
    return data[:n].decode("ascii")


def read_mlb(raw):
    if len(raw) < MLB_HEADER_SIZE:
        raise ValueError("Truncated material library")
    version, magic, count = struct.unpack_from("<3I",raw)
    if (version,magic)!=(3,0xFACE) or count>40000 or len(raw)!=12+count*788:
        raise ValueError("Unsupported material library layout")
    rows=[]
    for i in range(count):
        record=raw[12+i*788:12+(i+1)*788]
        name=fixed_string(record[:64],require_zero_tail=True)
        if not name:
            raise ValueError("Empty library material name")
        rows.append((name,record))
    return rows


def source_key(source):
    p=source.replace("\\","/").casefold()
    parts=p.split("/")
    positions=[i for i,x in enumerate(parts) if x=="matlib"]
    if len(positions)!=1:
        return None
    tail=parts[positions[0]:]
    if any(x in ("",".","..") for x in tail) or not tail[-1].endswith(".mlb"):
        return None
    return "/".join(tail)


def audit(ibd_zip, *, mlb_zip=None, verify_clones=False):
    totals=Counter()
    formats=Counter()
    libraries=defaultdict(list)
    for key in ("ibd_bundles","materials","active_diffuse","inactive_diffuse",
                "eligible_diffuse","unresolved_or_unsupported_diffuse","clone_reversals",
                "header_relocations","mlb_libraries","mlb_records","mlb_unique_matches",
                "mlb_no_source_path","mlb_missing_record","mlb_ambiguous_record",
                "mlb_diffuse_exact","mlb_flags_exact","mlb_stage_mask_exact"):
        totals[key]=0
    if mlb_zip is not None:
        for path,raw in members(mlb_zip,".mlb",MAX_MLB_SIZE):
            key=source_key(path)
            if key is None:
                raise ValueError("Library member outside MatLib tree")
            totals["mlb_libraries"]+=1
            for name,record in read_mlb(raw):
                totals["mlb_records"]+=1
                libraries[(key,name.casefold())].append(record)
        if not totals["mlb_libraries"]:
            raise ValueError("No standalone material libraries found")
    for _,raw in members(ibd_zip,".ibd",MAX_BUNDLE_BYTES):
        bundle=verify_bundle(raw)
        totals["ibd_bundles"]+=1
        pin=sha256(raw)
        for resource in bundle.resources:
            if resource.typ!=10:
                continue
            layout=inspect_material(bundle,resource)
            totals["materials"]+=1
            if mlb_zip is not None:
                key=source_key(layout.parts[18][:-1].decode("ascii"))
                records=libraries.get((key,resource.name.casefold()),[])
                if key is None:
                    totals["mlb_no_source_path"]+=1
                elif not records:
                    totals["mlb_missing_record"]+=1
                elif len(records)!=1:
                    totals["mlb_ambiguous_record"]+=1
                else:
                    record=records[0]
                    totals["mlb_unique_matches"]+=1
                    totals["mlb_diffuse_exact"]+=fixed_string(record[148:212])==layout.stages[0]
                    totals["mlb_flags_exact"]+=record[144:148]==layout.parts[1]
                    totals["mlb_stage_mask_exact"]+=record[64:68]==layout.parts[2]
            old=layout.stages[0]
            if not old:
                totals["inactive_diffuse"]+=1
                continue
            totals["active_diffuse"]+=1
            try:
                texture=inspect_layout(bundle,select_texture(bundle,old))
            except (ValueError,IndexError):
                totals["unresolved_or_unsupported_diffuse"]+=1
                continue
            totals["eligible_diffuse"]+=1
            formats[texture.texture.fmt]+=1
            if verify_clones:
                # Fixed deterministic name, not exported. Collisions refuse.
                new_name="DX2SDK_private_clone_"+str(resource.index)
                candidate=clone_and_bind(raw,resource.name,new_name,palette="cyan")
                parsed=verify_bundle(candidate)
                if reverse_clone_trial(candidate,pin,resource.name,old,new_name,palette="cyan")!=raw:
                    raise ValueError("Original clone reverse comparison failed")
                totals["clone_reversals"]+=1
                totals["header_relocations"]+=parsed.data_start>bundle.data_start
    if not totals["ibd_bundles"] or not totals["materials"]:
        raise ValueError("No bundled materials audited")
    return {"schema":"DX2-MaterialAudit-v1","counts":dict(totals),
            "eligible_formats":dict(formats),"clone_verification_requested":verify_clones,
            "standalone_comparison_requested":mlb_zip is not None,
            "runtime_verified":False,"source_modified":False,"game_assets_included":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ibd_zip",type=Path)
    parser.add_argument("--mlb-zip",type=Path)
    parser.add_argument("--verify-clones",action="store_true")
    args=parser.parse_args(argv)
    try:
        result=audit(args.ibd_zip,mlb_zip=args.mlb_zip,verify_clones=args.verify_clones)
    except (OSError,ValueError,IndexError,struct.error,zipfile.BadZipFile):
        # Do not expose private asset paths or filenames in failure output.
        print(json.dumps({"status":"refused","reason":"Private material audit failed"}))
        return 2
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
