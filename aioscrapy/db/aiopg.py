from contextlib import asynccontextmanager

from asyncpg.pool import create_pool

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class PGExecutor:
    def __init__(self, alias: str, pool_manager: "AioPGPoolManager"):
        self.alias = alias
        self.pool_manager = pool_manager

    async def insert(self, sql, value):
        async with self.pool_manager.get(self.alias) as connect:
            try:
                result = await connect.executemany(sql, value)
                return result
            except Exception as e:
                await connect.rollback()
                raise Exception from e

    async def fetch(self, sql: str):
        async with self.pool_manager.get(self.alias) as connect:
            return await connect.fetch(sql)

    async def query(self, sql: str):
        return await self.fetch(sql)


class AioPGPoolManager(AbsDBPoolManager):
    _clients = {}

    async def create(self, alias: str, params: dict):
        if alias in self._clients:
            return self._clients[alias]

        params = params.copy()
        params.setdefault('timeout', 30)
        pg_pool = await create_pool(**params)
        return self._clients.setdefault(alias, pg_pool)

    def get_pool(self, alias: str):
        pg_pool = self._clients.get(alias)
        assert pg_pool is not None, f"Dont create the PG pool named {alias}"
        return pg_pool

    @asynccontextmanager
    async def get(self, alias: str):
        """ Get connection of pg """
        pg_pool = self.get_pool(alias)
        conn = await pg_pool.acquire()
        try:
            yield conn
        finally:
            await pg_pool.release(conn)

    def executor(self, alias: str) -> PGExecutor:
        return PGExecutor(alias, self)

    async def close(self, alias: str):
        pg_pool = self._clients.pop(alias, None)
        if pg_pool:
            await pg_pool.close()

    async def close_all(self):
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        for alias, pg_args in db_args.items():
            await self.create(alias, pg_args)

    async def from_settings(self, settings: aioscrapy.Settings):
        for alias, pg_args in settings.getdict('PG_ARGS').items():
            await self.create(alias, pg_args)


pg_manager = AioPGPoolManager()

if __name__ == '__main__':
    import asyncio


    async def test():
        pg_pool = await pg_manager.create(
            'default',
            dict(
                user='username',
                password='pwd',
                database='dbname',
                host='127.0.0.1'
            )
        )

        # 方式一:
        conn = await pg_pool.acquire()
        try:
            result = await conn.fetch('select 1 ')
            print(tuple(result[0]))
        finally:
            await pg_pool.release(conn)

        # 方式二:
        async with pg_manager.get('default') as conn:
            result = await conn.fetch('select 1 ')
            print(tuple(result[0]))


    asyncio.run(test())
