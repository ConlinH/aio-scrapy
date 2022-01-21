
from aioredis import BlockingConnectionPool, Redis

from .interface import IManager


class AioRedisManager(IManager):
    _clients = {}

    async def create(self, alias: str, params: dict) -> Redis:
        url = params.pop('url', None)
        if url:
            connection_pool = BlockingConnectionPool.from_url(url, **params)
        else:
            connection_pool = BlockingConnectionPool(**params)
        redis = Redis(connection_pool=connection_pool)
        return self._clients.setdefault(alias, redis)

    def get_pool(self, alias: str):
        """获取数据库链接和数据库游标"""
        redis_pool = self._clients.get(alias)
        assert redis_pool is not None, f"redis没有创建该连接池： {alias}"
        return redis_pool

    async def close(self, alias: str):
        """关闭指定redis pool"""
        redis = self._clients.pop(alias, None)
        if redis:
            await redis.close()
            await redis.connection_pool.disconnect()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_settings(self, settings: "scrapy.settings.Setting"):
        for alias, redis_args in settings.getdict('REDIS_ARGS').items():
            await self.create(alias, redis_args)


redis_manager = AioRedisManager()


if __name__ == '__main__':
    import asyncio

    async def test():
        redis = await redis_manager.create('default', {
                'url': 'redis://:erpteam_redis@192.168.5.216:6381/9',
                'max_connections': 4
            })

        await redis.zadd('key1', {'value': 1})

        async with redis.pipeline(transaction=True) as pipe:
            results, count = await (
                pipe.zrange('key1', 0, 0)
                    .zremrangebyrank('key1', 0, 0)
                    .execute()
            )

        print(results)
        await redis_manager.close_all()


    # asyncio.run(test(), debug=True)
    asyncio.get_event_loop().run_until_complete(test())

