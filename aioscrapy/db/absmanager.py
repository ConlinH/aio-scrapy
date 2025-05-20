"""
Abstract database pool manager for aioscrapy.
aioscrapy的抽象数据库池管理器。

This module defines the abstract base class for all database pool managers
in aioscrapy. It specifies the interface that all database managers must implement.
此模块定义了aioscrapy中所有数据库池管理器的抽象基类。
它指定了所有数据库管理器必须实现的接口。
"""

from abc import ABCMeta, abstractmethod

import aioscrapy


class AbsDBPoolManager(object, metaclass=ABCMeta):
    """
    Abstract base class for database connection pool managers.
    数据库连接池管理器的抽象基类。

    This class defines the interface that all database pool managers must implement.
    It provides methods for creating, accessing, and closing connection pools,
    as well as initializing pools from settings or configuration dictionaries.
    此类定义了所有数据库池管理器必须实现的接口。
    它提供了创建、访问和关闭连接池的方法，以及从设置或配置字典初始化池的方法。
    """

    @property
    @abstractmethod
    def _clients(self) -> dict:
        """
        Dictionary of connection pools managed by this manager.
        此管理器管理的连接池字典。

        This property should return a dictionary mapping aliases to connection pools.
        Subclasses must implement this property.
        此属性应返回将别名映射到连接池的字典。
        子类必须实现此属性。

        Returns:
            dict: A dictionary mapping aliases to connection pools.
                 将别名映射到连接池的字典。
        """
        return {}

    @abstractmethod
    async def create(self, alias: str, params: dict):
        """
        Create a new connection pool.
        创建新的连接池。

        This method creates a new connection pool with the given alias and parameters.
        Subclasses must implement this method.
        此方法使用给定的别名和参数创建新的连接池。
        子类必须实现此方法。

        Args:
            alias: The alias for the new connection pool.
                  新连接池的别名。
            params: The parameters for creating the connection pool.
                   创建连接池的参数。

        Returns:
            The created connection pool.
            创建的连接池。
        """

    @abstractmethod
    def get_pool(self, alias: str):
        """
        Get a connection pool by its alias.
        通过别名获取连接池。

        This method retrieves an existing connection pool with the given alias.
        Subclasses must implement this method.
        此方法检索具有给定别名的现有连接池。
        子类必须实现此方法。

        Args:
            alias: The alias of the connection pool to retrieve.
                  要检索的连接池的别名。

        Returns:
            The connection pool with the given alias.
            具有给定别名的连接池。

        Raises:
            KeyError: If no connection pool exists with the given alias.
                     如果不存在具有给定别名的连接池。
        """

    @abstractmethod
    async def close_all(self):
        """
        Close all connection pools.
        关闭所有连接池。

        This method closes all connection pools managed by this manager.
        Subclasses must implement this method.
        此方法关闭此管理器管理的所有连接池。
        子类必须实现此方法。

        Returns:
            None
        """

    @abstractmethod
    async def close(self, alias: str):
        """
        Close a specific connection pool.
        关闭特定的连接池。

        This method closes the connection pool with the given alias.
        Subclasses must implement this method.
        此方法关闭具有给定别名的连接池。
        子类必须实现此方法。

        Args:
            alias: The alias of the connection pool to close.
                  要关闭的连接池的别名。

        Returns:
            None

        Raises:
            KeyError: If no connection pool exists with the given alias.
                     如果不存在具有给定别名的连接池。
        """

    @abstractmethod
    async def from_dict(self, db_args: dict):
        """
        Initialize connection pools from a configuration dictionary.
        从配置字典初始化连接池。

        This method creates connection pools based on the configuration in db_args.
        Subclasses must implement this method.
        此方法根据db_args中的配置创建连接池。
        子类必须实现此方法。

        Args:
            db_args: A dictionary mapping aliases to connection parameters.
                    将别名映射到连接参数的字典。
                    Example:
                    {
                        'default': {'host': 'localhost', 'port': 6379},
                        'cache': {'host': 'cache.example.com', 'port': 6379}
                    }

        Returns:
            None
        """

    @abstractmethod
    async def from_settings(self, settings: aioscrapy.Settings):
        """
        Initialize connection pools from aioscrapy settings.
        从aioscrapy设置初始化连接池。

        This method creates connection pools based on the configuration in settings.
        Subclasses must implement this method.
        此方法根据settings中的配置创建连接池。
        子类必须实现此方法。

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """

    async def from_crawler(self, crawler: "aioscrapy.Crawler"):
        """
        Initialize connection pools from a crawler.
        从爬虫初始化连接池。

        This is a convenience method that extracts settings from the crawler
        and calls from_settings.
        这是一个便捷方法，它从爬虫中提取设置并调用from_settings。

        Args:
            crawler: The aioscrapy crawler instance.
                    aioscrapy爬虫实例。

        Returns:
            None
        """
        return await self.from_settings(crawler.settings)

    def __call__(self, alias: str):
        """
        Make the manager callable to get a connection pool.
        使管理器可调用以获取连接池。

        This method allows using the manager as a function to get a connection pool:
        manager('default')
        此方法允许将管理器用作函数以获取连接池：
        manager('default')

        Args:
            alias: The alias of the connection pool to retrieve.
                  要检索的连接池的别名。

        Returns:
            The connection pool with the given alias.
            具有给定别名的连接池。
        """
        return self.get_pool(alias)

    def __getitem__(self, alias: str):
        """
        Allow dictionary-style access to connection pools.
        允许字典样式访问连接池。

        This method allows accessing connection pools using dictionary syntax:
        manager['default']
        此方法允许使用字典语法访问连接池：
        manager['default']

        Args:
            alias: The alias of the connection pool to retrieve.
                  要检索的连接池的别名。

        Returns:
            The connection pool with the given alias.
            具有给定别名的连接池。
        """
        return self.get_pool(alias)

    def __getattr__(self, alias: str):
        """
        Allow attribute-style access to connection pools.
        允许属性样式访问连接池。

        This method allows accessing connection pools using attribute syntax:
        manager.default
        此方法允许使用属性语法访问连接池：
        manager.default

        Args:
            alias: The alias of the connection pool to retrieve.
                  要检索的连接池的别名。

        Returns:
            The connection pool with the given alias.
            具有给定别名的连接池。

        Raises:
            AttributeError: If no connection pool exists with the given alias.
                           如果不存在具有给定别名的连接池。
        """
        return self.get_pool(alias)
