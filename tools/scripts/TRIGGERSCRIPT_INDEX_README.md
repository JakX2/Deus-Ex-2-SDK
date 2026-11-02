# DX2Ed TriggerScript Source Inventory (read-only)

This tool inspects the user's **original** `TriggerScript.zip` and
optional DX2Ed `actors.json`. It extracts *source-declared symbols* and
names without claiming to parse the runtime expression tree or native
script/actor bindings. It does **not** modify the game.

## Use it on original archives

From the repository root (Python 3.11+), where
`DX2restofstuff(2).zip` is the user's archive containing
`TriggerScript.zip`:

```powershell
python tools/scripts/dx2_trigger_script_index.py "C:\DX2Files\DX2restofstuff(2).zip" --output "C:\DX2EdResearch\triggers.json"
python tools/scripts/dx2_trigger_script_index.py "C:\DX2Files\DX2restofstuff(2).zip" --actors "C:\DX2EdCache\WTO\actors.json" --format html --output "C:\DX2EdResearch\triggers.html"
```

Alternatively use the standalone original `TriggerScript.zip` as input.
Open `triggers.html` in a web browser. It is completely **offline** and
has a script-name/title/symbol search, an active/deleted source filter,
and a separate view of unresolved actor script arrays (when supplied).

### Observed definitions in supplied original archive

- **3,263** TSD files; **2,645** located under `Defs/` and
  **618** under `DeletedScripts/` (historical/deleted source).
- Headers: **2,889** `1FFE2FST`, **373** `0FFE2FST`,
  **one** `0FFE1FST`. The latter is `DeletedScripts/ScriptDefs.tsd`,
  with unusual name content.
- Readable token categories: **133 unique** `kTCT_` condition
  tokens, **244 unique** `kTAT_` action tokens, and **23 unique**
  `kTPT_` parameter-type tokens.
- Examples include `kTCT_FrobByPlayer`, `kTCT_FlagSet`,
  `kTCT_OnMapStart`, `kTAT_SetFlag`, `kTAT_CompleteGoal`,
  `kTAT_SendTriggerMsg`, and `kTAT_TeleportPlayerToMap`.

The tool reports **string occurrences and byte offsets** recovered from
the UTF-16LE source fields. It does **not** prove that two neighboring
tokens belong to one condition/action node, or how conditions are
combined, whether actions execute, or which map actor owns them.
The source file label after the name is only a display-label hint.

### Original WTO actor reference boundary

In the user's cached `M1_Seattle_Hub_WTOterminal.gmp` actors.json,
**19 actors** carry property ID 92 as a serialized index array containing
**26 numeric indices** in total. Those are not yet verified names or
IDs of `TS_...tsd` resources. The browser deliberately displays them
separately with status `unresolved_script_index_array` and **does
not link them to guessed TSD filenames**.

The index preserves the input archive identity, script source hashes,
raw symbolic byte offsets and map source hash, where provided.

## Original ScriptOrganizer.tso hierarchy

When the original archive includes `Organize/ScriptOrganizer.tso`,
the source index now validates and imports the actual nested folder trees
instead of guessing categories from `TS_` numeric suffixes.

The original file is ASCII TSO **version 2**. It contains exactly three
`HeaderBegin` trees (scripts, conditions, actions), with a declared
child count for each folder. A `0` record starts a folder, while a
`1` record identifies a script/symbol entry. The parser rejects
truncated nodes, invalid record tags, excessive depth, unsupported
versions and unexpected trailing text.

Verified source counts:

| Tree | Original organizer leaf entries | Distinct entries | Folders |
|---|---:|---:|---:|
| Script sources | 2,646 | 2,645 | 121 |
| Condition symbols | 154 | 154 | 25 |
| Action symbols | 277 | 277 | 43 |

All **2,645 active `Defs/*.tsd` source filenames** occur in the
ScriptOrganizer source tree. No orphan organizer names or unlisted active
definitions were found. The extra leaf is a deliberate/repeated
`TS_2316` organizer entry: it appears twice in different paths.
A single original definition may legitimately have multiple organizer
paths. Historical `DeletedScripts/` sources are not automatically
assigned to active categories.

**The browser now provides **three source browsing modes**:
**Script definitions**, **Condition palette**, and **Action palette**.
Each has its own hierarchy-based original category filter. Source
definitions display their precise organizer folder paths. The condition
and action palettes show which active TSD source definitions contain
a given symbol name as text. These matches do **not** establish runtime
graph connections or executed events.

These folders describe original authoring organization, **not** the
game's runtime condition/action execution order, actor bindings or event
graph topology. Category names such as `M1_Seattle` are directory labels,
not proof that every contained script runs in that map.

If the archive lacks the organizer, the index still works but leaves
all source categories explicitly unknown.

## Known limitations and next steps

1. Decode binary TSD nodes/condition expressions/branch order, preserving
   all unrecognized bytes.
2. Determine whether property 92 indices resolve through the game package
   name table, a distinct scripting table, or a mission registry.
   Validate against more than one map and bundled TSD before naming links.
3. Link verified actor exports to script definitions and event/flag
   references. Don't infer links from matching numeric suffixes.
4. Add a genuinely editable, versioned event graph **draft** only after
   binary object identities and validation rules are understood.
5. Repack native scripts into **new** test resources and confirm runtime
   behavior in a disposable game installation before calling edits playable.

### Synthetic tests

```powershell
python -m unittest discover -s tests -p "test_trigger_script_index.py" -v
```

No proprietary TSD, GMP or IBD contents are committed to GitHub.
