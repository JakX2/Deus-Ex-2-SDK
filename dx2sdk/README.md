# DX2SDK v0.1.0: Public Deus Ex: Invisible War Python SDK

**Status:** usable source-backed Python toolkit and experimental native
StaticMeshActor translation-only Save As. This is **not** the complete original
UnrealEd/T3Ed editor and is **not** a validated retail mission compiler.

The SDK packages existing DX2Ed reverse engineering into one documented,
reusable API plus a source-only command-line entry point. It builds on the
original DX2 v95 Unreal package reader, T3SDK's byte-identical roundtrip
support, and a narrowly limited source-pinned Location writer.

No original Deus Ex: Invisible War game files are included. Bring your own
legally obtained retail `.gmp`, `.ibd`, `TriggerScript.zip` and, where
needed, DX2Ed-generated private `actors.json` for that exact GMP.

## Windows: one-file entry point

Use the packaged **DX2SDK_CONSOLE.cmd** next to `START_DX2ED.cmd`:

```bat
DX2SDK_CONSOLE.cmd --help
DX2SDK_CONSOLE.cmd info --map "D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp"
DX2SDK_CONSOLE.cmd actors --map "D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp" --class StaticMeshActor --limit 25
```

The launcher calls the existing `CHECK_DX2ED.cmd` Python 3.11+ preflight
and uses its verified interpreter. On a repo checkout, from the repository
root, replace `DX2SDK_CONSOLE.cmd` with `python -B -m dx2sdk`.

With an exact DX2Ed-generated private actor cache:

```bat
DX2SDK_CONSOLE.cmd native-audit --map "D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp" --actors "D:\DX2EdPrivateCache\actors.json"
DX2SDK_CONSOLE.cmd scripts --map "D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp" --actors "D:\DX2EdPrivateCache\actors.json" --zip "D:\Games\DXIW\Content\DX2\Scripts\TriggerScript.zip" --filter door
```

The final ZIP location for `TriggerScript.zip` depends on your game
installation. Select the actual original file, rather than assuming the
illustrated path.

### First supported native write: existing static prop translation

The SDK takes **native DX2 world X, Y, Z** (not Godot viewport coordinates).
It supports only existing `StaticMeshActor` objects whose serialized
`Location` fields and exact source actor metadata can be independently
verified. No rotation/scale or new actor spawns are serialized.

A dry run is the default:

```bat
DX2SDK_CONSOLE.cmd move --map "D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp" --actors "D:\DX2EdPrivateCache\actors.json" --actor "StaticMeshActor__1" --x 100 --y 200 --z 300 --output "D:\DX2SDK_Experiment\M1_Test.gmp"
```

To produce an **isolated, fresh copy**, append `--write` only after inspecting
the dry run. The output filename must match the original GMP. The output
directory must be outside **every** `Content/DX2/Maps` directory and
outside the original source map's tree. Existing GMP/manifest outputs are
never overwritten.

The SDK also invokes the independent full-file byte verification before
reporting `independent_binary_verification.verified_binary_structure=true`.
You can rerun that verification later:

```bat
DX2SDK_CONSOLE.cmd verify-move --map "D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp" --output "D:\DX2SDK_Experiment\M1_Test.gmp"
```

**Important:** The writer's status is intentionally
`written-unverified`. It confirms the output has the expected native
serialization and only approved original Location float fields changed,
**not** that the retail game accepts it. Test only on isolated, backed-up
game copies, with disposable saves and no original content overwritten.

## Python API

From a checkout or extracted Windows prototype root (Python 3.11+):

```python
from dx2sdk import DX2Map

source = r"D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp"
actors_json = r"D:\DX2EdPrivateCache\actors.json"

world = DX2Map.open(source)
print(world.info())
print(world.actors(actor_class="StaticMeshActor", limit=25))

# A source-matched private actors.json is mandatory for native edits.
world = DX2Map.open(source, actors_json)

# Prepare multiple existing StaticMeshActor translation-only edits:
moves = {
    "StaticMeshActor__1": (100.0, 200.0, 300.0),
}
dest = r"D:\DX2SDK_Experiment\M1_Test.gmp"

preview = world.save_as_translations(moves, dest)  # DEFAULT: dry run!
print(preview["status"])

# Only after verifying the target is a safe, unused isolated path:
written = world.save_as_translations(moves, dest, write=True)
print(written["independent_binary_verification"])
print(world.verify_saved_translation(dest))
```

