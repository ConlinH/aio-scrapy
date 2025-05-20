"""
Python utility functions for aioscrapy.
aioscrapy的Python实用函数。

This module contains essential utility functions for Python that enhance the standard library.
It provides functions for type conversion, string handling, regular expression searching,
memoization, and other common operations.
此模块包含增强标准库的Python基本实用函数。
它提供了用于类型转换、字符串处理、正则表达式搜索、记忆化和其他常见操作的函数。
"""
import gc
import re
import sys
import weakref
from functools import wraps

from aioscrapy.utils.decorators import deprecated


def is_listlike(x):
    """
    Check if the given object is list-like (iterable but not a string or bytes).
    检查给定对象是否类似列表（可迭代但不是字符串或字节）。

    This function determines if an object is iterable (has the __iter__ method)
    but is not a string or bytes object. This is useful for functions that
    should treat strings differently from other iterables.
    此函数确定对象是否可迭代（具有__iter__方法）但不是字符串或字节对象。
    这对于应该将字符串与其他可迭代对象区别对待的函数很有用。

    Args:
        x: The object to check.
           要检查的对象。

    Returns:
        bool: True if the object is list-like, False otherwise.
              如果对象类似列表则为True，否则为False。

    Examples:
        >>> is_listlike("foo")
        False
        >>> is_listlike(5)
        False
        >>> is_listlike(b"foo")
        False
        >>> is_listlike([b"foo"])
        True
        >>> is_listlike((b"foo",))
        True
        >>> is_listlike({})
        True
        >>> is_listlike(set())
        True
        >>> is_listlike((x for x in range(3)))
        True
        >>> is_listlike(range(5))
        True
    """
    return hasattr(x, "__iter__") and not isinstance(x, (str, bytes))


def to_unicode(text, encoding=None, errors='strict'):
    """
    Convert a bytes object to a unicode (str) object.
    将字节对象转换为unicode（str）对象。

    This function converts a bytes object to a unicode string using the specified
    encoding. If the input is already a unicode string, it is returned unchanged.
    此函数使用指定的编码将字节对象转换为unicode字符串。
    如果输入已经是unicode字符串，则原样返回。

    Args:
        text: The text to convert. Must be a bytes or str object.
              要转换的文本。必须是bytes或str对象。
        encoding: The encoding to use for decoding bytes. Defaults to 'utf-8'.
                 用于解码字节的编码。默认为'utf-8'。
        errors: The error handling scheme for decoding. Defaults to 'strict'.
               解码的错误处理方案。默认为'strict'。

    Returns:
        str: The unicode representation of the input text.
             输入文本的unicode表示。

    Raises:
        TypeError: If the input is not a bytes or str object.
                  如果输入不是bytes或str对象。
    """
    if isinstance(text, str):
        return text
    if not isinstance(text, (bytes, str)):
        raise TypeError('to_unicode must receive a bytes or str '
                        f'object, got {type(text).__name__}')
    if encoding is None:
        encoding = 'utf-8'
    return text.decode(encoding, errors)


def to_bytes(text, encoding=None, errors='strict'):
    """
    Convert a unicode (str) object to a bytes object.
    将unicode（str）对象转换为字节对象。

    This function converts a unicode string to a bytes object using the specified
    encoding. If the input is already a bytes object, it is returned unchanged.
    此函数使用指定的编码将unicode字符串转换为字节对象。
    如果输入已经是字节对象，则原样返回。

    Args:
        text: The text to convert. Must be a str or bytes object.
              要转换的文本。必须是str或bytes对象。
        encoding: The encoding to use for encoding the string. Defaults to 'utf-8'.
                 用于编码字符串的编码。默认为'utf-8'。
        errors: The error handling scheme for encoding. Defaults to 'strict'.
               编码的错误处理方案。默认为'strict'。

    Returns:
        bytes: The binary representation of the input text.
               输入文本的二进制表示。

    Raises:
        TypeError: If the input is not a str or bytes object.
                  如果输入不是str或bytes对象。
    """
    if isinstance(text, bytes):
        return text
    if not isinstance(text, str):
        raise TypeError('to_bytes must receive a str or bytes '
                        f'object, got {type(text).__name__}')
    if encoding is None:
        encoding = 'utf-8'
    return text.encode(encoding, errors)


