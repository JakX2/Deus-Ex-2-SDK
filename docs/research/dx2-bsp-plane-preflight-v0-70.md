# v0.70: one source-pinned BSP plane preflight, still no writer

The independent original GMP Model byte provenance from v0.69 and source-authored Light plane-path counterfactual from v0.68 now meet in `dx2sdk.bsp_plane_preflight.preflight_original_bsp_plane`.

The entry point independently rechecks the original GMP, computes exact original Model export/node plane byte offsets and hypothetical float32 differences, then checks the same hypothetical plane against the original Light inventory. It refuses to return a combined result if original GMP SHA-256, original Model SHA-256, Model export, node ordinal, float32 planes or no-write capability declarations disagree.

This reduces the chance of accidentally applying an impact estimate to the wrong original package or Model plane. The combined report preserves original actor export identifiers and candidate path changes; it explicitly never claims a new engine Region leaf, collision validity or runtime acceptance. It writes nothing.

Synthetic tests cover the positive evidence join, mismatched identities, contradictory capability declarations, input immutability, deterministic report and source recheck calls. The public native writer remains limited to its preexisting narrow actor scalar/translation edits.

**Next native evidence gate:** determine which original compiled collision/MOPP surface references the same spatial geometry, and validate exact original byte extents before considering a disposable isolated native edit. A 16-byte Model plane substitution by itself is *not* a valid playable BSP edit.
