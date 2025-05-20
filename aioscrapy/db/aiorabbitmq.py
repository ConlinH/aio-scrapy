"""
RabbitMQ connection manager for aioscrapy.
aioscrapy的RabbitMQ连接管理器。

This module provides classes for managing RabbitMQ connections in aioscrapy.
It includes a connection manager for creating and managing RabbitMQ connections and channels,
and an executor for convenient access to RabbitMQ operations.
此模块提供了在aioscrapy中管理RabbitMQ连接的类。
它包括一个用于创建和管理RabbitMQ连接和通道的连接管理器，以及一个用于方便访问RabbitMQ操作的执行器。
"""

from contextlib import asynccontextmanager

import aio_pika
from aio_pika.exceptions import QueueEmpty
from aio_pika.pool import Pool

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class RabbitmqExecutor:
    """
    Executor for RabbitMQ operations.
    RabbitMQ操作的执行器。

    This class provides a convenient way to execute RabbitMQ operations on a specific
    RabbitMQ connection. It offers methods for publishing messages, getting messages,
    checking queue counts, and cleaning message queues.
    此类提供了一种在特定RabbitMQ连接上执行RabbitMQ操作的便捷方式。
    它提供了发布消息、获取消息、检查队列计数和清理消息队列的方法。
    """

    def __init__(self, alias: str, pool_manager: "AioRabbitmqManager"):
        """
        Initialize a RabbitmqExecutor.
        初始化RabbitmqExecutor。

        Args:
            alias: The alias of the RabbitMQ connection to use.
                  要使用的RabbitMQ连接的别名。
            pool_manager: The RabbitMQ manager that manages the connection.
                         管理连接的RabbitMQ管理器。
        """
        self.alias = alias
        self.pool_manager = pool_manager

    async def clean_message_queue(
            self,
            routing_key: str,
            *args,
            if_unused=False,
            if_empty=False,
            timeout=None,
            **kwargs
    ):
        """
        Clean (delete) a message queue.
        清理（删除）消息队列。

        This method deletes a queue with the specified routing key.
        此方法删除具有指定路由键的队列。

        Args:
            routing_key: The routing key (queue name) to delete.
                        要删除的路由键（队列名称）。
            *args: Additional arguments to pass to declare_queue.
                  传递给declare_queue的其他参数。
            if_unused: If True, the queue will only be deleted if it has no consumers.
                      如果为True，则只有当队列没有消费者时才会删除它。
            if_empty: If True, the queue will only be deleted if it has no messages.
                     如果为True，则只有当队列没有消息时才会删除它。
            timeout: Deletion timeout in seconds.
                    删除超时（秒）。
            **kwargs: Additional keyword arguments to pass to declare_queue.
                     传递给declare_queue的其他关键字参数。

        Returns:
            None
        """
        async with self.pool_manager.get(self.alias) as channel:
            # Declare the queue to ensure it exists
            # 声明队列以确保它存在
            queue = await channel.declare_queue(routing_key, *args, **kwargs)

            # Delete the queue
            # 删除队列
            await queue.delete(if_unused=if_unused, if_empty=if_empty, timeout=timeout)

    async def get_message_count(
            self,
            routing_key: str,
            *args,
            **kwargs
    ):
        """
        Get the number of messages in a queue.
        获取队列中的消息数量。

        This method returns the number of messages in a queue with the specified routing key.
        It attempts to get a message from the queue (without removing it) to check the message count.
        此方法返回具有指定路由键的队列中的消息数量。
        它尝试从队列中获取一条消息（不删除它）以检查消息计数。

        Args:
            routing_key: The routing key (queue name) to check.
                        要检查的路由键（队列名称）。
            *args: Additional arguments to pass to declare_queue.
                  传递给declare_queue的其他参数。
            **kwargs: Additional keyword arguments to pass to declare_queue.
                     传递给declare_queue的其他关键字参数。

        Returns:
            int: The number of messages in the queue, or 0 if the queue is empty.
                 队列中的消息数量，如果队列为空则为0。
        """
        async with self.pool_manager.get(self.alias) as channel:
            # Declare the queue to ensure it exists
            # 声明队列以确保它存在
            queue = await channel.declare_queue(routing_key, *args, **kwargs)

            try:
                # Try to get a message without acknowledging it
                # 尝试获取一条消息而不确认它
                result = await queue.get(no_ack=False)

                # Negative acknowledgment to return the message to the queue
                # 负确认以将消息返回到队列
                await result.nack()

                # Return the message count
                # 返回消息计数
                return result.message_count
            except QueueEmpty:
                # If the queue is empty, return 0
                # 如果队列为空，则返回0
                return 0

    async def get_message(
            self,
            routing_key: str,
            *args,
            **kwargs
    ):
        """
        Get a message from a queue.
        从队列中获取消息。

        This method retrieves and removes a message from a queue with the specified routing key.
        If the queue is empty, it returns None.
        此方法从具有指定路由键的队列中检索并删除一条消息。
        如果队列为空，则返回None。

        Args:
            routing_key: The routing key (queue name) to get a message from.
                        要从中获取消息的路由键（队列名称）。
            *args: Additional arguments to pass to declare_queue.
                  传递给declare_queue的其他参数。
            **kwargs: Additional keyword arguments to pass to declare_queue.
                     传递给declare_queue的其他关键字参数。

        Returns:
            bytes: The message body, or None if the queue is empty.
                  消息体，如果队列为空则为None。
        """
        async with self.pool_manager.get(self.alias) as channel:
            # Declare the queue to ensure it exists
            # 声明队列以确保它存在
            queue = await channel.declare_queue(routing_key, *args, **kwargs)

            try:
                # Try to get a message with auto-acknowledgment
                # 尝试获取一条消息并自动确认
                result = await queue.get(no_ack=True)

                # Return the message body
                # 返回消息体
                return result.body
            except QueueEmpty:
                # If the queue is empty, return None
                # 如果队列为空，则返回None
                return None

    async def publish(
            self,
            routing_key: str,
            body: bytes,
            *args,
            mandatory=True,
            immediate=False,
            timeout=None,
            **kwargs
    ):
        """
        Publish a message to a queue.
        向队列发布消息。

        This method publishes a message to a queue with the specified routing key.
        此方法向具有指定路由键的队列发布消息。

        Args:
            routing_key: The routing key (queue name) to publish to.
                        要发布到的路由键（队列名称）。
            body: The message body as bytes.
                 消息体（字节）。
            *args: Additional arguments to pass to Message constructor.
                  传递给Message构造函数的其他参数。
            mandatory: If True, the server will return an unroutable message to the client.
                      如果为True，服务器将向客户端返回不可路由的消息。
            immediate: If True, the server will return a message if it cannot be routed to a queue consumer immediately.
                      如果为True，如果消息不能立即路由到队列消费者，服务器将返回消息。
            timeout: Publish timeout in seconds.
                    发布超时（秒）。
            **kwargs: Additional keyword arguments to pass to Message constructor.
                     传递给Message构造函数的其他关键字参数。

        Returns:
            bool: True if the message was published successfully.
                 如果消息发布成功，则为True。
        """
        async with self.pool_manager.get(self.alias) as channel:
            # Create a message with the provided body and arguments
            # 使用提供的消息体和参数创建消息
            message = aio_pika.Message(body, *args, **kwargs)

            # Publish the message to the default exchange with the specified routing key
            # 使用指定的路由键将消息发布到默认交换机
            return await channel.default_exchange.publish(
                message,
                routing_key,
                mandatory=mandatory,
                immediate=immediate,
                timeout=timeout
            )


