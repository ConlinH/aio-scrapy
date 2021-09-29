from typing import Union, Tuple

from aioredis import BlockingConnectionPool, Redis


class AioRedisManager(object):
    _clients = {}

    @staticmethod
    def parse_params(alias_or_params:  Union[str, dict]) -> Tuple[str, Union[dict, None]]:
        """
        将参数中的别名和redis参数提取出来
        """
        if isinstance(alias_or_params, str):
            return alias_or_params, None

        redis_params = alias_or_params.copy()
        url = redis_params.get('url')
        db = redis_params.get('db', '')
        alias = redis_params.pop('alias', url + str(db))
        return alias, redis_params

    def create(self, params: Union[dict], alias=None) -> Redis:
        if alias is None:
            alias, params = self.parse_params(params)
        url = params.pop('url')
        redis = Redis(connection_pool=BlockingConnectionPool.from_url(url, **params))
        return self._clients.setdefault(alias, redis)

    def get(self, alias_or_params: Union[str, dict]) -> Redis:
        """获取redis链接"""
        assert isinstance(alias_or_params, (str, dict)), "alias_or_params 参数不正确"
        alias, redis_params = self.parse_params(alias_or_params)
        redis = self._clients.get(alias)
        if redis:
            return redis
        return self.create(redis_params, alias)

    async def close(self, alias_or_params: Union[str, dict]):
        """关闭指定redis pool"""
        assert isinstance(alias_or_params, (str, dict)), "alias_or_params 参数不正确"
        alias, _ = self.parse_params(alias_or_params)
        redis = self._clients.pop(alias, None)
        if redis:
            await redis.close()
            await redis.connection_pool.disconnect()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_settings(self, settings: "scrapy.settings.Setting"):
        redis_args = settings.getdict('REDIS_ARGS')
        return self.get(redis_args)

    async def from_crawler(self, crawler):
        return await self.from_settings(crawler.settings)


redis_manager = AioRedisManager()


if __name__ == '__main__':
    import asyncio

    async def test():
        redis = redis_manager.get({
                'alias': 'xx',
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

