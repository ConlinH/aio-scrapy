
"""
Form request implementation for aioscrapy.
aioscrapy的表单请求实现。

This module provides the FormRequest class, which is a specialized Request
that handles HTML form submission, both GET and POST methods.
此模块提供了FormRequest类，这是一个专门处理HTML表单提交的Request，
支持GET和POST方法。
"""

from typing import List, Optional, Tuple, Union
from urllib.parse import urlencode

from aioscrapy.http.request import Request
from aioscrapy.utils.python import to_bytes, is_listlike

# Type definition for form data, which can be a dictionary or a list of key-value tuples
# 表单数据的类型定义，可以是字典或键值元组列表
FormdataType = Optional[Union[dict, List[Tuple[str, str]]]]


class FormRequest(Request):
    """
    A Request that submits HTML form data.
    提交HTML表单数据的Request。

    This class extends the base Request to handle form submissions,
    automatically setting the appropriate method, headers, and
    encoding the form data either in the URL (for GET requests)
    or in the body (for POST requests).
    此类扩展了基本Request以处理表单提交，自动设置适当的方法、
    头部，并将表单数据编码到URL中（对于GET请求）或请求体中
    （对于POST请求）。
    """

    # Valid HTTP methods for form submission
    # 表单提交的有效HTTP方法
    valid_form_methods = ['GET', 'POST']

    def __init__(self, *args, formdata: FormdataType = None, **kwargs) -> None:
        """
        Initialize a FormRequest.
        初始化FormRequest。

        This constructor extends the base Request constructor to handle form data.
        If form data is provided and no method is specified, it defaults to POST.
        此构造函数扩展了基本Request构造函数以处理表单数据。
        如果提供了表单数据且未指定方法，则默认为POST。

        Args:
            *args: Positional arguments passed to the Request constructor.
                  传递给Request构造函数的位置参数。
            formdata: Form data to submit, either as a dict or a list of (name, value) tuples.
                     要提交的表单数据，可以是字典或(名称, 值)元组的列表。
            **kwargs: Keyword arguments passed to the Request constructor.
                     传递给Request构造函数的关键字参数。
        """
        # Default to POST method if form data is provided and no method is specified
        # 如果提供了表单数据且未指定方法，则默认为POST方法
        if formdata and kwargs.get('method') is None:
            kwargs['method'] = 'POST'

        # Initialize the base Request
        # 初始化基本Request
        super().__init__(*args, **kwargs)

        # Process form data if provided
        # 如果提供了表单数据，则处理它
        if formdata:
            # Convert dict to items() iterator if necessary
            # 如果需要，将字典转换为items()迭代器
            items = formdata.items() if isinstance(formdata, dict) else formdata

            # URL-encode the form data
            # URL编码表单数据
            form_query: str = _urlencode(items, self.encoding)

            if self.method == 'POST':
                # For POST requests, set the Content-Type header and put form data in the body
                # 对于POST请求，设置Content-Type头部并将表单数据放入请求体
                self.headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                self._set_body(form_query)
            else:
                # For GET requests, append form data to the URL
                # 对于GET请求，将表单数据附加到URL
                self._set_url(self.url + ('&' if '?' in self.url else '?') + form_query)


def _urlencode(seq, enc):
    """
    URL-encode a sequence of form data.
    URL编码表单数据序列。

    This internal function handles the encoding of form data for submission,
    converting keys and values to bytes using the specified encoding and
    properly handling list-like values.
    此内部函数处理表单数据的编码以便提交，使用指定的编码将键和值转换为字节，
    并正确处理类似列表的值。

    Args:
        seq: A sequence of (name, value) pairs to encode.
             要编码的(名称, 值)对序列。
        enc: The encoding to use for converting strings to bytes.
             用于将字符串转换为字节的编码。

    Returns:
        str: The URL-encoded form data string.
             URL编码的表单数据字符串。
    """
    # Convert each key-value pair to bytes and handle list-like values
    # 将每个键值对转换为字节并处理类似列表的值
    values = [(to_bytes(k, enc), to_bytes(v, enc))
              for k, vs in seq
              for v in (vs if is_listlike(vs) else [vs])]

    # Use urllib's urlencode with doseq=1 to properly handle sequences
    # 使用urllib的urlencode，doseq=1以正确处理序列
    return urlencode(values, doseq=1)
