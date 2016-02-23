"""
.. module:: pmemlog
.. moduleauthor:: Christian S. Perone <christian.perone@gmail.com>

:mod:`pmemlog` -- pmem-resident log file
==================================================================

.. seealso:: `NVML libpmemlog documentation <http://pmem.io/nvml/libpmemlog/libpmemlog.3.html>`_.
"""
import os
from _pmem import lib, ffi


class LogPool(object):
    """This class represents the Log Pool opened or created using
    :func:`~nvm.pmemlog.create()` or :func:`~nvm.pmemlog.open()`.
    """
    def __init__(self, log_pool):
        self.log_pool = log_pool

    def close(self):
        """This method closes the memory pool. The log memory pool itself
        lives on in the file that contains it and may be re-opened at a
        later time using :func:`~nvm.pmemlog.open()`.
        """
        lib.pmemlog_close(self.log_pool)
        return None

    def __len__(self):
        return self.nbyte()

    def nbyte(self):
        """This method returns the amount of usable space in the log pool.
        This method may be used to determine how much usable space is
        available after libpmemlog has added its metadata to the memory pool.

        .. note:: You can also use `len()` to get the usable space.

        :return: amount of usable space in the log pool.
        """
        ret = lib.pmemlog_nbyte(self.log_pool)
        return ret

    def rewind(self):
        """This method resets the current write point for the log to zero.
        After this call, the next append adds to the beginning of the log."""
        lib.pmemlog_rewind(self.log_pool)
        return None

    def tell(self):
        """This method returns the current write point for the log, expressed
        as a byte offset into the usable log space in the memory pool. This
        offset starts off as zero on a newly-created log, and is incremented
        by each successful append operation. This function can be used to
        determine how much data is currently in the log.

        :return: the current write point for the log, expressed as
                 a byte offset.
        """
        ret = lib.pmemlog_tell(self.log_pool)
        return ret

    def append(self, buf):
        """This method appends from buffer to the current write offset in
        the log memory pool plp. Calling this function is analogous to
        appending to a file. The append is atomic and cannot be torn
        by a program failure or system crash.

        On success, zero is returned. On error, -1 is returned and errno
        is set.
        """
        ret = lib.pmemlog_append(self.log_pool, buf, len(buf))
        return ret

    def walk(self, func, chunk_size=0):
        """This function walks through the log pool, from beginning to end,
        calling the callback function for each chunksize block of data found.
        The chunksize argument is useful for logs with fixed-length records
        and may be specified as 0 to cause a single call to the callback
        with the entire log contents.

        :param chunk_size: chunk size or 0 for total length (default to 0).
        :param func: the callback function, should return 1 if it should
                     continue walking through the log, or 0 to terminate
                     the walk.
        """
        def inner_walk(buf, len, arg):
            cast_buf = ffi.cast("char *", buf)
            data = cast_buf[0:len]
            ret = func(ffi.string(data))
            return int(ret)

        ffi_func = ffi.callback("int(void *buf, size_t len, void *arg)",
                                inner_walk)
        ret = lib.pmemlog_walk(self.log_pool, chunk_size,
                               ffi_func, ffi.NULL)
        return ret


def check_version(major_required, minor_required):
    """Checks the libpmemlog version according to the specified major
    and minor versions required.

    :param major_required: Major version required.
    :param minor_required: Minor version required.
    :return: returns True if the nvm has the required version,
          or raises a RuntimeError exception in case of failure.
    """
    ret = lib.pmemlog_check_version(major_required, minor_required)
    if ret != ffi.NULL:
        raise RuntimeError(ffi.string(ret))
    return True


def check(filename):
    """This method performs a consistency check of the file indicated
    and returns `True` if the memory pool is found to be consistent.
    Any inconsistencies found will cause this function to return False,
    in which case the use of the file with libpmemlog will result
    in undefined behavior.

    :return: True if memory pool is consistent, False otherwise.
    """
    ret = lib.pmemlog_check(filename)
    return ret == 1


def open(filename):
    """This function opens an existing log memory pool, returning a memory pool.

    .. note:: If an error prevents the pool from being opened, this function
              will rise an exception.

    :param filename: Filename must be an existing file containing a log memory
                     pool as created by the :func:`~nvm.pmemlog.create()`
                     method.
                     The application must have permission to open the file and
                     memory map it with read/write permissions.
    :return: the log memory pool.
    :rtype: LogPool
    """
    ret = lib.pmemlog_open(filename)
    if ret == ffi.NULL:
        raise RuntimeError(os.strerror(ffi.errno))
    return LogPool(ret)


def create(filename, pool_size=1024 * 1024 * 2, mode=0666):
    """The `create()` function creates a log memory pool with the given total
    `pool_size`. Since the transactional nature of a log memory pool
    requires some space overhead in the memory pool, the resulting available
    log size is less than poolsize, and is made available to the caller via
    the `nbyte()` function.

    .. note:: If the error prevents any of the pool set files from being
              created, this function will raise an exception.

    :param filename: specifies the name of the memory pool file to be created.
    :param pool_size: the size of the pool (default to 2MB).
    :param mode: specifies the permissions to use when creating the file.
    :return: the new log memory pool created.
    :rtype: LogPool
    """
    ret = lib.pmemlog_create(filename, pool_size, mode)
    if ret == ffi.NULL:
        raise RuntimeError(os.strerror(ffi.errno))
    return LogPool(ret)
