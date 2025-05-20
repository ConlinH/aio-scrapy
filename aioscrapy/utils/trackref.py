"""
Object reference tracking utilities for aioscrapy.
aioscrapy的对象引用跟踪实用工具。

This module provides functions and classes to record and report references to
live object instances. It's useful for debugging memory leaks and tracking
object lifetimes in aioscrapy applications.
此模块提供了用于记录和报告活动对象实例引用的函数和类。
它对于调试内存泄漏和跟踪aioscrapy应用程序中的对象生命周期很有用。

Usage:
使用方法：
If you want live objects for a particular class to be tracked, you only have to
subclass from object_ref (instead of object).
如果您希望跟踪特定类的活动对象，只需从object_ref（而不是object）继承即可。

About performance:
关于性能：
This library has a minimal performance impact when enabled, and no performance
penalty at all when disabled (as object_ref becomes just an alias to object
in that case).
启用时，此库对性能的影响最小，禁用时完全没有性能损失
（因为在这种情况下，object_ref只是object的别名）。
"""

from collections import defaultdict
from operator import itemgetter
from time import time
from typing import DefaultDict
from weakref import WeakKeyDictionary


# Type alias for the None type, used for default ignore parameter in format_live_refs
# None类型的类型别名，用于format_live_refs中的默认ignore参数
NoneType = type(None)

# Global dictionary that maps classes to WeakKeyDictionaries of their instances
# 全局字典，将类映射到其实例的WeakKeyDictionary
# The WeakKeyDictionary for each class maps object instances to their creation time
# 每个类的WeakKeyDictionary将对象实例映射到它们的创建时间
live_refs: DefaultDict[type, WeakKeyDictionary] = defaultdict(WeakKeyDictionary)


