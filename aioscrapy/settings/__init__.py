"""
Settings module for aioscrapy.
aioscrapy的设置模块。

This module provides classes for managing settings in aioscrapy.
It includes a settings system that supports priorities, type conversion,
and immutable settings.
此模块提供了在aioscrapy中管理设置的类。
它包括一个支持优先级、类型转换和不可变设置的设置系统。
"""

import json
import copy
from collections.abc import MutableMapping
from importlib import import_module
from pprint import pformat

from aioscrapy.settings import default_settings


SETTINGS_PRIORITIES = {
    'default': 0,
    'command': 10,
    'project': 20,
    'spider': 30,
    'cmdline': 40,
}


def get_settings_priority(priority):
    """
    Convert a priority string to its numerical value.
    将优先级字符串转换为其数值。

    This helper function looks up a given string priority in the
    SETTINGS_PRIORITIES dictionary and returns its numerical value,
    or directly returns a given numerical priority.
    此辅助函数在SETTINGS_PRIORITIES字典中查找给定的字符串优先级并返回其数值，
    或直接返回给定的数值优先级。

    Args:
        priority: The priority as a string (e.g., 'default', 'project') or a number.
                 作为字符串（例如，'default'，'project'）或数字的优先级。

    Returns:
        int: The numerical priority value.
             数值优先级值。
    """
    if isinstance(priority, str):
        return SETTINGS_PRIORITIES[priority]
    else:
        return priority


class SettingsAttribute:
    """
    Class for storing data related to settings attributes.
    用于存储与设置属性相关的数据的类。

    This class is intended for internal usage. You should use the Settings class
    for settings configuration, not this one. It stores both the value of a setting
    and its priority.
    此类仅供内部使用。您应该使用Settings类进行设置配置，而不是这个类。
    它存储设置的值和其优先级。

    Attributes:
        value: The value of the setting. 设置的值。
        priority: The priority of the setting. 设置的优先级。
    """

    def __init__(self, value, priority):
        """
        Initialize a SettingsAttribute.
        初始化SettingsAttribute。

        Args:
            value: The value of the setting.
                  设置的值。
            priority: The priority of the setting.
                     设置的优先级。
        """
        self.value = value
        if isinstance(self.value, BaseSettings):
            # If the value is a BaseSettings, use the maximum priority
            # 如果值是BaseSettings，使用最大优先级
            self.priority = max(self.value.maxpriority(), priority)
        else:
            self.priority = priority

    def set(self, value, priority):
        """
        Set the value if the priority is higher or equal than current priority.
        如果优先级高于或等于当前优先级，则设置值。

        Args:
            value: The new value to set.
                  要设置的新值。
            priority: The priority of the new value.
                     新值的优先级。
        """
        if priority >= self.priority:
            if isinstance(self.value, BaseSettings):
                value = BaseSettings(value, priority=priority)
            self.value = value
            self.priority = priority

    def __str__(self):
        """
        Return a string representation of the SettingsAttribute.
        返回SettingsAttribute的字符串表示。

        Returns:
            str: A string representation of the SettingsAttribute.
                 SettingsAttribute的字符串表示。
        """
        return f"<SettingsAttribute value={self.value!r} priority={self.priority}>"

    # Make __repr__ use the same implementation as __str__
    # 使__repr__使用与__str__相同的实现
    __repr__ = __str__


