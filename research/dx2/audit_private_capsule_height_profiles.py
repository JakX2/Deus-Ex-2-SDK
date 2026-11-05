#!/usr/bin/env python3
"""Owner-local GMP profile replay auditor with a minimal aggregate-only report.

Input manifest and profile sidecars contain PRIVATE original-game-derived data
and must remain OUTSIDE the repository. For each profile this tool reopens the
owner's original GMP through the existing SHA-authenticated, source-complete
Python first-contact/MOPP oracle, regenerates the entire multi-height profile,
and refuses publication if ANY field differs (within tiny numerical tolerance).

The output contains only fixed-schema aggregate counters and fixed labels:
NEVER paths, map names, hashes, coordinates, original triangle IDs, timing,
per-map breakdowns, or the private manifest's contents. Aggregation is NOT
cryptographic anonymization; publishing even aggregates is a conscious choice.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import math
from pathlib import Path
import sys
import tempfile
from typing import Any

import export_capsule_first_contact_preview as preview

MANIFEST_SCHEMA = "DX2Ed-private-GMP-capsule-profile-audit-manifest-v1"
REPORT_SCHEMA = "DX2Ed-redacted-GMP-capsule-profile-audit-v1"
MAX_MANIFEST_BYTES = 128_000
MAX_PROFILE_BYTES = 512_000
MAX_CASES = 32
MIN_PUBLIC_MAPS = 3
REPO_ROOT = Path(__file__).resolve().parents[2]


class AuditRefusal(ValueError):
    """Publicly safe code only; never use raw owner paths in exceptions."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def refuse(code: str) -> None:
    raise AuditRefusal(code)


def _private_file(raw: Any, base: Path, suffix: str) -> Path:
    if not isinstance(raw, str) or not 0 < len(raw) <= 4096 or "\x00" in raw:
        refuse("invalid_private_path")
    path = Path(raw)
    path = (path if path.is_absolute() else base / path).resolve()
    if (path.suffix.lower() != suffix or not path.is_file()
            or path.is_relative_to(REPO_ROOT)):
        refuse("unsafe_private_path")
    return path


def _read_json(path: Path, maximum: int) -> Any:
    size = path.stat().st_size
    if not 0 < size <= maximum:
        refuse("private_input_size_refused")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        refuse("invalid_private_json")


def _number(value: Any, low: float, high: float) -> bool:
    return (type(value) in (int, float)
            and math.isfinite(value) and low <= value <= high)


def _preview_to_level(value: Any) -> tuple[float, float, float]:
    if (not isinstance(value, list) or len(value) != 3
            or any(not _number(v, -100_000., 100_000.) for v in value)):
        refuse("invalid_private_profile")
    # Godot preview = original Level (x,z,y)/10.
    return (float(value[0]) * 10., float(value[2]) * 10.,
            float(value[1]) * 10.)


def _profile_inputs(document: Any, source: Path) -> dict[str, Any]:
    if (not isinstance(document, dict)
            or document.get("schema") != preview.PROFILE_SCHEMA
            or document.get("source_map") != source.name
            or document.get("read_only") is not True
            or document.get("not_a_native_collision_writer") is not True
            or document.get("original_game_assets_modified") is not False
            or document.get("havok_runtime_contact_verified") is not False
            or document.get("physics_materials_verified") is not False
            or document.get("coordinate_system") != preview.COORD
            or document.get("height_direction_original_Level") != "positive Z"
            or document.get("height_offsets_relative_to_baseline") is not True
            or document.get("contact_is_not_a_blocking_classifier") is not True
            or document.get("no_contact_is_not_proof_of_walkability") is not True):
        refuse("invalid_private_profile")
    digest = document.get("source_sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        refuse("invalid_private_profile")
    a = _preview_to_level(document.get("baseline_capsule_start_godot_xyz"))
    b = _preview_to_level(document.get("baseline_capsule_end_godot_xyz"))
    radius = document.get("capsule_radius_level_units")
    half = document.get("capsule_axis_half_length_level_units")
    offsets = document.get("profile_samples")
    if (not _number(radius, .01, 20.) or not _number(half, 0., 20.)
            or not isinstance(offsets, list) or not 2 <= len(offsets) <= 9):
        refuse("invalid_private_profile")
    elevations = []
    previous = -1.
    for index, sample in enumerate(offsets):
        if not isinstance(sample, dict):
            refuse("invalid_private_profile")
        height = sample.get("relative_height_level_units")
        if (not _number(height, 0., 100.)
                or (index == 0 and height != 0.)
                or (index > 0 and height - previous < .01)):
            refuse("invalid_private_profile")
        elevations.append(float(height))
        previous = float(height)
    return {
        "expected_sha256": digest,
        "start": a, "end": b,
        "radius": float(radius),
        "axis": (0., 0., 1.),
        "axis_half_length": float(half),
        "height_offsets": elevations,
    }


def _same(left: Any, right: Any) -> bool:
    """Compare complete private documents, with safe 1e-6 float tolerance.

    Integers, booleans, null, strings and dictionary keys remain exact.
    Float tolerance exists only for cross-OS numerical first-contact rounding.
    """
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if type(left) is float or type(right) is float:
        return (_number(left, -1e9, 1e9) and _number(right, -1e9, 1e9)
                and math.isclose(left, right, rel_tol=1e-8, abs_tol=1e-6))
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same(a, b) for a, b in zip(left, right))
    return left == right


