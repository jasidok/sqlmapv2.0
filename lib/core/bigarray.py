#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

try:
    import cPickle as pickle
except:
    import pickle

import itertools
import os
import sys
import tempfile
import threading
import zlib
from pathlib import Path
from typing import Any, Iterator, List, Optional, Set, Union, Generic, TypeVar
from functools import lru_cache

from lib.core.compat import xrange
from lib.core.enums import MKSTEMP_PREFIX
from lib.core.exception import SqlmapSystemException
from lib.core.settings import BIGARRAY_CHUNK_SIZE
from lib.core.settings import BIGARRAY_COMPRESS_LEVEL

# Type variable for generic BigArray
T = TypeVar('T')

try:
    DEFAULT_SIZE_OF = sys.getsizeof(object())
except TypeError:
    DEFAULT_SIZE_OF = 16


@lru_cache(maxsize=512)
def _size_of(instance: Any) -> int:
    """
    Returns total size of a given instance / object (in bytes) with caching for performance
    """

    try:
        retval = sys.getsizeof(instance, DEFAULT_SIZE_OF)
    except (TypeError, ValueError):
        return DEFAULT_SIZE_OF

    if isinstance(instance, dict):
        try:
            retval += sum(_size_of(item) for item in itertools.chain.from_iterable(instance.items())
                          if item != instance)
        except (RuntimeError, RecursionError):
            # Handle circular references
            pass
    elif hasattr(instance, "__iter__") and not isinstance(instance, (str, bytes)):
        try:
            retval += sum(_size_of(item) for item in instance if item != instance)
        except (RuntimeError, RecursionError, TypeError):
            # Handle circular references and non-iterable types
            pass

    return retval


class Cache:
    """
    Auxiliary class used for storing cached chunks with slots for memory efficiency
    """

    __slots__ = ('index', 'data', 'dirty', '_last_access')

    def __init__(self, index: int, data: List[Any], dirty: bool = False):
        self.index = index
        self.data = data
        self.dirty = dirty
        self._last_access = 0  # For potential LRU eviction in future


