"""
PostgreSQL connection pool manager for aioscrapy.
aioscrapy的PostgreSQL连接池管理器。

This module provides classes for managing PostgreSQL connection pools in aioscrapy.
It includes a pool manager for creating and managing PostgreSQL connections, and an executor
for convenient execution of SQL queries.
此模块提供了在aioscrapy中管理PostgreSQL连接池的类。
它包括一个用于创建和管理PostgreSQL连接的池管理器，以及一个用于方便执行SQL查询的执行器。
"""

from contextlib import asynccontextmanager

from asyncpg.pool import create_pool

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class PGExecutor:
    """
    Executor for PostgreSQL queries.
    PostgreSQL查询的执行器。

    This class provides a convenient way to execute SQL queries on a specific
    PostgreSQL connection pool. It offers methods for inserting data, fetching results,
    and executing queries.
    此类提供了一种在特定PostgreSQL连接池上执行SQL查询的便捷方式。
    它提供了插入数据、获取结果和执行查询的方法。
    """

    def __init__(self, alias: str, pool_manager: "AioPGPoolManager"):
        """
        Initialize a PGExecutor.
        初始化PGExecutor。

        Args:
            alias: The alias of the PostgreSQL connection pool to use.
                  要使用的PostgreSQL连接池的别名。
            pool_manager: The PostgreSQL pool manager that manages the connection pool.
                         管理连接池的PostgreSQL池管理器。
        """
        self.alias = alias
        self.pool_manager = pool_manager

    async def insert(self, sql: str, value: list):
        """
        Insert multiple rows into a PostgreSQL table.
        向PostgreSQL表中插入多行数据。

        This method executes an INSERT statement with multiple sets of values.
        It automatically handles transactions, rolling back on failure.
        此方法执行带有多组值的INSERT语句。
        它自动处理事务，在失败时回滚。

        Args:
            sql: The SQL INSERT statement with placeholders.
                 带有占位符的SQL INSERT语句。
            value: A list of tuples or lists, each containing values for one row.
                  元组或列表的列表，每个包含一行的值。

        Returns:
            The result of the insert operation.
            插入操作的结果。

        Raises:
            Exception: If the query fails.
                      如果查询失败。
        """
        async with self.pool_manager.get(self.alias) as connect:
            try:
                # Execute the query with multiple sets of values
                # 使用多组值执行查询
                result = await connect.executemany(sql, value)
                return result
            except Exception as e:
                # Roll back the transaction on error
                # 出错时回滚事务
                await connect.rollback()
                raise Exception from e

    async def fetch(self, sql: str):
        """
        Execute a SQL query and fetch all results.
        执行SQL查询并获取所有结果。

        This method executes a SQL query and returns all rows from the result.
        此方法执行SQL查询并返回结果中的所有行。

        Args:
            sql: The SQL query to execute.
                 要执行的SQL查询。

        Returns:
            list: A list of records containing the query results.
                 包含查询结果的记录列表。
        """
        async with self.pool_manager.get(self.alias) as connect:
            # Execute the query and fetch all results
            # 执行查询并获取所有结果
            return await connect.fetch(sql)

    async def query(self, sql: str):
        """
        Alias for fetch method.
        fetch方法的别名。

        This method is a convenience alias for the fetch method.
        此方法是fetch方法的便捷别名。

        Args:
            sql: The SQL query to execute.
                 要执行的SQL查询。

        Returns:
            list: A list of records containing the query results.
                 包含查询结果的记录列表。
        """
        return await self.fetch(sql)


