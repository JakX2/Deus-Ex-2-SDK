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
                       if not i.is_dir() and (
                           i.filename.replace("\\", "/").casefold()
                           .endswith("/conversations/english/context.eng")
                           or i.filename.replace("\\", "/").casefold()
                           in ("conversations/english/context.eng", "context.eng")
                       )]
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


def conversation_inventory(source_path: Path) -> list[dict]:
    """List compiled .con containers in the same ZIP without decoding graphs.

    The 0FFE/1FFE header variants are recorded literally; a size header
    matching file length does NOT establish correct branch/condition parsing.
    """
    if source_path.suffix.casefold() != ".zip":
        return []
    records = []
    with zipfile.ZipFile(source_path) as archive:
        for member in archive.infolist():
            if member.is_dir() or not member.filename.casefold().endswith(".con"):
                continue
            if member.file_size > MAX_SOURCE_BYTES:
                raise ValueError("Compiled conversation exceeds safety size limit")
            raw = archive.read(member)
            magic = raw[:8]
            declared = int.from_bytes(raw[12:16], "little") if len(raw) >= 16 else None
            records.append({
                "member": member.filename,
                "map_filename_hint": Path(member.filename).stem + ".gmp",
                "bytes": len(raw),
                "sha256": digest(raw),
                "header_variant": magic.decode("ascii", errors="replace"),
                "recognized_container_header": magic in (b"0FFE1NOC", b"1FFE1NOC"),
                "declared_payload_bytes": declared,
                "declared_size_matches_file": declared == len(raw) - 16 if declared is not None else False,
                "graph_decoded": False,
                "map_link_verified": False,
            })
    return sorted(records, key=lambda r: r["member"].casefold())


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
        "compiled_con_files": conversation_inventory(source["path"]),
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


def render_html(document: dict) -> str:
    """Portable offline browser. All source strings enter the DOM as text."""
    payload = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace("&", "\\u0026")
    template = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DX2Ed Dialogue Source Browser</title>
<style>
:root{font:14px Segoe UI,system-ui,sans-serif;color:#e0ebfa;background:#111b28;color-scheme:dark}
*{box-sizing:border-box}body{margin:0}header{padding:17px 22px;background:#1b2b3c;border-bottom:1px solid #34465a}
h1{font-size:19px;margin:0 0 7px}small,.muted{color:#a0b8cf}main{max-width:1200px;margin:0 auto;padding:18px}
.tools{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:16px}input,select{background:#1d3043;color:#e6f4ff;padding:10px;border:1px solid #465e75;border-radius:6px}
input{flex:1;min-width:240px}.row{border-bottom:1px solid #2d3e50;padding:11px 10px;display:grid;grid-template-columns:80px minmax(80px,160px) 1fr;gap:12px;align-items:start}
.row:nth-child(even){background:#172536}.row .line{color:#82a8c6;font-variant-numeric:tabular-nums}.row .speaker{color:#92d5fa;font-weight:600;word-break:break-word}
.row.comment .speaker{color:#e6b96d}.row.choice .speaker{color:#ecbafa}.row .content{overflow-wrap:anywhere;white-space:pre-wrap}
#out{border:1px solid #354b61;border-radius:8px;overflow:hidden}.hint{margin:10px 0;color:#bed1e4}
@media(max-width:700px){.row{grid-template-columns:52px 100px 1fr;gap:6px}}
</style></head><body>
<header><h1>DX2Ed Dialogue Source Browser</h1><small id="source"></small></header>
<main><p class="hint">Source text only. Line order does not establish game dialogue branching or event conditions.</p>
<div class="tools"><input id="query" placeholder="Search lines, speakers and developer comments" aria-label="Search dialogue">
<select id="speaker" aria-label="Filter speaker"><option value="">All speakers</option></select>
<select id="kind" aria-label="Filter kind"><option value="">All line types</option><option value="spoken">Spoken</option><option value="choice">Choice labels</option><option value="comment">Developer comments</option></select></div>
<div class="hint" id="count"></div><div id="out"></div><p class="hint" id="footer"></p></main>
<script id="dialogue-data" type="application/json">__DATA__</script>
<script>
(function(){
"use strict";
const doc=JSON.parse(document.getElementById("dialogue-data").textContent);
const rows=doc.lines,out=document.getElementById("out"),query=document.getElementById("query"),speaker=document.getElementById("speaker"),kind=document.getElementById("kind");
document.getElementById("source").textContent=doc.source_member+" · "+doc.source_line_count+" lines · "+doc.compiled_con_files.length+" compiled .con containers (metadata only)";
document.getElementById("footer").textContent="Compiled .con branching and TriggerScript execution are not decoded. Source SHA-256: "+doc.source_sha256;
Object.keys(doc.counts_by_speaker).sort().forEach(function(name){let o=document.createElement("option");o.value=name;o.textContent=name;speaker.appendChild(o);});
function el(tag,content,cls){let e=document.createElement(tag);e.textContent=content;if(cls)e.className=cls;return e;}
function draw(){let q=query.value.toLocaleLowerCase(),sp=speaker.value,k=kind.value;
let rowsFound=rows.filter(function(r){return (!sp||r.speaker===sp)&&(!k||r.kind===k)&&(!q||((r.speaker||"")+" "+(r.text||"")).toLocaleLowerCase().includes(q));});
document.getElementById("count").textContent=rowsFound.length+" / "+rows.length+" matching source lines; showing at most 350.";
out.replaceChildren();let frag=document.createDocumentFragment();
rowsFound.slice(0,350).forEach(function(r){let item=el("div","","row "+r.kind);
item.appendChild(el("div","#"+r.line,"line"));item.appendChild(el("div",r.speaker||r.kind,"speaker"));
item.appendChild(el("div",r.text||"","content"));frag.appendChild(item);});out.appendChild(frag);}
query.addEventListener("input",draw);speaker.addEventListener("change",draw);kind.addEventListener("change",draw);draw();
})();
</script></body></html>'''
    return template.replace("__DATA__", payload)


def write_distinct(output: Path, inputs: list[Path], content: bytes):
    if output.resolve() in {p.resolve() for p in inputs}:
        raise ValueError("Output must differ from every input; refusing in-place edit")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)


def cli(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for cmd in ("index", "html", "new-draft", "preview"):
        p = sub.add_parser(cmd)
        p.add_argument("source", type=Path, help="ConText.eng or ZIP containing it")
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--encoding", default="utf-8")
        if cmd == "preview":
            p.add_argument("--draft", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        source = load_source(args.source, encoding=args.encoding)
        if args.command in ("index", "html"):
            document = index_source(source)
            content = ((json.dumps(document, ensure_ascii=False, indent=2) + "\n")
                       if args.command == "index" else render_html(document)).encode("utf-8")
            inputs = [args.source]
            summary = {"source_lines": document["source_line_count"], "counts": document["counts_by_kind"],
                       "compiled_con_files": len(document["compiled_con_files"])}
        elif args.command == "new-draft":
            content = (json.dumps(new_draft(source), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            inputs = [args.source]
            summary = {"edits": 0}
        else:
            if args.output.name.casefold() == "context.eng":
                raise ValueError("Preview output must not be named ConText.eng (use preview.eng)")
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