class BaseSettings(MutableMapping):
    """
    Dictionary-like settings container with priority support.
    具有优先级支持的类字典设置容器。

    Instances of this class behave like dictionaries, but store priorities
    along with their (key, value) pairs, and can be frozen (i.e., marked
    immutable).
    此类的实例行为类似于字典，但存储(键, 值)对及其优先级，
    并且可以被冻结（即标记为不可变）。

    Key-value entries can be passed on initialization with the ``values``
    argument, and they would take the ``priority`` level (unless ``values`` is
    already an instance of BaseSettings, in which case the existing priority
    levels will be kept). If the ``priority`` argument is a string, the priority
    name will be looked up in SETTINGS_PRIORITIES. Otherwise, a specific integer
    should be provided.
    可以在初始化时通过``values``参数传递键值条目，它们将采用``priority``级别
    （除非``values``已经是BaseSettings的实例，在这种情况下，将保留现有的优先级）。
    如果``priority``参数是字符串，则将在SETTINGS_PRIORITIES中查找优先级名称。
    否则，应提供特定的整数。

    Once the object is created, new settings can be loaded or updated with the
    ``set`` method, and can be accessed with the square bracket notation of
    dictionaries, or with the ``get`` method of the instance and its value
    conversion variants. When requesting a stored key, the value with the
    highest priority will be retrieved.
    创建对象后，可以使用``set``方法加载或更新新设置，并可以使用字典的方括号表示法
    或实例的``get``方法及其值转换变体进行访问。请求存储的键时，将检索具有最高优先级的值。

    Attributes:
        frozen (bool): Whether the settings are frozen (immutable).
                      设置是否被冻结（不可变）。
        attributes (dict): Dictionary storing the settings as SettingsAttribute objects.
                          存储设置为SettingsAttribute对象的字典。
    """

    def __init__(self, values=None, priority='project'):
        """
        Initialize a BaseSettings instance.
        初始化BaseSettings实例。

        Args:
            values: Initial settings values as a dict or BaseSettings instance.
                   作为字典或BaseSettings实例的初始设置值。
            priority: Priority level for the initial values.
                     初始值的优先级。
        """
        # Start with unfrozen settings
        # 从未冻结的设置开始
        self.frozen = False

        # Initialize empty attributes dictionary
        # 初始化空属性字典
        self.attributes = {}

        # Load initial values if provided
        # 如果提供了初始值，则加载它们
        if values:
            self.update(values, priority)

    def __getitem__(self, opt_name):
        """
        Get a setting value by name.
        通过名称获取设置值。

        Args:
            opt_name: The name of the setting to retrieve.
                     要检索的设置的名称。

        Returns:
            The value of the setting, or None if it doesn't exist.
            设置的值，如果不存在则为None。
        """
        if opt_name not in self:
            return None
        return self.attributes[opt_name].value

    def __contains__(self, name):
        """
        Check if a setting exists.
        检查设置是否存在。

        Args:
            name: The name of the setting to check.
                 要检查的设置的名称。

        Returns:
            bool: True if the setting exists, False otherwise.
                 如果设置存在则为True，否则为False。
        """
        return name in self.attributes

    def get(self, name, default=None):
        """
        Get a setting value without affecting its original type.
        获取设置值而不影响其原始类型。

        Args:
            name: The setting name.
                 设置名称。
            default: The value to return if no setting is found.
                    如果未找到设置，则返回的值。

        Returns:
            The value of the setting, or the default value if not found.
            设置的值，如果未找到则为默认值。
        """
        return self[name] if self[name] is not None else default

    def getbool(self, name, default=False):
        """
        Get a setting value as a boolean.
        将设置值作为布尔值获取。

        ``1``, ``'1'``, ``True`` and ``'True'`` return ``True``,
        while ``0``, ``'0'``, ``False``, ``'False'`` and ``None`` return ``False``.
        ``1``、``'1'``、``True``和``'True'``返回``True``，
        而``0``、``'0'``、``False``、``'False'``和``None``返回``False``。

        For example, settings populated through environment variables set to
        ``'0'`` will return ``False`` when using this method.
        例如，通过环境变量设置为``'0'``的设置在使用此方法时将返回``False``。

        Args:
            name: The setting name.
                 设置名称。
            default: The value to return if no setting is found.
                    如果未找到设置，则返回的值。

        Returns:
            bool: The boolean value of the setting.
                 设置的布尔值。

        Raises:
            ValueError: If the value cannot be converted to a boolean.
                       如果值无法转换为布尔值。
        """
        got = self.get(name, default)
        try:
            # Try to convert to int first, then to bool
            # 首先尝试转换为int，然后转换为bool
            return bool(int(got))
        except ValueError:
            # Handle string boolean values
            # 处理字符串布尔值
            if got in ("True", "true"):
                return True
            if got in ("False", "false"):
                return False
            raise ValueError("Supported values for boolean settings "
                             "are 0/1, True/False, '0'/'1', "
                             "'True'/'False' and 'true'/'false'")

    def getint(self, name, default=0):
        """
        Get a setting value as an int.
        将设置值作为整数获取。

        Args:
            name: The setting name.
                 设置名称。
            default: The value to return if no setting is found.
                    如果未找到设置，则返回的值。

        Returns:
            int: The integer value of the setting.
                 设置的整数值。

        Raises:
            ValueError: If the value cannot be converted to an int.
                       如果值无法转换为整数。
        """
        return int(self.get(name, default))

    def getfloat(self, name, default=0.0):
        """
        Get a setting value as a float.
        将设置值作为浮点数获取。

        Args:
            name: The setting name.
                 设置名称。
            default: The value to return if no setting is found.
                    如果未找到设置，则返回的值。

        Returns:
            float: The float value of the setting.
                  设置的浮点值。

        Raises:
            ValueError: If the value cannot be converted to a float.
                       如果值无法转换为浮点数。
        """
        return float(self.get(name, default))

    def getlist(self, name, default=None):
        """
        Get a setting value as a list.
        将设置值作为列表获取。

        If the setting original type is a list, a copy of it will be returned.
        If it's a string it will be split by ",".
        如果设置的原始类型是列表，将返回其副本。
        如果是字符串，将按","拆分。

        For example, settings populated through environment variables set to
        ``'one,two'`` will return a list ['one', 'two'] when using this method.
        例如，通过环境变量设置为``'one,two'``的设置在使用此方法时将返回列表['one', 'two']。

        Args:
            name: The setting name.
                 设置名称。
            default: The value to return if no setting is found.
                    如果未找到设置，则返回的值。

        Returns:
            list: The list value of the setting.
                 设置的列表值。
        """
        value = self.get(name, default or [])
        if isinstance(value, str):
            value = value.split(',')
        return list(value)

    def getdict(self, name, default=None):
        """
        Get a setting value as a dictionary.
        将设置值作为字典获取。

        If the setting original type is a dictionary, a copy of it will be returned.
        If it is a string it will be evaluated as a JSON dictionary.
        In the case that it is a BaseSettings instance itself, it will be
        converted to a dictionary, containing all its current settings values
        as they would be returned by get, and losing all information about
        priority and mutability.
        如果设置的原始类型是字典，将返回其副本。
        如果是字符串，将被评估为JSON字典。
        如果它本身是BaseSettings实例，它将被转换为字典，包含所有当前设置值，
        就像它们由get返回一样，并丢失有关优先级和可变性的所有信息。

        Args:
            name: The setting name.
                 设置名称。
            default: The value to return if no setting is found.
                    如果未找到设置，则返回的值。

        Returns:
            dict: The dictionary value of the setting.
                 设置的字典值。

        Raises:
            ValueError: If the string value cannot be parsed as JSON.
                       如果字符串值无法解析为JSON。
        """
        value = self.get(name, default or {})
        if isinstance(value, str):
            value = json.loads(value)
        return dict(value)

    def getwithbase(self, name):
        """
        Get a composition of a dictionary-like setting and its base variants.
        获取字典类设置及其基础变体的组合。

        This method creates a new BaseSettings instance that combines three settings:
        name + '_BASE', name, and name + '_SPIDER', with increasing priority.
        此方法创建一个新的BaseSettings实例，它结合了三个设置：
        name + '_BASE'、name和name + '_SPIDER'，优先级依次增加。

        This is useful for settings that have base values and spider-specific overrides,
        such as middlewares and extensions.
        这对于具有基本值和爬虫特定覆盖的设置很有用，例如中间件和扩展。

        Args:
            name: Name of the dictionary-like setting without the '_BASE' or '_SPIDER' suffix.
                 不带'_BASE'或'_SPIDER'后缀的字典类设置的名称。

        Returns:
            BaseSettings: A new BaseSettings instance with the combined settings.
                         包含组合设置的新BaseSettings实例。
        """
        compbs = BaseSettings()
        compbs.update(self[name + '_BASE'])
        compbs.update(self[name])
        compbs.update(self[name + '_SPIDER'])
        return compbs

    def getpriority(self, name):
        """
        Return the current numerical priority value of a setting.
        返回设置的当前数值优先级。

        This method returns the priority of a setting, which determines whether
        the setting can be overridden by other settings with different priorities.
        此方法返回设置的优先级，它决定了该设置是否可以被具有不同优先级的其他设置覆盖。

        Args:
            name: The name of the setting.
                 设置的名称。

        Returns:
            int or None: The numerical priority value of the setting, or None if the setting doesn't exist.
                        设置的数值优先级，如果设置不存在则为None。
        """
        if name not in self:
            return None
        return self.attributes[name].priority

    def maxpriority(self):
        """
        Return the highest priority value among all settings.
        返回所有设置中的最高优先级值。

        This method scans through all settings and returns the highest priority value.
        If there are no settings stored, it returns the priority value for 'default'.
        此方法扫描所有设置并返回最高优先级值。
        如果没有存储设置，则返回'default'的优先级值。

        Returns:
            int: The highest priority value among all settings, or the priority value for 'default'
                if there are no settings.
                所有设置中的最高优先级值，如果没有设置则为'default'的优先级值。
        """
        if len(self) > 0:
            return max(self.getpriority(name) for name in self)
        else:
            return get_settings_priority('default')

    def __setitem__(self, name, value):
        self.set(name, value)

    def set(self, name, value, priority='project'):
        """
        Store a key/value attribute with a given priority.
        存储具有给定优先级的键/值属性。

        This method sets a setting with the specified name, value, and priority.
        If a setting with the same name already exists, it will be updated only
        if the new priority is equal to or higher than the existing priority.
        此方法设置具有指定名称、值和优先级的设置。
        如果已存在同名设置，则仅当新优先级等于或高于现有优先级时才会更新。

        Settings should be populated *before* configuring the Crawler object,
        otherwise they won't have any effect.
        应在配置Crawler对象之前填充设置，否则它们将不会产生任何效果。

        Args:
            name: The setting name.
                 设置名称。
            value: The value to associate with the setting.
                  与设置关联的值。
            priority: The priority of the setting. Should be a key of
                     SETTINGS_PRIORITIES or an integer.
                     设置的优先级。应该是SETTINGS_PRIORITIES的键或整数。

        Raises:
            TypeError: If the settings object is frozen (immutable).
                      如果设置对象被冻结（不可变）。
        """
        self._assert_mutability()
        priority = get_settings_priority(priority)
        if name not in self:
            # If the setting doesn't exist, create a new SettingsAttribute
            # 如果设置不存在，创建一个新的SettingsAttribute
            if isinstance(value, SettingsAttribute):
                self.attributes[name] = value
            else:
                self.attributes[name] = SettingsAttribute(value, priority)
        else:
            # If the setting exists, update it with the new value and priority
            # 如果设置存在，使用新的值和优先级更新它
            self.attributes[name].set(value, priority)

    def setdict(self, values, priority='project'):
        self.update(values, priority)

    def setmodule(self, module, priority='project'):
        """
        Store settings from a module with a given priority.
        以给定优先级存储来自模块的设置。

        This is a helper function that calls set() for every globally declared
        uppercase variable of the module with the provided priority.
        这是一个辅助函数，它为模块的每个全局声明的大写变量调用set()，并使用提供的优先级。

        This is commonly used to load settings from a settings module.
        这通常用于从设置模块加载设置。

        Args:
            module: The module or the path of the module.
                   模块或模块的路径。
            priority: The priority of the settings. Should be a key of
                     SETTINGS_PRIORITIES or an integer.
                     设置的优先级。应该是SETTINGS_PRIORITIES的键或整数。

        Raises:
            TypeError: If the settings object is frozen (immutable).
                      如果设置对象被冻结（不可变）。
            ImportError: If the module path cannot be imported.
                        如果无法导入模块路径。
        """
        self._assert_mutability()
        if isinstance(module, str):
            # If module is a string, import it
            # 如果模块是字符串，导入它
            module = import_module(module)

        # Set all uppercase variables from the module
        # 设置模块中的所有大写变量
        for key in dir(module):
            if key.isupper():
                self.set(key, getattr(module, key), priority)

    def update(self, values, priority='project'):
        """
        Store key/value pairs with a given priority.
        以给定优先级存储键/值对。

        This is a helper function that calls set() for every item of values
        with the provided priority.
        这是一个辅助函数，它为values的每个项目调用set()，并使用提供的优先级。

        If values is a string, it is assumed to be JSON-encoded and parsed
        into a dict with json.loads() first. If it is a BaseSettings instance,
        the per-key priorities will be used and the priority parameter ignored.
        This allows inserting/updating settings with different priorities with
        a single command.
        如果values是字符串，则假定它是JSON编码的，并首先使用json.loads()解析为字典。
        如果它是BaseSettings实例，则将使用每个键的优先级，并忽略priority参数。
        这允许使用单个命令插入/更新具有不同优先级的设置。

        Args:
            values: The settings names and values.
                   设置名称和值。
                   Can be a dict, a JSON string, or a BaseSettings instance.
                   可以是字典、JSON字符串或BaseSettings实例。
            priority: The priority of the settings. Should be a key of
                     SETTINGS_PRIORITIES or an integer.
                     设置的优先级。应该是SETTINGS_PRIORITIES的键或整数。

        Raises:
            TypeError: If the settings object is frozen (immutable).
                      如果设置对象被冻结（不可变）。
            ValueError: If values is a string that cannot be parsed as JSON.
                       如果values是无法解析为JSON的字符串。
        """
        self._assert_mutability()
        if isinstance(values, str):
            # Parse JSON string into a dict
            # 将JSON字符串解析为字典
            values = json.loads(values)

        if values is not None:
            if isinstance(values, BaseSettings):
                # If values is a BaseSettings, use its per-key priorities
                # 如果values是BaseSettings，使用其每个键的优先级
                for name, value in values.items():
                    self.set(name, value, values.getpriority(name))
            else:
                # Otherwise, use the provided priority for all items
                # 否则，对所有项目使用提供的优先级
                for name, value in values.items():
                    self.set(name, value, priority)

    def delete(self, name, priority='project'):
        """
        Delete a setting if the given priority is higher or equal than its priority.
        如果给定优先级高于或等于设置的优先级，则删除该设置。

        This method deletes a setting with the specified name if the provided
        priority is higher than or equal to the setting's priority.
        此方法删除具有指定名称的设置，如果提供的优先级高于或等于设置的优先级。

        Args:
            name: The name of the setting to delete.
                 要删除的设置的名称。
            priority: The priority level. Should be a key of SETTINGS_PRIORITIES or an integer.
                     优先级级别。应该是SETTINGS_PRIORITIES的键或整数。

        Raises:
            TypeError: If the settings object is frozen (immutable).
                      如果设置对象被冻结（不可变）。
        """
        self._assert_mutability()
        priority = get_settings_priority(priority)
        if priority >= self.getpriority(name):
            del self.attributes[name]

    def __delitem__(self, name):
        self._assert_mutability()
        del self.attributes[name]

    def _assert_mutability(self):
        """
        Assert that the settings object is mutable.
        断言设置对象是可变的。

        This internal method checks if the settings object is frozen (immutable)
        and raises a TypeError if it is.
        此内部方法检查设置对象是否被冻结（不可变），如果是则引发TypeError。

        Raises:
            TypeError: If the settings object is frozen (immutable).
                      如果设置对象被冻结（不可变）。
        """
        if self.frozen:
            raise TypeError("Trying to modify an immutable Settings object")

    def copy(self):
        """
        Make a deep copy of current settings.
        创建当前设置的深拷贝。

        This method returns a new instance of the BaseSettings class,
        populated with the same values and their priorities.
        此方法返回BaseSettings类的新实例，填充相同的值及其优先级。

        Modifications to the new object won't be reflected on the original
        settings, and vice versa.
        对新对象的修改不会反映在原始设置上，反之亦然。

        Returns:
            BaseSettings: A new instance with the same settings and priorities.
                         具有相同设置和优先级的新实例。
        """
        return copy.deepcopy(self)

    def freeze(self):
        """
        Disable further changes to the current settings.
        禁止对当前设置进行进一步更改。

        After calling this method, the present state of the settings will become
        immutable. Trying to change values through the set() method and
        its variants won't be possible and will raise a TypeError.
        调用此方法后，设置的当前状态将变为不可变。
        尝试通过set()方法及其变体更改值将不可能，并将引发TypeError。

        Returns:
            None
        """
        self.frozen = True

    def frozencopy(self):
        """
        Return an immutable copy of the current settings.
        返回当前设置的不可变副本。

        This method creates a copy of the current settings and then freezes it,
        making it immutable.
        此方法创建当前设置的副本，然后冻结它，使其不可变。

        It's equivalent to calling copy() followed by freeze().
        它相当于调用copy()后跟freeze()。

        Returns:
            BaseSettings: An immutable copy of the current settings.
                         当前设置的不可变副本。
        """
        settings_copy = self.copy()
        settings_copy.freeze()
        return settings_copy

    def __iter__(self):
        return iter(self.attributes)

    def __len__(self):
        return len(self.attributes)

    def _to_dict(self):
        """
        Internal method to convert settings to a dictionary.
        将设置转换为字典的内部方法。

        This method recursively converts BaseSettings instances to dictionaries.
        此方法递归地将BaseSettings实例转换为字典。

        Returns:
            dict: A dictionary representation of the settings.
                 设置的字典表示。
        """
        return {k: (v._to_dict() if isinstance(v, BaseSettings) else v)
                for k, v in self.items()}

    def copy_to_dict(self):
        """
        Make a copy of current settings and convert to a dict.
        创建当前设置的副本并转换为字典。

        This method returns a new dict populated with the same values
        as the current settings, with nested BaseSettings also converted to dicts.
        此方法返回一个新字典，填充与当前设置相同的值，嵌套的BaseSettings也转换为字典。

        Modifications to the returned dict won't be reflected on the original
        settings, and vice versa.
        对返回的字典的修改不会反映在原始设置上，反之亦然。

        This method can be useful for example for printing settings
        or for serialization.
        此方法例如对于打印设置或序列化很有用。

        Returns:
            dict: A dictionary representation of the settings.
                 设置的字典表示。
        """
        settings = self.copy()
        return settings._to_dict()

    def _repr_pretty_(self, p, cycle):
        """
        Pretty-printing support for IPython/Jupyter.
        IPython/Jupyter的美观打印支持。

        This method is called by IPython/Jupyter to format the object for display.
        此方法由IPython/Jupyter调用，用于格式化对象以供显示。

        Args:
            p: The pretty printer instance.
               美观打印器实例。
            cycle: Whether a cycle was detected in the object graph.
                  是否在对象图中检测到循环。

        Returns:
            None
        """
        if cycle:
            # If a cycle is detected, use the standard repr
            # 如果检测到循环，使用标准的repr
            p.text(repr(self))
        else:
            # Otherwise, format the settings as a pretty-printed dict
            # 否则，将设置格式化为美观打印的字典
            p.text(pformat(self.copy_to_dict()))


