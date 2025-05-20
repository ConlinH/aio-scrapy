
"""
HTTP Response implementation for aioscrapy.
aioscrapy的HTTP响应实现。

This module provides the Response class, which represents an HTTP response
received by the crawler. It handles response data, headers, cookies, and
provides methods for URL joining and following links.
此模块提供了Response类，表示爬虫接收到的HTTP响应。它处理响应数据、
头部、Cookie，并提供URL连接和跟踪链接的方法。
"""

from typing import Generator, Optional
from urllib.parse import urljoin

from aioscrapy.exceptions import NotSupported
from aioscrapy.http.request import Request
from aioscrapy.link import Link


class Response(object):

    def __init__(
            self,
            url: str,
            status: int = 200,
            headers: Optional[dict] = None,
            cookies: Optional[dict] = None,
            body: bytes = b"",
            flags: Optional[list] = None,
            request: Optional[Request] = None,
    ):
        """
        Initialize a Response object.
        初始化Response对象。

        Args:
            url: URL for this response. 此响应的URL。
            status: HTTP status code. HTTP状态码。
            headers: HTTP headers. HTTP头信息。
            cookies: Cookies from the response. 响应中的Cookie。
            body: Response body. 响应体。
            flags: Response flags. 响应标志。
            request: The Request object that generated this response. 生成此响应的Request对象。
        """
        self.headers = headers or {}
        self.status = int(status)
        self._set_body(body)
        self._set_url(url)
        self.request = request
        self.flags = [] if flags is None else list(flags)
        self.cookies = cookies or {}

    @property
    def cb_kwargs(self):
        """
        Get the callback keyword arguments from the request that generated this response.
        从生成此响应的请求中获取回调关键字参数。

        This property provides access to the cb_kwargs dictionary of the request
        that generated this response, allowing callback functions to access
        data passed from the request.
        此属性提供对生成此响应的请求的cb_kwargs字典的访问，
        允许回调函数访问从请求传递的数据。

        Returns:
            dict: The callback keyword arguments dictionary.
                 回调关键字参数字典。

        Raises:
            AttributeError: If this response is not tied to any request.
                           如果此响应未与任何请求关联。
        """
        try:
            return self.request.cb_kwargs
        except AttributeError:
            raise AttributeError(
                "Response.cb_kwargs not available, this response "
                "is not tied to any request"
            )

    @property
    def meta(self):
        """
        Get the metadata from the request that generated this response.
        从生成此响应的请求中获取元数据。

        This property provides access to the meta dictionary of the request
        that generated this response, allowing callback functions to access
        metadata passed from the request.
        此属性提供对生成此响应的请求的meta字典的访问，
        允许回调函数访问从请求传递的元数据。

        Returns:
            dict: The request metadata dictionary.
                 请求元数据字典。

        Raises:
            AttributeError: If this response is not tied to any request.
                           如果此响应未与任何请求关联。
        """
        try:
            return self.request.meta
        except AttributeError:
            raise AttributeError(
                "Response.meta not available, this response "
                "is not tied to any request"
            )

    def _get_url(self):
        """
        Get the response URL.
        获取响应URL。

        This is an internal method used by the url property.
        这是由url属性使用的内部方法。

        Returns:
            str: The response URL.
                响应URL。
        """
        return self._url

    def _set_url(self, url):
        """
        Set the response URL.
        设置响应URL。

        This method validates that the URL is a string.
        此方法验证URL是一个字符串。

        Args:
            url: The URL to set.
                要设置的URL。

        Raises:
            TypeError: If the URL is not a string.
                      如果URL不是字符串。
        """
        if isinstance(url, str):
            self._url = url
        else:
            raise TypeError(f'{type(self).__name__} url must be str, '
                            f'got {type(url).__name__}')

    # Property that uses the getter and setter methods
    # 使用getter和setter方法的属性
    url = property(_get_url, _set_url)

    def _get_body(self):
        """
        Get the response body.
        获取响应体。

        This is an internal method used by the body property.
        这是由body属性使用的内部方法。

        Returns:
            bytes: The response body.
                 响应体。
        """
        return self._body

    def _set_body(self, body):
        """
        Set the response body.
        设置响应体。

        This method validates that the body is bytes and converts None to an empty bytes object.
        此方法验证body是字节对象，并将None转换为空字节对象。

        Args:
            body: The body to set.
                 要设置的响应体。

        Raises:
            TypeError: If the body is not bytes.
                      如果body不是字节对象。
        """
        if body is None:
            self._body = b''
        elif not isinstance(body, bytes):
            raise TypeError(
                "Response body must be bytes. "
                "If you want to pass unicode body use TextResponse "
                "or HtmlResponse.")
        else:
            self._body = body

    # Property that uses the getter and setter methods
    # 使用getter和setter方法的属性
    body = property(_get_body, _set_body)

    def __str__(self):
        """
        Return a string representation of the response.
        返回响应的字符串表示。

        The string representation includes the HTTP status code and URL.
        字符串表示包括HTTP状态码和URL。

        Returns:
            str: A string representation of the response.
                响应的字符串表示。
        """
        return f"<{self.status} {self.url}>"

    # Use the same implementation for __repr__
    # 对__repr__使用相同的实现
    __repr__ = __str__

    def copy(self):
        """
        Return a copy of this Response.
        返回此Response的副本。

        Returns:
            A copy of this Response. 此Response的副本。
        """
        return self.replace()

    def replace(self, *args, **kwargs):
        """
        Create a new Response with the same attributes except for those given new values.
        创建一个新的Response，除了给定的新值外，其他属性与当前Response相同。

        Args:
            *args: Positional arguments for the new Response. 新Response的位置参数。
            **kwargs: Keyword arguments for the new Response. 新Response的关键字参数。

        Returns:
            A new Response object. 一个新的Response对象。
        """
        for x in [
            "url", "status", "headers", "body", "request", "flags"
        ]:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)

    def urljoin(self, url):
        """
        Join this Response's url with a possible relative url to form an absolute interpretation of the latter.
        将此Response的url与可能的相对url连接，形成后者的绝对解释。

        Args:
            url: The URL to join. 要连接的URL。

        Returns:
            The absolute URL. 绝对URL。
        """
        return urljoin(self.url, url)

    @property
    def text(self):
        """
        Get the response body as text.
        将响应体作为文本获取。

        This property is only implemented by subclasses of TextResponse.
        In the base Response class, it raises an AttributeError.
        此属性仅由TextResponse的子类实现。
        在基本Response类中，它会引发AttributeError。

        Returns:
            str: The response body as text (in subclasses).
                响应体作为文本（在子类中）。

        Raises:
            AttributeError: In the base Response class.
                           在基本Response类中。
        """
        raise AttributeError("Response content isn't text")

    def css(self, *a, **kw):
        """
        Apply the given CSS selector to this response's content.
        将给定的CSS选择器应用于此响应的内容。

        This method is only implemented by subclasses of TextResponse.
        In the base Response class, it raises a NotSupported exception.
        此方法仅由TextResponse的子类实现。
        在基本Response类中，它会引发NotSupported异常。

        Args:
            *a: Positional arguments for the CSS selector.
                CSS选择器的位置参数。
            **kw: Keyword arguments for the CSS selector.
                 CSS选择器的关键字参数。

        Raises:
            NotSupported: In the base Response class.
                         在基本Response类中。
        """
        raise NotSupported("Response content isn't text")

    def xpath(self, *a, **kw):
        """
        Apply the given XPath selector to this response's content.
        将给定的XPath选择器应用于此响应的内容。

        This method is only implemented by subclasses of TextResponse.
        In the base Response class, it raises a NotSupported exception.
        此方法仅由TextResponse的子类实现。
        在基本Response类中，它会引发NotSupported异常。

        Args:
            *a: Positional arguments for the XPath selector.
                XPath选择器的位置参数。
            **kw: Keyword arguments for the XPath selector.
                 XPath选择器的关键字参数。

        Raises:
            NotSupported: In the base Response class.
                         在基本Response类中。
        """
        raise NotSupported("Response content isn't text")

    def json(self, *a, **kw):
        """
        Parse this response's body as JSON.
        将此响应的正文解析为JSON。

        This method is only implemented by subclasses of TextResponse.
        In the base Response class, it raises a NotSupported exception.
        此方法仅由TextResponse的子类实现。
        在基本Response类中，它会引发NotSupported异常。

        Args:
            *a: Positional arguments for the JSON parser.
                JSON解析器的位置参数。
            **kw: Keyword arguments for the JSON parser.
                 JSON解析器的关键字参数。

        Raises:
            NotSupported: In the base Response class.
                         在基本Response类中。
        """
        raise NotSupported("Response content isn't text")

    def follow(self, url, callback=None, method='GET', headers=None, body=None,
               cookies=None, meta=None, encoding='utf-8', priority=0, dont_filter=False,
               fingerprint=None, errback=None, cb_kwargs=None, flags=None):
        # type: (...) -> Request
        """
        Return a Request instance to follow a link.
        返回一个Request实例以跟踪链接。

        This method creates a new Request to follow the given URL. The URL can be
        a relative URL, a Link object, or an absolute URL. If it's a relative URL,
        it will be joined with the current response's URL.
        此方法创建一个新的Request以跟踪给定的URL。URL可以是相对URL、Link对象或绝对URL。
        如果是相对URL，它将与当前响应的URL连接。

        Args:
            url: The URL to follow. Can be a string or a Link object.
                要跟踪的URL。可以是字符串或Link对象。
            callback: A function to be called with the response from the request.
                     使用请求的响应调用的函数。
            method: The HTTP method to use.
                   要使用的HTTP方法。
            headers: The headers to use for the request.
                    请求使用的头部。
            body: The body of the request.
                 请求的正文。
            cookies: The cookies to send with the request.
                    与请求一起发送的Cookie。
            meta: Extra data to pass to the request.
                 传递给请求的额外数据。
            encoding: The encoding to use for the request.
                     请求使用的编码。
            priority: The priority of the request.
                     请求的优先级。
            dont_filter: Whether to filter duplicate requests.
                        是否过滤重复请求。
            fingerprint: The fingerprint for the request.
                        请求的指纹。
            errback: A function to be called if the request fails.
                    如果请求失败时调用的函数。
            cb_kwargs: Additional keyword arguments to pass to the callback.
                      传递给回调的额外关键字参数。
            flags: Flags for the request.
                  请求的标志。

        Returns:
            Request: A new Request instance.
                    一个新的Request实例。
        """
        if isinstance(url, Link):
            url = url.url
        elif url is None:
            raise ValueError("url can't be None")
        url = self.urljoin(url)

        return Request(
            url=url,
            callback=callback,
            method=method,
            headers=headers,
            body=body,
            cookies=cookies,
            meta=meta,
            encoding=encoding,
            priority=priority,
            dont_filter=dont_filter,
            errback=errback,
            cb_kwargs=cb_kwargs,
            flags=flags,
            fingerprint=fingerprint
        )

    def follow_all(self, urls, callback=None, method='GET', headers=None, body=None,
                   cookies=None, meta=None, encoding='utf-8', priority=0,
                   dont_filter=False, errback=None, cb_kwargs=None, flags=None):
        # type: (...) -> Generator[Request, None, None]
        """
        Return an iterable of Request instances to follow all links in urls.
        返回一个Request实例的可迭代对象，以跟踪urls中的所有链接。

        This method creates multiple Requests to follow the given URLs. Each URL can be
        a relative URL, a Link object, or an absolute URL. If it's a relative URL,
        it will be joined with the current response's URL.
        此方法创建多个Request以跟踪给定的URL。每个URL可以是相对URL、Link对象或绝对URL。
        如果是相对URL，它将与当前响应的URL连接。

        Args:
            urls: An iterable of URLs to follow. Each can be a string or a Link object.
                 要跟踪的URL的可迭代对象。每个可以是字符串或Link对象。
            callback: A function to be called with the response from each request.
                     使用每个请求的响应调用的函数。
            method: The HTTP method to use.
                   要使用的HTTP方法。
            headers: The headers to use for the requests.
                    请求使用的头部。
            body: The body of the requests.
                 请求的正文。
            cookies: The cookies to send with the requests.
                    与请求一起发送的Cookie。
            meta: Extra data to pass to the requests.
                 传递给请求的额外数据。
            encoding: The encoding to use for the requests.
                     请求使用的编码。
            priority: The priority of the requests.
                     请求的优先级。
            dont_filter: Whether to filter duplicate requests.
                        是否过滤重复请求。
            errback: A function to be called if the requests fail.
                    如果请求失败时调用的函数。
            cb_kwargs: Additional keyword arguments to pass to the callback.
                      传递给回调的额外关键字参数。
            flags: Flags for the requests.
                  请求的标志。

        Returns:
            Generator[Request, None, None]: A generator of Request instances.
                                           Request实例的生成器。

        Raises:
            TypeError: If urls is not an iterable.
                      如果urls不是可迭代的。
        """
        if not hasattr(urls, '__iter__'):
            raise TypeError("'urls' argument must be an iterable")
        return (
            self.follow(
                url=url,
                callback=callback,
                method=method,
                headers=headers,
                body=body,
                cookies=cookies,
                meta=meta,
                encoding=encoding,
                priority=priority,
                dont_filter=dont_filter,
                errback=errback,
                cb_kwargs=cb_kwargs,
                flags=flags,
            )
            for url in urls
        )
