"""Generate a non-retail PE32 with a known direct call into the collector target.

Usage: python synthetic_reference_pe.py make fixture.exe
       python synthetic_reference_pe.py check fixture.exe evidence.json
No external packages or game files required.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

BASE = 0x400000
RVA = 0x1C5000
TARGET = 0x5C56A0
ENTRY = BASE + RVA


def fixture():
    data = bytearray(0xA00)
    def put(offset, fmt, *values):
        struct.pack_into("<" + fmt, data, offset, *values)
    data[:2] = b"MZ"
    put(0x3C, "I", 0x80)
    data[0x80:0x84] = b"PE\0\0"
    put(0x84, "HHIIIHH", 0x14C, 1, 0, 0, 0, 224, 0x102)
    o = 0x98
    put(o, "H", 0x10B)
    put(o+4, "III", 0x800, 0, 0)
    put(o+16, "IIIIII", RVA, RVA, 0, BASE, 0x1000, 0x200)
    put(o+40, "HHHHHH", 4, 0, 0, 0, 4, 0)
    put(o+56, "IIIHH", RVA+0x1000, 0x200, 0, 3, 0)
    put(o+72, "IIIIII", 0x100000, 0x1000, 0x100000, 0x1000, 0, 16)
    s = o+224
    data[s:s+8] = b".text\0\0\0"
    put(s+8, "IIIIIIHHI", 0x800, RVA, 0x800, 0x200, 0, 0, 0, 0, 0x60000020)
    data[0x200] = 0xE8
    put(0x201, "i", TARGET-ENTRY-5)
    data[0x205] = 0xC3
    data[0x200+TARGET-ENTRY] = 0xC3
    return bytes(data)


def check(binary, evidence):
    if binary != fixture():
        raise ValueError("Not the exact synthetic fixture")
    if evidence["executable_sha256"] != hashlib.sha256(binary).hexdigest():
        raise ValueError("Fingerprint mismatch")
    if evidence["schema"] != "DX2-SanitizedCallEdges-v1":
        raise ValueError("Schema mismatch")
    if evidence["runtime_verified"] is not False or evidence["native_writer_ready"] is not False:
        raise ValueError("Unexpected claim")
    expected = {(ENTRY, TARGET, "CALL")}
    actual = {(int(e["caller"], 16), int(e["callee"], 16), e["reference_kind"])
              for e in evidence["edges"]}
    if actual != expected or len(evidence["edges"]) != 1:
        raise ValueError("Unexpected reference set")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "make":
        with Path(sys.argv[2]).open("xb") as out:
            out.write(fixture())
        print(hashlib.sha256(fixture()).hexdigest())
    elif len(sys.argv) == 4 and sys.argv[1] == "check":
        check(Path(sys.argv[2]).read_bytes(), json.loads(Path(sys.argv[3]).read_text()))
        print("Synthetic direct-call evidence verified")
    else:
        raise SystemExit(__doc__)
