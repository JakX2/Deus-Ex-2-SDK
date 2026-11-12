"""Byte-exact, no-op decomposition/reassembly of ORIGINAL DX2 World Model payload.

The result is always byte-identical to the original source. This is a
serialization *baseline*, not permission to change World BSP planes,
topology, surfaces, zone tables, collision, or native GMP packages.

Only source-observed node/zone structure is typed. All opaque bytes and
float32 bit-patterns are preserved exactly, including noncanonical but
source-decodable compact integer encodings.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import struct

from dx2inspect import Cursor
from inspect_world_bsp_node_boundaries import (
    parse_world_model, ZONE_RECORD_BYTES, ZONE_TRAILER_BYTES,
)
from inspect_world_bsp_zone_relations import inspect_zone_relations
from .bsp_trace import _load_model

SCHEMA = "DX2SDK-original-World-Model-structural-noop-reassembly-v1"
HEADER_BYTES = 50
NODE_PREFIX_PLANE_BYTES = 16
NODE_ZONE_MASK_BYTES = 32
NODE_COMPACT_FIELDS = 8
NODE_SPATIAL_OPAQUE_BYTES = 16
NODE_RESERVED_OPAQUE_BYTES = 16
NODE_ZONE_AND_VERTEX_BYTES = 5
NODE_SUFFIX_BYTES = 16
NODE_FIXED_BYTES = (NODE_PREFIX_PLANE_BYTES + NODE_ZONE_MASK_BYTES
                    + NODE_SPATIAL_OPAQUE_BYTES + NODE_RESERVED_OPAQUE_BYTES
                    + NODE_ZONE_AND_VERTEX_BYTES + NODE_SUFFIX_BYTES)
MAX_MODEL_BYTES = 16 * 1024 * 1024


def reassemble_original_world_model(payload: bytes) -> tuple[bytes, dict]:
    """Reconstruct known source fields and retain all unknown bytes verbatim.

    The independent original BSP and zone decoders must accept the complete
    payload before the caller receives any reassembled bytes.
    """
    if type(payload) is not bytes or not 100 <= len(payload) <= MAX_MODEL_BYTES:
        raise ValueError("Original immutable World Model payload exceeds size bounds")
    source_hash = hashlib.sha256(payload).hexdigest()
    frame = parse_world_model(payload, include_nodes=True)
    graph = inspect_zone_relations(payload, frame)
    if (graph["rooted_node_graph_validated"] is not True
            or graph["exact_zone_mask_subtree_recurrence"] != frame["candidate_node_count"]
            or graph["verified_parent_child_zone_mask_subsets"]
            != frame["candidate_node_count"]-1):
        raise ValueError("Original World Model topology or zone-mask proof absent")
    start = frame["node_array_start"]
    if (start <= HEADER_BYTES or start >= len(payload)
            or frame["candidate_node_count_width"] != start-HEADER_BYTES):
        raise ValueError("Original World Model compact node-count source boundary shifted")
    count_source = payload[HEADER_BYTES:start]
    c = Cursor(count_source)
    if c.ci() != frame["candidate_node_count"] or c.at != len(count_source):
        raise ValueError("Original node-count compact encoding does not decode exactly")
    header = payload[:HEADER_BYTES]
    rebuilt_parts = [header, count_source]
    cursor_offset = start
    field_widths = Counter()
    record_lengths = Counter()
    reserved_nonzero = 0
    raw_compact_bytes = 0
    first_fields = []
    for ordinal, record in enumerate(frame["node_records"]):
        node_start, length = record["start"], record["length"]
        end = node_start+length
        if (node_start != cursor_offset or length < NODE_FIXED_BYTES+NODE_COMPACT_FIELDS
                or end > len(payload)
                or record["ordinal"] != ordinal):
            raise ValueError("Original Model node source records not contiguous or malformed")
        data = payload[node_start:end]
        plane_bytes = data[:16]
        zone_mask_raw = data[16:48]
        zone_mask = int.from_bytes(zone_mask_raw, "little")
        compact_end = length-53
        fields = Cursor(data, 48, compact_end)
        encoded_fields = []
        values = []
        for field_id in range(NODE_COMPACT_FIELDS):
            field_start = fields.at
            values.append(fields.ci())
            raw = data[field_start:fields.at]
            if not 1 <= len(raw) <= 5:
                raise ValueError("Original Model compact integer field width unsupported")
            encoded_fields.append(raw)
            field_widths[str(len(raw))] += 1
            raw_compact_bytes += len(raw)
        if fields.at != compact_end or sum(map(len, encoded_fields)) != length-NODE_FIXED_BYTES:
            raise ValueError("Eight native compact fields do not fill original Model node")
        if ordinal < 12:
            first_fields.append({
                "node": ordinal,
                "original_node_start_in_model": node_start,
                "original_record_length": length,
                "original_field2_offset_in_model": node_start + 48
                    + sum(len(encoded_fields[i]) for i in range(2)),
                "source_field2_raw": values[2],
                "original_compact_field_widths": [len(value) for value in encoded_fields],
            })
        # The original floating-point bits are retained, not decoded and
        # re-quantized to new float32 values. Spatial field semantics are
        # unknown and must not be renamed or made writable.
        spatial_opaque = data[compact_end:compact_end+NODE_SPATIAL_OPAQUE_BYTES]
        reserved = data[compact_end+NODE_SPATIAL_OPAQUE_BYTES:
                        compact_end+NODE_SPATIAL_OPAQUE_BYTES+NODE_RESERVED_OPAQUE_BYTES]
        reserved_nonzero += sum(byte != 0 for byte in reserved)
        zones_at = length-21
        zone_a, zone_b, vcount = struct.unpack_from("<HHB", data, zones_at)
        backref_a, backref_b, zero_word, opaque_word = struct.unpack_from(
            "<iiII", data, length-NODE_SUFFIX_BYTES)
        # Structurally rebuild the identified integer and zone-mask fields.
        # Unknown 16-byte source regions remain exactly as found.
        emitted = (
            plane_bytes + zone_mask.to_bytes(NODE_ZONE_MASK_BYTES, "little")
            + b"".join(encoded_fields) + spatial_opaque + reserved
            + struct.pack("<HHB", zone_a, zone_b, vcount)
            + struct.pack("<iiII", backref_a, backref_b, zero_word, opaque_word)
        )
        if len(emitted) != length or emitted != data:
            raise ValueError(f"Original Model node {ordinal} did not reassemble byte-exactly")
        record_lengths[str(length)] += 1
        rebuilt_parts.append(emitted)
        cursor_offset = end
    if (cursor_offset != frame["node_array_end"]
            or cursor_offset+4 != frame["candidate_zone_array_start"]):
        raise ValueError("Original node-record array does not meet zone-count framing")
    count = frame["candidate_zone_count"]
    rebuilt_parts.append(struct.pack("<I", count))
    zone_start = frame["candidate_zone_array_start"]
    zone_end = zone_start+count*ZONE_RECORD_BYTES
    if zone_end+ZONE_TRAILER_BYTES != len(payload):
        raise ValueError("Original Model zone table/trailer escaped source payload")
    zone_leading_hist = Counter()
    for zone in range(count):
        at = zone_start+zone*ZONE_RECORD_BYTES
        original = payload[at:at+ZONE_RECORD_BYTES]
        leading = original[0]
        relation = int.from_bytes(original[1:33], "little")
        emitted = (
            bytes((leading,)) + relation.to_bytes(32, "little")
            + bytes((1,))*32 + bytes(4)
        )
        if len(emitted) != ZONE_RECORD_BYTES or original != emitted:
            raise ValueError("Original Model source zone record failed reassembly")
        zone_leading_hist[str(leading)] += 1
        rebuilt_parts.append(emitted)
    original_tail = payload[zone_end:]
    if original_tail != bytes(ZONE_TRAILER_BYTES):
        raise ValueError("Original native Model zero trailer differs from source")
    rebuilt_parts.append(bytes(ZONE_TRAILER_BYTES))
    rebuilt = b"".join(rebuilt_parts)
    if rebuilt != payload or hashlib.sha256(rebuilt).hexdigest() != source_hash:
        raise ValueError("Reassembled original World Model is not byte-identical")
    if sum(map(len, rebuilt_parts)) != len(payload):
        raise ValueError("Original World Model structural spans do not cover all bytes")
    # Reparse the in-memory bytes with the *independent* original validators.
    check = parse_world_model(rebuilt, include_nodes=False)
    if (check["candidate_node_count"] != frame["candidate_node_count"]
            or check["candidate_zone_count"] != count
            or check["node_record_lengths"] != dict(record_lengths)
            or check["everything_in_model_payload_accounted_for"] is not True):
        raise ValueError("Reassembled World Model framing disagrees with original reader")
    return rebuilt, {
        "schema": SCHEMA,
        "status": "original-World-Model-byte-identical-structural-noop",
        "source_model_sha256": source_hash,
        "reassembled_model_sha256": hashlib.sha256(rebuilt).hexdigest(),
        "original_model_bytes": len(payload),
        "source_node_count": frame["candidate_node_count"],
        "source_zone_count": count,
        "node_record_length_histogram": dict(sorted(record_lengths.items())),
        "compact_integer_width_histogram": dict(sorted(field_widths.items())),
        "original_node_count_compact_width": len(count_source),
        "original_node_compact_field_bytes": raw_compact_bytes,
        "source_reserved_nonzero_bytes_preserved": reserved_nonzero,
        "zone_leading_byte_histogram": dict(sorted(zone_leading_hist.items())),
        "first_source_node_compact_field_offsets": first_fields,
        "all_source_bytes_accounted_for": True,
        "model_reassembled_byte_identical": True,
        "source_original_f32_bits_preserved_without_requantization": True,
        "source_compact_index_byte_encodings_preserved": True,
        "opaque_source_regions_preserved": True,
        "native_modified_model_writer_enabled": False,
        "native_BSP_surface_or_vertex_pool_recovered": False,
        "native_collision_or_BSP_rebuild_implemented": False,
        "runtime_verified": False,
    }


def inspect_original_world_model_noop(world) -> dict:
    """Read-only DX2Map source-bound no-op reconstruction, no file writes."""
    world._check_original_unchanged()
    model = _load_model(world)
    pkg = world._package
    if hashlib.sha256(pkg.data).hexdigest() != world.source_sha256:
        raise ValueError("Original opened GMP bytes differ from pinned source")
    export = model["world_model_export"]
    if (type(export) is not int or not 1 <= export <= len(pkg.exports)
            or pkg.class_name(pkg.exports[export-1]) != "Model"):
        raise ValueError("Original Level World Model reference changed")
    record = pkg.exports[export-1]
    at, size = record["offset"], record["size"]
    if (type(at) is not int or type(size) is not int
            or at < 0 or size < 100 or size > len(pkg.data)-at):
        raise ValueError("Original native Model source byte envelope malformed")
    original = pkg.payload(record)
    if (original != pkg.data[at:at+size]
            or hashlib.sha256(original).hexdigest() != model["world_model_sha256"]):
        raise ValueError("Original exported Model does not match source GMP")
    rebuilt, report = reassemble_original_world_model(original)
    if rebuilt != original:
        raise ValueError("In-memory native Model no-op unexpectedly changed bytes")
    world._check_original_unchanged()
    return {
        **report, "source_gmp_sha256": world.source_sha256,
        "source_map": world.source.name,
        "original_world_model_export": export,
        "original_world_model_absolute_offset_in_gmp": at,
        "original_world_model_export_length": size,
        "original_game_package_modified": False,
        "limitations": [
            "This is a byte-identical original-Model no-op only; no edited Model payload is supported.",
            "Node float32 source bits, compact index bytes and opaque regions are preserved exactly.",
            "Actual original BSP surfaces/vertex XYZ, CSG builder, collision cooker and Region writer remain unknown.",
            "No original GMP file, collision system, or retail game runtime was modified.",
        ],
    }
