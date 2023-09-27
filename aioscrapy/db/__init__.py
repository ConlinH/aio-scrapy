from importlib import import_module
from typing import Any

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager
from aioscrapy.db.aioredis import redis_manager
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_object

__all__ = ['db_manager', 'get_pool', 'get_manager']

DB_MODULE_MAP = {
    'redis': ('redis', 'aioscrapy.db.aioredis.redis_manager'),
    'aiomysql': ('mysql', 'aioscrapy.db.aiomysql.mysql_manager'),
    'aio_pika': ('rabbitmq', 'aioscrapy.db.aiorabbitmq.rabbitmq_manager'),
    'motor': ('mongo', 'aioscrapy.db.aiomongo.mongo_manager'),
    'asyncpg': ('pg', 'aioscrapy.db.aiopg.pg_manager'),
}

db_manager_map = {}

for module_name, (manager_key, class_path) in DB_MODULE_MAP.items():
    try:
        import_module(module_name)
    except ImportError:
        pass
    else:
        db_manager_map[manager_key] = load_object(class_path)


class DBManager:

    @staticmethod
    def get_manager(db_type: str) -> AbsDBPoolManager:
        manager = db_manager_map.get(db_type)
        assert manager is not None, f"Not support db type：{db_type}"
        return manager

    def get_pool(self, db_type: str, alias='default') -> Any:
        manager = self.get_manager(db_type)
        return manager.get_pool(alias)

    @staticmethod
    async def close_all() -> None:
        for manager in db_manager_map.values():
            await manager.close_all()

    @staticmethod
    async def from_dict(db_args: dict) -> None:
        for db_type, args in db_args.items():
            manager = db_manager_map.get(db_type)
            if manager is None:
                logger.warning(f'Not support db type: {db_type}; Only {", ".join(db_manager_map.keys())} supported')
            await manager.from_dict(args)

    @staticmethod
    async def from_settings(settings: aioscrapy.Settings) -> None:
        for manager in db_manager_map.values():
            await manager.from_settings(settings)

    async def from_crawler(self, crawler: "aioscrapy.Crawler") -> None:
        return await self.from_settings(crawler.settings)

    def __getattr__(self, db_type: str) -> Any:
        if db_type not in db_manager_map:
            raise AttributeError(f'Not support db type: {db_type}')
        return db_manager_map[db_type]


db_manager = DBManager()
get_manager = db_manager.get_manager
get_pool = db_manager.get_pool