class AioRabbitmqManager(AbsDBPoolManager):
    """
    Manager for RabbitMQ connections.
    RabbitMQ连接的管理器。

    This class manages RabbitMQ connections and channels. It implements the
    AbsDBPoolManager interface for RabbitMQ connections, providing methods for
    creating, accessing, and closing RabbitMQ connections and channels.
    此类管理RabbitMQ连接和通道。它为RabbitMQ连接实现了AbsDBPoolManager接口，
    提供了创建、访问和关闭RabbitMQ连接和通道的方法。
    """

    # Dictionary to store RabbitMQ connection and channel pools by alias
    # 按别名存储RabbitMQ连接和通道池的字典
    _clients = {}

    @staticmethod
    async def get_channel(connection_pool):
        """
        Get a channel from a connection pool.
        从连接池获取通道。

        This static method acquires a connection from the connection pool
        and creates a channel from that connection.
        此静态方法从连接池获取连接，并从该连接创建通道。

        Args:
            connection_pool: The RabbitMQ connection pool.
                            RabbitMQ连接池。

        Returns:
            Channel: A RabbitMQ channel.
                    RabbitMQ通道。
        """
        # Acquire a connection from the pool
        # 从池中获取连接
        async with connection_pool.acquire() as connection:
            # Create and return a channel from the connection
            # 从连接创建并返回通道
            return await connection.channel()

    async def create(self, alias: str, params: dict):
        """
        Create new RabbitMQ connection and channel pools.
        创建新的RabbitMQ连接和通道池。

        This method creates new RabbitMQ connection and channel pools with the given alias and parameters.
        If pools with the given alias already exist, it returns the existing pools.
        此方法使用给定的别名和参数创建新的RabbitMQ连接和通道池。
        如果具有给定别名的池已经存在，则返回现有池。

        Args:
            alias: The alias for the new RabbitMQ pools.
                  新RabbitMQ池的别名。
            params: The parameters for creating the RabbitMQ pools. Must include:
                   创建RabbitMQ池的参数。必须包括：
                   - url: RabbitMQ connection URL (required)
                          RabbitMQ连接URL（必需）
                   - connection_max_size: Maximum number of connections in the pool
                                         池中的最大连接数
                   - channel_max_size: Maximum number of channels in the pool
                                      池中的最大通道数

        Returns:
            tuple: A tuple containing (connection_pool, channel_pool).
                  包含(连接池, 通道池)的元组。

        Raises:
            AssertionError: If the URL parameter is missing.
                           如果缺少URL参数。
        """
        # Return existing pools if they exist
        # 如果池已存在，则返回现有池
        if alias in self._clients:
            return self._clients[alias]

        # Make a copy of params to avoid modifying the original
        # 复制params以避免修改原始参数
        params = params.copy()

        # Extract required URL parameter
        # 提取必需的URL参数
        url = params.pop('url', None)
        assert url, "Must args url"

        # Extract pool size parameters
        # 提取池大小参数
        connection_max_size = params.pop('connection_max_size', None)
        channel_max_size = params.pop('channel_max_size', None)

        # Create connection pool
        # 创建连接池
        connection_pool: Pool = Pool(aio_pika.connect_robust, url, max_size=connection_max_size)

        # Create channel pool that uses the connection pool
        # 创建使用连接池的通道池
        channel_pool: Pool = Pool(self.get_channel, connection_pool, max_size=channel_max_size)

        # Store and return the pools
        # 存储并返回池
        return self._clients.setdefault(alias, (connection_pool, channel_pool))

    def get_pool(self, alias: str):
        """
        Get RabbitMQ connection and channel pools by their alias.
        通过别名获取RabbitMQ连接和通道池。

        This method retrieves existing RabbitMQ connection and channel pools with the given alias.
        此方法检索具有给定别名的现有RabbitMQ连接和通道池。

        Args:
            alias: The alias of the RabbitMQ pools to retrieve.
                  要检索的RabbitMQ池的别名。

        Returns:
            tuple: A tuple containing (connection_pool, channel_pool).
                  包含(连接池, 通道池)的元组。

        Raises:
            AssertionError: If no RabbitMQ pools exist with the given alias.
                           如果不存在具有给定别名的RabbitMQ池。
        """
        # Get the pools from the clients dictionary
        # 从客户端字典获取池
        pools = self._clients.get(alias)

        if pools:
            connection_pool, channel_pool = pools
        else:
            connection_pool, channel_pool = None, None

        # Verify that both pools exist
        # 验证两个池都存在
        assert channel_pool is not None, f"Dont create the rabbitmq channel_pool named {alias}"
        assert connection_pool is not None, f"Dont create the rabbitmq connection_pool named {alias}"

        return connection_pool, channel_pool

    @asynccontextmanager
    async def get(self, alias: str):
        """
        Get a RabbitMQ channel as an async context manager.
        获取RabbitMQ通道作为异步上下文管理器。

        This method provides a convenient way to acquire a channel
        from a RabbitMQ channel pool, and automatically release it when the
        context is exited.
        此方法提供了一种从RabbitMQ通道池获取通道的便捷方式，
        并在退出上下文时自动释放它。

        Example:
            ```python
            async with rabbitmq_manager.get('default') as channel:
                await channel.declare_queue('my_queue')
            ```

        Args:
            alias: The alias of the RabbitMQ pools to use.
                  要使用的RabbitMQ池的别名。

        Yields:
            Channel: A RabbitMQ channel.
                    RabbitMQ通道。
        """
        # Get the connection and channel pools
        # 获取连接和通道池
        _, channel_pool = self.get_pool(alias)

        # Acquire a channel from the channel pool
        # 从通道池获取通道
        async with channel_pool.acquire() as channel:
            # Yield the channel to the caller
            # 将通道传递给调用者
            yield channel

    def executor(self, alias: str) -> RabbitmqExecutor:
        """
        Get a RabbitmqExecutor for a specific RabbitMQ connection.
        获取特定RabbitMQ连接的RabbitmqExecutor。

        This method creates a RabbitmqExecutor that provides a convenient way to
        execute operations on the RabbitMQ connection with the given alias.
        此方法创建一个RabbitmqExecutor，提供了一种在具有给定别名的RabbitMQ连接上
        执行操作的便捷方式。

        Args:
            alias: The alias of the RabbitMQ connection to use.
                  要使用的RabbitMQ连接的别名。

        Returns:
            RabbitmqExecutor: An executor for the RabbitMQ connection.
                             RabbitMQ连接的执行器。
        """
        return RabbitmqExecutor(alias, self)

    async def close(self, alias: str):
        """
        Close specific RabbitMQ connection and channel pools.
        关闭特定的RabbitMQ连接和通道池。

        This method closes the RabbitMQ connection and channel pools with the given alias
        and removes them from the managed pools.
        此方法关闭具有给定别名的RabbitMQ连接和通道池，并将它们从管理的池中移除。

        Args:
            alias: The alias of the RabbitMQ pools to close.
                  要关闭的RabbitMQ池的别名。

        Returns:
            None
        """
        # Remove the pools from the managed pools
        # 从管理的池中移除池
        connection_pool, channel_pool = self._clients.pop(alias, (None, None))
        connection_pool: Pool
        channel_pool: Pool

        # Close the channel pool if it exists
        # 如果通道池存在，则关闭它
        if channel_pool:
            await channel_pool.close()

        # Close the connection pool if it exists
        # 如果连接池存在，则关闭它
        if connection_pool:
            await connection_pool.close()

    async def close_all(self):
        """
        Close all RabbitMQ connection and channel pools.
        关闭所有RabbitMQ连接和通道池。

        This method closes all RabbitMQ connection and channel pools managed by this manager.
        此方法关闭此管理器管理的所有RabbitMQ连接和通道池。

        Returns:
            None
        """
        # Create a copy of the keys to avoid modifying the dictionary during iteration
        # 创建键的副本，以避免在迭代期间修改字典
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        """
        Initialize RabbitMQ pools from a configuration dictionary.
        从配置字典初始化RabbitMQ池。

        This method creates RabbitMQ connection and channel pools based on the configuration in db_args.
        此方法根据db_args中的配置创建RabbitMQ连接和通道池。

        Args:
            db_args: A dictionary mapping aliases to RabbitMQ connection parameters.
                    将别名映射到RabbitMQ连接参数的字典。
                    Example:
                    {
                        'default': {
                            'url': 'amqp://guest:guest@localhost:5672/',
                            'connection_max_size': 2,
                            'channel_max_size': 10
                        },
                        'analytics': {
                            'url': 'amqp://user:password@analytics.example.com:5672/',
                            'connection_max_size': 5,
                            'channel_max_size': 20
                        }
                    }

        Returns:
            None
        """
        for alias, rabbitmq_args in db_args.items():
            await self.create(alias, rabbitmq_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        """
        Initialize RabbitMQ pools from aioscrapy settings.
        从aioscrapy设置初始化RabbitMQ池。

        This method creates RabbitMQ connection and channel pools based on the RABBITMQ_ARGS setting.
        此方法根据RABBITMQ_ARGS设置创建RabbitMQ连接和通道池。

        The RABBITMQ_ARGS setting should be a dictionary mapping aliases to RabbitMQ
        connection parameters, for example:
        RABBITMQ_ARGS设置应该是一个将别名映射到RabbitMQ连接参数的字典，例如：

        ```python
        RABBITMQ_ARGS = {
            'default': {
                'url': 'amqp://guest:guest@localhost:5672/',
                'connection_max_size': 2,
                'channel_max_size': 10
            },
            'analytics': {
                'url': 'amqp://user:password@analytics.example.com:5672/',
                'connection_max_size': 5,
                'channel_max_size': 20
            }
        }
        ```

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。

        Returns:
            None
        """
        for alias, rabbitmq_args in settings.getdict('RABBITMQ_ARGS').items():
            await self.create(alias, rabbitmq_args)


# Singleton instance of AioRabbitmqManager
# AioRabbitmqManager的单例实例
rabbitmq_manager = AioRabbitmqManager()

# Example usage
# 示例用法
if __name__ == '__main__':
    import asyncio


    async def test():
        """
        Test function demonstrating the usage of the RabbitMQ manager.
        演示RabbitMQ管理器用法的测试函数。
        """
        # Create RabbitMQ connection and channel pools with alias 'default'
        # 创建别名为'default'的RabbitMQ连接和通道池
        await rabbitmq_manager.create('default', {
            'url': "amqp://guest:guest@192.168.234.128:5673/",
            'connection_max_size': 2,
            'channel_max_size': 10,
        })

        # Define a queue name for testing
        # 定义用于测试的队列名称
        queue_name = 'pool_queue'

        # Get a RabbitMQ executor for the 'default' connection
        # 获取'default'连接的RabbitMQ执行器
        execute = rabbitmq_manager.executor('default')

        # Publish 10 messages to the queue
        # 向队列发布10条消息
        for i in range(10):
            result = await execute.publish(queue_name, f"msg{i}".encode(), priority=3)
            print(result)

        # Get and print the message count
        # 获取并打印消息计数
        print(await execute.get_message_count(queue_name))

        # Get and print 5 messages from the queue
        # 从队列获取并打印5条消息
        for i in range(5):
            print(await execute.get_message(queue_name))
            print(await execute.get_message_count(queue_name))

        # Clean the message queue and print the result
        # 清理消息队列并打印结果
        print(await execute.clean_message_queue(queue_name))

        # Verify the queue is empty
        # 验证队列为空
        print(await execute.get_message_count(queue_name))

        # Close all RabbitMQ connections and channels
        # 关闭所有RabbitMQ连接和通道
        await rabbitmq_manager.close_all()


    # Run the test function
    # 运行测试函数
    asyncio.get_event_loop().run_until_complete(test())
