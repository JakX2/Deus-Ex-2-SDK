#!/usr/bin/env python3
"""DX2Ed: read-only indexed dialogue text and non-destructive edit previews.

This handles ConText.eng *source lines*, not compiled .con graphs. It does
not know which text line belongs to which .con conversation node, and it
does not compile a playable conversation.

  python tools/dialogue/dx2_dialogue_library.py index DX2mr.zip --output index.json
  python tools/dialogue/dx2_dialogue_library.py new-draft DX2mr.zip --output draft.json
  python tools/dialogue/dx2_dialogue_library.py preview DX2mr.zip --draft draft.json --output preview.eng

Draft JSON "edits" entries: {"line": 5, "original_sha256": "<from index>",
                             "replacement_text": "Replacement text"}.
Source content and original game installations are never modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

SCHEMA = "DX2Ed-dialogue-source-index-v1"
DRAFT_SCHEMA = "DX2Ed-dialogue-text-draft-v1"
MAX_SOURCE_BYTES = 12 * 1024 * 1024
LINE = re.compile(r'^(?P<prefix>\s*[A-Za-z_][A-Za-z0-9_]*:\s*")(?P<text>.*)(?P<suffix>"\s*)$')


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def load_source(path: Path, *, encoding: str = "utf-8") -> dict:
    """Load one ConText.eng from a local file or ZIP; never extract archives."""
    if not path.is_file():
        raise ValueError(f"Source file not found: {path}")
    if path.suffix.casefold() == ".zip":
        with zipfile.ZipFile(path) as archive:
            matches = [i for i in archive.infolist()
                       if not i.is_dir() and i.filename.replace("\\", "/").casefold()
                       .endswith("/conversations/english/context.eng")]
            # Some user's archives have ConText.eng at the archive root.
            matches.extend(i for i in archive.infolist()
                           if not i.is_dir() and i.filename.casefold() == "context.eng")
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one English ConText.eng in ZIP, found {len(matches)}")
            member = matches[0]
            if member.file_size > MAX_SOURCE_BYTES:
                raise ValueError("Conversation source exceeds safety size limit")
            raw = archive.read(member)
            identity = member.filename
    else:
        if path.name.casefold() != "context.eng":
            raise ValueError("Standalone input must be named ConText.eng")
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("Conversation source exceeds safety size limit")
        raw = path.read_bytes()
        identity = path.name
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Conversation source exceeds safety size limit")
    text = raw.decode(encoding, errors="strict")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "1":
        raise ValueError("Unexpected ConText.eng header (expected version 1)")
    return {"path": path, "member": identity, "sha256": digest(raw),
            "encoding": encoding, "raw": raw, "lines": lines}


def classify(line: str, number: int) -> dict:
    """Preserve exact source line number and hash; never invent conversation IDs."""
    without_eol = line.rstrip("\r\n")
    result = {"line": number, "raw_sha256": digest(line.encode("utf-8")),
              "kind": "unknown"}
    if number == 1 and without_eol == "1":
        result["kind"] = "header"
    elif not without_eol.strip():
        result["kind"] = "blank"
    elif without_eol.lstrip().startswith("//"):
        result.update(kind="comment", text=without_eol)
    else:
        m = LINE.fullmatch(without_eol)
        if m:
            speaker = m.group("prefix").split(":", 1)[0].strip()
            result.update(kind="choice" if speaker.casefold() == "choice" else "spoken",
                          speaker=speaker, text=m.group("text"))
        else:
            result.update(kind="unparsed", text=without_eol)
    return result


def index_source(source: dict) -> dict:
    # Hashes for drafts must follow the user's selected encoding, not UTF8
    # for the source text when an alternate encoding was supplied.
    records = []
    for n, line in enumerate(source["lines"], 1):
        record = classify(line, n)
        record["raw_sha256"] = digest(line.encode(source["encoding"]))
        records.append(record)
    by_kind = Counter(x["kind"] for x in records)
    speakers = Counter(x["speaker"] for x in records if x["kind"] in ("spoken", "choice"))
    return {
        "schema": SCHEMA,
        "read_only": True,
        "compiled_con_graph_decoded": False,
        "game_runtime_editing_supported": False,
        "source_member": source["member"],
        "source_sha256": source["sha256"],
        "source_encoding": source["encoding"],
        "source_line_count": len(records),
        "counts_by_kind": dict(sorted(by_kind.items())),
        "counts_by_speaker": dict(sorted(speakers.items(), key=lambda x: x[0].casefold())),
        "warnings": [
            "These are original ConText.eng text lines, not .con node links or gameplay order.",
            "Choice lines are source labels only; branching conditions are not decoded.",
            "A draft preview is not a cooked game dialogue file."
        ],
        "lines": records,
    }


def new_draft(source: dict) -> dict:
    return {
        "schema": DRAFT_SCHEMA,
        "source_member": source["member"],
        "source_sha256": source["sha256"],
        "source_encoding": source["encoding"],
        "read_only_source": True,
        "game_runtime_editing_supported": False,
        "edits": [],
    }


def preview_changes(source: dict, draft: dict) -> tuple[bytes, dict]:
    """Apply only quoted text spans to a new preview; never rewrite a source."""
    if not isinstance(draft, dict) or draft.get("schema") != DRAFT_SCHEMA:
        raise ValueError("Invalid dialogue draft schema")
    if (draft.get("source_sha256") != source["sha256"] or
            draft.get("source_member") != source["member"] or
            draft.get("source_encoding") != source["encoding"]):
        raise ValueError("Draft source identity/hash mismatch; refusing stale edits")
    edits = draft.get("edits")
    if not isinstance(edits, list):
        raise ValueError("Draft edits must be a list")
    lines = list(source["lines"])
    seen = set()
    changed = []
    for item in edits:
        if not isinstance(item, dict):
            raise ValueError("Each edit must be an object")
        line = item.get("line")
        if type(line) is not int or line < 2 or line > len(lines) or line in seen:
            raise ValueError(f"Invalid or repeated source line number: {line!r}")
        seen.add(line)
        original = source["lines"][line-1]
        if digest(original.encode(source["encoding"])) != item.get("original_sha256"):
            raise ValueError(f"Original line hash mismatch at line {line}")
        m = LINE.fullmatch(original.rstrip("\r\n"))
        if not m:
            raise ValueError(f"Line {line} is not a supported spoken/choice line")
        replacement = item.get("replacement_text")
        if not isinstance(replacement, str) or len(replacement) > 4096 or any(
            c in replacement for c in "\r\n\0"
        ):
            raise ValueError(f"Invalid replacement dialogue on line {line}")
        # Preserve the original speaker, quotes, spacing and line-ending.
        eol = original[len(original.rstrip("\r\n")):]
        modified = m.group("prefix") + replacement + m.group("suffix") + eol
        try:
            modified.encode(source["encoding"], errors="strict")
        except UnicodeError as error:
            raise ValueError(f"Replacement not representable in {source['encoding']}") from error
        lines[line-1] = modified
        changed.append({"line": line, "speaker": m.group("prefix").split(":", 1)[0].strip(),
                        "original_sha256": item["original_sha256"],
                        "preview_sha256": digest(modified.encode(source["encoding"]))})
    return "".join(lines).encode(source["encoding"]), {
        "schema": "DX2Ed-dialogue-preview-report-v1",
        "source_sha256": source["sha256"], "preview_edit_count": len(changed),
        "changes": sorted(changed, key=lambda x: x["line"]),
        "native_con_compiled": False, "original_source_modified": False,
    }


def write_distinct(output: Path, inputs: list[Path], content: bytes):
    if output.resolve() in {p.resolve() for p in inputs}:
        raise ValueError("Output must differ from every input; refusing in-place edit")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)


def cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for cmd in ("index", "new-draft", "preview"):
        p = sub.add_parser(cmd)
        p.add_argument("source", type=Path, help="ConText.eng or ZIP containing it")
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--encoding", default="utf-8")
        if cmd == "preview":
            p.add_argument("--draft", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        source = load_source(args.source, encoding=args.encoding)
        if args.command == "index":
            document = index_source(source)
            content = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            inputs = [args.source]
            summary = {"source_lines": document["source_line_count"], "counts": document["counts_by_kind"]}
        elif args.command == "new-draft":
            content = (json.dumps(new_draft(source), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            inputs = [args.source]
            summary = {"edits": 0}
        else:
            draft = json.loads(args.draft.read_text(encoding="utf-8"))
            content, summary = preview_changes(source, draft)
            inputs = [args.source, args.draft]
        write_distinct(args.output, inputs, content)
        print(json.dumps({"status":"ok", "output":str(args.output), **summary}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(json.dumps({"status":"error", "message":str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
