#!/usr/bin/env python3
"""Guarded DDS import and visible diagnostic recoloring of existing DX2 textures.

Only existing 2D texture pixel parts change. Dimensions, format, mip count,
usage, prefixes and all other resource bytes remain identical. Legacy DDS
without DX10 extension only; no image compression, texture creation or resizing.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from dx2_ibd_integrity import read_bounded, verify_bundle, replace_same_size, sha256

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "map_exporter"))
from dx2textures import parse_texture, mip_size, to_dds  # noqa: E402

PALETTES = {"magenta": (255, 0, 255), "cyan": (0, 255, 255)}
MAX_TEXTURE_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class TextureLayout:
    texture: object
    parts: tuple
    pixel_slots: tuple


def select_texture(bundle, name):
    matches = [r for r in bundle.resources if r.typ == 8 and r.name.casefold() == name.casefold()]
    if len(matches) != 1:
        raise ValueError("Expected exactly one existing texture with that name")
    return matches[0]


def inspect_layout(bundle, resource):
    if resource.typ != 8 or resource.size > MAX_TEXTURE_BYTES:
        raise ValueError("Unsupported texture resource")
    parts = tuple(bundle.parts(resource))
    if (len(parts) < 18 or len(parts[0]) != 1 or parts[0] != b"\x01"
            or any(len(p) != 4 for p in parts[1:10])
            or any(len(p) != 1 for p in parts[10:12])):
        raise ValueError("Unrecognized texture metadata layout")
    nm, usage, detail, w, h, w2, h2, total = struct.unpack("<8I", b"".join(parts[2:10]))
    if not (1 <= nm <= 16 and 1 <= w <= 8192 and 1 <= h <= 8192):
        raise ValueError("Invalid texture dimensions or mip count")
    if usage == 6 or (w2, h2) != (w, h):
        raise ValueError("Only ordinary 2D textures with matching dimensions supported")
    if len(parts) != 12 + 6 * nm:
        raise ValueError("Unexpected texture part count")
    code = parts[1]
    fmt = {b"DXT1": "DXT1", b"DXT3": "DXT3", b"DXT5": "DXT5",
           b"\x15\0\0\0": "BGRA8", b"\x16\0\0\0": "BGRX8"}.get(code)
    if fmt is None:
        raise ValueError("Unsupported pixel format")
    slots = []
    for i in range(nm):
        at = 12 + 6*i
        if any(len(p) != 4 for p in parts[at:at+4]) or len(parts[at+4]) > 128:
            raise ValueError("Invalid texture mip metadata")
        level, mw, mh, size = struct.unpack("<4I", b"".join(parts[at:at+4]))
        if (level, mw, mh) != (i, max(1, w>>i), max(1, h>>i)):
            raise ValueError("Invalid texture mip dimensions")
        if size != mip_size(fmt, mw, mh) or size != len(parts[at+5]):
            raise ValueError("Invalid texture mip payload extent")
        slots.append(at+5)
    if total != sum(len(parts[i]) for i in slots):
        raise ValueError("Texture total mip bytes mismatch")
    # Independent existing reader must agree on every extracted mip.
    texture = parse_texture(bundle, resource)
    if (texture.faces is not None or texture.fmt != fmt or
            (texture.width, texture.height, texture.usage, texture.detail) != (w,h,usage,detail) or
            [data for _,_,data in texture.mipmaps] != [parts[i] for i in slots]):
        raise ValueError("Texture readers disagree")
    return TextureLayout(texture, parts, tuple(slots))


def decode_dds_for_texture(dds, layout):
    """Accept tightly packed legacy 2D DDS, exact original pixel format/shape."""
    tex = layout.texture
    if len(dds) < 128 or len(dds) > MAX_TEXTURE_BYTES or dds[:4] != b"DDS ":
        raise ValueError("Invalid legacy DDS")
    size, flags, h, w, pitch, depth, count = struct.unpack_from("<7I", dds, 4)
    if (size != 124 or flags & 0x1007 != 0x1007 or flags & ~0xA100F
            or depth not in (0,1) or (w,h) != (tex.width,tex.height)):
        raise ValueError("DDS header or dimensions differ from original texture")
    count = count if flags & 0x20000 else (count or 1)
    if count != len(tex.mipmaps) or (count > 1 and not flags & 0x20000):
        raise ValueError("DDS must include every original mip level")
    pf_size, pf_flags, fourcc, bits, rm, gm, bm, am = struct.unpack_from("<II4sIIIII",dds,76)
    caps, caps2, caps3, caps4, reserved = struct.unpack_from("<5I",dds,108)
    if (pf_size != 32 or caps & 0x1000 != 0x1000 or caps & ~0x401008
            or any((caps2,caps3,caps4,reserved)) or
            (count > 1 and caps & 0x400008 != 0x400008)):
        raise ValueError("DDS cubemaps, volumes, arrays or unsupported caps refused")
    if tex.fmt in ("DXT1","DXT3","DXT5"):
        if (pf_flags != 4 or fourcc != tex.fmt.encode("ascii") or
                any((bits,rm,gm,bm,am)) or not flags & 0x80000 or flags & 8
                or pitch != len(tex.mipmaps[0][2])):
            raise ValueError("DDS compressed format or linear size differs from original")
    else:
        alpha = tex.fmt == "BGRA8"
        if ((pf_flags,fourcc,bits,rm,gm,bm,am) !=
            (0x40 | int(alpha),b"\0"*4,32,0xff0000,0xff00,0xff,0xff000000 if alpha else 0)
                or not flags & 8 or flags & 0x80000 or pitch != w*4):
            raise ValueError("DDS must have exact original 32-bit masks and tight row pitch")
    pos = 128
    mips = []
    for mw,mh,_ in tex.mipmaps:
        n = mip_size(tex.fmt,mw,mh)
        if pos+n > len(dds):
            raise ValueError("DDS mip payload truncated")
        mips.append(dds[pos:pos+n])
        pos += n
    if pos != len(dds):
        raise ValueError("Unexpected extra DDS payload")
    return tuple(mips)


def marker_mips(layout, palette):
    """Recolor all mips, retaining original per-pixel alpha and BC1 mode."""
    if palette not in PALETTES:
        raise ValueError("Unknown diagnostic palette")
    red,green,blue = PALETTES[palette]
    rgb565 = (red>>3)<<11 | (green>>2)<<5 | (blue>>3)
    out = []
    for _,_,raw in layout.texture.mipmaps:
        data = bytearray(raw)
        fmt = layout.texture.fmt
        if fmt in ("BGRA8","BGRX8"):
            for pos in range(0,len(data),4):
                data[pos:pos+3] = bytes((blue,green,red))
        else:
            stride = 8 if fmt == "DXT1" else 16
            for pos in range(0,len(data),stride):
                at = pos + stride - 8
                a,b = struct.unpack_from("<HH",data,at)
                # BC1 transparent index 3 remains transparent when a<=b.
                # Four-color BC1 retains a>b. BC2/3 alpha block is untouched.
                c1 = rgb565-1 if fmt == "DXT1" and a>b else rgb565
                struct.pack_into("<HH",data,at,rgb565,c1)
        out.append(bytes(data))
    return tuple(out)


def replace_mips(raw, name, mips):
    bundle = verify_bundle(raw)
    resource = select_texture(bundle,name)
    layout = inspect_layout(bundle,resource)
    if (len(mips) != len(layout.pixel_slots) or
            any(type(data) is not bytes or len(data) != len(layout.parts[slot])
                for data,slot in zip(mips,layout.pixel_slots))):
        raise ValueError("Replacement mip lengths differ from original")
    parts = list(layout.parts)
    for slot,data in zip(layout.pixel_slots,mips):
        parts[slot] = data
    candidate = replace_same_size(raw,resource.index,b"".join(parts))
    rebuilt = verify_bundle(candidate)
    observed = inspect_layout(rebuilt,select_texture(rebuilt,name))
    if observed.parts != tuple(parts) or observed.pixel_slots != layout.pixel_slots:
        raise ValueError("Reparsed texture differs from requested mip-only change")
    return candidate


def replace_dds(raw,name,dds):
    bundle = verify_bundle(raw)
    layout = inspect_layout(bundle,select_texture(bundle,name))
    return replace_mips(raw,name,decode_dds_for_texture(dds,layout))


def write_candidate(source,output,name,pin,*,dds=None,palette=None):
    if not re.fullmatch(r"[0-9a-f]{64}",pin):
        raise ValueError("Expected lowercase original IBD SHA-256")
    if source.is_symlink() or output.is_symlink():
        raise ValueError("Symlink input or output refused")
    source = source.resolve(strict=True)
    output = output.resolve()
    if (source.suffix.lower() != ".ibd" or output.name != source.name or
            output.parent == source.parent or source.parent in output.parents or output.exists()):
        raise ValueError("Output must retain original filename in a new isolated directory")
    raw = read_bounded(source)
    if sha256(raw) != pin:
        raise ValueError("Source SHA-256 mismatch")
    if (dds is None) == (palette is None):
        raise ValueError("Choose exactly one DDS or diagnostic palette")
    bundle = verify_bundle(raw)
    layout = inspect_layout(bundle,select_texture(bundle,name))
    mips = (decode_dds_for_texture(read_bounded(dds),layout) if dds is not None
            else marker_mips(layout,palette))
    candidate = replace_mips(raw,name,mips)
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
        verify_bundle(actual)
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {"schema":"DX2-TextureMipCandidate-v1","source_sha256":pin,
            "candidate_sha256":sha256(candidate),"texture":name,
            "format":layout.texture.fmt,"width":layout.texture.width,"height":layout.texture.height,
            "mip_count":len(mips),"same_size":True,"runtime_verified":False,
            "source_modified":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command",required=True)
    inspect = subs.add_parser("inspect")
    inspect.add_argument("source",type=Path)
    inspect.add_argument("--name",required=True)
    for command in ("import-dds","marker"):
        edit = subs.add_parser(command)
        edit.add_argument("source",type=Path)
        edit.add_argument("--name",required=True)
        edit.add_argument("--source-sha256",required=True)
        edit.add_argument("--output",type=Path,required=True)
        if command == "import-dds":
            edit.add_argument("--dds",required=True,type=Path)
        else:
            edit.add_argument("--palette",required=True,choices=PALETTES)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            raw = read_bounded(args.source)
            bundle = verify_bundle(raw)
            layout = inspect_layout(bundle,select_texture(bundle,args.name))
            t = layout.texture
            report = {"source_sha256":sha256(raw),"format":t.fmt,"width":t.width,
                      "height":t.height,"mip_count":len(t.mipmaps),"texture":args.name,
                      "runtime_verified":False}
        else:
            report = write_candidate(args.source,args.output,args.name,args.source_sha256,
                                     dds=getattr(args,"dds",None),palette=getattr(args,"palette",None))
        print(json.dumps(report,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,IndexError,struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