The proposed coordinates must differ from the selected actor's source
coordinates. Python scripts may submit multiple distinct actors in one plan,
up to the underlying native writer's explicit bound. All basis/rotation data
are preserved from the exact source map.

### Read-only original script resources

```python
from dx2sdk import DX2Map

world = DX2Map.open(
    r"D:\Games\DXIW\Content\DX2\Maps\M1_Test.gmp",
    r"D:\DX2EdPrivateCache\actors.json",
)
catalog = world.script_definitions(r"D:\OriginalDX2\TriggerScript.zip")
print(len(catalog["script_definitions"]))

mission = world.script_resources(
    r"D:\OriginalDX2\TriggerScript.zip",
    r"D:\OriginalDX2\Content\DX2\Maps\M1_Test.ibd",
)
print(mission["counts"])

comparison = world.compare_script_bundles(
    r"D:\OriginalDX2\TriggerScript.zip",
    r"D:\OriginalDX2\Content\DX2\Maps\M1_Test.ibd",
    r"D:\OriginalDX2\Content\DX2\Maps\Kernel_TSDALL.ibd",
)
print(comparison["counts"])
```

These methods inspect original compiled payloads and produce local Python
dictionaries. **The full comparison report includes script identities,
source hashes and other original-file metadata. Do not post it publicly**.
The CLI `ibd` and `compare` subcommands instead output aggregate summaries
without owner-original filenames or asset bytes.

## CLI commands

| Command | Original input | What it does | Writes game resources? |
|---|---|---|---|
| `info` | GMP | Original package identity, exports, versions | No |
| `actors` | GMP | List positioned actors; filter class | No |
| `scripts` | GMP + matching actors.json + TriggerScript ZIP | Read standalone source definitions | No |
| `ibd` | GMP + actors.json + ZIP + IBD | Compare named TSD and IBD payloads | No |
| `compare` | GMP + actors.json + ZIP + mission IBD + Kernel_TSDALL | Cross-bundle and original standalone TSD comparison | No |
| `native-audit` | GMP + actors.json | Source-backed writable-Location inventory | No |
| `noop-audit` | GMP | T3SDK/DX2SDK identical package roundtrip | No |
| `move` | GMP + actors.json + output | Dry-run by default; optional new isolated GMP copy with `--write` | Only new isolated copy |
| `verify-move` | Original GMP + isolated copy | Verify the approved changed native byte ranges | No |

The entry point never downloads, locates or bundles original retail content.
Passing unsupported original source structures fails closed.

## Compatibility and limits relative to T3Ed

| Editing capability | DX2SDK v0.1 |
|---|---|
| Native Ion Storm Unreal v95 GMP parsing | Implemented |
| Source-matched actor metadata and hierarchy | Implemented |
| Original script definition and IBD resource inspection | Implemented, read-only |
| T3SDK byte-identical no-op GMP reconstruction | Supported when original source passes independent parity checks |
| Native editing of existing static actor positions | Experimental isolated Save As, binary verified; retail behavior unverified |
| Arbitrary native actor spawns / clones | Separate research-only probes; **not part of public API** |
| Rotation and scale native serialization | Not implemented |
| BSP / CSG brush editing and rebuilding | Not implemented |
| Havok/MOPP collision regeneration | Not implemented |
| Native TriggerScript compile/replace/assign | Not implemented |
| Conversation resource compilation | Not implemented |
| Retail game compatibility for modified maps | **Not verified by SDK tests** |

The repository's Godot editor, separate collision/source diagnostics and
T3SDK adapter remain available alongside this public API.

## Version and distribution

- **SDK API:** `DX2SDK v0.1.0`, usable from the repository/source-only
  Windows prototype; standard-library Python 3.11+.
- **DX2Ed editor:** Godot 4.3 GUI in the same prototype ZIP, with its own
  independent feature/version development.
- **Test approach:** synthetic Ion Storm v95 package fixtures, source-hash
  spoof resistance, native writer byte range constraints, CLI invocation
  and Windows runtime package preflight.
- **Distribution:** the source-only Windows prototype includes the
  `dx2sdk/` package, launcher and the existing tested open-source readers
  and package writer. It never includes original game resources.

Planned next SDK milestones include native actor property schemas, better
roundtrip-safe native transformations, stronger original-map smoke reports,
asset placement, script-resource serialization research, and eventual
source-verified mission packaging. **Do not enable any feature as a native
writer until exact binary serialization and owner-side gameplay behavior are
independently established.**
