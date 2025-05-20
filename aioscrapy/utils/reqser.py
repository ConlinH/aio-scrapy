"""
Request serialization utilities for aioscrapy.
aioscrapy的请求序列化实用工具。

This module provides helper functions for serializing and deserializing Request objects.
These functions are particularly useful for storing requests in queues, databases,
or transmitting them between different processes or systems.
此模块提供了用于序列化和反序列化Request对象的辅助函数。
这些函数对于在队列、数据库中存储请求或在不同进程或系统之间传输请求特别有用。
"""
from typing import Optional

import aioscrapy
from aioscrapy.utils.request import request_from_dict as _from_dict


def request_to_dict(request: "aioscrapy.Request", spider: Optional["aioscrapy.Spider"] = None) -> dict:
    """
    Convert a Request object to a dictionary representation.
    将Request对象转换为字典表示。

    This function serializes a Request object into a dictionary that can be easily
    stored or transmitted. The dictionary contains all the necessary information
    to reconstruct the Request object later using request_from_dict().
    此函数将Request对象序列化为可以轻松存储或传输的字典。
    该字典包含稍后使用request_from_dict()重建Request对象所需的所有信息。

    Args:
        request: The Request object to serialize.
                要序列化的Request对象。
        spider: Optional Spider instance that may be used to customize the
               serialization process. Some Request subclasses may use the spider
               to properly serialize their attributes.
               可选的Spider实例，可用于自定义序列化过程。
               某些Request子类可能使用spider来正确序列化其属性。

    Returns:
        dict: A dictionary representation of the Request object.
              Request对象的字典表示。

    Example:
        >>> request = Request('http://example.com', callback='parse_item')
        >>> request_dict = request_to_dict(request, spider)
        >>> # The dictionary can be stored or transmitted
        >>> new_request = await request_from_dict(request_dict, spider)
    """
    # Delegate to the Request object's to_dict method
    # 委托给Request对象的to_dict方法
    return request.to_dict(spider=spider)


async def request_from_dict(d: dict, spider: Optional["aioscrapy.Spider"] = None) -> "aioscrapy.Request":
    """
    Convert a dictionary representation back to a Request object.
    将字典表示转换回Request对象。

    This function deserializes a dictionary (previously created by request_to_dict)
    back into a Request object. It reconstructs all the attributes and properties
    of the original Request, including callback and errback methods if a spider
    is provided.
    此函数将（先前由request_to_dict创建的）字典反序列化回Request对象。
    它重建原始Request的所有属性和属性，如果提供了spider，
    还包括回调和错误回调方法。

    Args:
        d: The dictionary representation of a Request object.
           Request对象的字典表示。
        spider: Optional Spider instance that may be used to resolve callback
               and errback method names to actual methods on the spider.
               可选的Spider实例，可用于将回调和错误回调方法名称
               解析为spider上的实际方法。

    Returns:
        aioscrapy.Request: A reconstructed Request object.
                          重建的Request对象。

    Example:
        >>> request_dict = {
        ...     'url': 'http://example.com',
        ...     'callback': 'parse_item',
        ...     'method': 'GET'
        ... }
        >>> request = await request_from_dict(request_dict, spider)
        >>> request.url
        'http://example.com'
    """
    # Delegate to the imported _from_dict function from aioscrapy.utils.request
    # 委托给从aioscrapy.utils.request导入的_from_dict函数
    return await _from_dict(d, spider=spider)