class BigArray(Generic[T], list):
    """
    List-like class used for storing large amounts of data (disk cached) with modern optimizations

    >>> _ = BigArray(range(100000))
    >>> _[20] = 0
    >>> _[99999]
    99999
    >>> _ += [0]
    >>> _[100000]
    0
    >>> _ = _ + [1]
    >>> _[-1]
    1
    >>> len([_ for _ in BigArray(range(100000))])
    100000
    """

    __slots__ = (
        'chunks', 'chunk_length', 'cache', 'filenames', '_lock',
        '_os_remove', '_size_counter', '_closed', '_compress_level'
    )

    def __init__(self, items: Optional[Iterator[T]] = None,
                 chunk_size: int = BIGARRAY_CHUNK_SIZE,
                 compress_level: int = BIGARRAY_COMPRESS_LEVEL):
        self.chunks: List[Union[List[T], str]] = [[]]
        self.chunk_length = sys.maxsize
        self.cache: Optional[Cache] = None
        self.filenames: Set[str] = set()
        self._lock = threading.RLock()  # Use RLock for better thread safety
        self._os_remove = os.remove
        self._size_counter = 0
        self._closed = False
        self._compress_level = compress_level

        # Override chunk size if provided
        if chunk_size != BIGARRAY_CHUNK_SIZE:
            self.chunk_length = chunk_size
            self._size_counter = None

        if items is not None:
            self.extend(items)

    def __enter__(self) -> 'BigArray[T]':
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager cleanup"""
        self.close()

    def __add__(self, value: Iterator[T]) -> 'BigArray[T]':
        retval = BigArray(self)
        retval.extend(value)
        return retval

    def __iadd__(self, value: Iterator[T]) -> 'BigArray[T]':
        self.extend(value)
        return self

    def append(self, value: T) -> None:
        if self._closed:
            raise ValueError("Operation on closed BigArray")

        with self._lock:
            self.chunks[-1].append(value)

            # Dynamic chunk size calculation for better memory management
            if self.chunk_length == sys.maxsize and self._size_counter is not None:
                self._size_counter += _size_of(value)
                if self._size_counter >= BIGARRAY_CHUNK_SIZE:
                    self.chunk_length = max(len(self.chunks[-1]), 1)  # Avoid zero length
                    self._size_counter = None

            if len(self.chunks[-1]) >= self.chunk_length:
                filename = self._dump(self.chunks[-1])
                self.chunks[-1] = filename
                self.chunks.append([])

    def extend(self, values: Iterator[T]) -> None:
        """Efficiently extend with multiple values"""
        if self._closed:
            raise ValueError("Operation on closed BigArray")

        # Batch append for better performance
        for value in values:
            self.append(value)

    def pop(self) -> T:
        if self._closed:
            raise ValueError("Operation on closed BigArray")

        with self._lock:
            if len(self.chunks[-1]) < 1:
                if len(self.chunks) <= 1:
                    raise IndexError("pop from empty BigArray")

                self.chunks.pop()
                self._load_chunk(-1)

            return self.chunks[-1].pop()

    def index(self, value: T, start: int = 0, stop: Optional[int] = None) -> int:
        """Find index of value with optional start/stop parameters"""
        length = len(self)
        stop = length if stop is None else min(stop, length)

        for index in range(start, stop):
            if self[index] == value:
                return index

        raise ValueError(f"{value} is not in BigArray")

    def close(self) -> None:
        """Explicitly close and cleanup temporary files"""
        if self._closed:
            return

        with self._lock:
            self._closed = True
            while self.filenames:
                filename = self.filenames.pop()
                try:
                    self._os_remove(filename)
                except OSError:
                    pass  # File might already be deleted

            # Clear cache
            self.cache = None

    def __del__(self) -> None:
        """Cleanup on garbage collection"""
        try:
            self.close()
        except:
            pass  # Ignore errors during cleanup

    def _dump(self, chunk: List[T]) -> str:
        """Dump chunk to disk with better error handling"""
        try:
            handle, filename = tempfile.mkstemp(prefix=MKSTEMP_PREFIX.BIG_ARRAY)
            self.filenames.add(filename)
            os.close(handle)

            # Use highest protocol for better performance
            data = pickle.dumps(chunk, pickle.HIGHEST_PROTOCOL)
            compressed_data = zlib.compress(data, self._compress_level)

            with open(filename, "w+b") as f:
                f.write(compressed_data)
            return filename
        except (OSError, IOError) as ex:
            errMsg = f"exception occurred while storing data to a temporary file ('{ex}'). Please "
            errMsg += "make sure that there is enough disk space left. If problem persists, "
            errMsg += "try to set environment variable 'TEMP' to a location "
            errMsg += "writeable by the current user"
            raise SqlmapSystemException(errMsg)

    def _load_chunk(self, index: int) -> None:
        """Load chunk from disk into memory"""
        try:
            filename = self.chunks[index]
            if isinstance(filename, str):
                with open(filename, "rb") as f:
                    data = pickle.loads(zlib.decompress(f.read()))
                self.chunks[index] = data
        except (IOError, OSError, pickle.PickleError, zlib.error) as ex:
            errMsg = f"exception occurred while retrieving data from a temporary file ('{ex}')"
            raise SqlmapSystemException(errMsg)

    def _checkcache(self, index: int) -> None:
        """Check and update cache with improved logic"""
        # Write dirty cache to disk
        if self.cache and self.cache.index != index and self.cache.dirty:
            filename = self._dump(self.cache.data)
            self.chunks[self.cache.index] = filename
            self.cache.dirty = False

        # Load new chunk if not already cached
        if not (self.cache and self.cache.index == index):
            try:
                filename = self.chunks[index]
                if isinstance(filename, str):
                    with open(filename, "rb") as f:
                        data = pickle.loads(zlib.decompress(f.read()))
                    self.cache = Cache(index, data, False)
                else:
                    # Chunk is still in memory
                    self.cache = Cache(index, filename, False)
            except Exception as ex:
                errMsg = f"exception occurred while retrieving data from a temporary file ('{ex}')"
                raise SqlmapSystemException(errMsg)

    def __getstate__(self) -> tuple:
        """Support for pickling"""
        return (self.chunks, self.filenames, self.chunk_length, self._compress_level)

    def __setstate__(self, state: tuple) -> None:
        """Support for unpickling"""
        if len(state) == 4:
            chunks, filenames, chunk_length, compress_level = state
        else:
            # Backward compatibility
            chunks, filenames = state[:2]
            chunk_length = sys.maxsize
            compress_level = BIGARRAY_COMPRESS_LEVEL

        self.__init__()
        self.chunks = chunks
        self.filenames = filenames
        self.chunk_length = chunk_length
        self._compress_level = compress_level

    def __getitem__(self, key: Union[int, slice]) -> Union[T, 'BigArray[T]']:
        if self._closed:
            raise ValueError("Operation on closed BigArray")

        if isinstance(key, slice):
            return self._getslice(key)

        length = len(self)
        if length == 0:
            raise IndexError("BigArray index out of range")

        # Handle negative indices
        if key < 0:
            key += length

        if key < 0 or key >= length:
            raise IndexError("BigArray index out of range")

        index = key // self.chunk_length
        offset = key % self.chunk_length
        chunk = self.chunks[index]

        if isinstance(chunk, list):
            return chunk[offset]
        else:
            self._checkcache(index)
            return self.cache.data[offset]

    def _getslice(self, key: slice) -> 'BigArray[T]':
        """Handle slice operations efficiently"""
        start, stop, step = key.indices(len(self))
        result = BigArray()

        if step == 1:
            # Optimized path for simple slices
            for i in range(start, stop):
                result.append(self[i])
        else:
            # General case with step
            for i in range(start, stop, step):
                result.append(self[i])

        return result

    def __setitem__(self, key: int, value: T) -> None:
        if self._closed:
            raise ValueError("Operation on closed BigArray")

        length = len(self)
        if key < 0:
            key += length

        if key < 0 or key >= length:
            raise IndexError("BigArray assignment index out of range")

        index = key // self.chunk_length
        offset = key % self.chunk_length
        chunk = self.chunks[index]

        if isinstance(chunk, list):
            chunk[offset] = value
        else:
            self._checkcache(index)
            self.cache.data[offset] = value
            self.cache.dirty = True

    def __repr__(self) -> str:
        if self._closed:
            return "BigArray(closed)"
        prefix = "..." if len(self.chunks) > 1 else ""
        return f"{prefix}{self.chunks[-1]!r}"

    def __iter__(self) -> Iterator[T]:
        """Efficient iterator implementation"""
        length = len(self)
        for i in range(length):
            try:
                yield self[i]
            except IndexError:
                break

    def __len__(self) -> int:
        if self._closed:
            return 0
        return (len(self.chunks[-1]) if len(self.chunks) == 1
                else (len(self.chunks) - 1) * self.chunk_length + len(self.chunks[-1]))

    def clear(self) -> None:
        """Clear all data and cleanup temporary files"""
        with self._lock:
            self.close()
            self.__init__()

    def count(self, value: T) -> int:
        """Count occurrences of value"""
        return sum(1 for item in self if item == value)

    def reverse(self) -> None:
        """Reverse the BigArray in place (warning: can be memory intensive)"""
        if self._closed:
            raise ValueError("Operation on closed BigArray")

        # For large arrays, this could be memory intensive
        # Consider implementing a more memory-efficient version if needed
        items = list(self)
        items.reverse()
        self.clear()
        self.extend(items)
