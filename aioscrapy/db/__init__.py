import logging
from typing import Any

import aioscrapy
from aioscrapy.db.absmanager import AbsDBPoolManager
from aioscrapy.db.aioredis import redis_manager

db_manager_map = {
    'redis': redis_manager
}

try:
    from aiomysql import create_pool
    from aioscrapy.db.aiomysql import mysql_manager

    db_manager_map['mysql'] = mysql_manager
except ImportError:
    pass

try:
    import aio_pika
    from aioscrapy.db.aiorabbitmq import rabbitmq_manager

    db_manager_map['rabbitmq'] = rabbitmq_manager
except ImportError:
    pass

logger = logging.getLogger(__name__)

__all__ = ['db_manager', 'get_pool', 'get_manager']


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
