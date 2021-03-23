from aioredis import create_redis_pool
from aioredis.util import parse_url
from scrapy.settings import Settings

from aioscrapy.utils.tools import singleton


@singleton
class AioRedisManager(object):
    _clients = {}

    @staticmethod
    def get_alias(redis_arg):
        if redis_arg is None:
            raise
        address = redis_arg.pop('address', None)
        db = redis_arg.pop('db', None)
        if isinstance(address, str):
            address, options = parse_url(address)
            db = options.setdefault('db', db)
            redis_arg.update(options)
            redis_arg.update({"address": address})
        alias = redis_arg.pop('alias', ''.join([str(i) for i in address]) + str(db))
        return alias, redis_arg

    async def create(self, params, alias=None):
        if alias is None:
            alias, params = self.get_alias(params)
        address = params.pop('address')
        con = await create_redis_pool(address, **params)
        return self._clients.setdefault(alias, con)

    async def get(self, alias_or_params):
        if isinstance(alias_or_params, dict):
            alias, params = self.get_alias(alias_or_params)
            if not (con := self._clients.get(alias)):
                return await self.create(params, alias=alias)
            return con
        elif isinstance(alias_or_params, str):
            alias = alias_or_params
            if con := self._clients.get(alias):
                return con
        raise

    async def close(self, alias_or_params):
        if alias_or_params is dict:
            alias, _ = self.get_alias(alias_or_params)
        elif isinstance(alias_or_params, str):
            alias = alias_or_params
        else:
            raise
        if con := self._clients.get(alias):
            await con.close()

    async def close_all(self):
        for con in self._clients.values():
            await con.close()

    async def from_settings(self, settings: Settings):
        redis_args = settings.getdict('REDIS_ARGS')
        return await self.get(redis_args)

    async def from_crawler(self, crawler):
        return await self.from_settings(crawler.settings)


redis_manager = AioRedisManager()
