#!/usr/bin/env python3
"""Coordinated custom DDS import into existing DX2 material instances.

All source ZIPs are pinned. A single new texture name is reserved across the
supplied IBD/MLB corpus, then added to every bundled instance of one uniquely
identified standalone material. The standalone diffuse slot is synchronized
without touching any other bytes. This is an isolated offline candidate, not
a guarantee of runtime registration or a whole-game inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import zipfile

from dx2_ibd_integrity import (
    MAX_BUNDLE_BYTES, MAX_ZIP_BYTES, read_bounded, sha256, verify_bundle,
)
from dx2_material_audit import members, read_mlb, source_key, MAX_MLB_SIZE
from dx2_material_writer import (
    clone_and_bind, reverse_clone_trial, inspect_material, select_material,
)
from dx2_texture_writer import (
    decode_dds_for_texture, inspect_layout, replace_mips, select_texture,
)

SCHEMA = "DX2-CoordinatedCustomDDS-v1"
MAX_SELECTED = 32
MAX_SELECTED_BYTES = 256 * 1024 * 1024
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}


def import_clone(raw, material, new_name, dds):
    """Create a new texture with caller-supplied compatible DDS mip bytes."""
    before = verify_bundle(raw)
    m = inspect_material(before, select_material(before, material))
    original = inspect_layout(before, select_texture(before, m.stages[0]))
    mips = decode_dds_for_texture(dds, original)
    cloned = clone_and_bind(raw, material, new_name)
    # The existing copy may already contain exactly the requested pixels.
    original_mips = tuple(original.parts[i] for i in original.pixel_slots)
    candidate = cloned if mips == original_mips else replace_mips(cloned, new_name, mips)
    after = verify_bundle(candidate)
    new = inspect_layout(after, select_texture(after, new_name))
    if tuple(new.parts[i] for i in new.pixel_slots) != mips:
        raise ValueError("Appended texture pixels do not match requested DDS")
    if inspect_material(after, select_material(after, material)).stages[0] != new_name:
        raise ValueError("Edited diffuse binding does not resolve to new texture")
    # Independently undo the custom pixels and then remove the append/rebind.
    restored_clone = (candidate if mips == original_mips else
                      replace_mips(candidate, new_name, original_mips))
    if restored_clone != cloned:
        raise ValueError("Custom mip reversal differs from ordinary clone")
    restored = reverse_clone_trial(restored_clone, sha256(raw), material,
                                   m.stages[0], new_name)
    if restored != raw:
        raise ValueError("Custom import inverse did not restore original")
    return candidate


def _fixed_name(field):
    n = field.find(b"\0")
    if n < 0:
        raise ValueError("Unterminated standalone material string")
    return field[:n].decode("ascii")


def patch_mlb(raw, material, expected_diffuse, new_name, flags, stage_mask):
    """Change one proven 64-byte standalone diffuse slot, not other stages."""
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", new_name):
        raise ValueError("Synchronized texture name must be 1-63 safe ASCII characters")
    rows = read_mlb(raw)
    matches = [(i, rec) for i, (name, rec) in enumerate(rows)
               if name.casefold() == material.casefold()]
    if len(matches) != 1:
        raise ValueError("Expected one standalone material record")
    i, rec = matches[0]
    field = rec[148:212]
    old = _fixed_name(field)
    if (not expected_diffuse or old != expected_diffuse or
            any(field[len(old)+1:]) or rec[144:148] != flags or
            rec[64:68] != stage_mask):
        raise ValueError("Standalone diffuse, flags, mask or zero-tail check failed")
    if new_name.casefold() == old.casefold():
        raise ValueError("New standalone texture name collides with old name")
    start = 12 + 788*i + 148
    end = start + 64
    replacement = new_name.encode("ascii").ljust(64, b"\0")
    candidate = raw[:start] + replacement + raw[end:]
    after = read_mlb(candidate)
    if (len(after) != len(rows) or after[i][0] != rows[i][0] or
            after[i][1][148:212] != replacement or
            candidate[:start] != raw[:start] or candidate[end:] != raw[end:]):
        raise ValueError("Standalone material reparse failed")
    if candidate[:start] + field + candidate[end:] != raw:
        raise ValueError("Standalone material reversal failed")
    return candidate


def _zip_pin(path, expected):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Expected lowercase source ZIP SHA-256")
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_ZIP_BYTES:
        raise ValueError("Invalid or oversized source ZIP")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("Source ZIP SHA-256 mismatch")


def _check_name(new_name):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", new_name):
        raise ValueError("Synchronized texture name must be 1-63 safe ASCII characters")
    return new_name.casefold()


def _portable_parts(parts):
    """Refuse ambiguous Windows destinations, including NTFS stream names."""
    if not parts or any(
            not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,127}", p)
            or p.endswith((".", " "))
            or p.split(".",1)[0].upper() in WINDOWS_RESERVED
            for p in parts):
        raise ValueError("Unsafe or unsupported portable output path")
    return parts


def _actual_member_names(path):
    with zipfile.ZipFile(path) as archive:
        return {i.filename.replace("\\","/").casefold():i.filename.replace("\\","/")
                for i in archive.infolist() if not i.is_dir()}


def plan(ibd_zip, mlb_zip, ibd_pin, mlb_pin, library, material, new_name, dds):
    """Return candidate bytes in memory, after corpus and correspondence checks.

    library is a full path rooted at MatLib, never a basename-only guess.
    All matching bundled instances in the supplied ZIP are edited together.
    """
    wanted = _check_name(new_name)
    key = source_key(library)
    if key is None or library.replace("\\","/").casefold() != key:
        raise ValueError("Specify a full MatLib-relative library path")
    _zip_pin(ibd_zip, ibd_pin)
    _zip_pin(mlb_zip, mlb_pin)
    originals = _actual_member_names(ibd_zip)
    library_names = _actual_member_names(mlb_zip)
    selected = []
    used_names = set()
    standalone = []
    total_libraries = 0
    total_bundles = 0
    selected_bytes = 0

    for path, raw in members(mlb_zip, ".mlb", MAX_MLB_SIZE):
        total_libraries += 1
        for name, rec in read_mlb(raw):
            if name.casefold() == wanted:
                raise ValueError("New texture name collides with a standalone material")
            # Only the nine established texture slots; unrelated tail is opaque.
            for stage in range(9):
                if _fixed_name(rec[148+64*stage:212+64*stage]).casefold() == wanted:
                    raise ValueError("New texture name already referenced in standalone corpus")
        if source_key(path) == key:
            standalone.append((path,raw))
    if len(standalone) != 1:
        raise ValueError("Expected one standalone library at the requested full path")

    for path, raw in members(ibd_zip, ".ibd", MAX_BUNDLE_BYTES):
        total_bundles += 1
        bundle = verify_bundle(raw)
        for r in bundle.resources:
            if r.name.casefold() == wanted:
                raise ValueError("New texture name already exists in supplied IBD corpus")
            if r.typ != 10:
                continue
            mat = inspect_material(bundle,r)
            if wanted in (s.casefold() for s in mat.stages):
                raise ValueError("New texture name already referenced in bundled corpus")
            if (r.name.casefold() == material.casefold() and
                    source_key(mat.parts[18][:-1].decode("ascii")) == key):
                # Exact unique name in this bundle; prevent editing one of duplicates.
                if select_material(bundle,material).index != r.index:
                    raise ValueError("Ambiguous material instance")
                file_name = PurePosixPath(originals[path]).name
                _portable_parts((file_name,))
                if file_name.casefold() in used_names:
                    raise ValueError("Selected bundles collide by destination filename")
                used_names.add(file_name.casefold())
                selected.append((file_name,raw,r.name,mat))
                selected_bytes += len(raw)
                if len(selected) > MAX_SELECTED or selected_bytes > MAX_SELECTED_BYTES:
                    raise ValueError("Selected instance or byte limit exceeded")
    if not selected:
        raise ValueError("No matching bundled material instances")

    lib_path, lib_raw = standalone[0]
    first = selected[0][3]
    if any((mat.stages[0],mat.parts[1],mat.parts[2]) !=
           (first.stages[0],first.parts[1],first.parts[2]) for _,_,_,mat in selected):
        raise ValueError("Bundled instances disagree on proven standalone fields")
    lib_candidate = patch_mlb(lib_raw,material,first.stages[0],new_name,first.parts[1],first.parts[2])
    # Preserve source path case from archive entry, starting at MatLib.
    lib_parts = PurePosixPath(library_names[lib_path]).parts
    start = next(i for i,p in enumerate(lib_parts) if p.casefold()=="matlib")
    output_lib = "/".join(_portable_parts(lib_parts[start:]))
    outputs = {output_lib: (lib_raw,lib_candidate)}
    output_bytes = len(lib_candidate)
    for file_name, raw, name, _ in selected:
        candidate = import_clone(raw,name,new_name,dds)
        output_bytes += len(candidate)
        if output_bytes > MAX_SELECTED_BYTES:
            raise ValueError("Combined candidate byte limit exceeded")
        outputs["Maps/"+file_name] = (raw,candidate)
    # Refuse stale input even if a ZIP was replaced during processing.
    _zip_pin(ibd_zip,ibd_pin)
    _zip_pin(mlb_zip,mlb_pin)
    receipt = {
        "schema":SCHEMA,"source_ibd_zip_sha256":ibd_pin,"source_mlb_zip_sha256":mlb_pin,
        "dds_sha256":sha256(dds),"material":material,"new_texture":new_name,
        "bundles_scanned":total_bundles,"libraries_scanned":total_libraries,
        "coordinated_bundle_instances":len(selected),
        "files":[{"relative_path":name,"source_sha256":sha256(old),
                  "candidate_sha256":sha256(new),"source_bytes":len(old),
                  "candidate_bytes":len(new)} for name,(old,new) in sorted(outputs.items())],
        "all_selected_candidates_reversed_exactly":True,
        "name_collision_scope":"supplied IBD and MLB ZIPs only",
        "runtime_verified":False,"source_modified":False,
        "game_installation_modified":False,
    }
    return outputs, receipt


def write_trial(ibd_zip,mlb_zip,ibd_pin,mlb_pin,library,material,new_name,dds_path,output):
    if output.is_symlink() or output.exists():
        raise ValueError("Output must be a new isolated directory")
    output = output.resolve()
    if output.exists():
        raise ValueError("Output must be a new isolated directory")
    dds = read_bounded(dds_path)
    outputs,receipt = plan(ibd_zip,mlb_zip,ibd_pin,mlb_pin,library,material,new_name,dds)
    output.mkdir(parents=True,exist_ok=False)
    try:
        for name,(_,data) in outputs.items():
            path=output.joinpath(*PurePosixPath(name).parts)
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
            if sha256(read_bounded(path)) != sha256(data):
                raise ValueError("Candidate disk verification failed")
        with (output/"trial.json").open("x",encoding="utf-8") as stream:
            json.dump(receipt,stream,sort_keys=True,indent=2)
            stream.write("\n")
    except Exception:
        shutil.rmtree(output)
        raise
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ibd-zip",required=True,type=Path)
    parser.add_argument("--mlb-zip",required=True,type=Path)
    parser.add_argument("--ibd-sha256",required=True)
    parser.add_argument("--mlb-sha256",required=True)
    parser.add_argument("--library",required=True)
    parser.add_argument("--material",required=True)
    parser.add_argument("--new-name",required=True)
    parser.add_argument("--dds",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        receipt=write_trial(args.ibd_zip,args.mlb_zip,args.ibd_sha256,args.mlb_sha256,
            args.library,args.material,args.new_name,args.dds,args.output)
        print(json.dumps(receipt,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,IndexError,struct.error,zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
