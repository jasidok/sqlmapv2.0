#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

try:
    import cPickle as pickle
except:
    import pickle

import base64
import binascii
import codecs
import collections.abc
import json
import re
import sys
import time
from typing import Optional, Union, List, Any, Tuple
from functools import lru_cache

from lib.core.bigarray import BigArray
from lib.core.compat import xrange
from lib.core.data import conf
from lib.core.data import kb
from lib.core.settings import INVALID_UNICODE_PRIVATE_AREA
from lib.core.settings import IS_TTY
from lib.core.settings import IS_WIN
from lib.core.settings import NULL
from lib.core.settings import PICKLE_PROTOCOL
from lib.core.settings import SAFE_HEX_MARKER
from lib.core.settings import UNICODE_ENCODING

try:
    from html import escape as htmlEscape
except ImportError:
    from cgi import escape as htmlEscape


# Modern encoding patterns for Python 3.11+
@lru_cache(maxsize=256)
def detect_encoding(data: bytes) -> str:
    """
    Detects the most likely encoding of binary data using modern heuristics
    
    >>> detect_encoding(b'hello world')
    'utf-8'
    >>> detect_encoding(b'\\xff\\xfe\\x68\\x00\\x65\\x00')
    'utf-16'
    """

    if not data:
        return UNICODE_ENCODING

    # Check for BOM markers first
    if data.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    elif data.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    elif data.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    elif data.startswith(b'\xff\xfe\x00\x00'):
        return 'utf-32-le'
    elif data.startswith(b'\x00\x00\xfe\xff'):
        return 'utf-32-be'

    # Try UTF-8 first (most common)
    try:
        data.decode('utf-8', errors='strict')
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    # Try common encodings
    encodings = ['latin-1', 'cp1252', 'iso-8859-1', 'ascii']
    for encoding in encodings:
        try:
            data.decode(encoding, errors='strict')
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    # Fallback to UTF-8 with error handling
    return 'utf-8'


def safe_encode(value: Union[str, bytes], encoding: Optional[str] = None, errors: str = 'replace') -> bytes:
    """
    Safely encodes a string value to bytes with better error handling
    
    >>> safe_encode('hello world')
    b'hello world'
    >>> safe_encode('café', 'ascii', 'ignore')
    b'caf'
    """

    if value is None:
        return b''

    if isinstance(value, bytes):
        return value

    if not isinstance(value, str):
        value = str(value)

    encoding = encoding or conf.get("encoding") or UNICODE_ENCODING

    try:
        return value.encode(encoding, errors)
    except (LookupError, TypeError):
        # Fallback to UTF-8 if encoding is invalid
        return value.encode(UNICODE_ENCODING, errors)


def safe_decode(value: Union[str, bytes], encoding: Optional[str] = None, errors: str = 'replace') -> str:
    """
    Safely decodes bytes to string with automatic encoding detection
    
    >>> safe_decode(b'hello world')
    'hello world'
    >>> safe_decode('already string')
    'already string'
    """

    if value is None:
        return ''

    if isinstance(value, str):
        return value

    if not isinstance(value, bytes):
        return str(value)

    # Use provided encoding or detect it
    if encoding:
        try:
            return value.decode(encoding, errors)
        except (UnicodeDecodeError, LookupError):
            pass

    # Auto-detect encoding
    detected_encoding = detect_encoding(value)
    try:
        return value.decode(detected_encoding, errors)
    except UnicodeDecodeError:
        # Ultimate fallback
        return value.decode(UNICODE_ENCODING, errors='replace')


def normalize_encoding_name(encoding: str) -> str:
    """
    Normalizes encoding names to their canonical forms
    
    >>> normalize_encoding_name('utf8')
    'utf-8'
    >>> normalize_encoding_name('UTF-8')
    'utf-8'
    """

    if not encoding:
        return UNICODE_ENCODING

    # Normalize common variations
    encoding = encoding.lower().replace('_', '-')

    normalization_map = {
        'utf8': 'utf-8',
        'utf16': 'utf-16',
        'utf32': 'utf-32',
        'latin1': 'latin-1',
        'iso88591': 'iso-8859-1',
        'ascii': 'ascii',
        'cp1252': 'cp1252',
    }

    return normalization_map.get(encoding, encoding)


