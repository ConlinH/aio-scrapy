"""
Response utility functions for aioscrapy.
aioscrapy的响应实用函数。

This module provides utility functions for working with aioscrapy.http.Response objects.
It includes functions for extracting base URLs and meta refresh directives from HTML responses.
此模块提供了用于处理aioscrapy.http.Response对象的实用函数。
它包括从HTML响应中提取基本URL和元刷新指令的函数。
"""
from typing import Iterable, Optional, Tuple, Union
from weakref import WeakKeyDictionary

from w3lib import html

import aioscrapy
from aioscrapy.http.response import Response

# Cache for storing base URLs to avoid repeated parsing of the same response
# 缓存存储基本URL，以避免重复解析相同的响应
_baseurl_cache: "WeakKeyDictionary[Response, str]" = WeakKeyDictionary()


def get_base_url(response: "aioscrapy.http.response.TextResponse") -> str:
    """
    Extract the base URL from an HTML response.
    从HTML响应中提取基本URL。

    This function extracts the base URL from an HTML response by looking for
    the <base> tag in the HTML. If found, it returns the href attribute of the
    base tag, resolved against the response URL. If not found, it returns the
    response URL.
    此函数通过查找HTML中的<base>标签来从HTML响应中提取基本URL。
    如果找到，它返回base标签的href属性，相对于响应URL解析。
    如果未找到，它返回响应URL。

    The function uses a cache to avoid repeated parsing of the same response.
    Only the first 4KB of the response text are examined for performance reasons.
    该函数使用缓存来避免重复解析相同的响应。
    出于性能原因，只检查响应文本的前4KB。

    Args:
        response: The HTML response to extract the base URL from.
                 要从中提取基本URL的HTML响应。

    Returns:
        str: The base URL of the response, which could be either:
             响应的基本URL，可能是：
             - The href attribute of the <base> tag, resolved against the response URL
               <base>标签的href属性，相对于响应URL解析
             - The response URL if no <base> tag is found
               如果未找到<base>标签，则为响应URL
    """
    # Check if the base URL is already cached for this response
    # 检查此响应的基本URL是否已缓存
    if response not in _baseurl_cache:
        # Only examine the first 4KB of the response for performance
        # 出于性能考虑，只检查响应的前4KB
        text = response.text[0:4096]
        # Extract the base URL using w3lib.html
        # 使用w3lib.html提取基本URL
        _baseurl_cache[response] = html.get_base_url(text, response.url, response.encoding)
    # Return the cached base URL
    # 返回缓存的基本URL
    return _baseurl_cache[response]


# Cache for storing meta refresh directives to avoid repeated parsing of the same response
# 缓存存储元刷新指令，以避免重复解析相同的响应
# The cache stores either (None, None) if no meta refresh is found, or (seconds, url) if found
# 如果未找到元刷新，缓存存储(None, None)，如果找到，则存储(秒数, url)
_metaref_cache: "WeakKeyDictionary[Response, Union[Tuple[None, None], Tuple[float, str]]]" = WeakKeyDictionary()


def get_meta_refresh(
    response: "aioscrapy.http.response.TextResponse",
    ignore_tags: Optional[Iterable[str]] = ('script', 'noscript'),
) -> Union[Tuple[None, None], Tuple[float, str]]:
    """
    Extract the meta refresh directive from an HTML response.
    从HTML响应中提取元刷新指令。

    This function looks for the HTML meta refresh tag in the response and extracts
    the delay (in seconds) and the URL to redirect to. The meta refresh tag is
    typically used for automatic page redirection or refreshing.
    此函数在响应中查找HTML元刷新标签，并提取延迟（以秒为单位）和要重定向到的URL。
    元刷新标签通常用于自动页面重定向或刷新。

    Example of a meta refresh tag:
    元刷新标签的示例：
    <meta http-equiv="refresh" content="5; url=https://example.com">

    The function uses a cache to avoid repeated parsing of the same response.
    Only the first 4KB of the response text are examined for performance reasons.
    该函数使用缓存来避免重复解析相同的响应。
    出于性能原因，只检查响应文本的前4KB。

    Args:
        response: The HTML response to extract the meta refresh from.
                 要从中提取元刷新的HTML响应。
        ignore_tags: HTML tags to ignore when parsing. Default is ('script', 'noscript').
                    解析时要忽略的HTML标签。默认为('script', 'noscript')。

    Returns:
        A tuple containing:
        包含以下内容的元组：
        - If meta refresh is found: (delay_seconds, url)
          如果找到元刷新：(延迟秒数, url)
        - If no meta refresh is found: (None, None)
          如果未找到元刷新：(None, None)
    """
    # Check if the meta refresh is already cached for this response
    # 检查此响应的元刷新是否已缓存
    if response not in _metaref_cache:
        # Only examine the first 4KB of the response for performance
        # 出于性能考虑，只检查响应的前4KB
        text = response.text[0:4096]
        # Extract the meta refresh using w3lib.html
        # 使用w3lib.html提取元刷新
        _metaref_cache[response] = html.get_meta_refresh(
            text, response.url, response.encoding, ignore_tags=ignore_tags)
    # Return the cached meta refresh
    # 返回缓存的元刷新
    return _metaref_cache[response]