@deprecated('to_unicode')
def to_native_str(text, encoding=None, errors='strict'):
    """
    Convert text to native string type (str).
    将文本转换为本地字符串类型（str）。

    This function is deprecated. Use to_unicode() instead.
    此函数已弃用。请改用to_unicode()。

    Args:
        text: The text to convert.
              要转换的文本。
        encoding: The encoding to use for decoding bytes. Defaults to 'utf-8'.
                 用于解码字节的编码。默认为'utf-8'。
        errors: The error handling scheme. Defaults to 'strict'.
               错误处理方案。默认为'strict'。

    Returns:
        str: The string representation of the input text.
             输入文本的字符串表示。
    """
    return to_unicode(text, encoding, errors)


def re_rsearch(pattern, text, chunk_size=1024):
    """
    Perform a reverse search in text using a regular expression pattern.
    使用正则表达式模式在文本中执行反向搜索。

    This function searches for the last occurrence of a pattern in a text,
    starting from the end. Since the re module does not provide reverse search
    functionality, this function implements it by searching in chunks from the
    end of the text for efficiency.
    此函数从文本末尾开始搜索模式的最后一次出现。
    由于re模块不提供反向搜索功能，此函数通过从文本末尾的块中搜索来实现它，以提高效率。

    The algorithm works as follows:
    1. Extract a chunk of 'chunk_size' kilobytes from the end of the text
    2. Search for the pattern in this chunk
    3. If not found, extract another chunk further from the end and search again
    4. Continue until a match is found or the entire text has been searched

    算法工作原理如下：
    1. 从文本末尾提取'chunk_size'千字节的块
    2. 在此块中搜索模式
    3. 如果未找到，从末尾进一步提取另一个块并再次搜索
    4. 继续直到找到匹配项或已搜索整个文本

    Args:
        pattern: The regular expression pattern to search for.
                要搜索的正则表达式模式。
                Can be a string or a compiled regex pattern.
                可以是字符串或已编译的正则表达式模式。
        text: The text to search in.
              要搜索的文本。
        chunk_size: The size of each chunk in kilobytes. Defaults to 1024 (1MB).
                   每个块的大小（千字节）。默认为1024（1MB）。

    Returns:
        tuple or None: If a match is found, returns a tuple (start, end) with the
                      positions of the match in the entire text. If no match is found,
                      returns None.
                      如果找到匹配项，返回一个元组(start, end)，其中包含整个文本中
                      匹配项的位置。如果未找到匹配项，返回None。
    """
    # Inner function to generate chunks from the end of the text
    # 从文本末尾生成块的内部函数
    def _chunk_iter():
        offset = len(text)
        while True:
            offset -= (chunk_size * 1024)
            if offset <= 0:
                break
            yield (text[offset:], offset)
        yield (text, 0)

    # Compile the pattern if it's a string
    # 如果模式是字符串，则编译它
    if isinstance(pattern, str):
        pattern = re.compile(pattern)

    # Search for the pattern in each chunk
    # 在每个块中搜索模式
    for chunk, offset in _chunk_iter():
        matches = [match for match in pattern.finditer(chunk)]
        if matches:
            # Return the position of the last match in the chunk
            # 返回块中最后一个匹配项的位置
            start, end = matches[-1].span()
            return offset + start, offset + end
    return None


