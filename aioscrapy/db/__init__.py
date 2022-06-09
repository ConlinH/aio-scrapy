import logging

from aioscrapy.db._aioredis import redis_manager
from aioscrapy.db._aiomysql import mysql_manager
from aioscrapy.db._aiorabbitmq import rabbitmq_manager

logger = logging.getLogger(__name__)

__all__ = ['db_manager', 'get_pool', 'get_manager']


db_manager_map = {
    'mysql': mysql_manager,
    'redis': redis_manager,
    'rabbitmq': rabbitmq_manager,
}


class DBManager:

    @staticmethod
    def get_manager(db_type):
        manager = db_manager_map.get(db_type)
        assert manager is not None, f"暂时不支持该类型数据库：{db_type}"
        return manager

    def get_pool(self, db_type, alias='default'):
        manager = self.get_manager(db_type)
        return manager.get_pool(alias)

    @staticmethod
    async def close_all():
        for manager in db_manager_map.values():
            await manager.close_all()

    @staticmethod
    async def from_dict(db_args: dict):
        for db_type, args in db_args.items():
            manager = db_manager_map.get(db_type)
            if manager is None:
                logger.warning(f'Not support db type: {db_type}; Only {", ".join(db_manager_map.keys())} supported')
            await manager.from_dict(args)

    @staticmethod
    async def from_settings(settings: "aioscrapy.settings.Setting"):
        for manager in db_manager_map.values():
            await manager.from_settings(settings)

    async def from_crawler(self, crawler):
        return await self.from_settings(crawler.settings)

    def __getattr__(self, db_type: str):
        if db_type not in db_manager_map:
            raise AttributeError(f'Not support db type: {db_type}')
        return db_manager_map[db_type]


db_manager = DBManager()
get_manager = db_manager.get_manager
get_pool = db_manager.get_pool
