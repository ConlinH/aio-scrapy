"""
Spider utility functions for aioscrapy.
aioscrapy的爬虫实用函数。

This module provides utility functions for working with spider classes in aioscrapy.
It includes functions for discovering and iterating over spider classes.
此模块提供了用于处理aioscrapy中爬虫类的实用函数。
它包括用于发现和迭代爬虫类的函数。
"""

import inspect

from aioscrapy.spiders import Spider


def iter_spider_classes(module):
    """
    Iterate over all valid spider classes defined in a module.
    迭代模块中定义的所有有效爬虫类。

    This function finds all classes in the given module that:
    1. Are subclasses of the Spider class
    2. Are defined in the module itself (not imported)
    3. Have a non-empty 'name' attribute (required for instantiation)

    此函数查找给定模块中满足以下条件的所有类：
    1. 是Spider类的子类
    2. 在模块本身中定义（非导入）
    3. 具有非空的'name'属性（实例化所必需的）

    The function is used by the spider loader to discover spiders in a module.
    该函数被爬虫加载器用来在模块中发现爬虫。

    Args:
        module: The module object to inspect for spider classes.
               要检查爬虫类的模块对象。

    Yields:
        class: Spider classes that can be instantiated.
              可以实例化的爬虫类。

    Note:
        This implementation avoids importing the spider manager singleton
        from aioscrapy.spider.spiders, which would create circular imports.
        此实现避免从aioscrapy.spider.spiders导入爬虫管理器单例，
        这会创建循环导入。
    """
    # Iterate through all objects in the module
    # 迭代模块中的所有对象
    for obj in vars(module).values():
        # Check if the object meets all criteria for a valid spider class
        # 检查对象是否满足有效爬虫类的所有条件
        if (
                # Must be a class
                # 必须是一个类
                inspect.isclass(obj)
                # Must be a subclass of Spider
                # 必须是Spider的子类
                and issubclass(obj, Spider)
                # Must be defined in this module (not imported)
                # 必须在此模块中定义（非导入）
                and obj.__module__ == module.__name__
                # Must have a name attribute (required for instantiation)
                # 必须有name属性（实例化所必需的）
                and getattr(obj, 'name', None)
        ):
            yield obj
