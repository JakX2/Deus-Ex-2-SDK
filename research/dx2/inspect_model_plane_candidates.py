#!/usr/bin/env python3
"""Read-only DX2 Model candidate face-plane scan, not a BSP or CSG decoder.

Observed in source GMPs: for simple nonempty Models of total byte length
63 + 109*n, the n chunks at offset 51 + 109*i begin with 4 float32 values.
All sampled normals were near unit length. The rest of each chunk is opaque.
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

SCHEMA = "DX2SDK-native-model-candidate-face-planes-v1"
PLANE_START = 51
OBSERVED_STRIDE = 109
NORMAL_TOLERANCE = 1e-3


def inspect_planes(payload: bytes) -> dict:
    info = header.inspect_model(payload)
    if not info.get("header_recognized"):
        return {"status": "skip_unrecognized_header", "candidate_plane_count": 0}
    if info["box_valid_byte"] != 1:
        return {"status": "skip_invalid_box_or_unknown_flag", "candidate_plane_count": 0}
    count = info["observed_count_byte_at_50"]
    if count == 0:
        return {"status": "no_candidate_planes", "candidate_plane_count": 0, "planes": []}
    if not info["length_formula_exact"]:
        return {
            "status": "skip_variable_length_case",
            "candidate_plane_count": count,
            "length_delta_from_simple_rule": info["length_formula_delta"],
            "reason": "Record boundaries not established for nonmatching native Model payload",
        }
    if not info["bbox_finite_ordered"]:
        return {"status": "skip_invalid_bounds", "candidate_plane_count": count}
    planes = []
    for i in range(count):
        offset = PLANE_START + OBSERVED_STRIDE * i
        if offset + 16 > len(payload):
            return {"status": "skip_truncated_candidate_plane", "candidate_plane_count": count}
        x, y, z, w = struct.unpack_from("<4f", payload, offset)
        norm_length = math.sqrt(x*x + y*y + z*z)
        finite = all(math.isfinite(v) for v in (x, y, z, w, norm_length))
        unit = finite and abs(norm_length - 1.0) <= NORMAL_TOLERANCE
        planes.append({
            "index": i, "relative_payload_offset": offset,
            "candidate_normal_xyz": [v if math.isfinite(v) else None for v in (x, y, z)],
            "candidate_plane_w": w if math.isfinite(w) else None,
            "normal_length": norm_length if finite else None,
            "unit_normal": unit,
        })
    return {
        "status": "candidate_planes_decoded",
        "candidate_plane_count": count,
        "unit_length_planes": sum(p["unit_normal"] for p in planes),
        "nonunit_or_nonfinite_planes": sum(not p["unit_normal"] for p in planes),
        "planes": planes,
        "limitations": [
            "Four float32 values at each observed 109-byte interval are candidate plane coefficients.",
            "Their ownership, coordinate frame and sign convention have not been established.",
            "Do not interpret the full 109-byte chunk as a fixed-size native polygon record.",
            "Models that break the simple length rule are skipped, not heuristically decoded.",
        ],
    }


def audit_map(path: Path) -> dict:
    path = Path(path)
    if path.suffix.lower() != ".gmp" or not path.is_file():
        raise ValueError("Expected an existing original DX2 .gmp")
    if path.stat().st_size > header.MAX_MAP_BYTES:
        raise ValueError("Map file exceeds research size limit")
    pkg = header.Package(path)
    if pkg.version != 95 or pkg.licensee not in header.DX2_LICENSEES:
        raise ValueError("Expected source-observed UE95 DX2 licensee 65/67/68/69")
    counters = Counter()
    rows = []
    for exp in pkg.exports:
        if pkg.class_name(exp) != "Model":
            continue
        counters["model_exports"] += 1
        result = inspect_planes(pkg.payload(exp))
        status = result["status"]
        counters[status] += 1
        if status == "candidate_planes_decoded":
            counters["planes"] += result["candidate_plane_count"]
            counters["unit_length_planes"] += result["unit_length_planes"]
            counters["nonunit_or_nonfinite_planes"] += result["nonunit_or_nonfinite_planes"]
        if status != "no_candidate_planes":
            rows.append({"model_export": exp["index"], "model_name": exp["name"], **result})
    return {
        "file": path.name, "sha256": hashlib.sha256(pkg.data).hexdigest(),
        "ue_version": pkg.version, "licensee": pkg.licensee,
        "counts": dict(counters), "candidate_models": rows,
    }


def audit_maps(paths) -> dict:
    if not paths or len(paths) > header.MAX_MAPS:
        raise ValueError("Provide 1 to 32 input GMP files")
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate map input paths")
    reports = [audit_map(p) for p in resolved]
    total = Counter()
    for report in reports:
        total.update(report["counts"])
    return {
        "schema": SCHEMA,
        "read_only": True,
        "native_model_polygon_decoder_complete": False,
        "bsp_or_collision_decoded": False,
        "game_runtime_verified": False,
        "record_start_offset": PLANE_START,
        "empirical_record_spacing_bytes": OBSERVED_STRIDE,
        "unit_normal_tolerance": NORMAL_TOLERANCE,
        "total": dict(total),
        "maps": reports,
        "limits": [
            "Candidate first-four-float plane coefficients only; other fields inside 109-byte spans remain opaque.",
            "The 109-byte spacing is an observed layout for matching-length records, not a universal native polygon stride.",
            "One +3-byte model and any future nonconforming records must be skipped until decoded.",
            "Plane coefficients have not been verified in actor/world coordinate frames.",
            "No source packages are modified; cannot compile DX2 BSP or collision.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        document = audit_maps(args.maps)
        if args.report:
            header.write_report(document, args.report, args.maps)
            print(json.dumps({"status":"ok", "report": str(args.report),
                              "total": document["total"]}, indent=2))
        else:
            print(json.dumps(document, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, struct.error, OverflowError) as error:
        print(json.dumps({"status":"error", "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
