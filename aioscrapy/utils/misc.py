"""
Miscellaneous utility functions for aioscrapy.
aioscrapy的杂项实用函数。

This module contains helper functions that don't fit into other utility categories.
It provides functionality for module walking, object loading, and instance creation.
此模块包含不适合其他实用程序类别的辅助函数。
它提供了模块遍历、对象加载和实例创建的功能。
"""

from importlib import import_module
from pkgutil import iter_modules

from aioscrapy.utils.tools import call_helper


def walk_modules(path):
    """
    Load a module and all its submodules recursively.
    递归加载模块及其所有子模块。

    This function imports a module and all its submodules from the given module path
    and returns them as a list. It performs a recursive traversal of the module tree.
    If any module raises an exception during import, that exception is propagated.
    此函数从给定的模块路径导入模块及其所有子模块，并将它们作为列表返回。
    它执行模块树的递归遍历。如果任何模块在导入过程中引发异常，则该异常会被传播。

    Args:
        path: The module path to load (e.g., 'aioscrapy.utils').
              要加载的模块路径（例如，'aioscrapy.utils'）。

    Returns:
        list: A list of imported modules, including the root module and all submodules.
              导入的模块列表，包括根模块和所有子模块。

    Raises:
        ImportError: If any module cannot be imported.
                    如果任何模块无法导入。

    Example:
        >>> mods = walk_modules('aioscrapy.utils')
        >>> 'aioscrapy.utils.url' in [mod.__name__ for mod in mods]
        True
    """
    # Initialize the list of modules
    # 初始化模块列表
    mods = []

    # Import the root module
    # 导入根模块
    mod = import_module(path)
    mods.append(mod)

    # If the module is a package (has a __path__), process its submodules
    # 如果模块是一个包（有__path__），处理其子模块
    if hasattr(mod, '__path__'):
        for _, subpath, ispkg in iter_modules(mod.__path__):
            # Construct the full path for the submodule
            # 构造子模块的完整路径
            fullpath = path + '.' + subpath

            # If the submodule is a package, recursively walk it
            # 如果子模块是一个包，递归遍历它
            if ispkg:
                mods += walk_modules(fullpath)
            # Otherwise, import the submodule and add it to the list
            # 否则，导入子模块并将其添加到列表中
            else:
                submod = import_module(fullpath)
                mods.append(submod)

    return mods


def load_object(path: str):
    """
    Load an object by its fully qualified name.
    通过完全限定名称加载对象。

    This function imports a module and retrieves an object from it based on the
    provided import path. The object can be a class, function, variable, or an
    instance defined in the specified module.
    此函数根据提供的导入路径导入模块并从中检索对象。
    对象可以是在指定模块中定义的类、函数、变量或实例。

    Args:
        path: The absolute object path (e.g., 'aioscrapy.libs.downloader.redirect.RedirectMiddleware').
              对象的绝对路径（例如，'aioscrapy.libs.downloader.redirect.RedirectMiddleware'）。

    Returns:
        The loaded object.
        加载的对象。

    Raises:
        ValueError: If the path is not a full path (doesn't contain a dot).
                   如果路径不是完整路径（不包含点）。
        NameError: If the module doesn't define the specified object.
                  如果模块未定义指定的对象。
        ImportError: If the module cannot be imported.
                    如果无法导入模块。

    Example:
        >>> middleware = load_object('aioscrapy.libs.downloader.redirect.RedirectMiddleware')
        >>> middleware.__name__
        'RedirectMiddleware'
    """
    # Find the last dot in the path to separate module path from object name
    # 在路径中查找最后一个点，以将模块路径与对象名称分开
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ValueError(f"Error loading object '{path}': not a full path")

    # Split the path into module path and object name
    # 将路径分割为模块路径和对象名称
    module, name = path[:dot], path[dot + 1:]

    # Import the module
    # 导入模块
    mod = import_module(module)

    # Get the object from the module
    # 从模块中获取对象
    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError(f"Module '{module}' doesn't define any object named '{name}'")

    return obj


