"""
HTTP object utility functions for aioscrapy.
aioscrapy的HTTP对象实用函数。

This module provides utility functions for working with HTTP objects (Request, Response)
in aioscrapy. It includes functions for parsing and caching URL information to improve
performance when the same URLs are processed multiple times.
此模块提供了用于处理aioscrapy中HTTP对象（Request, Response）的实用函数。
它包括用于解析和缓存URL信息的函数，以提高多次处理相同URL时的性能。
"""

from typing import Union
from urllib.parse import urlparse, ParseResult
from weakref import WeakKeyDictionary

from aioscrapy.http import Request, Response


# Cache for storing parsed URLs to avoid repeated parsing of the same URL
# Uses WeakKeyDictionary so entries are automatically removed when the Request/Response is garbage collected
# 用于存储已解析URL的缓存，以避免重复解析相同的URL
# 使用WeakKeyDictionary，因此当Request/Response被垃圾回收时，条目会自动删除
_urlparse_cache: "WeakKeyDictionary[Union[Request, Response], ParseResult]" = WeakKeyDictionary()


def urlparse_cached(request_or_response: Union[Request, Response]) -> ParseResult:
    """
    Parse the URL of a Request or Response object with caching.
    解析Request或Response对象的URL，并进行缓存。

    This function parses the URL of the given Request or Response object using
    urllib.parse.urlparse and caches the result. If the same object is passed
    again, the cached result is returned instead of re-parsing the URL.
    此函数使用urllib.parse.urlparse解析给定Request或Response对象的URL，
    并缓存结果。如果再次传递相同的对象，则返回缓存的结果，而不是重新解析URL。

    The caching mechanism uses a WeakKeyDictionary, so the cache entries are
    automatically removed when the Request or Response objects are garbage collected.
    This prevents memory leaks while still providing performance benefits.
    缓存机制使用WeakKeyDictionary，因此当Request或Response对象被垃圾回收时，
    缓存条目会自动删除。这可以防止内存泄漏，同时仍然提供性能优势。

    Args:
        request_or_response: A Request or Response object whose URL will be parsed.
                            将解析其URL的Request或Response对象。

    Returns:
        ParseResult: The parsed URL components (scheme, netloc, path, params,
                    query, fragment).
                    解析的URL组件（scheme, netloc, path, params, query, fragment）。

    Example:
        >>> request = Request('https://example.com/path?query=value')
        >>> parsed = urlparse_cached(request)
        >>> parsed.netloc
        'example.com'
        >>> parsed.path
        '/path'
        >>> parsed.query
        'query=value'
    """
    # Check if this object's URL has already been parsed and cached
    # 检查此对象的URL是否已被解析和缓存
    if request_or_response not in _urlparse_cache:
        # If not in cache, parse the URL and store the result
        # 如果不在缓存中，解析URL并存储结果
        _urlparse_cache[request_or_response] = urlparse(request_or_response.url)

    # Return the cached parse result
    # 返回缓存的解析结果
    return _urlparse_cache[request_or_response]
