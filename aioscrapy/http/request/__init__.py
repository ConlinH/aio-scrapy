"""
This module implements the Request class which is used to represent HTTP
requests in Aioscrapy.

See documentation in docs/topics/request-response.rst
"""
import hashlib
import inspect
import json
from typing import Callable, List, Optional, Tuple, Type, TypeVar

from w3lib.url import canonicalize_url
from w3lib.url import safe_url_string

import aioscrapy
from aioscrapy.http.headers import Headers
from aioscrapy.utils.curl import curl_to_request_kwargs
from aioscrapy.utils.python import to_unicode
from aioscrapy.utils.url import escape_ajax

RequestTypeVar = TypeVar("RequestTypeVar", bound="Request")


class Request(object):
    attributes: Tuple[str, ...] = (
        "url", "callback", "method", "headers", "body",
        "cookies", "meta", "encoding", "priority",
        "dont_filter", "errback", "flags", "cb_kwargs",
        "fingerprint", "use_proxy"
    )

    def __init__(
            self,
            url: str,
            callback: Optional[Callable] = None,
            method: str = 'GET',
            headers: Optional[dict] = None,
            body: Optional[str] = None,
            cookies: Optional[dict] = None,
            meta: Optional[dict] = None,
            encoding: str = 'utf-8',
            priority: int = 0,
            dont_filter: bool = False,
            errback: Optional[Callable] = None,
            flags: Optional[List[str]] = None,
            cb_kwargs: Optional[Callable] = None,
            fingerprint: Optional[str] = None,
            use_proxy: bool = True,
    ):

        self._encoding = encoding
        self.method = str(method).upper()
        self._set_url(url)
        self._set_body(body)
        assert isinstance(priority, int), f"Request priority not an integer: {priority!r}"
        self.priority = priority

        self.callback = callback
        self.errback = errback

        self.cookies = cookies or {}
        self.headers = Headers(headers or {})
        self.dont_filter = dont_filter
        self._fingerprint = fingerprint
        self.use_proxy = use_proxy

        self._meta = dict(meta) if meta else None
        self._cb_kwargs = dict(cb_kwargs) if cb_kwargs else None
        self.flags = [] if flags is None else list(flags)

    @property
    def cb_kwargs(self) -> dict:
        if self._cb_kwargs is None:
            self._cb_kwargs = {}
        return self._cb_kwargs

    @property
    def meta(self) -> dict:
        if self._meta is None:
            self._meta = {}
        return self._meta

    def _get_url(self) -> str:
        return self._url

    def _set_url(self, url: str) -> None:
        if not isinstance(url, str):
            raise TypeError(f'Request url must be str or unicode, got {type(url).__name__}')

        s = safe_url_string(url, self.encoding)
        self._url = escape_ajax(s)

        if (
                '://' not in self._url
                and not self._url.startswith('about:')
                and not self._url.startswith('data:')
        ):
            raise ValueError(f'Missing scheme in request url: {self._url}')

    url = property(_get_url, _set_url)

    def _get_body(self) -> str:
        return self._body

    def _set_body(self, body: str) -> None:
        self._body = '' if body is None else body

    body = property(_get_body, _set_body)

    def _set_fingerprint(self, fingerprint: str) -> None:
        self._fingerprint = fingerprint

    def _get_fingerprint(self) -> str:
        if self._fingerprint is None and not self.dont_filter:
            self._fingerprint = self.make_fingerprint()
        return self._fingerprint

    fingerprint = property(_get_fingerprint, _set_fingerprint)

    @property
    def encoding(self) -> str:
        return self._encoding

    def __str__(self) -> str:
        return f"<{self.method} {self.url}>"

    __repr__ = __str__

    def copy(self) -> "Request":
        """Return a copy of this Request"""
        return self.replace()

    def replace(self, *args, **kwargs) -> "Request":
        """Create a new Request with the same attributes except for those given new values."""
        for x in self.attributes:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)

    @classmethod
    def from_curl(
            cls: Type[RequestTypeVar], curl_command: str, ignore_unknown_options: bool = True, **kwargs
    ) -> RequestTypeVar:
        """Create a Request object from a string containing a `cURL"""
        request_kwargs = curl_to_request_kwargs(curl_command, ignore_unknown_options)
        request_kwargs.update(kwargs)
        return cls(**request_kwargs)

    def make_fingerprint(
            self,
            keep_fragments: bool = False,
    ) -> str:
        """ make the request fingerprint. """
        return hashlib.sha1(
            json.dumps({
                'method': to_unicode(self.method),
                'url': canonicalize_url(self.url, keep_fragments=keep_fragments),
                'body': self.body,
            }, sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self, *, spider: Optional["aioscrapy.Spider"] = None) -> dict:
        """Return a dictionary containing the Request's data.

        Use :func:`~scrapy.utils.request.request_from_dict` to convert back into a :class:`~scrapy.Request` object.

        If a spider is given, this method will try to find out the name of the spider methods used as callback
        and errback and include them in the output dict, raising an exception if they cannot be found.
        """
        d = {
            "url": self.url,  # urls are safe (safe_string_url)
            "callback": _find_method(spider, self.callback) if callable(self.callback) else self.callback,
            "errback": _find_method(spider, self.errback) if callable(self.errback) else self.errback,
            "headers": dict(self.headers),
        }
        if self._fingerprint:
            d['fingerprint'] = self._fingerprint

        for attr in self.attributes:
            if attr != 'fingerprint':
                d.setdefault(attr, getattr(self, attr))
        if type(self) is not Request:
            d["_class"] = self.__module__ + '.' + self.__class__.__name__
        return d


def _find_method(obj, func):
    """Helper function for Request.to_dict"""
    # Only instance methods contain ``__func__``
    if obj and hasattr(func, '__func__'):
        members = inspect.getmembers(obj, predicate=inspect.ismethod)
        for name, obj_func in members:
            # We need to use __func__ to access the original function object because instance
            # method objects are generated each time attribute is retrieved from instance.
            #
            # Reference: The standard type hierarchy
            # https://docs.python.org/3/reference/datamodel.html
            if obj_func.__func__ is func.__func__:
                return name
    raise ValueError(f"Function {func} is not an instance method in: {obj}")
