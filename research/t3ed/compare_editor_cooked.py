#!/usr/bin/env python3
"""Read-only T3/Flesh .unr -> .gmp source/cooked comparison.

Compares *preexisting* maps; NEVER runs T3Ed, recompiles, edits source
or claims runtime-compatible collision, lighting or BSP.
Uses DX2SDK's existing UE95 package and packed Flesh BSP readers.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

SDK_ROOT = Path(__file__).resolve().parents[2]
MAP_EXPORTER = SDK_ROOT / "map_exporter"
if str(MAP_EXPORTER) not in sys.path:
    sys.path.insert(0, str(MAP_EXPORTER))

from dx2inspect import Package
from dx2scene import find_bsp

SCHEMA = "DX2SDK-T3Ed-editor-cooked-audit-v1"
MAX_CORPUS_PAIRS = 200


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _package(path: Path) -> tuple[Package, dict]:
    pkg = Package(path)
    if pkg.version != 95:
        raise ValueError(f"Unsupported UE package version {pkg.version} for {path.name}; expected 95")
    if not any(pkg.class_name(e) == "Level" for e in pkg.exports):
        raise ValueError(f"Missing Level export: {path.name}")
    classes = Counter(pkg.class_name(e) for e in pkg.exports)
    return pkg, {
        "file": path.name, "bytes": len(pkg.data), "sha256": _sha(pkg.data),
        "unreal_package_version": pkg.version, "licensee_version": pkg.licensee,
        "package_guid": pkg.guid, "names": len(pkg.names),
        "imports": len(pkg.imports), "exports": len(pkg.exports),
        "classes": dict(sorted(classes.items())),
    }


def _export_groups(pkg: Package) -> dict[tuple[str, str], list[dict]]:
    result: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in pkg.exports:
        result[(pkg.class_name(e), e["name"])].append(e)
    return result


def _diff_exports(source: Package, cooked: Package) -> dict:
    src, dst = _export_groups(source), _export_groups(cooked)
    unchanged, changed, removed, added = Counter(), Counter(), Counter(), Counter()
    ambiguous, examples = [], []
    for cls, name in sorted(src.keys() | dst.keys()):
        left = src.get((cls, name), [])
        right = dst.get((cls, name), [])
        # Indices can be renumbered on cook. Ambiguous class+name never
        # implies that two exports are semantically the same object.
        if len(left) > 1 or len(right) > 1:
            ambiguous.append({"class": cls, "name": name,
                              "source_count": len(left), "cooked_count": len(right)})
        elif left and not right:
            removed[cls] += 1
        elif right and not left:
            added[cls] += 1
        elif left and right:
            a, b = source.payload(left[0]), cooked.payload(right[0])
            if a == b:
                unchanged[cls] += 1
            else:
                changed[cls] += 1
                if len(examples) < 30:
                    examples.append({
                        "class": cls, "name": name,
                        "source_bytes": len(a), "cooked_bytes": len(b),
                        "source_sha256": _sha(a), "cooked_sha256": _sha(b),
                    })
    return {
        "matching_method": "unique class+name; native export indices are not stable",
        "identical_payloads_by_class": dict(sorted(unchanged.items())),
        "changed_payloads_by_class": dict(sorted(changed.items())),
        "source_only_exports_by_class": dict(sorted(removed.items())),
        "cooked_only_exports_by_class": dict(sorted(added.items())),
        "ambiguous_export_identities": ambiguous,
        "changed_examples": examples,
        "identical_payloads": sum(unchanged.values()),
        "changed_payloads": sum(changed.values()),
        "source_only_exports": sum(removed.values()),
        "cooked_only_exports": sum(added.values()),
    }


def _flesh_bsp(pkg: Package) -> tuple[dict, Counter[str], list[tuple[int, int, str]]]:
    level = next(e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0)
    raw = pkg.payload(level)
    blocks = find_bsp(pkg)
    fingerprints: Counter[str] = Counter()
    spans: list[tuple[int, int, str]] = []
    materials: Counter[str] = Counter()
    triangles = 0
    last_end = 0
    for b in blocks:
        start, end = int(b["offset"]), int(b["end"])
        if not last_end <= start < end <= len(raw):
            raise ValueError("Validated BSP decoder returned overlapping or invalid Level-relative ranges")
        last_end = end
        digest = _sha(raw[start:end])
        fingerprints[digest] += 1
        spans.append((start, end, digest))
        for sec in b["sections"]:
            n = len(sec["indices"]) // 3
            triangles += n
            materials[str(sec["material"])] += n
    return {
        "level_payload_bytes": len(raw),
        "validated_render_blocks": len(blocks),
        "render_triangles": triangles,
        "material_section_count": sum(len(b["sections"]) for b in blocks),
        "triangle_count_by_material": dict(sorted(materials.items())),
        "unique_render_block_payload_sha256": len(fingerprints),
    }, fingerprints, spans


def _common_prefix_length(a: bytes, b: bytes) -> int:
    """Exact offset-aligned common prefix, not a heuristic binary diff."""
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def _level_nonrender_regions(
    src_level: bytes, src_spans: list[tuple[int, int, str]],
    dst_level: bytes, dst_spans: list[tuple[int, int, str]],
) -> dict:
    """Compare only bytes outside validated, ordered Flesh render blocks.

    Never infer native semantics from unknown bytes. For re-ordered, changed
    or missing render blocks, fail closed instead of misaligning opaque data.
    The caller is responsible for validating the spans via _flesh_bsp.
    """
    if not src_spans or not dst_spans:
        return {"status": "unavailable_no_render_anchors",
                "render_block_order_aligned": False, "regions": []}
    if [s[2] for s in src_spans] != [s[2] for s in dst_spans]:
        return {"status": "unavailable_render_blocks_changed_or_reordered",
                "render_block_order_aligned": False, "regions": []}
    def regions(level: bytes, spans: list[tuple[int, int, str]]) -> list[tuple[int, int, bytes]]:
        cuts: list[tuple[int, int, bytes]] = []
        start = 0
        for block_start, block_end, _ in spans:
            cuts.append((start, block_start, level[start:block_start]))
            start = block_end
        cuts.append((start, len(level), level[start:]))
        return cuts

    before = regions(src_level, src_spans)
    after = regions(dst_level, dst_spans)
    assert len(before) == len(after)
    result = []
    for i, (source, cooked) in enumerate(zip(before, after)):
        src_start, src_end, src_data = source
        dst_start, dst_end, dst_data = cooked
        shared = _common_prefix_length(src_data, dst_data)
        src_divergence = src_data[shared:]
        dst_divergence = dst_data[shared:]
        label = ("before_first_render_block" if i == 0 else
                 "after_last_render_block" if i == len(before) - 1 else
                 f"between_render_blocks_{i}_{i+1}")
        result.append({
            "region": label,
            "source_level_start": src_start, "source_level_end": src_end,
            "cooked_level_start": dst_start, "cooked_level_end": dst_end,
            "source_bytes": len(src_data), "cooked_bytes": len(dst_data),
            "cooked_minus_source_bytes": len(dst_data) - len(src_data),
            "whole_region_equal": src_data == dst_data,
            "aligned_common_prefix_bytes": shared,
            "source_divergent_bytes": len(src_divergence),
            "cooked_divergent_bytes": len(dst_divergence),
            "source_divergent_sha256": _sha(src_divergence),
            "cooked_divergent_sha256": _sha(dst_divergence),
        })
    return {
        "status": "aligned_by_ordered_byte_identical_render_blocks",
        "render_block_order_aligned": True,
        "regions": result,
        "unknown_native_sections_parsed": False,
        "collision_visibility_lighting_inferred": False,
    }


def audit_pair(source_path: Path, cooked_path: Path) -> dict:
    source_path, cooked_path = Path(source_path), Path(cooked_path)
    if source_path.resolve() == cooked_path.resolve():
        raise ValueError("Source and cooked map must be different files")
    if source_path.suffix.casefold() != ".unr" or cooked_path.suffix.casefold() != ".gmp":
        raise ValueError("Expected source .unr and cooked .gmp in this order")
    if source_path.stem.casefold() != cooked_path.stem.casefold():
        raise ValueError("Source and cooked map basenames do not match")
    src, src_info = _package(source_path)
    dst, dst_info = _package(cooked_path)
    if src.version != dst.version or src.licensee != dst.licensee:
        raise ValueError("Package version/licensee mismatch; not a same-branch source/cooked pair")
    src_bsp, src_hashes, src_spans = _flesh_bsp(src)
    dst_bsp, dst_hashes, dst_spans = _flesh_bsp(dst)
    source_level = src.payload(next(e for e in src.exports if src.class_name(e) == "Level" and e["size"] > 0))
    cooked_level = dst.payload(next(e for e in dst.exports if dst.class_name(e) == "Level" and e["size"] > 0))
    nonrender = _level_nonrender_regions(source_level, src_spans, cooked_level, dst_spans)
    common = src_hashes & dst_hashes  # multiset: repeat block digests matter
    return {
        "schema": SCHEMA, "read_only": True,
        "native_compiler_executed": False, "game_runtime_verified": False,
        "source": src_info, "cooked": dst_info,
        "exports": _diff_exports(src, dst),
        "level_nonrender_regions": nonrender,
        "bsp": {
            "source": src_bsp, "cooked": dst_bsp,
            "byte_identical_render_blocks": sum(common.values()),
            "source_only_render_blocks": sum((src_hashes - common).values()),
            "cooked_only_render_blocks": sum((dst_hashes - common).values()),
            "equality_test": "SHA-256 of whole validated Level-relative render blocks; multiplicity preserved",
            "collision_visibility_lighting_parity_proven": False,
        },
        "limits": [
            "Exports matched only when class+name is unique in both packages.",
            "Changed serialized payloads may reflect reference or offset rewrites, not semantic changes.",
            "Matching visible render blocks do NOT prove collision, Havok, lighting, portal or navigation equality.",
            "Level non-render sections are opaque; byte deltas are not attributed to collision, lighting or PVS.",
            "T3Ed was not executed and no fresh level was compiled.",
        ],
    }


def collect_pairs(folder: Path) -> list[tuple[Path, Path]]:
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("Corpus path must be an existing directory")
    names: dict[tuple[str, str], Path] = {}
    for p in folder.iterdir():
        if not p.is_file() or p.suffix.casefold() not in (".unr", ".gmp"):
            continue
        key = (p.stem.casefold(), p.suffix.casefold())
        if key in names:
            raise ValueError(f"Duplicate case-insensitive filename for {p.stem}")
        names[key] = p
    keys = sorted(k for k, ext in names if ext == ".unr")
    pairs = [(names[(k, ".unr")], names[(k, ".gmp")])
             for k in keys if (k, ".gmp") in names]
    if not pairs:
        raise ValueError("No same-name .unr/.gmp source/cooked pairs found")
    if len(pairs) > MAX_CORPUS_PAIRS:
        raise ValueError(f"Corpus exceeds {MAX_CORPUS_PAIRS} pairs")
    return pairs


def _write_report(doc: dict, output: Path, source_paths: list[Path]) -> None:
    output = Path(output).expanduser().resolve()
    if output.suffix.casefold() != ".json":
        raise ValueError("Report destination must be a JSON filename")
    if any(output == p.resolve() or output.is_relative_to(p.resolve().parent)
           for p in source_paths):
        raise ValueError("Report destination must be outside original map directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf8") as stream:
        json.dump(doc, stream, indent=2)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    pair = sub.add_parser("pair", help="Audit one source/cooked .unr/.gmp pair")
    pair.add_argument("source", type=Path)
    pair.add_argument("cooked", type=Path)
    pair.add_argument("--report", type=Path)
    corpus = sub.add_parser("corpus", help="Audit every matching pair in one folder")
    corpus.add_argument("folder", type=Path)
    corpus.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "pair":
            paths = [args.source, args.cooked]
            doc = audit_pair(*paths)
        else:
            pairs = collect_pairs(args.folder)
            paths = [p for a, b in pairs for p in (a, b)]
            items = [audit_pair(a, b) for a, b in pairs]
            doc = {
                "schema": SCHEMA, "read_only": True,
                "native_compiler_executed": False, "game_runtime_verified": False,
                "pair_count": len(items), "pairs": items,
                "totals": {
                    "byte_identical_bsp_blocks": sum(item["bsp"]["byte_identical_render_blocks"] for item in items),
                    "source_only_polys": sum(item["exports"]["source_only_exports_by_class"].get("Polys", 0) for item in items),
                    "changed_level_exports": sum(item["exports"]["changed_payloads_by_class"].get("Level", 0) for item in items),
                    "ordered_render_blocks_aligned_pairs": sum(
                        item["level_nonrender_regions"]["render_block_order_aligned"] for item in items),
                    "post_render_cooked_divergence_fingerprints": dict(sorted(Counter(
                        item["level_nonrender_regions"]["regions"][-1]["cooked_divergent_sha256"]
                        for item in items
                        if item["level_nonrender_regions"]["render_block_order_aligned"]
                    ).items())),
                },
            }
        if args.report:
            _write_report(doc, args.report, paths)
            print(json.dumps({"status": "ok", "report": str(args.report), "schema": SCHEMA}))
        else:
            print(json.dumps(doc, indent=2))
        return 0
    except (ValueError, OSError, IndexError, KeyError) as e:
        print(json.dumps({"status": "error", "reason": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
