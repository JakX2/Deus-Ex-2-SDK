"""Read-only source-authenticated original DX2 World BSP node dossier.

Original source-framed plane and compact-field bytes are surfaced in bounded
metadata for Godot. Compact field names 1/2/6/7 remain strictly UNKNOWN.
This is not a native BSP vertex, surface, material, UV or collision decoder,
and cannot write or mutate GMP/IBD, Model, Havok/MOPP or DX2 assets.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Any

from dx2inspect import Cursor
from inspect_world_bsp_node_boundaries import parse_world_model
from .bsp_model_spans import build_original_model_span_ledger
from .bsp_trace import _load_model

SCHEMA = "DX2SDK-original-BSP-source-node-dossier-v1"
MAX_NODES = 20_000


def inspect_model_node_bytes(payload: bytes, node_index: int) -> dict:
    """Inspect ONE original node only after full span/no-op/tree validation."""
    if type(node_index) is not int or not 0 <= node_index < MAX_NODES:
        raise ValueError("Original BSP node ordinal must be in 0..19999")
    if type(payload) is not bytes:
        raise ValueError("Original World Model payload must be immutable bytes")
    # Strict ledger invokes full original Model reassembly, tree and zone
    # validation. Never reconstruct/emit a modified native node record.
    ledger = build_original_model_span_ledger(payload, node_indices=[node_index])
    frame = parse_world_model(payload, include_nodes=True)
    count = frame["candidate_node_count"]
    if (not 1 <= count <= MAX_NODES or node_index >= count
        or ledger["original_source_node_count"] != count
        or ledger["original_source_zone_count"] != frame["candidate_zone_count"]
        or not ledger["model_byte_ledger_fully_contiguous_nonoverlapping"]
        or not ledger["original_model_noop_reassembled_byte_identical"]
        or ledger["source_model_bytes_without_framing"] != 0):
        raise ValueError("Native Model source/node boundary evidence disagrees")
    node = frame["node_records"][node_index]
    start, length = node["start"], node["length"]
    if type(start) is not int or type(length) is not int or not (
        frame["node_array_start"] <= start and 109 <= length <= 116
        and start + length <= frame["node_array_end"]):
        raise ValueError("Original BSP node source bounds invalid")
    cursor = Cursor(payload, start + 48, start + length - 53)
    fields, offsets, widths = [], [], []
    for _ in range(8):
        pos = cursor.at
        value = cursor.ci()
        fields.append(value)
        offsets.append(pos)
        widths.append(cursor.at - pos)
    if (cursor.at != start + length - 53
        or any(not 1 <= width <= 5 for width in widths)):
        raise ValueError("Original source compact indices do not match frame")
    plane = struct.unpack_from("<4f", payload, start)
    if (any(not math.isfinite(x) for x in plane)
        or abs(sum(float(x)*float(x) for x in plane[:3]) - 1.) > .002):
        raise ValueError("Native node plane is not source-normalized")
    zone_a, zone_b, vertices = struct.unpack_from(
        "<HHB", payload, start + length - 21)
    if not 3 <= vertices <= 32:
        raise ValueError("Original BSP node vertex count outside bounds")
    samples = ledger["selected_node_source_spans"]
    if len(samples) != 1 or samples[0]["node"] != node_index:
        raise ValueError("Native source byte ledger did not select original node")
    spans = samples[0]["spans"]
    if (len(spans) != 21
        or sum(span["byte_count"] for span in spans) != length
        or spans[0]["original_model_relative_offset"] != start
        or spans[-1]["original_model_relative_offset"] + 4 != start + length
        or [span["original_model_relative_offset"] for span in spans[2:10]]
            != offsets
        or [span["byte_count"] for span in spans[2:10]] != widths):
        raise ValueError("Native BSP node compact/byte span provenance disagrees")
    return {
        "schema": SCHEMA,
        "status": "source-original-read-only-node-structure",
        "original_model_sha256": ledger["original_model_sha256"],
        "original_model_byte_length": len(payload),
        "original_node_count": count,
        "original_zone_record_count": frame["candidate_zone_count"],
        "original_node_ordinal": node_index,
        "native_model_node_offset": start,
        "native_model_node_record_bytes": length,
        "candidate_plane_source_f32": list(plane),
        "raw_compact_fields": fields,
        "raw_compact_offsets_in_model": offsets,
        "raw_compact_byte_widths": widths,
        "source_candidate_zone_u16": [zone_a, zone_b],
        "source_polygon_vertex_slot_count_u8": vertices,
        "node_source_spans": spans,
        "original_model_exact_noop_verified": True,
        "original_model_full_span_ledger_verified": True,
        "compact_field2_native_surface_id_authenticated": False,
        "native_vertex_xyz_pool_recovered": False,
        "native_surface_material_uv_binding_verified": False,
        "native_BSP_or_Havok_collision_writer_enabled": False,
        "retail_runtime_verified": False,
    }


def inspect_original_bsp_node_dossier(world: Any, node_index: int) -> dict:
    """Source-GMP-identity gate for original Level→World Model node metadata."""
    world._check_original_unchanged()
    model = _load_model(world)
    pkg = world._package
    if hashlib.sha256(pkg.data).hexdigest() != world.source_sha256:
        raise ValueError("Original GMP in-memory data SHA-256 changed")
    ref = model["world_model_export"]
    if (type(ref) is not int or not 1 <= ref <= len(pkg.exports)
        or pkg.class_name(pkg.exports[ref-1]) != "Model"):
        raise ValueError("Original Level World Model reference invalid")
    exp = pkg.exports[ref-1]
    offset, size = exp["offset"], exp["size"]
    if (type(offset) is not int or type(size) is not int
        or offset < 0 or size < 100 or size > len(pkg.data)-offset):
        raise ValueError("Original GMP Model export exceeds source file")
    payload = pkg.payload(exp)
    if (payload != pkg.data[offset:offset+size]
        or hashlib.sha256(payload).hexdigest() != model["world_model_sha256"]):
        raise ValueError("Model source bytes disagree with native GMP export")
    report = inspect_model_node_bytes(payload, node_index)
    if (report["original_node_count"] != model["node_count"]
        or report["original_model_sha256"] != model["world_model_sha256"]):
        raise ValueError("Native Model node evidence disagrees across validators")
    world._check_original_unchanged()
    return {
        **report,
        "source_map": world.source.name,
        "source_gmp_sha256": world.source_sha256,
        "world_model_export": ref,
        "source_gmp_model_absolute_offset": offset,
        "source_gmp_node_absolute_offset": offset + report["native_model_node_offset"],
        "original_source_gmp_modified": False,
        "limitations": [
            "The original World Model node plane is source-observed float32, not a rendered surface polygon.",
            "Compact field 2 is an unproven surface index candidate, never an authenticated iSurf.",
            "No native BSP polygon vertex XYZ array or material/UV bindings have been recovered.",
            "No compiled native BSP/CSG changes, collision cooking, GMP writes or runtime verification.",
        ],
    }
