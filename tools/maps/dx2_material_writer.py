#!/usr/bin/env python3
"""Experimental DX2 material edit and append-only texture cloning.

Requires a canonical, digest-valid original IBD. Material bindings may be
redirected only to a compatible texture within that same archive. Cloning
adds an existing 2D texture with a new unique name and optional diagnostic
recolor. This is archive/record validation, not retail engine acceptance.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import struct
import sys

from dx2_ibd_integrity import read_bounded, verify_bundle, sha256
from dx2_ibd_repack import _build, _parts, rebuild_canonical
from dx2_texture_writer import inspect_layout, select_texture, marker_mips, PALETTES
from dx2bundles import HEADER_SIZE, ENTRY_SIZE
from dx2textures import parse_material

NAME_OFFSET = 41
MAX_NEW_NAME = 96
FIXED_PREFIX = (1,4,4,16,16,16,4,4,4,1,4,4,1,1,1,4,4,4)


@dataclass(frozen=True)
class MaterialLayout:
    parts: tuple
    stages: tuple
    mask: int
    colors: tuple


def select_material(bundle, name):
    matches = [r for r in bundle.resources if r.typ == 10 and
               r.name.casefold() == name.casefold()]
    if len(matches) != 1:
        raise ValueError("Expected exactly one original material with that name")
    return matches[0]


def _string(parts, slot):
    if len(parts[slot]) != 4:
        raise ValueError("Invalid material string length field")
    n = struct.unpack("<I",parts[slot])[0]
    data = parts[slot+1]
    if not 1 <= n <= 4096 or len(data) != n or data[-1:] != b"\0" or b"\0" in data[:-1]:
        raise ValueError("Invalid NUL-terminated material string")
    return data[:-1].decode("ascii")


def inspect_material(bundle, resource):
    if resource.typ != 10 or resource.size > 65536:
        raise ValueError("Unsupported material resource")
    parts = tuple(bundle.parts(resource))
    if (len(parts) != 40 or tuple(map(len,parts[:18])) != FIXED_PREFIX or
            parts[0] != b"\0" or tuple(map(len,parts[19:22])) != (4,1,4)):
        raise ValueError("Unsupported version-0 material layout")
    source = _string(parts,17)
    stages = tuple(_string(parts,i) for i in range(22,40,2))
    mask = struct.unpack("<I",parts[2])[0]
    if mask != sum(1<<i for i,s in enumerate(stages) if s):
        raise ValueError("Material stage mask differs from reference strings")
    colors = tuple(struct.unpack("<4f",p) for p in parts[3:6])
    if not all(math.isfinite(v) for row in colors for v in row):
        raise ValueError("Nonfinite material color")
    # Existing reader must agree with independently checked part layout.
    parsed = parse_material(bundle,resource)
    if (tuple(parsed["stages"]) != stages or parsed["stage_mask"] != mask or
            parsed["source"] != source or tuple(map(tuple,parsed["colors"])) != colors):
        raise ValueError("Material readers disagree")
    return MaterialLayout(parts,stages,mask,colors)


def _compatibility(layout):
    t = layout.texture
    return (t.fmt,t.width,t.height,t.usage,t.detail,len(t.mipmaps))


def _new_binding(layout, name):
    data = name.encode("ascii")+b"\0"
    if len(data) > 4096 or not layout.stages[0]:
        raise ValueError("Material must already have an active diffuse reference")
    parts = list(layout.parts)
    parts[22:24] = [struct.pack("<I",len(data)),data]
    if parts == list(layout.parts):
        raise ValueError("Diffuse reference would not change")
    return parts


def retarget_diffuse(raw, material_name, target_name):
    bundle = verify_bundle(raw)
    material = select_material(bundle,material_name)
    layout = inspect_material(bundle,material)
    source = inspect_layout(bundle,select_texture(bundle,layout.stages[0]))
    target_resource = select_texture(bundle,target_name)
    target = inspect_layout(bundle,target_resource)
    if _compatibility(source) != _compatibility(target):
        raise ValueError("Replacement texture differs in format, dimensions, usage or mip layout")
    parts = _new_binding(layout,target_resource.name)
    candidate = rebuild_canonical(raw,{material.index:parts})
    result = verify_bundle(candidate)
    after = inspect_material(result,select_material(result,material_name))
    if after.parts != tuple(parts) or after.stages[0] != target_resource.name:
        raise ValueError("Reparsed material binding differs from edit")
    return candidate


def clone_and_bind(raw, material_name, new_name, *, palette=None):
    """Append one texture copied from the material's existing diffuse resource.

    Preserve original indices/order and all original resource payloads except
    the selected material's two diffuse-string parts. The new record's name
    field is reconstructed only if the template has an entirely zero tail.
    """
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,95}",new_name):
        raise ValueError("New texture name must be 1-96 safe ASCII characters")
    bundle = verify_bundle(raw)
    if any(r.name.casefold() == new_name.casefold() for r in bundle.resources):
        raise ValueError("New resource name already exists in archive")
    material = select_material(bundle,material_name)
    mat = inspect_material(bundle,material)
    if not mat.stages[0]:
        raise ValueError("Material has no active diffuse reference")
    texture = select_texture(bundle,mat.stages[0])
    layout = inspect_layout(bundle,texture)
    # Require canonical source before changing resource count or table geometry.
    rebuild_canonical(raw)
    original_rows = _parts(raw,bundle)
    rows = list(original_rows)
    edited_mat = _new_binding(mat,new_name)
    rows[material.index] = edited_mat
    clone = list(layout.parts)
    if palette is not None:
        for slot,data in zip(layout.pixel_slots,marker_mips(layout,palette)):
            clone[slot] = data
    rows.append(clone)
    records = [raw[HEADER_SIZE+i*ENTRY_SIZE:HEADER_SIZE+(i+1)*ENTRY_SIZE]
               for i in range(len(bundle.resources))]
    template = bytearray(records[texture.index])
    old_name = template[NAME_OFFSET:]
    end = old_name.find(b"\0")
    if end < 0 or any(old_name[end+1:]) or old_name[:end].decode("ascii") != texture.name:
        raise ValueError("Texture name field contains unknown nonzero metadata")
    template[NAME_OFFSET:] = new_name.encode("ascii").ljust(ENTRY_SIZE-NAME_OFFSET,b"\0")
    records.append(bytes(template))
    candidate = _build(raw,bundle,rows,record_templates=records)
    after = verify_bundle(candidate)
    if len(after.resources) != len(bundle.resources)+1:
        raise ValueError("Appended resource count mismatch")
    for old,new in zip(bundle.resources,after.resources):
        at = HEADER_SIZE+old.index*ENTRY_SIZE
        if ((new.index,new.name,new.typ,new.first_part,new.part_count) !=
                (old.index,old.name,old.typ,old.first_part,old.part_count) or
                raw[at+40:at+ENTRY_SIZE] != candidate[at+40:at+ENTRY_SIZE]):
            raise ValueError("Existing resource identity changed")
        if list(after.parts(new)) != rows[old.index]:
            raise ValueError("Repacked original resource parts differ from plan")
    appended = after.resources[-1]
    observed = inspect_layout(after,appended)
    if (appended.name != new_name or appended.first_part != bundle.part_count or
            appended.part_count != texture.part_count or observed.parts != tuple(clone) or
            _compatibility(observed) != _compatibility(layout)):
        raise ValueError("Reparsed appended texture differs from plan")
    new_mat = inspect_material(after,after.resources[material.index])
    if new_mat.parts != tuple(edited_mat) or new_mat.stages[0] != new_name:
        raise ValueError("Reparsed material differs from requested binding")
    if select_texture(after,new_mat.stages[0]).index != appended.index:
        raise ValueError("Material does not resolve uniquely to appended texture")
    # Check that the newly built layout is itself canonical.
    rebuild_canonical(candidate)
    return candidate


def restore_clone_trial(candidate, original, material_name, new_name, *, palette=None):
    """Verify an exact reproducible candidate; recover original bytes in memory.

    Not an arbitrary deletion API. The caller must retain the original.
    """
    if clone_and_bind(original,material_name,new_name,palette=palette) != candidate:
        raise ValueError("Candidate does not reproduce from original clone plan")
    return original


def write_candidate(source,output,pin,material,*,target=None,new_name=None,palette=None):
    if not re.fullmatch(r"[0-9a-f]{64}",pin):
        raise ValueError("Expected lowercase source SHA-256")
    if source.is_symlink() or output.is_symlink():
        raise ValueError("Symlink input or output refused")
    source = source.resolve(strict=True)
    output = output.resolve()
    if (source.suffix.lower() != ".ibd" or output.name != source.name or output.exists() or
            output.parent == source.parent or source.parent in output.parents):
        raise ValueError("Output must retain source filename in a new isolated directory")
    original = read_bounded(source)
    if sha256(original) != pin:
        raise ValueError("Source SHA-256 mismatch")
    if (target is None) == (new_name is None) or (palette is not None and target is not None):
        raise ValueError("Choose an existing target or a new clone name")
    candidate = (retarget_diffuse(original,material,target) if target is not None else
                 clone_and_bind(original,material,new_name,palette=palette))
    if sha256(read_bounded(source)) != pin:
        raise ValueError("Source changed during preparation")
    output.parent.mkdir(parents=True,exist_ok=True)
    created = False
    try:
        with output.open("xb") as stream:
            created = True
            stream.write(candidate)
        actual = read_bounded(output)
        if actual != candidate or sha256(read_bounded(source)) != pin:
            raise ValueError("Candidate or source changed")
        verified = verify_bundle(actual)
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {"schema":"DX2-MaterialTextureCandidate-v1","material":material,
            "source_sha256":pin,"candidate_sha256":sha256(candidate),
            "original_bytes":len(original),"candidate_bytes":len(candidate),
            "candidate_resource_count":len(verified.resources),
            "new_texture":new_name,"existing_target":target,
            "runtime_verified":False,"source_modified":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command",required=True)
    inspect = subs.add_parser("inspect")
    inspect.add_argument("source",type=Path)
    inspect.add_argument("--material",required=True)
    for command in ("retarget-diffuse","clone-and-bind"):
        edit = subs.add_parser(command)
        edit.add_argument("source",type=Path)
        edit.add_argument("--material",required=True)
        edit.add_argument("--source-sha256",required=True)
        edit.add_argument("--output",required=True,type=Path)
        if command == "retarget-diffuse":
            edit.add_argument("--target",required=True)
        else:
            edit.add_argument("--new-name",required=True)
            edit.add_argument("--palette",choices=PALETTES)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            raw = read_bounded(args.source)
            bundle = verify_bundle(raw)
            layout = inspect_material(bundle,select_material(bundle,args.material))
            report = {"source_sha256":sha256(raw),"material":args.material,
                      "stage_mask":layout.mask,"stages":layout.stages,
                      "runtime_verified":False}
        else:
            report = write_candidate(args.source,args.output,args.source_sha256,args.material,
                target=getattr(args,"target",None),new_name=getattr(args,"new_name",None),
                palette=getattr(args,"palette",None))
        print(json.dumps(report,indent=2,sort_keys=True))
        return 0
    except (OSError,ValueError,IndexError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
