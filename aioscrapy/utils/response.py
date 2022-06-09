"""
This module provides some useful functions for working with
scrapy.http.Response objects
"""
from typing import Iterable, Optional, Tuple, Union
from weakref import WeakKeyDictionary

from w3lib import html

import aioscrapy
from aioscrapy.http.response import Response

_baseurl_cache: "WeakKeyDictionary[Response, str]" = WeakKeyDictionary()


def get_base_url(response: "aioscrapy.http.response.TextResponse") -> str:
    """Return the base url of the given response, joined with the response url"""
    if response not in _baseurl_cache:
        text = response.text[0:4096]
        _baseurl_cache[response] = html.get_base_url(text, response.url, response.encoding)
    return _baseurl_cache[response]


_metaref_cache: "WeakKeyDictionary[Response, Union[Tuple[None, None], Tuple[float, str]]]" = WeakKeyDictionary()


def get_meta_refresh(
    response: "aioscrapy.http.response.TextResponse",
    ignore_tags: Optional[Iterable[str]] = ('script', 'noscript'),
) -> Union[Tuple[None, None], Tuple[float, str]]:
    """Parse the http-equiv refrsh parameter from the given response"""
    if response not in _metaref_cache:
        text = response.text[0:4096]
        _metaref_cache[response] = html.get_meta_refresh(
            text, response.url, response.encoding, ignore_tags=ignore_tags)
    return _metaref_cache[response]


