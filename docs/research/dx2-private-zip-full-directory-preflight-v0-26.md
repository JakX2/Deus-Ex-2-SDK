# DX2SDK v0.26: full-directory ZIP preflight

This small hardening follow-up to draft PR #92 preserves its private, read-only, in-memory package audit. Before any GMP/D2U member is read, the scanner checks the entire ZIP central directory, including unrelated members, for duplicate normalized names, negative sizes, unsupported strong-encryption flags and a bounded sum of advertised uncompressed bytes (2 GiB). This closes a budget-accounting gap where large unrelated members were previously excluded from the total. It does **not** decompress unrelated members or extract files.

Synthetic tests use an invented valid package and an unrelated member with a deliberately reduced test budget; they also verify a bounded unrelated member remains accepted. The previous per-eligible-member rejection categories remain unchanged. An archive exceeding the global budget fails closed with no aggregate report, rather than silently skipping unrelated entries.

**Limits:** ZIP central-directory metadata can be dishonest. This preflight is not a proof that unexamined entries are safe, nor does it validate native BSP leaves/zones, package export ownership, runtime behavior, geometry cooking, or writes. No retail maps are included or published. This research tool remains opt-in and does not alter source packages or the Godot editor.
