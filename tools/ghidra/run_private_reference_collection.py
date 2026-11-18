#!/usr/bin/env python3
"""Private, pinned DX2Main reference extraction; never uploads or prints raw evidence.

Requires the reviewed validate_sanitized_call_edges.py contract from PR #195.
Use with a local owner-original PE and pinned Ghidra 12.2 installation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
TARGETS = {int(x, 16) for x in (
    "005c56a0", "005c5c69", "005be1b0", "005febd0", "00606c50",
    "00623a00", "0060cdf0", "0060a690", "0060a900", "0060b9b0", "0060cbb0")}


def authenticate(image, pins):
    rows = [row for row in pins if row["name"] == "DX2Main.exe"]
    if len(rows) != 1:
        raise ValueError("expected exactly one DX2Main pin")
    pin = rows[0]
    if image.name.lower() != pin["name"].lower() or image.stat().st_size != pin["size"]:
        raise ValueError("original PE name or size mismatch")
    with image.open("rb") as src:
        digest = hashlib.file_digest(src, "sha256").hexdigest()
    if digest != pin["sha256"]:
        raise ValueError("original PE fingerprint mismatch")
    return digest


def check_scope(doc, digest):
    if doc["executable_sha256"] != digest:
        raise ValueError("report fingerprint mismatch")
    for edge in doc["edges"]:
        for key in ("caller", "callee"):
            value = edge[key]
            if ":" in value or not 0 <= int(value, 16) <= 0xffffffff:
                raise ValueError("expected flat 32-bit PE addresses")
        if int(edge["callee"], 16) not in TARGETS:
            raise ValueError("reference destination outside candidate scope")


def publish_report(doc, output):
    """Publish validated evidence without partial files or destination replacement."""
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError("refusing to overwrite evidence")
    payload = (json.dumps(doc, sort_keys=True) + "\n").encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=output.parent,
                                         prefix=".dx2-evidence-", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link atomically creates the final name only if it does not exist.
        # os.replace would silently overwrite an existing evidence report.
        os.link(temporary, output)
        try:
            directory_fd = os.open(output.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            # Only documented unsupported directory-sync operations are optional.
            # An actual I/O failure must be reported even though the final name
            # has already been published and must not be deleted.
            import errno
            unsupported = {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}
            if os.name == "nt":
                unsupported.add(errno.EACCES)  # Windows may refuse directory handles.
            if exc.errno not in unsupported:
                raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    from validate_sanitized_call_edges import load_bounded_json, validate
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--headless", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    image = args.image.resolve(strict=True)
    pins = json.loads((ROOT / "dx2_system_pe_pins.json").read_text())
    digest = authenticate(image, pins)
    if args.output.exists():
        raise FileExistsError("refusing to overwrite evidence")
    with tempfile.TemporaryDirectory(prefix="dx2-private-reference-") as tmp:
        scratch = Path(tmp)
        (scratch / "projects").mkdir()
        # Capture all analyzer logs privately; no raw output enters CI logs.
        with (scratch / "ghidra.log").open("wb") as log:
            subprocess.run([
                str(args.headless.resolve(strict=True)), str(scratch / "projects"),
                "DX2PrivateRefs", "-import", str(image), "-scriptPath", str(ROOT),
                "-postScript", "DX2BoundedReferenceCollector.java",
                str(scratch / "edges.json"), digest, "-analysisTimeoutPerFile", "3600",
                "-deleteProject"], stdout=log, stderr=subprocess.STDOUT,
                check=True, timeout=5400)
        with (scratch / "edges.json").open(encoding="utf-8") as source:
            doc = load_bounded_json(source)
        summary = validate(doc)
        check_scope(doc, digest)
        authenticate(image, pins)
        publish_report(doc, args.output)
        print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
