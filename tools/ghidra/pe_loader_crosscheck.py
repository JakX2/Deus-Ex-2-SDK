#!/usr/bin/env python3
"""Independent PE32/objdump cross-check of Ghidra's DX2 loader leads.

Only aggregate counts leave this tool; no addresses, instructions or raw strings.
Linear disassembly and proximity are static evidence, not function ownership.
"""
from __future__ import annotations
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
SCHEMA = "DX2-PELoaderCrosscheck-v1"
LITERALS = {
    "gmp_extension": b".gmp", "entry_gmp_path": b".\\data\\Entry.gmp",
    "ibd_extension": b".ibd", "ibdm_extension": b".ibdm",
    "package_failure_name": b"FailedLoadPackage", "static_mesh_actor_name": b"StaticMeshActor",
}
IMPORTS = ("CreateFileA", "GetFileAttributesA")
REGS = ("eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi")
HEX = re.compile(r"0x[0-9a-f]+\Z")
ABS = re.compile(r"(?:ds:|\[)(0x[0-9a-f]+)(?:\]|\Z)")
MAX_OUTPUT = 256 * 1024 * 1024


class PE:
    def __init__(self, data):
        self.data = data
        if len(data) < 256 or data[:2] != b"MZ":
            raise ValueError("Missing PE header")
        p = self.u32(0x3c)
        if p + 24 > len(data) or data[p:p+4] != b"PE\0\0":
            raise ValueError("Invalid PE signature")
        machine, count = struct.unpack_from("<HH", data, p+4)
        opt = p+24
        optsize = self.u16(p+20)
        if (machine != 0x14c or not 1 <= count <= 96 or optsize < 112 or
                opt+optsize+40*count > len(data) or self.u16(opt) != 0x10b):
            raise ValueError("Expected bounded x86 PE32")
        self.base = self.u32(opt+28)
        self.sections = []
        for i in range(count):
            s = opt+optsize+40*i
            rva, size, off = struct.unpack_from("<III", data, s+12)
            if not size:
                continue
            va = self.base+rva
            if off+size > len(data) or va+size > 2**32:
                raise ValueError("Section outside image")
            self.sections.append((va, off, size, bool(self.u32(s+36)&0x20000000)))
        self.import_rva = self.u32(opt+104) if self.u32(opt+92) >= 2 else 0
        self.import_size = self.u32(opt+108) if self.import_rva else 0

    def u16(self, off):
        return struct.unpack_from("<H", self.data, off)[0]

    def u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def offset(self, va, size, *, code=False):
        for start, off, length, executable in self.sections:
            if start <= va and va+size <= start+length and (not code or executable):
                return off+va-start
        raise ValueError("Address not backed by a matching PE section")

    def cstring(self, rva):
        off = self.offset(self.base+rva, 1)
        end = self.data.find(b"\0", off, min(off+256,len(self.data)))
        if end < 0:
            raise ValueError("Unterminated import string")
        return self.data[off:end].decode("ascii")

    def import_slots(self):
        slots = {}
        if not self.import_rva:
            return slots
        for i in range(min(self.import_size//20, 128)):
            off = self.offset(self.base+self.import_rva+20*i, 20)
            lookup, _, _, name, first = struct.unpack_from("<5I", self.data, off)
            if not name:
                return slots
            if self.cstring(name).lower() != "kernel32.dll":
                continue
            for j in range(4096):
                thunk = self.u32(self.offset(self.base+(lookup or first)+4*j,4))
                if not thunk:
                    break
                if not thunk&0x80000000:
                    symbol = self.cstring(thunk+2)
                    if symbol in IMPORTS:
                        slot = self.base+first+4*j
                        self.offset(slot,4)
                        slots[slot] = symbol
            else:
                raise ValueError("Import thunk cap exceeded")
        return slots

    def literal_addresses(self):
        result = {key:set() for key in LITERALS}
        for va, off, size, executable in self.sections:
            if executable:
                continue
            section = self.data[off:off+size]
            for name, literal in LITERALS.items():
                pos = section.find(literal+b"\0")
                while pos >= 0:
                    boundary = pos == 0 or section[pos-1] == 0
                    alias = (name == "static_mesh_actor_name" and pos >= 1 and
                             section[pos-1:pos] == b"A" and (pos == 1 or section[pos-2] == 0))
                    if boundary or alias:
                        result[name].add(va+pos)
                        if len(result[name]) > 32:
                            raise ValueError("Literal cap exceeded")
                    pos = section.find(literal+b"\0", pos+1)
        return result


def parse_instruction(line):
    parts = line.rstrip().split("\t")
    if len(parts) != 3 or not parts[0].strip().endswith(":"):
        return None
    try:
        address = int(parts[0].strip()[:-1],16)
        raw = bytes.fromhex(parts[1])
    except ValueError:
        return None
    body = parts[2].strip().lower().split(None,1)
    if not body or not 1 <= len(raw) <= 15:
        return None
    return address, raw, body[0], body[1] if len(body)==2 else ""


def operand_values(operand):
    for part in operand.split(","):
        part=part.strip()
        if HEX.fullmatch(part):
            yield int(part,16), "immediate"
        else:
            match=ABS.search(part)
            if match:
                yield int(match.group(1),16), "absolute_memory"


def scan(pe, lines, candidates):
    literals=pe.literal_addresses()
    targets={addr:name for name, addresses in literals.items() for addr in addresses}
    slots=pe.import_slots()
    refs={name:set() for name in literals}
    call_sites={addr:set() for addresses in candidates.values() for addr in addresses}
    for addr in call_sites:
        pe.offset(addr,1,code=True)
    jump_sites={addr:set() for addr in call_sites}
    imports={name:set() for name in IMPORTS}
    tracked={}
    previous_end=None
    for line in lines:
        decoded=parse_instruction(line)
        if decoded is None:
            continue
        va,raw,mnemonic,operand=decoded
        if previous_end != va:
            tracked.clear()
        previous_end=va+len(raw)
        if mnemonic not in ("push","mov","lea","call","jmp"):
            tracked.clear()
            continue
        off=pe.offset(va,len(raw),code=True)
        if pe.data[off:off+len(raw)] != raw:
            raise ValueError("Disassembly bytes do not match PE")
        operands=list(operand_values(operand))
        if mnemonic in ("push","mov","lea"):
            for value,kind in operands:
                if value in targets and struct.pack("<I",value) in raw:
                    refs[targets[value]].add((va,kind))
        if mnemonic == "call" or mnemonic == "jmp":
            if mnemonic == "call" and len(raw)==5 and raw[0]==0xe8:
                dest=(va+5+int.from_bytes(raw[1:],"little",signed=True))&0xffffffff
                if dest in call_sites:
                    call_sites[dest].add(va)
            if mnemonic == "jmp" and ((len(raw)==5 and raw[0]==0xe9) or (len(raw)==2 and raw[0]==0xeb)):
                dest=(va+len(raw)+int.from_bytes(raw[1:],"little",signed=True))&0xffffffff
                if dest in jump_sites:
                    jump_sites[dest].add(va)
            if mnemonic=="call":
                if len(raw)==6 and raw[:2]==b"\xff\x15":
                    slot=int.from_bytes(raw[2:],"little")
                    if slot in slots:
                        imports[slots[slot]].add(va)
                elif len(raw)==2 and raw[0]==0xff and 0xd0<=raw[1]<=0xd7:
                    reg=REGS[raw[1]-0xd0]
                    if reg in tracked and va-tracked[reg][1]<=128:
                        imports[tracked[reg][0]].add(va)
            tracked.clear()
        elif mnemonic in ("mov","lea"):
            dest=operand.split(",",1)[0].strip()
            if dest in REGS:
                tracked.pop(dest,None)
                if mnemonic=="mov" and len(operands)==1:
                    value,kind=operands[0]
                    if (dest!="esp" and kind=="absolute_memory" and value in slots and
                        struct.pack("<I",value) in raw and operand.partition(",")[2].strip().startswith("dword ptr")):
                        tracked[dest]=(slots[value],va)
            else:
                tracked.clear()  # conservative: partial-register or memory writes
    def near(sites, va, distance):
        i=bisect.bisect_left(sites,va-distance)
        return i<len(sites) and sites[i]<=va+distance
    file_calls=sorted(imports["CreateFileA"])
    attr_calls=sorted(imports["GetFileAttributesA"])
    failures=sorted(va for va,_ in refs["package_failure_name"])
    return {"schema":SCHEMA,"static_only":True,"runtime_verified":False,"loader_verified":False,
        "actor_registration_verified":False,"game_assets_included":False,
        "literal_evidence":{name:{"literals":len(literals[name]),
          "immediate_references":sum(kind=="immediate" for _,kind in rows),
          "absolute_memory_references":sum(kind=="absolute_memory" for _,kind in rows),
          "near_file_open_refs":sum(near(file_calls,va,128) for va,_ in rows),
          "near_file_attributes_refs":sum(near(attr_calls,va,128) for va,_ in rows)}
          for name,rows in refs.items()},
        "ghidra_leads":{name:{"candidate_count":len(addresses),
          "candidates_with_direct_calls":sum(bool(call_sites[a]) for a in addresses),
          "direct_call_sites":sum(len(call_sites[a]) for a in addresses),
          "direct_jump_sites":sum(len(jump_sites[a]) for a in addresses),
          "near_package_failure_candidates":sum(near(failures,a,32) for a in addresses)}
          for name,addresses in candidates.items()},
        "import_call_sites":{name:len(sites) for name,sites in imports.items()}}


def analyze(image, candidates):
    pe=PE(image.read_bytes())
    with tempfile.TemporaryFile(mode="w+b") as scratch:
        subprocess.run(["objdump","-d","-w","-Mintel",str(image)],stdout=scratch,
                       stderr=subprocess.DEVNULL,check=True,timeout=90)
        if scratch.tell()>MAX_OUTPUT:
            raise ValueError("Disassembly exceeds private scratch cap")
        scratch.seek(0)
        return scan(pe,(line.decode("ascii",errors="replace") for line in scratch),candidates)


def main():
    from validate_hosted_summary import validate
    from stage_original_pe_from_zip import load_expectations
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image",type=Path,required=True)
    parser.add_argument("--summary",type=Path,required=True)
    args=parser.parse_args()
    pins=ROOT/"dx2_system_pe_pins.json"
    expected=load_expectations(pins)["dx2main.exe"]
    validate(args.summary,pins)
    if (args.image.is_symlink() or args.image.name.lower()!="dx2main.exe" or
        args.image.stat().st_size!=expected[0] or hashlib.sha256(args.image.read_bytes()).hexdigest()!=expected[1]):
        raise ValueError("DX2Main owner input does not match committed pin")
    original=json.loads(args.summary.read_text())
    entry=next(x for x in original["reports"] if x["pe_sha256"]==expected[1])
    candidates={}
    for row in entry["keyword_evidence"]:
        if row["term"] not in (".gmp",".ibd","loadpackage","staticmeshactor","serialize","gamesys"):
            continue
        addresses=row["candidate_function_addresses"]
        if any(not re.fullmatch(r"[0-9a-fA-F]{1,8}",a) for a in addresses):
            raise ValueError("Expected flat PE32 candidate addresses")
        normalized={int(a,16) for a in addresses}
        if len(normalized)!=len(addresses):
            raise ValueError("Duplicate canonical candidate address")
        candidates[row["term"]]=normalized
    report=analyze(args.image,candidates)
    if hashlib.sha256(args.image.read_bytes()).hexdigest()!=expected[1]:
        raise ValueError("Owner PE changed during analysis")
    print(json.dumps(report,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
