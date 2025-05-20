"""
HTTP headers implementation for aioscrapy.
aioscrapy的HTTP头部实现。

This module provides the Headers class, which is a case-insensitive dictionary
specifically designed for handling HTTP headers. It normalizes header names
to title case for consistent access regardless of the original casing.
此模块提供了Headers类，这是一个专门为处理HTTP头部设计的大小写不敏感的字典。
它将头部名称规范化为标题大小写，以便无论原始大小写如何都能一致地访问。
"""

from collections.abc import Mapping


class Headers(dict):
    """
    Case insensitive HTTP headers dictionary.
    大小写不敏感的HTTP头部字典。

    This class extends the built-in dict to provide a case-insensitive
    dictionary specifically for HTTP headers. Header names are normalized
    to title case (e.g., 'content-type' becomes 'Content-Type') for
    consistent access regardless of the original casing.
    此类扩展了内置的dict，为HTTP头部提供了一个大小写不敏感的字典。
    头部名称被规范化为标题大小写（例如，'content-type'变为'Content-Type'），
    以便无论原始大小写如何都能一致地访问。

    Example:
        ```python
        headers = Headers({'content-type': 'text/html'})
        assert headers['Content-Type'] == 'text/html'
        assert headers['CONTENT-TYPE'] == 'text/html'
        assert headers['content-type'] == 'text/html'
        ```
    """

    # Use __slots__ to optimize memory usage
    # 使用__slots__优化内存使用
    __slots__ = ()

    def __init__(self, seq=None):
        """
        Initialize a Headers dictionary.
        初始化Headers字典。

        Args:
            seq: An optional sequence of key-value pairs or a mapping to initialize the dictionary.
                一个可选的键值对序列或映射，用于初始化字典。
        """
        super().__init__()
        if seq:
            self.update(seq)

    def __getitem__(self, key):
        """
        Get a header value by key.
        通过键获取头部值。

        The key is normalized to title case before lookup.
        在查找之前，键会被规范化为标题大小写。

        Args:
            key: The header name.
                头部名称。

        Returns:
            The header value.
            头部值。

        Raises:
            KeyError: If the header is not found.
                     如果未找到头部。
        """
        return dict.__getitem__(self, self.normkey(key))

    def __setitem__(self, key, value):
        """
        Set a header value.
        设置头部值。

        The key is normalized to title case and the value is normalized
        before being stored.
        在存储之前，键会被规范化为标题大小写，值也会被规范化。

        Args:
            key: The header name.
                头部名称。
            value: The header value.
                  头部值。
        """
        dict.__setitem__(self, self.normkey(key), self.normvalue(value))

    def __delitem__(self, key):
        """
        Delete a header.
        删除头部。

        The key is normalized to title case before lookup.
        在查找之前，键会被规范化为标题大小写。

        Args:
            key: The header name.
                头部名称。

        Raises:
            KeyError: If the header is not found.
                     如果未找到头部。
        """
        dict.__delitem__(self, self.normkey(key))

    def __contains__(self, key):
        """
        Check if a header exists.
        检查头部是否存在。

        The key is normalized to title case before lookup.
        在查找之前，键会被规范化为标题大小写。

        Args:
            key: The header name.
                头部名称。

        Returns:
            bool: True if the header exists, False otherwise.
                 如果头部存在则为True，否则为False。
        """
        return dict.__contains__(self, self.normkey(key))

    # Alias for backward compatibility
    # 为了向后兼容的别名
    has_key = __contains__

    def __copy__(self):
        """
        Create a copy of the Headers dictionary.
        创建Headers字典的副本。

        Returns:
            Headers: A new Headers instance with the same contents.
                    具有相同内容的新Headers实例。
        """
        return self.__class__(self)

    # Alias for standard dict interface
    # 标准dict接口的别名
    copy = __copy__

    def normkey(self, key):
        """
        Normalize a dictionary key for case-insensitive access.
        规范化字典键以进行大小写不敏感的访问。

        This method converts the key to title case (e.g., 'content-type' becomes 'Content-Type').
        此方法将键转换为标题大小写（例如，'content-type'变为'Content-Type'）。

        Args:
            key: The header name to normalize.
                要规范化的头部名称。

        Returns:
            str: The normalized header name.
                规范化的头部名称。
        """
        return key.title()

    def normvalue(self, value):
        """
        Normalize a value before setting it in the dictionary.
        在将值设置到字典中之前对其进行规范化。

        This method is a hook for subclasses to override. The base implementation
        returns the value unchanged.
        此方法是供子类重写的钩子。基本实现返回未更改的值。

        Args:
            value: The header value to normalize.
                  要规范化的头部值。

        Returns:
            The normalized header value.
            规范化的头部值。
        """
        return value

    def get(self, key, def_val=None):
        """
        Get a header value by key, with a default value if not found.
        通过键获取头部值，如果未找到则返回默认值。

        The key is normalized to title case and the default value is normalized
        before lookup.
        在查找之前，键会被规范化为标题大小写，默认值也会被规范化。

        Args:
            key: The header name.
                头部名称。
            def_val: The default value to return if the header is not found.
                    如果未找到头部，则返回的默认值。

        Returns:
            The header value if found, otherwise the default value.
            如果找到头部值则返回它，否则返回默认值。
        """
        return dict.get(self, self.normkey(key), self.normvalue(def_val))

    def setdefault(self, key, def_val=None):
        """
        Get a header value by key, or set it to a default value if not found.
        通过键获取头部值，如果未找到则将其设置为默认值。

        The key is normalized to title case and the default value is normalized
        before lookup or insertion.
        在查找或插入之前，键会被规范化为标题大小写，默认值也会被规范化。

        Args:
            key: The header name.
                头部名称。
            def_val: The default value to set and return if the header is not found.
                    如果未找到头部，则设置并返回的默认值。

        Returns:
            The header value if found, otherwise the default value.
            如果找到头部值则返回它，否则返回默认值。
        """
        return dict.setdefault(self, self.normkey(key), self.normvalue(def_val))

    def update(self, seq):
        """
        Update the dictionary with new headers.
        使用新头部更新字典。

        The keys and values are normalized before insertion.
        在插入之前，键和值会被规范化。

        Args:
            seq: A sequence of key-value pairs or a mapping to update the dictionary with.
                用于更新字典的键值对序列或映射。
        """
        # Convert mapping to items() if necessary
        # 如果需要，将映射转换为items()
        seq = seq.items() if isinstance(seq, Mapping) else seq

        # Normalize keys and values
        # 规范化键和值
        iseq = ((self.normkey(k), self.normvalue(v)) for k, v in seq)

        # Update the dictionary
        # 更新字典
        super().update(iseq)

    @classmethod
    def fromkeys(cls, keys, value=None):
        """
        Create a new Headers dictionary with the specified keys and value.
        使用指定的键和值创建一个新的Headers字典。

        Args:
            keys: An iterable of keys.
                 键的可迭代对象。
            value: The value to set for all keys.
                  为所有键设置的值。

        Returns:
            Headers: A new Headers instance with the specified keys and value.
                    具有指定键和值的新Headers实例。
        """
        return cls((k, value) for k in keys)

    def pop(self, key, *args):
        """
        Remove a header and return its value.
        移除头部并返回其值。

        The key is normalized to title case before lookup.
        在查找之前，键会被规范化为标题大小写。

        Args:
            key: The header name.
                头部名称。
            *args: Optional default value to return if the header is not found.
                  如果未找到头部，则返回的可选默认值。

        Returns:
            The header value if found, otherwise the default value.
            如果找到头部值则返回它，否则返回默认值。

        Raises:
            KeyError: If the header is not found and no default value is provided.
                     如果未找到头部且未提供默认值。
        """
        return dict.pop(self, self.normkey(key), *args)
