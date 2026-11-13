# DX2Ed prototype P104: map-cache-scoped private CSG recipe manager

This milestone adds a **small persistent recipe inventory** to the Godot 4.3 editor. It references the replayable `.dx2csg.json` recipes introduced in P103. Every rendered result is recomputed by the source-private Python CSG backend, never trusted from saved polygon data. It is **not** native Deus Ex: Invisible War World BSP, CSG, collision, or an editable game actor.

## Using the editor

1. Load a private cached map/GLB in DX2Ed. The editor looks up its own CSG recipe catalog from `user://private_csg_catalogs/<SHA256 of private cache folder>.json`. Missing catalogs are empty, not an error. Catalogs are **not** embedded in a GMP, IBD, or the existing map-specific `DX2Ed-prop-draft-v1` sidecar.
2. Create a source-private Box pair and **Save CSG recipe...** using P103, or select an existing valid `.dx2csg.json`. Choose **Register CSG...** and pick the file. This independently verifies and recomputes it, then adds a map-cache-scoped **reference**, SHA-256 of the original recipe file and its recomputed result fingerprint. Duplicate paths and more than 64 entries are refused.
3. The compact toolbar selector lists registered recipes with operation, file name and private operand names. Choose a recipe and click **Refresh CSG** to verify the saved bytes still match the registered SHA-256, **rerun P103's complete CSG recomputation**, check identity and operation, and render a disposable intersection or multi-piece subtraction overlay.
4. **Unlink CSG** removes only the catalog entry. It never deletes or edits the referenced `.dx2csg.json`. If the removed entry owns the active catalog preview, that preview is cleared. Other registered recipes and original map data remain unchanged.
5. Reopen the same private GLB cache to automatically restore its registered recipe list. The list does not automatically render any geometry: refresh is an explicit operation. Another cache folder has an independent list.

## Safety and file guarantees

The catalog contains **only** a source-private map-cache path identity, an array of existing P103 recipe file paths, pinned SHA-256 values, operation, source-private `DraftProp_N` provenance, and disabled native collision/BSP flags. It does not contain original actor records, imported map bytes, generated triangle meshes, GameSys, native Havok/MOPP or source map authoring directives.

- The index resides under Godot's application `user://private_csg_catalogs`, not under original game folders.
- Catalog records have a strict versioned schema, bounded file length (128 KiB), maximum 64 entries, unique references, validated 64-character SHA fingerprints, and exact private-cache identity. Unsupported schemas and native-writer claims are refused.
- Mutation uses a private `.pending` file, verifies the staged bytes, retains a `.bak` when replacing an existing valid index, and rolls back on rename failure. Existing malformed catalogs cannot silently be overwritten. The P103 recipe file itself is never modified by the catalog.
- Registration requires a successful P103 private recipe load/recompute. On refresh, the recipe's bytes, source-private operands, operation, and recomputed result must still match the registered identity. Changed, moved, tampered, or otherwise untrusted files are refused. The existing preview is preserved on refusal, rather than replaced with unverifiable geometry.
- The manager cannot register arbitrary original StaticMeshActor records or native .gmp/.ibd assets; those inputs are rejected by P103 before catalog updates.
- Any CSG overlay remains a disposable, unselectable Godot mesh, outside draft actor lists, physics bodies, original map exporters, and Undo history.

## Synthetic validation

`native_editor/godot_editor/tests/smoke_private_csg_catalog.gd` exercises the **actual editor toolbar** using a copied demo GLB in a temporary private cache. It creates two valid source-private P103 recipes (including the six-piece, 44 m³ subtraction cavity), registers and selects both, refuses a duplicate, renders and refreshes the six pieces, reloads the map/GLB and finds the same inventory, checks a 2 m³ intersection, refuses a modified previously registered recipe, verifies isolation from another map cache, unlinks without deleting either recipe, refuses an index that claims native BSP/collision support, and checks unchanged synthetic original GMP bytes and Undo count.

The Windows source packaging manifests and offline prototype doctor require the new Godot script and fixture. The native GitHub Actions workflow independently compiles the manager and executes the headless Godot integration test.

## Non-goals

P104 is a private recipe **index**, not a persistent editable derived brush or integrated CSG dependency graph. Repositioning or editing generated CSG pieces, internal live CSG updates, native World BSP/CSG rebuilding, original surface identity, UV/material assignment, portal/zone/collision recreation, original GMP/IBD writing, and retail gameplay acceptance remain unsupported. **P104 is a prototype milestone, not product v1.0.**
