#!/usr/bin/env python3
"""Read-only DX2 native Model bounds/sphere and byte-50 length-correlation audit.

All offsets are **source-observed**, not an Unreal/Flesh serializer writer.
No BSP, collision, CSG, Havok or map mutation is implemented.
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

SDK_ROOT = Path(__file__).resolve().parents[2]
EXPORTER = SDK_ROOT / "map_exporter"
if str(EXPORTER) not in sys.path:
    sys.path.insert(0, str(EXPORTER))
from dx2inspect import Package

SCHEMA = "DX2SDK-native-model-header-length-observations-v1"
DX2_LICENSEES = (65, 67, 68, 69)
MAX_MAP_BYTES = 250 * 1024 * 1024
MAX_MAPS = 32
MIN_HEADER_BYTES = 51
BOX_OFFSET = 9
BOX_VALID_OFFSET = 33
SPHERE_OFFSET = 34
COUNT_OFFSET = 50
PREDICTED_BASE_BYTES = 63
OBSERVED_BYTES_PER_COUNT = 109


def _all_finite(values) -> bool:
    return all(math.isfinite(v) for v in values)


def inspect_model(payload: bytes) -> dict:
    """Inspect validated header, preserving anomalies instead of "fixing" them.

    The byte at offset 50 correlates strongly with serialized payload length;
    its exact native field name/meaning is not yet confirmed.
    """
    row = {"payload_bytes": len(payload), "header_recognized": False}
    if len(payload) < MIN_HEADER_BYTES or payload[:BOX_OFFSET] != b"\0" * BOX_OFFSET:
        row["reason"] = "short_payload_or_nonzero_nine_byte_prefix"
        return row
    bbox = struct.unpack_from("<6f", payload, BOX_OFFSET)
    lo, hi = bbox[:3], bbox[3:]
    valid = payload[BOX_VALID_OFFSET]
    center = struct.unpack_from("<3f", payload, SPHERE_OFFSET)
    radius = struct.unpack_from("<f", payload, SPHERE_OFFSET + 12)[0]
    count = payload[COUNT_OFFSET]
    row.update({
        "header_recognized": True,
        "box_valid_byte": valid,
        "bbox_min": list(lo),
        "bbox_max": list(hi),
        "sphere_center": list(center),
        "sphere_radius": radius,
        "observed_count_byte_at_50": count,
        "length_formula_expected": PREDICTED_BASE_BYTES + OBSERVED_BYTES_PER_COUNT * count,
        "length_formula_delta": len(payload) - (PREDICTED_BASE_BYTES + OBSERVED_BYTES_PER_COUNT * count),
        "length_formula_exact": len(payload) == PREDICTED_BASE_BYTES + OBSERVED_BYTES_PER_COUNT * count,
        "remaining_native_model_bytes_after_header": len(payload) - MIN_HEADER_BYTES,
    })
    row["bbox_finite_ordered"] = (_all_finite(bbox) and
                                  all(a <= b for a, b in zip(lo, hi)))
    row["sphere_finite_nonnegative"] = _all_finite((*center, radius)) and radius >= 0.0
    if valid not in (0, 1):
        row["reason"] = "unexpected_box_valid_byte"
        return row
    if not row["bbox_finite_ordered"] or not row["sphere_finite_nonnegative"]:
        row["reason"] = "nonfinite_or_unordered_bounds_or_sphere"
        return row
    if valid == 0:
        row["box_state"] = "marked_invalid"
        row["empty_zero_box_and_sphere"] = all(v == 0.0 for v in (*bbox, *center, radius))
        # A large invalid-box Model remains unclassified, not proven world BSP.
        return row
    row["box_state"] = "marked_valid"
    midpoint = [(a + b) * 0.5 for a, b in zip(lo, hi)]
    center_diff = max(abs(a - b) for a, b in zip(midpoint, center))
    center_tol = max(0.001, 2e-6 * max(abs(x) for x in (*midpoint, *center)))
    row["center_midpoint_max_absolute_error"] = center_diff
    row["center_matches_bbox_midpoint"] = center_diff <= center_tol
    half_diagonal = math.sqrt(sum(((b - a) * 0.5) ** 2 for a, b in zip(lo, hi)))
    expected = half_diagonal * 1.001
    row["observed_radius_1p001_halfdiagonal"] = expected
    row["radius_minus_1p001_halfdiagonal"] = radius - expected
    # Empirical tolerance from actual retail float32 serialization, not a
    # statement that a radius must be derived this way by the runtime.
    row["radius_matches_1p001_halfdiagonal"] = (
        abs(radius - expected) <= max(0.002, expected * 1e-5)
    )
    return row


def audit_map(path: Path, *, include_rows: bool = True) -> dict:
    path = Path(path)
    if path.suffix.lower() != ".gmp" or not path.is_file():
        raise ValueError("Expected an existing user-owned DX2 .gmp file")
    if path.stat().st_size > MAX_MAP_BYTES:
        raise ValueError("Map exceeds research input size limit")
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in DX2_LICENSEES:
        raise ValueError("Input is not a source-observed UE95 DX2 licensee 65/67/68/69 map")
    models = [exp for exp in pkg.exports if pkg.class_name(exp) == "Model"]
    if not models:
        raise ValueError("Map has no Model exports")
    count = Counter()
    lengths = Counter()
    values = Counter()
    anomalies = []
    rows = []
    for exp in models:
        record = inspect_model(pkg.payload(exp))
        row = {"export": exp["index"], "name": exp["name"], **record}
        if include_rows:
            rows.append(row)
        lengths[str(record["payload_bytes"])] += 1
        if not record["header_recognized"]:
            count["unrecognized_header"] += 1
            anomalies.append({"export": exp["index"], "name": exp["name"],
                              "reason": record["reason"]})
            continue
        count["header_recognized"] += 1
        values[str(record["box_valid_byte"])] += 1
        if record["box_valid_byte"] == 1:
            count["valid_box_flag"] += 1
            for k in ("center_matches_bbox_midpoint", "radius_matches_1p001_halfdiagonal",
                      "length_formula_exact"):
                if record.get(k) is True:
                    count[k] += 1
            fail = [k for k in ("bbox_finite_ordered", "sphere_finite_nonnegative",
                                "center_matches_bbox_midpoint", "radius_matches_1p001_halfdiagonal",
                                "length_formula_exact") if record.get(k) is not True]
            if fail:
                anomalies.append({"export": exp["index"], "name": exp["name"],
                                  "reason": "valid_model_header_deviation",
                                  "failed_observations": fail,
                                  "payload_bytes": record["payload_bytes"],
                                  "byte_50": record["observed_count_byte_at_50"],
                                  "length_formula_delta": record["length_formula_delta"]})
        elif record["box_valid_byte"] == 0:
            count["invalid_box_flag"] += 1
            if not record["empty_zero_box_and_sphere"]:
                anomalies.append({"export": exp["index"], "name": exp["name"],
                                  "reason": "invalid_box_with_nonzero_header"})
            if record["payload_bytes"] > 4096:
                count["large_invalid_box_candidates"] += 1
        else:
            count["unexpected_box_flag"] += 1
            anomalies.append({"export": exp["index"], "name": exp["name"],
                              "reason": "unexpected_box_valid_byte"})
    return {
        "source": {"file": path.name, "sha256": hashlib.sha256(pkg.data).hexdigest(),
                   "bytes": len(pkg.data), "unreal_version": pkg.version,
                   "licensee": pkg.licensee, "model_exports": len(models)},
        "summary": {**dict(count), "length_histogram": dict(sorted(lengths.items(), key=lambda x: int(x[0]))),
                    "box_validity_values": dict(sorted(values.items()))},
        "anomalies": anomalies,
        **({"models": rows} if include_rows else {}),
    }


def audit_maps(paths, *, include_rows=True) -> dict:
    if not paths or len(paths) > MAX_MAPS:
        raise ValueError("Provide between 1 and 32 map files")
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Do not pass duplicate input files")
    reports = [audit_map(p, include_rows=include_rows) for p in resolved]
    aggregate = Counter()
    licenses = Counter()
    for item in reports:
        licenses[str(item["source"]["licensee"])] += 1
        aggregate["models"] += item["source"]["model_exports"]
        for k, v in item["summary"].items():
            if isinstance(v, int):
                aggregate[k] += v
        aggregate["anomalies"] += len(item["anomalies"])
    return {
        "schema": SCHEMA, "read_only": True, "native_gmp_written": False,
        "bsp_or_collision_decoded": False, "runtime_verified": False,
        "maps_scanned": len(reports),
        "aggregate": {**dict(aggregate), "map_licensees": dict(sorted(licenses.items()))},
        "observed_layout": {
            "prefix": "nine zero bytes at offset 0",
            "box_min_max_f32_le": "offset 9, six float32",
            "box_valid_byte": "offset 33",
            "sphere_center_f32_le": "offset 34, three float32",
            "sphere_radius_f32_le": "offset 46",
            "correlated_count_byte": "offset 50, not an authenticated native field name",
            "length_hypothesis_for_nonempty_models": "63 + 109 * byte[50]",
        },
        "limits": [
            "Header interpreted from the retail byte patterns and Thief 3 FBox reference, not DX2 source code.",
            "Radius relation and length rule are statistical observations with exceptions, not required game invariants.",
            "Large Model exports with invalid-box flags are world-model candidates, not proven BSP ownership.",
            "The payload after offset 50 remains structurally unparsed; surface and collision data not established.",
            "No game files are modified or executed; no DX2 map writer is implemented.",
        ],
        "maps": reports,
    }


def write_report(document: dict, output: Path, sources) -> None:
    output = Path(output).resolve()
    paths = [Path(p).resolve() for p in sources]
    if output.suffix.lower() != ".json":
        raise ValueError("Report must have .json extension")
    if any(output == source or output.is_relative_to(source.parent) for source in paths):
        raise ValueError("Write reports outside original map directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf8") as fp:
        json.dump(document, fp, indent=2, allow_nan=False)
        fp.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path, help="One or more original DX2 GMPs")
    parser.add_argument("--report", type=Path, help="New JSON path outside input directories")
    parser.add_argument("--summary-only", action="store_true", help="Omit per-Model rows")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps, include_rows=not args.summary_only)
        if args.report:
            write_report(report, args.report, args.maps)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "aggregate": report["aggregate"]}, indent=2))
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, struct.error, OverflowError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
