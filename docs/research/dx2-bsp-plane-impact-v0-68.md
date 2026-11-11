# v0.68: original DX2 BSP plane counterfactual against existing Light paths

This milestone examines a concrete edit consequence before attempting native BSP serialization.

The existing `dx2sdk.bsp_trace._load_model` source parser validates the unchanged original GMP's World Model export, source SHA-256, compact child graph and zone-mask recurrence. The original Light audit supplies native actor export IDs, locations and original Region leaf/zone fields.

`compare_original_plane_impact(world, node=N, replacement=(a,b,c,d))` takes a single node's original float32 plane, creates an **in-memory** modified plane in a copied node array, and traces each original Light through the unchanged and counterfactual candidate plane-side graph. The report includes changed plane-byte offsets, original Light exports and unchanged original Region observations, plus which candidate paths would change.

It explicitly does not solve Region.iLeaf, visibility, collision, MOPP, portals, gameplay or node writer semantics. A candidate missing-child terminal is not a verified engine leaf. It cannot prove that writing a plane would yield a valid game map. This is a targeted research step to measure potential damage to existing actor spatial relationships before a future isolated BSP writer is considered.

All original game files and source metadata remain read-only. Synthetic two-node tests exercise a changed plane that reroutes one original Light, deterministic output, float32/no-op refusal, invalid normals, duplicate actor exports and input immutability.

## Next evidence gate

Cross-check proposed plane changes against source render triangles, zone masks and MOPP collision triangles in a single source-pinned report, then validate the native World Model serialization boundary with a strict no-op byte replay. Only consider isolated native writes after multiple real-map format proofs and disposable runtime testing.
