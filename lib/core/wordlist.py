#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

import zipfile
from typing import List, Union, Optional, Any, Iterator

from lib.core.common import getSafeExString
from lib.core.common import isZipFile
from lib.core.exception import SqlmapDataException
from lib.core.exception import SqlmapInstallationException


class Wordlist(object):
    """
    Iterator for looping over a large dictionaries with context manager support

    >>> from lib.core.option import paths
    >>> isinstance(next(Wordlist(paths.SMALL_DICT)), bytes)
    True
    >>> isinstance(next(Wordlist(paths.WORDLIST)), bytes)
    True
    >>> with Wordlist(paths.SMALL_DICT) as wl:
    ...     isinstance(next(wl), bytes)
    True
    """

    def __init__(self, filenames: Union[str, List[str]], proc_id: Optional[int] = None,
                 proc_count: Optional[int] = None, custom: Optional[List[str]] = None) -> None:
        self.filenames: List[str] = [filenames] if isinstance(filenames, str) else filenames
        self.fp: Optional[Any] = None
        self.index: int = 0
        self.counter: int = -1
        self.current: Optional[str] = None
        self.iter: Optional[Iterator[bytes]] = None
        self.custom: List[str] = custom or []
        self.proc_id: Optional[int] = proc_id
        self.proc_count: Optional[int] = proc_count
        self.adjust()

    def __iter__(self) -> 'Wordlist':
        return self

    def __enter__(self) -> 'Wordlist':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.closeFP()

    def adjust(self) -> None:
        self.closeFP()
        if self.index > len(self.filenames):
            return  # Note: https://stackoverflow.com/a/30217723 (PEP 479)
        elif self.index == len(self.filenames):
            self.iter = iter(self.custom)
        else:
            self.current = self.filenames[self.index]
            if isZipFile(self.current):
                try:
                    _ = zipfile.ZipFile(self.current, 'r')
                except zipfile.error as ex:
                    errMsg = "something appears to be wrong with "
                    errMsg += "the file '%s' ('%s'). Please make " % (self.current, getSafeExString(ex))
                    errMsg += "sure that you haven't made any changes to it"
                    raise SqlmapInstallationException(errMsg)
                if len(_.namelist()) == 0:
                    errMsg = "no file(s) inside '%s'" % self.current
                    raise SqlmapDataException(errMsg)
                self.fp = _.open(_.namelist()[0])
            else:
                self.fp = open(self.current, "rb")
            self.iter = iter(self.fp)

        self.index += 1

    def closeFP(self) -> None:
        if self.fp:
            self.fp.close()
            self.fp = None

    def __next__(self) -> bytes:
        retVal: Optional[bytes] = None
        while True:
            self.counter += 1
            try:
                retVal = next(self.iter).rstrip()
            except zipfile.error as ex:
                errMsg = "something appears to be wrong with "
                errMsg += "the file '%s' ('%s'). Please make " % (self.current, getSafeExString(ex))
                errMsg += "sure that you haven't made any changes to it"
                raise SqlmapInstallationException(errMsg)
            except StopIteration:
                self.adjust()
                retVal = next(self.iter).rstrip()
            if not self.proc_count or self.counter % self.proc_count == self.proc_id:
                break
        return retVal

    def rewind(self) -> None:
        self.index = 0
        self.adjust()
