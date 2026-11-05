#!/usr/bin/env python3
"""Owner-local, privacy-redacted GMP/IBD discovery check for DX2Ed 0.6 alpha.

This checks whether the existing direct-GMP importer can locate an original
map and companion mission/shared IBD files. It does NOT parse the entire GMP,
run Godot, certify texture coverage, modify source files, or write a cache.

Output is fixed-schema JSON with no owner map names, hashes or filesystem paths.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCHEMA = "DX2Ed-original-GMP-resource-discovery-preflight-v1"
ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "native_editor" / "godot_editor" / "backend"
MAX_GMP_BYTES = 500_000_000


def preflight(map_file: Path, bundles: list[Path] | None = None) -> dict:
    result = {
        "schema": SCHEMA, "status": "refused",
        "code": "source_not_checked",
        "read_only": True,
        "original_game_assets_modified": False,
        "original_map_package_parsed": False,
        "rendered_godot_scene_verified": False,
        "ibd_contents_verified": False,
        "native_havok_or_gameplay_verified": False,
    }
    try:
        owner = Path(map_file).expanduser().resolve()
        if owner.suffix.lower() != ".gmp" or not owner.is_file():
            result["code"] = "missing_original_gmp"
            return result
        if not 0 < owner.stat().st_size <= MAX_GMP_BYTES:
            result["code"] = "source_size_refused"
            return result
        extra = [Path(p).expanduser().resolve() for p in (bundles or [])]
        if any(p.suffix.lower() != ".ibd" or not p.is_file() for p in extra):
            result["code"] = "invalid_ibd_override"
            return result

        if str(BACKEND_DIR) not in sys.path:
            sys.path.insert(0, str(BACKEND_DIR))
        import dx2_native_backend as backend
        level, selected = backend.map_inputs(owner, extra)
        if not selected or any(not Path(p).is_file() for p in selected):
            result["code"] = "ibd_resource_discovery_incomplete"
            return result
        result.update({
            "status": "ready",
            "code": "bundle_paths_found",
            "selected_ibd_bundle_count": len(selected),
            "mission_ibd_or_override_found": bool(level.mission_bundle or extra),
            "original_map_package_parsed": False,
        })
        return result
    except ValueError as exc:
        # No source names/paths/exception details may appear in a shareable
        # readiness report, even when underlying parser raises them.
        reason = str(exc)
        result["code"] = (
            "mission_ibd_missing" if "Matching .ibd bundle not found" in reason
            else "resource_discovery_refused")
        return result
    except Exception:
        result["code"] = "resource_discovery_failed"
        return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, required=True,
                        help="Owner-original DX2 .gmp file, used locally only")
    parser.add_argument("--bundle", type=Path, action="append", default=[],
                        help="Optional owner-original mission/shared .ibd override")
    args = parser.parse_args(argv)
    report = preflight(args.map, args.bundle)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
