"""Synthetic-only negative controls for experimental DX2 export table audit."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "dx2"))
from dx2_export_boundary_audit import (  # noqa: E402
    SCHEMA, ExportBoundaryError, _Reader, audit_dx2_export_boundaries,
)


def ci(n: int) -> bytes:
    magnitude = abs(n)
    first = magnitude & 0x3f
    magnitude >>= 6
    result = bytearray([first | (0x80 if n < 0 else 0) | (0x40 if magnitude else 0)])
    while magnitude:
        b = magnitude & 0x7f
        magnitude >>= 7
        result.append(b | (0x80 if magnitude else 0))
    return bytes(result)


def fixture(*, payload_offsets=(512, 520), payload_lengths=(5, 5),
            names=("None", "Class", "StaticMeshActor", "TestActor", "OtherActor"),
            second_name=4, version=95, licensee=68, import_name=2):
    name_table = b"".join(ci(len(n) + 1) + n.encode("ascii") + b"\0" + struct.pack("<I", 0)
                          for n in names)
    import_table = ci(1) + ci(2) + struct.pack("<i", 0) + ci(import_name)
    export_table = b""
    for index, (offset, length) in enumerate(zip(payload_offsets, payload_lengths)):
        export_table += (ci(-1) + ci(0) + struct.pack("<i", 0) + ci(3 if index == 0 else second_name)
                         + struct.pack("<I", 0) + ci(length) + (ci(offset) if length else b""))
    header_size = 76  # DX2 v95: header, extra dword, GUID, generation, 2 extras
    no = header_size
    io = no + len(name_table)
    eo = io + len(import_table)
    header = (struct.pack("<IHHI", 0x9E2A83C1, version, licensee, 0)
              + struct.pack("<IIIIII", len(names), no, 2, eo, 1, io)
              + struct.pack("<I", 0) + b"SYNTHETIC-GUID!!" + struct.pack("<I", 1)
              + struct.pack("<II", 2, len(names)) + struct.pack("<II", 0, 0))
    assert len(header) == header_size
    data = bytearray(header + name_table + import_table + export_table)
    for i, (offset, length) in enumerate(zip(payload_offsets, payload_lengths)):
        if length:
            if offset < len(data):
                # Deliberately permit invalid, overlapping test ranges without modifying tables.
                continue
            data.extend(bytes(offset + length - len(data)))
            data[offset:offset + length] = bytes([0x41 + i]) * length
    return bytes(data), {"no": no, "io": io, "eo": eo, "end_tables": eo + len(export_table)}


class ExportBoundaryAuditTests(unittest.TestCase):
    def audit(self, source):
        return audit_dx2_export_boundaries(source, source_sha256=sha256(source).hexdigest())

    def test_valid_synthetic_layout_retains_non_authoritative_status(self):
        source, bounds = fixture()
        original = bytes(source)
        result = self.audit(source)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["table_ranges"]["names"]["offset"], bounds["no"])
        self.assertEqual(result["table_ranges"]["exports"]["offset"], bounds["eo"])
        self.assertEqual(result["table_counts"], {"names": 5, "imports": 1, "exports": 2})
        self.assertEqual(result["candidate_export_envelopes"], [
            {"export": 1, "offset": 512, "length": 5},
            {"export": 2, "offset": 520, "length": 5},
        ])
        self.assertTrue(result["table_structural_checks_passed"])
        self.assertFalse(result["export_envelopes_independently_verified"])
        self.assertFalse(result["native_bsp_leaf_zone_decoded"])
        self.assertFalse(result["runtime_game_verified"])
        self.assertFalse(result["writable"])
        self.assertEqual(source, original)
        self.assertEqual(self.audit(source), result)

    def test_reject_wrong_magic_version_licensee_and_sha(self):
        source, _ = fixture()
        for modified in (b"BAD!" + source[4:], fixture(version=94)[0],
                         fixture(licensee=70)[0], bytearray(source)):
            with self.subTest(modified=type(modified)), self.assertRaises(ExportBoundaryError):
                self.audit(modified)
        with self.assertRaises(ExportBoundaryError):
            audit_dx2_export_boundaries(source, source_sha256="0" * 64)
        with self.assertRaises(ExportBoundaryError):
            audit_dx2_export_boundaries(source, source_sha256=sha256(source).hexdigest().upper())

    def test_reject_export_overlap_table_collision_and_truncation(self):
        samples = (
            fixture(payload_offsets=(512, 515))[0],  # shared byte ranges
            fixture(payload_offsets=(512, 512))[0],  # duplicate byte range
            fixture(payload_offsets=(512, 76))[0],   # header/table collision
            fixture(payload_offsets=(512, 125))[0],  # possible name/import collision
            fixture(payload_offsets=(512, 524))[0],  # adjacent is not overlap
            fixture(payload_offsets=(512, 520))[0][:-1],  # truncated payload
        )
        for index, source in enumerate(samples):
            if index == 4:
                self.assertTrue(self.audit(source))  # adjacent is not an overlap
                continue
            with self.subTest(index=index), self.assertRaises(ExportBoundaryError):
                self.audit(source)

    def test_reject_bad_name_ref_and_export_index(self):
        source, bounds = fixture(second_name=31)
        with self.assertRaises(ExportBoundaryError):
            self.audit(source)
        source, _ = fixture(import_name=20)
        with self.assertRaises(ExportBoundaryError):
            self.audit(source)
        source, bounds = fixture()
        bad = bytearray(source)
        bad[bounds["eo"]] = 0xBF  # negative import -63, only one import exists
        with self.assertRaises(ExportBoundaryError):
            self.audit(bytes(bad))

    def test_reject_invented_malformed_compact_index_and_bad_name_termination(self):
        source, bounds = fixture()
        bad = bytearray(source)
        bad[bounds["no"] + 1 + len("None")] = 0x7a
        with self.assertRaises(ExportBoundaryError):
            self.audit(bytes(bad))
        bad = bytearray(source)
        # A noncanonical zero embedded as first import class package reference.
        bad[bounds["io"]] = 0x40
        with self.assertRaises(ExportBoundaryError):
            self.audit(bytes(bad))

    def test_reject_zero_length_name_record(self):
        source, bounds = fixture()
        bad = bytearray(source)
        bad[bounds["no"]] = 0  # An invented empty name record.
        with self.assertRaisesRegex(ExportBoundaryError, "zero-length package name"):
            self.audit(bytes(bad))

    def test_reject_embedded_name_terminators_in_invented_records(self):
        source, bounds = fixture()
        bad = bytearray(source)
        bad[bounds["no"] + 2] = 0  # Internal ANSI NUL, final NUL intact.
        with self.assertRaisesRegex(ExportBoundaryError, "embedded ANSI"):
            self.audit(bytes(bad))
        # Negative compact length denotes UTF16 code units in this candidate layout.
        for raw in (ci(-3) + b"A\\x00\\x00\\x00\\x00\\x00",
                    ci(-3) + b"A\\x00B\\x00\\x00\\x00"):
            if raw[3:5] == b"\\x00\\x00":
                with self.assertRaisesRegex(ExportBoundaryError, "embedded UTF16"):
                    _Reader(raw).name()
            else:
                _Reader(raw).name()

    def test_reject_zero_export_owner_but_preserve_other_owners(self):
        source, _ = fixture(payload_lengths=(0, 5))
        report = self.audit(source)
        self.assertEqual(report["candidate_export_envelopes"], [
            {"export": 2, "offset": 520, "length": 5}
        ])


if __name__ == "__main__":
    unittest.main()
