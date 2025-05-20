"""
Redis connection pool manager for aioscrapy.
aioscrapy的Redis连接池管理器。

This module provides classes for managing Redis connection pools in aioscrapy.
It includes a pool manager for creating and managing Redis clients, and an executor
for convenient access to Redis commands.
此模块提供了在aioscrapy中管理Redis连接池的类。
它包括一个用于创建和管理Redis客户端的池管理器，以及一个用于方便访问Redis命令的执行器。
"""

from redis.asyncio import BlockingConnectionPool, Redis

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class RedisExecutor:
    """
    Executor for Redis commands.
    Redis命令的执行器。

    This class provides a convenient way to execute Redis commands on a specific
    Redis client. It dynamically forwards command calls to the underlying Redis client.
    此类提供了一种在特定Redis客户端上执行Redis命令的便捷方式。
    它动态地将命令调用转发到底层Redis客户端。
    """

    def __init__(self, alias: str, pool_manager: "AioRedisPoolManager"):
        """
        Initialize a RedisExecutor.
        初始化RedisExecutor。

        Args:
            alias: The alias of the Redis client to use.
                  要使用的Redis客户端的别名。
            pool_manager: The Redis pool manager that manages the Redis client.
                         管理Redis客户端的Redis池管理器。
        """
        self.alias = alias
        self.pool_manager = pool_manager

    def __getattr__(self, command: str):
        """
        Dynamically forward command calls to the Redis client.
        动态地将命令调用转发到Redis客户端。

        This method allows calling Redis commands directly on the executor:
        executor.get('key'), executor.set('key', 'value'), etc.
        此方法允许直接在执行器上调用Redis命令：
        executor.get('key')、executor.set('key', 'value')等。

        Args:
            command: The Redis command to execute.
                    要执行的Redis命令。

        Returns:
            The method of the Redis client corresponding to the command.
            对应于命令的Redis客户端的方法。
        """
        redis_pool: Redis = self.pool_manager.get_pool(self.alias)
        return getattr(redis_pool, command)


