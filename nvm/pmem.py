"""
.. module:: pmem
.. moduleauthor:: Christian S. Perone <christian.perone@gmail.com>

:mod:`pmem` -- low level persistent memory support
==================================================================

.. seealso:: `NVML libpmem documentation <http://pmem.io/nvml/libpmem/libpmem.3.html>`_.
"""
import os
from _pmem import lib, ffi


class MemoryBuffer(object):
    """A file-like I/O (similar to cStringIO) for persistent mmap'd regions."""

    def __init__(self, buffer_):
        self.buffer = buffer_
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


def map(file_, size):
    """Map the entire file for read/write access

    :param file: The file descriptor of a file object.
    :return: The mapping, an exception will rise in case
             of error.
    """
    if hasattr(file_, 'fileno'):
        ret = lib.pmem_map(file_.fileno())
    else:
        ret = lib.pmem_map(file_)

    if ret == ffi.NULL:
        raise RuntimeError(os.strerror(ffi.errno))

    cast = ffi.buffer(ret, size)
    return MemoryBuffer(cast)


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
