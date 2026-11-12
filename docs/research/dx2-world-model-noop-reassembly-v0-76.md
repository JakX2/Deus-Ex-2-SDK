# DX2Ed v0.76: original compiled World Model byte-exact no-op reassembly

**Milestone:** source-validated, entirely read-only native DX2 compiled BSP Model
**serialization baseline**. This is **not an edited BSP writer or game runtime
test**. It neither enables geometry mutation nor produces a modified GMP.

## Why this is a format advance

Earlier research independently validated the original DX2 UE95 World Model
export, variable native BSP node records (observed 109..116 bytes), eight
Unreal compact-index fields per node, rooted tree/zone-mask relationships,
69-byte zone records and trailing eight zero bytes.

This milestone introduces an **exact original-payload reconstruction** rather
than another geometric correlation. It decodes identified source fields,
rebuilds them in the existing original order, retains unknown regions
byte-for-byte, and validates the in-memory result against the original entire
Model export SHA-256. No field may shift or have its compact encoding
normalized.

For every accepted original World Model:

- The 50-byte empty-bound header and **original variable-width node-count
  encoding** are retained.
- Each native node is split into its original 16-byte float32 plane,
  32-byte zone mask, **exactly eight raw compact-index encodings**,
  the source 16-byte spatial record whose engine meaning remains provisional,
  16 opaque bytes, two little-endian uint16 zone candidates and one vertex-
  count byte, then the observed 16-byte suffix with two signed and two
  unsigned int32 values.
- The uint32 zone count and each 69-byte source-observed zone record are
  reassembled from their individual source fields: leading byte, 32-byte
  relation bitset, 32 all-0x01 bytes and four trailing zero bytes, followed
  by the Model's eight-byte zero trailer.
- The rebuilt stream must have **the same byte count, bytes and SHA-256**
  as the original Model. The standalone original BSP framing parser then
  checks the reconstructed bytes again.
- Source float32 bits and opaque byte regions are preserved, rather than
  performing round-trip decimal float conversion, recompilation or
  normalization of compact integers.
- The source Model graph, node array, zone table and per-node subtree
  zone-mask recurrence are validated **before** the in-memory copy is
  exposed. Unknown or unsupported record boundaries are rejected.
- A read-only report includes original node count, zone count, record-width
  and compact-integer-width histograms, total byte span and original and
  rebuilt SHA-256. Up to twelve source nodes expose exact field-2 positions
  inside the original Model payload as a research aid, not surface IDs.

The in-memory output is permitted to be emitted only when **identical** to
the input. It is not an API for supplying changed records or serialized
GMP exports. Source package binaries are not written.

## Public SDK and private CLI

~~~python
from dx2sdk import DX2Map

world = DX2Map.open(r"C:\DX2\Content\DX2\Maps\ORIGINAL.gmp")
report = world.inspect_original_world_model_noop()
assert report["model_reassembled_byte_identical"]
~~~

Use the strict, read-only source-SHA-pinned CLI to save a private JSON
report **outside** your retail game Maps directory:

~~~powershell
python research/dx2/inspect_world_model_noop.py "C:\DX2\Content\DX2\Maps\ORIGINAL.gmp" --source-sha256 ORIGINAL_64_HEX_SHA256 --report "C:\DX2Research\world_model_noop.json"
~~~

Replace the placeholder SHA with the actual original file hash. The
existing DX2Map public API currently accepts the conservative UE95
licensee 68/69 source set; older research handled 65/67 separately.
No original retail packages or generated collision data are included
in the source-only SDK or Windows Godot ZIP.

## Regression scope and caveats

Asset-free synthetic tests cover a full rooted world BSP node graph,
source native zone table and original headers; two-byte noncanonical
but decodable compact encodings in node-count and individual node
records; exact source field offsets after record growth; opaque float32
bit preservation; malformed zone masks and tables; damaged source
headers, length and trailers; source-export absolute offsets and hashes;
spoofed/mismatched exported payloads; SHA-pinned CLI routing.

The **whole Model is fully byte-covered**, but that does not mean all
its fields have correct engine names or can be mutated. In particular,
the source data does **not** authenticate a native surface array,
stored BSP vertex XYZ, new world CSG cooking, Havok/MOPP collision
compilation, runtime actor Region generation or edited mission support.

The 19-map original source format research from earlier milestones is
the basis for the framing. This PR adds synthetic tests and the no-op
method; do not imply a new full 19-map empirical test occurred without
explicitly running it against private original GMPs.

This is a stricter foundation for eventual native BSP editing: first
guarantee original-source serialization is lossless, then locate the
missing native surface/vertex references, and only then attempt
isolated edited binary writers and real-game playtests.
