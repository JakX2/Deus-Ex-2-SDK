#!/usr/bin/env python3
"""T3Ed-style DX2 class palette, grounded in observed map actors and script declarations.

No actors are manufactured and no binary packages are modified. An observed
placed actor is only a *visual template candidate*, not a proven instantiable
Gamesys archetype. Script inheritance is reported only when declared.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import sys

ACTOR_CLASS_SCHEMA = "DX2Ed-archetype-catalog-v1"


def archetype_catalog(actors: list[dict], *, system_classes: dict | None = None,
                      system_properties: dict | None = None) -> dict:
    system_classes = system_classes or {}
    system_properties = system_properties or {}
    by_name: dict[str, dict] = {}
    observed: dict[str, list[dict]] = defaultdict(list)
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        kind = actor.get("class")
        if isinstance(kind, str) and kind.strip():
            observed[kind.casefold()].append(actor)
    # Preserve qualified package names; class suffixes are not globally unique.
    for qualified, record in system_classes.items():
        if not isinstance(qualified, str) or not isinstance(record, dict):
            continue
        short = qualified.rsplit(".", 1)[-1]
        by_name[qualified.casefold()] = {
            "qualified": qualified,
            "class": short,
            "package": str(record.get("package", "")),
            "base": record.get("base") if isinstance(record.get("base"), str) else None,
            "source": "system_declaration",
            "observed_actors": 0,
            "template_actor": None,
            "template_export": None,
            "template_mesh": None,
            "property_signatures": [],
        }

    # Add observed classes without a matching declared script. For ambiguous
    # duplicate class names, do not choose a guessed GameSys package.
    declared_names: dict[str, list[dict]] = defaultdict(list)
    for rec in by_name.values():
        declared_names[rec["class"].casefold()].append(rec)
    for key, matches in observed.items():
        if len(declared_names[key]) == 1:
            rec = declared_names[key][0]
        else:
            label = matches[0]["class"]
            qualified = "observed." + label
            rec = {
                "qualified": qualified, "class": label, "package": None,
                "base": None, "source": "map_observation",
                "observed_actors": 0, "template_actor": None,
                "template_export": None, "template_mesh": None,
                "property_signatures": [],
            }
            by_name[qualified.casefold()] = rec
        rec["observed_actors"] = len(matches)
        scalar_signatures: dict[int, set[tuple[str, str]]] = defaultdict(set)
        template = None
        for actor in matches:
            for prop in actor.get("game_properties", []):
                if not isinstance(prop, dict):
                    continue
                pid = prop.get("id")
                if not isinstance(pid, (int, float)) or int(pid) != pid:
                    continue
                scalar_signatures[int(pid)].add((str(prop.get("name", "")),
                                                 str(prop.get("type", ""))))
            if template is None and isinstance(actor.get("mesh"), str) and actor["mesh"].strip():
                template = actor
        if template:
            rec["template_actor"] = template.get("name")
            rec["template_export"] = template.get("export")
            rec["template_mesh"] = template["mesh"]
        rec["property_signatures"] = [
            {"id": pid,
             "name": next(iter(signatures))[0] if len(signatures) == 1 else None,
             "type": next(iter(signatures))[1] if len(signatures) == 1 else None,
             "conflicting": len(signatures) > 1}
            for pid, signatures in sorted(scalar_signatures.items())
        ]

    return {
        "schema": ACTOR_CLASS_SCHEMA,
        "read_only": True,
        "native_spawn_supported": False,
        "source_class_count": len(system_classes),
        "observed_actor_count": sum(len(v) for v in observed.values()),
        "classes": sorted(by_name.values(), key=lambda rec: (rec["class"].casefold(),
                                                               rec["qualified"].casefold())),
        "ambiguous_names": sorted(k for k in observed if len(declared_names[k]) > 1),
        "property_catalog_size": len(system_properties),
        "warnings": [
            "A GameSys class declaration does not prove an actor can be safely spawned.",
            "Template actors are existing original map instances, not constructor defaults.",
            "Ambiguous class names are not assigned to arbitrary packages.",
            "Property signatures summarize observation, not verified inherited schemas."
        ],
    }


def catalog_for_map(actors: list[dict], system_path: Path | None = None) -> dict:
    if system_path is None:
        return archetype_catalog(actors)
    # This existing SDK parser decodes the user's own .d2u TextBuffers.
    from dx2catalog import build_catalog
    catalog = build_catalog(system_path)
    return archetype_catalog(actors, system_classes=catalog.get("classes", {}),
                             system_properties=catalog.get("properties", {}))

