# DX2Ed native import architecture

```text
Original retail .gmp map
      + matching .ibd mission bundle (+ optional shared resource bundles)
                      |
            Read-only Python backend
           /                     \
   scene.glb                  actors.json
           \                     /
            Godot native viewport
           Actor tree + inspector
```

**The original GMP is the authoritative game map.** GLB is only a renderer/interchange cache. The backend reads DX2 map/bundle data using existing modules in `map_exporter/` and `actor_explorer/` without writing to the game installation.

Godot's `Open DX2 map (.gmp)` file picker launches `dx2_native_backend.py` on a worker thread and stores generated output beneath Godot's user data directory. It then imports the GLB as a native 3D scene and opens the adjacent actor metadata automatically.

The cache key includes the source map SHA-256, selected resource-bundle SHA-256 values and importer version. This avoids reprocessing unchanged maps while invalidating cached scenes when source bytes change.

## Planned work

Selection by original export index, exact hit testing, native asset browser, mesh isolation, transform gizmos, and guarded 'Save As' GMP edits. TriggerScript editing must remain a separate verified IBD write path until robust rebuilding is available.

## Publication boundary

Do not commit extracted retail map resources, models, textures, modified IBD bundles, or other copyrighted game files. Only original SDK code, documentation, and asset-free tests belong in this repository.