class object_ref:
    """
    Base class for tracking live object instances.
    用于跟踪活动对象实例的基类。

    Inherit from this class instead of directly from 'object' to enable tracking
    of instances of your class. Each instance will be recorded in the global
    'live_refs' dictionary with its creation time.
    从此类继承而不是直接从'object'继承，以启用对您的类实例的跟踪。
    每个实例都将与其创建时间一起记录在全局'live_refs'字典中。

    This tracking uses weak references, so it doesn't prevent garbage collection
    of objects that are no longer referenced elsewhere.
    此跟踪使用弱引用，因此不会阻止垃圾收集不再在其他地方引用的对象。
    """

    # Using __slots__ to reduce memory footprint
    # 使用__slots__减少内存占用
    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance and register it in the tracking system.
        创建一个新实例并将其注册到跟踪系统中。

        This method creates a new instance of the class and adds it to the
        'live_refs' dictionary with the current timestamp. This allows tracking
        when the object was created and how many instances exist.
        此方法创建类的新实例，并将其与当前时间戳一起添加到'live_refs'字典中。
        这允许跟踪对象的创建时间以及存在多少个实例。

        Args:
            *args: Variable length argument list passed to the constructor.
                  传递给构造函数的可变长度参数列表。
            **kwargs: Arbitrary keyword arguments passed to the constructor.
                     传递给构造函数的任意关键字参数。

        Returns:
            The newly created object instance.
            新创建的对象实例。
        """
        # Create the object using the standard object.__new__
        # 使用标准的object.__new__创建对象
        obj = object.__new__(cls)

        # Register the object in live_refs with current timestamp
        # 使用当前时间戳在live_refs中注册对象
        live_refs[cls][obj] = time()

        return obj


def format_live_refs(ignore=NoneType):
    """
    Generate a formatted table of tracked live objects.
    生成跟踪的活动对象的格式化表格。

    This function creates a human-readable table showing statistics about
    tracked objects, including:
    - The class name
    - The number of live instances
    - The age of the oldest instance

    此函数创建一个人类可读的表格，显示有关跟踪对象的统计信息，包括：
    - 类名
    - 活动实例的数量
    - 最旧实例的年龄

    Args:
        ignore: A class or type to ignore in the output. Instances of this class
               and its subclasses will not be included in the report.
               要在输出中忽略的类或类型。此类及其子类的实例将不会包含在报告中。
               Default is NoneType.
               默认为NoneType。

    Returns:
        str: A formatted string containing the tabular representation of tracked objects.
             包含跟踪对象的表格表示的格式化字符串。
    """
    # Start with a header
    # 以标题开始
    s = "Live References\n\n"

    # Get current time for age calculation
    # 获取当前时间用于年龄计算
    now = time()

    # Sort classes by name for consistent output
    # 按名称对类进行排序以获得一致的输出
    for cls, wdict in sorted(live_refs.items(),
                             key=lambda x: x[0].__name__):
        # Skip empty dictionaries (no instances)
        # 跳过空字典（没有实例）
        if not wdict:
            continue

        # Skip ignored classes and their subclasses
        # 跳过被忽略的类及其子类
        if issubclass(cls, ignore):
            continue

        # Find the oldest instance
        # 查找最旧的实例
        oldest = min(wdict.values())

        # Format the line: class name, instance count, and age of oldest instance
        # 格式化行：类名、实例计数和最旧实例的年龄
        s += f"{cls.__name__:<30} {len(wdict):6}   oldest: {int(now - oldest)}s ago\n"

    return s


def print_live_refs(*a, **kw):
    """
    Print a formatted table of tracked live objects to stdout.
    将跟踪的活动对象的格式化表格打印到标准输出。

    This is a convenience function that calls format_live_refs() and prints
    the result to the standard output. It's useful for interactive debugging
    or for logging object tracking information.
    这是一个便捷函数，它调用format_live_refs()并将结果打印到标准输出。
    它对于交互式调试或记录对象跟踪信息很有用。

    Args:
        *a: Positional arguments passed to format_live_refs().
            传递给format_live_refs()的位置参数。
        **kw: Keyword arguments passed to format_live_refs().
              传递给format_live_refs()的关键字参数。

    Returns:
        None
    """
    # Format the live references and print the result
    # 格式化活动引用并打印结果
    print(format_live_refs(*a, **kw))


def get_oldest(class_name):
    """
    Get the oldest tracked instance of a class by its name.
    通过名称获取类的最旧跟踪实例。

    This function finds the oldest (longest-living) instance of a class
    with the given name. The age is determined by the timestamp recorded
    when the object was created.
    此函数查找具有给定名称的类的最旧（存活时间最长）实例。
    年龄由创建对象时记录的时间戳确定。

    Args:
        class_name: The name of the class to search for.
                   要搜索的类的名称。

    Returns:
        object: The oldest instance of the specified class, or None if no
               instances are found.
               指定类的最旧实例，如果未找到实例则为None。
    """
    # Iterate through all tracked classes
    # 遍历所有跟踪的类
    for cls, wdict in live_refs.items():
        # Find the class with the matching name
        # 查找具有匹配名称的类
        if cls.__name__ == class_name:
            # If there are no instances, return None
            # 如果没有实例，返回None
            if not wdict:
                break

            # Find the instance with the minimum timestamp (oldest)
            # 查找具有最小时间戳（最旧）的实例
            return min(wdict.items(), key=itemgetter(1))[0]

    # Return None if no matching class or instances are found
    # 如果未找到匹配的类或实例，则返回None
    return None


def iter_all(class_name):
    """
    Iterate over all tracked instances of a class by its name.
    通过名称迭代类的所有跟踪实例。

    This function returns an iterator over all live instances of a class
    with the given name. It's useful for inspecting or manipulating all
    instances of a particular class during debugging.
    此函数返回具有给定名称的类的所有活动实例的迭代器。
    它对于在调试期间检查或操作特定类的所有实例很有用。

    Args:
        class_name: The name of the class to search for.
                   要搜索的类的名称。

    Returns:
        iterator: An iterator over all instances of the specified class,
                 or None if no matching class is found.
                 指定类的所有实例的迭代器，如果未找到匹配的类则为None。
    """
    # Iterate through all tracked classes
    # 遍历所有跟踪的类
    for cls, wdict in live_refs.items():
        # Find the class with the matching name
        # 查找具有匹配名称的类
        if cls.__name__ == class_name:
            # Return an iterator over all instances of this class
            # 返回此类的所有实例的迭代器
            return wdict.keys()

    # Return None if no matching class is found
    # 如果未找到匹配的类，则返回None
    return None
