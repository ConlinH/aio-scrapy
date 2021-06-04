from contextlib import asynccontextmanager

from aiomysql import create_pool
from scrapy.settings import Settings

from aioscrapy.utils.tools import singleton


@singleton
class AioMysqlManager(object):
    _clients = {}

    @staticmethod
    def get_alias(params):
        if params is None:
            raise
        host = params.get('host')
        port = params.get('port')
        alias = params.pop('alias', host + str(port))
        return alias, params

    async def create(self, params, alias=None):
        if alias is None:
            alias, params = self.get_alias(params)
        pool = await create_pool(**params)
        return self._clients.setdefault(alias, pool)

    @asynccontextmanager
    async def get(self, alias_or_params, ping=False):
        if isinstance(alias_or_params, dict):
            alias, params = self.get_alias(alias_or_params)
            if not (pool := self._clients.get(alias)):
                pool = await self.create(params, alias=alias)
        elif isinstance(alias_or_params, str):
            alias = alias_or_params
            if not (pool := self._clients.get(alias)):
                raise
        else:
            raise

        conn = await pool.acquire()
        if ping:
            await conn.ping()
        cur = await conn.cursor()
        yield conn, cur
        await cur.close()
        await pool.release(conn)

    async def close(self, alias_or_params):
        if alias_or_params is dict:
            alias, _ = self.get_alias(alias_or_params)
        elif isinstance(alias_or_params, str):
            alias = alias_or_params
        else:
            raise

        if pool := self._clients.get(alias):
            pool.close()
            await pool.wait_closed()

    async def close_all(self):
        for pool in self._clients.values():
            pool.close()
            await pool.wait_closed()


mysql_manager = AioMysqlManager()

if __name__ == '__main__':
    import asyncio


    async def t():
        await mysql_manager.create({
            'db': 'test',
            'user': 'root',
            'password': '123456',
            'host': '172.16.177.22',
            'port': 3306,
            'charset': 'utf8',
        }, alias='xc')
        async with mysql_manager.get('xc') as (conn, cur):
            print(cur.execute('select 1'))
            # print(conn.commit())
        await mysql_manager.close_all()


    asyncio.run(t())
