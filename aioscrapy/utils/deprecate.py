"""
Deprecation utilities for aioscrapy.
aioscrapy的弃用实用工具。

This module provides utility functions and classes for handling deprecation in aioscrapy.
It includes tools for creating deprecation warnings, creating deprecated classes,
and updating class paths to their new locations.
此模块提供了用于处理aioscrapy中弃用的实用函数和类。
它包括用于创建弃用警告、创建已弃用类以及将类路径更新到其新位置的工具。
"""

import inspect
import warnings

from aioscrapy.exceptions import AioScrapyDeprecationWarning


def attribute(obj, oldattr, newattr, version='0.12'):
    """
    Issue a deprecation warning for an attribute that has been renamed.
    为已重命名的属性发出弃用警告。

    This function issues a deprecation warning when code accesses an old attribute
    that has been renamed. It helps guide users to update their code to use the
    new attribute name.
    当代码访问已重命名的旧属性时，此函数会发出弃用警告。
    它有助于指导用户更新其代码以使用新的属性名称。

    Args:
        obj: The object containing the deprecated attribute.
             包含已弃用属性的对象。
        oldattr: The name of the deprecated attribute.
                已弃用属性的名称。
        newattr: The name of the attribute that should be used instead.
                应该使用的属性的名称。
        version: The version of aioscrapy in which the old attribute will be removed.
                将删除旧属性的aioscrapy版本。
                Defaults to '0.12'.
                默认为'0.12'。

    Example:
        >>> class MyClass:
        ...     def __getattr__(self, name):
        ...         if name == 'old_name':
        ...             attribute(self, 'old_name', 'new_name')
        ...             return self.new_name
        ...         raise AttributeError(f"{self.__class__.__name__} has no attribute {name}")
        ...
        ...     @property
        ...     def new_name(self):
        ...         return "value"
    """
    # Get the class name of the object
    # 获取对象的类名
    cname = obj.__class__.__name__

    # Issue a deprecation warning with information about the old and new attributes
    # 发出包含有关旧属性和新属性信息的弃用警告
    warnings.warn(
        f"{cname}.{oldattr} attribute is deprecated and will be no longer supported "
        f"in Aioscrapy {version}, use {cname}.{newattr} attribute instead",
        AioScrapyDeprecationWarning,
        stacklevel=3)  # Use stacklevel=3 to point to the caller's caller


