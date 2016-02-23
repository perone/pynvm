"""
.. module:: pmemblk
.. moduleauthor:: Christian S. Perone <christian.perone@gmail.com>

:mod:`pmemblk` -- arrays of pmem-resident blocks
==================================================================

.. seealso:: `NVML libpmemblk documentation <http://pmem.io/nvml/libpmemblk/libpmemblk.3.html>`_.
"""
import os
from _pmem import lib, ffi


class BlockPool(object):
    """This class represents the Block Pool opened or created using
    :func:`~nvm.pmemblk.create()` or :func:`~nvm.pmemblk.open()`.
    """
    def __init__(self, block_pool):
        self.block_pool = block_pool
        self.block_size = self.bsize()

    def close(self):
        """This method closes the memory pool. The block memory pool itself
        lives on in the file that contains it and may be re-opened at a
        later time using :func:`~nvm.pmemblk.open()`.
        """
        lib.pmemblk_close(self.block_pool)
        return None

    def bsize(self):
        """This method returns the block size of the specified block memory
        pool. It's the value which was passed as block size
        to :func:`~nvm.pmemblk.create()`.

        :return: the block size.
        """
        ret = lib.pmemblk_bsize(self.block_pool)
        return ret

    def nblock(self):
        """This method returns the usable space in the block memory pool,
        expressed as the number of blocks available.

        :return: usable space in block memory pool in number of blocks.
        """
        ret = lib.pmemblk_nblock(self.block_pool)
        return ret

    def read(self, block_num):
        """This method reads a block from memory pool at specified block number.

        .. note:: Reading a block that has never been written will return an
                  empty buffer.

        :return: data at block.
        """
        data = ffi.new("char[]", self.block_size)
        ret = lib.pmemblk_read(self.block_pool, data, block_num)
        if ret == -1:
            raise RuntimeError(ffi.string(ret))
        return ffi.string(data)

    def write(self, data, block_num):
        """This method writes a block from data to block number blockno in the
        memory pool. The write is atomic with respect to other reads and
        writes. In addition, the write cannot be torn by program failure
        or system crash; on recovery the block is guaranteed to
        contain either the old data or the new data, never a mixture of both.

        :return: On success, zero is returned. On error, an exception
                 will be raised.
        """
        ret = lib.pmemblk_write(self.block_pool, data, block_num)
        if ret == -1:
            raise RuntimeError(os.strerror(ffi.errno))
        return ret

    def set_zero(self, block_num):
        """This method writes zeros to block number blockno in memory pool.
        Using this function is faster than actually writing a block of zeros
        since libpmemblk uses metadata to indicate the block should read
        back as zero.

        :return: On success, zero is returned. On error, an exception will
                 be raised.
        """
        ret = lib.pmemblk_set_zero(self.block_pool, block_num)
        if ret == -1:
            raise RuntimeError(os.strerror(ffi.errno))
        return ret

    def set_error(self, block_num):
        """This method sets the error state for block number blockno in memory
        pool. A block in the error state returns errno EIO when read. Writing
        the block clears the error state and returns the block to normal use.

        :return: On success, zero is returned. On error, an exception will
                 be raised.
        """
        ret = lib.pmemblk_set_error(self.block_pool, block_num)
        if ret == -1:
            raise RuntimeError(os.strerror(ffi.errno))
        return ret


def open(filename, block_size=0):
    """This function opens an existing block memory pool, returning a memory pool.

    .. note:: If an error prevents the pool from being opened, this function
              will rise an exception. If the block size provided is non-zero,
              it will verify the given block size matches the block size used
              when the pool was created. Otherwise, it will open the pool
              without verification of the block size.

    :param filename: Filename must be an existing file containing a block
                     memory pool as created by the
                     :func:`~nvm.pmemblk.create()` method.
                     The application must have permission to open the file and
                     memory map it with read/write permissions.
    :return: the block memory pool.
    :rtype: BlockPool
    """
    ret = lib.pmemblk_open(filename, block_size)
    if ret == ffi.NULL:
        raise RuntimeError(os.strerror(ffi.errno))
    return BlockPool(ret)


def create(filename, block_size, pool_size=1024 * 1024 * 2, mode=0666):
    """This function function creates a block memory pool with the given
    total pool size divided up into as many elements of block size as will
    fit in the pool.

    .. note:: Since the transactional nature of a block memory pool requires
              some space overhead in the memory pool, the resulting number
              of available blocks is less than poolsize / block size, and is
              made available to the caller via the `nblock()`.

              If the error prevents any of the pool set files from being
              created, this function will raise an exception.

    :param filename: specifies the name of the memory pool file to be created.
    :param block_size: the size of the blocks.
    :param pool_size: the size of the pool (default to 2MB).
    :param mode: specifies the permissions to use when creating the file.
    :return: the new block memory pool created.
    :rtype: BlockPool
    """
    ret = lib.pmemblk_create(filename, block_size, pool_size, mode)
    if ret == ffi.NULL:
        raise RuntimeError(os.strerror(ffi.errno))
    return BlockPool(ret)


def check(filename, block_size=0):
    """This function performs a consistency check of the file indicated
    by path and returns True if the memory pool is found to be consistent.
    Any inconsistencies found will cause it to return False, in which case
    the use of the file with libpmemblk will result in undefined behavior.

    .. note:: When block size is non-zero, it will compare it to the
              block size of the pool and return False when they don't match.

    :return: True if memory pool is consistent, False otherwise.
    """
    ret = lib.pmemblk_check(filename, block_size)
    return ret == 1


def check_version(major_required, minor_required):
    """Checks the libpmemblk version according to the specified major
    and minor versions required.

    :param major_required: Major version required.
    :param minor_required: Minor version required.
    :return: returns True if the nvm has the required version,
          or raises a RuntimeError exception in case of failure.
    """
    ret = lib.pmemblk_check_version(major_required, minor_required)
    if ret != ffi.NULL:
        raise RuntimeError(ffi.string(ret))
    return True
