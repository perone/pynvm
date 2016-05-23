import sys
import unittest
import os
import uuid

from nvm import pmem


class MapMixin(object):

    def create_mapping(self, size=4096):
        filename = "{}.pmem".format(uuid.uuid4())
        mapping = pmem.map_file(filename, size,
                                pmem.FILE_CREATE | pmem.FILE_EXCL,
                                0o666)
        return filename, mapping

    def clear_mapping(self, filename, mapping):
        pmem.unmap(mapping)
        os.unlink(filename)


class TestCheckVersion(unittest.TestCase):
    def test_version_ok(self):
        self.assertTrue(pmem.check_version(1, 0))

    def test_wrong_version(self):
        with self.assertRaises(RuntimeError):
            pmem.check_version(1000, 1000)


class TestHasHardwareDrain(unittest.TestCase):
    def test_has_hw_drain(self):
        self.assertIn(pmem.has_hw_drain(), [True, False])


class TestMap(unittest.TestCase, MapMixin):
    def test_map_ok(self):
        filename, mapping = self.create_mapping()
        self.assertIsInstance(mapping, pmem.MemoryBuffer)
        self.clear_mapping(filename, mapping)


class TestMemoryBuffer(unittest.TestCase, MapMixin):
    def test_len(self):
        filename, mapping = self.create_mapping(4096)
        self.assertEqual(len(mapping), 4096)
        self.clear_mapping(filename, mapping)

    def test_write_seek_read(self):
        filename, mapping = self.create_mapping()
        test_data = b"testing"
        test_len = len(test_data)
        mapping.write(test_data)
        mapping.seek(0)
        self.assertEqual(mapping.read(test_len), test_data)
        self.clear_mapping(filename, mapping)

    def test_write_out_range(self):
        filename, mapping = self.create_mapping(128)
        with self.assertRaises(RuntimeError):
            mapping.write('0' * 256)
        self.clear_mapping(filename, mapping)


class TestIsPmem(unittest.TestCase, MapMixin):
    def test_is_pmem(self):
        filename, mapping = self.create_mapping()
        self.assertIn(pmem.is_pmem(mapping), [True, False])
        self.clear_mapping(filename, mapping)


class TestPersist(unittest.TestCase, MapMixin):
    def test_persist(self):
        filename, mapping = self.create_mapping()
        pmem.persist(mapping)
        self.clear_mapping(filename, mapping)


class TestMsync(unittest.TestCase, MapMixin):
    def test_msync(self):
        filename, mapping = self.create_mapping()
        ret = pmem.msync(mapping)
        self.assertEqual(ret, 0)
        self.clear_mapping(filename, mapping)


class TestFlush(unittest.TestCase, MapMixin):
    def test_flush(self):
        filename, mapping = self.create_mapping()
        pmem.flush(mapping)
        self.clear_mapping(filename, mapping)


class TestHwDrain(unittest.TestCase, MapMixin):
    def test_hw_drain(self):
        filename, mapping = self.create_mapping()
        pmem.drain(mapping)
        self.clear_mapping(filename, mapping)


class TestMapContext(unittest.TestCase):
    def test_map_context(self):
        filename = "{}.pmem".format(uuid.uuid4())
        with pmem.map_file(filename, 4096,
                           pmem.FILE_CREATE | pmem.FILE_EXCL,
                           0o0666) as reg:
            reg.write(b"test")

        os.unlink(filename)


class TestPy2Py3FilenameSupport(unittest.TestCase):

    def test_non_ascii_bytes_filename(self):
        filename = b'\xf4' + "{}.pmem".format(uuid.uuid4()).encode()
        pmem.map_file(filename, 4096,
                      pmem.FILE_CREATE | pmem.FILE_EXCL,
                      0o0666)
        os.unlink(filename)

    if sys.version_info[0] > 2:
        def test_non_ascii_py3_string_filename(self):
            filename = b'\xf4' + "{}.pmem".format(uuid.uuid4()).encode()
            filename = filename.decode(errors='surrogateescape')
            pmem.map_file(filename, 4096,
                          pmem.FILE_CREATE | pmem.FILE_EXCL,
                          0o0666)
            os.unlink(filename)


if __name__ == '__main__':
    unittest.main()
