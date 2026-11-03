#!/usr/bin/env python3
"""Reconstruct *candidate* convex brush corners from source-observed DX2 Model faces.

Read-only. This derives vertices by intersecting existing planes; it does NOT
decode stored native vertex XYZ, CSG, BSP, collision, or write any game map.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import sys

import inspect_model_face_records as face_reader

SCHEMA = "DX2SDK-native-model-convex-candidate-v1"
MAX_PLANES = 64
MIN_DETERMINANT = 1e-6
RADIUS_FACTOR = 1.001


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def length(v):
    return math.sqrt(dot(v, v))


def midpoint(points):
    return [sum(p[i] for p in points)/len(points) for i in range(3)]


def triple_intersection(a, b, c):
    """Solve three candidate plane equations n.dot(p)=w."""
    na, wa = a
    nb, wb = b
    nc, wc = c
    va, vb, vc = cross(nb, nc), cross(nc, na), cross(na, nb)
    denom = dot(na, va)
    if abs(denom) < MIN_DETERMINANT:
        return None
    point = [(wa*va[i]+wb*vb[i]+wc*vc[i])/denom for i in range(3)]
    if not all(math.isfinite(x) and abs(x) < 1e8 for x in point):
        return None
    return point


def _ordered_face(vertices, indices, normal):
    center = midpoint([vertices[i] for i in indices])
    cardinal = min(((1.,0.,0.), (0.,1.,0.), (0.,0.,1.)),
                   key=lambda a: abs(dot(a, normal)))
    u = cross(cardinal, normal)
    mag = length(u)
    if mag < MIN_DETERMINANT:
        return []
    u = tuple(v/mag for v in u)
    v = cross(normal, u)
    return sorted(indices, key=lambda i: math.atan2(
        dot(sub(vertices[i], center), v), dot(sub(vertices[i], center), u)))


def _face_fields(face):
    normal = face["candidate_normal_xyz"]
    w = face["candidate_plane_w"]
    center = face["candidate_point_on_plane"]
    radius = face["candidate_face_radius"]
    count = face["vertex_slot_count"]
    if (type(normal) is not list or len(normal) != 3
            or type(center) is not list or len(center) != 3
            or type(count) is not int or not 3 <= count <= 16):
        raise ValueError("Invalid candidate face structure")
    values = (*normal, w, *center, radius)
    if not all(type(x) in (int, float) and math.isfinite(x) and abs(x) < 1e8
               for x in values):
        raise ValueError("Nonfinite/out-of-range candidate face data")
    if abs(length(normal)-1) > 1e-3 or radius < 0:
        raise ValueError("Nonunit normal or negative candidate radius")
    return (tuple(float(x) for x in normal), float(w)), tuple(float(x) for x in center), float(radius), count


def reconstruct_faces(faces):
    """Return a hull only if independent native face metadata agrees.

    Uses the source-observed outward normal hypothesis: interior n.dot(x)<=w.
    The Model export's stored box can use a different coordinate frame;
    intentionally do not force the derived corners into those bounds.
    """
    if not isinstance(faces, list) or not 4 <= len(faces) <= MAX_PLANES:
        return {"status": "unsupported_plane_count",
                "source_face_count": len(faces) if isinstance(faces, list) else None}
    try:
        parsed = [_face_fields(face) for face in faces]
    except (ValueError, KeyError, TypeError):
        return {"status": "unsupported_face_fields"}
    planes = [entry[0] for entry in parsed]
    scale = max(1., *(abs(w) for _, w in planes),
                *(abs(x) for _p, center, _radius, _count in parsed for x in center))
    tol = max(0.025, 2e-5*scale)
    corners = []
    for a, b, c in itertools.combinations(planes, 3):
        vertex = triple_intersection(a, b, c)
        if vertex is None:
            continue
        if any(dot(normal, vertex) > w + tol for normal, w in planes):
            continue
        if not any(length(sub(vertex, seen)) <= tol for seen in corners):
            corners.append(vertex)
    if len(corners) < 4:
        return {"status": "no_bounded_convex_candidate", "vertices_found": len(corners)}

    polygons = []
    radius_errors = []
    for face_id, ((normal, w), point, stored_radius, source_count) in enumerate(parsed):
        ids = [i for i, vertex in enumerate(corners)
               if abs(dot(normal, vertex)-w) <= tol]
        if len(ids) < 3:
            return {"status": "face_has_fewer_than_three_vertices",
                    "first_bad_face": face_id, "found": len(ids),
                    "expected": source_count}
        ids = _ordered_face(corners, ids, normal)
        if len(ids) != source_count:
            return {"status": "source_vertex_count_mismatch",
                    "first_bad_face": face_id, "found": len(ids),
                    "expected": source_count}
        expected_radius = RADIUS_FACTOR * max(
            length(sub(corners[i], point)) for i in ids)
        radius_err = abs(expected_radius - stored_radius)
        radius_tol = max(0.10, stored_radius*0.00005)
        if radius_err > radius_tol:
            return {"status": "source_face_radius_mismatch",
                    "first_bad_face": face_id, "difference": radius_err,
                    "tolerance": radius_tol}
        winding_area = sum(dot(cross(sub(corners[ids[i]], point),
                                     sub(corners[ids[(i+1)%len(ids)]], point)),
                               normal) for i in range(len(ids)))
        if winding_area <= tol*tol:
            return {"status": "invalid_polygon_winding_or_area",
                    "first_bad_face": face_id}
        polygons.append({
            "source_face": face_id, "vertex_indices": ids,
            "source_vertex_slot_count": source_count,
            "candidate_plane_normal_xyz": list(normal), "candidate_plane_w": w,
            "source_face_point_xyz": list(point),
            "source_face_radius": stored_radius,
            "predicted_face_radius": expected_radius,
            "radius_absolute_error": radius_err,
        })
        radius_errors.append(radius_err)

    edges = Counter()
    directed = Counter()
    for poly in polygons:
        ids = poly["vertex_indices"]
        for i in range(len(ids)):
            a, b = ids[i], ids[(i+1)%len(ids)]
            edges[tuple(sorted((a,b)))] += 1
            directed[(a,b)] += 1
    if (any(n != 2 for n in edges.values())
            or any(directed[(a,b)] != 1 or directed[(b,a)] != 1
                   for a,b in edges)):
        return {"status": "nonmanifold_candidate",
                "vertices_found": len(corners),
                "source_face_count": len(faces)}
    if len(corners)-len(edges)+len(polygons) != 2:
        return {"status": "euler_characteristic_mismatch",
                "vertices_found": len(corners),
                "edges_found": len(edges),
                "source_face_count": len(faces)}
    return {
        "status": "validated_candidate_convex_hull",
        "coordinate_space": "candidate source Model face-plane coords, not confirmed game world",
        "corner_xyz": corners, "polygons_outward": polygons,
        "corner_count": len(corners), "face_count": len(polygons),
        "edge_count": len(edges),
        "vertex_slots_checked": sum(p["source_vertex_slot_count"] for p in polygons),
        "max_source_radius_error": max(radius_errors),
        "halfspace_tolerance_ue_units": tol,
        "source_plane_winding_assumption": "outward normal; interior dot(n,x)<=w",
        "native_vertex_coordinates_decoded": False,
        "native_bsp_or_collision_decoded": False,
    }


def audit_map(path: Path, *, include_geometry=False):
    path = Path(path)
    if path.suffix.casefold() != ".gmp" or not path.is_file():
        raise ValueError("Expected existing user-owned DX2 .gmp")
    if path.stat().st_size > face_reader.header.MAX_MAP_BYTES:
        raise ValueError("Map input too large")
    pkg = face_reader.header.Package(path)
    if pkg.version != 95 or pkg.licensee not in face_reader.header.DX2_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    counts = Counter()
    rows = []
    for exp in pkg.exports:
        if pkg.class_name(exp) != "Model":
            continue
        counts["model_exports"] += 1
        record = face_reader.inspect_model_faces(pkg.payload(exp))
        if record["status"] != "decoded_candidate_face_records":
            counts["skipped_"+record["status"]] += 1
            continue
        result = reconstruct_faces(record["faces"])
        counts[result["status"]] += 1
        if result["status"] == "validated_candidate_convex_hull":
            counts["reconstructed_corners"] += result["corner_count"]
            counts["reconstructed_faces"] += result["face_count"]
            counts["reconstructed_vertex_slots"] += result["vertex_slots_checked"]
            if not include_geometry:
                del result["corner_xyz"], result["polygons_outward"]
        rows.append({"model_export": exp["index"], "model_name": exp["name"],
                     **result})
    return {"file": path.name, "sha256": hashlib.sha256(pkg.data).hexdigest(),
            "licensee": pkg.licensee, "counts": dict(counts),
            "nonempty_model_results": rows}


def audit_maps(paths, *, include_geometry=False):
    if not paths or len(paths) > face_reader.header.MAX_MAPS:
        raise ValueError("Provide 1 to 32 user-owned DX2 GMPs")
    resolved = [Path(path).resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate input map path")
    reports = [audit_map(path, include_geometry=include_geometry) for path in resolved]
    counts = Counter()
    for report in reports:
        counts.update(report["counts"])
    return {
        "schema": SCHEMA, "read_only": True, "source_game_maps_modified": False,
        "native_model_vertices_decoded": False,
        "native_bsp_or_collision_compiled": False, "dx2_runtime_verified": False,
        "totals": dict(counts), "maps": reports,
        "limitations": [
            "Derived intersections are not native stored vertex XYZ data.",
            "Only convex watertight shapes matching native face counts and radii are emitted.",
            "Stored Model bbox may use a different face-plane coordinate frame.",
            "Compound, disconnected or ambiguous solids are explicitly refused.",
            "No BSP, collision, Havok, CSG or GMP writing is implemented.",
        ],
    }


def write_candidate_obj(shape, output: Path, source: Path, export_id: int):
    """Write one validated triangulated, untextured offline preview OBJ."""
    if shape.get("status") != "validated_candidate_convex_hull":
        raise ValueError("Only validated candidate convex hulls may be previewed")
    output, source = Path(output).resolve(), Path(source).resolve()
    if output.suffix.casefold() != ".obj" or output == source:
        raise ValueError("Expected a new .obj distinct from source GMP")
    if output.is_relative_to(source.parent):
        raise ValueError("Write previews outside the original game map directory")
    lines = [
        "# DX2SDK candidate convex Model, reconstructed from original face planes",
        "# NOT native vertex data; runtime coordinate frame unverified",
        "o Model_Export_"+str(export_id)
    ]
    for xyz in shape["corner_xyz"]:
        lines.append("v "+" ".join(format(float(v), ".10g") for v in xyz))
    for poly in shape["polygons_outward"]:
        ids = poly["vertex_indices"]
        lines.append("g Candidate_Face_"+str(poly["source_face"]))
        for i in range(1, len(ids)-1):
            lines.append("f "+" ".join(str(v+1) for v in (ids[0],ids[i],ids[i+1])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="ascii") as stream:
        stream.write("\n".join(lines)+"\n")


def export_single_model(source: Path, export_id: int, output: Path) -> dict:
    if type(export_id) is not int or export_id < 1:
        raise ValueError("Model export ID must be a positive integer")
    source = Path(source)
    if source.suffix.casefold() != ".gmp" or not source.is_file():
        raise ValueError("Expected existing user-owned DX2 .gmp")
    if source.stat().st_size > face_reader.header.MAX_MAP_BYTES:
        raise ValueError("Map exceeds safe research input size")
    pkg = face_reader.header.Package(source)
    if pkg.version != 95 or pkg.licensee not in face_reader.header.DX2_LICENSEES:
        raise ValueError("Expected UE95 DX2 licensee 65/67/68/69")
    if export_id > len(pkg.exports):
        raise ValueError("Model export index outside source package")
    exp = pkg.exports[export_id-1]
    if pkg.class_name(exp) != "Model":
        raise ValueError("Selected export is not a Model")
    record = face_reader.inspect_model_faces(pkg.payload(exp))
    if record["status"] != "decoded_candidate_face_records":
        raise ValueError("Selected Model has no supported candidate face records")
    hull = reconstruct_faces(record["faces"])
    if hull["status"] != "validated_candidate_convex_hull":
        raise ValueError("Model did not pass convex validation: "+hull["status"])
    write_candidate_obj(hull, output, source, export_id)
    return {"model_export": export_id, "model_name": exp["name"],
            "candidate_vertices": hull["corner_count"], "faces": hull["face_count"],
            "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
            "obj": str(Path(output).resolve()), "native_map_written": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", type=Path, nargs="+")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-geometry", action="store_true")
    parser.add_argument("--preview-model-export", type=int)
    parser.add_argument("--preview-obj", type=Path)
    args = parser.parse_args(argv)
    try:
        if (args.preview_model_export is None) != (args.preview_obj is None):
            raise ValueError("Specify --preview-model-export and --preview-obj together")
        if args.preview_obj is not None and len(args.maps) != 1:
            raise ValueError("OBJ preview needs exactly one original GMP source")
        result = audit_maps(args.maps, include_geometry=args.include_geometry)
        if args.preview_obj is not None:
            result["obj_preview"] = export_single_model(
                args.maps[0], args.preview_model_export, args.preview_obj)
        if args.report:
            face_reader.header.write_report(result, args.report, args.maps)
            print(json.dumps({"status": "ok", "report": str(args.report),
                              "totals": result["totals"]}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, IndexError, OverflowError, struct.error) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
