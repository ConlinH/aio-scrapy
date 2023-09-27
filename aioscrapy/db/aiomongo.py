from motor.motor_asyncio import AsyncIOMotorClient

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager


class MongoExecutor:
    def __init__(self, alias: str, pool_manager: "AioMongoManager"):
        self.alias = alias
        self.pool_manager = pool_manager

    async def insert(self, table_name, values, db_name=None):
        client, db_name_default = self.pool_manager.get_pool(self.alias)
        db_name = db_name or db_name_default
        return await client[f'{db_name}'][f'{table_name}'].insert_many(values)

    def __getattr__(self, table_name: str):
        client, db_name_default = self.pool_manager.get_pool(self.alias)
        return client[f'{db_name_default}'][f'{table_name}']


class AioMongoManager(AbsDBPoolManager):
    _clients = {}

    async def create(self, alias: str, params: dict):
        if alias in self._clients:
            return self._clients[alias]

        params = params.copy()
        db_name = params.pop('db')
        params.setdefault('connecttimeoutms', 30)
        client = AsyncIOMotorClient(**params)
        return self._clients.setdefault(alias, (client, db_name))

    def get_pool(self, alias: str):
        return self._clients.get(alias)

    def executor(self, alias: str) -> MongoExecutor:
        """Get RedisExecutor"""
        return MongoExecutor(alias, self)

    async def close(self, alias: str):
        """Close mongo pool named `alias`"""
        client, *_ = self._clients.pop(alias, None)
        if client:
            client.close()

    async def close_all(self):
        """Close all clients of mongo"""
        for alias in list(self._clients.keys()):
            await self.close(alias)

    async def from_dict(self, db_args: dict):
        """Create mongo with dict"""
        for alias, args in db_args.items():
            await self.create(alias, args)

    async def from_settings(self, settings: aioscrapy.Settings):
        """Create mongo with settings"""
        for alias, args in settings.getdict('MONGO_ARGS').items():
            await self.create(alias, args)


mongo_manager = AioMongoManager()

if __name__ == '__main__':
    import asyncio


    async def test():
        await mongo_manager.create('default', {
            'host': 'mongodb://root:root@192.168.234.128:27017',
            'db': 'test',
        })
        mongo = mongo_manager.executor('default')
        result = await mongo.insert('user', [{'name': 'zhang', 'age': 18}, {'name': 'li', 'age': 20}])
        # print('inserted %d docs' % (len(result.inserted_ids),))

        document = await mongo.user.find_one({'img_url': {'$gt': 19}})
        print(document)
        await mongo_manager.close_all()


    asyncio.get_event_loop().run_until_complete(test())