def create_deprecated_class(
    name,
    new_class,
    clsdict=None,
    warn_category=AioScrapyDeprecationWarning,
    warn_once=True,
    old_class_path=None,
    new_class_path=None,
    subclass_warn_message="{cls} inherits from deprecated class {old}, please inherit from {new}.",
    instance_warn_message="{cls} is deprecated, instantiate {new} instead."
):
    """
    Create a deprecated class that redirects to a new class.
    创建一个重定向到新类的已弃用类。

    This function creates a "deprecated" class that issues warnings when:
    1. A user subclasses from the deprecated class
    2. A user instantiates the deprecated class directly

    此函数创建一个"已弃用"类，在以下情况下发出警告：
    1. 用户从已弃用的类继承
    2. 用户直接实例化已弃用的类

    The deprecated class acts as a proxy to the new class, so:
    - Subclasses of the new class are considered subclasses of the deprecated class
    - isinstance() and issubclass() checks work as expected
    - The deprecated class can be instantiated and will create instances of the new class

    已弃用的类充当新类的代理，因此：
    - 新类的子类被视为已弃用类的子类
    - isinstance()和issubclass()检查按预期工作
    - 可以实例化已弃用的类，它将创建新类的实例

    This is particularly useful when renaming or moving classes in a library
    while maintaining backward compatibility.

    当在保持向后兼容性的同时重命名或移动库中的类时，这特别有用。

    Args:
        name: Name of the deprecated class.
              已弃用类的名称。
        new_class: The class that should be used instead.
                  应该使用的类。
        clsdict: Additional attributes to add to the deprecated class.
                要添加到已弃用类的其他属性。
                Defaults to None.
                默认为None。
        warn_category: Warning category to use.
                      要使用的警告类别。
                      Defaults to AioScrapyDeprecationWarning.
                      默认为AioScrapyDeprecationWarning。
        warn_once: Whether to warn only once when a subclass inherits from the deprecated class.
                  当子类从已弃用的类继承时是否只警告一次。
                  Defaults to True.
                  默认为True。
        old_class_path: Full import path of the old class (for better warning messages).
                       旧类的完整导入路径（用于更好的警告消息）。
                       Defaults to None.
                       默认为None。
        new_class_path: Full import path of the new class (for better warning messages).
                       新类的完整导入路径（用于更好的警告消息）。
                       Defaults to None.
                       默认为None。
        subclass_warn_message: Warning message template when a class inherits from the deprecated class.
                              当类从已弃用的类继承时的警告消息模板。
                              Defaults to "{cls} inherits from deprecated class {old}, please inherit from {new}.".
                              默认为"{cls} inherits from deprecated class {old}, please inherit from {new}."。
        instance_warn_message: Warning message template when the deprecated class is instantiated.
                              当实例化已弃用的类时的警告消息模板。
                              Defaults to "{cls} is deprecated, instantiate {new} instead.".
                              默认为"{cls} is deprecated, instantiate {new} instead."。

    Returns:
        type: A deprecated class that proxies to the new class.
              代理到新类的已弃用类。

    Example:
        >>> class OldName(SomeClass):
        ...     # ...
        ...
        >>> class NewName(SomeClass):
        ...     # ...
        ...
        >>> OldName = create_deprecated_class('OldName', NewName)
        >>>
        >>> # The following will issue a warning but still work:
        >>> class UserClass(OldName):
        ...     pass
        ...
        >>> # This will also issue a warning but create a NewName instance:
        >>> instance = OldName()
        >>>
        >>> # These will return True:
        >>> issubclass(UserClass, OldName)
        >>> issubclass(UserClass, NewName)
        >>> isinstance(instance, OldName)
        >>> isinstance(instance, NewName)
    """

    class DeprecatedClass(new_class.__class__):

        deprecated_class = None
        warned_on_subclass = False

        def __new__(metacls, name, bases, clsdict_):
            cls = super().__new__(metacls, name, bases, clsdict_)
            if metacls.deprecated_class is None:
                metacls.deprecated_class = cls
            return cls

        def __init__(cls, name, bases, clsdict_):
            meta = cls.__class__
            old = meta.deprecated_class
            if old in bases and not (warn_once and meta.warned_on_subclass):
                meta.warned_on_subclass = True
                msg = subclass_warn_message.format(cls=_clspath(cls),
                                                   old=_clspath(old, old_class_path),
                                                   new=_clspath(new_class, new_class_path))
                if warn_once:
                    msg += ' (warning only on first subclass, there may be others)'
                warnings.warn(msg, warn_category, stacklevel=2)
            super().__init__(name, bases, clsdict_)

        # see https://www.python.org/dev/peps/pep-3119/#overloading-isinstance-and-issubclass
        # and https://docs.python.org/reference/datamodel.html#customizing-instance-and-subclass-checks
        # for implementation details
        def __instancecheck__(cls, inst):
            return any(cls.__subclasscheck__(c)
                       for c in {type(inst), inst.__class__})

        def __subclasscheck__(cls, sub):
            if cls is not DeprecatedClass.deprecated_class:
                # we should do the magic only if second `issubclass` argument
                # is the deprecated class itself - subclasses of the
                # deprecated class should not use custom `__subclasscheck__`
                # method.
                return super().__subclasscheck__(sub)

            if not inspect.isclass(sub):
                raise TypeError("issubclass() arg 1 must be a class")

            mro = getattr(sub, '__mro__', ())
            return any(c in {cls, new_class} for c in mro)

        def __call__(cls, *args, **kwargs):
            old = DeprecatedClass.deprecated_class
            if cls is old:
                msg = instance_warn_message.format(cls=_clspath(cls, old_class_path),
                                                   new=_clspath(new_class, new_class_path))
                warnings.warn(msg, warn_category, stacklevel=2)
            return super().__call__(*args, **kwargs)

    deprecated_cls = DeprecatedClass(name, (new_class,), clsdict or {})

    try:
        frm = inspect.stack()[1]
        parent_module = inspect.getmodule(frm[0])
        if parent_module is not None:
            deprecated_cls.__module__ = parent_module.__name__
    except Exception as e:
        # Sometimes inspect.stack() fails (e.g. when the first import of
        # deprecated class is in jinja2 template). __module__ attribute is not
        # important enough to raise an exception as users may be unable
        # to fix inspect.stack() errors.
        warnings.warn(f"Error detecting parent module: {e!r}")

    return deprecated_cls


