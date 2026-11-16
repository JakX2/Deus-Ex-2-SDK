#!/usr/bin/env python3
"""Strictly validate an existing/cached DX2 sanitized hosted survey.

Do not trust a cache hit, downloadable artifact, or preceding Ghidra process
until every SHA256 maps one-to-one to the owner's pinned original PE hashes.
No original game code or binary paths appear in this metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from run_private_survey import SUMMARY_SCHEMA, TERMS
from stage_original_pe_from_zip import load_expectations

MAX_BYTES = 2 * 1024 * 1024
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
ADDR_RE = re.compile(r"[0-9a-fA-F:]{1,32}\Z")
REPORT_KEYS = {
    "schema", "pe_sha256", "pe_role", "processor",
    "function_count", "defined_data_scanned", "scan_limit_reached",
    "keyword_evidence", "native_writer_ready",
    "retail_runtime_verified", "game_assets_included",
}
EVIDENCE_KEYS = {
    "term", "defined_literal_hits", "candidate_function_addresses",
}
TOP_KEYS = {
    "schema", "target_count", "reports", "game_assets_included",
    "retail_runtime_verified", "source_assets_modified",
}


class EvidenceError(ValueError):
    pass


def validate(summary: Path, pins: Path) -> dict:
    original = load_expectations(pins)
    if (not summary.is_file() or summary.is_symlink()
            or not 0 < summary.stat().st_size <= MAX_BYTES):
        raise EvidenceError("Missing, symlinked, or oversized metadata summary")
    try:
        report = json.loads(summary.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise EvidenceError("Metadata is not JSON") from exc
    expected_hashes = {record[1] for record in original.values()}
    if (type(report) is not dict or set(report) != TOP_KEYS
            or report["schema"] != SUMMARY_SCHEMA
            or type(report["target_count"]) is not int
            or report["target_count"] != len(original)
            or type(report["reports"]) is not list
            or len(report["reports"]) != len(original)
            or report["game_assets_included"] is not False
            or report["retail_runtime_verified"] is not False
            or report["source_assets_modified"] is not False):
        raise EvidenceError("Metadata root does not match strict schema and pins")
    observed = []
    for row in report["reports"]:
        if (type(row) is not dict or set(row) != REPORT_KEYS
                or row["schema"] != SUMMARY_SCHEMA
                or type(row["pe_sha256"]) is not str
                or not SHA_RE.fullmatch(row["pe_sha256"])
                or row["pe_sha256"] not in expected_hashes
                or row["pe_role"] != "EXE"
                or type(row["processor"]) is not str
                or not re.fullmatch(r"[A-Za-z0-9:._-]{1,80}", row["processor"])
                or type(row["function_count"]) is not int
                or not 0 <= row["function_count"] <= 50_000_000
                or type(row["defined_data_scanned"]) is not int
                or not 0 <= row["defined_data_scanned"] <= 500_000
                or type(row["scan_limit_reached"]) is not bool
                or row["native_writer_ready"] is not False
                or row["retail_runtime_verified"] is not False
                or row["game_assets_included"] is not False
                or type(row["keyword_evidence"]) is not list
                or len(row["keyword_evidence"]) != len(TERMS)):
            raise EvidenceError("Metadata contains untrusted or unmatched PE evidence")
        observed.append(row["pe_sha256"])
        seen_terms = set()
        for evidence in row["keyword_evidence"]:
            if (type(evidence) is not dict or set(evidence) != EVIDENCE_KEYS
                    or evidence["term"] not in TERMS
                    or evidence["term"] in seen_terms
                    or type(evidence["defined_literal_hits"]) is not int
                    or not 0 <= evidence["defined_literal_hits"] <= 500_000
                    or type(evidence["candidate_function_addresses"]) is not list
                    or len(evidence["candidate_function_addresses"]) > 24):
                raise EvidenceError("Metadata keyword evidence not allowlisted")
            seen_terms.add(evidence["term"])
            addresses = evidence["candidate_function_addresses"]
            if (len(addresses) != len(set(map(str, addresses)))
                    or any(type(x) is not str or not ADDR_RE.fullmatch(x)
                           for x in addresses)):
                raise EvidenceError("Metadata function addresses invalid")
        if seen_terms != set(TERMS):
            raise EvidenceError("Metadata keywords incomplete")
    if len(observed) != len(set(observed)) or set(observed) != expected_hashes:
        raise EvidenceError("Metadata PE fingerprint set differs from original pin manifest")
    return {
        "status": "matched-strict-sanitized-report",
        "module_count": len(observed),
        "original_game_binaries_uploaded": False,
        "retail_runtime_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--pins", type=Path, required=True)
    args = parser.parse_args()
    try:
        status = validate(args.summary, args.pins)
        print(json.dumps(status, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "reason": (
            str(exc) if isinstance(exc, EvidenceError) else "Private metadata I/O or pin error")}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
