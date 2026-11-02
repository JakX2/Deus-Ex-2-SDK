#!/usr/bin/env python3
"""Read-only TriggerScript source-symbol inventory and unresolved actor references.

Index original .tsd definitions from TriggerScript.zip (or an outer ZIP
containing TriggerScript.zip). Optionally inspect existing DX2Ed actors.json.

The string table is NOT an executed event graph: the format's binary
expression tree, node ownership, branch order, and runtime object bindings
have not been decoded. No source assets are written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

from dx2_script_organizer import parse_organizer, attach_organizer_index

SCHEMA = "DX2Ed-trigger-symbol-index-v1"
ACTOR_SCHEMA = "DX2Ed-unresolved-script-references-v1"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_SCRIPT_BYTES = 4 * 1024 * 1024
TSD_MAGIC = {b"1FFE2FST": 16, b"0FFE2FST": 12, b"0FFE1FST": 12}
TOKENS = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _read_nested_or_direct_zip(path: Path) -> tuple[bytes, str]:
    if not path.is_file():
        raise ValueError("Script archive does not exist")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Outer archive exceeds size limit")
    raw = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        candidate = [m for m in archive.infolist() if not m.is_dir()
                     and Path(m.filename.replace("\\", "/")).name.casefold() == "triggerscript.zip"]
        has_direct_definitions = any(
            m.filename.replace("\\", "/").casefold().startswith(("defs/", "deletedscripts/"))
            and m.filename.casefold().endswith(".tsd") for m in archive.infolist())
        if has_direct_definitions:
            return raw, path.name
        if len(candidate) != 1:
            raise ValueError("Archive must contain .tsd definitions or exactly one TriggerScript.zip")
        if candidate[0].file_size > MAX_ARCHIVE_BYTES:
            raise ValueError("Nested TriggerScript archive exceeds size limit")
        return archive.read(candidate[0]), candidate[0].filename


def _read_utf16_zero_string(blob: bytes, offset: int, limit: int = 256) -> str | None:
    chars = []
    for i in range(offset, min(len(blob) - 1, offset + 2 * limit), 2):
        num = struct.unpack_from("<H", blob, i)[0]
        if num == 0:
            return "".join(chars) if chars else None
        if not 32 <= num < 127:
            return None
        chars.append(chr(num))
    return None


def parse_tsd(data: bytes, name: str, *, deleted: bool) -> dict:
    if len(data) < 16 or data[:8] not in TSD_MAGIC:
        raise ValueError(f"{name}: unknown or truncated TSD header")
    header_bytes = TSD_MAGIC[data[:8]]
    declared = struct.unpack_from("<I", data, header_bytes - 4)[0]
    if declared != len(data) - header_bytes:
        raise ValueError(f"{name}: declared payload length mismatch")
    if header_bytes == 16 and struct.unpack_from("<I", data, 8)[0] != 0:
        raise ValueError(f"{name}: unexpected v1 TSD prefix")
    # Both header variants contain a 32-bit field (0x10 in retail files)
    # before the first UTF-16LE script name. It is not part of the name.
    source_name = _read_utf16_zero_string(data, header_bytes + 4)
    if source_name is None:
        # Some original deletion/metadata stubs may lack a normal name.
        source_name = None
    texts = []
    for m in TOKENS.finditer(data, header_bytes):
        word = m.group(0).decode("utf-16le")
        texts.append({"offset": header_bytes + m.start(), "text": word})
    symbol_hits = {"condition": [], "action": [], "parameter_type": []}
    for word in texts:
        text = word["text"]
        group = ("condition" if text.startswith("kTCT_") else
                 "action" if text.startswith("kTAT_") else
                 "parameter_type" if text.startswith("kTPT_") else None)
        if group is not None:
            symbol_hits[group].append(word)
    return {
        "member": name, "deleted_source": deleted,
        "raw_sha256": sha256(data), "bytes": len(data),
        "header_magic": data[:8].decode("ascii"),
        "header_payload_length_matches": True,
        "source_name": source_name,
        "filename_stem": Path(name).stem,
        "embedded_name_matches_filename": (source_name.casefold() == Path(name).stem.casefold()
                                           if source_name else False),
        "display_label_hint": next((t["text"] for t in texts if t["text"] != source_name
                                    and not t["text"].startswith(("kTCT_", "kTAT_", "kTPT_"))),
                                   None),
        "condition_symbols": symbol_hits["condition"],
        "action_symbols": symbol_hits["action"],
        "parameter_type_symbols": symbol_hits["parameter_type"],
        "symbol_graph_decoded": False,
    }


def index_script_archive(archive_path: Path) -> dict:
    inner, member = _read_nested_or_direct_zip(archive_path)
    definitions = []
    organizer_bytes = None
    with zipfile.ZipFile(io.BytesIO(inner)) as zipf:
        organizer_files = [
            item for item in zipf.infolist()
            if not item.is_dir()
            and item.filename.replace("\\", "/").casefold() == "organize/scriptorganizer.tso"
        ]
        if len(organizer_files) > 1:
            raise ValueError("Duplicate original organizer paths")
        if organizer_files:
            if organizer_files[0].file_size > 2 * 1024 * 1024:
                raise ValueError("Original organizer exceeds size limit")
            organizer_bytes = zipf.read(organizer_files[0])
        for item in zipf.infolist():
            if item.is_dir() or not item.filename.casefold().endswith(".tsd"):
                continue
            normalized = item.filename.replace("\\", "/")
            top = normalized.split("/", 1)[0].casefold()
            if top not in ("defs", "deletedscripts"):
                continue
            if item.file_size > MAX_SCRIPT_BYTES:
                raise ValueError(f"Script source exceeds size limit: {normalized}")
            definitions.append(parse_tsd(zipf.read(item), normalized,
                                         deleted=(top == "deletedscripts")))
    counts = Counter()
    for record in definitions:
        counts["deleted_sources" if record["deleted_source"] else "active_source_definitions"] += 1
        for kind in ("condition", "action", "parameter_type"):
            counts[kind + "_occurrences"] += len(record[kind + "_symbols"])
    unique = {}
    for kind in ("condition", "action", "parameter_type"):
        unique[kind] = sorted({hit["text"] for record in definitions
                               for hit in record[kind + "_symbols"]})
    result = {
        "schema": SCHEMA, "read_only": True,
        "archive": archive_path.name, "source_member": member,
        "embedded_archive_sha256": sha256(inner),
        "definitions_count": len(definitions),
        "counts": dict(sorted(counts.items())),
        "unique_symbols": unique,
        "definitions": sorted(definitions, key=lambda x: x["member"].casefold()),
        "warnings": [
            "kTCT/kTAT/kTPT are source-declared string tokens, not decoded runtime nodes.",
            "Token occurrence order does not prove condition/action pairing or execution order.",
            "DeletedScripts are historical source records; they are not active scripts.",
            "Script display labels, source filenames, and map actor array indices are not verified bindings.",
            "No original game package or native TriggerScript is modified.",
        ],
        "native_script_editing_supported": False,
        "event_graph_decoded": False,
    }
    if organizer_bytes is not None:
        attach_organizer_index(result, parse_organizer(organizer_bytes))
    else:
        result["organizer"] = None
        result["warnings"].append(
            "ScriptOrganizer.tso not supplied; no categories can be verified."
        )
    return result


def _valid_index(value):
    return type(value) is int and 0 <= value <= 2147483647


def actor_script_reference_report(actors_json: dict) -> dict:
    """Summarize verified serialized property 92 without guessing script IDs."""
    if not isinstance(actors_json, dict) or not isinstance(actors_json.get("actors"), list):
        raise ValueError("Expected DX2Ed actors.json with actors list")
    references = []
    total_indices = 0
    for actor in actors_json["actors"]:
        if not isinstance(actor, dict):
            continue
        properties = actor.get("game_properties")
        if not isinstance(properties, list):
            continue
        for prop in properties:
            if not isinstance(prop, dict) or prop.get("id") != 92:
                continue
            value = prop.get("value")
            indexes = value.get("items") if isinstance(value, dict) else None
            if not isinstance(indexes, list) or not all(_valid_index(x) for x in indexes):
                references.append({"actor": actor.get("name"), "export": actor.get("export"),
                                   "class": actor.get("class"), "status": "unparsed_serialized_value",
                                   "raw_value_type": type(value).__name__})
                continue
            total_indices += len(indexes)
            references.append({"actor": actor.get("name"), "export": actor.get("export"),
                               "class": actor.get("class"), "property_id": 92,
                               "serialized_indices": indexes,
                               "status": "unresolved_script_index_array"})
    meta = actors_json.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    return {
        "schema": ACTOR_SCHEMA,
        "read_only": True, "native_script_binding_verified": False,
        "source_map": meta.get("source_map", meta.get("map")),
        "source_map_sha256": meta.get("source_map_sha256", meta.get("map_sha256")),
        "actor_count": len(actors_json["actors"]),
        "actors_with_property_92": len(references),
        "serialized_indices_total": total_indices,
        "actors": references,
        "warning": "Property 92 contains serialized numeric indices; do not equate them to TS_ filenames, resource-table positions or event graph IDs without evidence.",
    }


def build_report(archive: Path, actors_file: Path | None = None) -> dict:
    result = index_script_archive(archive)
    if actors_file is not None:
        result["actor_script_references"] = actor_script_reference_report(
            json.loads(actors_file.read_text(encoding="utf-8")))
    return result


def render_html(index: dict) -> str:
    """Searchable offline source-symbol browser, with no runtime graph claims."""
    payload = json.dumps(index, ensure_ascii=True, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace("&", "\\u0026")
    template = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DX2Ed Mission Logic Source Browser</title>
<style>
:root{font:14px Segoe UI,system-ui,sans-serif;background:#111a27;color:#e3eefb;color-scheme:dark}
*{box-sizing:border-box}body{margin:0}header{padding:16px 24px;background:#1b2d40;border-bottom:1px solid #334b61}
h1{font-size:20px;margin:0 0 7px}small,.dim{color:#aec0d4}.desc{padding:10px 15px;color:#d9bd80}
main{display:grid;grid-template-columns:minmax(265px,400px) minmax(350px,1fr);height:calc(100vh - 125px);max-width:1600px;margin:auto}
section{border-right:1px solid #314358;min-width:0;display:flex;flex-direction:column}
.controls{padding:12px;display:grid;gap:10px;background:#192839}
input,select,button{background:#253a50;border:1px solid #4c6780;color:#ebf6ff;padding:9px;border-radius:6px;width:100%}button{cursor:pointer}
.list{overflow:auto;flex:1}.entry{padding:11px 13px;border-bottom:1px solid #304157;cursor:pointer}
.entry:hover,.entry.selected{background:#27445a}.entry strong{color:#92d9ff}
.meta{color:#b2c8db;font-size:12px;margin-top:5px}.details{padding:19px;overflow:auto;flex:1}
h2{font-size:18px}h3{font-size:14px;margin-top:22px;color:#9bd4f4}
.badge{display:inline-block;padding:4px 8px;margin:3px;background:#2c445c;border-radius:4px;font-size:12px;overflow-wrap:anywhere}
.deletion{color:#f1bb89}.token{border-bottom:1px solid #33465d;padding:6px 0;overflow-wrap:anywhere}
code{font-size:12px;color:#b2e4ff}.notice{padding:12px;background:#1c3045;color:#d4dce8;margin:12px 0}
@media(max-width:760px){main{display:block;height:auto}section{height:48vh}.details{height:45vh}}
</style></head><body><header><h1>DX2Ed Mission Logic Source Browser</h1>
<small id="summary"></small></header><div class="desc">Read-only evidence: symbols occur in .tsd definitions. This is not a decoded event graph or an in-game script editor.</div>
<main><section><div class="controls"><input id="query" placeholder="Search script, title or kTAT/kTCT symbol" aria-label="Search scripts">
<select id="status"><option value="active">Active definitions</option><option value="all">All sources</option><option value="deleted">Deleted source history</option></select>
<select id="category"><option value="">All verified script categories</option></select>
<button id="actors-btn" type="button">Actor Script Indices (unresolved)</button><div class="dim" id="count"></div></div><div id="list" class="list"></div></section>
<section><div class="details" id="details"><p class="dim">Select a source definition to inspect contained symbols.</p></div></section></main>
<script id="src-data" type="application/json">__DATA__</script>
<script>(function(){"use strict";
const data=JSON.parse(document.getElementById("src-data").textContent),list=document.getElementById("list"),details=document.getElementById("details");
const query=document.getElementById("query"),status=document.getElementById("status"),category=document.getElementById("category");
let chosen=null;
if(data.organizer){
 const nodes=data.organizer.category_trees.scripts.filter(x=>x.folder);
 const names=new Set(nodes.map(x=>x.path.join(" / ")));
 [...names].sort().forEach(function(name){let opt=document.createElement("option");opt.value=name;opt.textContent=name;category.appendChild(opt);});
}else{category.hidden=true;}
const actorRef=data.actor_script_references,actorsButton=document.getElementById("actors-btn");
if(!actorRef){actorsButton.hidden=true;}else{
actorsButton.textContent="Actor script index arrays ("+actorRef.actors_with_property_92+", unresolved)";
actorsButton.addEventListener("click",function(){
chosen=null;details.replaceChildren();
details.appendChild(e("h2","Serialized actor script references"));
details.appendChild(e("p","Source map: "+actorRef.source_map+" · SHA256: "+actorRef.source_map_sha256,"meta"));
details.appendChild(e("p",actorRef.warning,"notice"));
for(const ref of actorRef.actors.slice(0,150)){
let box=e("div",undefined,"token");
box.appendChild(e("strong",ref.actor+" / export "+ref.export+" / "+ref.class));
box.appendChild(e("p",ref.status+": "+JSON.stringify(ref.serialized_indices||[])));
details.appendChild(box);
}drawList();});
}
document.getElementById("summary").textContent=data.definitions_count+" original .tsd source files · "+data.unique_symbols.condition.length+" condition symbols · "+data.unique_symbols.action.length+" action symbols · "+data.counts.active_source_definitions+" active source definitions";
function e(tag,txt,cls){const n=document.createElement(tag);if(txt!==undefined)n.textContent=String(txt);if(cls)n.className=cls;return n;}
function show(x){chosen=x;details.replaceChildren();
details.appendChild(e("h2",x.source_name||x.filename_stem));
details.appendChild(e("p",x.member,"meta"));
details.appendChild(e("p","SHA-256: "+x.raw_sha256,"meta"));
if(x.display_label_hint)details.appendChild(e("p","Display label hint: "+x.display_label_hint));
if(Array.isArray(x.organizer_paths)&&x.organizer_paths.length){
 details.appendChild(e("h3","Original ScriptOrganizer categories"));
 for(const path of x.organizer_paths){details.appendChild(e("div",path.join(" / ")||"(root)","token"));}
}
if(x.deleted_source)details.appendChild(e("p","Historical deleted script source, not an active definition","notice"));
for(const pair of [["condition","Condition tokens (kTCT_)"],["action","Action tokens (kTAT_)"],["parameter_type","Parameter type tokens (kTPT_)"]]){
let k=pair[0];details.appendChild(e("h3",pair[1]+" · "+x[k+"_symbols"].length));
for(const token of x[k+"_symbols"]){details.appendChild(e("div",token.text+"   @ byte "+token.offset,"token"));}}
details.appendChild(e("p","Tokens are recovered from UTF-16LE source fields; their occurrence order does not prove event edges, branching, parameters or execution order.","notice"));
drawList();
}
function drawList(){const q=query.value.toLocaleLowerCase(),mode=status.value,cat=category.value;
const found=data.definitions.filter(x=>(mode==="all"||(mode==="deleted"?x.deleted_source:!x.deleted_source))&&
(!cat||(Array.isArray(x.organizer_paths)&&x.organizer_paths.some(p=>{
 const full=p.join(" / ");return full===cat||full.startsWith(cat+" / ");
})))&&(!q||(
[x.source_name,x.filename_stem,x.display_label_hint].join(" ")+" "+
x.condition_symbols.map(y=>y.text).join(" ")+" "+
x.action_symbols.map(y=>y.text).join(" ")+" "+
x.parameter_type_symbols.map(y=>y.text).join(" ")).toLocaleLowerCase().includes(q)));
document.getElementById("count").textContent=found.length+" matches; showing first 250.";
list.replaceChildren();const frag=document.createDocumentFragment();
for(const x of found.slice(0,250)){let div=e("div",undefined,"entry"+(x===chosen?" selected":""));
div.appendChild(e("strong",x.source_name||x.filename_stem));
div.appendChild(e("div",(x.display_label_hint||"")+" · C:"+x.condition_symbols.length+" A:"+x.action_symbols.length+(x.deleted_source?" · Deleted":""),"meta"));
div.addEventListener("click",()=>show(x));frag.appendChild(div);}
list.appendChild(frag);
}
query.addEventListener("input",drawList);status.addEventListener("change",drawList);category.addEventListener("change",drawList);drawList();
if(data.definitions.length)show(data.definitions.find(x=>!x.deleted_source)||data.definitions[0]);
})();</script></body></html>'''
    return template.replace("__DATA__", payload)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script_archive", type=Path)
    parser.add_argument("--actors", type=Path, help="Existing DX2Ed cached actors.json")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args(argv)
    sources = {args.script_archive.resolve()}
    if args.actors:
        sources.add(args.actors.resolve())
    if args.output.resolve() in sources:
        parser.error("Refusing to overwrite original input")
    try:
        report = build_report(args.script_archive, args.actors)
        if args.format == "html" and args.output.suffix.casefold() not in (".html", ".htm"):
            raise ValueError("HTML output filename must end in .html or .htm")
        if args.format == "json" and args.output.suffix.casefold() != ".json":
            raise ValueError("JSON output filename must end in .json")
        data = (render_html(report) if args.format == "html"
                else json.dumps(report, indent=2, ensure_ascii=True) + "\n")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding="utf-8")
        print(json.dumps({"status": "ok", "source_definitions": report["definitions_count"],
                          "counts": report["counts"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