def ensure_text(value: Union[str, bytes, Any], encoding: Optional[str] = None) -> str:
    """
    Ensures the value is a text string, handling various input types
    
    >>> ensure_text(b'hello')
    'hello'
    >>> ensure_text(123)
    '123'
    >>> ensure_text(['a', 'b'])
    "['a', 'b']"
    """

    if value is None:
        return ''

    if isinstance(value, str):
        return value

    if isinstance(value, bytes):
        return safe_decode(value, encoding)

    # Handle other types
    return str(value)


def ensure_bytes(value: Union[str, bytes, Any], encoding: Optional[str] = None) -> bytes:
    """
    Ensures the value is bytes, handling various input types
    
    >>> ensure_bytes('hello')
    b'hello'
    >>> ensure_bytes(b'hello')
    b'hello'
    >>> ensure_bytes(123)
    b'123'
    """

    if value is None:
        return b''

    if isinstance(value, bytes):
        return value

    if isinstance(value, str):
        return safe_encode(value, encoding)

    # Handle other types
    return safe_encode(str(value), encoding)


def base64pickle(value):
    """
    Serializes (with pickle) and encodes to Base64 format supplied (binary) value

    >>> base64unpickle(base64pickle([1, 2, 3])) == [1, 2, 3]
    True
    """

    retVal = None

    try:
        retVal = encodeBase64(pickle.dumps(value, PICKLE_PROTOCOL), binary=False)
    except:
        warnMsg = "problem occurred while serializing "
        warnMsg += "instance of a type '%s'" % type(value)
        singleTimeWarnMessage(warnMsg)

        try:
            retVal = encodeBase64(pickle.dumps(value), binary=False)
        except:
            retVal = encodeBase64(pickle.dumps(str(value), PICKLE_PROTOCOL), binary=False)

    return retVal

def base64unpickle(value):
    """
    Decodes value from Base64 to plain format and deserializes (with pickle) its content

    >>> type(base64unpickle('gAJjX19idWlsdGluX18Kb2JqZWN0CnEBKYFxAi4=')) == object
    True
    """

    retVal = None

    try:
        retVal = pickle.loads(decodeBase64(value))
    except TypeError:
        retVal = pickle.loads(decodeBase64(bytes(value)))

    return retVal

def htmlUnescape(value):
    """
    Returns (basic conversion) HTML unescaped value

    >>> htmlUnescape('a&lt;b') == 'a<b'
    True
    """

    retVal = value

    if value and isinstance(value, (str, bytes)):
        replacements = (("&lt;", '<'), ("&gt;", '>'), ("&quot;", '"'), ("&nbsp;", ' '), ("&amp;", '&'), ("&apos;", "'"))
        for code, value in replacements:
            retVal = retVal.replace(code, value)

        try:
            retVal = re.sub(r"&#x([^ ;]+);", lambda match: chr(int(match.group(1), 16)), retVal)
        except (ValueError, OverflowError):
            pass

    return retVal

def singleTimeWarnMessage(message):  # Cross-referenced function
    sys.stdout.write(message)
    sys.stdout.write("\n")
    sys.stdout.flush()

def filterNone(values):  # Cross-referenced function
    return [_ for _ in values if _] if isinstance(values, collections.abc.Iterable) else values

def isListLike(value):  # Cross-referenced function
    return isinstance(value, (list, tuple, set, BigArray))

def shellExec(cmd):  # Cross-referenced function
    raise NotImplementedError

def jsonize(data):
    """
    Returns JSON serialized data

    >>> jsonize({'foo':'bar'})
    '{\\n    "foo": "bar"\\n}'
    """

    return json.dumps(data, sort_keys=False, indent=4)

def dejsonize(data):
    """
    Returns JSON deserialized data

    >>> dejsonize('{\\n    "foo": "bar"\\n}') == {u'foo': u'bar'}
    True
    """

    return json.loads(data)

def rot13(data):
    """
    Returns ROT13 encoded/decoded text

    >>> rot13('foobar was here!!')
    'sbbone jnf urer!!'
    >>> rot13('sbbone jnf urer!!')
    'foobar was here!!'
    """

    # Reference: https://stackoverflow.com/a/62662878
    retVal = ""
    alphabit = "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for char in data:
        retVal += alphabit[alphabit.index(char) + 13] if char in alphabit else char
    return retVal

