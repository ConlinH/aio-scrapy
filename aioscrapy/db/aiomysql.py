"""
MySQL connection pool manager for aioscrapy.
aioscrapy的MySQL连接池管理器。

This module provides classes for managing MySQL connection pools in aioscrapy.
It includes a pool manager for creating and managing MySQL connections, and an executor
for convenient execution of SQL queries.
此模块提供了在aioscrapy中管理MySQL连接池的类。
它包括一个用于创建和管理MySQL连接的池管理器，以及一个用于方便执行SQL查询的执行器。
"""

import socket
from contextlib import asynccontextmanager

from aiomysql import create_pool

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class MysqlExecutor:
    """
    Executor for MySQL queries.
    MySQL查询的执行器。

    This class provides a convenient way to execute SQL queries on a specific
    MySQL connection pool. It offers methods for inserting data, executing queries,
    and fetching results.
    此类提供了一种在特定MySQL连接池上执行SQL查询的便捷方式。
    它提供了插入数据、执行查询和获取结果的方法。
    """

    def __init__(self, alias: str, pool_manager: "AioMysqlPoolManager"):
        """
        Initialize a MysqlExecutor.
        初始化MysqlExecutor。

        Args:
            alias: The alias of the MySQL connection pool to use.
                  要使用的MySQL连接池的别名。
            pool_manager: The MySQL pool manager that manages the connection pool.
                         管理连接池的MySQL池管理器。
        """
        self.alias = alias
        self.pool_manager = pool_manager

    async def insert(self, sql: str, value: list):
        """
        Insert multiple rows into a MySQL table.
        向MySQL表中插入多行数据。

        This method executes an INSERT statement with multiple sets of values.
        It automatically handles transactions, committing on success and
        rolling back on failure.
        此方法执行带有多组值的INSERT语句。
        它自动处理事务，在成功时提交，在失败时回滚。

        Args:
            sql: The SQL INSERT statement with placeholders.
                 带有占位符的SQL INSERT语句。
            value: A list of tuples or lists, each containing values for one row.
                  元组或列表的列表，每个包含一行的值。

        Returns:
            int: The number of affected rows.
                 受影响的行数。

        Raises:
            Exception: If the query fails.
                      如果查询失败。
        """
        async with self.pool_manager.get(self.alias) as (conn, cursor):
            try:
                # Execute the query with multiple sets of values
                # 使用多组值执行查询
                result = await cursor.executemany(sql, value)
                # Commit the transaction
                # 提交事务
                await conn.commit()
                return result
            except Exception as e:
                # Roll back the transaction on error
                # 出错时回滚事务
                await conn.rollback()
                raise Exception from e

    async def execute(self, sql: str):
        """
        Execute a SQL query and fetch all results.
        执行SQL查询并获取所有结果。

        This method executes a SQL query and returns all rows from the result.
        此方法执行SQL查询并返回结果中的所有行。

        Args:
            sql: The SQL query to execute.
                 要执行的SQL查询。

        Returns:
            list: A list of tuples containing the query results.
                 包含查询结果的元组列表。
        """
        async with self.pool_manager.get(self.alias) as (conn, cursor):
            # Execute the query
            # 执行查询
            await cursor.execute(sql)
            # Fetch all results
            # 获取所有结果
            return await cursor.fetchall()

    async def query(self, sql: str):
        """
        Alias for execute method.
        execute方法的别名。

        This method is a convenience alias for the execute method.
        此方法是execute方法的便捷别名。

        Args:
            sql: The SQL query to execute.
                 要执行的SQL查询。

        Returns:
            list: A list of tuples containing the query results.
                 包含查询结果的元组列表。
        """
        return await self.execute(sql)