async def create_instance(objcls, settings, crawler, *args, spider=None, **kwargs):
    """
    Create an instance of a class using its factory methods.
    使用类的工厂方法创建类的实例。

    This function tries to create an instance of the given class using one of its
    factory methods in the following order of preference:
    1. from_crawler(crawler, *args, **kwargs) - if crawler is provided
    2. from_spider(spider, *args, **kwargs) - if spider is provided
    3. from_settings(settings, *args, **kwargs) - if settings is provided
    4. Regular constructor: objcls(*args, **kwargs) - as a fallback

    此函数尝试使用给定类的一个工厂方法创建实例，优先顺序如下：
    1. from_crawler(crawler, *args, **kwargs) - 如果提供了crawler
    2. from_spider(spider, *args, **kwargs) - 如果提供了spider
    3. from_settings(settings, *args, **kwargs) - 如果提供了settings
    4. 常规构造函数：objcls(*args, **kwargs) - 作为后备选项

    Args:
        objcls: The class to instantiate.
               要实例化的类。
        settings: The settings object to use. Can be None if crawler is provided.
                 要使用的设置对象。如果提供了crawler，可以为None。
        crawler: The crawler object to use. Can be None.
                要使用的爬虫对象。可以为None。
        *args: Positional arguments to pass to the constructor.
               传递给构造函数的位置参数。
        spider: The spider object to use. Can be None.
               要使用的蜘蛛对象。可以为None。
        **kwargs: Keyword arguments to pass to the constructor.
                 传递给构造函数的关键字参数。

    Returns:
        An instance of the specified class.
        指定类的实例。

    Raises:
        ValueError: If settings, crawler, and spider are all None.
                   如果settings、crawler和spider都为None。
        TypeError: If the factory method returns None.
                  如果工厂方法返回None。
    """
    # Ensure we have settings from either crawler, spider, or directly provided
    # 确保我们从crawler、spider或直接提供的参数中获取设置
    if settings is None:
        if crawler is None and spider is None:
            raise ValueError("Specify at least one of settings, crawler and spider.")

        # Get settings from crawler or spider
        # 从crawler或spider获取设置
        settings = crawler and crawler.settings or spider and spider.settings
        # Get spider from crawler if not directly provided
        # 如果没有直接提供，从crawler获取spider
        spider = spider or crawler and crawler.spider

    # Try to create instance using the appropriate factory method
    # 尝试使用适当的工厂方法创建实例
    if crawler and hasattr(objcls, 'from_crawler'):
        # Use from_crawler if available and crawler is provided
        # 如果可用且提供了crawler，则使用from_crawler
        instance = await call_helper(objcls.from_crawler, crawler, *args, **kwargs)
        method_name = 'from_crawler'
    elif spider and hasattr(objcls, 'from_spider'):
        # Use from_spider if available and spider is provided
        # 如果可用且提供了spider，则使用from_spider
        instance = await call_helper(objcls.from_spider, spider, *args, **kwargs)
        method_name = 'from_spider'
    elif hasattr(objcls, 'from_settings'):
        # Use from_settings if available
        # 如果可用，则使用from_settings
        instance = await call_helper(objcls.from_settings, settings, *args, **kwargs)
        method_name = 'from_settings'
    else:
        # Fall back to regular constructor
        # 回退到常规构造函数
        instance = objcls(*args, **kwargs)
        method_name = '__new__'

    # Ensure the factory method returned a valid instance
    # 确保工厂方法返回了有效的实例
    if instance is None:
        raise TypeError(f"{objcls.__qualname__}.{method_name} returned None")

    return instance


async def load_instance(clspath: str, *args, settings=None, spider=None, crawler=None, **kwargs):
    """
    Load a class by its path and create an instance of it.
    通过路径加载类并创建其实例。

    This function combines load_object() and create_instance() to load a class
    by its fully qualified name and then create an instance of it using the
    appropriate factory method.
    此函数结合了load_object()和create_instance()，通过完全限定名称加载类，
    然后使用适当的工厂方法创建其实例。

    Args:
        clspath: The fully qualified class path (e.g., 'aioscrapy.libs.downloader.redirect.RedirectMiddleware').
                完全限定的类路径（例如，'aioscrapy.libs.downloader.redirect.RedirectMiddleware'）。
        *args: Positional arguments to pass to the constructor.
               传递给构造函数的位置参数。
        settings: The settings object to use. Can be None if crawler is provided.
                 要使用的设置对象。如果提供了crawler，可以为None。
        spider: The spider object to use. Can be None.
               要使用的蜘蛛对象。可以为None。
        crawler: The crawler object to use. Can be None.
                要使用的爬虫对象。可以为None。
        **kwargs: Keyword arguments to pass to the constructor.
                 传递给构造函数的关键字参数。

    Returns:
        An instance of the specified class.
        指定类的实例。

    Raises:
        ValueError: If settings, crawler, and spider are all None.
                   如果settings、crawler和spider都为None。
        TypeError: If the factory method returns None.
                  如果工厂方法返回None。
        ImportError: If the class cannot be imported.
                    如果无法导入类。
        NameError: If the module doesn't define the specified class.
                  如果模块未定义指定的类。
    """
    # First load the class by its path
    # 首先通过路径加载类
    cls = load_object(clspath)

    # Then create an instance of the class
    # 然后创建类的实例
    return await create_instance(
        cls,
        settings,
        crawler,
        *args,
        spider=spider,
        **kwargs
    )
