#!/usr/bin/env python3
"""Canonical IBD repacking, preserving existing resource identity and part count.

Requires a byte-identical no-op rebuild of the original before changing any
part lengths. Only canonical contiguous, zero-padded originals are accepted.
No validation of resource-specific payload meaning or game runtime behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from dx2bundles import MAGIC, HEADER_SIZE, ENTRY_SIZE
from dx2_ibd_integrity import (
    MAX_BUNDLE_BYTES, read_bounded, verify_bundle, header_digest, sha256,
)


def align_up(size, alignment):
    return ((size + alignment - 1) // alignment) * alignment


def _parts(raw, bundle):
    result = []
    for resource in bundle.resources:
        pos = resource.offset
        row = []
        for length in bundle.part_sizes[
                resource.first_part:resource.first_part + resource.part_count]:
            row.append(memoryview(raw)[pos:pos+length])
            pos += length
        result.append(row)
    return result


def _build(raw, bundle, rows):
    n = len(rows)
    lengths = [len(part) for row in rows for part in row]
    sizes = [sum(map(len, row)) for row in rows]
    if not n or not lengths or any(not size for size in sizes):
        raise ValueError("Empty resource or part table unsupported")
    if any(size > MAX_BUNDLE_BYTES for size in sizes):
        raise ValueError("Oversized resource")
    alignment = bundle.alignment
    start = align_up(HEADER_SIZE + n * ENTRY_SIZE + len(lengths) * 4, alignment)
    extent = sum(align_up(size, alignment) for size in sizes)
    if start + extent > MAX_BUNDLE_BYTES:
        raise ValueError("Repacked IBD exceeds output limit")

    output = bytearray(start + extent)
    struct.pack_into("<8I", output, 0, MAGIC, alignment, start, extent,
                     max(sizes), max(lengths), n, len(lengths))
    part_table = HEADER_SIZE + n * ENTRY_SIZE
    for i, length in enumerate(lengths):
        struct.pack_into("<I", output, part_table + 4*i, length)
    cursor = start
    first = 0
    for index, (row, size) in enumerate(zip(rows, sizes)):
        at = HEADER_SIZE + index * ENTRY_SIZE
        # Retain all unknown record bytes, names, resource type, and ordering.
        output[at:at+ENTRY_SIZE] = raw[at:at+ENTRY_SIZE]
        padded = align_up(size, alignment)
        struct.pack_into("<5I", output, at, cursor, size, padded-size, first, len(row))
        pos = cursor
        for part in row:
            output[pos:pos+len(part)] = part
            pos += len(part)
        digest = hashlib.sha1(memoryview(output)[cursor:cursor+padded]).digest()
        output[at+20:at+40] = digest
        cursor += padded
        first += len(row)
    output[32:52] = header_digest(output, start)
    return bytes(output)


def rebuild_canonical(raw, edits=None):
    """Rebuild existing parts, checking exact original reconstruction first.

    edits maps zero-based resource index to a list/tuple of replacement bytes.
    Resource count and each resource's part count must remain identical.
    """
    bundle = verify_bundle(raw)
    original = _parts(raw, bundle)
    if _build(raw, bundle, original) != raw:
        raise ValueError("Original IBD is not byte-identical under canonical rebuild")
    if edits is None:
        return raw
    if not isinstance(edits, dict) or not edits:
        raise ValueError("Expected a nonempty resource edit mapping")
    rows = list(original)
    for index, parts in edits.items():
        if type(index) is not int or not 0 <= index < len(rows):
            raise ValueError("Resource index outside original table")
        if (not isinstance(parts, (list, tuple)) or len(parts) != len(original[index])
                or any(type(part) is not bytes for part in parts)):
            raise ValueError("Replacement must preserve exact part count and contain bytes")
        rows[index] = parts
    if all(a == b for a, b in zip(original, rows)):
        raise ValueError("Replacement would not change any part")
    candidate = _build(raw, bundle, rows)
    if candidate == raw:
        raise ValueError("Replacement would not change the IBD")
    result = verify_bundle(candidate)
    if len(result.resources) != len(bundle.resources):
        raise ValueError("Resource table count changed")
    for i, (before, after) in enumerate(zip(bundle.resources, result.resources)):
        at = HEADER_SIZE + i * ENTRY_SIZE
        if (after.part_count != before.part_count or
                after.first_part != before.first_part or
                candidate[at+40:at+ENTRY_SIZE] != raw[at+40:at+ENTRY_SIZE]):
            raise ValueError("Resource identity or part count changed")
        observed = list(result.parts(after))
        if len(observed) != len(rows[i]) or any(a != b for a, b in zip(observed, rows[i])):
            raise ValueError("Repacked part bytes differ from plan")
    return candidate


def read_replacement_parts(directory, count):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Parts directory must be an ordinary directory")
    expected = {f"{i:06d}.bin" for i in range(count)}
    if {p.name for p in directory.iterdir()} != expected:
        raise ValueError("Parts directory must contain exactly the numbered original part slots")
    parts = []
    total = 0
    for i in range(count):
        path = directory / f"{i:06d}.bin"
        if path.is_symlink() or not path.is_file():
            raise ValueError("Invalid replacement part")
        size = path.stat().st_size
        total += size
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("Replacement parts exceed limit")
        with path.open("rb") as stream:
            data = stream.read(size+1)
        if len(data) != size:
            raise ValueError("Replacement part changed while reading")
        parts.append(data)
    return parts


def write_repacked(source, output, index, directory, pin):
    if not re.fullmatch(r"[0-9a-f]{64}", pin):
        raise ValueError("Expected lowercase original SHA-256")
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
    bundle = verify_bundle(raw)
    if type(index) is not int or not 0 <= index < len(bundle.resources):
        raise ValueError("Resource index outside original table")
    parts = read_replacement_parts(directory, bundle.resources[index].part_count)
    candidate = rebuild_canonical(raw, {index: parts})
    if sha256(read_bounded(source)) != pin:
        raise ValueError("Source changed during preparation")
    output.parent.mkdir(parents=True, exist_ok=True)
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
    return {"schema":"DX2-IBDCanonicalRepack-v1","status":"isolated-candidate",
            "source_sha256":pin,"candidate_sha256":sha256(candidate),
            "original_bytes":len(raw),"candidate_bytes":len(candidate),
            "resource_index":index,"original_noop_byte_identical":True,
            "runtime_verified":False,"source_modified":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit-rebuild")
    audit.add_argument("source", type=Path)
    repack = sub.add_parser("replace-parts")
    repack.add_argument("source", type=Path)
    repack.add_argument("--index", type=int, required=True)
    repack.add_argument("--parts-dir", type=Path, required=True)
    repack.add_argument("--source-sha256", required=True)
    repack.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit-rebuild":
            raw = read_bounded(args.source)
            rebuild_canonical(raw)
            report = {"schema":"DX2-IBDCanonicalRepack-v1","status":"byte-identical",
                      "original_noop_byte_identical":True,"runtime_verified":False,
                      "source_modified":False}
        else:
            report = write_repacked(args.source, args.output, args.index,
                                   args.parts_dir, args.source_sha256)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