def decodeHex(value, binary=True):
    """
    Returns a decoded representation of provided hexadecimal value

    >>> decodeHex("313233") == b"123"
    True
    >>> decodeHex("313233", binary=False) == u"123"
    True
    """

    retVal = value

    if isinstance(value, bytes):
        value = getText(value)

    if value.lower().startswith("0x"):
        value = value[2:]

    try:
        retVal = codecs.decode(value, "hex")
    except LookupError:
        retVal = binascii.unhexlify(value)

    if not binary:
        retVal = getText(retVal)

    return retVal

def encodeHex(value, binary=True):
    """
    Returns a encoded representation of provided string value

    >>> encodeHex(b"123") == b"313233"
    True
    >>> encodeHex("123", binary=False)
    '313233'
    >>> encodeHex(b"123"[0]) == b"31"
    True
    """

    if isinstance(value, int):
        value = chr(value)

    if isinstance(value, str):
        value = value.encode(UNICODE_ENCODING)

    try:
        retVal = codecs.encode(value, "hex")
    except LookupError:
        retVal = binascii.hexlify(value)

    if not binary:
        retVal = getText(retVal)

    return retVal

def decodeBase64(value, binary=True, encoding=None):
    """
    Returns a decoded representation of provided Base64 value

    >>> decodeBase64("MTIz") == b"123"
    True
    >>> decodeBase64("MTIz", binary=False)
    '123'
    >>> decodeBase64("A-B_CDE") == decodeBase64("A+B/CDE")
    True
    >>> decodeBase64(b"MTIzNA") == b"1234"
    True
    >>> decodeBase64("MTIzNA") == b"1234"
    True
    >>> decodeBase64("MTIzNA==") == b"1234"
    True
    """

    if value is None:
        return None

    padding = '='

    # Reference: https://stackoverflow.com/a/49459036
    if not value.endswith(padding):
        value += 3 * padding

    # Reference: https://en.wikipedia.org/wiki/Base64#URL_applications
    # Reference: https://perldoc.perl.org/MIME/Base64.html
    if isinstance(value, bytes):
        value = value.replace(b'-', b'+').replace(b'_', b'/')
    else:
        value = value.replace('-', '+').replace('_', '/')

    retVal = base64.b64decode(value)

    if not binary:
        retVal = getText(retVal, encoding)

    return retVal