class AioRedisPoolManager(AbsDBPoolManager):
    """
    Pool manager for Redis connections.
    Redis连接的池管理器。

    This class manages Redis connection pools and clients. It implements the
    AbsDBPoolManager interface for Redis connections, providing methods for
    creating, accessing, and closing Redis clients.
    此类管理Redis连接池和客户端。它为Redis连接实现了AbsDBPoolManager接口，
    提供了创建、访问和关闭Redis客户端的方法。
    """

    # Dictionary to store Redis clients by alias
    # 按别名存储Redis客户端的字典
    _clients = {}

    async def create(self, alias: str, params: dict) -> Redis:
        """
        Create a new Redis client.
        创建新的Redis客户端。

        This method creates a new Redis client with the given alias and parameters.
        If a client with the given alias already exists, it returns the existing client.
        此方法使用给定的别名和参数创建新的Redis客户端。
        如果具有给定别名的客户端已经存在，则返回现有客户端。

        Args:
            alias: The alias for the new Redis client.
                  新Redis客户端的别名。
            params: The parameters for creating the Redis client. Can include:
                   创建Redis客户端的参数。可以包括：
                   - url: Redis connection URL (e.g., 'redis://user:password@host:port/db')
                          Redis连接URL（例如，'redis://user:password@host:port/db'）
                   - host: Redis server host
                           Redis服务器主机
                   - port: Redis server port
                           Redis服务器端口
                   - db: Redis database number
                         Redis数据库编号
                   - password: Redis server password
                              Redis服务器密码
                   - socket_connect_timeout: Connection timeout in seconds
                                           连接超时（秒）
                   - and other parameters accepted by BlockingConnectionPool
                     以及BlockingConnectionPool接受的其他参数

        Returns:
            Redis: The created or existing Redis client.
                  创建的或现有的Redis客户端。
        """
        # Return existing client if it exists
        # 如果客户端已存在，则返回现有客户端
        if alias in self._clients:
            return self._clients[alias]

        # Make a copy of params to avoid modifying the original
        # 复制params以避免修改原始参数
        params = params.copy()

        # Extract URL if provided
        # 如果提供了URL，则提取它
        url = params.pop('url', None)

        # Set default connection timeout
        # 设置默认连接超时
        params.setdefault('socket_connect_timeout', 30)

        # Create connection pool from URL or parameters
        # 从URL或参数创建连接池
        if url:
            connection_pool = BlockingConnectionPool.from_url(url, **params)
        else:
            connection_pool = BlockingConnectionPool(**params)

        # Create Redis client with the connection pool
        # 使用连接池创建Redis客户端
        redis = Redis(connection_pool=connection_pool)

        # Store and return the client
        # 存储并返回客户端
        return self._clients.setdefault(alias, redis)

    def get_pool(self, alias: str) -> Redis:
        """
        Get a Redis client by its alias.
        通过别名获取Redis客户端。

        This method retrieves an existing Redis client with the given alias.
        此方法检索具有给定别名的现有Redis客户端。

        Args:
            alias: The alias of the Redis client to retrieve.
                  要检索的Redis客户端的别名。

        Returns:
            Redis: The Redis client with the given alias.
                  具有给定别名的Redis客户端。

        Raises:
            AssertionError: If no Redis client exists with the given alias.
                           如果不存在具有给定别名的Redis客户端。
        """
        redis_pool: Redis = self._clients.get(alias)
        assert redis_pool is not None, f"Dont create the redis client named {alias}"
        return redis_pool

    def executor(self, alias: str) -> RedisExecutor:
        """
        Get a RedisExecutor for a specific Redis client.
        获取特定Redis客户端的RedisExecutor。

        This method creates a RedisExecutor that provides a convenient way to
        execute commands on the Redis client with the given alias.
        此方法创建一个RedisExecutor，提供了一种在具有给定别名的Redis客户端上
        执行命令的便捷方式。

        Args:
            alias: The alias of the Redis client to use.
                  要使用的Redis客户端的别名。

        Returns:
            RedisExecutor: An executor for the Redis client.
                          Redis客户端的执行器。
        """
        return RedisExecutor(alias, self)

    async def close(self, alias: str):
        """
        Close a specific Redis client.
        关闭特定的Redis客户端。

        This method closes the Redis client with the given alias and removes it
        from the managed clients.
        此方法关闭具有给定别名的Redis客户端，并将其从管理的客户端中移除。

        Args:
            alias: The alias of the Redis client to close.
                  要关闭的Redis客户端的别名。

        Returns:
            None
        """
        # Remove the client from the managed clients
        # 从管理的客户端中移除客户端
        redis = self._clients.pop(alias, None)

        # Close the client if it exists
        # 如果客户端存在，则关闭它
        if redis:
            # Close the Redis client
            # 关闭Redis客户端
            await redis.close()

            # Disconnect the connection pool
            # 断开连接池
            await redis.connection_pool.disconnect()

    async def close_all(self):
        """
        Close all Redis clients.
        关闭所有Redis客户端。

        This method closes all Redis clients managed by this manager.
        此方法关闭此管理器管理的所有Redis客户端。

        Returns:
            None
        """
        # Create a copy of the keys to avoid modifying the dictionary during iteration
        # 创建键的副本，以避免在迭代期间修改字典
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        """
        Initialize Redis clients from a configuration dictionary.
        从配置字典初始化Redis客户端。

        This method creates Redis clients based on the configuration in db_args.
        此方法根据db_args中的配置创建Redis客户端。

        Args:
            db_args: A dictionary mapping aliases to Redis connection parameters.
                    将别名映射到Redis连接参数的字典。
                    Example:
                    {
                        'default': {'url': 'redis://localhost:6379/0'},
                        'cache': {'host': 'cache.example.com', 'port': 6379, 'db': 1}
                    }

        Returns:
            None
        """
        for alias, redis_args in db_args.items():
            await self.create(alias, redis_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        """
        Initialize Redis clients from aioscrapy settings.
        从aioscrapy设置初始化Redis客户端。

        This method creates Redis clients based on the REDIS_ARGS setting.
        此方法根据REDIS_ARGS设置创建Redis客户端。

        The REDIS_ARGS setting should be a dictionary mapping aliases to Redis
        connection parameters, for example:
        REDIS_ARGS设置应该是一个将别名映射到Redis连接参数的字典，例如：

        ```python
        REDIS_ARGS = {
            'default': {'url': 'redis://localhost:6379/0'},
            'cache': {'host': 'cache.example.com', 'port': 6379, 'db': 1}
        }
        ```

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """
        for alias, redis_args in settings.getdict('REDIS_ARGS').items():
            await self.create(alias, redis_args)


# Singleton instance of AioRedisPoolManager
# AioRedisPoolManager的单例实例
redis_manager = AioRedisPoolManager()

# Example usage
# 示例用法
if __name__ == '__main__':
    import asyncio


    async def test():
        """
        Test function demonstrating the usage of the Redis manager.
        演示Redis管理器用法的测试函数。
        """
        # Create a Redis client with alias 'default'
        # 创建别名为'default'的Redis客户端
        await redis_manager.create('default', {
            'url': 'redis://@192.168.234.128:6379/9',
        })

        # Get a Redis executor for the 'default' client
        # 获取'default'客户端的Redis执行器
        redis = redis_manager.executor('default')

        # Add a value to a sorted set
        # 向有序集合添加一个值
        print(await redis.zadd('key1', {'value': 2}))

        # Use a pipeline to execute multiple commands atomically
        # 使用管道原子地执行多个命令
        async with redis.pipeline(transaction=True) as pipe:
            # Get the first element and remove it in one transaction
            # 在一个事务中获取第一个元素并删除它
            results, _ = await (
                pipe.zrange('key1', 0, 0)
                    .zremrangebyrank('key1', 0, 0)
                    .execute()
            )

        # Print the results
        # 打印结果
        print(results)

        # Close all Redis clients
        # 关闭所有Redis客户端
        await redis_manager.close_all()


    # Run the test function
    # 运行测试函数
    # asyncio.run(test())  # For Python 3.7+
    asyncio.get_event_loop().run_until_complete(test())  # For Python 3.6
