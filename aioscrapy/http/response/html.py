
"""
HTML response implementation for aioscrapy.
aioscrapy的HTML响应实现。

This module provides the HtmlResponse class, which is a specialized TextResponse
for handling HTML content. It inherits all functionality from TextResponse
but is specifically intended for HTML responses.
此模块提供了HtmlResponse类，这是一个专门用于处理HTML内容的TextResponse。
它继承了TextResponse的所有功能，但专门用于HTML响应。
"""

from aioscrapy.http.response.text import TextResponse


class HtmlResponse(TextResponse):
    """
    A Response subclass specifically for HTML responses.
    专门用于HTML响应的Response子类。

    This class extends TextResponse to handle HTML content. It inherits all the
    functionality of TextResponse, including:
    此类扩展了TextResponse以处理HTML内容。它继承了TextResponse的所有功能，包括：

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

    The main purpose of this class is to provide a specific type for HTML responses,
    which can be useful for type checking and middleware processing.
    此类的主要目的是为HTML响应提供特定类型，这对类型检查和中间件处理很有用。

    Example:
        ```python
        def parse(self, response):
            if isinstance(response, HtmlResponse):
                # Process HTML response
                title = response.css('title::text').get()
            else:
                # Handle other response types
                pass
        ```
    """
    pass