def memoizemethod_noargs(method):
    """
    Decorator to cache the result of a method with no arguments.
    装饰器，用于缓存无参数方法的结果。

    This decorator caches the result of a method call using a weak reference
    to the object. This means the cache entry will be automatically removed
    when the object is garbage collected.
    此装饰器使用对对象的弱引用缓存方法调用的结果。
    这意味着当对象被垃圾回收时，缓存条目将自动被移除。

    Note that while the decorated method can accept arguments, the caching
    is based only on the object instance, not on the arguments. This means
    that only the first call's result will be cached, regardless of arguments.
    请注意，虽然装饰的方法可以接受参数，但缓存仅基于对象实例，而不是参数。
    这意味着无论参数如何，只有第一次调用的结果将被缓存。

    Args:
        method: The method to be decorated.
               要装饰的方法。

    Returns:
        function: A new method that caches its result.
                 缓存其结果的新方法。
    """
    # Create a weak key dictionary to store cached results
    # 创建一个弱键字典来存储缓存的结果
    cache = weakref.WeakKeyDictionary()

    @wraps(method)
    def new_method(self, *args, **kwargs):
        # If the result is not cached for this object, call the method
        # 如果此对象的结果未缓存，则调用该方法
        if self not in cache:
            cache[self] = method(self, *args, **kwargs)
        # Return the cached result
        # 返回缓存的结果
        return cache[self]

    return new_method


def without_none_values(iterable):
    """
    Return a copy of an iterable with all None entries removed.
    返回一个去除所有None条目的可迭代对象的副本。

    This function creates a new iterable of the same type as the input,
    but with all None values removed. It handles both mappings (like dictionaries)
    and sequences (like lists, tuples).
    此函数创建一个与输入相同类型的新可迭代对象，但移除了所有None值。
    它处理映射（如字典）和序列（如列表、元组）。

    Args:
        iterable: The iterable to process. Can be a mapping or a sequence.
                 要处理的可迭代对象。可以是映射或序列。

    Returns:
        A new iterable of the same type as the input, but with all None values removed.
        一个与输入相同类型的新可迭代对象，但移除了所有None值。

    Examples:
        >>> without_none_values({'a': 1, 'b': None, 'c': 3})
        {'a': 1, 'c': 3}
        >>> without_none_values([1, None, 3, None, 5])
        [1, 3, 5]
    """
    try:
        # Handle mappings (objects with .items() method)
        # 处理映射（具有.items()方法的对象）
        return {k: v for k, v in iterable.items() if v is not None}
    except AttributeError:
        # Handle sequences and other iterables
        # 处理序列和其他可迭代对象
        return type(iterable)((v for v in iterable if v is not None))


def global_object_name(obj):
    """
    Return the full qualified name of a global object.
    返回全局对象的完全限定名称。

    This function returns the full name of an object, including its module path.
    It's useful for debugging, logging, and serialization purposes.
    此函数返回对象的完整名称，包括其模块路径。
    它对于调试、日志记录和序列化目的很有用。

    Args:
        obj: The object to get the name for. Must have __module__ and __name__ attributes.
             要获取名称的对象。必须具有__module__和__name__属性。

    Returns:
        str: The full qualified name of the object in the format "module.name".
             对象的完全限定名称，格式为"module.name"。

    Examples:
        >>> from aioscrapy import Request
        >>> global_object_name(Request)
        'aioscrapy.http.request.Request'
    """
    return f"{obj.__module__}.{obj.__name__}"


if hasattr(sys, "pypy_version_info"):
    def garbage_collect():
        """
        Force garbage collection, with special handling for PyPy.
        强制垃圾回收，对PyPy进行特殊处理。

        On PyPy, collecting weak references can take two collection cycles,
        so this function calls gc.collect() twice.
        在PyPy上，收集弱引用可能需要两个收集周期，
        因此此函数调用gc.collect()两次。
        """
        # Collecting weakreferences can take two collections on PyPy.
        # 在PyPy上收集弱引用可能需要两次收集。
        gc.collect()
        gc.collect()
else:
    def garbage_collect():
        """
        Force garbage collection.
        强制垃圾回收。

        This function calls Python's garbage collector to force a collection cycle.
        It's useful when you need to ensure that objects with no references are
        properly cleaned up, especially those with __del__ methods or weak references.
        此函数调用Python的垃圾收集器来强制进行收集周期。
        当您需要确保没有引用的对象被正确清理时，这很有用，
        特别是那些具有__del__方法或弱引用的对象。
        """
        gc.collect()
