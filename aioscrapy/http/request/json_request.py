
"""
JSON request implementation for aioscrapy.
aioscrapy的JSON请求实现。

This module provides the JsonRequest class, which is a specialized Request
that handles JSON data, automatically setting appropriate headers and
serializing Python objects to JSON.
此模块提供了JsonRequest类，这是一个专门处理JSON数据的Request，
自动设置适当的头部并将Python对象序列化为JSON。
"""

import copy
import json
import warnings
from typing import Optional, Tuple

from aioscrapy.http.request import Request


class JsonRequest(Request):
    """
    A Request that handles JSON data.
    处理JSON数据的Request。

    This class extends the base Request to handle JSON data, automatically
    setting appropriate headers for JSON content and serializing Python
    objects to JSON format.
    此类扩展了基本Request以处理JSON数据，自动设置JSON内容的
    适当头部，并将Python对象序列化为JSON格式。
    """

    # Add dumps_kwargs to the list of attributes to be included in serialization
    # 将dumps_kwargs添加到要包含在序列化中的属性列表中
    attributes: Tuple[str, ...] = Request.attributes + ("dumps_kwargs",)

    def __init__(self, *args, dumps_kwargs: Optional[dict] = None, **kwargs) -> None:
        """
        Initialize a JsonRequest.
        初始化JsonRequest。

        This constructor extends the base Request constructor to handle JSON data.
        It accepts either a 'body' parameter with pre-serialized JSON or a 'data'
        parameter with a Python object to be serialized to JSON.
        此构造函数扩展了基本Request构造函数以处理JSON数据。
        它接受带有预序列化JSON的'body'参数或带有要序列化为JSON的Python对象的'data'参数。

        Args:
            *args: Positional arguments passed to the Request constructor.
                  传递给Request构造函数的位置参数。
            dumps_kwargs: Optional keyword arguments to pass to json.dumps().
                         可选的关键字参数，传递给json.dumps()。
            **kwargs: Keyword arguments passed to the Request constructor.
                     May include 'data' (a Python object to serialize to JSON)
                     or 'body' (pre-serialized JSON string).
                     传递给Request构造函数的关键字参数。
                     可能包括'data'（要序列化为JSON的Python对象）
                     或'body'（预序列化的JSON字符串）。
        """
        # Make a deep copy of dumps_kwargs to avoid modifying the original
        # 深拷贝dumps_kwargs以避免修改原始对象
        dumps_kwargs = copy.deepcopy(dumps_kwargs) if dumps_kwargs is not None else {}
        self._dumps_kwargs = dumps_kwargs

        # Check if body or data parameters were provided
        # 检查是否提供了body或data参数
        body_passed = kwargs.get('body', None) is not None
        data = kwargs.pop('data', None)
        data_passed = data is not None

        # Handle the case where both body and data are provided
        # 处理同时提供body和data的情况
        if body_passed and data_passed:
            warnings.warn('Both body and data passed. data will be ignored')

        # Handle the case where only data is provided
        # 处理只提供data的情况
        elif not body_passed and data_passed:
            # Serialize the data to JSON and set it as the body
            # 将数据序列化为JSON并将其设置为body
            kwargs['body'] = self._dumps(data)

            # Default to POST method if not specified
            # 如果未指定，则默认为POST方法
            if 'method' not in kwargs:
                kwargs['method'] = 'POST'

        # Initialize the base Request
        # 初始化基本Request
        super().__init__(*args, **kwargs)

        # Set default headers for JSON content
        # 设置JSON内容的默认头部
        self.headers.setdefault('Content-Type', 'application/json')
        self.headers.setdefault('Accept', 'application/json, text/javascript, */*; q=0.01')

    @property
    def dumps_kwargs(self) -> dict:
        """
        Get the keyword arguments used for JSON serialization.
        获取用于JSON序列化的关键字参数。

        These arguments are passed to json.dumps() when serializing data.
        这些参数在序列化数据时传递给json.dumps()。

        Returns:
            dict: The keyword arguments for json.dumps().
                 json.dumps()的关键字参数。
        """
        return self._dumps_kwargs

    def replace(self, *args, **kwargs) -> Request:
        """
        Create a new JsonRequest with the same attributes except for those given new values.
        创建一个新的JsonRequest，除了给定的新值外，其他属性与当前JsonRequest相同。

        This method extends the base Request.replace() method to handle the 'data'
        parameter, serializing it to JSON if provided.
        此方法扩展了基本Request.replace()方法以处理'data'参数，
        如果提供了该参数，则将其序列化为JSON。

        Args:
            *args: Positional arguments passed to the base replace() method.
                  传递给基本replace()方法的位置参数。
            **kwargs: Keyword arguments passed to the base replace() method.
                     May include 'data' (a Python object to serialize to JSON)
                     or 'body' (pre-serialized JSON string).
                     传递给基本replace()方法的关键字参数。
                     可能包括'data'（要序列化为JSON的Python对象）
                     或'body'（预序列化的JSON字符串）。

        Returns:
            Request: A new JsonRequest object.
                    一个新的JsonRequest对象。
        """
        # Check if body or data parameters were provided
        # 检查是否提供了body或data参数
        body_passed = kwargs.get('body', None) is not None
        data = kwargs.pop('data', None)
        data_passed = data is not None

        # Handle the case where both body and data are provided
        # 处理同时提供body和data的情况
        if body_passed and data_passed:
            warnings.warn('Both body and data passed. data will be ignored')

        # Handle the case where only data is provided
        # 处理只提供data的情况
        elif not body_passed and data_passed:
            # Serialize the data to JSON and set it as the body
            # 将数据序列化为JSON并将其设置为body
            kwargs['body'] = self._dumps(data)

        # Call the base replace() method
        # 调用基本replace()方法
        return super().replace(*args, **kwargs)

    def _dumps(self, data: dict) -> str:
        """
        Convert Python data to a JSON string.
        将Python数据转换为JSON字符串。

        This internal method serializes the given data to JSON using the
        json.dumps() function with the configured keyword arguments.
        此内部方法使用json.dumps()函数和配置的关键字参数将给定数据序列化为JSON。

        Args:
            data: The Python object to serialize to JSON.
                 要序列化为JSON的Python对象。

        Returns:
            str: The JSON string representation of the data.
                数据的JSON字符串表示。
        """
        return json.dumps(data, **self._dumps_kwargs)
