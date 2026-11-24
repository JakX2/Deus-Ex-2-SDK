# Fixed-width original MOPP axis-operand refit

Research-only, in-memory. The refitter independently traces the original
control-flow graph, carrying exact integer affine rescale factors and biases.
For every original leaf ID, the complete triangle is bounded in quantized
root space. Bottom-up subtree extrema constrain all original axis splits
and filters, including 24-bit operands. A half split must satisfy both
children simultaneously. Original source path coverage is mandatory.
The nearest representable operand is chosen only where needed; an empty
integer interval refuses the candidate. Candidate bytecode is independently
decoded; all opcodes, widths, destinations, rescale operands, output bases,
terminal IDs, diagonal operands and opaque bytes must remain unchanged.
Replacing the changed operand spans restores the original code exactly.

The original one-unit interpreter margin is part of this hypothesis; the
complete affine path inequalities are not proof of retail Havok arithmetic.
No collision package is emitted. Source-wide diagonal projection comparisons
are separately diagnostic, never taken as runtime truth.

    python research/dx2/inspect_vbsp_coupled_corners.py MAP.gmp --delta-d 1 --refit-axis-bounds

Use root, map_exporter and research/dx2 on PYTHONPATH.

## Private corpus validation

19 original Seattle maps, one deterministic plane per map, offsets +1 and
-1. Source coverage at every axis operand passed all maps (120,697 operands).
Accepted candidate subsets retain all original triangle IDs and unchanged
source origin/scale; the candidate header formula is a separate gate.

| Offset | Axis refits passed | Changed streams | Changed bytes | Accepted triangle point samples | Axis sample misses | Combined geometry/header/axis gate | Derived diagonal sample misses |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +1 | 19/19 | 8 | 10 | 1673 | 0 | 8 | 17 |
| -1 | 17/19 | 4 | 8 | 1631 | 0 | 9 | 13 |

The two refusals have unrepresentable unsigned lower-bound operands (three
infeasible filters total). No truncation or clamping past feasible limits.
Across each signed sweep, all 451,638 source diagonal vertex/path tests
passed the current hypothesized projections, with no original violations.
The changed subsets introduced 13 and 17 diagonal violations respectively
(nine affected triangles each), including samples where the conservative
axis-only interpreter still finds the intended ID. A successful axis refit
therefore cannot authorize native map output; the diagonal model needs
further verification and refitting, and Model, portal, shadow, navigation
and full Havok runtime validation remain outstanding. No original assets
modified or committed. Seven synthetic regression tests passed locally.
