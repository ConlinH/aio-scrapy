import asyncio
import logging
from aioscrapy.db import db_manager

logger = logging.getLogger(__name__)


class MongoPipeline:
    def __init__(self, settings):
        self.cache_num = settings.getint('SAVE_CACHE_NUM', 500)
        self.save_cache_interval = settings.getint('SAVE_CACHE_INTERVAL', 10)
        self.lock = asyncio.Lock()
        self.running: bool = True
        self.db_alias_cache = {}
        self.table_cache = {}
        self.item_cache = {}
        self.db_cache = {}

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    async def open_spider(self, spider):
        asyncio.create_task(self.save_heartbeat())

    async def save_heartbeat(self):
        while self.running:
            await asyncio.sleep(self.save_cache_interval)
            asyncio.create_task(self.save_all())

    async def process_item(self, item, spider):
        await self.save_item(item)
        return item

    async def close_spider(self, spider):
        self.running = False
        await self.save_all()

    def parse_item_to_cache(self, item: dict):
        item.pop('save_insert_type', None)
        db_name = item.pop('save_db_name', None)
        table_name = item.pop('save_table_name', None)
        assert table_name is not None, Exception('please set save_table_name')
        save_db_alias = item.pop('save_db_alias', ['default'])
        if isinstance(save_db_alias, str):
            save_db_alias = [save_db_alias]

        cache_key = ''.join(save_db_alias) + (db_name or '') + table_name

        if self.table_cache.get(cache_key) is None:
            self.db_alias_cache[cache_key] = save_db_alias
            self.table_cache[cache_key] = table_name
            self.db_cache[cache_key] = db_name
            self.item_cache[cache_key] = []

        self.item_cache[cache_key].append(item)
        return cache_key, len(self.item_cache[cache_key])

    async def save_all(self):
        async with self.lock:
            for cache_key, items in self.item_cache.items():
                items and await self._save(cache_key)

    async def save_item(self, item: dict):
        async with self.lock:
            cache_key, cache_count = self.parse_item_to_cache(item)
            if cache_count >= self.cache_num:
                await self._save(cache_key)

    async def _save(self, cache_key):
        table_name = self.table_cache[cache_key]
        try:
            for alias in self.db_alias_cache[cache_key]:
                try:
                    executor = db_manager.mongo.executor(alias)
                    result = await executor.insert(
                        table_name, self.item_cache[cache_key], db_name=self.db_cache[cache_key]
                    )
                    logger.info(
                        f'table:{alias}->{table_name} sum:{len(self.item_cache[cache_key])} ok:{len(result.inserted_ids)}')
                except Exception as e:
                    logger.exception(f'save data error, table:{alias}->{table_name}, err_msg:{e}')
        finally:
            self.item_cache[cache_key] = []
