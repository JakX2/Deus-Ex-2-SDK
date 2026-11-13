#!/usr/bin/env python3
"""Repeatable whole-map DX2 exporter timings and cProfile hot-function report.

Requires a LOCAL, user-owned Deus Ex: Invisible War Maps directory. This
script does not download, ship, write or alter retail assets. It exports
into an automatically removed temporary folder and checks input SHA-256
before/after, GLB determinism across repetitions and a profiled output.

Example (PowerShell):
  python tools/profile_dx2_map_export.py --maps "D:\\DX2\\Content\\DX2\\Maps" \\
    --map M1_Seattle_Hub_Penthouse_Upper.gmp --repeats 3
  python tools/profile_dx2_map_export.py --maps "D:\\DX2\\Content\\DX2\\Maps" \\
    --map M3_Germany_Trier.gmp --bundle "D:\\DX2\\Content\\DX2\\Maps\\m3_trier.ibd" \\
    --repeats 3 --report "D:\\DX2Bench\\trier_profile.json"

A cProfile pass runs SEPARATELY from unprofiled wall-time samples.
Neither the profile cumulative times nor synthetic microbench timings are
claims about retail-game performance until real assets are actually tested.
"""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "map_exporter"))

from dx2_map_exporter import choose_bundles, resolve_map, run_export


