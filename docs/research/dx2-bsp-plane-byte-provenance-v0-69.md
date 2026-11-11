# v0.69: exact original Model plane byte provenance

The original UE95 DX2 package export table contains an offset and serialized size for the Level-referenced World Model. The existing source-observed Model parser independently validates node boundaries and planes. This change joins those two observations to identify the exact 16 original GMP bytes occupied by any validated BSP node plane.

`dx2sdk.bsp_plane_bytes.inspect_original_plane_bytes(world, node=N, replacement=(nx,ny,nz,d))` revalidates the source GMP and Model SHA, confirms the Level-referenced export is a Model, locates the original node boundary, and reports the original absolute GMP offset, the original and hypothetical float32 plane values, changed byte positions and SHA-256 hashes of both 16-byte values.

The report is a **read-only patch provenance plan**, not a patch operation. No writer is enabled. It does not claim that replacing 16 bytes preserves valid BSP topology, actor Region state, collision/MOPP, visibility or runtime gameplay. No retail asset is committed or modified. Synthetic tests use invented byte arrays and a mocked parser boundary solely to test the offset arithmetic and refusal behavior. The real entry point uses the independent native Model parser and source hash checks.

Next evidence gate: cross-check an original Model plane against associated original geometry and collision surfaces before considering an isolated native copy writer. Native runtime acceptance remains untested.
