#!/usr/bin/env python3
"""Private, address-free coverage triage for authenticated DX2 static references.

Accepts only the strict v1 sanitized schema. Output contains counts, not addresses,
fingerprints, strings, or decompiled code. No function ownership/API claim is made.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from validate_sanitized_call_edges import canonical_address, load_bounded_json, validate

# The eleven unverified candidate destinations in the private collector.
# These are research leads, not proven function entry points.
TARGETS = (
    "005c56a0", "005c5c69", "005be1b0", "005febd0",
    "00606c50", "00623a00", "0060cdf0", "0060a690",
    "0060a900", "0060b9b0", "0060cbb0",
)


def summarize(doc):
    validate(doc)
    targets = {canonical_address(a) for a in TARGETS}
    counts = Counter()
    unexpected = 0
    for edge in doc["edges"]:
        destination = canonical_address(edge["callee"])
        if destination not in targets:
            unexpected += 1
        else:
            counts[destination] += 1
    return {
        "schema": "DX2-ReferenceCoverage-v1",
        "candidate_targets": len(targets),
        "targets_with_references": len(counts),
        "targets_without_references": len(targets) - len(counts),
        "reference_count": len(doc["edges"]),
        "out_of_scope_destinations": unexpected,
        "reference_kinds": {kind: sum(e["reference_kind"] == kind for e in doc["edges"])
                            for kind in ("CALL", "JUMP", "DATA")},
        "function_ownership_verified": False,
        "loader_or_actor_registration_verified": False,
        "runtime_verified": False,
        "interpretation": "Static candidate references only; no function ownership or API proof",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="private validated bounded-reference JSON")
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as source:
        doc = load_bounded_json(source)
    print(json.dumps(summarize(doc), sort_keys=True))


if __name__ == "__main__":
    main()