class _DictProxy(MutableMapping):
    """
    Dictionary proxy that updates settings when modified.
    修改时更新设置的字典代理。

    This class is used internally to provide a dictionary-like interface
    that updates settings with a specific priority when modified.
    此类在内部用于提供类字典接口，在修改时以特定优先级更新设置。
    """

    def __init__(self, settings, priority):
        """
        Initialize a _DictProxy.
        初始化_DictProxy。

        Args:
            settings: The settings object to update.
                     要更新的设置对象。
            priority: The priority to use when updating settings.
                     更新设置时使用的优先级。
        """
        self.o = {}
        self.settings = settings
        self.priority = priority

    def __len__(self):
        """
        Return the number of items in the dictionary.
        返回字典中的项目数。

        Returns:
            int: The number of items in the dictionary.
                 字典中的项目数。
        """
        return len(self.o)

    def __getitem__(self, k):
        """
        Get an item from the dictionary.
        从字典中获取项目。

        Args:
            k: The key to get.
               要获取的键。

        Returns:
            The value for the key.
            键的值。

        Raises:
            KeyError: If the key is not found.
                     如果未找到键。
        """
        return self.o[k]

    def __setitem__(self, k, v):
        """
        Set an item in the dictionary and update the settings.
        在字典中设置项目并更新设置。

        Args:
            k: The key to set.
               要设置的键。
            v: The value to set.
               要设置的值。
        """
        self.settings.set(k, v, priority=self.priority)
        self.o[k] = v

    def __delitem__(self, k):
        """
        Delete an item from the dictionary.
        从字典中删除项目。

        Args:
            k: The key to delete.
               要删除的键。

        Raises:
            KeyError: If the key is not found.
                     如果未找到键。
        """
        del self.o[k]

    def __iter__(self):
        """
        Return an iterator over the dictionary keys.
        返回字典键的迭代器。

        Returns:
            iterator: An iterator over the dictionary keys.
                     字典键的迭代器。
        """
        return iter(self.o)


