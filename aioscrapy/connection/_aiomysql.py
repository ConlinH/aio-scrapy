from typing import Union, Tuple
from contextlib import asynccontextmanager

from aiomysql import create_pool


class AioMysqlManager(object):
    _clients = {}

    @staticmethod
    def parse_params(alias_or_params: Union[str, dict]) -> Tuple[str, Union[dict, None]]:
        if isinstance(alias_or_params, str):
            return alias_or_params, None

        mysql_params = alias_or_params.copy()
        alias = mysql_params.pop('alias', f"{mysql_params['host']}{mysql_params['port']}")
        return alias, mysql_params

    async def create(self, params: Union[dict], alias=None):
        if alias is None:
            alias, params = self.parse_params(params)
        mysql_pool = await create_pool(**params)
        return self._clients.setdefault(alias, mysql_pool)

    @asynccontextmanager
    async def get(self, alias_or_params: Union[str, dict], ping=False):
        """获取数据库链接和数据库游标"""
        assert isinstance(alias_or_params, (str, dict)), "alias_or_params 参数不正确"
        alias, params = self.parse_params(alias_or_params)
        mysql_pool = self._clients.get(alias)
        if not mysql_pool:
            mysql_pool = await self.create(params, alias)

        conn = await mysql_pool.acquire()
        if ping:
            await conn.ping()
        cur = await conn.cursor()
        yield conn, cur
        await cur.close()
        await mysql_pool.release(conn)

    async def close(self, alias_or_params: Union[str, dict]):
        assert isinstance(alias_or_params, (str, dict)), "alias_or_params 参数不正确"
        alias, _ = self.parse_params(alias_or_params)
        mysql_pool = self._clients.get(alias)
        if mysql_pool:
            mysql_pool.close()
            await mysql_pool.wait_closed()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)


mysql_manager = AioMysqlManager()

if __name__ == '__main__':
    import asyncio


    async def test():
        mysql_pool = await mysql_manager.create({
            'alias': 'xx',
            'db': 'test',
            'user': 'root',
            'password': 'root',
            'host': '192.168.5.237',
            'port': 3306,
            'charset': 'utf8',
        })

        # 方式一:
        try:
            conn = await mysql_pool.acquire()
            cur = await conn.cursor()
            print(await cur.execute('select 1'))
            # await conn.commit()
        finally:
            await cur.close()
            await mysql_pool.release(conn)

        # 方式二:
        async with mysql_manager.get('xx') as (conn, cur):
            print(await cur.execute('select 1'))
            # await conn.commit()

        await mysql_manager.close_all()


    asyncio.run(test())
