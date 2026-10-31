"""Fixture-free unit tests for the read-only DX2 IBD resource probe."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "scripts"))
from dx2_script_bundle_probe import parse_tsd_resources, HEADER_SIZE, ENTRY_SIZE, MAGIC


def example_bundle(kind=21, broken_part=False):
    start = 2048
    data = bytearray(start + 2048)
    struct.pack_into('<8I', data, 0, MAGIC, 2048, start, 2048, 1, 2, 1, 2)
    struct.pack_into('<5I', data, HEADER_SIZE, start, 8, 2040, 0, 2)
    data[HEADER_SIZE + 0x28] = kind
    data[HEADER_SIZE + 0x29:HEADER_SIZE + 0x30] = b'TS_TEST'
    struct.pack_into('<2I', data, HEADER_SIZE + ENTRY_SIZE, 4, 5 if broken_part else 4)
    data[start:start + 8] = b'abcdefgh'
    return bytes(data)


class BundleProbeTests(unittest.TestCase):
    def test_extracts_script_index_and_data(self):
        b = example_bundle()
        summary, resources = parse_tsd_resources(b, bundle_name='test.ibd')
        self.assertEqual(summary['resource_count'], 1)
        self.assertEqual(summary['trigger_scripts'], 1)
        item = resources['ts_test']
        self.assertEqual(item['index'], 0)
        self.assertEqual(item['offset'], 2048)
        self.assertEqual(item['size'], 8)
        self.assertEqual(item['part_sizes'], [4, 4])

    def test_ignores_non_trigger_script_resources(self):
        summary, resources = parse_tsd_resources(example_bundle(kind=4), bundle_name='test.ibd')
        self.assertEqual(summary['trigger_scripts'], 0)
        self.assertFalse(resources)

    def test_rejects_invalid_magic(self):
        b = bytearray(example_bundle())
        b[0] = 0
        with self.assertRaises(ValueError):
            parse_tsd_resources(bytes(b), bundle_name='test.ibd')

    def test_rejects_partition_size_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'invalid layout'):
            parse_tsd_resources(example_bundle(broken_part=True), bundle_name='test.ibd')

    def test_rejects_truncated_header(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            parse_tsd_resources(b'123', bundle_name='test.ibd')


if __name__ == '__main__':
    unittest.main()
