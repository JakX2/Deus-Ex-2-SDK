"""Exact original GMP byte provenance for a hypothetical World Model plane edit.

Research-only patch plan. It never emits a modified GMP, and does not assert
that BSP, collision or Region fields can be rebuilt.
"""
from __future__ import annotations

import hashlib
import struct

from .bsp_plane_impact import _plane
from .bsp_trace import _load_model
from inspect_world_bsp_node_boundaries import parse_world_model

SCHEMA = "DX2SDK-original-Model-plane-byte-provenance-v1"
PLANE_SIZE = 16


def inspect_plane_bytes(package_bytes: bytes, *, export_offset: int,
                        export_size: int, node_start: int, replacement) -> dict:
    """Validate a source-bounded Model payload and describe exactly 16 changed bytes.

    Only source bytes are inspected; a proposed replacement is never applied
    to the package, even temporarily. The node_start is relative to Model.
    """
    if not isinstance(package_bytes, bytes):
        raise ValueError("Immutable source package bytes required")
    if any(type(x) is not int for x in (export_offset, export_size, node_start)):
        raise ValueError("Export and node offsets must be integers")
    if (export_offset < 0 or export_size < 100 or node_start < 0
            or export_offset > len(package_bytes)
            or export_size > len(package_bytes) - export_offset):
        raise ValueError("Invalid original Model export envelope")
    payload = package_bytes[export_offset:export_offset + export_size]
    frame = parse_world_model(payload, include_nodes=True)
    starts = {row["start"] for row in frame["node_records"]}
    if node_start not in starts or node_start + PLANE_SIZE > len(payload):
        raise ValueError("Plane is not at a validated original Model node boundary")
    old = payload[node_start:node_start + PLANE_SIZE]
    old_plane = struct.unpack("<4f", old)
    proposed = _plane(replacement)
    new = struct.pack("<4f", *proposed)
    if old == new:
        raise ValueError("Original float32 plane bytes would not change")
    absolute = export_offset + node_start
    if package_bytes[absolute:absolute + PLANE_SIZE] != old:
        raise ValueError("Original package-to-Model byte offset mismatch")
    return {
        "schema": SCHEMA,
        "source_package_sha256": hashlib.sha256(package_bytes).hexdigest(),
        "source_model_sha256": hashlib.sha256(payload).hexdigest(),
        "model_export_absolute_offset": export_offset,
        "model_export_serialized_size": export_size,
        "model_node_relative_offset": node_start,
        "original_plane_absolute_offset": absolute,
        "original_plane_float32": list(old_plane),
        "hypothetical_plane_float32": list(proposed),
        "changed_byte_offsets_relative_to_plane": [
            i for i in range(PLANE_SIZE) if old[i] != new[i]],
        "original_plane_sha256": hashlib.sha256(old).hexdigest(),
        "hypothetical_plane_sha256": hashlib.sha256(new).hexdigest(),
        "original_bytes_unchanged": True,
        "native_writer_enabled": False,
        "collision_rebuild_verified": False,
        "runtime_verified": False,
    }


def inspect_original_plane_bytes(world, *, node: int, replacement) -> dict:
    """Anchor byte provenance to a fully source-validated original World Model."""
    world._check_original_unchanged()
    model = _load_model(world)
    if type(node) is not int or not 0 <= node < model["node_count"]:
        raise ValueError("Original Model node ordinal out of bounds")
    pkg = world._package
    exp = pkg.exports[model["world_model_export"] - 1]
    if pkg.class_name(exp) != "Model" or exp["size"] <= 0:
        raise ValueError("Original Level World Model export identity invalid")
    payload = pkg.payload(exp)
    frame = parse_world_model(payload, include_nodes=True)
    row = frame["node_records"][node]
    report = inspect_plane_bytes(pkg.data, export_offset=exp["offset"],
                                 export_size=exp["size"],
                                 node_start=row["start"], replacement=replacement)
    if (report["source_package_sha256"] != world.source_sha256
            or report["source_model_sha256"] != model["world_model_sha256"]
            or tuple(report["original_plane_float32"]) != model["nodes"][node]["plane"]):
        raise ValueError("Independent Model and source-byte provenance mismatch")
    world._check_original_unchanged()
    return {**report, "original_world_model_export": model["world_model_export"],
            "original_node_ordinal": node,
            "original_map": world.source.name,
            "limitations": [
                "Offsets identify original serialized Model plane bytes only.",
                "A hypothetical 16-byte replacement is not a valid BSP/collision edit.",
                "No original source files or native output packages are written.",
            ]}
