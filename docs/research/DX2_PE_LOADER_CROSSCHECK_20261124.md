# DX2 independent PE loader cross-check — 2026-11-24

## Why

The original Ghidra keyword survey remains reproducible (the 2026-11-24
hosted artifact from run 45313385819 has the same report SHA-256 as the
initial report). But string hits alone are an incomplete search strategy.
For example, the survey reported no IBD candidates. We need an independent,
cheap check before deciding what to investigate in the native map loader.

## Implementation and actual owner-input observation

`tools/ghidra/pe_loader_crosscheck.py` authenticates the owner-provided
DX2Main.exe against the committed pin and validates the existing two-module
Ghidra summary. It parses PE32 sections and the normal KERNEL32 import
directory, decodes executable sections with GNU objdump, and checks
relevant decoded instruction bytes against the PE. It identifies
NUL-terminated literal anchors in file-backed non-executable sections,
counts immediate and absolute-memory references, and counts direct
relative calls/jumps to the selected Ghidra candidates. A conservative
straight-line import-slot tracking rule recognizes direct and
register-indirect calls to the two allowlisted Windows file APIs.

Actual private local run on the SHA-pinned DX2Main.exe from the owner's
System.zip, using the already generated Ghidra report:

| Anchor | Exact literal locations | Immediate references | Absolute-memory references |
| --- | ---: | ---: | ---: |
| GMP extension | 1 | 4 | 0 |
| Entry GMP path | 1 | 1 | 0 |
| IBD extension | 1 | 4 | 5 |
| IBDM extension | 1 | 1 | 0 |
| Package failure marker | 1 | 1 | 0 |
| Static mesh actor class-name suffix | 1 | 1 | 0 |

Three IBD references occur within 128 bytes of a recognized CreateFileA
call site; three occur within 128 bytes of a recognized GetFileAttributesA
call site. These are **proximity observations**, not proof that those
calls consume that specific literal.

| Ghidra keyword | Candidates | Candidates with direct calls | Direct call sites |
| --- | ---: | ---: | ---: |
| GMP | 1 | 1 | 8 |
| IBD | 0 | 0 | 0 |
| StaticMeshActor | 0 | 0 | 0 |
| GameSys | 5 | 3 | 7 |
| Serialize | 4 | 2 | 4 |
| LoadPackage | 1 | 0 | 0 |

The LoadPackage keyword candidate is within 32 bytes of the package-failure
literal reference. It should **not** be promoted to a callable loader entry
on the strength of the keyword match. In contrast the GMP candidate has
eight independently decoded direct calls. The IBD result shows why a
literal/operand search supplements the Ghidra defined-string survey.
The actor-name reference is a lead for class registration investigation,
not proof of the registration or serialization routine.

The local independent cross-check completed in about five seconds on
this environment. The scheduled workflow integration is proposed in this
branch and is not yet an observed hosted original run.

## Tests and privacy

Synthetic PE32 regression fixtures exercise real objdump decoding of
relative calls, jumps, literal immediates and memory references, named
import slots and register clobbers. The report has fixed keys, bounded
research categories, counts only, and explicit false flags for runtime,
loader, actor-registration verification and asset inclusion.

The report does not include original bytes, disassembly, raw discovered
strings, addresses, private file paths or function bodies. The hosted
workflow proposes an explicit single-file aggregate artifact, generated
after original hash verification and validated Ghidra metadata, before
scratch deletion. No new raw address artifacts are introduced.

This remains static analysis. Linear disassembly can misclassify embedded
data and proximity is not a control-flow relationship. No native writer,
BSP compiler, or retail gameplay behavior is verified by these counts.

## Next technical target

Follow the actual GMP call sites and distinguish normal map opening from
entry-map fallback and error logging. For IBD, follow the verified
file-API neighborhoods toward archive header parsing. For StaticMeshActor,
establish the class-name reference's containing function and its caller
context before claiming native actor registration. Any candidate writer
change must be checked against real package bytes and, ultimately,
observed in the retail engine.