class AioPGPoolManager(AbsDBPoolManager):
    """
    Pool manager for PostgreSQL connections.
    PostgreSQL连接的池管理器。

    This class manages PostgreSQL connection pools. It implements the
    AbsDBPoolManager interface for PostgreSQL connections, providing methods for
    creating, accessing, and closing PostgreSQL connection pools.
    此类管理PostgreSQL连接池。它为PostgreSQL连接实现了AbsDBPoolManager接口，
    提供了创建、访问和关闭PostgreSQL连接池的方法。
    """

    # Dictionary to store PostgreSQL connection pools by alias
    # 按别名存储PostgreSQL连接池的字典
    _clients = {}

    async def create(self, alias: str, params: dict):
        """
        Create a new PostgreSQL connection pool.
        创建新的PostgreSQL连接池。

        This method creates a new PostgreSQL connection pool with the given alias and parameters.
        If a pool with the given alias already exists, it returns the existing pool.
        此方法使用给定的别名和参数创建新的PostgreSQL连接池。
        如果具有给定别名的池已经存在，则返回现有池。

        Args:
            alias: The alias for the new PostgreSQL connection pool.
                  新PostgreSQL连接池的别名。
            params: The parameters for creating the PostgreSQL connection pool. Can include:
                   创建PostgreSQL连接池的参数。可以包括：
                   - host: PostgreSQL server host
                           PostgreSQL服务器主机
                   - port: PostgreSQL server port
                           PostgreSQL服务器端口
                   - user: PostgreSQL username
                           PostgreSQL用户名
                   - password: PostgreSQL password
                              PostgreSQL密码
                   - database: PostgreSQL database name
                              PostgreSQL数据库名称
                   - timeout: Connection timeout in seconds
                             连接超时（秒）
                   - and other parameters accepted by asyncpg.create_pool
                     以及asyncpg.create_pool接受的其他参数

        Returns:
            Pool: The created or existing PostgreSQL connection pool.
                 创建的或现有的PostgreSQL连接池。
        """
        # Return existing pool if it exists
        # 如果池已存在，则返回现有池
        if alias in self._clients:
            return self._clients[alias]

        # Make a copy of params to avoid modifying the original
        # 复制params以避免修改原始参数
        params = params.copy()

        # Set default connection timeout
        # 设置默认连接超时
        params.setdefault('timeout', 30)

        # Create the PostgreSQL connection pool
        # 创建PostgreSQL连接池
        pg_pool = await create_pool(**params)

        # Store and return the pool
        # 存储并返回池
        return self._clients.setdefault(alias, pg_pool)

    def get_pool(self, alias: str):
        """
        Get a PostgreSQL connection pool by its alias.
        通过别名获取PostgreSQL连接池。

        This method retrieves an existing PostgreSQL connection pool with the given alias.
        此方法检索具有给定别名的现有PostgreSQL连接池。

        Args:
            alias: The alias of the PostgreSQL connection pool to retrieve.
                  要检索的PostgreSQL连接池的别名。

        Returns:
            Pool: The PostgreSQL connection pool with the given alias.
                 具有给定别名的PostgreSQL连接池。

        Raises:
            AssertionError: If no PostgreSQL connection pool exists with the given alias.
                           如果不存在具有给定别名的PostgreSQL连接池。
        """
        pg_pool = self._clients.get(alias)
        assert pg_pool is not None, f"Dont create the PG pool named {alias}"
        return pg_pool

    @asynccontextmanager
    async def get(self, alias: str):
        """
        Get a PostgreSQL connection as an async context manager.
        获取PostgreSQL连接作为异步上下文管理器。

        This method provides a convenient way to acquire a connection
        from a PostgreSQL connection pool, and automatically release it when the
        context is exited.
        此方法提供了一种从PostgreSQL连接池获取连接的便捷方式，
        并在退出上下文时自动释放它。

        Example:
            ```python
            async with pg_manager.get('default') as conn:
                result = await conn.fetch('SELECT * FROM users')
            ```

        Args:
            alias: The alias of the PostgreSQL connection pool to use.
                  要使用的PostgreSQL连接池的别名。

        Yields:
            Connection: A PostgreSQL connection.
                       PostgreSQL连接。
        """
        # Get the PostgreSQL connection pool
        # 获取PostgreSQL连接池
        pg_pool = self.get_pool(alias)

        # Acquire a connection from the pool
        # 从池中获取连接
        conn = await pg_pool.acquire()

        try:
            # Yield the connection to the caller
            # 将连接传递给调用者
            yield conn
        finally:
            # Always release the connection back to the pool
            # 始终将连接释放回池
            await pg_pool.release(conn)

    def executor(self, alias: str) -> PGExecutor:
        """
        Get a PGExecutor for a specific PostgreSQL connection pool.
        获取特定PostgreSQL连接池的PGExecutor。

        This method creates a PGExecutor that provides a convenient way to
        execute SQL queries on the PostgreSQL connection pool with the given alias.
        此方法创建一个PGExecutor，提供了一种在具有给定别名的PostgreSQL连接池上
        执行SQL查询的便捷方式。

        Args:
            alias: The alias of the PostgreSQL connection pool to use.
                  要使用的PostgreSQL连接池的别名。

        Returns:
            PGExecutor: An executor for the PostgreSQL connection pool.
                       PostgreSQL连接池的执行器。
        """
        return PGExecutor(alias, self)

    async def close(self, alias: str):
        """
        Close a specific PostgreSQL connection pool.
        关闭特定的PostgreSQL连接池。

        This method closes the PostgreSQL connection pool with the given alias and removes it
        from the managed pools.
        此方法关闭具有给定别名的PostgreSQL连接池，并将其从管理的池中移除。

        Args:
            alias: The alias of the PostgreSQL connection pool to close.
                  要关闭的PostgreSQL连接池的别名。

        Returns:
            None
        """
        # Remove the pool from the managed pools
        # 从管理的池中移除池
        pg_pool = self._clients.pop(alias, None)

        # Close the pool if it exists
        # 如果池存在，则关闭它
        if pg_pool:
            await pg_pool.close()

    async def close_all(self):
        """
        Close all PostgreSQL connection pools.
        关闭所有PostgreSQL连接池。

        This method closes all PostgreSQL connection pools managed by this manager.
        此方法关闭此管理器管理的所有PostgreSQL连接池。

        Returns:
            None
        """
        # Create a copy of the keys to avoid modifying the dictionary during iteration
        # 创建键的副本，以避免在迭代期间修改字典
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        """
        Initialize PostgreSQL connection pools from a configuration dictionary.
        从配置字典初始化PostgreSQL连接池。

        This method creates PostgreSQL connection pools based on the configuration in db_args.
        此方法根据db_args中的配置创建PostgreSQL连接池。

        Args:
            db_args: A dictionary mapping aliases to PostgreSQL connection parameters.
                    将别名映射到PostgreSQL连接参数的字典。
                    Example:
                    {
                        'default': {'host': 'localhost', 'user': 'postgres', 'password': 'password', 'database': 'mydb'},
                        'analytics': {'host': 'analytics.example.com', 'user': 'analyst', 'password': 'password', 'database': 'analytics'}
                    }

        Returns:
            None
        """
        for alias, pg_args in db_args.items():
            await self.create(alias, pg_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        """
        Initialize PostgreSQL connection pools from aioscrapy settings.
        从aioscrapy设置初始化PostgreSQL连接池。

        This method creates PostgreSQL connection pools based on the PG_ARGS setting.
        此方法根据PG_ARGS设置创建PostgreSQL连接池。

        The PG_ARGS setting should be a dictionary mapping aliases to PostgreSQL
        connection parameters, for example:
        PG_ARGS设置应该是一个将别名映射到PostgreSQL连接参数的字典，例如：

        ```python
        PG_ARGS = {
            'default': {'host': 'localhost', 'user': 'postgres', 'password': 'password', 'database': 'mydb'},
            'analytics': {'host': 'analytics.example.com', 'user': 'analyst', 'password': 'password', 'database': 'analytics'}
        }
        ```

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """
        for alias, pg_args in settings.getdict('PG_ARGS').items():
            await self.create(alias, pg_args)


# Singleton instance of AioPGPoolManager
# AioPGPoolManager的单例实例
pg_manager = AioPGPoolManager()

if __name__ == '__main__':
    import asyncio


    async def test():
        pg_pool = await pg_manager.create(
            'default',
            dict(
                user='username',
                password='pwd',
                database='dbname',
                host='127.0.0.1'
            )
        )

        # 方式一:
        conn = await pg_pool.acquire()
        try:
            result = await conn.fetch('select 1 ')
            print(tuple(result[0]))
        finally:
            await pg_pool.release(conn)

        # 方式二:
        async with pg_manager.get('default') as conn:
            result = await conn.fetch('select 1 ')
            print(tuple(result[0]))


    asyncio.run(test())
