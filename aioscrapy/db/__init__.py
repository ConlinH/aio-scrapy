"""
Database management module for aioscrapy.
aioscrapy的数据库管理模块。

This module provides a unified interface for managing different types of database
connections in aioscrapy. It supports Redis, MySQL, RabbitMQ, MongoDB, and PostgreSQL
through their respective async libraries.
此模块为aioscrapy中的不同类型数据库连接提供了统一的接口。它通过各自的异步库
支持Redis、MySQL、RabbitMQ、MongoDB和PostgreSQL。
"""

from importlib import import_module
from typing import Any

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager
from aioscrapy.db.aioredis import redis_manager
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_object

# Public API
# 公共API
__all__ = ['db_manager', 'get_pool', 'get_manager']

# Mapping of database module names to their manager keys and class paths
# 数据库模块名称到其管理器键和类路径的映射
DB_MODULE_MAP = {
    'redis': ('redis', 'aioscrapy.db.aioredis.redis_manager'),
    'aiomysql': ('mysql', 'aioscrapy.db.aiomysql.mysql_manager'),
    'aio_pika': ('rabbitmq', 'aioscrapy.db.aiorabbitmq.rabbitmq_manager'),
    'motor': ('mongo', 'aioscrapy.db.aiomongo.mongo_manager'),
    'asyncpg': ('pg', 'aioscrapy.db.aiopg.pg_manager'),
}

# Dictionary to store available database managers
# 存储可用数据库管理器的字典
db_manager_map = {}

# Dynamically load available database managers based on installed packages
# 根据已安装的包动态加载可用的数据库管理器
for module_name, (manager_key, class_path) in DB_MODULE_MAP.items():
    try:
        # Try to import the module to check if it's available
        # 尝试导入模块以检查它是否可用
        import_module(module_name)
    except ImportError:
        # Skip if the module is not installed
        # 如果模块未安装，则跳过
        pass
    else:
        # Load the manager class and add it to the map
        # 加载管理器类并将其添加到映射中
        db_manager_map[manager_key] = load_object(class_path)


class DBManager:
    """
    Central manager for database connections in aioscrapy.
    aioscrapy中数据库连接的中央管理器。

    This class provides a unified interface for accessing different types of database
    connections. It manages connection pools for various database types and provides
    methods to initialize connections from settings or configuration dictionaries.
    此类为访问不同类型的数据库连接提供了统一的接口。它管理各种数据库类型的连接池，
    并提供从设置或配置字典初始化连接的方法。
    """

    @staticmethod
    def get_manager(db_type: str) -> AbsDBPoolManager:
        """
        Get the database manager for a specific database type.
        获取特定数据库类型的数据库管理器。

        Args:
            db_type: The type of database ('redis', 'mysql', 'rabbitmq', 'mongo', 'pg').
                    数据库类型（'redis'、'mysql'、'rabbitmq'、'mongo'、'pg'）。

        Returns:
            AbsDBPoolManager: The database manager instance.
                             数据库管理器实例。

        Raises:
            AssertionError: If the specified database type is not supported.
                           如果不支持指定的数据库类型。
        """
        manager = db_manager_map.get(db_type)
        assert manager is not None, f"Not support db type：{db_type}"
        return manager

    def get_pool(self, db_type: str, alias='default') -> Any:
        """
        Get a connection pool for a specific database type.
        获取特定数据库类型的连接池。

        Args:
            db_type: The type of database ('redis', 'mysql', 'rabbitmq', 'mongo', 'pg').
                    数据库类型（'redis'、'mysql'、'rabbitmq'、'mongo'、'pg'）。
            alias: The alias of the connection pool, defaults to 'default'.
                  连接池的别名，默认为'default'。

        Returns:
            Any: The connection pool instance.
                连接池实例。
        """
        manager = self.get_manager(db_type)
        return manager.get_pool(alias)

    @staticmethod
    async def close_all() -> None:
        """
        Close all database connections.
        关闭所有数据库连接。

        This method closes all connection pools for all database types.
        此方法关闭所有数据库类型的所有连接池。

        Returns:
            None
        """
        for manager in db_manager_map.values():
            await manager.close_all()

    @staticmethod
    async def from_dict(db_args: dict) -> None:
        """
        Initialize database connections from a configuration dictionary.
        从配置字典初始化数据库连接。

        Args:
            db_args: A dictionary mapping database types to their configuration.
                    将数据库类型映射到其配置的字典。
                    Example:
                    {
                        'redis': {'default': {'host': 'localhost', 'port': 6379}},
                        'mysql': {'default': {'host': 'localhost', 'user': 'root'}}
                    }

        Returns:
            None
        """
        for db_type, args in db_args.items():
            manager = db_manager_map.get(db_type)
            if manager is None:
                logger.warning(f'Not support db type: {db_type}; Only {", ".join(db_manager_map.keys())} supported')
                continue
            await manager.from_dict(args)

    @staticmethod
    async def from_settings(settings: aioscrapy.Settings) -> None:
        """
        Initialize database connections from aioscrapy settings.
        从aioscrapy设置初始化数据库连接。

        This method initializes all available database managers with the provided settings.
        Each manager will extract its relevant settings from the settings object.
        此方法使用提供的设置初始化所有可用的数据库管理器。
        每个管理器将从设置对象中提取其相关设置。

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """
        for manager in db_manager_map.values():
            await manager.from_settings(settings)

    async def from_crawler(self, crawler: "aioscrapy.Crawler") -> None:
        """
        Initialize database connections from a crawler.
        从爬虫初始化数据库连接。

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

    def __getattr__(self, db_type: str) -> Any:
        """
        Access a database manager directly as an attribute.
        直接将数据库管理器作为属性访问。

        This method allows accessing database managers using attribute syntax:
        db_manager.redis, db_manager.mysql, etc.
        此方法允许使用属性语法访问数据库管理器：
        db_manager.redis、db_manager.mysql等。

        Args:
            db_type: The type of database ('redis', 'mysql', 'rabbitmq', 'mongo', 'pg').
                    数据库类型（'redis'、'mysql'、'rabbitmq'、'mongo'、'pg'）。

        Returns:
            AbsDBPoolManager: The database manager instance.
                             数据库管理器实例。

        Raises:
            AttributeError: If the specified database type is not supported.
                           如果不支持指定的数据库类型。
        """
        if db_type not in db_manager_map:
            raise AttributeError(f'Not support db type: {db_type}')
        return db_manager_map[db_type]


# Singleton instance of DBManager
# DBManager的单例实例
db_manager = DBManager()

# Convenience functions for accessing the singleton
# 用于访问单例的便捷函数
get_manager = db_manager.get_manager
get_pool = db_manager.get_pool