def sha256_file(path: Path) -> str:
    """Stream instead of keeping entire GMP/IBD/Maps.zip in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _profile_stats(profiler: cProfile.Profile, limit: int) -> list[dict]:
    import pstats

    stats = pstats.Stats(profiler)
    rows = []
    for (filename, line, name), (primitive, calls, self_s, total_s, _callers) in stats.stats.items():
        if Path(filename).name not in (
                "dx2level.py", "dx2textures.py", "dx2bundles.py",
                "dx2scene.py", "dx2_map_exporter.py", "dx2inspect.py"):
            continue
        rows.append({
            "module": Path(filename).name, "function": name,
            "line": line, "calls": calls,
            "self_ms": round(self_s * 1000, 3),
            "cumulative_ms": round(total_s * 1000, 3),
        })
    rows.sort(key=lambda item: (-item["cumulative_ms"], -item["self_ms"],
                                item["module"], item["line"], item["function"]))
    return rows[:limit]


def _assert_safe_report_path(path: Path, sources: list[Path]) -> None:
    if path.suffix.lower() != ".json":
        raise ValueError("Profiler report must have a .json extension")
    output = path.resolve()
    if any(output == p.resolve() or _is_within(output, p.parent)
           for p in sources):
        raise ValueError("Profiler report cannot be placed in source map/bundle folders")
    if output.exists():
        raise ValueError("Choose an unused report filename; existing files are not overwritten")


def profile_map_export(
        maps: Path, map_name: str, *,
        manual_bundles: list[Path] | None = None,
        transform_overrides: Path | None = None,
        repeats: int = 3, top: int = 25,
        collect_profile: bool = True,
        runner: Callable | None = None,
) -> dict:
    """Run unprofiled exports and an independent profiled pass.

    All outputs are temporary and deleted on success and failure.
    The optional runner is for test-only dependency injection.
    """
    if not 1 <= repeats <= 12 or not 1 <= top <= 100:
        raise ValueError("Allowed repeats: 1..12; hot-function count: 1..100")
    level = resolve_map(Path(maps), map_name)
    manual = [Path(p) for p in (manual_bundles or [])]
    bundles = choose_bundles(level, manual)
    sources = list(dict.fromkeys(
        [level.path.resolve(), *(p.resolve() for p in bundles)]))
    if transform_overrides is not None:
        overrides = Path(transform_overrides).resolve()
        if not overrides.is_file():
            raise ValueError("Transform override JSON file not found")
        sources.append(overrides)
    sources = list(dict.fromkeys(sources))
    if any(not p.is_file() for p in sources):
        raise ValueError("Required source map or bundle does not exist")
    original = {path: sha256_file(path) for path in sources}
    export = runner or run_export
    samples = []
    fingerprints = []
    counts = []
    profiled = None
    try:
        with TemporaryDirectory(prefix="dx2sdk_profile_") as folder:
            temp = Path(folder).resolve()
            # Most machines use a separate OS temp area. Reject an installation
            # whose configured TMP directory would put output in the source Maps.
            if any(_is_within(temp, source.parent) for source in sources):
                raise ValueError("OS temporary directory is inside source asset folder")
            for repeat in range(repeats + int(collect_profile)):
                output = temp / ("profile.glb" if repeat == repeats else f"sample_{repeat}.glb")
                profiler = cProfile.Profile() if repeat == repeats else None
                start = perf_counter()
                if profiler:
                    profiler.enable()
                try:
                    result = export(level, output, manual=manual,
                                    transform_overrides=transform_overrides)
                finally:
                    if profiler:
                        profiler.disable()
                elapsed = (perf_counter() - start) * 1000
                sidecar = output.with_suffix(".report.json")
                if not output.is_file() or not sidecar.is_file():
                    raise ValueError("Exporter did not produce both GLB and report")
                with output.open("rb") as glb:
                    magic = glb.read(4)
                if output.stat().st_size < 12 or magic != b"glTF":
                    raise ValueError("Exporter produced an invalid GLB header")
                fingerprints.append(sha256_file(output))
                # SHA256 of report bytes verifies serialization determinism too.
                report_digest = sha256_file(sidecar)
                counts.append((fingerprints[-1], report_digest))
                if profiler:
                    profiled = {
                        "label": "SEPARATE cProfile run (instrumented, not wall-time baseline)",
                        "wall_ms_including_profiler": round(elapsed, 3),
                        "hot_functions": _profile_stats(profiler, top),
                    }
                else:
                    samples.append(round(elapsed, 3))
                if not isinstance(result, dict):
                    raise ValueError("Exporter returned a non-dictionary report")
            if len(set(counts)) != 1:
                raise ValueError(
                    "Repeated full-map GLB or report bytes differ; profile result refused")
    finally:
        # Guard the original data even if export, cProfile or the output
        # determinism check raises. This is a detection check; the exporter
        # itself must still use its read-only API.
        for path, digest in original.items():
            if not path.is_file() or sha256_file(path) != digest:
                raise ValueError(
                    "Source map, resource bundle or transform overrides changed")
    summary = {
        "schema": "DX2SDK-exporter-full-map-profile-v1",
        "status": "real-asset-run-verified" if runner is None else "test-runner-only",
        "map_name": level.path.name,
        "bundle_names": [p.name for p in bundles],
        "original_asset_count": len(sources),
        "original_assets_unchanged_sha256": True,
        "glb_report_byte_determinism_verified": True,
        "output_glb_sha256": fingerprints[0],
        "output_report_sha256": counts[0][1],
        "timing_note": "unprofiled wall time, first run may include cold caches",
        "unprofiled_wall_ms": samples,
        "median_unprofiled_ms": round(statistics.median(samples), 3),
        "python_version": platform.python_version(),
        "operating_system": platform.system(),
        "profile": profiled,
        "temporary_glb_and_reports_deleted": True,
        "original_game_files_modified": False,
        "native_dx2_bsp_writer_enabled": False,
        "native_havok_collision_enabled": False,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", required=True, type=Path,
                        help="Local extracted Content/DX2/Maps folder or game root")
    parser.add_argument("--map", required=True, dest="map_name",
                        help="Exact original .gmp filename")
    parser.add_argument("--bundle", action="append", type=Path, default=[],
                        help="Optional IBD or shared bundle, repeatable")
    parser.add_argument("--overrides", type=Path,
                        help="Optional map-specific transform overrides JSON")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--no-profile", action="store_true",
                        help="Skip separate cProfile pass")
    parser.add_argument("--report", type=Path,
                        help="New JSON summary path outside source asset folders")
    args = parser.parse_args(argv)
    try:
        if args.report:
            # Path safety is checked against the actual resolved asset paths
            # immediately before the benchmark to avoid partial writes.
            level = resolve_map(args.maps, args.map_name)
            sources = [level.path, *choose_bundles(level, args.bundle)]
            if args.overrides:
                sources.append(args.overrides)
            _assert_safe_report_path(args.report, sources)
        summary = profile_map_export(
            args.maps, args.map_name, manual_bundles=args.bundle,
            transform_overrides=args.overrides, repeats=args.repeats,
            top=args.top, collect_profile=not args.no_profile)
        text = json.dumps(summary, indent=2, sort_keys=True)
        if args.report:
            # Exclusive create refuses an overwrite race.
            with args.report.open("x", encoding="utf-8") as handle:
                handle.write(text + "\n")
        print(text)
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, OverflowError) as exc:
        print("DX2 full-map benchmark REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