def _redacted_counts(documents: list[dict[str, Any]], distinct_maps: int) -> dict:
    touched = empty = one = few = many = 0
    cases_with_contact = 0
    for doc in documents:
        case_hit = False
        for row in doc["profile_samples"]:
            count = row["geometric_source_triangle_hits"]
            first = row["first_hit_original_triangle_id"]
            # All values below came from a fresh, authenticated worker
            # invocation AND passed complete private document equivalence.
            if type(count) is not int or count < 0:
                refuse("invalid_verified_contact_count")
            if count == 0:
                empty += 1
                if first is not None:
                    refuse("invalid_verified_contact_count")
            else:
                touched += 1
                case_hit = True
                if type(first) is not int or first < 0:
                    refuse("invalid_verified_contact_count")
                if count == 1:
                    one += 1
                elif count <= 4:
                    few += 1
                else:
                    many += 1
        cases_with_contact += int(case_hit)
    return {
        "schema": REPORT_SCHEMA,
        "report_kind": "redacted_aggregate_only",
        "verified_original_gmp_count": distinct_maps,
        "verified_private_profile_count": len(documents),
        "total_capsule_height_samples": touched + empty,
        "height_samples_with_source_triangle_contact": touched,
        "height_samples_without_source_triangle_contact": empty,
        "profiles_with_any_source_triangle_contact": cases_with_contact,
        "contact_triangle_count_buckets": {
            "none": empty, "one": one, "two_to_four": few, "five_or_more": many},
        "read_only": True,
        "original_game_assets_modified": False,
        "havok_runtime_contact_verified": False,
        "not_a_gameplay_walkability_classifier": True,
        "aggregate_counts_can_still_be_sensitive": True,
    }


def audit(manifest_path: Path, output_path: Path, *,
          allow_small_cohort: bool = False) -> dict:
    """Fail closed: no report written until every private source replay passes."""
    manifest_path = Path(manifest_path).resolve()
    output_path = Path(output_path).resolve()
    if (not manifest_path.is_file() or manifest_path.suffix.lower() != ".json"
            or manifest_path.is_relative_to(REPO_ROOT)
            or output_path.is_relative_to(REPO_ROOT)
            or output_path.suffix.lower() != ".json"
            or not output_path.parent.is_dir()
            or output_path.exists()
            or manifest_path == output_path):
        refuse("unsafe_report_or_manifest_path")
    manifest = _read_json(manifest_path, MAX_MANIFEST_BYTES)
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "cases"}:
        refuse("invalid_private_manifest")
    cases = manifest["cases"]
    if (manifest["schema"] != MANIFEST_SCHEMA or not isinstance(cases, list)
            or not 1 <= len(cases) <= MAX_CASES):
        refuse("invalid_private_manifest")

    inputs: list[tuple[Path, Path, dict, dict]] = []
    seen_profiles: set[Path] = set()
    seen_requests: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"map_file", "private_profile"}:
            refuse("invalid_private_manifest")
        source = _private_file(case["map_file"], manifest_path.parent, ".gmp")
        private = _private_file(case["private_profile"], manifest_path.parent, ".json")
        if (private == manifest_path or source == manifest_path
                or private.is_relative_to(source.parent)
                or source.is_relative_to(private.parent)
                or output_path.is_relative_to(source.parent)
                or private in seen_profiles):
            refuse("unsafe_private_path")
        profile = _read_json(private, MAX_PROFILE_BYTES)
        kwargs = _profile_inputs(profile, source)
        signature = json.dumps([str(source), kwargs], sort_keys=True)
        if signature in seen_requests:
            refuse("duplicate_private_profile")
        seen_profiles.add(private)
        seen_requests.add(signature)
        inputs.append((source, private, profile, kwargs))

    unique_hashes = {kwargs["expected_sha256"] for _, _, _, kwargs in inputs}
    if not allow_small_cohort and len(unique_hashes) < MIN_PUBLIC_MAPS:
        refuse("too_few_distinct_source_maps_for_aggregate")

    # Stage sensitive derived documents in a temporary LOCAL directory
    # adjacent to the owner's chosen report destination. All temporary
    # sidecars are removed even if a later validation refuses the batch.
    verified: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(
            prefix="dx2sdk_private_audit_", dir=output_path.parent) as work:
        for index, (source, _private, profile, kwargs) in enumerate(inputs):
            staging = Path(work) / f"case_{index:02d}.json"
            try:
                # Never echo original map paths or private worker exceptions:
                # stdout/stderr from the existing exporter are discarded.
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    preview.build(source, staging, **kwargs)
                replay = _read_json(staging, MAX_PROFILE_BYTES)
            except Exception:
                # Decoders may raise struct.error, RuntimeError or diagnostics
                # embedding owner file names; none can escape the public CLI.
                refuse("source_recomputation_refused")
            if not _same(profile, replay):
                refuse("original_profile_replay_mismatch")
            verified.append(replay)

    report = _redacted_counts(verified, len(unique_hashes))
    # Use exclusive creation to avoid overwriting an owner file. No private
    # sample data appears in the output or in any progress/log message.
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True,
                    help="Private owner-local JSON manifest, NEVER commit")
    ap.add_argument("--output", type=Path, required=True,
                    help="Fresh aggregate-only JSON outside checkout and retail Maps")
    ap.add_argument("--allow-small-cohort", action="store_true",
                    help="Explicitly publish aggregation from fewer than 3 distinct GMPs")
    args = ap.parse_args(argv)
    try:
        report = audit(args.manifest, args.output,
                       allow_small_cohort=args.allow_small_cohort)
    except AuditRefusal as exc:
        print(json.dumps({"status": "refused", "code": exc.code}), file=sys.stderr)
        return 1
    except Exception:
        # Never expose unexpected private-map exception details/tracebacks.
        print(json.dumps({"status": "refused", "code": "audit_failed"}),
              file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok",
                      "verified_original_gmp_count": report["verified_original_gmp_count"],
                      "verified_private_profile_count": report["verified_private_profile_count"],
                      "redacted_aggregate_only": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
