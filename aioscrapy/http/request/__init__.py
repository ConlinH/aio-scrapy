
"""
HTTP Request implementation for aioscrapy.
aioscrapy的HTTP请求实现。

This module provides the Request class, which represents an HTTP request to be sent by the crawler.
It handles URL normalization, fingerprinting, serialization, and other request-related functionality.
此模块提供了Request类，表示由爬虫发送的HTTP请求。
它处理URL规范化、指纹生成、序列化和其他与请求相关的功能。
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

# Type variable for Request class to use in class methods
# 用于在类方法中使用的Request类的类型变量
RequestTypeVar = TypeVar("RequestTypeVar", bound="Request")


class Request(object):
    attributes: Tuple[str, ...] = (
        "url", "callback", "method", "headers", "body",
        "cookies", "meta", "encoding", "priority",
        "dont_filter", "errback", "flags", "cb_kwargs",
        "use_proxy"
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
        """
        Initialize a Request object.
        初始化Request对象。

        Args:
            url: URL for the request. 请求的URL。
            callback: Function to call when the response is received. 接收到响应时调用的函数。
            method: HTTP method. HTTP方法。
            headers: HTTP headers. HTTP头信息。
            body: Request body. 请求体。
            cookies: Cookies to send with the request. 随请求发送的Cookie。
            meta: Additional metadata. 额外的元数据。
            encoding: Encoding for the URL and body. URL和请求体的编码。
            priority: Request priority. 请求优先级。
            dont_filter: Whether to filter this request through the scheduler's dupefilter. 是否通过调度器的去重过滤器过滤此请求。
            errback: Function to call if an error occurs during processing. 处理过程中发生错误时调用的函数。
            flags: Request flags. 请求标志。
            cb_kwargs: Additional keyword arguments to pass to the callback. 传递给回调函数的额外关键字参数。
            fingerprint: Request fingerprint. 请求指纹。
            use_proxy: Whether to use a proxy for this request. 是否为此请求使用代理。
        """
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
        self.use_proxy = use_proxy

        self._meta = dict(meta) if meta else {}
        if fingerprint is not None:
            self._set_fingerprint(fingerprint)
        self._cb_kwargs = dict(cb_kwargs) if cb_kwargs else None
        self.flags = [] if flags is None else list(flags)

    @property
    def cb_kwargs(self) -> dict:
        """
        Get the callback keyword arguments dictionary.
        获取回调关键字参数字典。

        This property ensures that the callback keyword arguments dictionary
        is always initialized, creating an empty dictionary if needed.
        此属性确保回调关键字参数字典始终被初始化，如果需要则创建一个空字典。

        Returns:
            dict: The callback keyword arguments dictionary.
                 回调关键字参数字典。
        """
        if self._cb_kwargs is None:
            self._cb_kwargs = {}
        return self._cb_kwargs

    @property
    def meta(self) -> dict:
        """
        Get the request metadata dictionary.
        获取请求元数据字典。

        This property ensures that the metadata dictionary is always initialized,
        creating an empty dictionary if needed. The metadata dictionary is used
        to store arbitrary data associated with the request.
        此属性确保元数据字典始终被初始化，如果需要则创建一个空字典。
        元数据字典用于存储与请求相关的任意数据。

        Returns:
            dict: The request metadata dictionary.
                 请求元数据字典。
        """
        if self._meta is None:
            self._meta = {}
        return self._meta

    def _get_url(self) -> str:
        """
        Get the request URL.
        获取请求URL。

        This is an internal method used by the url property.
        这是由url属性使用的内部方法。

        Returns:
            str: The request URL.
                请求URL。
        """
        return self._url

    def _set_url(self, url: str) -> None:
        """
        Set the request URL.
        设置请求URL。

        This method normalizes the URL by:
        此方法通过以下方式规范化URL：
        1. Converting it to a safe string using the request's encoding
           使用请求的编码将其转换为安全字符串
        2. Escaping AJAX-specific characters
           转义AJAX特定字符
        3. Validating that the URL has a scheme
           验证URL具有协议方案

        Args:
            url: The URL to set.
                要设置的URL。

        Raises:
            TypeError: If the URL is not a string.
                      如果URL不是字符串。
            ValueError: If the URL does not have a scheme.
                       如果URL没有协议方案。
        """
        if not isinstance(url, str):
            raise TypeError(f'Request url must be str or unicode, got {type(url).__name__}')

        # Normalize the URL
        # 规范化URL
        s = safe_url_string(url, self.encoding)
        self._url = escape_ajax(s)

        # Validate that the URL has a scheme
        # 验证URL具有协议方案
        if (
                '://' not in self._url
                and not self._url.startswith('about:')
                and not self._url.startswith('data:')
        ):
            raise ValueError(f'Missing scheme in request url: {self._url}')

    # Property that uses the getter and setter methods
    # 使用getter和setter方法的属性
    url = property(_get_url, _set_url)

    def _get_body(self) -> str:
        """
        Get the request body.
        获取请求体。

        This is an internal method used by the body property.
        这是由body属性使用的内部方法。

        Returns:
            str: The request body.
                请求体。
        """
        return self._body

    def _set_body(self, body: str) -> None:
        """
        Set the request body.
        设置请求体。

        This method sets the request body, converting None to an empty string.
        此方法设置请求体，将None转换为空字符串。

        Args:
            body: The body to set.
                 要设置的请求体。
        """
        self._body = '' if body is None else body

    # Property that uses the getter and setter methods
    # 使用getter和setter方法的属性
    body = property(_get_body, _set_body)

    def _set_fingerprint(self, fingerprint: str) -> None:
        """
        Set the request fingerprint.
        设置请求指纹。

        This is an internal method used by the fingerprint property.
        The fingerprint is stored in the request's metadata.
        这是由fingerprint属性使用的内部方法。
        指纹存储在请求的元数据中。

        Args:
            fingerprint: The fingerprint to set.
                        要设置的指纹。
        """
        self._meta['_fingerprint'] = fingerprint

    def _get_fingerprint(self) -> str:
        """
        Get the request fingerprint.
        获取请求指纹。

        This is an internal method used by the fingerprint property.
        If the fingerprint doesn't exist, it's generated using make_fingerprint().
        这是由fingerprint属性使用的内部方法。
        如果指纹不存在，则使用make_fingerprint()生成。

        Returns:
            str: The request fingerprint.
                请求指纹。
        """
        if not self._meta.get('_fingerprint'):
            self._meta['_fingerprint'] = self.make_fingerprint()
        return self._meta.get('_fingerprint')

    # Property that uses the getter and setter methods
    # 使用getter和setter方法的属性
    fingerprint = property(_get_fingerprint, _set_fingerprint)

    @property
    def encoding(self) -> str:
        """
        Get the request encoding.
        获取请求编码。

        This encoding is used for URL and body encoding.
        此编码用于URL和请求体编码。

        Returns:
            str: The request encoding.
                请求编码。
        """
        return self._encoding

    def __str__(self) -> str:
        """
        Return a string representation of the request.
        返回请求的字符串表示。

        The string representation includes the HTTP method and URL.
        字符串表示包括HTTP方法和URL。

        Returns:
            str: A string representation of the request.
                请求的字符串表示。
        """
        return f"<{self.method} {self.url}>"

    # Use the same implementation for __repr__
    # 对__repr__使用相同的实现
    __repr__ = __str__

    def copy(self) -> "Request":
        """
        Return a copy of this Request.
        返回此Request的副本。

        Returns:
            A copy of this Request. 此Request的副本。
        """
        return self.replace()

    def replace(self, *args, **kwargs) -> "Request":
        """
        Create a new Request with the same attributes except for those given new values.
        创建一个新的Request，除了给定的新值外，其他属性与当前Request相同。

        Args:
            *args: Positional arguments for the new Request. 新Request的位置参数。
            **kwargs: Keyword arguments for the new Request. 新Request的关键字参数。

        Returns:
            A new Request object. 一个新的Request对象。
        """
        for x in self.attributes:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)

    @classmethod
    def from_curl(
            cls: Type[RequestTypeVar], curl_command: str, ignore_unknown_options: bool = True, **kwargs
    ) -> RequestTypeVar:
        """
        Create a Request object from a string containing a cURL command.
        从包含cURL命令的字符串创建Request对象。

        Args:
            curl_command: The cURL command. cURL命令。
            ignore_unknown_options: Whether to ignore unknown cURL options. 是否忽略未知的cURL选项。
            **kwargs: Additional keyword arguments for the Request. Request的额外关键字参数。

        Returns:
            A Request object. Request对象。
        """
        request_kwargs = curl_to_request_kwargs(curl_command, ignore_unknown_options)
        request_kwargs.update(kwargs)
        return cls(**request_kwargs)

    def make_fingerprint(
            self,
            keep_fragments: bool = False,
    ) -> str:
        """
        Make the request fingerprint.
        生成请求指纹。

        The fingerprint is a hash of the request's method, URL, and body.
        指纹是请求的方法、URL和请求体的哈希值。

        Args:
            keep_fragments: Whether to keep URL fragments in the fingerprint. 是否在指纹中保留URL片段。

        Returns:
            The request fingerprint. 请求指纹。
        """
        return hashlib.sha1(
            json.dumps({
                'method': to_unicode(self.method),
                'url': canonicalize_url(self.url, keep_fragments=keep_fragments),
                'body': self.body,
            }, sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self, *, spider: Optional["aioscrapy.Spider"] = None) -> dict:
        """
        Return a dictionary containing the Request's data.
        返回包含Request数据的字典。

        Use request_from_dict() to convert back into a Request object.
        使用request_from_dict()将其转换回Request对象。

        If a spider is given, this method will try to find out the name of the spider methods used as callback
        and errback and include them in the output dict, raising an exception if they cannot be found.
        如果提供了爬虫，此方法将尝试找出用作回调和错误回调的爬虫方法的名称，并将它们包含在输出字典中，如果找不到则引发异常。

        Args:
            spider: The spider instance. 爬虫实例。

        Returns:
            A dictionary containing the Request's data. 包含Request数据的字典。
        """
        d = {
            "url": self.url,  # urls are safe (safe_string_url)
            "callback": _find_method(spider, self.callback) if callable(self.callback) else self.callback,
            "errback": _find_method(spider, self.errback) if callable(self.errback) else self.errback,
            "headers": dict(self.headers),
        }

        for attr in self.attributes:
            d.setdefault(attr, getattr(self, attr))
        if type(self) is not Request:
            d["_class"] = self.__module__ + '.' + self.__class__.__name__
        return d


def _find_method(obj, func):
    """
    Find the name of a method in an object.
    在对象中查找方法的名称。

    This is a helper function for Request.to_dict() that finds the name of a method
    in an object by comparing the underlying function objects.
    这是Request.to_dict()的辅助函数，通过比较底层函数对象在对象中查找方法的名称。

    Args:
        obj: The object to search in.
             要搜索的对象。
        func: The method to find.
              要查找的方法。

    Returns:
        str: The name of the method.
             方法的名称。

    Raises:
        ValueError: If the function is not an instance method in the object.
                   如果函数不是对象中的实例方法。
    """
    # Only instance methods contain ``__func__``
    # 只有实例方法包含``__func__``
    if obj and hasattr(func, '__func__'):
        # Get all methods of the object
        # 获取对象的所有方法
        members = inspect.getmembers(obj, predicate=inspect.ismethod)
        for name, obj_func in members:
            # We need to use __func__ to access the original function object because instance
            # method objects are generated each time attribute is retrieved from instance.
            # 我们需要使用__func__来访问原始函数对象，因为实例方法对象在每次从实例检索属性时都会生成。
            #
            # Reference: The standard type hierarchy
            # 参考：标准类型层次结构
            # https://docs.python.org/3/reference/datamodel.html
            if obj_func.__func__ is func.__func__:
                return name
    # If we get here, the function was not found
    # 如果我们到达这里，则未找到函数
    raise ValueError(f"Function {func} is not an instance method in: {obj}")
