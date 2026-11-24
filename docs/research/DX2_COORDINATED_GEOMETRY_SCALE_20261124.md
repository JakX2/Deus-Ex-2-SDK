# Coordinated native mesh and physics hull scaling (2026-11-24)

This experiment is stacked on #208 and #209. It changes existing
geometry without changing vertex count, triangle topology, material
assignment, hardpoint rotation, auxiliary index buffers or opaque fields.
It is not arbitrary combined mesh/hull generation or runtime registration.

Original-data inspection found 330 static mesh records with the same
64-byte vertex layout and internally consistent AABB, bounding center
and radius. Of these, 113 include auxiliary vertices and indices.
All 1,288 hardpoint records match a position followed by a proper
orthonormal rotation matrix. The first three floats in each 16-byte
auxiliary vertex are finite positions, while its fourth word is opaque.

The new tool applies the same positive factor (2 or 1/2) separately
to native render positions, hardpoint translations, auxiliary XYZ
positions, bounding fields and native physics hull points. No conversion
between render and physics units is required. Directions, rotations,
unknown words and non-position metadata remain byte-identical. Each
scaled float must survive the inverse operation exactly. The original
archive and candidate must pass canonical reconstruction and all resource
checks. Unrelated resources are unchanged.

The coordinated trial selects existing type-4 records by exact case-folded
mesh name and type-5 records by the observed base-name--number convention.
It checks for a contiguous hull suffix group, explicit expected mesh and
hull counts, unique filenames, source ZIP SHA-256, and isolated output.
This name convention is a research association, not established runtime
actor binding. All output files retain their original names and are
placed under a new Maps directory with a trial receipt.

## Actual private validation

Exact source-only CI run 45334701034 passed. Its downloaded bundle
passed all 51 synthetic tests locally. Using the owner's original
Maps code.zip, all 39 named mesh/hull groups were exercised:
78 render records, 40 hull records and 117 archive scale/reverse
experiments. All passed, with exact original bytes after inverse
scaling. Both source hash checks and unrelated-resource checks passed.

One additional end-to-end disk trial for go_wine created three isolated
IBD candidates (two render copies and one hull) and verified every
candidate SHA-256 in the receipt. No game installation was modified.

## Usage

Use Python 3.11 or newer with the source-only package. For the specific
owner ZIP version, an ordinary existing-prop scale trial is:

    python tools/maps/dx2_geometry_scale.py --source-zip "C:\Owned\Maps code.zip" --source-sha256 0e97c15a30a85b7b01a256b403237e3a9216ff2b8945e1ecb126283ecc54c8ff --mesh go_wine --exponent 1 --expected-meshes 2 --expected-hulls 1 --output "C:\DX2GeometryTrial"

The output directory must not exist. An exponent of -1 halves the
geometry. Verify the original files in a separate complete disposable
game installation against the receipt before any manual trial. Close
the game between runs, back up and restore every original file, and
record render and physical behavior separately.

Mass, inertia, actor placement, physics registration, shadow-specific
runtime behavior, arbitrary mesh topology with linked collision, and
BSP compilation are NOT established. Runtime flags remain false.
No original or modified game assets are included.
