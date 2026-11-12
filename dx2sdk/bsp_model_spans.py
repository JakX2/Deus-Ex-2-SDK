"""Complete source-byte span ledger for original DX2 compiled World Models.

Read-only: the ledger accounts for every byte from original source framing,
preserves unknown fields without assigning fictitious surface/vertex meanings,
and refuses overlaps, holes, malformed compact integers and failed no-op
serialization. No modified Model or GMP bytes are ever produced or persisted.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import struct

from dx2inspect import Cursor
from inspect_world_bsp_node_boundaries import parse_world_model, ZONE_RECORD_BYTES
from .bsp_model_noop import reassemble_original_world_model
from .bsp_trace import _load_model

SCHEMA = "DX2SDK-original-World-Model-complete-byte-span-ledger-v1"
MAX_NODE_EXAMPLES = 12
MAX_ZONE_EXAMPLES = 8

# Certainty is about framing and source observations, NEVER write safety.
OBSERVED = "source_observed_byte_layout"
HYPOTHESIS = "candidate_field_meaning"
OPAQUE = "opaque_original_source_bytes"


def _selected_nodes(indices: object, count: int) -> list[int]:
    if indices is None:
        return []
    if (not isinstance(indices, (list, tuple))
            or len(indices) > MAX_NODE_EXAMPLES
            or any(type(index) is not int or not 0 <= index < count
                   for index in indices)
            or len(set(indices)) != len(indices)):
        raise ValueError("Select at most 12 unique original BSP node ordinals")
    return list(indices)


def build_original_model_span_ledger(
    payload: bytes, *, node_indices: object = None,
) -> dict:
    """Verify byte-by-byte structural coverage against v0.76's independent no-op.

    Source spans are lossless and nonoverlapping in original serialized order.
    Compact-index *widths* are observed, not normalized by re-encoding.
    The role statistics emit only counts and hashes, not proprietary bytes.
    """
    reconstructed, baseline = reassemble_original_world_model(payload)
    if (reconstructed != payload
            or not baseline["model_reassembled_byte_identical"]):
        raise ValueError("Original World Model byte-exact baseline unavailable")
    frame = parse_world_model(payload, include_nodes=True)
    n = frame["candidate_node_count"]
    selected = _selected_nodes(node_indices, n)
    selected_set = set(selected)
    examples: dict[int, list[dict]] = {index: [] for index in selected}
    zone_examples = []
    role_hashers: dict[str, object] = {}
    role_stats: dict[str, dict] = {}
    class_bytes: dict[str, int] = defaultdict(int)
    class_spans: dict[str, int] = defaultdict(int)
    expected = 0
    emitted = 0

    def add(offset: int, length: int, role: str, certainty: str,
            *, node: int | None = None, zone: int | None = None) -> None:
        nonlocal expected, emitted
        if (type(offset) is not int or type(length) is not int
                or offset != expected or length <= 0
                or offset + length > len(payload)
                or certainty not in (OBSERVED, HYPOTHESIS, OPAQUE)):
            raise ValueError("Original World Model source span overlap, gap or overflow")
        chunk = payload[offset:offset+length]
        if role not in role_stats:
            role_stats[role] = {
                "certainty": certainty,
                "span_count": 0,
                "total_bytes": 0,
                "nonzero_original_bytes": 0,
            }
            role_hashers[role] = hashlib.sha256()
        if role_stats[role]["certainty"] != certainty:
            raise ValueError("Original source role assigned contradictory certainty")
        s = role_stats[role]
        s["span_count"] += 1
        s["total_bytes"] += length
        s["nonzero_original_bytes"] += sum(byte != 0 for byte in chunk)
        role_hashers[role].update(chunk)
        class_bytes[certainty] += length
        class_spans[certainty] += 1
        emitted += 1
        expected = offset + length
        if node in selected_set:
            examples[node].append({
                "role": role, "certainty": certainty,
                "original_model_relative_offset": offset, "byte_count": length,
                "source_span_sha256": hashlib.sha256(chunk).hexdigest(),
                "native_writer_permission": False,
            })
        if zone is not None and zone < MAX_ZONE_EXAMPLES:
            zone_examples.append({
                "zone_ordinal": zone, "role": role, "certainty": certainty,
                "original_model_relative_offset": offset, "byte_count": length,
            })

    add(0, 9, "header.opaque_empty_bounds_prefix", OPAQUE)
    add(9, 24, "header.zero_bound_candidate_f32_bits", HYPOTHESIS)
    add(33, 1, "header.observed_zero_u8", OBSERVED)
    add(34, 16, "header.zero_sphere_candidate_f32_bits", HYPOTHESIS)
    node_array_start = frame["node_array_start"]
    add(50, node_array_start-50, "header.node_count_raw_compact", OBSERVED)
    compact_field_bytes = 0
    node_bytes = 0
    for ordinal, record in enumerate(frame["node_records"]):
        start, size = record["start"], record["length"]
        if (start != expected or size < 109 or
                ordinal != record["ordinal"] or
                start + size > frame["node_array_end"]):
            raise ValueError("Original World Model framed node disagrees with byte ledger")
        add(start, 16, "node.candidate_plane_f32_bits", HYPOTHESIS, node=ordinal)
        add(start+16, 32, "node.subtree_zone_mask_bits", OBSERVED, node=ordinal)
        cursor = Cursor(payload, start+48, start+size-53)
        for field in range(8):
            field_start = cursor.at
            value = cursor.ci()
            length = cursor.at - field_start
            if not 1 <= length <= 5:
                raise ValueError("Original native Model compact index width invalid")
            if field in (3, 4, 5):
                certainty = OBSERVED  # rooted graph edges; member names still provisional
            else:
                certainty = OPAQUE  # numeric field role is not engine authenticated
            add(field_start, length, f"node.compact_field_{field}", certainty,
                node=ordinal)
            compact_field_bytes += length
        spatial_start = start+size-53
        if cursor.at != spatial_start:
            raise ValueError("Original World Model compact fields shifted against spatial bytes")
        add(spatial_start, 16, "node.opaque_spatial_f32_bits", OPAQUE, node=ordinal)
        add(spatial_start+16, 16, "node.opaque_spatial_reserved", OPAQUE, node=ordinal)
        za_start = start+size-21
        za, zb, vc = struct.unpack_from("<HHB", payload, za_start)
        if not 3 <= vc <= 32:
            raise ValueError("Native node vertex slot count outside source-validated bounds")
        add(za_start, 2, "node.zone_candidate_a_u16", OBSERVED, node=ordinal)
        add(za_start+2, 2, "node.zone_candidate_b_u16", OBSERVED, node=ordinal)
        add(za_start+4, 1, "node.vertex_slot_count_u8", OBSERVED, node=ordinal)
        end_suffix = start+size-16
        add(end_suffix, 4, "node.opaque_bounded_i32_0", OPAQUE, node=ordinal)
        add(end_suffix+4, 4, "node.opaque_bounded_i32_1", OPAQUE, node=ordinal)
        add(end_suffix+8, 4, "node.observed_zero_u32", OBSERVED, node=ordinal)
        add(end_suffix+12, 4, "node.opaque_last_u32", OPAQUE, node=ordinal)
        if expected != start+size:
            raise ValueError("Original native Model node spans do not fill record")
        node_bytes += size
    if (expected != frame["node_array_end"]
            or compact_field_bytes != baseline["original_node_compact_field_bytes"]
            or node_bytes != frame["node_array_bytes"]):
        raise ValueError("Native BSP array or compact field byte count differs from v0.76")
    add(expected, 4, "zone_table.count_u32", OBSERVED)
    zone_start = frame["candidate_zone_array_start"]
    count = frame["candidate_zone_count"]
    if expected != zone_start:
        raise ValueError("Original zone count did not reach source table boundary")
    for zone in range(count):
        base = zone_start + zone*ZONE_RECORD_BYTES
        add(base, 1, "zone_record.opaque_leading_u8", OPAQUE, zone=zone)
        add(base+1, 32, "zone_record.sourced_relation_mask_bits", OBSERVED,
            zone=zone)
        add(base+33, 32, "zone_record.observed_01_padding", OBSERVED,
            zone=zone)
        add(base+65, 4, "zone_record.observed_zero_trailer", OBSERVED,
            zone=zone)
    add(expected, 8, "model.observed_zero_trailer_8", OBSERVED)
    if (expected != len(payload) or
            sum(class_bytes.values()) != len(payload) or
            sum(class_spans.values()) != emitted or
            sum(stat["total_bytes"] for stat in role_stats.values())
            != len(payload)):
        raise ValueError("Original Model byte ledger has gaps, overlaps or missing classes")
    class_fraction = {kind: value / len(payload)
                      for kind, value in sorted(class_bytes.items())}
    summarized = {role: {**stat,
                         "concatenated_source_span_sha256":
                             role_hashers[role].hexdigest()}
                  for role, stat in sorted(role_stats.items())}
    if (n != baseline["source_node_count"]
            or count != baseline["source_zone_count"]
            or baseline["source_model_sha256"] != hashlib.sha256(payload).hexdigest()):
        raise ValueError("Independent native World Model no-op identity disagreeing")
    return {
        "schema": SCHEMA,
        "status": "read-only-original-World-Model-complete-byte-ledger",
        "original_model_sha256": baseline["source_model_sha256"],
        "original_model_byte_length": len(payload),
        "original_source_node_count": n,
        "original_source_zone_count": count,
        "original_node_array_start": node_array_start,
        "original_node_array_end": frame["node_array_end"],
        "original_zone_table_start": zone_start,
        "source_node_record_bytes": node_bytes,
        "source_compact_integer_field_bytes": compact_field_bytes,
        "model_byte_ledger_fully_contiguous_nonoverlapping": True,
        "original_model_noop_reassembled_byte_identical": True,
        "total_nonoverlapping_source_spans": emitted,
        "byte_class_totals": dict(sorted(class_bytes.items())),
        "byte_class_span_totals": dict(sorted(class_spans.items())),
        "byte_class_fractions": class_fraction,
        "role_byte_statistics": summarized,
        "selected_original_node_ordinals": selected,
        "selected_node_source_spans": [
            {"node": index, "original_native_model_record":
                {"start": frame["node_records"][index]["start"],
                 "byte_count": frame["node_records"][index]["length"]},
             "spans": examples[index]}
            for index in selected],
        "first_zone_source_spans": zone_examples,
        "source_model_bytes_without_framing": 0,
        "source_surface_array_indexed_from_model_authenticated": False,
        "engine_field_names_authenticated": False,
        "native_edited_BSP_or_MOPP_writer_enabled": False,
        "source_gmp_modified": False,
        "retail_game_runtime_verified": False,
    }


def inspect_original_model_span_ledger(world, node_indices: object = None) -> dict:
    """Source-GMP SHA checked immutable original Model ledger, no file output."""
    world._check_original_unchanged()
    model = _load_model(world)
    pkg = world._package
    if hashlib.sha256(pkg.data).hexdigest() != world.source_sha256:
        raise ValueError("Original GMP changed after DX2Map opened")
    reference = model["world_model_export"]
    if (type(reference) is not int or not 1 <= reference <= len(pkg.exports)
            or pkg.class_name(pkg.exports[reference-1]) != "Model"):
        raise ValueError("Original Model reference no longer matches Level")
    record = pkg.exports[reference-1]
    offset, length = record["offset"], record["size"]
    if (type(offset) is not int or type(length) is not int
            or offset < 0 or length < 100 or length > len(pkg.data)-offset):
        raise ValueError("Original GMP Model export byte bounds invalid")
    original = pkg.payload(record)
    if (original != pkg.data[offset:offset+length]
            or hashlib.sha256(original).hexdigest() != model["world_model_sha256"]):
        raise ValueError("Original GMP exported World Model bytes changed")
    report = build_original_model_span_ledger(original, node_indices=node_indices)
    if report["original_model_sha256"] != model["world_model_sha256"]:
        raise ValueError("Independent World Model byte ledger SHA-256 mismatch")
    for node in report["selected_node_source_spans"]:
        for span in node["spans"]:
            span["original_gmp_absolute_offset"] = (
                offset + span["original_model_relative_offset"])
    world._check_original_unchanged()
    return {
        **report,
        "source_map": world.source.name,
        "original_gmp_sha256": world.source_sha256,
        "original_model_export": reference,
        "original_model_absolute_offset_in_gmp": offset,
        "original_source_modified": False,
        "limitations": [
            "The structural ledger assigns one read-only span to every byte, not editable semantics.",
            "An opaque byte range may contain meaningful engine data; zero unframed bytes is not absence of surfaces.",
            "Candidate native field names or Model/Level links are not engine-authenticated surface references.",
            "No native BSP/CSG, Havok/MOPP, zone or Actor Region writer; no retail game test.",
        ],
    }
