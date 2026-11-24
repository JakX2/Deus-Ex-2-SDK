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

## Experimental diagonal operand refit

A separate opt-in mode uses the existing source-derived diagonal projection
hypotheses to derive the minimum/maximum integer operand constraints on
all original and changed triangle corners along their original paths.
It refuses any source violation, unknown 0x1b opcode or infeasible bound.
Only diagonal operand bytes may change; an independently decoded original
control-flow graph and exact reverse proof are required. It runs only
following an accepted axis refit. No candidate package is emitted.

    python research/dx2/inspect_vbsp_coupled_corners.py MAP.gmp --delta-d 1 --refit-derived-diagonals

The same 38 signed experiments on the private 19-map corpus reproduced all
36 accepted axis refits. Each also passed the experimental diagonal refit.
For +1, four streams required seven additional diagonal byte changes;
for -1, two streams required seven additional diagonal byte changes.
All 1,673 positive and 1,631 accepted negative candidate point samples
were recovered by the independent derived-diagonal walker. The prior 30
derived-diagonal misses were eliminated. The two unrepresentable negative
axis candidates remain refused. Three additional synthetic tests passed.
This is still a source-model result, not verification of Havok's actual
integer arithmetic, diagonal semantics, swept collision or retail loading.
The combined axis-only geometry/header gate is not upgraded by this mode.

## Local rescale-coordinate recovery

The two negative-axis refusals are local unsigned filter underflows, not
root origin errors. A separate bounded experimental rebase searches nearby
ancestor rescale coordinate bytes (at most 32 single-byte trials, offsets
within four units), then recomputes all source-tree axis and experimental
diagonal operand intervals in that new coordinate system. The original
source paths must pass before search, and every candidate path must pass
afterward. Control-flow comparison deliberately excludes the changed local
spatial affine transforms but includes opcode, size, original PC/base,
ordered destinations and terminal triangle ownership. All unrelated bytes
must reverse exactly. Shared path contexts are refused.

Private targeted verification: both formerly refused -1 candidates now
pass in their first trial, each changing one rescale byte. The upper lab
requires three additional spatial bytes; the club requires two. All 140
affected-triangle point comparisons pass both original offline query modes.
The club still fails the coupled geometry gate. Four synthetic tests pass.
No root quantization change, instruction relocation, native output or
Havok runtime verification is implied. Integrated corpus validation pending.

    python research/dx2/inspect_vbsp_coupled_corners.py MAP.gmp --delta-d -1 --rebase-rescale-offsets
