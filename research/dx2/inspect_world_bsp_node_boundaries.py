#!/usr/bin/env python3
"""Read-only DX2 compiled-world Model BSP *node boundary* and zone-table audit.

Observed in UE95 licensee 65/67/68/69 DX2 maps. Field names and topology
beyond the source-checked plane, mask-length and trailing integer patterns
remain provisional. Never writes map packages or collision data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import inspect_level_world_model as world

SCHEMA = "DX2SDK-native-world-BSP-node-boundaries-v1"
PLANE_BYTES = 16
MASK_BYTES = 32
OBSERVED_RECORD_LENGTHS = tuple(range(109, 117))
ZONE_RECORD_BYTES = 69
ZONE_TRAILER_BYTES = 8
MAX_NODES = 20000
MAX_ZONES = 512


def _plane_at(data: bytes, offset: int) -> bool:
    if offset < 0 or offset + PLANE_BYTES + MASK_BYTES > len(data):
        return False
    coeff = struct.unpack_from("<4f", data, offset)
    if not all(math.isfinite(v) and abs(v) < 1_000_000 for v in coeff):
        return False
    # A shifted u32 object index may decode as a denormal float which looks
    # like zero numerically. Reject this accidental 'normal' match.
    if any(0 < abs(v) < 1e-15 for v in coeff[:3]):
        return False
    squared = sum(v*v for v in coeff[:3])
    return abs(squared - 1.0) < 2e-4


def _candidate_end(data: bytes, start: int, size: int, ordinal: int,
                   count: int) -> dict | None:
    end = start + size
    if end > len(data):
        return None
    # Last 16 bytes: two source-observed bounded i32 values, one zero u32,
    # and one opaque u32. Do NOT call the i32 fields node 'children': node 0
    # often has -1/-1 yet the map has many nodes.
    first_ref, second_ref, zero_word, last_word = struct.unpack_from(
        "<iiII", data, end-16)
    if zero_word != 0 or not (-1 <= first_ref < count and -1 <= second_ref < count):
        return None
    zone_count = None
    if ordinal < count-1:
        if not _plane_at(data, end):
            return None
    else:
        # The final node has no following plane. Use independent table shape
        # rather than accepting a lucky run of zeros within a later section.
        if (first_ref, second_ref) != (-1, -1) or end + 4 > len(data):
            return None
        zone_count = struct.unpack_from("<I", data, end)[0]
        if not 1 <= zone_count <= MAX_ZONES:
            return None
        if len(data) - end != 4 + zone_count*ZONE_RECORD_BYTES + ZONE_TRAILER_BYTES:
            return None
        if data[-ZONE_TRAILER_BYTES:] != bytes(ZONE_TRAILER_BYTES):
            return None
    return {
        "next_offset": end, "record_bytes": size,
        "suffix_int32_0": first_ref, "suffix_int32_1": second_ref,
        "opaque_last_u32": last_word, "next_zone_count": zone_count,
    }


def parse_world_model(payload: bytes, *, include_nodes: bool = False) -> dict:
    if not isinstance(payload, bytes) or len(payload) < 100:
        raise ValueError("World Model payload too short or wrong type")
    if payload[:9] != bytes(9) or payload[33] != 0:
        raise ValueError("World Model lacks source-observed empty-bound header")
    # For these source samples, the empty bounds/sphere are exactly zero.
    if payload[9:33] != bytes(24) or payload[34:50] != bytes(16):
        raise ValueError("World Model has unexpected nonzero empty bounds/sphere")
    cursor = world.Cursor(payload, 50)
    count = cursor.ci()
    start = cursor.at
    if not 0 < count <= MAX_NODES:
        raise ValueError("World Model compact candidate node count unsupported")
    records = []
    length_histogram = Counter()
    suffix_histogram = Counter()
    mask_nonzero_records = 0
    offset = start
    opaque_last_u32_max = 0
    for ordinal in range(count):
        if not _plane_at(payload, offset):
            raise ValueError(f"Bad candidate plane at node {ordinal} offset {offset}")
        candidates = []
        for size in OBSERVED_RECORD_LENGTHS:
            match = _candidate_end(payload, offset, size, ordinal, count)
            if match is not None:
                candidates.append(match)
        if len(candidates) != 1:
            raise ValueError(
                f"Ambiguous/unrecognized node boundary at {ordinal} offset {offset}: "
                f"{len(candidates)} candidate lengths")
        found = candidates[0]
        length_histogram[str(found["record_bytes"])] += 1
        a, b = found["suffix_int32_0"], found["suffix_int32_1"]
        suffix_histogram[("none" if a == -1 else "ref") + "/" +
                         ("none" if b == -1 else "ref")] += 1
        opaque_last_u32_max = max(opaque_last_u32_max, found["opaque_last_u32"])
        zone_mask = payload[offset+PLANE_BYTES:offset+PLANE_BYTES+MASK_BYTES]
        mask_nonzero_records += int(any(zone_mask))
        if include_nodes:
            plane = struct.unpack_from("<4f", payload, offset)
            records.append({
                "ordinal": ordinal, "start": offset,
                "length": found["record_bytes"],
                "candidate_plane_xyzw": list(plane),
                "candidate_zone_mask_nonzero_bytes": sum(x != 0 for x in zone_mask),
                "suffix_int32_0": a, "suffix_int32_1": b,
                "opaque_last_u32": found["opaque_last_u32"],
            })
        offset = found["next_offset"]
    zone_count = struct.unpack_from("<I", payload, offset)[0]
    zone_start = offset + 4
    # These 69-byte entries are still opaque, despite matching every sample.
    entries = payload[zone_start:zone_start + ZONE_RECORD_BYTES * zone_count]
    if (len(entries) != zone_count * ZONE_RECORD_BYTES or
            zone_start + len(entries) + ZONE_TRAILER_BYTES != len(payload)):
        raise ValueError("Candidate zone-table extent mismatch")
    return {
        "status": "observed_node_and_zone_array_boundaries",
        "candidate_node_count": count,
        "candidate_node_count_width": start-50,
        "node_array_start": start,
        "node_array_end": offset,
        "node_array_bytes": offset-start,
        "node_record_lengths": dict(sorted(length_histogram.items(), key=lambda v:int(v[0]))),
        "suffix_pair_kinds": dict(sorted(suffix_histogram.items())),
        "nodes_with_nonzero_32byte_mask": mask_nonzero_records,
        "max_opaque_node_suffix_u32": opaque_last_u32_max,
        "candidate_zone_count": zone_count,
        "zone_count_offset": offset,
        "candidate_zone_array_start": zone_start,
        "zone_entry_bytes": ZONE_RECORD_BYTES,
        "candidate_zone_array_bytes": len(entries),
        "trailing_zero_bytes": ZONE_TRAILER_BYTES,
        "everything_in_model_payload_accounted_for": True,
        **({"node_records": records} if include_nodes else {}),
    }


def audit_map(path: Path, *, include_nodes: bool = False) -> dict:
    path = Path(path)
    if path.suffix.casefold() != ".gmp" or not path.is_file():
        raise ValueError("Expected original user-owned DX2 GMP")
    if path.stat().st_size > world.MAX_MAP_BYTES:
        raise ValueError("Map exceeds research size limit")
    pkg = world.Package(path)
    if pkg.version != 95 or pkg.licensee not in world.OBSERVED_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    level = world._parse_world_model(pkg)
    exp = pkg.exports[level["world_model_export_ref"] - 1]
    if pkg.class_name(exp) != "Model":
        raise ValueError("Direct Level ref is not a Model export")
    payload = pkg.payload(exp)
    result = parse_world_model(payload, include_nodes=include_nodes)
    return {
        "file": path.name, "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
        "licensee": pkg.licensee, "world_model_export_ref": exp["index"],
        "world_model_name": exp["name"],
        "world_model_sha256": hashlib.sha256(payload).hexdigest(),
        "world_model_bytes": len(payload),
        **result,
    }


def audit_maps(paths, *, include_nodes: bool = False) -> dict:
    if not 1 <= len(paths) <= world.MAX_MAPS:
        raise ValueError("Supply 1 to 64 source maps")
    inputs = [Path(path).resolve() for path in paths]
    if len(set(inputs)) != len(inputs):
        raise ValueError("Duplicate GMP input")
    rows = [audit_map(path, include_nodes=include_nodes) for path in inputs]
    hist = Counter()
    links = Counter()
    counts = Counter()
    for row in rows:
        hist.update(row["node_record_lengths"])
        links.update(row["suffix_pair_kinds"])
        counts["maps"] += 1
        counts["nodes"] += row["candidate_node_count"]
        counts["candidate_zone_records"] += row["candidate_zone_count"]
        counts["node_mask_nonzero"] += row["nodes_with_nonzero_32byte_mask"]
        counts["licensee_"+str(row["licensee"])] += 1
    return {
        "schema": SCHEMA, "read_only": True,
        "new_native_map_written": False, "native_bsp_node_semantics_complete": False,
        "collision_or_havok_decoded": False, "dx2_runtime_verified": False,
        "summary": dict(counts),
        "all_node_record_length_histogram": dict(sorted(hist.items(),key=lambda v:int(v[0]))),
        "all_suffix_pair_kinds": dict(sorted(links.items())),
        "maps": rows,
        "limits": [
            "The 109..116 byte record widths are only the observed source corpus.",
            "The first 16 bytes are candidate planes; the next 32 bytes are mask-like.",
            "Trailing i32 pairs are bounded refs, NOT confirmed BSP child links.",
            "The 69-byte entries after node records are candidate zone data, fields unknown.",
            "No node topology, zone meaning, render-block index, BSP writer or collision semantics confirmed.",
            "No map files or original resources are modified or distributed.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-nodes", action="store_true",
                        help="Include per-node offsets and observed metadata in JSON")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps, include_nodes=args.include_nodes)
        if args.report:
            world.write_report(report, args.report, args.maps)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "summary": report["summary"]}, indent=2))
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, IndexError, struct.error) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
