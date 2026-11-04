# DX2Ed: replay one height from a source-exact capsule profile

**Research PR #54**, stacked on #53's read-only multi-height wireframe, #52's private multi-height contact summaries, #51's finite original source-edge chord, and #50's exact-original-Level welded edge cache.

## DX2Ed workflow

1. Open an **owner-provided original GMP**, enable **Inspect source collision**, click an original collision triangle, and select a unique valid exact source edge connection.
2. Run **Profile capsule heights** with bounded offsets. The existing full-map offline Python oracles produce a fresh private profile JSON. Its original hash, map, each height, original triangle IDs, contact values and starting source chord are validated before the 3D bundle is shown.
3. In the interactive capsule panel, choose a row in the new height selector and click **Inspect selected height**.
4. The editor independently rebuilds the baseline chord using the *current source-exact v3 collision cache*, compares it against the authenticated profile's baseline, and translates it upward in preview space by the chosen original Level +Z offset.
5. The same PR #46/48 read-only Python worker reopens and SHA-verifies the entire owner GMP and independently recomputes one height's full-map fixed-axis capsule sweep, numerical first-contact estimate and conservative MOPP candidate coverage. The new detail JSON is a fresh private file outside original Maps.
6. The replay validator refuses the detail result unless it matches the prior profile's **original first-hit triangle ID, complete geometric-contact count, first-entry normalized path time, initial-overlap flag and near-tangency flag**. It also matches start/end XYZ, capsule dimensions, axis and original source hash, then invokes the existing single-height PR #47 contact capsule/normal wireframe.
7. The 3D multi-height lines stay visible. **Clear height paths**, a new picked point, another profile run, source-inspection reset or map change invalidates the replay state; the existing detailed single-height visualization follows its own source lifecycle.

## Important scientific limits

- The pink mark in the multi-height profile indicates a **path parameter**, not a contact point. The detailed single-height overlay includes the numerical source contact point/normal when resolved.
- A contact can represent intended **floor support**, not blocking geometry. No-contact does not certify traversal. A straight fixed-axis chord is not a Havok controller path.
- **No gameplay Havok queries, controller dimensions, friction/collision filters, dynamic actor geometry, pathfinding, native Level/MOPP saving or cooked collision.**
- Never commit owner retail game content or generated source coordinates. The only new checked-in tests use invented geometry and synthetic metadata. The original GMP/IBD are never written.

## Automated verification

- `source_edge_capsule_height_replay.gd`: conservative worker request generator and independent profile/detail congruence verifier.
- `capsule_sweep_panel.gd`: **Inspect selected height** button/selector, source-exact recreation, existing private worker, successful detailed-overlay handoff.
- `smoke_source_edge_capsule_height_replay.gd`: ninth Godot 4.3 headless fixture checks authentic synthetic replay, deliberate disagreement in first hit/height/time/size/hash/tangency and invalid row selection.
- `smoke_source_edge_capsule_probe.gd`: extended source-connected picker/Inspector fixture requiring current v3 original chord reconstruction and rejecting stale hash and cleared profile state.
- CI runs these alongside the existing Python source geometry tests and all previous Godot fixtures.

**Owner-side work still needed:** original-GMP Windows click-through and runtime Havok comparison. Keep this PR a draft until that evidence is collected. Passing synthetic CI is not a real-map or gameplay result.
