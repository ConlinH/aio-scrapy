"""
Serialization utilities for AioScrapy.
AioScrapy的序列化实用工具。

This module provides serializer classes for converting Python objects to and from
serialized formats like JSON and Pickle. These serializers are used throughout
AioScrapy for data persistence, message passing, and caching.
此模块提供了用于将Python对象转换为序列化格式（如JSON和Pickle）以及从这些格式转换回来的
序列化器类。这些序列化器在AioScrapy中用于数据持久化、消息传递和缓存。
"""

import ujson
import pickle
from abc import ABCMeta, abstractmethod

__all__ = ['PickleSerializer', 'JsonSerializer', 'AbsSerializer']


class AbsSerializer(object, metaclass=ABCMeta):
    """
    Abstract base class for serializers.
    序列化器的抽象基类。

    This class defines the interface that all serializers must implement.
    It provides methods for serializing Python objects to a string format
    and deserializing strings back to Python objects.
    此类定义了所有序列化器必须实现的接口。
    它提供了将Python对象序列化为字符串格式以及将字符串反序列化回Python对象的方法。
    """

    @staticmethod
    @abstractmethod
    def loads(s):
        """
        Deserialize a string to a Python object.
        将字符串反序列化为Python对象。

        This method takes a serialized string and converts it back to
        a Python object.
        此方法接受一个序列化的字符串并将其转换回Python对象。

        Args:
            s: The serialized string to deserialize.
               要反序列化的序列化字符串。

        Returns:
            The deserialized Python object.
            反序列化的Python对象。

        Raises:
            Depends on the implementation.
            取决于实现。
        """
        pass

    @staticmethod
    @abstractmethod
    def dumps(obj):
        """
        Serialize a Python object to a string.
        将Python对象序列化为字符串。

        This method takes a Python object and converts it to a serialized
        string format.
        此方法接受一个Python对象并将其转换为序列化的字符串格式。

        Args:
            obj: The Python object to serialize.
                 要序列化的Python对象。

        Returns:
            The serialized string representation of the object.
            对象的序列化字符串表示。

        Raises:
            Depends on the implementation.
            取决于实现。
        """
        pass


class PickleSerializer(AbsSerializer):
    """
    Serializer that uses Python's pickle module.
    使用Python的pickle模块的序列化器。

    This serializer uses Python's built-in pickle module to serialize and
    deserialize Python objects. Pickle can handle a wide range of Python
    objects, including custom classes, but the resulting serialized data
    is not human-readable and may not be compatible across different
    Python versions.
    此序列化器使用Python内置的pickle模块来序列化和反序列化Python对象。
    Pickle可以处理各种Python对象，包括自定义类，但生成的序列化数据
    不是人类可读的，并且可能在不同的Python版本之间不兼容。

    Warning:
        Pickle is not secure against maliciously constructed data. Never unpickle
        data received from untrusted or unauthenticated sources.
        Pickle对恶意构造的数据不安全。切勿对来自不受信任或未经身份验证的
        来源的数据进行反序列化。
    """

    @staticmethod
    def loads(s):
        """
        Deserialize a pickle-encoded string to a Python object.
        将pickle编码的字符串反序列化为Python对象。

        Args:
            s: The pickle-encoded string to deserialize.
               要反序列化的pickle编码字符串。

        Returns:
            The deserialized Python object.
            反序列化的Python对象。

        Raises:
            pickle.UnpicklingError: If the data cannot be unpickled.
                                   如果数据无法被反序列化。
            ValueError: If the pickle data is truncated.
                       如果pickle数据被截断。
            TypeError: If the serialized data is not a bytes-like object.
                      如果序列化数据不是类字节对象。
        """
        return pickle.loads(s)

    @staticmethod
    def dumps(obj):
        """
        Serialize a Python object to a pickle-encoded string.
        将Python对象序列化为pickle编码的字符串。

        Args:
            obj: The Python object to serialize.
                要序列化的Python对象。

        Returns:
            bytes: The pickle-encoded representation of the object.
                  对象的pickle编码表示。

        Raises:
            pickle.PicklingError: If the object cannot be pickled.
                                 如果对象无法被序列化。

        Note:
            Uses the highest available pickle protocol for maximum efficiency.
            使用最高可用的pickle协议以获得最大效率。
        """
        # protocol=-1 means use the highest available protocol
        # protocol=-1表示使用最高可用的协议
        return pickle.dumps(obj, protocol=-1)


class JsonSerializer(AbsSerializer):
    """
    Serializer that uses the ujson module.
    使用ujson模块的序列化器。

    This serializer uses the ujson module (UltraJSON) to serialize and
    deserialize Python objects to and from JSON format. UltraJSON is a fast
    JSON encoder and decoder written in C with Python bindings.
    此序列化器使用ujson模块（UltraJSON）将Python对象序列化为JSON格式
    以及从JSON格式反序列化。UltraJSON是一个用C编写的快速JSON编码器和
    解码器，带有Python绑定。

    JSON serialization is more limited than pickle in terms of the types it can
    handle (primarily: dict, list, str, int, float, bool, None), but it produces
    human-readable output and is safe to use with untrusted data.
    JSON序列化在可以处理的类型方面比pickle更有限（主要是：dict、list、str、
    int、float、bool、None），但它产生人类可读的输出，并且可以安全地
    用于不受信任的数据。
    """

    @staticmethod
    def loads(s):
        """
        Deserialize a JSON string to a Python object.
        将JSON字符串反序列化为Python对象。

        Args:
            s: The JSON string to deserialize.
               要反序列化的JSON字符串。

        Returns:
            The deserialized Python object (typically a dict, list, or primitive type).
            反序列化的Python对象（通常是dict、list或原始类型）。

        Raises:
            ValueError: If the string is not valid JSON.
                       如果字符串不是有效的JSON。
        """
        return ujson.loads(s)

    @staticmethod
    def dumps(obj):
        """
        Serialize a Python object to a JSON string.
        将Python对象序列化为JSON字符串。

        Args:
            obj: The Python object to serialize.
                要序列化的Python对象。
                Must be a type that can be represented in JSON (dict, list, str,
                int, float, bool, None, or a combination of these).
                必须是可以在JSON中表示的类型（dict、list、str、int、float、
                bool、None或这些的组合）。

        Returns:
            str: The JSON string representation of the object.
                 对象的JSON字符串表示。

        Raises:
            TypeError: If the object contains types that cannot be serialized to JSON.
                      如果对象包含无法序列化为JSON的类型。
            OverflowError: If an integer is too large to be represented in JSON.
                          如果整数太大而无法在JSON中表示。
        """
        return ujson.dumps(obj)

