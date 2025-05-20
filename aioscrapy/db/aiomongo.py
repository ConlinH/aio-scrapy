"""
MongoDB connection manager for aioscrapy.
aioscrapy的MongoDB连接管理器。

This module provides classes for managing MongoDB connections in aioscrapy.
It includes a connection manager for creating and managing MongoDB clients, and an executor
for convenient access to MongoDB collections and operations.
此模块提供了在aioscrapy中管理MongoDB连接的类。
它包括一个用于创建和管理MongoDB客户端的连接管理器，以及一个用于方便访问MongoDB集合和操作的执行器。
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import NetworkTimeout

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager
from loguru import logger


class MongoExecutor:
    """
    Executor for MongoDB operations.
    MongoDB操作的执行器。

    This class provides a convenient way to execute MongoDB operations on a specific
    MongoDB client. It offers methods for inserting data and direct access to collections.
    此类提供了一种在特定MongoDB客户端上执行MongoDB操作的便捷方式。
    它提供了插入数据和直接访问集合的方法。
    """

    def __init__(self, alias: str, pool_manager: "AioMongoManager"):
        """
        Initialize a MongoExecutor.
        初始化MongoExecutor。

        Args:
            alias: The alias of the MongoDB client to use.
                  要使用的MongoDB客户端的别名。
            pool_manager: The MongoDB manager that manages the client.
                         管理客户端的MongoDB管理器。
        """
        self.alias = alias
        self.pool_manager = pool_manager

    async def insert(self, table_name: str, values: list, db_name=None, ordered=False, retry_times=3):
        """
        Insert multiple documents into a MongoDB collection.
        向MongoDB集合中插入多个文档。

        This method inserts multiple documents into a MongoDB collection with retry
        capability in case of network timeouts.
        此方法向MongoDB集合中插入多个文档，在网络超时的情况下具有重试功能。

        Args:
            table_name: The name of the collection to insert into.
                       要插入的集合名称。
            values: A list of documents (dictionaries) to insert.
                   要插入的文档（字典）列表。
            db_name: The name of the database to use. If None, uses the default database.
                    要使用的数据库名称。如果为None，则使用默认数据库。
            ordered: If True, performs an ordered insert operation, which stops on first error.
                    如果为True，执行有序插入操作，在第一个错误时停止。
            retry_times: Number of times to retry in case of network timeout.
                        网络超时时重试的次数。

        Returns:
            InsertManyResult: The result of the insert operation.
                             插入操作的结果。

        Raises:
            NetworkTimeout: If the operation times out after all retries.
                           如果操作在所有重试后超时。
        """
        # Get the MongoDB client and default database name
        # 获取MongoDB客户端和默认数据库名称
        client, db_name_default = self.pool_manager.get_pool(self.alias)

        # Use the provided database name or fall back to the default
        # 使用提供的数据库名称或回退到默认值
        db_name = db_name or db_name_default

        # Retry the insert operation in case of network timeout
        # 在网络超时的情况下重试插入操作
        for _ in range(retry_times):
            try:
                return await client[f'{db_name}'][f'{table_name}'].insert_many(values, ordered=ordered)
            except NetworkTimeout:
                logger.warning("mongo insert error by NetworkTimeout, retrying...")

        # If all retries fail, raise the exception
        # 如果所有重试都失败，则引发异常
        raise NetworkTimeout

    def __getattr__(self, table_name: str):
        """
        Access a MongoDB collection directly as an attribute.
        直接将MongoDB集合作为属性访问。

        This method allows accessing MongoDB collections using attribute syntax:
        executor.users, executor.products, etc.
        此方法允许使用属性语法访问MongoDB集合：
        executor.users、executor.products等。

        Args:
            table_name: The name of the collection to access.
                       要访问的集合名称。

        Returns:
            Collection: The MongoDB collection object.
                       MongoDB集合对象。
        """
        # Get the MongoDB client and default database name
        # 获取MongoDB客户端和默认数据库名称
        client, db_name_default = self.pool_manager.get_pool(self.alias)

        # Return the collection from the default database
        # 从默认数据库返回集合
        return client[f'{db_name_default}'][f'{table_name}']


class AioMongoManager(AbsDBPoolManager):
    """
    Manager for MongoDB connections.
    MongoDB连接的管理器。

    This class manages MongoDB clients and connections. It implements the
    AbsDBPoolManager interface for MongoDB connections, providing methods for
    creating, accessing, and closing MongoDB clients.
    此类管理MongoDB客户端和连接。它为MongoDB连接实现了AbsDBPoolManager接口，
    提供了创建、访问和关闭MongoDB客户端的方法。
    """

    # Dictionary to store MongoDB clients by alias
    # 按别名存储MongoDB客户端的字典
    _clients = {}

    async def create(self, alias: str, params: dict):
        """
        Create a new MongoDB client.
        创建新的MongoDB客户端。

        This method creates a new MongoDB client with the given alias and parameters.
        If a client with the given alias already exists, it returns the existing client.
        此方法使用给定的别名和参数创建新的MongoDB客户端。
        如果具有给定别名的客户端已经存在，则返回现有客户端。

        Args:
            alias: The alias for the new MongoDB client.
                  新MongoDB客户端的别名。
            params: The parameters for creating the MongoDB client. Can include:
                   创建MongoDB客户端的参数。可以包括：
                   - host: MongoDB server host or connection string
                           MongoDB服务器主机或连接字符串
                   - port: MongoDB server port
                           MongoDB服务器端口
                   - db: MongoDB database name (required)
                         MongoDB数据库名称（必需）
                   - username: MongoDB username
                              MongoDB用户名
                   - password: MongoDB password
                              MongoDB密码
                   - connecttimeoutms: Connection timeout in milliseconds
                                      连接超时（毫秒）
                   - and other parameters accepted by AsyncIOMotorClient
                     以及AsyncIOMotorClient接受的其他参数

        Returns:
            tuple: A tuple containing (client, db_name).
                  包含(客户端, 数据库名称)的元组。
        """
        # Return existing client if it exists
        # 如果客户端已存在，则返回现有客户端
        if alias in self._clients:
            return self._clients[alias]

        # Make a copy of params to avoid modifying the original
        # 复制params以避免修改原始参数
        params = params.copy()

        # Extract database name
        # 提取数据库名称
        db_name = params.pop('db')

        # Set default connection timeout
        # 设置默认连接超时
        params.setdefault('connecttimeoutms', 30)

        # Create the MongoDB client
        # 创建MongoDB客户端
        client = AsyncIOMotorClient(**params)

        # Store and return the client with its database name
        # 存储并返回客户端及其数据库名称
        return self._clients.setdefault(alias, (client, db_name))

    def get_pool(self, alias: str):
        """
        Get a MongoDB client by its alias.
        通过别名获取MongoDB客户端。

        This method retrieves an existing MongoDB client with the given alias.
        此方法检索具有给定别名的现有MongoDB客户端。

        Args:
            alias: The alias of the MongoDB client to retrieve.
                  要检索的MongoDB客户端的别名。

        Returns:
            tuple: A tuple containing (client, db_name), or None if not found.
                  包含(客户端, 数据库名称)的元组，如果未找到则为None。
        """
        return self._clients.get(alias)

    def executor(self, alias: str) -> MongoExecutor:
        """
        Get a MongoExecutor for a specific MongoDB client.
        获取特定MongoDB客户端的MongoExecutor。

        This method creates a MongoExecutor that provides a convenient way to
        execute operations on the MongoDB client with the given alias.
        此方法创建一个MongoExecutor，提供了一种在具有给定别名的MongoDB客户端上
        执行操作的便捷方式。

        Args:
            alias: The alias of the MongoDB client to use.
                  要使用的MongoDB客户端的别名。

        Returns:
            MongoExecutor: An executor for the MongoDB client.
                          MongoDB客户端的执行器。
        """
        return MongoExecutor(alias, self)

    async def close(self, alias: str):
        """
        Close a specific MongoDB client.
        关闭特定的MongoDB客户端。

        This method closes the MongoDB client with the given alias and removes it
        from the managed clients.
        此方法关闭具有给定别名的MongoDB客户端，并将其从管理的客户端中移除。

        Args:
            alias: The alias of the MongoDB client to close.
                  要关闭的MongoDB客户端的别名。

        Returns:
            None
        """
        # Remove the client from the managed clients
        # 从管理的客户端中移除客户端
        client_tuple = self._clients.pop(alias, None)

        # Close the client if it exists
        # 如果客户端存在，则关闭它
        if client_tuple:
            client, *_ = client_tuple
            client.close()

    async def close_all(self):
        """
        Close all MongoDB clients.
        关闭所有MongoDB客户端。

        This method closes all MongoDB clients managed by this manager.
        此方法关闭此管理器管理的所有MongoDB客户端。

        Returns:
            None
        """
        # Create a copy of the keys to avoid modifying the dictionary during iteration
        # 创建键的副本，以避免在迭代期间修改字典
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        """
        Initialize MongoDB clients from a configuration dictionary.
        从配置字典初始化MongoDB客户端。

        This method creates MongoDB clients based on the configuration in db_args.
        此方法根据db_args中的配置创建MongoDB客户端。

        Args:
            db_args: A dictionary mapping aliases to MongoDB connection parameters.
                    将别名映射到MongoDB连接参数的字典。
                    Example:
                    {
                        'default': {'host': 'mongodb://localhost:27017', 'db': 'mydb'},
                        'analytics': {'host': 'mongodb://analytics.example.com:27017', 'db': 'analytics'}
                    }

        Returns:
            None
        """
        for alias, args in db_args.items():
            await self.create(alias, args)

    async def from_settings(self, settings: aioscrapy.Settings):
        """
        Initialize MongoDB clients from aioscrapy settings.
        从aioscrapy设置初始化MongoDB客户端。

        This method creates MongoDB clients based on the MONGO_ARGS setting.
        此方法根据MONGO_ARGS设置创建MongoDB客户端。

        The MONGO_ARGS setting should be a dictionary mapping aliases to MongoDB
        connection parameters, for example:
        MONGO_ARGS设置应该是一个将别名映射到MongoDB连接参数的字典，例如：

        ```python
        MONGO_ARGS = {
            'default': {'host': 'mongodb://localhost:27017', 'db': 'mydb'},
            'analytics': {'host': 'mongodb://analytics.example.com:27017', 'db': 'analytics'}
        }
        ```

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """
        for alias, args in settings.getdict('MONGO_ARGS').items():
            await self.create(alias, args)


# Singleton instance of AioMongoManager
# AioMongoManager的单例实例
mongo_manager = AioMongoManager()

# Example usage
# 示例用法
if __name__ == '__main__':
    import asyncio


    async def test():
        """
        Test function demonstrating the usage of the MongoDB manager.
        演示MongoDB管理器用法的测试函数。
        """
        # Create a MongoDB client with alias 'default'
        # 创建别名为'default'的MongoDB客户端
        await mongo_manager.create('default', {
            'host': 'mongodb://root:root@192.168.234.128:27017',
            'db': 'test',
        })

        # Get a MongoDB executor for the 'default' client
        # 获取'default'客户端的MongoDB执行器
        mongo = mongo_manager.executor('default')

        # Insert documents into the 'user' collection
        # 向'user'集合插入文档
        inserted = await mongo.insert('user', [{'name': 'zhang', 'age': 18}, {'name': 'li', 'age': 20}])
        # Uncomment to print the number of inserted documents
        # 取消注释以打印插入的文档数量
        # print('inserted %d docs' % (len(inserted.inserted_ids),))

        # Query a document from the 'user' collection
        # 从'user'集合查询文档
        document = await mongo.user.find_one({'img_url': {'$gt': 19}})
        print(document)

        # Close all MongoDB clients
        # 关闭所有MongoDB客户端
        await mongo_manager.close_all()


    # Run the test function
    # 运行测试函数
    asyncio.get_event_loop().run_until_complete(test())
