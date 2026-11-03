#!/usr/bin/env python3
"""Read-only source-observed DX2 Model face record decoder; not a BSP writer.

Examines 109/110-byte candidate records in UE95 DX2 licensee 65/67/68/69
Model exports. Vertex index slots are NOT decoded vertex XYZ positions.
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

import inspect_model_serialization as header

SCHEMA = "DX2SDK-native-model-face-records-v1"
RECORD_START = 51
RECORD_SIZES = (109, 110)
MAX_FACE_COUNT = 64
MAX_VERTEX_SLOTS = 255


def _candidate(record: bytes, first: int, order: int) -> dict | None:
    length = len(record)
    if length not in RECORD_SIZES:
        return None
    if record[16:48] != bytes(32) or record[48] != 0:
        return None
    if record[-16:-8] != b"\xff" * 8 or record[-8:-4] != bytes(4):
        return None
    if first > MAX_VERTEX_SLOTS or record[49] != first:
        return None
    suffix_first = struct.unpack_from("<I", record, length - 4)[0]
    if suffix_first != first:
        return None
    vertex_count = record[-17]
    if not 3 <= vertex_count <= 16:
        return None
    normal = struct.unpack_from("<3f", record, 0)
    distance = struct.unpack_from("<f", record, 12)[0]
    point = struct.unpack_from("<3f", record, length - 53)
    radius = struct.unpack_from("<f", record, length - 41)[0]
    if not all(map(math.isfinite, (*normal, distance, *point, radius))) or radius < 0:
        return None
    norm_error = abs(math.sqrt(sum(v*v for v in normal)) - 1.0)
    if norm_error > 1e-3:
        return None
    dot_error = abs(sum(n*c for n,c in zip(normal, point)) - distance)
    if dot_error > max(0.01, abs(distance)*2e-5):
        return None
    if record[length - 37:length - 17] != bytes(20):
        return None
    return {
        "face_order": order, "record_bytes": length,
        "vertex_first_byte49": first, "vertex_first_u32_suffix": suffix_first,
        "vertex_slot_count": vertex_count,
        "candidate_normal_xyz": list(normal),
        "candidate_plane_w": distance,
        "candidate_point_on_plane": list(point),
        "candidate_face_radius": radius,
        "plane_dot_point_error": dot_error,
        "normal_length_error": norm_error,
        "unknown_byte50": record[50],
    }


def inspect_model_faces(payload: bytes) -> dict:
    meta = header.inspect_model(payload)
    if not meta.get("header_recognized"):
        return {"status": "unsupported_model_header", "reason": meta.get("reason", "unknown")}
    if meta["box_valid_byte"] != 1 or not meta["bbox_finite_ordered"]:
        return {"status": "skip_invalid_box_model"}
    count = meta["observed_count_byte_at_50"]
    if count == 0:
        return {"status": "no_face_candidates", "candidate_face_count": 0, "faces": []}
    if count > MAX_FACE_COUNT:
        return {"status": "unsupported_large_face_count", "candidate_face_count": count}
    offset = RECORD_START
    first = 0
    rows = []
    for order in range(count):
        matches = []
        for length in RECORD_SIZES:
            record = payload[offset:offset+length]
            if len(record) != length:
                continue
            decoded = _candidate(record, first, order)
            if decoded is not None:
                decoded["record_offset"] = offset
                decoded["point_offset"] = offset + length - 53
                decoded["radius_offset"] = offset + length - 41
                decoded["vertex_count_offset"] = offset + length - 17
                matches.append(decoded)
        if len(matches) != 1:
            return {
                "status": "ambiguous_or_unrecognized_face_boundary",
                "candidate_face_count": count, "first_bad_face": order,
                "byte_offset": offset, "choices_found": len(matches),
            }
        face = matches[0]
        rows.append(face)
        offset += face["record_bytes"]
        first += face["vertex_slot_count"]
        if first > MAX_VERTEX_SLOTS:
            return {"status": "unsupported_vertex_slot_count", "vertex_slots": first}
    if len(payload) - offset != 12:
        return {"status": "unrecognized_model_tail", "tail_bytes": len(payload)-offset}
    return {
        "status": "decoded_candidate_face_records",
        "candidate_face_count": count, "candidate_vertex_slots": first,
        "record_byte_histogram": dict(Counter(str(x["record_bytes"]) for x in rows)),
        "max_plane_dot_point_error": max(r["plane_dot_point_error"] for r in rows),
        "tail_bytes": 12, "faces": rows,
        "limitations": [
            "Vertex counts and starts are NOT reconstructed XYZ vertex coordinates.",
            "Face plane/point/radius interpretations require future independent geometry verification.",
            "Remaining native fields are opaque; no DX2 BSP, CSG, physics or collision decoded.",
            "Ambiguous/unobserved record lengths are refused instead of guessed.",
        ],
    }


def audit_map(path: Path, *, include_faces=False) -> dict:
    path = Path(path)
    if path.suffix.casefold() != ".gmp" or not path.is_file():
        raise ValueError("Expected existing user-owned DX2 .gmp")
    if path.stat().st_size > header.MAX_MAP_BYTES:
        raise ValueError("Map exceeds safe research input size")
    pkg = header.Package(path)
    if pkg.version != 95 or pkg.licensee not in header.DX2_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    stats = Counter()
    models = []
    for exp in pkg.exports:
        if pkg.class_name(exp) != "Model":
            continue
        stats["model_exports"] += 1
        result = inspect_model_faces(pkg.payload(exp))
        stats[result["status"]] += 1
        if result["status"] == "decoded_candidate_face_records":
            stats["face_records"] += result["candidate_face_count"]
            stats["vertex_slots"] += result["candidate_vertex_slots"]
            for size, n in result["record_byte_histogram"].items():
                stats["records_bytes_" + size] += n
        if result["status"] != "no_face_candidates":
            if not include_faces:
                result.pop("faces", None)
            models.append({"model_name": exp["name"], "model_export": exp["index"], **result})
    return {
        "file": path.name, "sha256": hashlib.sha256(pkg.data).hexdigest(),
        "ue_version": pkg.version, "licensee": pkg.licensee,
        "summary": dict(stats), "models": models,
    }


def audit_maps(paths, *, include_faces=False):
    if not paths or len(paths) > header.MAX_MAPS:
        raise ValueError("Provide between 1 and 32 GMP inputs")
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate map input paths")
    reports = [audit_map(p, include_faces=include_faces) for p in resolved]
    totals = Counter()
    for result in reports:
        totals.update(result["summary"])
    return {
        "schema": SCHEMA, "read_only": True, "native_gmp_written": False,
        "vertex_positions_decoded": False, "bsp_or_collision_decoded": False,
        "game_runtime_verified": False, "observed_record_sizes": list(RECORD_SIZES),
        "totals": dict(totals), "maps": reports,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-faces", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit_maps(args.maps, include_faces=args.include_faces)
        if args.report:
            header.write_report(result, args.report, args.maps)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "totals": result["totals"]}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, struct.error, OverflowError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