def _clspath(cls, forced=None):
    """
    Get the full import path of a class.
    获取类的完整导入路径。

    This internal helper function returns the full import path of a class
    (module name + class name). It's used to generate informative deprecation
    warning messages.
    这个内部辅助函数返回类的完整导入路径（模块名+类名）。
    它用于生成信息丰富的弃用警告消息。

    Args:
        cls: The class to get the path for.
             要获取路径的类。
        forced: An optional string to use instead of the actual class path.
               可选的字符串，用于替代实际的类路径。
               Defaults to None.
               默认为None。

    Returns:
        str: The full import path of the class (e.g., 'package.module.ClassName')
             or the forced path if provided.
             类的完整导入路径（例如，'package.module.ClassName'）
             或者如果提供了forced参数，则返回forced路径。
    """
    # If a forced path is provided, use it instead of calculating the path
    # 如果提供了强制路径，则使用它而不是计算路径
    if forced is not None:
        return forced

    # Otherwise, construct the path from the module and class name
    # 否则，从模块和类名构造路径
    return f'{cls.__module__}.{cls.__name__}'


# List of (prefix, replacement) tuples for updating deprecated class paths
# Each rule specifies a prefix to match and its replacement for updating import paths
# 用于更新已弃用类路径的(前缀, 替换)元组列表
# 每个规则指定要匹配的前缀及其替换，用于更新导入路径
DEPRECATION_RULES = []


def update_classpath(path):
    """
    Update a deprecated class path to its new location.
    将已弃用的类路径更新到其新位置。

    This function checks if a given import path matches any of the known
    deprecated paths (defined in DEPRECATION_RULES) and returns the updated
    path if a match is found. It also issues a deprecation warning.
    此函数检查给定的导入路径是否匹配任何已知的已弃用路径
    （在DEPRECATION_RULES中定义），如果找到匹配项，则返回更新的路径。
    它还会发出弃用警告。

    This is useful for handling cases where classes have been moved to
    different modules or packages.
    这对于处理类已移动到不同模块或包的情况很有用。

    Args:
        path: The import path to check and potentially update.
              要检查和可能更新的导入路径。

    Returns:
        str: The updated path if the input path matches a deprecated path,
             otherwise the original path.
             如果输入路径匹配已弃用路径，则返回更新的路径，
             否则返回原始路径。

    Example:
        >>> # Add a deprecation rule
        >>> DEPRECATION_RULES.append(('old.module', 'new.module'))
        >>>
        >>> # This will return 'new.module.MyClass' and issue a warning
        >>> update_classpath('old.module.MyClass')
        'new.module.MyClass'
        >>>
        >>> # This will return the original path unchanged
        >>> update_classpath('other.module.MyClass')
        'other.module.MyClass'
    """
    # Check each deprecation rule to see if the path matches
    # 检查每个弃用规则，看路径是否匹配
    for prefix, replacement in DEPRECATION_RULES:
        # Only process string paths that start with the deprecated prefix
        # 只处理以已弃用前缀开头的字符串路径
        if isinstance(path, str) and path.startswith(prefix):
            # Replace the deprecated prefix with its replacement (only the first occurrence)
            # 将已弃用的前缀替换为其替换（仅第一次出现）
            new_path = path.replace(prefix, replacement, 1)

            # Issue a deprecation warning
            # 发出弃用警告
            warnings.warn(f"`{path}` class is deprecated, use `{new_path}` instead",
                          AioScrapyDeprecationWarning)

            return new_path

    # If no rules matched, return the original path unchanged
    # 如果没有规则匹配，则原样返回原始路径
    return path
