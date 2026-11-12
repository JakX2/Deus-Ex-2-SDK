# DX2Ed v0.77: original World BSP Model complete byte-span ledger

**Status: read-only, source-SHA-pinned, no native World Model writer.**

This extends v0.76's exact original World Model no-op reconstruction with an explicit nonoverlapping byte-level structural map. The older no-op could reconstruct the same source payload and report an overall count but did not expose which original bytes occupy each observed or opaque field.

## What is actually recovered

For a user-owned original DX2 UE95 World Model, the new dx2sdk/bsp_model_spans.py reader:

1. Requires the existing complete original payload no-op, exact source bytes, rooted BSP graph, zone-mask recurrence and recognized 109–116-byte node records.
2. Enumerates every byte from the 50-byte Model header through the original variable-width compact node count, all native node records, the four-byte zone count, source 69-byte per-zone records, and the eight-byte zero trailer. The source-span ledger rejects gaps, overlaps and extents outside the original Model.
3. Splits each node into individual source bit-preserving spans: 16-byte float32 plane, 32-byte subtree-zone mask, eight separately sized original compact indexes, source-unknown 16-byte spatial region, 16-byte reserved/unknown region, two 2-byte zone candidates, the original one-byte vertex-slot count, and four source 4-byte suffix words.
4. Records raw compact field widths, including noncanonical but source-decodable encodings. There is no canonicalization to shorter encodings or float32 re-quantization.
5. Distinguishes three epistemic classes, not three writer permissions:
   - source_observed_byte_layout: observed length/structure and independently tested references or zone framing, without claiming original engine member names.
   - candidate_field_meaning: source-normalized plane and header bound candidates, not authenticated writable geometry.
   - opaque_original_source_bytes: bytes whose semantics are unknown, including compact field 2, candidate external surface IDs, and suffix unknowns.
6. Aggregates a count, source length, nonzero byte count and SHA-256 of concatenated original source bytes for each role, so different original private maps can be compared without including game payload bytes. Reports per-class byte totals and fractions. These fingerprints do not decode engine fields.
7. Optionally exposes metadata about up to 12 selected original nodes, with exact Model-relative and source-GMP absolute offsets, lengths and per-span hashes. No raw Model bytes are output. First eight zone records have analogous bounded Model-relative span examples.

Independent v0.76 no-op byte identity and SHA-256 must agree. Total byte-class lengths and all role lengths must each equal the original Model payload size. Source GMP byte identity is rechecked before and after.

**Important format conclusion:** Under the currently validated header/node/zone framing, there are zero unframed source bytes left inside the World Model export. This does not show that surface or vertex data is absent: it might be encoded in currently opaque node fields, reside in a different export or be formed by the game at runtime. There is no decoded independent native Surfs array yet.

## API / reproduction

~~~python
from dx2sdk import DX2Map

world = DX2Map.open(r"C:\DX2\Content\DX2\Maps\ORIGINAL.gmp")
ledger = world.inspect_original_model_byte_spans(node_indices=[0, 12])
assert ledger["model_byte_ledger_fully_contiguous_nonoverlapping"]
assert ledger["original_model_noop_reassembled_byte_identical"]
~~~

For a pinned original GMP, create a new private JSON outside retail Maps:

~~~powershell
python research/dx2/inspect_world_model_spans.py "C:\DX2\Content\DX2\Maps\ORIGINAL.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --node 0 --node 12 --report "C:\DX2Research\world_model_spans.json"
~~~

The CLI refuses duplicate/out-of-range node ordinals, mismatched source hashes, malformed Model payloads and writing over an existing report. No GMP or collision bytes are written.

## Tests and unresolved engineering work

Synthetic fixtures verify exact full-payload coverage, selected per-node contiguous spans, source compact index width expansion, original source-count encoding width, role class labels, byte hashes of unknown spatial values, zone 69-byte breakdown, invalid fields and source hashes, original GMP absolute offsets and CLI refusal. No proprietary maps or generated shaders are shipped.

This is a precise structural byte map for future source/format audits, not a geometry editor, native compiler, gameplay feature or runtime test. We have not authenticated a complete vertex XYZ pool, source-owned surfaces, native CSG/BSP cooking or regenerated Havok/MOPP collision. The next useful source research is to identify consumers of the opaque numeric fields or independently serialized external surfaces, then validate index bounds against them.

Original files remain unchanged. The read-only inspector and CLI are in both the standalone SDK and Windows Godot prototype source-only ZIPs.
