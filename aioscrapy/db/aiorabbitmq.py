from contextlib import asynccontextmanager

import aio_pika
from aio_pika.exceptions import QueueEmpty
from aio_pika.pool import Pool

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class RabbitmqExecutor:
    def __init__(self, alias: str, pool_manager: "AioRabbitmqManager"):
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
        async with self.pool_manager.get(self.alias) as channel:
            queue = await channel.declare_queue(routing_key, *args, **kwargs)
            await queue.delete(if_unused=if_unused, if_empty=if_empty, timeout=timeout)

    async def get_message_count(
            self,
            routing_key: str,
            *args,
            **kwargs
    ):
        async with self.pool_manager.get(self.alias) as channel:
            queue = await channel.declare_queue(routing_key, *args, **kwargs)
            try:
                result = await queue.get(no_ack=False)
                await result.nack()
                return result.message_count
            except QueueEmpty:
                return 0

    async def get_message(
            self,
            routing_key: str,
            *args,
            **kwargs
    ):
        async with self.pool_manager.get(self.alias) as channel:
            queue = await channel.declare_queue(routing_key, *args, **kwargs)
            try:
                result = await queue.get(no_ack=True)
                return result.body
            except QueueEmpty:
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
        async with self.pool_manager.get(self.alias) as channel:
            return await channel.default_exchange.publish(
                aio_pika.Message(body, *args, **kwargs),
                routing_key,
                mandatory=mandatory,
                immediate=immediate,
                timeout=timeout
            )


class AioRabbitmqManager(AbsDBPoolManager):
    _clients = {}

    @staticmethod
    async def get_channel(connection_pool):
        async with connection_pool.acquire() as connection:
            return await connection.channel()

    async def create(self, alias: str, params: dict):
        if alias in self._clients:
            return self._clients[alias]

        params = params.copy()
        url = params.pop('url', None)
        assert url, "Must args url"
        connection_max_size = params.pop('connection_max_size', None)
        channel_max_size = params.pop('channel_max_size', None)

        connection_pool: Pool = Pool(aio_pika.connect_robust, url, max_size=connection_max_size)
        channel_pool: Pool = Pool(self.get_channel, connection_pool, max_size=channel_max_size)

        return self._clients.setdefault(alias, (connection_pool, channel_pool))

    def get_pool(self, alias: str):
        connection_pool, channel_pool = self._clients.get(alias)
        assert channel_pool is not None, f"Dont create the rabbitmq channel_pool named {alias}"
        assert connection_pool is not None, f"Dont create the rabbitmq connection_pool named {alias}"
        return connection_pool, channel_pool

    @asynccontextmanager
    async def get(self, alias: str):
        connection_pool, channel_pool = self.get_pool(alias)
        async with channel_pool.acquire() as channel:
            yield channel

    def executor(self, alias: str) -> RabbitmqExecutor:
        return RabbitmqExecutor(alias, self)

    async def close(self, alias: str):
        connection_pool, channel_pool = self._clients.pop(alias, (None, None))
        connection_pool: Pool
        channel_pool: Pool
        if channel_pool:
            await channel_pool.close()

        if connection_pool:
            await connection_pool.close()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        for alias, rabbitmq_args in db_args.items():
            await self.create(alias, rabbitmq_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        for alias, rabbitmq_args in settings.getdict('RABBITMQ_ARGS').items():
            await self.create(alias, rabbitmq_args)


rabbitmq_manager = AioRabbitmqManager()

if __name__ == '__main__':
    import asyncio


    async def test():
        _, channel_pool = await rabbitmq_manager.create('default', {
            'url': "amqp://guest:guest@192.168.234.128:5673/",
            'connection_max_size': 2,
            'channel_max_size': 10,
        })

        queue_name = 'pool_queue'
        execute = rabbitmq_manager.executor('default')

        for i in range(10):
            result = await execute.publish(queue_name, f"msg{i}".encode(), priority=3)
            print(result)

        print(await execute.get_message_count(queue_name))

        for i in range(5):
            print(await execute.get_message(queue_name))
            print(await execute.get_message_count(queue_name))

        print(await execute.clean_message_queue(queue_name))
        print(await execute.get_message_count(queue_name))

        await rabbitmq_manager.close_all()


    asyncio.get_event_loop().run_until_complete(test())
