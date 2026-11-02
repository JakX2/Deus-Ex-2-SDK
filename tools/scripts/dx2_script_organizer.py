#!/usr/bin/env python3
"""Read the original ASCII ScriptOrganizer.tso hierarchy without guessing links.

TSO version 2 has three successive HeaderBegin trees:
  0: script source filenames (Defs/*.tsd stems)
  1: condition symbol names (kTCT_*)
  2: action symbol names (kTAT_*)
Each tree uses explicit counts, nested '0' folder records and '1' leaf
records. These are *organizer categories*, not runtime graph edges.
"""
from __future__ import annotations

from collections import Counter

SCHEMA = "DX2Ed-script-organizer-v1"
TREE_KINDS = ("scripts", "conditions", "actions")
MAX_LINES = 120000
MAX_DEPTH = 20
MAX_ENTRIES = 20000


def parse_organizer(blob: bytes) -> dict:
    """Decode and validate the entire original organizer, including EOF."""
    if len(blob) > 2 * 1024 * 1024:
        raise ValueError("Organizer exceeds size limit")
    try:
        lines = blob.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError("Expected ASCII TSO organizer") from error
    if len(lines) > MAX_LINES or len(lines) < 5 or lines[0] != "2":
        raise ValueError("Unsupported ScriptOrganizer.tso version or length")
    pos = 1

    def number() -> int:
        nonlocal pos
        if pos >= len(lines) or not lines[pos].isdigit():
            raise ValueError("Expected nonnegative organizer child count")
        value = int(lines[pos])
        pos += 1
        if value > MAX_ENTRIES:
            raise ValueError("Organizer child count exceeds limit")
        return value

    def children(count: int, parents: tuple[str, ...], depth: int, records: list[dict]):
        nonlocal pos
        if depth > MAX_DEPTH:
            raise ValueError("Organizer hierarchy exceeds maximum depth")
        for _ in range(count):
            if pos + 1 >= len(lines):
                raise ValueError("Truncated organizer node")
            marker = lines[pos]
            name = lines[pos + 1]
            pos += 2
            if marker not in ("0", "1") or not name or len(name) > 256:
                raise ValueError("Invalid organizer node marker or name")
            path = [*parents, name]
            if len(records) >= MAX_ENTRIES:
                raise ValueError("Organizer has too many nodes")
            record = {"name": name, "path": path, "folder": marker == "0"}
            records.append(record)
            if marker == "0":
                size = number()
                record["child_count"] = size
                children(size, (*parents, name), depth + 1, records)

    trees = {}
    for kind in TREE_KINDS:
        if pos >= len(lines) or lines[pos] != "HeaderBegin":
            raise ValueError(f"Expected organizer HeaderBegin for {kind}")
        pos += 1
        root_count = number()
        records = []
        children(root_count, (), 0, records)
        leaves = [r for r in records if not r["folder"]]
        paths = {}
        for leaf in leaves:
            paths.setdefault(leaf["name"].casefold(), []).append(leaf["path"][:-1])
        trees[kind] = {
            "root_child_count": root_count,
            "folder_count": len(records) - len(leaves),
            "entry_count": len(leaves),
            "unique_entry_count": len(paths),
            "duplicate_entry_names": [
                {"name": name, "count": amount}
                for name, amount in sorted(Counter(r["name"] for r in leaves).items())
                if amount > 1
            ],
            "entries": records,
            "paths_by_name": paths,
        }
    if pos != len(lines):
        raise ValueError("Organizer has trailing unconsumed records")
    return {
        "schema": SCHEMA,
        "source_format_version": 2,
        "read_only": True,
        "runtime_graph_decoded": False,
        "category_paths_are_runtime_edges": False,
        "trees": trees,
    }


def attach_organizer_index(script_index: dict, organizer: dict) -> dict:
    """Annotate existing source definitions with *verified organizer paths*.

    Does not fabricate actor links or use paths as runtime sequence/order.
    """
    if organizer.get("schema") != SCHEMA:
        raise ValueError("Unsupported organizer schema")
    scripts = organizer["trees"]["scripts"]["paths_by_name"]
    definitions = script_index.get("definitions")
    if not isinstance(definitions, list):
        raise ValueError("Expected script definitions list")
    source_names = set()
    for rec in definitions:
        if rec.get("deleted_source"):
            # DeletedScripts records may have been moved out of the tree.
            rec["organizer_paths"] = []
            rec["organizer_status"] = "historical_deleted_source"
            continue
        name = rec.get("filename_stem")
        if not isinstance(name, str):
            raise ValueError("Missing source definition name")
        key = name.casefold()
        source_names.add(key)
        rec["organizer_paths"] = scripts.get(key, [])
        rec["organizer_status"] = (
            "organized" if rec["organizer_paths"] else "unlisted_active_source"
        )
    organizer_leaf_names = set(scripts)
    script_index["organizer"] = {
        "schema": SCHEMA,
        "source_format_version": organizer["source_format_version"],
        "read_only": True,
        "runtime_graph_decoded": False,
        "categories_are_source_metadata_only": True,
        "counts": {
            kind: {key: organizer["trees"][kind][key] for key in
                   ("root_child_count", "folder_count", "entry_count",
                    "unique_entry_count", "duplicate_entry_names")}
            for kind in TREE_KINDS
        },
        "unlisted_active_definitions": sorted(source_names - organizer_leaf_names),
        "orphan_script_organizer_entries": sorted(organizer_leaf_names - source_names),
        "category_trees": {
            kind: organizer["trees"][kind]["entries"]
            for kind in TREE_KINDS
        },
        "warnings": [
            "Organizer paths are categories, not TriggerScript events, node edges or execution order.",
            "Condition/action organizers list available editor symbols; no TSD parameter or actor linkage is implied.",
        ],
    }
    return script_index
