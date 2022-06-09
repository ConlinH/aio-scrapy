"""
This module implements the XmlResponse class which adds encoding
discovering through XML encoding declarations to the TextResponse class.

See documentation in docs/topics/request-response.rst
"""

from aioscrapy.http.response.text import TextResponse


class XmlResponse(TextResponse):
    pass
