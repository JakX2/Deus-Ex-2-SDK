# DX2Ed Dialogue Source Library (research)

This tool provides an offline, **source-faithful** browser and non-destructive
text-editing preview for the user's original
Conversations/English/ConText.eng resource.

It accepts a standalone ConText.eng or a ZIP with exactly one
Conversations/English/ConText.eng (e.g. DX2mr.zip).

**This is not a .con compiler, a branching conversation graph editor or
a playable game patcher.** Original .con files encode additional links and
conditions that remain undecoded. Source text order is not the in-game
execution order; a Choice: label does not reveal its gameplay branch.

## 1. Browse dialogue offline

Run from the repository root with Python 3.11+:

    python tools/dialogue/dx2_dialogue_library.py html "C:\your-files\DX2mr.zip" --output "C:\DX2EdResearch\dialogue.html"
    python tools/dialogue/dx2_dialogue_library.py index "C:\your-files\DX2mr.zip" --output "C:\DX2EdResearch\dialogue.json"

Open dialogue.html in a browser. It is entirely offline: search lines,
filter speakers, and show spoken lines, choice labels or developer comments.

The JSON index has exact one-based line numbers and line SHA-256 values.
For ZIP input the index also lists every .con filename, length, hash,
raw header variant and header-declared payload size. The reported
map_filename_hint is **not an independently verified game link**.
No .con node link, event, branch or runtime flag is invented.

## 2. Make a safe dialogue text draft

    python tools/dialogue/dx2_dialogue_library.py new-draft "C:\your-files\DX2mr.zip" --output "C:\DX2EdResearch\dialogue-draft.json"

Open dialogue-draft.json and add edits under the "edits" array, using
the line number and original raw_sha256 from dialogue.json, e.g.:

    {
      "line": 42,
      "original_sha256": "COPY_THE_LINE_RAW_SHA256_FROM_YOUR_INDEX",
      "replacement_text": "Replacement line."
    }

Do not change source_sha256, source_member or source_encoding.
The line number refers to ConText.eng **source text**, not a .con node.
Only dialogue/choice text within the source double quotes is editable.
Speaker labels, comments and LF/CRLF line endings are preserved.

    python tools/dialogue/dx2_dialogue_library.py preview "C:\your-files\DX2mr.zip" --draft "C:\DX2EdResearch\dialogue-draft.json" --output "C:\DX2EdResearch\preview.eng"

The command refuses stale source hashes, changed original line hashes,
duplicate edit lines, unsafe multiline replacements, and in-place
source overwrites. A preview file cannot be called ConText.eng.

**The preview is not compiled into a playable .con file.** Do not put
this output into the game installation.

## Original resource observations

The supplied ConText.eng has 2,800 source lines: 2,592 spoken,
61 Choice:, 144 developer comments, two blank and one format header.
There are 184 distinct speaker/label names including Choice.

The user's English conversation archive has 62 .con files:
61 with magic 1FFE1NOC and one with 0FFE1NOC.
Both are catalogued as container metadata, not decoded graphs.

No proprietary dialogue, .con or .eng files are checked into GitHub.

## Next engineering milestones

1. Decode .con nodes/conditions/transitions with strict validation,
   preserving unknown bytes instead of guessing.
2. Correlate compiled references to ConText.eng lines only when proven.
3. Cross-reference verified conversation events with native map actors,
   TriggerScript assets, and game flags.
4. Build a non-destructive event/dialogue graph editor, then research
   verified original-game serialization separately.

Synthetic tests:

    python -m unittest discover -s tests -p "test_dialogue_library.py" -v