def encodeBase64(value, binary=True, encoding=None, padding=True, safe=False):
    """
    Returns a decoded representation of provided Base64 value

    >>> encodeBase64(b"123") == b"MTIz"
    True
    >>> encodeBase64(u"1234", binary=False)
    'MTIzNA=='
    >>> encodeBase64(u"1234", binary=False, padding=False)
    'MTIzNA'
    >>> encodeBase64(decodeBase64("A-B_CDE"), binary=False, safe=True)
    'A-B_CDE'
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.encode(encoding or UNICODE_ENCODING)

    retVal = base64.b64encode(value)

    if not binary:
        retVal = getText(retVal, encoding)

    if safe:
        padding = False

        # Reference: https://en.wikipedia.org/wiki/Base64#URL_applications
        # Reference: https://perldoc.perl.org/MIME/Base64.html
        if isinstance(retVal, bytes):
            retVal = retVal.replace(b'+', b'-').replace(b'/', b'_')
        else:
            retVal = retVal.replace('+', '-').replace('/', '_')

    if not padding:
        retVal = retVal.rstrip('=')

    return retVal

def getBytes(value, encoding=None, errors="strict", unsafe=True):
    """
    Returns byte representation of provided Unicode value with modern error handling

    >>> getBytes(u"foo\\\\x01\\\\x83\\\\xffbar") == b"foo\\x01\\x83\\xffbar"
    True
    """

    if value is None:
        return b''

    # Use modern encoding approach
    encoding = normalize_encoding_name(encoding or conf.get("encoding") or UNICODE_ENCODING)

    if isinstance(value, str):
        if INVALID_UNICODE_PRIVATE_AREA and unsafe:
            # Handle private Unicode area characters
            for char in range(0xF0000, 0xF00FF + 1):
                if chr(char) in value:
                    value = value.replace(chr(char), f"{SAFE_HEX_MARKER}{char - 0xF0000:02x}")

        try:
            retVal = value.encode(encoding, errors)
        except (UnicodeError, LookupError):
            # Fallback with better error handling
            retVal = safe_encode(value, encoding, 'replace')

        if unsafe and SAFE_HEX_MARKER.encode() in retVal:
            # Restore hex-encoded characters
            retVal = re.sub(
                rf"{re.escape(SAFE_HEX_MARKER)}([0-9a-f]{{2}})".encode(),
                lambda m: bytes([int(m.group(1), 16)]),
                retVal
            )
    elif isinstance(value, bytes):
        retVal = value
    else:
        # Handle other types
        retVal = ensure_bytes(value, encoding)

    return retVal

def getOrds(value):
    """
    Returns ORD(...) representation of provided string value

    >>> getOrds(u'fo\\xf6bar')
    [102, 111, 246, 98, 97, 114]
    >>> getOrds(b"fo\\xc3\\xb6bar")
    [102, 111, 195, 182, 98, 97, 114]
    """

    return [_ if isinstance(_, int) else ord(_) for _ in value]

def getUnicode(value, encoding=None, noneToNull=False):
    """
    Returns the unicode representation of the supplied value with modern encoding detection

    >>> getUnicode('test') == u'test'
    True
    >>> getUnicode(1) == u'1'
    True
    >>> getUnicode(None) == 'None'
    True
    """

    # Time limit check
    if conf.get("timeLimit") and kb.get("startTime") and (time.time() - kb.startTime > conf.timeLimit):
        raise SystemExit

    if noneToNull and value is None:
        return NULL

    if isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        # Use modern encoding detection and fallback strategy
        if encoding:
            encoding = normalize_encoding_name(encoding)
            try:
                return value.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                pass

        # Enhanced encoding candidates with better heuristics
        detected_encoding = detect_encoding(value)
        candidates = [
            detected_encoding,
            kb.get("pageEncoding") if kb.get("originalPage") else None,
            conf.get("encoding"),
            UNICODE_ENCODING,
            sys.getfilesystemencoding(),
            'latin-1'  # Always succeeds as fallback
        ]

        # Filter None values and normalize
        candidates = [normalize_encoding_name(enc) for enc in candidates if enc]

        # Remove duplicates while preserving order
        seen = set()
        candidates = [x for x in candidates if not (x in seen or seen.add(x))]

        for candidate in candidates:
            try:
                return value.decode(candidate)
            except (UnicodeDecodeError, LookupError):
                continue

        # Ultimate fallback with error replacement
        return value.decode('latin-1', errors='replace')
    elif isListLike(value):
        return [getUnicode(item, encoding, noneToNull) for item in value]
    else:
        try:
            return str(value)
        except (UnicodeDecodeError, UnicodeEncodeError):
            return repr(value)

def getText(value, encoding=None):
    """
    Returns textual value of a given value with modern string handling

    >>> getText(b"foobar")
    'foobar'
    >>> isinstance(getText(u"fo\\u2299bar"), str)
    True
    """

    if isinstance(value, bytes):
        return safe_decode(value, encoding)
    elif isinstance(value, str):
        return value
    else:
        return ensure_text(value, encoding)

def stdoutEncode(value):
    """
    Returns binary representation of a given Unicode value safe for writing to stdout
    """

    value = value or ""

    if IS_WIN and IS_TTY and kb.get("codePage", -1) is None:
        output = shellExec("chcp")
        match = re.search(r": (\d{3,})", output or "")

        if match:
            try:
                candidate = "cp%s" % match.group(1)
                codecs.lookup(candidate)
            except LookupError:
                pass
            else:
                kb.codePage = candidate

        kb.codePage = kb.codePage or ""

    if isinstance(value, str):
        encoding = kb.get("codePage") or getattr(sys.stdout, "encoding", None) or UNICODE_ENCODING

        while True:
            try:
                retVal = value.encode(encoding)
                break
            except UnicodeEncodeError as ex:
                value = value[:ex.start] + "?" * (ex.end - ex.start) + value[ex.end:]

                warnMsg = "cannot properly display (some) Unicode characters "
                warnMsg += "inside your terminal ('%s') environment. All " % encoding
                warnMsg += "unhandled occurrences will result in "
                warnMsg += "replacement with '?' character. Please, find "
                warnMsg += "proper character representation inside "
                warnMsg += "corresponding output files"
                singleTimeWarnMessage(warnMsg)

        if sys.version_info[0] == 3:
            retVal = getUnicode(retVal, encoding)

    else:
        retVal = value

    return retVal

def getConsoleLength(value):
    """
    Returns console width of unicode values

    >>> getConsoleLength("abc")
    3
    >>> getConsoleLength(u"\\u957f\\u6c5j")
    4
    """

    if isinstance(value, str):
        retVal = sum((2 if ord(_) >= 0x3000 else 1) for _ in value)
    else:
        retVal = len(value)

    return retVal
