from typing import Union, Tuple

from aioredis import create_redis_pool, Redis
from aioredis.util import parse_url
from scrapy.settings import Settings


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
        address = redis_params.pop('address', None)
        db = redis_params.pop('db', None)
        if isinstance(address, str):
            address, options = parse_url(address)
            db = options.setdefault('db', db)
            redis_params.update(options)
            redis_params.update({"address": address})
        alias = redis_params.pop('alias', ''.join([str(i) for i in address]) + str(db))
        return alias, redis_params

    async def get(self, alias_or_params: Union[str, dict]) -> Redis:
        """获取redis链接"""
        assert isinstance(alias_or_params, (str, dict)), "alias_or_params 参数不正确"
        alias, redis_params = self.parse_params(alias_or_params)
        redis_pool = self._clients.get(alias)
        if redis_pool:
            return redis_pool
        address = redis_params.pop('address')
        redis_pool = await create_redis_pool(address, **redis_params)
        return self._clients.setdefault(alias, redis_pool)

    async def close(self, alias_or_params: Union[str, dict]):
        """关闭指定redis pool"""
        assert isinstance(alias_or_params, (str, dict)), "alias_or_params 参数不正确"
        alias, _ = self.parse_params(alias_or_params)
        redis_pool = self._clients.pop(alias, None)
        if redis_pool:
            redis_pool.close()
            await redis_pool.wait_closed()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_settings(self, settings: Settings):
        redis_args = settings.getdict('REDIS_ARGS')
        return await self.get(redis_args)

    async def from_crawler(self, crawler):
        return await self.from_settings(crawler.settings)


redis_manager = AioRedisManager()


if __name__ == '__main__':
    import asyncio

    async def test():
        r1 = await redis_manager.get({
                'alias': 'xx',
                'address': 'redis://:erpteam_redis@192.168.5.216:6381/9',
                'maxsize': 4
            })
        r2 = await redis_manager.get('xx')
        print(r1 is r2)
        await redis_manager.close_all()


    asyncio.run(test())
