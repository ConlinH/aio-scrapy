
"""
Text response implementation for aioscrapy.
aioscrapy的文本响应实现。

This module provides the TextResponse class, which extends the base Response
to handle text content. It supports encoding detection, text extraction,
and provides methods for CSS and XPath selectors.
此模块提供了TextResponse类，它扩展了基本Response以处理文本内容。
它支持编码检测、文本提取，并提供CSS和XPath选择器的方法。
"""

import warnings
from contextlib import suppress
from typing import Generator
from urllib.parse import urljoin

import parsel
import ujson
from parsel import Selector
from w3lib.encoding import (html_body_declared_encoding, html_to_unicode,
                            http_content_type_encoding, resolve_encoding)
from w3lib.html import strip_html5_whitespace

from aioscrapy.exceptions import AioScrapyDeprecationWarning
from aioscrapy.http import Request
from aioscrapy.http.response import Response
from aioscrapy.utils.python import memoizemethod_noargs, to_unicode
from aioscrapy.utils.response import get_base_url

# Sentinel object to indicate that a value hasn't been cached yet
# 表示值尚未缓存的哨兵对象
_NONE = object()


class TextResponse(Response):
    """
    A Response subclass that adds support for text processing.
    添加文本处理支持的Response子类。

    This class extends the base Response to handle text content, with features for:
    此类扩展了基本Response以处理文本内容，具有以下功能：

    - Automatic encoding detection
      自动编码检测
    - Unicode conversion
      Unicode转换
    - CSS and XPath selectors
      CSS和XPath选择器
    - JSON parsing
      JSON解析
    - Enhanced link following
      增强的链接跟踪
    """

    # Default encoding to use if no encoding is specified or detected
    # 如果未指定或检测到编码，则使用的默认编码
    _DEFAULT_ENCODING = 'ascii'

    # Cache for decoded JSON content
    # 解码的JSON内容的缓存
    _cached_decoded_json = _NONE

    def __init__(self, *args, encoding=None, **kwargs):
        """
        Initialize a TextResponse.
        初始化TextResponse。

        Args:
            *args: Positional arguments passed to the Response constructor.
                  传递给Response构造函数的位置参数。
            encoding: The encoding of the response. If None, it will be auto-detected.
                     响应的编码。如果为None，将自动检测。
            **kwargs: Keyword arguments passed to the Response constructor.
                     传递给Response构造函数的关键字参数。
        """
        # The explicitly declared encoding
        # 明确声明的编码
        self._encoding = encoding

        # Cache for inferred body encoding
        # 推断的正文编码的缓存
        self._cached_benc = None

        # Cache for unicode body
        # Unicode正文的缓存
        self._cached_ubody = None

        # Cache for selector
        # 选择器的缓存
        self._cached_selector = None

        super().__init__(*args, **kwargs)

    def _set_url(self, url):
        """
        Set the response URL, ensuring it's properly encoded.
        设置响应URL，确保其正确编码。

        This method overrides the base Response._set_url to handle string URLs
        by converting them to unicode using the response's encoding.
        此方法重写了基本Response._set_url，通过使用响应的编码将字符串URL转换为unicode来处理它们。

        Args:
            url: The URL to set.
                要设置的URL。

        Raises:
            TypeError: If the URL is not a string (raised by the parent method).
                      如果URL不是字符串（由父方法引发）。
        """
        if isinstance(url, str):
            # Convert the URL to unicode using the response's encoding
            # 使用响应的编码将URL转换为unicode
            self._url = to_unicode(url, self.encoding)
        else:
            # Let the parent class handle non-string URLs
            # 让父类处理非字符串URL
            super()._set_url(url)

    def _set_body(self, body):
        """
        Set the response body, handling both bytes and string inputs.
        设置响应体，处理字节和字符串输入。

        This method overrides the base Response._set_body to handle string bodies
        by encoding them using the response's encoding.
        此方法重写了基本Response._set_body，通过使用响应的编码对字符串正文进行编码来处理它们。

        Args:
            body: The body to set, either as bytes or string.
                 要设置的正文，可以是字节或字符串。

        Raises:
            TypeError: If the body is a string but no encoding is specified.
                      如果正文是字符串但未指定编码。
        """
        # Initialize with empty bytes for encoding detection
        # 初始化为空字节以进行编码检测
        self._body = b''  # used by encoding detection

        if isinstance(body, str):
            # Handle string bodies by encoding them
            # 通过编码字符串正文来处理它们
            if self._encoding is None:
                raise TypeError('Cannot convert unicode body - '
                                f'{type(self).__name__} has no encoding')
            self._body = body.encode(self._encoding)
        else:
            # Let the parent class handle non-string bodies
            # 让父类处理非字符串正文
            super()._set_body(body)

    def replace(self, *args, **kwargs):
        """
        Create a new TextResponse with the same attributes except for those given new values.
        创建一个新的TextResponse，除了给定的新值外，其他属性与当前TextResponse相同。

        This method extends the base Response.replace() method to ensure that
        the encoding is preserved when creating a new TextResponse.
        此方法扩展了基本Response.replace()方法，以确保在创建新的TextResponse时保留编码。

        Args:
            *args: Positional arguments passed to the base replace() method.
                  传递给基本replace()方法的位置参数。
            **kwargs: Keyword arguments passed to the base replace() method.
                     传递给基本replace()方法的关键字参数。

        Returns:
            TextResponse: A new TextResponse object.
                         一个新的TextResponse对象。
        """
        # Ensure the encoding is preserved
        # 确保编码被保留
        kwargs.setdefault('encoding', self.encoding)
        return Response.replace(self, *args, **kwargs)

    @property
    def encoding(self):
        """
        Get the response encoding.
        获取响应编码。

        This property returns the encoding of the response, using a cascading approach:
        1. First, try to get the explicitly declared encoding
        2. If not available, try to infer the encoding from the body
        此属性返回响应的编码，使用级联方法：
        1. 首先，尝试获取明确声明的编码
        2. 如果不可用，尝试从正文推断编码

        Returns:
            str: The response encoding.
                响应编码。
        """
        return self._declared_encoding() or self._body_inferred_encoding()

    def _declared_encoding(self):
        """
        Get the explicitly declared encoding.
        获取明确声明的编码。

        This method tries to find the encoding from various sources, in order:
        1. The encoding specified in the constructor
        2. The encoding specified in the Content-Type header
        3. The encoding declared in the HTML/XML body
        此方法尝试从各种来源按顺序查找编码：
        1. 构造函数中指定的编码
        2. Content-Type头部中指定的编码
        3. HTML/XML正文中声明的编码

        Returns:
            str or None: The declared encoding, or None if not found.
                        声明的编码，如果未找到则为None。
        """
        return (
            self._encoding
            or self._headers_encoding()
            or self._body_declared_encoding()
        )

    def body_as_unicode(self):
        """
        Return the response body as unicode.
        将响应体作为unicode返回。

        This method is deprecated. Use the text property instead.
        此方法已弃用。请改用text属性。

        Returns:
            str: The response body as unicode.
                响应体作为unicode。
        """
        warnings.warn('Response.body_as_unicode() is deprecated, '
                      'please use Response.text instead.',
                      AioScrapyDeprecationWarning, stacklevel=2)
        return self.text

    def json(self):
        """
        Parse the response body as JSON.
        将响应体解析为JSON。

        This method deserializes the response body as a JSON document
        and returns the corresponding Python object. The result is cached
        for subsequent calls.
        此方法将响应体反序列化为JSON文档，并返回相应的Python对象。
        结果会被缓存以供后续调用。

        Returns:
            object: The deserialized JSON document.
                   反序列化的JSON文档。

        Raises:
            ValueError: If the body is not valid JSON.
                       如果正文不是有效的JSON。
        """
        # Use cached result if available
        # 如果可用，使用缓存的结果
        if self._cached_decoded_json is _NONE:
            self._cached_decoded_json = ujson.loads(self.text)
        return self._cached_decoded_json

    @property
    def text(self):
        """
        Get the response body as unicode text.
        将响应体作为unicode文本获取。

        This property converts the response body to unicode using the detected
        or specified encoding. The result is cached for subsequent access.
        此属性使用检测到的或指定的编码将响应体转换为unicode。
        结果会被缓存以供后续访问。

        Returns:
            str: The response body as unicode text.
                响应体作为unicode文本。
        """
        # Access self.encoding before _cached_ubody to make sure
        # _body_inferred_encoding is called
        # 在_cached_ubody之前访问self.encoding，以确保调用_body_inferred_encoding
        if self._cached_ubody is None:
            charset = f'charset={self.encoding}'
            self._cached_ubody = html_to_unicode(charset, self.body)[1]
        return self._cached_ubody

    def urljoin(self, url):
        """
        Join this Response's url with a possible relative url.
        将此Response的url与可能的相对url连接。

        This method extends the base Response.urljoin() method to use the base URL
        from the HTML document (if available) instead of the response URL.
        此方法扩展了基本Response.urljoin()方法，使用HTML文档中的基本URL
        （如果可用）而不是响应URL。

        Args:
            url: The URL to join. Can be a relative URL.
                要连接的URL。可以是相对URL。

        Returns:
            str: The absolute URL.
                绝对URL。
        """
        # Use get_base_url to extract the base URL from the HTML document
        # 使用get_base_url从HTML文档中提取基本URL
        return urljoin(get_base_url(self), url)

    @memoizemethod_noargs
    def _headers_encoding(self):
        """
        Get the encoding declared in the Content-Type header.
        获取Content-Type头部中声明的编码。

        This method extracts the charset parameter from the Content-Type header.
        The result is memoized for performance.
        此方法从Content-Type头部提取charset参数。
        结果会被记忆化以提高性能。

        Returns:
            str or None: The encoding declared in the header, or None if not found.
                        头部中声明的编码，如果未找到则为None。
        """
        content_type = self.headers.get('Content-Type', '')
        return http_content_type_encoding(to_unicode(content_type))

    def _body_inferred_encoding(self):
        """
        Infer the encoding from the response body.
        从响应体推断编码。

        This method tries to detect the encoding from the response body
        using various heuristics. The result is cached for subsequent calls.
        此方法尝试使用各种启发式方法从响应体检测编码。
        结果会被缓存以供后续调用。

        Returns:
            str: The inferred encoding.
                推断的编码。
        """
        if self._cached_benc is None:
            content_type = to_unicode(self.headers.get('Content-Type', ''))
            benc, ubody = html_to_unicode(content_type, self.body,
                                          auto_detect_fun=self._auto_detect_fun,
                                          default_encoding=self._DEFAULT_ENCODING)
            self._cached_benc = benc
            self._cached_ubody = ubody
        return self._cached_benc

    def _auto_detect_fun(self, text):
        """
        Auto-detect the encoding of the given text.
        自动检测给定文本的编码。

        This method tries to decode the text using a sequence of common encodings
        and returns the first one that succeeds.
        此方法尝试使用一系列常见编码解码文本，并返回第一个成功的编码。

        Args:
            text: The text to detect the encoding for.
                 要检测编码的文本。

        Returns:
            str or None: The detected encoding, or None if none of the encodings work.
                        检测到的编码，如果没有编码有效则为None。
        """
        # Try a sequence of common encodings
        # 尝试一系列常见编码
        for enc in (self._DEFAULT_ENCODING, 'utf-8', 'cp1252'):
            try:
                text.decode(enc)
            except UnicodeError:
                continue
            return resolve_encoding(enc)
        return None

    @memoizemethod_noargs
    def _body_declared_encoding(self):
        """
        Get the encoding declared in the HTML/XML body.
        获取HTML/XML正文中声明的编码。

        This method extracts the encoding from meta tags or XML declarations
        in the response body. The result is memoized for performance.
        此方法从响应体中的meta标签或XML声明中提取编码。
        结果会被记忆化以提高性能。

        Returns:
            str or None: The encoding declared in the body, or None if not found.
                        正文中声明的编码，如果未找到则为None。
        """
        return html_body_declared_encoding(self.body)

    @property
    def selector(self):
        """
        Get a Selector for this response.
        获取此响应的选择器。

        This property creates a parsel.Selector instance for the response text,
        which allows for XPath and CSS queries. The result is cached for
        subsequent access.
        此属性为响应文本创建一个parsel.Selector实例，允许XPath和CSS查询。
        结果会被缓存以供后续访问。

        Returns:
            parsel.Selector: A Selector instance for this response.
                            此响应的Selector实例。
        """
        if self._cached_selector is None:
            self._cached_selector = Selector(self.text)
        return self._cached_selector

    def xpath(self, query, **kwargs):
        """
        Apply the given XPath selector to this response's content.
        将给定的XPath选择器应用于此响应的内容。

        This is a shortcut method that creates a selector and applies the XPath query.
        此方法是一个快捷方法，创建选择器并应用XPath查询。

        Args:
            query: The XPath query string.
                  XPath查询字符串。
            **kwargs: Additional keyword arguments passed to the selector's xpath method.
                     传递给选择器的xpath方法的额外关键字参数。

        Returns:
            parsel.SelectorList: The result of the XPath query.
                                XPath查询的结果。
        """
        return self.selector.xpath(query, **kwargs)

    def css(self, query):
        """
        Apply the given CSS selector to this response's content.
        将给定的CSS选择器应用于此响应的内容。

        This is a shortcut method that creates a selector and applies the CSS query.
        此方法是一个快捷方法，创建选择器并应用CSS查询。

        Args:
            query: The CSS query string.
                  CSS查询字符串。

        Returns:
            parsel.SelectorList: The result of the CSS query.
                                CSS查询的结果。
        """
        return self.selector.css(query)

    def follow(self, url, callback=None, method='GET', headers=None, body=None,
               cookies=None, meta=None, encoding=None, priority=0, dont_filter=False,
               fingerprint=None, errback=None, cb_kwargs=None, flags=None):
        # type: (...) -> Request
        """
        Return a Request instance to follow a link.
        返回一个Request实例以跟踪链接。

        This method extends the base Response.follow() method to handle additional
        URL types, including Selector objects for HTML elements and attributes.
        此方法扩展了基本Response.follow()方法，以处理额外的URL类型，
        包括HTML元素和属性的Selector对象。

        The URL can be:
        URL可以是：

        * An absolute URL (string)
          绝对URL（字符串）
        * A relative URL (string)
          相对URL（字符串）
        * A Link object
          Link对象
        * A Selector object for a <link> or <a> element
          <link>或<a>元素的Selector对象
        * An attribute Selector (not SelectorList), e.g., from css('a::attr(href)')[0]
          属性Selector（非SelectorList），例如，来自css('a::attr(href)')[0]

        Args:
            url: The URL to follow. Can be any of the types described above.
                要跟踪的URL。可以是上述任何类型。
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
            encoding: The encoding to use for the request. Defaults to this response's encoding.
                     请求使用的编码。默认为此响应的编码。
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

        Raises:
            ValueError: If the URL is a SelectorList or cannot be extracted from a Selector.
                       如果URL是SelectorList或无法从Selector中提取。
        """
        if isinstance(url, parsel.Selector):
            url = _url_from_selector(url)
        elif isinstance(url, parsel.SelectorList):
            raise ValueError("SelectorList is not supported")
        encoding = self.encoding if encoding is None else encoding
        return super().follow(
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

    def follow_all(self, urls=None, callback=None, method='GET', headers=None, body=None,
                   cookies=None, meta=None, encoding=None, priority=0,
                   dont_filter=False, errback=None, cb_kwargs=None, flags=None,
                   css=None, xpath=None):
        # type: (...) -> Generator[Request, None, None]
        """
        Return a generator of Request instances to follow all links in urls.
        返回一个Request实例的生成器，以跟踪urls中的所有链接。

        This method extends the base Response.follow_all() method to handle additional
        URL types and to support direct extraction of links using CSS or XPath selectors.
        此方法扩展了基本Response.follow_all()方法，以处理额外的URL类型，
        并支持使用CSS或XPath选择器直接提取链接。

        The URLs can be provided in several ways:
        URLs可以通过几种方式提供：

        1. As a list in the 'urls' parameter, where each element can be:
           作为'urls'参数中的列表，其中每个元素可以是：
           * An absolute URL (string)
             绝对URL（字符串）
           * A relative URL (string)
             相对URL（字符串）
           * A Link object
             Link对象
           * A Selector object for a <link> or <a> element
             <link>或<a>元素的Selector对象
           * An attribute Selector (not SelectorList)
             属性Selector（非SelectorList）

        2. By providing a CSS selector in the 'css' parameter
           通过在'css'参数中提供CSS选择器

        3. By providing an XPath selector in the 'xpath' parameter
           通过在'xpath'参数中提供XPath选择器

        Note: Only one of 'urls', 'css', or 'xpath' should be provided.
        注意：只应提供'urls'、'css'或'xpath'中的一个。

        Args:
            urls: An iterable of URLs to follow. Each can be any of the types described above.
                 要跟踪的URL的可迭代对象。每个可以是上述任何类型。
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
            encoding: The encoding to use for the requests. Defaults to this response's encoding.
                     请求使用的编码。默认为此响应的编码。
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
            css: A CSS selector to extract links from this response.
                 从此响应中提取链接的CSS选择器。
            xpath: An XPath selector to extract links from this response.
                  从此响应中提取链接的XPath选择器。

        Returns:
            Generator[Request, None, None]: A generator of Request instances.
                                           Request实例的生成器。

        Raises:
            ValueError: If more than one of 'urls', 'css', or 'xpath' is provided.
                       如果提供了'urls'、'css'或'xpath'中的多个。
        """
        arguments = [x for x in (urls, css, xpath) if x is not None]
        if len(arguments) != 1:
            raise ValueError(
                "Please supply exactly one of the following arguments: urls, css, xpath"
            )
        if not urls:
            if css:
                urls = self.css(css)
            if xpath:
                urls = self.xpath(xpath)
        if isinstance(urls, parsel.SelectorList):
            selectors = urls
            urls = []
            for sel in selectors:
                with suppress(_InvalidSelector):
                    urls.append(_url_from_selector(sel))
        return super().follow_all(
            urls=urls,
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


class _InvalidSelector(ValueError):
    """
    Raised when a URL cannot be obtained from a Selector.
    当无法从Selector获取URL时引发。

    This exception is used internally by the _url_from_selector function
    to indicate that a Selector object cannot be converted to a URL.
    此异常由_url_from_selector函数内部使用，
    表示无法将Selector对象转换为URL。
    """


def _url_from_selector(sel):
    # type: (parsel.Selector) -> str
    """
    Extract a URL from a Selector object.
    从Selector对象中提取URL。

    This function extracts a URL from different types of Selector objects:
    此函数从不同类型的Selector对象中提取URL：

    1. If the selector root is a string (e.g., from ::attr(href)), it returns that string
       如果选择器根是字符串（例如，来自::attr(href)），则返回该字符串
    2. If the selector is for an <a> or <link> element, it returns the href attribute
       如果选择器是<a>或<link>元素，则返回href属性

    Args:
        sel: The Selector object to extract a URL from.
             要从中提取URL的Selector对象。

    Returns:
        str: The extracted URL with whitespace stripped.
             提取的URL，已去除空白。

    Raises:
        _InvalidSelector: If the URL cannot be extracted from the Selector.
                         如果无法从Selector中提取URL。
    """
    if isinstance(sel.root, str):
        # For attribute selectors (e.g., ::attr(href) result)
        # 对于属性选择器（例如，::attr(href)结果）
        return strip_html5_whitespace(sel.root)

    if not hasattr(sel.root, 'tag'):
        # For selectors that don't represent HTML elements
        # 对于不表示HTML元素的选择器
        raise _InvalidSelector(f"Unsupported selector: {sel}")

    if sel.root.tag not in ('a', 'link'):
        # Only <a> and <link> elements are supported
        # 只支持<a>和<link>元素
        raise _InvalidSelector("Only <a> and <link> elements are supported; "
                               f"got <{sel.root.tag}>")

    href = sel.root.get('href')
    if href is None:
        # The element has no href attribute
        # 元素没有href属性
        raise _InvalidSelector(f"<{sel.root.tag}> element has no href attribute: {sel}")

    # Return the href with whitespace stripped
    # 返回去除空白的href
    return strip_html5_whitespace(href)
