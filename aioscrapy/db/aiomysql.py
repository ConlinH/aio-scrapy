import socket
from contextlib import asynccontextmanager

from aiomysql import create_pool

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class MysqlExecutor:
    def __init__(self, alias: str, pool_manager: "AioMysqlPoolManager"):
        self.alias = alias
        self.pool_manager = pool_manager

    async def insert(self, sql, value):
        async with self.pool_manager.get(self.alias) as (connect, cursor):
            try:
                result = await cursor.executemany(sql, value)
                await connect.commit()
                return result
            except Exception as e:
                await connect.rollback()
                raise Exception from e

    async def execute(self, sql: str):
        async with self.pool_manager.get(self.alias) as (connect, cursor):
            await cursor.execute(sql)
            return await cursor.fetchall()

    async def query(self, sql: str):
        return await self.execute(sql)


class AioMysqlPoolManager(AbsDBPoolManager):
    _clients = {}

    async def create(self, alias: str, params: dict):
        if alias in self._clients:
            return self._clients[alias]

        params = params.copy()
        # When the host is domain,converted to IP
        # https://github.com/aio-libs/aiomysql/issues/641
        params.update({'host': socket.gethostbyname(params['host'])})
        params.setdefault('connect_timeout', 30)
        mysql_pool = await create_pool(**params)
        return self._clients.setdefault(alias, mysql_pool)

    def get_pool(self, alias: str):
        mysql_pool = self._clients.get(alias)
        assert mysql_pool is not None, f"Dont create the mysql pool named {alias}"
        return mysql_pool

    @asynccontextmanager
    async def get(self, alias: str, ping=False):
        """Get connection and cursor of mysql"""
        mysql_pool = self.get_pool(alias)
        conn = await mysql_pool.acquire()
        cur = await conn.cursor()
        try:
            if ping:
                await conn.ping()
            yield conn, cur
        finally:
            await cur.close()
            await mysql_pool.release(conn)

    def executor(self, alias: str) -> MysqlExecutor:
        return MysqlExecutor(alias, self)

    async def close(self, alias: str):
        mysql_pool = self._clients.pop(alias, None)
        if mysql_pool:
            mysql_pool.close()
            await mysql_pool.wait_closed()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        for alias, mysql_args in db_args.items():
            await self.create(alias, mysql_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        for alias, mysql_args in settings.getdict('MYSQL_ARGS').items():
            await self.create(alias, mysql_args)


mysql_manager = AioMysqlPoolManager()

if __name__ == '__main__':
    import asyncio


    async def test():
        mysql_pool = await mysql_manager.create('default', {
            'db': 'mysql',
            'user': 'root',
            'password': '123456',
            'host': '192.168.234.128',
            'port': 3306
        })

        # 方式一:
        try:
            conn = await mysql_pool.acquire()
            cur = await conn.cursor()
            await cur.execute('select * from user')
            print(await cur.fetchall())
            # await conn.commit()
        finally:
            await cur.close()
            await mysql_pool.release(conn)

        # 方式二:
        async with mysql_manager.get('xxx') as (conn, cur):
            print(await cur.execute('select 1'))
            # await conn.commit()

        await mysql_manager.close_all()


    asyncio.run(test())
