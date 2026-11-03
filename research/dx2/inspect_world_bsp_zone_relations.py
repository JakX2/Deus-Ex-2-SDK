#!/usr/bin/env python3
"""Read-only DX2 world BSP node-zone mask and symmetric zone relation audit.

This validates source-observed node zone indices, a subtree bitset OR
recurrence, and an independent 69-byte per-zone symmetric relation matrix.
It does NOT identify engine enum names, PVS/portal semantics or collision.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import struct
import sys

import inspect_world_bsp_tree_links as topology

SCHEMA = "DX2SDK-world-BSP-zone-mask-relations-v1"
ZONE_RECORD_SIZE = 69
ZONE_RELATION_MASK_OFFSET = 1
ZONE_MASK_BYTES = 32
ZONE_ONES_OFFSET = 33
ZONE_ONES_BYTES = 32
ZONE_TRAILER_OFFSET = 65
ZONE_TRAILER_BYTES = 4
MAX_EXAMPLES = 16


def inspect_zone_relations(payload: bytes, frame: dict, *,
                           include_zones: bool = False, include_nodes: bool = False) -> dict:
    """Validate all node masks against a rooted BSP graph and source zone table.

    Offset names are relative to each native Model's validated node record.
    A zone ID of zero is excluded from the node's *own* zone bits, because
    this convention is source-observed, not yet tied to an engine enum.
    """
    graph = topology.inspect_link_graph(payload, frame, include_edges=False)
    n = frame["candidate_node_count"]
    nz = frame["candidate_zone_count"]
    start = frame["candidate_zone_array_start"]
    if (type(nz) is not int or not 1 <= nz <= 256
            or type(start) is not int or start < 4
            or start + nz*ZONE_RECORD_SIZE + 8 != len(payload)):
        raise ValueError("Invalid or unsupported zone-record array extent")
    rows = [payload[start+i*ZONE_RECORD_SIZE:start+(i+1)*ZONE_RECORD_SIZE]
            for i in range(nz)]
    relation_masks = []
    first_byte_hist = Counter()
    for i, raw in enumerate(rows):
        if len(raw) != ZONE_RECORD_SIZE:
            raise ValueError(f"Truncated zone record {i}")
        if raw[ZONE_ONES_OFFSET:ZONE_ONES_OFFSET+ZONE_ONES_BYTES] != bytes([1])*32:
            raise ValueError(f"Zone record {i} has unfamiliar second 32-byte array")
        if raw[ZONE_TRAILER_OFFSET:ZONE_TRAILER_OFFSET+ZONE_TRAILER_BYTES] != bytes(4):
            raise ValueError(f"Zone record {i} has unexpected four-byte trailer")
        first_byte_hist[str(raw[0])] += 1
        mask = int.from_bytes(
            raw[ZONE_RELATION_MASK_OFFSET:ZONE_RELATION_MASK_OFFSET+ZONE_MASK_BYTES],
            "little")
        if mask >> nz:
            raise ValueError(f"Zone record {i} links outside the {nz}-zone array")
        if not mask & (1 << i):
            raise ValueError(f"Zone record {i} omits its own index bit")
        relation_masks.append(mask)
    undirected_edges = 0
    for a, mask in enumerate(relation_masks):
        for b in range(a+1, nz):
            ab = bool(mask & (1 << b))
            ba = bool(relation_masks[b] & (1 << a))
            if ab != ba:
                raise ValueError(f"Asymmetric zone relation between {a} and {b}")
            undirected_edges += int(ab)
    components = []
    seen = set()
    for root in range(nz):
        if root in seen:
            continue
        queue = deque([root])
        seen.add(root)
        size = 0
        while queue:
            i = queue.popleft()
            size += 1
            bits = relation_masks[i]
            while bits:
                bit = bits & -bits
                j = bit.bit_length()-1
                bits -= bit
                if j not in seen:
                    seen.add(j)
                    queue.append(j)
        components.append(size)
    if len(seen) != nz:
        raise ValueError("Zone graph traversal failed")

    masks = []
    zone_a_b = []
    links = []
    node_rows = []
    count = Counter()
    for i, record in enumerate(frame["node_records"]):
        offset, size = record["start"], record["length"]
        if (type(offset) is not int or type(size) is not int
                or not 0 <= offset < offset+size <= len(payload)
                or size not in topology.boundaries.OBSERVED_RECORD_LENGTHS):
            raise ValueError(f"Invalid source node record {i}")
        mask = int.from_bytes(payload[offset+16:offset+48], "little")
        if mask >> nz or mask & 1:
            raise ValueError(f"Node {i} zone-mask out of range or includes reserved bit 0")
        za, zb, vcount = struct.unpack_from("<HHB", payload, offset+size-21)
        if za >= nz or zb >= nz:
            raise ValueError(f"Node {i} zone fields out of bounds: {za}/{zb} >= {nz}")
        if not 3 <= vcount <= 32:
            raise ValueError(f"Node {i} unexpected native vertex count {vcount}")
        r = topology.boundaries.world.Cursor(
            payload, offset+48, offset+size-53)
        values = [r.ci() for _ in range(topology.FIELDS_PER_NODE)]
        if r.at != offset+size-53:
            raise ValueError(f"Node {i} compact fields do not fill their region")
        masks.append(mask)
        zone_a_b.append((za,zb))
        links.append([values[k] for k in topology.LINK_FIELDS])
        count["node_zone_fields"] += 1
        count["node_candidate_vertices"] += vcount
        if za > 0:
            count["nonzero_zone_a"] += 1
        if zb > 0:
            count["nonzero_zone_b"] += 1
        if za > 0 and zb > 0:
            count["both_nonzero_zones"] += 1
            if not (relation_masks[za] & (1 << zb)):
                raise ValueError(f"Node {i} has a zone pair absent from zone relation mask")
            count["both_nonzero_pairs_compatible_with_zone_relations"] += 1
        if include_nodes:
            node_rows.append({
                "node": i, "zone_a_u16": za, "zone_b_u16": zb,
                "vertex_count_byte": vcount,
                "zone_mask_set_bits": [j for j in range(nz) if mask & (1 << j)],
                "linked_children_compact_fields_3_4_5": links[-1],
            })

    # Not an approximate spatial correlation: an exact equality in each node
    # across all sampled DX2 maps, using the *already validated* root tree.
    for i, (za,zb) in enumerate(zone_a_b):
        own = (1 << za if za > 0 else 0) | (1 << zb if zb > 0 else 0)
        children = 0
        for child in links[i]:
            if child >= 0:
                if masks[i] & masks[child] != masks[child]:
                    raise ValueError(f"Node {i} does not include child {child}'s mask")
                children |= masks[child]
                count["verified_parent_child_zone_mask_subsets"] += 1
        if masks[i] != own | children:
            raise ValueError(f"Node {i} zone mask does not equal own bits OR child masks")
        count["exact_zone_mask_subtree_recurrence"] += 1

    result = {
        "status": "validated_symmetric_zone_relations_and_node_subtree_masks",
        "zones": nz,
        "zone_relation_bit_width": 256,
        "zone_record_bytes": ZONE_RECORD_SIZE,
        "zone_relation_self_bits": nz,
        "zone_relation_symmetric_directed_offdiagonal_bits": 2*undirected_edges,
        "zone_relation_undirected_edges": undirected_edges,
        "zone_relation_graph_components": len(components),
        "zone_relation_component_sizes_descending": sorted(components, reverse=True),
        "zone_first_byte_histogram": dict(sorted(first_byte_hist.items(),key=lambda x:int(x[0]))),
        "zone_second_32_bytes_all_01": True,
        "zone_final_four_bytes_all_zero": True,
        "rooted_node_graph_validated": graph["all_nodes_reachable"],
        "nodes": n,
        **dict(count),
        "candidate_zone_field_offsets_from_node_end": [-21,-19],
        "candidate_vertex_count_offset_from_node_end": -17,
        "node_zone_mask_offset_from_node_start": 16,
        **({"zone_relation_lists": [
            {"zone":i,"related_zones":[j for j in range(nz) if mask & (1 << j)],
             "leading_byte_unknown":rows[i][0]}
            for i,mask in enumerate(relation_masks)]} if include_zones else {}),
        **({"node_zone_records": node_rows} if include_nodes else {}),
    }
    if result["exact_zone_mask_subtree_recurrence"] != n:
        raise ValueError("Incomplete node zone-mask verification")
    if result["verified_parent_child_zone_mask_subsets"] != n-1:
        raise ValueError("Node mask subset count does not agree with rooted tree")
    return result


def audit_map(path: Path, *, include_zones=False, include_nodes=False) -> dict:
    path = Path(path)
    if (path.suffix.lower() != ".gmp" or not path.is_file()
            or path.stat().st_size > topology.boundaries.world.MAX_MAP_BYTES):
        raise ValueError("Expected an existing user-owned DX2 .gmp within size limit")
    pkg = topology.boundaries.world.Package(path)
    if pkg.version != 95 or pkg.licensee not in topology.boundaries.world.OBSERVED_LICENSEES:
        raise ValueError("Expected observed UE95 DX2 licensee 65/67/68/69")
    world_ref = topology.boundaries.world._parse_world_model(pkg)["world_model_export_ref"]
    model = pkg.exports[world_ref-1]
    payload = pkg.payload(model)
    frame = topology.boundaries.parse_world_model(payload, include_nodes=True)
    result = inspect_zone_relations(payload,frame,
                                    include_zones=include_zones,
                                    include_nodes=include_nodes)
    return {
        "file": path.name,
        "source_sha256": hashlib.sha256(pkg.data).hexdigest(),
        "world_model_export": world_ref,
        "world_model_sha256": hashlib.sha256(payload).hexdigest(),
        "licensee": pkg.licensee,
        **result,
    }


def audit_maps(paths, *, include_zones=False, include_nodes=False) -> dict:
    if not 1 <= len(paths) <= topology.boundaries.world.MAX_MAPS:
        raise ValueError("Provide between 1 and 64 user-owned GMPs")
    inputs = [Path(p).resolve() for p in paths]
    if len(set(inputs)) != len(inputs):
        raise ValueError("Duplicate original map paths")
    maps = [audit_map(path,include_zones=include_zones,include_nodes=include_nodes)
            for path in inputs]
    totals = Counter()
    for row in maps:
        totals["maps"] += 1
        for field in ("zones", "nodes", "zone_relation_undirected_edges",
                      "zone_relation_graph_components",
                      "zone_relation_symmetric_directed_offdiagonal_bits",
                      "exact_zone_mask_subtree_recurrence",
                      "verified_parent_child_zone_mask_subsets",
                      "both_nonzero_pairs_compatible_with_zone_relations",
                      "both_nonzero_zones", "node_candidate_vertices"):
            totals[field] += row[field]
    return {
        "schema": SCHEMA, "read_only": True, "native_gmp_written": False,
        "native_zones_rebuilt": False, "collision_or_pvs_decoded": False,
        "runtime_verified": False, "summary": dict(totals), "maps": maps,
        "limitations": [
            "The 69-byte zone record relation bitset is symmetric, reflexive and bounded; exact engine semantics unproven.",
            "Node zone_a and zone_b at tail offsets -21/-19 are source-observed uint16 indices.",
            "Zero is excluded from own-node zone bits; this is observed and is not an authenticated enum name.",
            "Node subtree zone masks are exact bitwise ORs of nonzero own zones and fields 3/4/5 child masks.",
            "The second 32-byte all-ones array, leading byte and four-byte zero zone trailer remain semantically opaque.",
            "This is not PVS, portals, collision, a DX2 world compiler or native map writing.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-zones", action="store_true",
                        help="Include per-zone bitset connection lists")
    parser.add_argument("--include-node-zones", action="store_true",
                        help="Include per-node zone indices/mask bits (large reports)")
    args = parser.parse_args(argv)
    try:
        report = audit_maps(args.maps,include_zones=args.include_zones,
                            include_nodes=args.include_node_zones)
        if args.report:
            topology.boundaries.world.write_report(report,args.report,args.maps)
            print(json.dumps({"status":"ok","report":str(args.report),
                              "summary":report["summary"]},indent=2))
        else:
            print(json.dumps(report,indent=2,allow_nan=False))
        return 0
    except (OSError, ValueError, IndexError, KeyError, OverflowError, struct.error) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}),file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
