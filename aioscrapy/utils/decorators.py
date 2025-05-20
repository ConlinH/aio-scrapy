"""
Decorator utilities for aioscrapy.
aioscrapy的装饰器实用工具。

This module provides utility decorators for use in aioscrapy.
It includes decorators for marking functions and methods as deprecated.
此模块提供了在aioscrapy中使用的实用装饰器。
它包括用于将函数和方法标记为已弃用的装饰器。
"""

import warnings
from functools import wraps

from aioscrapy.exceptions import AioScrapyDeprecationWarning


def deprecated(use_instead=None):
    """
    Decorator to mark functions or methods as deprecated.
    用于将函数或方法标记为已弃用的装饰器。

    This decorator can be used to mark functions or methods as deprecated.
    It will emit a warning when the decorated function is called, informing
    users that the function is deprecated and suggesting an alternative if provided.
    此装饰器可用于将函数或方法标记为已弃用。
    当调用被装饰的函数时，它将发出警告，通知用户该函数已弃用，
    并在提供替代方案时建议使用替代方案。

    The decorator can be used in two ways:
    装饰器可以通过两种方式使用：

    1. With no arguments: @deprecated
    2. With an argument specifying the alternative: @deprecated("new_function")

    Args:
        use_instead: Optional string indicating the alternative function or method to use.
                    可选的字符串，指示要使用的替代函数或方法。
                    Defaults to None.
                    默认为None。

    Returns:
        callable: A decorated function that will emit a deprecation warning when called.
                一个装饰后的函数，在调用时会发出弃用警告。

    Example:
        >>> @deprecated
        ... def old_function():
        ...     return "result"
        ...
        >>> @deprecated("new_improved_function")
        ... def another_old_function():
        ...     return "result"
        ...
        >>> # When called, these will emit warnings:
        >>> old_function()  # Warning: "Call to deprecated function old_function."
        >>> another_old_function()  # Warning: "Call to deprecated function another_old_function. Use new_improved_function instead."
    """
    # Handle case where decorator is used without arguments: @deprecated
    # 处理装饰器不带参数使用的情况：@deprecated
    if callable(use_instead):
        # In this case, use_instead is actually the function being decorated
        # 在这种情况下，use_instead实际上是被装饰的函数
        func = use_instead
        use_instead = None

        # Apply the decorator directly and return the wrapped function
        # 直接应用装饰器并返回包装后的函数
        @wraps(func)
        def wrapped(*args, **kwargs):
            message = f"Call to deprecated function {func.__name__}."
            warnings.warn(message, category=AioScrapyDeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapped

    # Handle case where decorator is used with an argument: @deprecated("new_function")
    # 处理装饰器带参数使用的情况：@deprecated("new_function")
    def deco(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # Create the warning message
            # 创建警告消息
            message = f"Call to deprecated function {func.__name__}."
            if use_instead:
                message += f" Use {use_instead} instead."

            # Emit the deprecation warning
            # 发出弃用警告
            warnings.warn(message, category=AioScrapyDeprecationWarning, stacklevel=2)

            # Call the original function
            # 调用原始函数
            return func(*args, **kwargs)
        return wrapped

    return deco