class AioMysqlPoolManager(AbsDBPoolManager):
    """
    Pool manager for MySQL connections.
    MySQL连接的池管理器。

    This class manages MySQL connection pools. It implements the
    AbsDBPoolManager interface for MySQL connections, providing methods for
    creating, accessing, and closing MySQL connection pools.
    此类管理MySQL连接池。它为MySQL连接实现了AbsDBPoolManager接口，
    提供了创建、访问和关闭MySQL连接池的方法。
    """

    # Dictionary to store MySQL connection pools by alias
    # 按别名存储MySQL连接池的字典
    _clients = {}

    async def create(self, alias: str, params: dict):
        """
        Create a new MySQL connection pool.
        创建新的MySQL连接池。

        This method creates a new MySQL connection pool with the given alias and parameters.
        If a pool with the given alias already exists, it returns the existing pool.
        此方法使用给定的别名和参数创建新的MySQL连接池。
        如果具有给定别名的池已经存在，则返回现有池。

        Args:
            alias: The alias for the new MySQL connection pool.
                  新MySQL连接池的别名。
            params: The parameters for creating the MySQL connection pool. Can include:
                   创建MySQL连接池的参数。可以包括：
                   - host: MySQL server host
                           MySQL服务器主机
                   - port: MySQL server port
                           MySQL服务器端口
                   - user: MySQL username
                           MySQL用户名
                   - password: MySQL password
                              MySQL密码
                   - db: MySQL database name
                         MySQL数据库名称
                   - connect_timeout: Connection timeout in seconds
                                     连接超时（秒）
                   - and other parameters accepted by aiomysql.create_pool
                     以及aiomysql.create_pool接受的其他参数

        Returns:
            Pool: The created or existing MySQL connection pool.
                 创建的或现有的MySQL连接池。
        """
        # Return existing pool if it exists
        # 如果池已存在，则返回现有池
        if alias in self._clients:
            return self._clients[alias]

        # Make a copy of params to avoid modifying the original
        # 复制params以避免修改原始参数
        params = params.copy()

        # When the host is domain, convert to IP
        # 当主机是域名时，转换为IP
        # https://github.com/aio-libs/aiomysql/issues/641
        params.update({'host': socket.gethostbyname(params['host'])})

        # Set default connection timeout
        # 设置默认连接超时
        params.setdefault('connect_timeout', 30)

        # Create the MySQL connection pool
        # 创建MySQL连接池
        mysql_pool = await create_pool(**params)

        # Store and return the pool
        # 存储并返回池
        return self._clients.setdefault(alias, mysql_pool)

    def get_pool(self, alias: str):
        """
        Get a MySQL connection pool by its alias.
        通过别名获取MySQL连接池。

        This method retrieves an existing MySQL connection pool with the given alias.
        此方法检索具有给定别名的现有MySQL连接池。

        Args:
            alias: The alias of the MySQL connection pool to retrieve.
                  要检索的MySQL连接池的别名。

        Returns:
            Pool: The MySQL connection pool with the given alias.
                 具有给定别名的MySQL连接池。

        Raises:
            AssertionError: If no MySQL connection pool exists with the given alias.
                           如果不存在具有给定别名的MySQL连接池。
        """
        mysql_pool = self._clients.get(alias)
        assert mysql_pool is not None, f"Dont create the mysql pool named {alias}"
        return mysql_pool

    @asynccontextmanager
    async def get(self, alias: str, ping=False):
        """
        Get a MySQL connection and cursor as an async context manager.
        获取MySQL连接和游标作为异步上下文管理器。

        This method provides a convenient way to acquire a connection and cursor
        from a MySQL connection pool, and automatically release them when the
        context is exited.
        此方法提供了一种从MySQL连接池获取连接和游标的便捷方式，
        并在退出上下文时自动释放它们。

        Example:
            ```python
            async with mysql_manager.get('default') as (conn, cur):
                await cur.execute('SELECT * FROM users')
                results = await cur.fetchall()
            ```

        Args:
            alias: The alias of the MySQL connection pool to use.
                  要使用的MySQL连接池的别名。
            ping: Whether to ping the server to check the connection.
                 是否ping服务器以检查连接。

        Yields:
            tuple: A tuple containing (connection, cursor).
                  包含(连接, 游标)的元组。
        """
        # Get the MySQL connection pool
        # 获取MySQL连接池
        mysql_pool = self.get_pool(alias)

        # Acquire a connection from the pool
        # 从池中获取连接
        conn = await mysql_pool.acquire()

        # Create a cursor
        # 创建游标
        cur = await conn.cursor()

        try:
            # Ping the server if requested
            # 如果请求，ping服务器
            if ping:
                await conn.ping()

            # Yield the connection and cursor to the caller
            # 将连接和游标传递给调用者
            yield conn, cur
        finally:
            # Always close the cursor and release the connection
            # 始终关闭游标并释放连接
            await cur.close()
            await mysql_pool.release(conn)

    def executor(self, alias: str) -> MysqlExecutor:
        """
        Get a MysqlExecutor for a specific MySQL connection pool.
        获取特定MySQL连接池的MysqlExecutor。

        This method creates a MysqlExecutor that provides a convenient way to
        execute SQL queries on the MySQL connection pool with the given alias.
        此方法创建一个MysqlExecutor，提供了一种在具有给定别名的MySQL连接池上
        执行SQL查询的便捷方式。

        Args:
            alias: The alias of the MySQL connection pool to use.
                  要使用的MySQL连接池的别名。

        Returns:
            MysqlExecutor: An executor for the MySQL connection pool.
                          MySQL连接池的执行器。
        """
        return MysqlExecutor(alias, self)

    async def close(self, alias: str):
        """
        Close a specific MySQL connection pool.
        关闭特定的MySQL连接池。

        This method closes the MySQL connection pool with the given alias and removes it
        from the managed pools.
        此方法关闭具有给定别名的MySQL连接池，并将其从管理的池中移除。

        Args:
            alias: The alias of the MySQL connection pool to close.
                  要关闭的MySQL连接池的别名。

        Returns:
            None
        """
        # Remove the pool from the managed pools
        # 从管理的池中移除池
        mysql_pool = self._clients.pop(alias, None)

        # Close the pool if it exists
        # 如果池存在，则关闭它
        if mysql_pool:
            # Close the pool (stop accepting new connections)
            # 关闭池（停止接受新连接）
            mysql_pool.close()

            # Wait for all connections to be released and closed
            # 等待所有连接被释放和关闭
            await mysql_pool.wait_closed()

    async def close_all(self):
        """
        Close all MySQL connection pools.
        关闭所有MySQL连接池。

        This method closes all MySQL connection pools managed by this manager.
        此方法关闭此管理器管理的所有MySQL连接池。

        Returns:
            None
        """
        # Create a copy of the keys to avoid modifying the dictionary during iteration
        # 创建键的副本，以避免在迭代期间修改字典
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        """
        Initialize MySQL connection pools from a configuration dictionary.
        从配置字典初始化MySQL连接池。

        This method creates MySQL connection pools based on the configuration in db_args.
        此方法根据db_args中的配置创建MySQL连接池。

        Args:
            db_args: A dictionary mapping aliases to MySQL connection parameters.
                    将别名映射到MySQL连接参数的字典。
                    Example:
                    {
                        'default': {'host': 'localhost', 'user': 'root', 'password': 'password', 'db': 'mydb'},
                        'analytics': {'host': 'analytics.example.com', 'user': 'analyst', 'password': 'password', 'db': 'analytics'}
                    }

        Returns:
            None
        """
        for alias, mysql_args in db_args.items():
            await self.create(alias, mysql_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        """
        Initialize MySQL connection pools from aioscrapy settings.
        从aioscrapy设置初始化MySQL连接池。

        This method creates MySQL connection pools based on the MYSQL_ARGS setting.
        此方法根据MYSQL_ARGS设置创建MySQL连接池。

        The MYSQL_ARGS setting should be a dictionary mapping aliases to MySQL
        connection parameters, for example:
        MYSQL_ARGS设置应该是一个将别名映射到MySQL连接参数的字典，例如：

        ```python
        MYSQL_ARGS = {
            'default': {'host': 'localhost', 'user': 'root', 'password': 'password', 'db': 'mydb'},
            'analytics': {'host': 'analytics.example.com', 'user': 'analyst', 'password': 'password', 'db': 'analytics'}
        }
        ```

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """
        for alias, mysql_args in settings.getdict('MYSQL_ARGS').items():
            await self.create(alias, mysql_args)


# Singleton instance of AioMysqlPoolManager
# AioMysqlPoolManager的单例实例
mysql_manager = AioMysqlPoolManager()

# Example usage
# 示例用法
if __name__ == '__main__':
    import asyncio


    async def test():
        """
        Test function demonstrating the usage of the MySQL manager.
        演示MySQL管理器用法的测试函数。
        """
        # Create a MySQL connection pool with alias 'default'
        # 创建别名为'default'的MySQL连接池
        mysql_pool = await mysql_manager.create('default', {
            'db': 'mysql',
            'user': 'root',
            'password': '123456',
            'host': '192.168.234.128',
            'port': 3306
        })

        # Method 1: Using the pool directly
        # 方式一：直接使用连接池
        try:
            # Acquire a connection from the pool
            # 从池中获取连接
            conn = await mysql_pool.acquire()

            # Create a cursor
            # 创建游标
            cur = await conn.cursor()

            # Execute a query
            # 执行查询
            await cur.execute('select * from user')

            # Fetch and print the results
            # 获取并打印结果
            print(await cur.fetchall())

            # Uncomment to commit changes if needed
            # 如果需要，取消注释以提交更改
            # await conn.commit()
        finally:
            # Always close the cursor and release the connection
            # 始终关闭游标并释放连接
            await cur.close()
            await mysql_pool.release(conn)

        # Method 2: Using the context manager
        # 方式二：使用上下文管理器
        async with mysql_manager.get('default') as (conn, cur):
            # Execute a query and print the number of affected rows
            # 执行查询并打印受影响的行数
            print(await cur.execute('select 1'))

            # Uncomment to commit changes if needed
            # 如果需要，取消注释以提交更改
            # await conn.commit()

        # Close all connection pools
        # 关闭所有连接池
        await mysql_manager.close_all()


    # Run the test function
    # 运行测试函数
    asyncio.run(test())