class Settings(BaseSettings):
    """
    Settings container for aioscrapy with default settings.
    具有默认设置的aioscrapy设置容器。

    This object stores aioscrapy settings for the configuration of internal
    components, and can be used for any further customization.
    此对象存储用于配置内部组件的aioscrapy设置，可用于任何进一步的自定义。

    It is a direct subclass and supports all methods of BaseSettings.
    Additionally, after instantiation of this class, the new object will
    have the global default settings from default_settings already populated.
    它是BaseSettings的直接子类，支持BaseSettings的所有方法。
    此外，在实例化此类后，新对象将已经填充了来自default_settings的全局默认设置。

    Attributes:
        frozen (bool): Whether the settings are frozen (immutable).
                      设置是否被冻结（不可变）。
        attributes (dict): Dictionary storing the settings as SettingsAttribute objects.
                          存储设置为SettingsAttribute对象的字典。
    """

    def __init__(self, values=None, priority='project'):
        """
        Initialize a Settings instance with default settings.
        使用默认设置初始化Settings实例。

        Args:
            values: Initial settings values as a dict or BaseSettings instance.
                   作为字典或BaseSettings实例的初始设置值。
            priority: Priority level for the initial values.
                     初始值的优先级。
        """
        # Do not pass kwarg values here. We don't want to promote user-defined
        # dicts, and we want to update, not replace, default dicts with the
        # values given by the user
        # 不要在这里传递kwarg值。我们不想提升用户定义的字典，
        # 我们想用用户给定的值更新默认字典，而不是替换它们
        super().__init__()

        # Load default settings with 'default' priority
        # 加载具有'default'优先级的默认设置
        self.setmodule(default_settings, 'default')

        # Promote default dictionaries to BaseSettings instances for per-key priorities
        # 将默认字典提升为BaseSettings实例以实现每个键的优先级
        for name, val in self.items():
            if isinstance(val, dict):
                self.set(name, BaseSettings(val, 'default'), 'default')

        # Update with user-provided values
        # 使用用户提供的值更新
        self.update(values, priority)


def iter_default_settings():
    """
    Return the default settings as an iterator.
    将默认设置作为迭代器返回。

    This function iterates through all uppercase attributes in the default_settings
    module and yields them as (name, value) tuples.
    此函数遍历default_settings模块中的所有大写属性，并将它们作为(名称, 值)元组生成。

    Returns:
        iterator: An iterator of (name, value) tuples of default settings.
                 默认设置的(名称, 值)元组的迭代器。
    """
    for name in dir(default_settings):
        if name.isupper():
            yield name, getattr(default_settings, name)


def overridden_settings(settings):
    """
    Return a dict of the settings that have been overridden.
    返回已被覆盖的设置的字典。

    This function compares the values in the provided settings object with
    the default values and yields the ones that have been changed.
    此函数将提供的设置对象中的值与默认值进行比较，并生成已更改的值。

    Args:
        settings: The settings object to check.
                 要检查的设置对象。

    Returns:
        iterator: An iterator of (name, value) tuples of overridden settings.
                 已覆盖设置的(名称, 值)元组的迭代器。
    """
    for name, defvalue in iter_default_settings():
        value = settings[name]
        if not isinstance(defvalue, dict) and value != defvalue:
            yield name, value
