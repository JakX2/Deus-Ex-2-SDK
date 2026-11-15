# DX2Ed P111: fix genuine retail actor identity lost during JSON parsing

## Report from Windows retail tester

The new Save / Export summary saved a private Seattle Hub draft, but reported
**zero eligible native moves/copies/unplacements** and 19 omissions. Among the
omissions were names beginning `StaticMeshActor__`, which looked eligible
but were refused as "not an original StaticMeshActor."

## Root cause

Godot 4.3 `JSON.parse_string()` decodes numeric values from `actors.json`
as **floats**, including exact source export indices such as `151` ->
`151.0`. The original GMP parser wrote true integer IDs, but the Godot
client's `_native_bulk_preview()` required
`typeof(actor["export"]) == TYPE_INT`. Thus an otherwise eligible source
record was rejected on **type** alone, before native GMP validation.

Relevant upstream Godot engine issue:
https://github.com/godotengine/godot/issues/103801

## Fix

- `load_actors()` now canonicalizes only positive, finite, exactly integral
  source export IDs from JSON to a Godot integer, with upper bound 2147483647.
  Strings, negatives, fractions, NaN, infinity and oversized values are
  refused rather than rounded or guessed.
- Original actor **classes** are *not* promoted. Only the exact
  `StaticMeshActor` source class is accepted by this experimental native
  writer, consistent with the independent T3SDK-side source identity check.
- A rejected actor now reveals whether it is an original but non-static
  source class (`D_...`), or whether its original export ID is missing or
  malformed. A name prefix alone is NOT sufficient to authorize a write.
- The P109 and P110 bulk/legacy writers and binary whole-GMP replay checks
  remain unchanged.

## Regression

`smoke_original_actor_json_export_id.gd` uses **actual
JSON.stringify / JSON.parse_string** followed by the **real load_actors**
path, not manually constructed int dictionaries. It checks that an original
`StaticMeshActor__151` with export `151.0` is eligible for a moved native
prop plan and original-source-backed private clone; a non-static `D_2494`
and a fractional export `12.5` remain rejected for precise reasons.

This fixture uses fabricated metadata and a Godot BoxMesh. It does **not**
serialize a retail GMP and does not claim original game runtime compatibility.
Godot scene fixture CI and Windows launcher self-test include this regression.

## Tester directions

1. Preserve the current editor draft and take a fresh copy of the original
   retail GMP.
2. Open the P111 Windows prototype, import the same original GMP and matching
   IBD resources, then **Load draft**.
3. Use **Save / Export map...** to check how many of the 19 edited objects
   now qualify. The exact count depends on *actual source class*, original
   export validity and supported translation/duplication only.
4. Save an isolated same-name GMP candidate only if eligibility is nonzero.
   The game installation is unchanged, and runtime verification remains an
   independent manual experiment.

P111 does not add native brush/BSP serialization, arbitrary props, doors,
vending machines, gameplay scripts, physics/collision baking or a complete
T3Ed-level compiler.
