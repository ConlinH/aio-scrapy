"""
Request utility functions for aioscrapy.
aioscrapy的请求实用函数。

This module provides utility functions for working with aioscrapy.http.Request objects.
It includes functions for converting requests to raw HTTP representations, extracting
referrer information, and creating Request objects from dictionaries.
此模块提供了用于处理aioscrapy.http.Request对象的实用函数。
它包括将请求转换为原始HTTP表示、提取引用者信息以及从字典创建Request对象的函数。
"""

from typing import Optional
from urllib.parse import urlunparse

from w3lib.http import headers_dict_to_raw

from aioscrapy import Spider, Request
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.misc import load_object
from aioscrapy.utils.python import to_bytes, to_unicode


def request_httprepr(request: Request) -> bytes:
    """
    Return the raw HTTP representation of a request as bytes.
    以字节形式返回请求的原始HTTP表示。

    This function converts a Request object to its raw HTTP representation,
    including the request line, headers, and body. This is useful for debugging
    and logging purposes.
    此函数将Request对象转换为其原始HTTP表示，包括请求行、头部和正文。
    这对于调试和日志记录目的很有用。

    Note:
        This is provided only for reference since it's not the actual stream of
        bytes that will be sent when performing the request (that's controlled
        by the HTTP client implementation).
        这仅供参考，因为它不是执行请求时将发送的实际字节流
        （那由HTTP客户端实现控制）。

    Args:
        request: The Request object to convert.
                要转换的Request对象。

    Returns:
        bytes: The raw HTTP representation of the request.
               请求的原始HTTP表示。

    Example:
        >>> request = Request('http://example.com', method='POST',
        ...                   headers={'Content-Type': 'application/json'},
        ...                   body='{"key": "value"}')
        >>> print(request_httprepr(request).decode())
        POST / HTTP/1.1
        Host: example.com
        Content-Type: application/json

        {"key": "value"}
    """
    # Parse the URL
    # 解析URL
    parsed = urlparse_cached(request)

    # Construct the path including params and query
    # 构造包含参数和查询的路径
    path = urlunparse(('', '', parsed.path or '/', parsed.params, parsed.query, ''))

    # Start with the request line
    # 从请求行开始
    s = to_bytes(request.method) + b" " + to_bytes(path) + b" HTTP/1.1\r\n"

    # Add the Host header
    # 添加Host头部
    s += b"Host: " + to_bytes(parsed.hostname or b'') + b"\r\n"

    # Add other headers if present
    # 如果存在，添加其他头部
    if request.headers:
        s += headers_dict_to_raw({to_bytes(k): to_bytes(v) for k, v in request.headers.items()}) + b"\r\n"

    # Add the empty line that separates headers from body
    # 添加分隔头部和正文的空行
    s += b"\r\n"

    # Add the body
    # 添加正文
    s += to_bytes(request.body)

    return s


def referer_str(request: Request) -> Optional[str]:
    """
    Return the Referer HTTP header in a format suitable for logging.
    以适合日志记录的格式返回Referer HTTP头。

    This function extracts the 'Referer' header from a request and converts it
    to a unicode string, replacing any invalid characters. This is useful for
    logging purposes to avoid encoding errors.
    此函数从请求中提取'Referer'头并将其转换为unicode字符串，
    替换任何无效字符。这对于日志记录很有用，可以避免编码错误。

    Args:
        request: The Request object to extract the Referer from.
                要提取Referer的Request对象。

    Returns:
        Optional[str]: The Referer header as a unicode string, or None if the
                      header is not present.
                      作为unicode字符串的Referer头，如果头不存在则为None。
    """
    # Get the Referer header from the request
    # 从请求中获取Referer头
    referrer = request.headers.get('Referer')

    # If there's no Referer header, return None
    # 如果没有Referer头，返回None
    if referrer is None:
        return referrer

    # Convert the Referer to unicode, replacing any invalid characters
    # 将Referer转换为unicode，替换任何无效字符
    return to_unicode(referrer, errors='replace')


async def request_from_dict(d: dict, *, spider: Optional[Spider] = None) -> Request:
    """
    Create a Request object from a dictionary.
    从字典创建Request对象。

    This function converts a dictionary representation of a request into an actual
    Request object. It's useful for deserializing requests, for example when
    loading them from a queue or a file.
    此函数将请求的字典表示转换为实际的Request对象。
    它对于反序列化请求很有用，例如从队列或文件加载请求时。

    If a spider is provided, the function will:
    1. First call the spider's request_from_dict method to allow custom processing
    2. Try to resolve callback and errback strings to actual methods on the spider

    如果提供了爬虫，该函数将：
    1. 首先调用爬虫的request_from_dict方法以允许自定义处理
    2. 尝试将callback和errback字符串解析为爬虫上的实际方法

    Args:
        d: Dictionary containing the request attributes.
           包含请求属性的字典。
        spider: Optional spider instance to resolve callbacks and errbacks.
               可选的爬虫实例，用于解析回调和错误回调。

    Returns:
        Request: A Request object (or subclass) with the attributes from the dictionary.
                具有字典中属性的Request对象（或子类）。

    Raises:
        ValueError: If a callback or errback name cannot be resolved to a method.
                   如果回调或错误回调名称无法解析为方法。
    """
    # Allow the spider to customize the dictionary
    # 允许爬虫自定义字典
    if spider:
        d = await spider.request_from_dict(d) or d

    # If the spider already returned a Request object, return it directly
    # 如果爬虫已经返回了一个Request对象，直接返回它
    if isinstance(d, Request):
        return d

    # Determine the request class to use (default is Request)
    # 确定要使用的请求类（默认为Request）
    request_cls = load_object(d["_class"]) if "_class" in d else Request

    # Filter the dictionary to only include valid attributes for the request class
    # 过滤字典，只包含请求类的有效属性
    kwargs = {key: value for key, value in d.items() if key in request_cls.attributes}

    # Resolve callback string to actual method if spider is provided
    # 如果提供了爬虫，将回调字符串解析为实际方法
    if d.get("callback") and spider:
        kwargs["callback"] = _get_method(spider, d["callback"])

    # Resolve errback string to actual method if spider is provided
    # 如果提供了爬虫，将错误回调字符串解析为实际方法
    if d.get("errback") and spider:
        kwargs["errback"] = _get_method(spider, d["errback"])

    # Create and return the request object
    # 创建并返回请求对象
    return request_cls(**kwargs)


def _get_method(obj, name):
    """
    Get a method from an object by name.
    通过名称从对象获取方法。

    This is a helper function for request_from_dict that resolves method names
    to actual method objects. It's used to convert callback and errback strings
    to callable methods on a spider.
    这是request_from_dict的辅助函数，用于将方法名称解析为实际的方法对象。
    它用于将回调和错误回调字符串转换为爬虫上的可调用方法。

    Args:
        obj: The object to get the method from (typically a spider).
             要从中获取方法的对象（通常是爬虫）。
        name: The name of the method to get.
              要获取的方法的名称。

    Returns:
        callable: The method object.
                 方法对象。

    Raises:
        ValueError: If the method is not found on the object.
                   如果在对象上找不到该方法。
    """
    # Ensure the name is a string
    # 确保名称是字符串
    name = str(name)

    # Try to get the method from the object
    # 尝试从对象获取方法
    try:
        return getattr(obj, name)
    except AttributeError:
        # Raise a more informative error if the method is not found
        # 如果找不到该方法，引发更多信息的错误
        raise ValueError(f"Method {name!r} not found in: {obj}")
