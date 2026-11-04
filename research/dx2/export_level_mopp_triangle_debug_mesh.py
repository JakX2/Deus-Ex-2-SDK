#!/usr/bin/env python3
"""Export a read-only DX2 Level MOPP-triangle debug OBJ plus provenance JSON.

SOURCE DATA: use only user-owned original DX2 .gmp maps. Output is a *research
visualization* of Level f32 geometry with source render-material names, NOT an
engine-authenticated Havok material table or a game-writable cooked mesh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import inspect_level_mopp_triangle_provenance as provenance

SCHEMA = "DX2SDK-Level-MOPP-triangle-debug-mesh-v1"
MAX_TRIANGLES = 300_000
MAX_VERTICES = 300_000


def _rgb(material: str) -> tuple[float, float, float]:
    """Visual-debug palette, deterministic and explicitly NOT physical material."""
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return tuple(round(0.2 + c * 0.7 / 255, 5) for c in digest[:3])


def inspect_mesh(level: bytes, blocks: list[dict]) -> dict:
    """Cross-validated, material-attributed triangles in Level vertex order."""
    original = provenance.inspect_triangle_provenance(level, blocks)
    flat = provenance.mopp.flatcheck.inspect_level_flattened_mesh(level, blocks)
    nverts = flat["render_and_flat_vertex_count"]
    ntri = flat["render_and_flat_triangle_count"]
    if not 3 <= nverts <= MAX_VERTICES or not 1 <= ntri <= MAX_TRIANGLES:
        raise ValueError("Level geometry exceeds debug export limits")

    vertices = [struct.unpack_from("<3f", level, flat["level_flat_vertex_array_offset"] + 16*i)
                for i in range(nverts)]
    indices = struct.unpack_from("<" + str(3*ntri) + "I", level,
                                 flat["level_flat_index_array_offset"])
    if any(i >= nverts for i in indices):
        raise ValueError("Flattened triangle refers to missing vertex")

    mapping = list(struct.iter_unpack("<II", level[
        original["triangle_provenance_start_in_level"]:
        original["triangle_provenance_end_in_level"]]))
    if len(mapping) != ntri:
        raise ValueError("Provenance table length differs from flattened triangles")

    mopp_checked = provenance.mopp.inspect_mopp_link(level, blocks)
    code = level[mopp_checked["mopp_code_start_in_level"]:
                 mopp_checked["mopp_code_end_in_level"]]
    leaf_ids = set(provenance.mopp.trace_mopp_code(code, ntri)[
        "reachable_terminal_triangle_ids"])
    if len(leaf_ids) != original["mopp_leaves_with_render_section_attribution"]:
        raise ValueError("MOPP leaf coverage unexpectedly differs from provenance table")

    material_indices: dict[str, int] = {}
    triangles = []
    t = 0
    source_sections = 0
    for block_idx, block in enumerate(blocks):
        for section_idx, section in enumerate(block["sections"]):
            name = section["material"]
            if not isinstance(name, str) or not name:
                raise ValueError("Missing source render material name")
            if name not in material_indices:
                material_indices[name] = len(material_indices)
            mat_id = material_indices[name]
            section_count = len(section["indices"]) // 3
            if section_count:
                source_sections += 1
            for _ in range(section_count):
                if t >= ntri:
                    raise ValueError("Source render sections exceed flattened triangles")
                block_id, actual_section = mapping[t]
                if actual_section != section_idx:
                    raise ValueError("Unexpected material/provenance section mismatch")
                verts = list(indices[3*t:3*t+3])
                triangles.append({
                    "triangle_id": t,
                    "source_block_id": block_id,
                    "render_block_ordinal": block_idx,
                    "render_section_ordinal": section_idx,
                    "render_material_id": mat_id,
                    "vertex_indices_zero_based": verts,
                    "mopp_terminal_leaf": t in leaf_ids,
                })
                t += 1
    if t != ntri or source_sections != original["distinct_block_section_pairs"]:
        raise ValueError("Source render-block sections do not exhaust flattened geometry")
    if sum(tri["mopp_terminal_leaf"] for tri in triangles) != len(leaf_ids):
        raise ValueError("MOPP terminal leaf manifest count differs from verified code")

    mats = [None] * len(material_indices)
    for name, mat_id in material_indices.items():
        mats[mat_id] = {
            "id": mat_id, "obj_material": f"debug_{mat_id:04d}",
            "render_material_name": name,
            "debug_color_rgb": list(_rgb(name)),
            "physics_material_verified": False,
        }
    return {
        "schema": SCHEMA,
        "status": "verified_MOPP_leaf_and_render_material_debug_mesh",
        "read_only_input": True,
        "world_coordinates": "source-observed Level flattened f32 XYZ (not labelled metres)",
        "render_material_names_are_physics_materials": False,
        "runtime_collision_verified": False,
        "native_writer_available": False,
        "source_vertex_count": nverts,
        "source_triangle_count": ntri,
        "mopp_leaf_triangle_count": len(leaf_ids),
        "zero_area_nonleaf_triangle_count": ntri - len(leaf_ids),
        "source_render_section_count": source_sections,
        "vertices": vertices,
        "triangles": triangles,
        "materials": mats,
    }


def render_obj(atlas: dict, *, include_zero_area: bool = False) -> tuple[str, str, dict]:
    """Turn validated atlas into OBJ/MTL strings, preserving source triangle IDs."""
    if type(include_zero_area) is not bool:
        raise ValueError("include_zero_area must be boolean")
    materials = atlas["materials"]
    lines = ["# DX2SDK read-only MOPP-linked Level debug geometry",
             "# coordinates: Level flattened XYZ; physical units unknown",
             "# materials: ORIGINAL RENDER STRINGS, not Havok physics materials",
             "mtllib collision_triangles.mtl"]
    for xyz in atlas["vertices"]:
        if len(xyz) != 3 or not all(math.isfinite(x) for x in xyz):
            raise ValueError("Nonfinite validated atlas vertex")
        lines.append("v " + " ".join(format(float(x), ".9g") for x in xyz))
    last_group = None
    written = 0
    dropped = 0
    face_source_ids = []
    for tri in atlas["triangles"]:
        if not tri["mopp_terminal_leaf"] and not include_zero_area:
            dropped += 1
            continue
        group = (tri["render_block_ordinal"], tri["render_section_ordinal"],
                 tri["render_material_id"])
        if group != last_group:
            lines.extend([
                f"g block_{group[0]:04d}_section_{group[1]:03d}",
                f"usemtl {materials[group[2]]['obj_material']}",
            ])
            last_group = group
        lines.append(f"# original_level_triangle_id {tri['triangle_id']} "
                     f"source_block_id {tri['source_block_id']} "
                     f"mopp_leaf {int(tri['mopp_terminal_leaf'])}")
        a, b, c = tri["vertex_indices_zero_based"]
        lines.append(f"f {a+1} {b+1} {c+1}")
        written += 1
        face_source_ids.append(tri["triangle_id"])
    if (written + dropped != atlas["source_triangle_count"] or
            written != (atlas["source_triangle_count"] if include_zero_area
                        else atlas["mopp_leaf_triangle_count"])):
        raise ValueError("OBJ export triangle total mismatch")
    mtl = ["# Deterministic debug colors only; NOT game texture or physics metadata"]
    for material in materials:
        r, g, b = material["debug_color_rgb"]
        mtl.extend([f"newmtl {material['obj_material']}",
                    f"Kd {r:.5f} {g:.5f} {b:.5f}",
                    "Ka 0.0 0.0 0.0", "Ks 0.0 0.0 0.0", "illum 1", ""])
    return ("\n".join(lines) + "\n", "\n".join(mtl) + "\n",
            {"obj_faces_written": written,
             "zero_area_faces_not_in_mopp_omitted_from_obj": dropped,
             "obj_face_to_level_triangle_id": face_source_ids,
             "obj_coordinate_reference": "source Level f32 XYZ",
             "debug_mtl_contains_no_verified_physics_properties": True})


def audit_map(path: Path) -> tuple[dict, dict]:
    source = Path(path)
    if (source.suffix.casefold() != ".gmp" or not source.is_file() or
            source.stat().st_size > provenance.mopp.flatcheck.MAX_MAP_BYTES):
        raise ValueError("Expected existing user-owned UE95 DX2 GMP within size limit")
    exporter_dir = Path(__file__).resolve().parents[2] / "map_exporter"
    if str(exporter_dir) not in sys.path:
        sys.path.insert(0, str(exporter_dir))
    from dx2inspect import Package
    from dx2scene import find_bsp
    pkg = Package(source)
    if pkg.version != 95 or pkg.licensee not in provenance.mopp.flatcheck.OBSERVED_LICENSEES:
        raise ValueError("Unrecognized DX2 package version/licensee")
    levels = [e for e in pkg.exports if pkg.class_name(e) == "Level" and e["size"] > 0]
    if len(levels) != 1:
        raise ValueError("Expected exactly one nonempty Level")
    atlas = inspect_mesh(pkg.payload(levels[0]), find_bsp(pkg))
    meta = {"file": source.name, "sha256": hashlib.sha256(pkg.data).hexdigest(),
            "licensee": pkg.licensee}
    return atlas, meta


def export_map(source: Path, destination: Path, *, include_zero_area=False) -> dict:
    """Refuse any write inside source map dir; create a *new* output dir only."""
    if type(include_zero_area) is not bool:
        raise ValueError("include_zero_area must be boolean")
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (destination == source.parent or destination.is_relative_to(source.parent)
            or destination == source or destination == source.parent.parent):
        raise ValueError("Refuse debug output inside or replacing source map directory")
    if destination.exists():
        raise FileExistsError("Destination exists; use a fresh research output directory")
    atlas, meta = audit_map(source)
    obj, mtl, export_info = render_obj(atlas, include_zero_area=include_zero_area)
    # The source has been fully audited before any destination is created.
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    (destination / "collision_triangles.obj").write_text(obj, encoding="utf-8")
    (destination / "collision_triangles.mtl").write_text(mtl, encoding="utf-8")
    manifest = {**meta, **{k:v for k,v in atlas.items() if k != "vertices"},
                "export": export_info}
    (destination / "triangle_provenance.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8")
    return {"source": meta["file"], "output_dir": str(destination),
            "vertices": atlas["source_vertex_count"],
            "triangles": atlas["source_triangle_count"],
            "mopp_leaf_triangles": atlas["mopp_leaf_triangle_count"],
            **{k:v for k,v in export_info.items() if k != "obj_face_to_level_triangle_id"}}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("map", type=Path, help="Original user-owned DX2 GMP")
    p.add_argument("--outdir", type=Path, required=True, help="Fresh directory OUTSIDE map folder")
    p.add_argument("--include-zero-area", action="store_true", help="Include degenerate non-MOPP faces")
    args = p.parse_args(argv)
    try:
        print(json.dumps(export_map(args.map, args.outdir,
                                    include_zero_area=args.include_zero_area), indent=2))
        return 0
    except (ValueError, OSError, IndexError, KeyError, OverflowError, struct.error) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())