"""
.. module:: pmem
.. moduleauthor:: Christian S. Perone <christian.perone@gmail.com>

:mod:`pmem` -- low level persistent memory support
==================================================================

.. seealso:: `NVML libpmem documentation <http://pmem.io/nvml/libpmem/libpmem.3.html>`_.
"""
import os
import sys
from _pmem import lib, ffi

#: Create the named file if it does not exist.
FILE_CREATE = 1

#: Ensure that this call creates the file.
FILE_EXCL = 2

#: When creating a file, create a sparse (holey) file instead of calling
#: posix_fallocate(2)
FILE_SPARSE = 4

#: Create a mapping for an unnamed temporary file.
FILE_TMPFILE = 8


class MemoryBuffer(object):
    """A file-like I/O (similar to cStringIO) for persistent mmap'd regions."""

    def __init__(self, buffer_, is_pmem, mapped_len):
        self.buffer = buffer_
        self.is_pmem = is_pmem
        self.mapped_len = mapped_len
        self.size = len(buffer_)
        self.pos = 0

    def __len__(self):
        return self.size

    def _cdata(self):
        return ffi.from_buffer(self.buffer)

    def write(self, data):
        """Write data into the buffer.

        :param data: data to write into the buffer.
        """
        if not data:
            return

        ldata = len(data)
        if (ldata + self.pos) > self.size:
            raise RuntimeError("Out of range error.")

        new_pos = self.pos + ldata
        self.buffer[self.pos:new_pos] = data
        self.pos = new_pos

    def read(self, size=0):
        """Read data from the buffer.

        :param size: size to read, zero equals to entire buffer size.
        :return: data read.
        """
        if size <= 0:
            if self.pos >= self.size:
                raise EOFError("End of file.")
            data = self.buffer[self.pos:self.size]
            self.pos = self.size
            return data
        else:
            if (self.pos + size) > self.size:
                raise RuntimeError("Out of range error.")
            data = self.buffer[self.pos:self.pos + size]
            self.pos += size
            return data

    def seek(self, pos):
        """Moves the cursor position in the buffer.

        :param pos: the new cursor position
        """
        if pos < 0:
            raise RuntimeError("Negative position.")
        if pos > self.size:
            raise RuntimeError("Out of range error.")
        self.pos = pos

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if is_pmem(self):
                persist(self)
            else:
                msync(self)
            unmap(self)
        return False


class FlushContext(object):
    """A context manager that will automatically flush the
    specified memory buffer.

    :param memory_buffer: the MemoryBuffer object.
    """
    def __init__(self, memory_buffer, unmap=True):
        self.memory_buffer = memory_buffer
        self.unmap = unmap

    def __enter__(self):
        return self.memory_buffer

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            flush(self.memory_buffer)
            if self.unmap:
                unmap(self.memory_buffer)
        return False


class DrainContext(object):
    """A context manager that will automatically drain the
    specified memory buffer.

    :param memory_buffer: the MemoryBuffer object.
    """
    def __init__(self, memory_buffer, unmap=True):
        self.memory_buffer = memory_buffer
        self.unmap = unmap

    def __enter__(self):
        return self.memory_buffer

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            drain(self.memory_buffer)
            if self.unmap:
                unmap(self.memory_buffer)
        return False


def check_version(major_required, minor_required):
    """Checks the libpmem version according to the specified major
    and minor versions required.

    :param major_required: Major version required.
    :param minor_required: Minor version required.
    :return: returns True if the nvm has the required version,
          or raises a RuntimeError exception in case of failure.
    """
    ret = lib.pmem_check_version(major_required, minor_required)
    if ret != ffi.NULL:
        raise RuntimeError(ffi.string(ret))
    return True


def has_hw_drain():
    """This function returns true if the machine supports the
    hardware drain function for persistent memory, such as that provided by the
    PCOMMIT instruction on Intel processors.

    :return: return True if it has hardware drain, False otherwise.
    """
    ret = lib.pmem_has_hw_drain()
    return bool(ret)


def map_file(file_name, file_size, flags, mode):
    """Given a path, this function creates a new read/write
    mapping for the named file. It will map the file using mmap,
    but it also takes extra steps to make large page mappings more
    likely.

    If creation flags are not supplied, then this function creates a mapping
    for an existing file. In such case, `file_size` should be zero. The entire
    file is mapped to memory; its length is used as the length of the
    mapping.

    .. seealso:: `NVML libpmem documentation <http://pmem.io/nvml/libpmem/libpm
                 em.3.html>`_.

    :param file_name: The file name to use.
    :param file_size: the size to allocate
    :param flags: The flags argument can be 0 or bitwise OR of one or more of
                  the following file creation flags:
                  :const:`~nvm.pmem.FILE_CREATE`,
                  :const:`~nvm.pmem.FILE_EXCL`,
                  :const:`~nvm.pmem.FILE_TMPFILE`,
                  :const:`~nvm.pmem.FILE_SPARSE`.
    :return: The mapping, an exception will rise in case
             of error.
    """
    ret_mappend_len = ffi.new("size_t *")
    ret_is_pmem = ffi.new("int *")

    if sys.version_info[0] > 2 and hasattr(file_name, 'encode'):
        file_name = file_name.encode(errors='surrogateescape')
    ret = lib.pmem_map_file(file_name, file_size, flags, mode,
                            ret_mappend_len, ret_is_pmem)

    if ret == ffi.NULL:
        raise RuntimeError(os.strerror(ffi.errno))

    ret_mapped_len = ret_mappend_len[0]
    ret_is_pmem = bool(ret_is_pmem[0])

    cast = ffi.buffer(ret, file_size)
    return MemoryBuffer(cast, ret_is_pmem, ret_mapped_len)


def unmap(memory_buffer):
    """Unmap the specified region.

    :param memory_buffer: the MemoryBuffer object.
    """
    cdata = memory_buffer._cdata()
    ret = lib.pmem_unmap(cdata, len(memory_buffer))

    if ret:
        raise RuntimeError(os.strerror(ffi.errno))

    return ret


def is_pmem(memory_buffer):
    """Return true if entire range is persistent memory.

    :return: True if the entire range is persistent memory, False otherwise.
    """
    cdata = memory_buffer._cdata()
    ret = lib.pmem_is_pmem(cdata, len(memory_buffer))
    return bool(ret)


def persist(memory_buffer):
    """Make any cached changes to a range of pmem persistent.

    :param memory_buffer: the MemoryBuffer object.
    """
    cdata = memory_buffer._cdata()
    lib.pmem_persist(cdata, len(memory_buffer))


def msync(memory_buffer):
    """Flush to persistence via `msync()`.

    :param memory_buffer: the MemoryBuffer object.
    :return: the msync() return result, in case of msync() error,
             an exception will rise.
    """
    cdata = memory_buffer._cdata()
    ret = lib.pmem_msync(cdata, len(memory_buffer))
    if ret:
        raise RuntimeError(os.strerror(ffi.errno))
    return ret


def flush(memory_buffer):
    """Flush processor cache for the given memory region.

    :param memory_buffer: the MemoryBuffer object.
    """
    cdata = memory_buffer._cdata()
    lib.pmem_flush(cdata, len(memory_buffer))


def drain(memory_buffer):
    """Wait for any PM stores to drain from HW buffers.

    :param memory_buffer: the MemoryBuffer object.
    """
    cdata = memory_buffer._cdata()
    lib.pmem_flush(cdata, len(memory_buffer))
