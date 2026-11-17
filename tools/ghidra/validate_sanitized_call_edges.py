#!/usr/bin/env python3
"""Source-only contract for future sanitized Ghidra call-reference reports.

An accepted edge is static reference evidence, never proof of an engine API,
GMP/IBD loading, actor registration, or in-game behavior.
"""
import argparse
import json
import re
import unittest

HEX = re.compile(r"^(?:[0-9a-fA-F]{1,8}:)?[0-9a-fA-F]{1,16}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
TOP = {"schema", "executable_sha256", "ghidra_version", "edges",
       "runtime_verified", "native_writer_ready"}
EDGE = {"caller", "callee", "reference_kind"}
KINDS = {"CALL", "JUMP", "DATA"}


def canonical_address(value):
    """Normalize equivalent hexadecimal spellings for duplicate detection."""
    if ":" in value:
        segment, offset = value.split(":")
        return (int(segment, 16), int(offset, 16))
    return (None, int(value, 16))


def validate(doc):
    if type(doc) is not dict or set(doc) != TOP:
        raise ValueError("unexpected top-level fields")
    if doc["schema"] != "DX2-SanitizedCallEdges-v1" or doc["ghidra_version"] != "12.2":
        raise ValueError("unexpected schema or analyzer version")
    if type(doc["executable_sha256"]) is not str or not SHA.fullmatch(doc["executable_sha256"]):
        raise ValueError("invalid executable fingerprint")
    if doc["runtime_verified"] is not False or doc["native_writer_ready"] is not False:
        raise ValueError("unsupported runtime verification claim")
    edges = doc["edges"]
    if type(edges) is not list or len(edges) > 512:
        raise ValueError("invalid edge collection")
    seen = set()
    for edge in edges:
        if type(edge) is not dict or set(edge) != EDGE:
            raise ValueError("unexpected edge fields")
        for field in ("caller", "callee"):
            if type(edge[field]) is not str or not HEX.fullmatch(edge[field]):
                raise ValueError("invalid edge address")
        if type(edge["reference_kind"]) is not str or edge["reference_kind"] not in KINDS:
            raise ValueError("invalid reference kind")
        key = (canonical_address(edge["caller"]), canonical_address(edge["callee"]), edge["reference_kind"])
        if key in seen:
            raise ValueError("duplicate edge")
        seen.add(key)
    return {"schema": doc["schema"], "edge_count": len(edges),
            "reference_kinds": {k: sum(e["reference_kind"] == k for e in edges)
                                for k in sorted(KINDS)},
            "interpretation": "static references only; no API or runtime verification"}


class SyntheticContractTests(unittest.TestCase):
    def fixture(self):
        return {"schema": "DX2-SanitizedCallEdges-v1", "executable_sha256": "a" * 64,
                "ghidra_version": "12.2", "runtime_verified": False,
                "native_writer_ready": False,
                "edges": [{"caller": "005c56a0", "callee": "005c5c69",
                           "reference_kind": "CALL"}]}

    def test_valid_synthetic_reference_is_not_api_proof(self):
        result = validate(self.fixture())
        self.assertEqual(result["edge_count"], 1)
        self.assertIn("no API", result["interpretation"])

    def test_reject_malformed_and_private_fields(self):
        cases = []
        for field, value in (("runtime_verified", True), ("native_writer_ready", True),
                             ("executable_sha256", "a" * 63), ("ghidra_version", "12.1")):
            doc = self.fixture()
            doc[field] = value
            cases.append(doc)
        for field, value in (("caller", "005c56a0:"), ("callee", "not-an-address"),
                             ("reference_kind", "DECOMPILED")):
            doc = self.fixture()
            doc["edges"][0][field] = value
            cases.append(doc)
        doc = self.fixture()
        doc["edges"].append(dict(doc["edges"][0]))
        cases.append(doc)
        doc = self.fixture()
        doc["edges"] *= 513
        cases.append(doc)
        doc = self.fixture()
        doc["edges"][0]["raw_string"] = "private"
        cases.append(doc)
        doc = self.fixture()
        doc["raw_decompilation"] = "private"
        cases.append(doc)
        for doc in cases:
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                validate(doc)

    def test_reject_equivalent_hex_spellings(self):
        doc = self.fixture()
        doc["edges"].append({"caller": "0x0", "callee": "005c5c69", "reference_kind": "CALL"})
        with self.assertRaises(ValueError):
            validate(doc)
        doc = self.fixture()
        doc["edges"].append({"caller": "5C56A0", "callee": "0000005C5C69", "reference_kind": "CALL"})
        with self.assertRaisesRegex(ValueError, "duplicate edge"):
            validate(doc)
        doc = self.fixture()
        doc["edges"] = [{"caller": "0001:000a", "callee": "0002:00ff", "reference_kind": "DATA"},
                        {"caller": "1:A", "callee": "2:FF", "reference_kind": "DATA"}]
        with self.assertRaisesRegex(ValueError, "duplicate edge"):
            validate(doc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="sanitized JSON input; omit with --self-test")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticContractTests)
        if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
            raise SystemExit(1)
    else:
        if not args.input:
            parser.error("input required without --self-test")
        with open(args.input, encoding="utf-8") as source:
            print(json.dumps(validate(json.load(source)), sort_keys=True))


if __name__ == "__main__":
    main()
