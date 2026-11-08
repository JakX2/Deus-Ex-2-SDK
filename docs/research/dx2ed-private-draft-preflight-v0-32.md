# DX2Ed v0.32: private draft load preflight

The existing **Load draft** command now validates the complete saved list of moved actor identities and preview copy identities before resetting editor transforms, clearing copies, or applying staged properties. Missing or duplicate original actors, duplicate/invalid `DraftProp_N` names, unavailable original mesh sources and missing local asset preview meshes are rejected with a visible reason. This closes the previous silent-skip path that could misleadingly report a partial load as successful. The asset preflight may populate the in-memory mesh cache but does not modify scene objects or source files.

The existing transform, brush dimension, class provenance and property-override checks still run before the new identity/source checks. The Windows Godot orthographic editor smoke now calls the real editor preflight with invented actors, duplicate and missing identities. CI must confirm this exact branch head before claiming a passing build.

**Limits:** This protects private `user://` JSON preview-draft reconstruction; it is not an authenticated DX2 GMP parser, BSP/zone writer, collision or lighting cooker. Native actor creation and unverified format writes remain disabled. Original retail GMP/IBD files are never overwritten. This is an incremental reliability step, not a completed native editing workflow.
