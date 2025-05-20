"""
XML response implementation for aioscrapy.
aioscrapy的XML响应实现。

This module provides the XmlResponse class, which is a specialized TextResponse
for handling XML content. It inherits all functionality from TextResponse
but is specifically intended for XML responses, with support for XML encoding
declarations.
此模块提供了XmlResponse类，这是一个专门用于处理XML内容的TextResponse。
它继承了TextResponse的所有功能，但专门用于XML响应，支持XML编码声明。
"""

from aioscrapy.http.response.text import TextResponse


class XmlResponse(TextResponse):
    """
    A Response subclass specifically for XML responses.
    专门用于XML响应的Response子类。

    This class extends TextResponse to handle XML content. It inherits all the
    functionality of TextResponse, including:
    此类扩展了TextResponse以处理XML内容。它继承了TextResponse的所有功能，包括：

    - Automatic encoding detection (including from XML declarations)
      自动编码检测（包括从XML声明中）
    - Unicode conversion
      Unicode转换
    - CSS and XPath selectors (particularly useful for XML)
      CSS和XPath选择器（对XML特别有用）
    - Enhanced link following
      增强的链接跟踪

    The main purpose of this class is to provide a specific type for XML responses,
    which can be useful for type checking and middleware processing.
    此类的主要目的是为XML响应提供特定类型，这对类型检查和中间件处理很有用。

    Example:
        ```python
        def parse(self, response):
            if isinstance(response, XmlResponse):
                # Process XML response
                items = response.xpath('//item')
                for item in items:
                    yield {
                        'name': item.xpath('./name/text()').get(),
                        'value': item.xpath('./value/text()').get()
                    }
            else:
                # Handle other response types
                pass
        ```
    """
    pass
