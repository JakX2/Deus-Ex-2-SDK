#!/usr/bin/env python3
"""Native DX2 IBD integrity verification and same-size resource replacement.

The legacy SHA-1 values are format fields, not authenticity signatures.
Source identity is separately pinned with SHA-256. Nothing here validates
the engine semantics of replacement bytes or rebuilds resources/geometry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from dx2bundles import Bundle, HEADER_SIZE, ENTRY_SIZE

MAX_BUNDLE_BYTES = 256 * 1024 * 1024
MAX_ZIP_BYTES = 512 * 1024 * 1024
MAX_ZIP_MEMBERS = 256
MAX_ZIP_EXPANDED = 1024 * 1024 * 1024
HEADER_DIGEST_OFFSET = 32
RESOURCE_DIGEST_OFFSET = 20
DIGEST_BYTES = 20


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def header_digest(raw, data_start):
    """Hash the complete header/table region with its own digest zeroed."""
    if not HEADER_SIZE <= data_start <= len(raw):
        raise ValueError("Invalid IBD header extent")
    h = hashlib.sha1()
    h.update(raw[:HEADER_DIGEST_OFFSET])
    h.update(bytes(DIGEST_BYTES))
    h.update(memoryview(raw)[HEADER_DIGEST_OFFSET + DIGEST_BYTES:data_start])
    return h.digest()


def resource_digest(raw, resource):
    return hashlib.sha1(memoryview(raw)[resource.offset:
                           resource.offset+resource.size+resource.padding]).digest()


def verify_bundle(raw):
    if not HEADER_SIZE <= len(raw) <= MAX_BUNDLE_BYTES:
        raise ValueError("Unsupported IBD size")
    bundle = Bundle("verified.ibd", raw)
    if bundle.expected_digest != header_digest(raw, bundle.data_start):
        raise ValueError("IBD header SHA-1 mismatch")
    for resource in bundle.resources:
        if resource.digest != resource_digest(raw, resource):
            raise ValueError("IBD resource SHA-1 mismatch at index %d" % resource.index)
    return bundle


def audit_zip(path):
    if not 0 < path.stat().st_size <= MAX_ZIP_BYTES:
        raise ValueError("IBD ZIP size exceeds limit")
    bundles = resources = parts = total = 0
    seen = set()
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ZIP_MEMBERS:
            raise ValueError("ZIP member count exceeds limit")
        for member in entries:
            if member.is_dir() or not member.filename.lower().endswith(".ibd"):
                continue
            name = member.filename.replace("\\", "/").lower()
            if name in seen:
                raise ValueError("Duplicate IBD member")
            seen.add(name)
            total += member.file_size
            if not HEADER_SIZE <= member.file_size <= MAX_BUNDLE_BYTES or total > MAX_ZIP_EXPANDED:
                raise ValueError("IBD ZIP expanded size exceeds limit")
            with archive.open(member) as stream:
                raw = stream.read(member.file_size + 1)
            if len(raw) != member.file_size:
                raise ValueError("IBD ZIP member size mismatch")
            bundle = verify_bundle(raw)
            bundles += 1
            resources += len(bundle.resources)
            parts += bundle.part_count
    if not bundles:
        raise ValueError("No IBD archives verified")
    return {"schema":"DX2-IBDIntegrity-v1","verified_bundles":bundles,
            "verified_header_digests":bundles,"verified_resource_digests":resources,
            "verified_part_records":parts,"runtime_verified":False,"source_modified":False}


def replace_same_size(raw, index, replacement):
    """Return a new byte buffer; preserve all part geometry and original padding.

    Verify the entire source and result, and limit changes to the exact
    payload and two digest fields. Index is the zero-based source table index.
    """
    bundle = verify_bundle(raw)
    if type(index) is not int or not 0 <= index < len(bundle.resources):
        raise ValueError("Resource index outside original table")
    resource = bundle.resources[index]
    if len(replacement) != resource.size:
        raise ValueError("Replacement must retain exact original payload size")
    start = resource.offset
    end = start + resource.size
    if raw[start:end] == replacement:
        raise ValueError("Replacement would not change the payload")
    result = bytearray(raw)
    result[start:end] = replacement
    digest_at = HEADER_SIZE + index * ENTRY_SIZE + RESOURCE_DIGEST_OFFSET
    result[digest_at:digest_at + DIGEST_BYTES] = resource_digest(result, resource)
    result[HEADER_DIGEST_OFFSET:HEADER_DIGEST_OFFSET+DIGEST_BYTES] = header_digest(
        result, bundle.data_start)
    result = bytes(result)
    verified = verify_bundle(result)
    if (len(raw) != len(result) or verified.data_start != bundle.data_start or
            verified.part_sizes != bundle.part_sizes or
            len(verified.resources) != len(bundle.resources)):
        raise ValueError("IBD structure changed unexpectedly")
    ranges = sorted(((HEADER_DIGEST_OFFSET, HEADER_DIGEST_OFFSET+DIGEST_BYTES),
                     (digest_at, digest_at+DIGEST_BYTES), (start,end)))
    cursor = 0
    for lo, hi in ranges:
        if lo < cursor or hi > len(raw) or raw[cursor:lo] != result[cursor:lo]:
            raise ValueError("Unexpected byte change outside permitted ranges")
        cursor = hi
    if raw[cursor:] != result[cursor:]:
        raise ValueError("Unexpected trailing byte change")
    return result


def read_bounded(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_BUNDLE_BYTES:
        raise ValueError("Invalid or oversized input")
    with path.open("rb") as stream:
        data = stream.read(MAX_BUNDLE_BYTES+1)
    if len(data)>MAX_BUNDLE_BYTES:
        raise ValueError("Input exceeds size limit")
    return data


def write_isolated(source, payload, output, index, expected_sha256):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("Expected lowercase source SHA-256")
    if source.is_symlink() or payload.is_symlink() or output.is_symlink():
        raise ValueError("Symlink input or output refused")
    source = source.resolve(strict=True)
    output = output.resolve()
    if (source.suffix.lower() != ".ibd" or output.name != source.name or
            output.parent == source.parent or source.parent in output.parents or
            output.exists()):
        raise ValueError("Output must retain the source filename in a new isolated directory")
    original = read_bounded(source)
    if sha256(original) != expected_sha256:
        raise ValueError("Source SHA-256 mismatch")
    candidate = replace_same_size(original, index, read_bounded(payload))
    if sha256(read_bounded(source)) != expected_sha256:
        raise ValueError("Source changed during preparation")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as stream:
            created = True
            stream.write(candidate)
        actual = read_bounded(output)
        if actual != candidate or sha256(read_bounded(source)) != expected_sha256:
            raise ValueError("Candidate or source changed")
        verified = verify_bundle(actual)
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {"schema":"DX2-IBDSameSizeCandidate-v1","status":"isolated-candidate",
            "resource_index":index,"source_sha256":expected_sha256,
            "candidate_sha256":sha256(candidate),"verified_resource_digests":len(verified.resources),
            "same_size":True,"runtime_verified":False,"source_modified":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    audit=sub.add_parser("audit")
    audit.add_argument("source",type=Path)
    archive=sub.add_parser("audit-zip")
    archive.add_argument("source",type=Path)
    replace=sub.add_parser("replace-same-size")
    replace.add_argument("source",type=Path)
    replace.add_argument("--payload",type=Path,required=True)
    replace.add_argument("--output",type=Path,required=True)
    replace.add_argument("--index",type=int,required=True)
    replace.add_argument("--source-sha256",required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="audit-zip":
            report=audit_zip(args.source)
        elif args.command=="audit":
            bundle=verify_bundle(read_bounded(args.source))
            report={"schema":"DX2-IBDIntegrity-v1","verified_bundles":1,
                    "verified_header_digests":1,"verified_resource_digests":len(bundle.resources),
                    "verified_part_records":bundle.part_count,"runtime_verified":False,"source_modified":False}
        else:
            report=write_isolated(args.source,args.payload,args.output,args.index,args.source_sha256)
        print(json.dumps(report,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
