"""Asset-free failure-path tests for private DX2 evidence publication."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "run_private_reference_collection.py"
spec = importlib.util.spec_from_file_location("dx2_private_reference", SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class PublicationFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.output = self.directory / "evidence.json"
        self.doc = {"executable_sha256": "0" * 64, "edges": []}

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.directory.glob(".dx2-evidence-*.tmp")), [])

    def test_successful_publication_is_complete(self):
        collector.publish_report(self.doc, self.output)
        self.assertEqual(self.output.read_text(), '{"edges": [], "executable_sha256": "' + "0" * 64 + '"}\n')
        self.assert_no_temporary_files()

    def test_existing_report_is_not_modified(self):
        self.output.write_bytes(b"prior evidence")
        with self.assertRaises(FileExistsError):
            collector.publish_report(self.doc, self.output)
        self.assertEqual(self.output.read_bytes(), b"prior evidence")
        self.assert_no_temporary_files()

    def test_serialization_failure_leaves_no_report(self):
        with mock.patch.object(collector.json, "dumps", side_effect=TypeError("invalid")):
            with self.assertRaises(TypeError):
                collector.publish_report(self.doc, self.output)
        self.assertFalse(self.output.exists())
        self.assert_no_temporary_files()

    def test_hard_link_failure_cleans_temporary_file(self):
        with mock.patch.object(collector.os, "link", side_effect=OSError("link unavailable")):
            with self.assertRaises(OSError):
                collector.publish_report(self.doc, self.output)
        self.assertFalse(self.output.exists())
        self.assert_no_temporary_files()

    def test_fsync_failure_leaves_no_report(self):
        with mock.patch.object(collector.os, "fsync", side_effect=OSError("sync failed")):
            with self.assertRaises(OSError):
                collector.publish_report(self.doc, self.output)
        self.assertFalse(self.output.exists())
        self.assert_no_temporary_files()

    def test_directory_sync_io_error_is_reported_after_publication(self):
        original_fsync = collector.os.fsync
        calls = 0

        def fail_directory_sync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(5, "directory I/O error")
            return original_fsync(fd)

        with mock.patch.object(collector.os, "fsync", side_effect=fail_directory_sync):
            with self.assertRaises(OSError):
                collector.publish_report(self.doc, self.output)
        self.assertEqual(calls, 2)
        self.assertTrue(self.output.is_file())
        self.assert_no_temporary_files()

    def test_unsupported_directory_sync_preserves_report(self):
        import errno
        original_fsync = collector.os.fsync
        calls = 0

        def unsupported_directory_sync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(errno.EINVAL, "directory sync unsupported")
            return original_fsync(fd)

        with mock.patch.object(collector.os, "fsync", side_effect=unsupported_directory_sync):
            collector.publish_report(self.doc, self.output)
        self.assertEqual(calls, 2)
        self.assertTrue(self.output.is_file())
        self.assert_no_temporary_files()

    def test_race_with_existing_destination_never_overwrites(self):
        def competing_writer(_src, dst):
            Path(dst).write_bytes(b"competing report")
            raise FileExistsError("destination exists")
        with mock.patch.object(collector.os, "link", side_effect=competing_writer):
            with self.assertRaises(FileExistsError):
                collector.publish_report(self.doc, self.output)
        self.assertEqual(self.output.read_bytes(), b"competing report")
        self.assert_no_temporary_files()


if __name__ == "__main__":
    unittest.main()
