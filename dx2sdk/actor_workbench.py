"""Source-authenticated original UE95 actor property workbench, read-only.

The native catalog preserves every authored top-level tagged name, kind, size
and original byte offset without interpreting unknown engine fields. Only a
unique nonindexed, four-byte IntProperty/FloatProperty already approved by
the existing DX2SDK scalar writer is flagged as an experimentally editable
field; the catalog itself NEVER enables writes or creates a new native tag.
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .scalars import (
    FORBIDDEN, _native_tags, _numeric_candidates, _source_actor,
)

if TYPE_CHECKING:
    from .api import DX2Map

SCHEMA = "DX2SDK-original-actor-property-workbench-v1"
MAX_SOURCE_TAGS = 4096
CATEGORY_META = (
    ("eligible-original-numeric", "Existing four-byte numeric tags"),
    ("protected-original", "Protected source tags (read only)"),
    ("duplicate-original-name", "Repeated original names (read only)"),
    ("indexed-or-special", "Indexed or special source tags (read only)"),
    ("unsupported-numeric-layout", "Unsupported numeric layout (read only)"),
    ("opaque-uninterpreted", "Other source tags (opaque, read only)"),
)


def original_actor_property_workbench(world: "DX2Map", actor_name: str) -> dict:
    """Catalog one *original* positioned StaticMeshActor, never an edit plan.

    Validation requires the unchanged source map, source-bound actor cache,
    independently verified source actor name/export/class/location and native
    source-tag bounds. The result is an observational report only.
    """
    world._check_original_unchanged()
    actor, exp = _source_actor(world, actor_name)
    tags = _native_tags(world._package, exp)
    if len(tags) > MAX_SOURCE_TAGS:
        raise ValueError("Original native actor has too many authored tagged fields")
    editable = {r["property"]: r for r in _numeric_candidates(world, actor_name)}
    names = Counter(row["property"] for row in tags)
    catalog = {key: [] for key, _ in CATEGORY_META}
    for ordinal, tag in enumerate(tags):
        name = tag["property"]
        kind = tag["native_kind"]
        numeric = editable.get(name)
        if numeric is not None:
            category = "eligible-original-numeric"
        elif name.casefold() in FORBIDDEN:
            category = "protected-original"
        elif names[name] > 1:
            category = "duplicate-original-name"
        elif tag["has_array_or_special_flag"]:
            category = "indexed-or-special"
        elif kind in (2, 4):
            category = "unsupported-numeric-layout"
        else:
            category = "opaque-uninterpreted"
        row = {
            "property": name,
            "tag_ordinal": ordinal,
            "native_kind": kind,
            "native_kind_label": (
                "IntProperty" if kind == 2
                else "FloatProperty" if kind == 4
                else "uninterpreted-native-kind-%d" % kind
            ),
            "serialized_payload_size": tag["size"],
            "source_byte_offset": tag["offset"],
            "indexed_or_special": tag["has_array_or_special_flag"],
            "original_value": numeric["source_value"] if numeric else None,
            "editable_existing_tag": numeric is not None,
            "runtime_effect_verified": False,
            "can_insert_property": False,
            "category": category,
        }
        catalog[category].append(row)
    world._check_original_unchanged()
    categories = [
        {"key": key, "label": title, "count": len(catalog[key]), "fields": catalog[key]}
        for key, title in CATEGORY_META
    ]
    return {
        "schema": SCHEMA,
        "status": "source-original-actor-property-catalog",
        "source_map": world.source.name,
        "source_sha256": world.source_sha256,
        "actors_sha256": world._actor_cache_sha256,
        "actor": actor_name,
        "export": actor["export"],
        "actor_class": "StaticMeshActor",
        "original_location_native_xyz": list(actor["location"]),
        "original_export_size": exp["size"],
        "source_top_level_tag_count": len(tags),
        "eligible_original_numeric_count": len(catalog["eligible-original-numeric"]),
        "read_only_original_tag_count": len(tags) - len(catalog["eligible-original-numeric"]),
        "categories": categories,
        "source_actor_cache_verified": True,
        "read_only": True,
        "no_map_or_cache_mutation": True,
        "new_tag_insertion_enabled": False,
        "arbitrary_gamesys_editing_enabled": False,
        "gameplay_runtime_verified": False,
    }
