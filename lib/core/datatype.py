#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

import copy
import threading
import types
from dataclasses import dataclass, field
from typing import (
    List, Optional, Any, Dict, TypeVar, Generic, Protocol, Union,
    Iterator, Mapping, MutableSet, TypedDict, runtime_checkable
)

from thirdparty.odict import OrderedDict
import collections.abc as _collections

# Generic type variables
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# Protocols for duck typing
@runtime_checkable
class SQLMapConfigProtocol(Protocol):
    """Protocol for SQLMap configuration objects"""

    def get(self, key: str, default: Any = None) -> Any: ...

    def __getitem__(self, key: str) -> Any: ...

    def __setitem__(self, key: str, value: Any) -> None: ...


@runtime_checkable
class CacheProtocol(Protocol[K, V]):
    """Protocol for cache-like objects"""

    def __getitem__(self, key: K) -> V: ...

    def __setitem__(self, key: K, value: V) -> None: ...

    def __contains__(self, key: K) -> bool: ...

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]: ...


# TypedDict for configuration dictionaries
class SQLMapConfig(TypedDict, total=False):
    """Type definition for SQLMap configuration dictionary"""
    url: Optional[str]
    method: Optional[str]
    data: Optional[str]
    cookie: Optional[str]
    headers: Optional[str]
    userAgent: Optional[str]
    timeout: Optional[int]
    retries: Optional[int]
    randomAgent: Optional[bool]
    threads: Optional[int]
    level: Optional[int]
    risk: Optional[int]
    technique: Optional[str]
    dbms: Optional[str]
    os: Optional[str]
    tamper: Optional[str]
    batch: Optional[bool]
    verbose: Optional[int]


class InjectionConfig(TypedDict, total=False):
    """Type definition for injection-specific configuration"""
    timeSec: Optional[int]
    unionCols: Optional[str]
    unionChar: Optional[str]
    unionFrom: Optional[str]
    dnsName: Optional[str]
    secondUrl: Optional[str]
    secondReq: Optional[str]


class AttribDict(dict, Generic[K, V]):
    """
    This class defines the dictionary with added capability to access members as attributes

    >>> foo = AttribDict()
    >>> foo.bar = 1
    >>> foo.bar
    1
    """

    def __init__(self, indict: Optional[Dict[K, V]] = None, attribute: Optional[str] = None, keycheck: bool = True):
        if indict is None:
            indict = {}

        # Set any attributes here - before initialisation
        # these remain as normal attributes
        self.attribute = attribute
        self.keycheck = keycheck
        dict.__init__(self, indict)
        self.__initialised = True

        # After initialisation, setting attributes
        # is the same as setting an item

    def __getattr__(self, item: str) -> Any:
        """
        Maps values to attributes
        Only called if there *is NOT* an attribute with this name
        """

        try:
            return self.__getitem__(item)
        except KeyError:
            if self.keycheck:
                raise AttributeError("unable to access item '%s'" % item)
            else:
                return None

    def __delattr__(self, item: str) -> Any:
        """
        Deletes attributes
        """

        try:
            return self.pop(item)
        except KeyError:
            if self.keycheck:
                raise AttributeError("unable to access item '%s'" % item)
            else:
                return None

    def __setattr__(self, item: str, value: Any) -> None:
        """
        Maps attributes to values
        Only if we are initialised
        """

        # This test allows attributes to be set in the __init__ method
        if "_AttribDict__initialised" not in self.__dict__:
            return dict.__setattr__(self, item, value)

        # Any normal attributes are handled normally
        elif item in self.__dict__:
            dict.__setattr__(self, item, value)

        else:
            self.__setitem__(item, value)

    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    def __setstate__(self, dict: Dict[str, Any]) -> None:
        self.__dict__ = dict

    def __deepcopy__(self, memo: Dict[int, Any]) -> 'AttribDict[K, V]':
        retVal = self.__class__()
        memo[id(self)] = retVal

        for attr in dir(self):
            if not attr.startswith('_'):
                value = getattr(self, attr)
                if not isinstance(value, (types.BuiltinFunctionType, types.FunctionType, types.MethodType)):
                    setattr(retVal, attr, copy.deepcopy(value, memo))

        for key, value in self.items():
            retVal.__setitem__(key, copy.deepcopy(value, memo))

        return retVal


@dataclass(slots=True)
class InjectionData:
    """
    Data class for injection detection information
    """
    place: Optional[str] = None
    parameter: Optional[str] = None
    ptype: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    clause: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    data: AttribDict[str, Any] = field(default_factory=AttribDict)
    conf: AttribDict[str, Any] = field(default_factory=AttribDict)
    dbms: Optional[str] = None
    dbms_version: Optional[str] = None
    os: Optional[str] = None


class InjectionDict(AttribDict[str, Any]):
    def __init__(self):
        AttribDict.__init__(self)
        injection_data = InjectionData()

        # Copy all fields from dataclass to the dict
        for field_name, field_value in injection_data.__dict__.items():
            setattr(self, field_name, field_value)


# Reference: https://www.kunxi.org/2014/05/lru-cache-in-python
class LRUDict(Generic[K, V], CacheProtocol[K, V]):
    """
    This class defines the LRU dictionary

    >>> foo = LRUDict(capacity=2)
    >>> foo["first"] = 1
    >>> foo["second"] = 2
    >>> foo["third"] = 3
    >>> "first" in foo
    False
    >>> "third" in foo
    True
    """

    __slots__ = ('capacity', 'cache', '_LRUDict__lock')

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict[K, V] = OrderedDict()
        self.__lock = threading.Lock()

    def __len__(self) -> int:
        return len(self.cache)

    def __contains__(self, key: K) -> bool:
        return key in self.cache

    def __getitem__(self, key: K) -> V:
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __setitem__(self, key: K, value: V) -> None:
        with self.__lock:
            try:
                self.cache.pop(key)
            except KeyError:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
        self.cache[key] = value

    def set(self, key: K, value: V) -> None:
        self.__setitem__(key, value)

    def keys(self) -> Iterator[K]:
        return self.cache.keys()


# Reference: https://code.activestate.com/recipes/576694/
class OrderedSet(Generic[T], MutableSet[T]):
    """
    This class defines the set with ordered (as added) items

    >>> foo = OrderedSet()
    >>> foo.add(1)
    >>> foo.add(2)
    >>> foo.add(3)
    >>> foo.pop()
    3
    >>> foo.pop()
    2
    >>> foo.pop()
    1
    """

    __slots__ = ('end', 'map')

    def __init__(self, iterable: Optional[Iterator[T]] = None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map: Dict[T, List] = {}  # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self) -> int:
        return len(self.map)

    def __contains__(self, key: object) -> bool:
        return key in self.map

    def add(self, value: T) -> None:
        if value not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[value] = [value, curr, end]

    def discard(self, value: T) -> None:
        if value in self.map:
            value, prev, next = self.map.pop(value)
            prev[2] = next
            next[1] = prev

    def __iter__(self) -> Iterator[T]:
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self) -> Iterator[T]:
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last: bool = True) -> T:
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self) -> str:
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def remove(self, value: T) -> None:
        if value not in self.map:
            raise KeyError(value)
        self.discard(value)
