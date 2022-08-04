"""
This module provides some useful functions for working with
aioscrapy.http.Request objects
"""

from typing import Optional
from urllib.parse import urlunparse

from w3lib.http import headers_dict_to_raw

from aioscrapy.http import Request
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.python import to_bytes, to_unicode


def request_httprepr(request: Request) -> bytes:
    """Return the raw HTTP representation (as bytes) of the given request.
    This is provided only for reference since it's not the actual stream of
    bytes that will be send when performing the request (that's controlled
    by Twisted).
    """
    parsed = urlparse_cached(request)
    path = urlunparse(('', '', parsed.path or '/', parsed.params, parsed.query, ''))
    s = to_bytes(request.method) + b" " + to_bytes(path) + b" HTTP/1.1\r\n"
    s += b"Host: " + to_bytes(parsed.hostname or b'') + b"\r\n"
    if request.headers:
        s += headers_dict_to_raw({to_bytes(k): to_bytes(v) for k, v in request.headers.items()}) + b"\r\n"
    s += b"\r\n"
    s += to_bytes(request.body)
    return s


def referer_str(request: Request) -> Optional[str]:
    """ Return Referer HTTP header suitable for logging. """
    referrer = request.headers.get('Referer')
    if referrer is None:
        return referrer
    return to_unicode(referrer, errors='replace')
