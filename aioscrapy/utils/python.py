"""
This module contains essential stuff that should've come with Python itself ;)
"""
import errno
import gc
import inspect
import re
import sys
import warnings
import weakref
from functools import partial, wraps

from aioscrapy.exceptions import AioScrapyDeprecationWarning
from aioscrapy.utils.decorators import deprecated


def is_listlike(x):
    """
    >>> is_listlike("foo")
    False
    >>> is_listlike(5)
    False
    >>> is_listlike(b"foo")
    False
    >>> is_listlike([b"foo"])
    True
    >>> is_listlike((b"foo",))
    True
    >>> is_listlike({})
    True
    >>> is_listlike(set())
    True
    >>> is_listlike((x for x in range(3)))
    True
    >>> is_listlike(range(5))
    True
    """
    return hasattr(x, "__iter__") and not isinstance(x, (str, bytes))


def to_unicode(text, encoding=None, errors='strict'):
    """Return the unicode representation of a bytes object ``text``. If
    ``text`` is already an unicode object, return it as-is."""
    if isinstance(text, str):
        return text
    if not isinstance(text, (bytes, str)):
        raise TypeError('to_unicode must receive a bytes or str '
                        f'object, got {type(text).__name__}')
    if encoding is None:
        encoding = 'utf-8'
    return text.decode(encoding, errors)


def to_bytes(text, encoding=None, errors='strict'):
    """Return the binary representation of ``text``. If ``text``
    is already a bytes object, return it as-is."""
    if isinstance(text, bytes):
        return text
    if not isinstance(text, str):
        raise TypeError('to_bytes must receive a str or bytes '
                        f'object, got {type(text).__name__}')
    if encoding is None:
        encoding = 'utf-8'
    return text.encode(encoding, errors)


@deprecated('to_unicode')
def to_native_str(text, encoding=None, errors='strict'):
    """ Return str representation of ``text``. """
    return to_unicode(text, encoding, errors)


def re_rsearch(pattern, text, chunk_size=1024):
    """
    This function does a reverse search in a text using a regular expression
    given in the attribute 'pattern'.
    Since the re module does not provide this functionality, we have to find for
    the expression into chunks of text extracted from the end (for the sake of efficiency).
    At first, a chunk of 'chunk_size' kilobytes is extracted from the end, and searched for
    the pattern. If the pattern is not found, another chunk is extracted, and another
    search is performed.
    This process continues until a match is found, or until the whole file is read.
    In case the pattern wasn't found, None is returned, otherwise it returns a tuple containing
    the start position of the match, and the ending (regarding the entire text).
    """

    def _chunk_iter():
        offset = len(text)
        while True:
            offset -= (chunk_size * 1024)
            if offset <= 0:
                break
            yield (text[offset:], offset)
        yield (text, 0)

    if isinstance(pattern, str):
        pattern = re.compile(pattern)

    for chunk, offset in _chunk_iter():
        matches = [match for match in pattern.finditer(chunk)]
        if matches:
            start, end = matches[-1].span()
            return offset + start, offset + end
    return None


def memoizemethod_noargs(method):
    """Decorator to cache the result of a method (without arguments) using a
    weak reference to its object
    """
    cache = weakref.WeakKeyDictionary()

    @wraps(method)
    def new_method(self, *args, **kwargs):
        if self not in cache:
            cache[self] = method(self, *args, **kwargs)
        return cache[self]

    return new_method


def without_none_values(iterable):
    """Return a copy of ``iterable`` with all ``None`` entries removed.

    If ``iterable`` is a mapping, return a dictionary where all pairs that have
    value ``None`` have been removed.
    """
    try:
        return {k: v for k, v in iterable.items() if v is not None}
    except AttributeError:
        return type(iterable)((v for v in iterable if v is not None))


def global_object_name(obj):
    """
    Return full name of a global object.

    >>> from aioscrapy import Request
    >>> global_object_name(Request)
    'aioscrapy.http.request.Request'
    """
    return f"{obj.__module__}.{obj.__name__}"


if hasattr(sys, "pypy_version_info"):
    def garbage_collect():
        # Collecting weakreferences can take two collections on PyPy.
        gc.collect()
        gc.collect()
else:
    def garbage_collect():
        gc.collect()

