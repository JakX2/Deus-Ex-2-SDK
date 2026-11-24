# Experimental fixed-width polygon UV translation

All 76,732 expanded vertices in the 19 original Seattle maps have four
byte-identical 8-byte UV pairs at record-relative offsets 24, 68, 76 and
84; the intervening 36 bytes at +32 are zero. The corresponding packed
32-byte render vertex has primary UV at +16 and a distinct secondary pair
at +24. The role of the latter is not decoded here and it is untouched.

The source-pinned experimental UV translator accepts a single expanded
polygon ordinal and a finite bounded float32-representable translation.
It updates the four matching expanded pairs and corresponding packed
primary pair for each vertex, preserving the whole-repeat UV relationship.
A full package reparse verifies all polygon links, Model bytes, package
tables, collision tail and MOPP attribution; reversal of the precise
source bytes must restore the complete original GMP.

Run from the SDK root with root, map_exporter and research/dx2 on PYTHONPATH:

    python research/dx2/experimental_polygon_uv.py MAP.gmp --expected-sha256 SHA --polygon 0 --delta 0.125 0.25

The default is an in-memory dry run. Optional --output permits only a fresh
isolated private file with the same basename outside the original map
directory and game Content/DX2/Maps. It is never installed automatically.
Retain the original file; the exact reverse proof uses original raw spans,
not floating-point subtraction of a translation.

This is a controlled native render-data patch, NOT native BSP geometry
editing, surface ownership decoding, collision rebuilding, or runtime
verification. No retail assets or edited packages belong in git or CI.
