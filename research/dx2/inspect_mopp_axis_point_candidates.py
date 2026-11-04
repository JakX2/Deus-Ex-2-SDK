#!/usr/bin/env python3
"""Conservative *hypothesis* for point candidates in original DX2 MOPP bytecode.

Uses documented axis tests, f32 source envelope quantization, and rescaling.
Diagonal 0x13..0x1c splits are ALWAYS followed down both branches: their
precise Havok arithmetic is not verified for Deus Ex: Invisible War.

This is a read-only broadphase research experiment, NOT Havok ray casting,
triangle contacts, a physics-material reader, or a native collision writer.
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

import inspect_level_mopp_triangle_tree as mopp

SCHEMA = "DX2SDK-MOPP-conservative-axis-point-candidates-v1"
SOURCE_SCALE_DIVISOR = 65536.0
DEFAULT_TOLERANCE = 1.0  # one quantization unit; EMPIRICALLY chosen, not Havok policy
MAX_QUERY_STATES = 200_000
MAX_MAPS = mopp.flatcheck.MAX_MAPS


def _finite_xyz(value: object, *, label: str) -> tuple[float, float, float]:
    if (not isinstance(value, (tuple, list)) or len(value) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or abs(v) > 1_000_000 for v in value)):
        raise ValueError(f"{label} must contain three finite, bounded XYZ coordinates")
    return tuple(float(v) for v in value)


class ConservativeMoppPointCandidates:
    """Validated source graph + intentionally incomplete axis-only point walker.

    The prior source-observed symbolic tracer validates all opcode lengths and
    branch destinations once. Each query may only prune *axis-aligned* branches.
    An unknown diagonal calculation must never be silently guessed.
    """

    def __init__(self, code: bytes, triangle_count: int,
                 origin_scale: tuple[float, float, float, float]):
        if (not isinstance(code, bytes) or type(triangle_count) is not int
                or not isinstance(origin_scale, (tuple, list))
                or len(origin_scale) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       for v in origin_scale)
                or origin_scale[3] <= 0.0 or origin_scale[3] > 1_000_000_000.0):
            raise ValueError("Invalid original MOPP code or source spatial parameters")
        self.origin = _finite_xyz(origin_scale[:3], label="MOPP source origin")
        self.scale = float(origin_scale[3])
        self.code = code
        self.triangle_count = triangle_count
        self.reference = mopp.trace_mopp_code(code, triangle_count)
        self.complete_leaf_set = frozenset(self.reference[
            "reachable_terminal_triangle_ids"])

    def point(self, xyz: object, *, tolerance_units: float = DEFAULT_TOLERANCE) -> dict:
        """Return conservative candidate triangle IDs for a POINT, not a ray.

        IMPORTANT: the margin is a hypothesis that was tested against retail
        source triangles. Diagonal branches are deliberately explored BOTH.
        The return value is a candidate list, never narrowphase hit results.
        """
        q = _finite_xyz(xyz, label="Probe point")
        if (type(tolerance_units) not in (float, int)
                or not math.isfinite(tolerance_units)
                or not 0 <= tolerance_units <= 4):
            raise ValueError("Tolerance must be a finite 0..4 quantization units")
        margin = float(tolerance_units)
        scaled = tuple((q[i] - self.origin[i]) * self.scale /
                       SOURCE_SCALE_DIVISOR for i in range(3))
        if not all(math.isfinite(c) and abs(c) < 1e15 for c in scaled):
            raise ValueError("Unrepresentable MOPP quantized point")
        todo = [(0, 0, scaled)]
        visited: set[tuple[int, int, tuple[float, float, float]]] = set()
        candidates: set[int] = set()
        counters = Counter()
        code = self.code
        while todo:
            pc, base, coords = todo.pop()
            state = (pc, base, coords)
            if state in visited:
                continue
            if len(visited) >= MAX_QUERY_STATES:
                raise ValueError("Conservative point-query instruction-state safety cap")
            visited.add(state)
            if not 0 <= pc < len(code):
                raise ValueError("Query escaped validated MOPP stream")
            op = code[pc]

            def number(offset: int, width: int) -> int:
                return int.from_bytes(code[offset:offset+width], "big")

            def route(target: int, new_base: int = base,
                      new_coords: tuple[float,float,float] = coords) -> None:
                if (not pc < target < len(code)
                        or not 0 <= new_base <= 0xffffffff
                        or not all(math.isfinite(x) for x in new_coords)):
                    raise ValueError("MOPP spatial query produced invalid next state")
                todo.append((target, new_base, new_coords))

            if 0x01 <= op <= 0x04:
                nxt = tuple((coords[i] - code[pc+1+i])*(1 << op)
                            for i in range(3))
                route(pc+4, new_coords=nxt)
                counters["rescale"] += 1
            elif op == 0x05:
                route(pc+2+code[pc+1])
            elif op == 0x06:
                route(pc+3+number(pc+1, 2))
            elif op == 0x09:
                route(pc+2, new_base=base+code[pc+1])
            elif op == 0x0a:
                route(pc+3, new_base=base+number(pc+1, 2))
            elif op == 0x0b:
                route(pc+5, new_base=number(pc+1, 4))
            elif 0x10 <= op <= 0x1c:
                low, high, delta = code[pc+1:pc+4]
                left, right = pc+4, pc+4+delta
                if op <= 0x12:
                    coordinate = coords[op-0x10]
                    if coordinate < low + margin:
                        route(left)
                    if coordinate >= high - margin:
                        route(right)
                    counters["axis_dual_split"] += 1
                else:
                    # UNKNOWN body/face diagonal arithmetic in DX2:
                    # following both yields a superset of either hypothesis.
                    route(left)
                    route(right)
                    counters["diagonal_opaque_both_branches"] += 1
            elif 0x20 <= op <= 0x22:
                threshold, delta = code[pc+1:pc+3]
                coordinate = coords[op-0x20]
                if coordinate < threshold+margin:
                    route(pc+3)
                if coordinate >= threshold-margin:
                    route(pc+3+delta)
                counters["axis_half_split"] += 1
            elif 0x23 <= op <= 0x25:
                low, high = code[pc+1:pc+3]
                first, second = number(pc+3, 2), number(pc+5, 2)
                coordinate = coords[op-0x23]
                if coordinate < low+margin:
                    route(pc+7+first)
                if coordinate >= high-margin:
                    route(pc+7+second)
                counters["axis_dual_split16"] += 1
            elif 0x26 <= op <= 0x28:
                low, high = code[pc+1:pc+3]
                coordinate = coords[op-0x26]
                if low-margin <= coordinate < high+margin:
                    route(pc+3)
                counters["axis_filter8"] += 1
            elif 0x29 <= op <= 0x2b:
                low, high = number(pc+1, 3), number(pc+4, 3)
                coordinate = coords[op-0x29]*SOURCE_SCALE_DIVISOR
                guard = margin*SOURCE_SCALE_DIVISOR
                if low-guard <= coordinate < high+guard:
                    route(pc+7)
                counters["axis_filter24_hypothesis"] += 1
            elif 0x30 <= op <= 0x4f:
                candidates.add(base+op-0x30)
            elif 0x50 <= op <= 0x52:
                candidates.add(base+number(pc+1, op-0x50+1))
            else:
                raise ValueError(f"Unknown query MOPP opcode 0x{op:02x}")
        if not candidates <= self.complete_leaf_set:
            raise ValueError("Point candidate escaped independently traced source leaf IDs")
        return {
            "candidate_triangle_ids": sorted(candidates),
            "candidate_triangle_count": len(candidates),
            "reachable_query_states": len(visited),
            "axis_filters_seen": (counters["axis_filter8"] +
                                  counters["axis_filter24_hypothesis"]),
            "opaque_diagonal_decisions_explored_both": counters[
                "diagonal_opaque_both_branches"],
            "rescale_instructions_applied": counters["rescale"],
            "tolerance_quantization_units": margin,
            "query_is_a_havok_runtime_result": False,
            "narrowphase_triangle_intersections_computed": False,
            "diagonal_filter_arithmetic_resolved": False,
        }


def inspect_source_level(level: bytes, blocks: list[dict], *,
                         max_centroids: int = 0,
                         tolerance_units: float = DEFAULT_TOLERANCE) -> dict:
    """Validate original Level→mesh→MOPP then probe selected triangle centroids.

    max_centroids=0 means ALL original nondegenerate triangle centroids.
    This is a source-derived experiment and does not execute game physics.
    """
    if type(max_centroids) is not int or not 0 <= max_centroids <= 300_000:
        raise ValueError("Invalid centroid sample bound")
    validated = mopp.inspect_mopp_link(level, blocks)
    flat = mopp.flatcheck.inspect_level_flattened_mesh(level, blocks)
    nverts = flat["render_and_flat_vertex_count"]
    ntri = flat["render_and_flat_triangle_count"]
    vertex_at = flat["level_flat_vertex_array_offset"]
    indices_at = flat["level_flat_index_array_offset"]
    origins = struct.unpack_from("<4f", level,
                                 validated["mopp_code_start_in_level"]-20)
    code = level[validated["mopp_code_start_in_level"]:
                 validated["mopp_code_end_in_level"]]
    walker = ConservativeMoppPointCandidates(code, ntri, origins)
    verts = [struct.unpack_from("<3f", level, vertex_at+16*i)
             for i in range(nverts)]
    tri = struct.unpack_from("<" + str(3*ntri)+"I", level, indices_at)
    excluded = set(validated["omitted_zero_area_triangle_ids"])
    samples = misses = total_candidates = max_candidates = 0
    diagonal_steps = rescale_steps = 0
    first_missed = []
    for tid in range(ntri):
        if tid in excluded:
            continue
        if max_centroids and samples >= max_centroids:
            break
        points = [verts[tri[3*tid+i]] for i in range(3)]
        xyz = tuple(sum(p[axis] for p in points)/3.0 for axis in range(3))
        answer = walker.point(xyz, tolerance_units=tolerance_units)
        candidates = answer["candidate_triangle_ids"]
        samples += 1
        total_candidates += len(candidates)
        max_candidates = max(max_candidates, len(candidates))
        diagonal_steps += answer["opaque_diagonal_decisions_explored_both"]
        rescale_steps += answer["rescale_instructions_applied"]
        if tid not in candidates:
            misses += 1
            if len(first_missed) < 8:
                # Never leak private original vertex positions into repo/CI.
                first_missed.append(tid)
    return {
        "schema": SCHEMA,
        "status": ("zero_observed_centroid_false_negatives" if not misses
                   else "centroid_counterexample_observed"),
        "original_level_triangle_count": ntri,
        "original_mopp_reachable_triangle_count":
            validated["unique_valid_mopp_triangle_leaves"],
        "nondegenerate_centroid_probes": samples,
        "centroid_false_negatives": misses,
        "first_missed_original_triangle_ids": first_missed,
        "mean_candidate_triangles": (total_candidates / samples if samples else 0.0),
        "maximum_candidate_triangles": max_candidates,
        "total_opaque_diagonal_both_branch_decisions": diagonal_steps,
        "total_rescale_instructions_executed": rescale_steps,
        "tolerance_quantization_units": tolerance_units,
        "all_centroids_checked": (samples ==
            validated["unique_valid_mopp_triangle_leaves"]),
        "spatial_semantics_runtime_verified": False,
        "query_uses_conservative_unknown_diagonal_routing": True,
        "native_collision_writer_available": False,
        "original_level_bytes_modified": False,
    }


def audit_map(path: Path, *, max_centroids: int = 0,
              tolerance_units: float = DEFAULT_TOLERANCE) -> dict:
    if (not isinstance(path, Path) or not path.is_file()
            or path.suffix.casefold() != ".gmp"
            or path.stat().st_size > mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected user-owned original DX2 GMP within size limit")
    root = Path(__file__).resolve().parents[2]
    exporter = root / "map_exporter"
    if str(exporter) not in sys.path:
        sys.path.insert(0, str(exporter))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(path)
    if pkg.version != 95 or pkg.licensee not in mopp.flatcheck.OBSERVED_LICENSEES:
        raise ValueError("Unrecognized original DX2 UE95 licensee")
    levels = [e for e in pkg.exports
              if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one original Level export")
    result = inspect_source_level(
        pkg.payload(levels[0]), find_bsp(pkg),
        max_centroids=max_centroids, tolerance_units=tolerance_units)
    return {"file": path.name,
            "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
            "licensee": pkg.licensee, **result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--max-centroids", type=int, default=0,
                        help="0 checks every nondegenerate triangle centroid")
    parser.add_argument("--tolerance-units", type=float,
                        default=DEFAULT_TOLERANCE,
                        help="Conservative quantization tolerance, default 1.0")
    parser.add_argument("--report", type=Path,
                        help="Write fresh JSON outside original game map directories")
    args = parser.parse_args(argv)
    try:
        if not 1 <= len(args.maps) <= MAX_MAPS:
            raise ValueError("Expected 1..64 original user-owned GMPs")
        paths = [p.resolve() for p in args.maps]
        if len(set(paths)) != len(paths):
            raise ValueError("Duplicate original map paths")
        rows = [audit_map(p, max_centroids=args.max_centroids,
                          tolerance_units=args.tolerance_units) for p in paths]
        summary = {
            "maps": len(rows),
            "triangle_centroid_queries": sum(
                row["nondegenerate_centroid_probes"] for row in rows),
            "missed_centroid_triangle_ids": sum(
                row["centroid_false_negatives"] for row in rows),
            "mean_candidate_triangles": (
                sum(row["mean_candidate_triangles"]*row["nondegenerate_centroid_probes"]
                    for row in rows) /
                sum(row["nondegenerate_centroid_probes"] for row in rows)),
            "all_samples_checked": all(row["all_centroids_checked"] for row in rows),
        }
        result = {
            "schema": SCHEMA, "read_only": True, "summary": summary,
            "maps": rows, "original_game_files_modified": False,
            "havok_query_runtime_verified": False,
            "unknown_diagonal_filters_are_conservatively_unpruned": True,
        }
        if args.report:
            out = args.report.resolve()
            if (out.suffix.casefold() != ".json"
                    or any(out == p or out.is_relative_to(p.parent) for p in paths)):
                raise ValueError("Report must be a new JSON outside all Maps folders")
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("x", encoding="utf-8") as report:
                json.dump(result, report, indent=2, allow_nan=False)
                report.write("\n")
            print(json.dumps({"status": "ok", "report": str(out),
                              "summary": summary}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        # Failure is recorded, not silently misrepresented as a passing query.
        return 1 if summary["missed_centroid_triangle_ids"] else 0
    except (OSError, ValueError, KeyError, TypeError, IndexError,
            OverflowError, struct.error) as error:
        print(json.dumps({"status": "refused", "reason": str(error)}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
