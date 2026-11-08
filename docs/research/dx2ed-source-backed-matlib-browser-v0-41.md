# DX2Ed v0.41: source-backed MatLib and texture browser

## User-visible workflow

The new **Materials** workspace tab imports one user-supplied `.ibd` file or
`Maps.zip`. The import worker reuses `map_exporter/dx2textures.py` and its
existing read-only IBD resource parser. It reads observed 40-part MatLib
records and texture resources, preserving the nine raw stage references,
flags, stage mask, category ID, source label, color vectors and parameters.

For resolved stage references, the worker decodes the existing supported
DX2 texture formats and writes small PNG thumbnails to a separate
`user://dx2ed_material_cache` tree. Each preview filename is content-derived
and each PNG is accompanied by a SHA-256 digest. The catalog records source
file SHA-256 values and source bundle names. Original IBD/ZIP bytes are never
written.

## Browser behavior

- Search material names, source labels, bundle names and raw stage names.
- Filter materials by resolved diffuse stage, missing diffuse, or unresolved
  stage references.
- Inspect all nine stage slots with a decoded thumbnail when one is available.
- View format, dimensions, usage, source bundle, flags, stage mask, category
  ID, color vectors and parameters.
- Missing references and omitted oversized thumbnails remain explicit; the
  browser never substitutes an invented texture.
- Catalog preflight rejects malformed stage arrays, oversized catalogs,
  invalid source hashes, path-traversing preview paths and malformed preview
  digests before replacing the currently loaded browser state.
- Preview loading checks file size and SHA-256 before asking Godot to decode
  the PNG. The Python worker writes only to the private cache.

## Format and safety boundaries

The existing parser observes a 40-part MatLib layout and nine texture-stage
resource references. v0.41 preserves these values as evidence. It does not
interpret shader effects or assign semantic names to category IDs. A resolved
stage reference means only that a resource with that name was found in the
selected IBD inventory.

This milestone is a **read-only browser and preview pipeline**. It does not
write source material data, modify original IBD/GMP files, assign native
BSP material indices, or implement a native material/shader writer. The
v0.40 procedural Polygon preview slots remain private editor data. Native
BSP/CSG/collision/lightmap cooking and GameSys/TriggerScript execution remain
disabled.

## Verification

The synthetic Python tests exercise stage resolution, unresolved references,
bounded thumbnail output and hostile resource names without retail data. The
real Godot 4.3 smoke creates an invented catalog and PNG, checks search and
stage filtering, renders nine slot cards, verifies the thumbnail digest, and
rejects path traversal while retaining the last valid catalog. CI also runs
the existing 910+ Python fixture suite, source-only bundle, portable SDK
checks and bundled Windows Godot 4.3 executable self-test on the exact head.
