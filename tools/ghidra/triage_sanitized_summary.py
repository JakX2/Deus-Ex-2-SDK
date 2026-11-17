#!/usr/bin/env python3
"""Produce a bounded, source-only triage of an already sanitized DX2 Ghidra summary.

This is not a call graph or evidence of a functioning native writer.
Input must first pass validate_hosted_summary.py in the hosted workflow.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

PRIORITY = (".gmp", ".ibd", "loadpackage", "serialize", "deserialize",
            "gamesys", "staticmeshactor", "triggerscript", "bsp",
            "collision", "havok")


def triage(summary):
    if summary.get("schema") != "DX2-GhidraPrivateSummary-v1":
        raise ValueError("unexpected sanitized report schema")
    if summary.get("game_assets_included") is not False:
        raise ValueError("report is not marked asset-free")
    reports = summary.get("reports")
    if not isinstance(reports, list) or not reports:
        raise ValueError("missing reports")
    results = []
    for report in reports:
        if report.get("game_assets_included") is not False:
            raise ValueError("target not marked asset-free")
        by_term = {}
        by_address = defaultdict(set)
        for item in report.get("keyword_evidence", []):
            term = item.get("term")
            if term not in PRIORITY or term in by_term:
                continue
            addresses = item.get("candidate_function_addresses", [])
            if not isinstance(addresses, list):
                raise ValueError("invalid candidate address list")
            if len(addresses) > 64:
                raise ValueError("unbounded candidate address list")
            normalized = []
            for address in addresses:
                if not isinstance(address, str) or len(address) > 16 or not address:
                    raise ValueError("invalid candidate address")
                if any(c not in "0123456789abcdefABCDEF" for c in address):
                    raise ValueError("nonhex candidate address")
                normalized.append(address.lower())
                by_address[address.lower()].add(term)
            by_term[term] = {
                "defined_literal_hits": item.get("defined_literal_hits", 0),
                "candidate_function_addresses": sorted(set(normalized)),
            }
        results.append({
            "pe_sha256": report.get("pe_sha256"),
            "function_count": report.get("function_count"),
            "topics": {term: by_term.get(term, {"defined_literal_hits": 0,
                      "candidate_function_addresses": []}) for term in PRIORITY},
            "overlaps": [{"address": address, "terms": sorted(terms)}
                         for address, terms in sorted(by_address.items())
                         if len(terms) > 1],
            "native_writer_ready": report.get("native_writer_ready"),
            "retail_runtime_verified": report.get("retail_runtime_verified"),
        })
    return {"schema": "DX2-SanitizedTriage-v1", "disclaimer":
            "Keyword/function correlations only; no verified calls, loader semantics, or gameplay.",
            "targets": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = triage(json.loads(args.summary.read_text(encoding="utf-8")))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
