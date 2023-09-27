import asyncio

from aioscrapy.utils.log import logger
from aioscrapy.utils.tools import create_task


class SqlFormat:

    @staticmethod
    def pg_insert(table: str, fields: list, *args) -> str:
        fields = ','.join(fields)
        placeholder = ','.join([f'${i + 1}' for i in range(len(fields))])
        return f'''INSERT INTO {table} ({fields}) VALUES ({placeholder})'''

    @staticmethod
    def pg_ignore_insert(table: str, fields: list, *args) -> str:
        placeholder = ','.join([f'${i + 1}' for i in range(len(fields))])
        fields = ','.join(fields)
        return f'INSERT INTO {table} ({fields}) VALUES ({placeholder}) ON CONFLICT DO NOTHING'

    @staticmethod
    def pg_update_insert(table: str, fields: list, update_fields: list, on_conflict: str, *args) -> str:
        assert on_conflict is not None, "on_conflict must be str, eg: 'id'"
        placeholder = ','.join([f'${i + 1}' for i in range(len(fields))])
        if not update_fields:
            update_fields = fields
        update_fields = ','.join([f"{key} = excluded.{key}" for key in update_fields])
        fields = ','.join(fields)
        return f'INSERT INTO {table} ({fields}) VALUES ({placeholder}) ON CONFLICT({on_conflict}) DO UPDATE SET {update_fields}'

    @staticmethod
    def mysql_insert(table: str, fields: list, *args) -> str:
        placeholder = ','.join(['%s'] * len(fields))
        fields = ','.join(fields)
        return f'''INSERT INTO {table} ({fields}) VALUES ({placeholder})'''

    @staticmethod
    def mysql_ignore_insert(table: str, fields: list, *args) -> str:
        placeholder = ','.join(['%s'] * len(fields))
        fields = ','.join(fields)
        return f'''INSERT IGNORE INTO {table} ({fields}) VALUES ({placeholder})'''

    @staticmethod
    def mysql_update_insert(table: str, fields: list, update_fields: list, *args) -> str:
        placeholder = ','.join(['%s'] * len(fields))
        if not update_fields:
            update_fields = fields
        update_fields = ','.join([f"{key} = VALUES({key})" for key in update_fields])
        fields = ','.join(fields)
        return f'INSERT INTO {table} ({fields}) VALUES ({placeholder}) ON DUPLICATE KEY UPDATE {update_fields}'

    def __call__(self, *args, db_type='mysql', insert_type='insert'):
        if getattr(self, f'{db_type}_{insert_type}'):
            return getattr(self, f'{db_type}_{insert_type}')(*args)
        raise Exception(f"This write type is not supported： {db_type}_{insert_type}")


get_sql = SqlFormat()


class ItemCacheMixin:
    def __init__(self, db_type: str):
        self.db_type = db_type
        self.item_cache = {}
        self.fields_cache = {}
        self.table_cache = {}
        self.insert_sql_cache = {}
        self.db_alias_cache = {}

    def parse_item_to_cache(self, item: dict, save_info):
        table_name = save_info.get('table_name')
        assert table_name is not None, 'Missing table_name'
        insert_type = save_info.get('insert_type', 'insert')
        update_fields = save_info.get('update_fields', [])
        db_alias = save_info.get('db_alias', ['default'])
        on_conflict = save_info.get('on_conflict')
        if isinstance(db_alias, str):
            db_alias = [db_alias]

        fields = list(item.keys())
        cache_key = ''.join(fields + update_fields + db_alias) + insert_type + table_name + (on_conflict or '')

        if self.fields_cache.get(cache_key) is None:
            self.db_alias_cache[cache_key] = db_alias
            self.table_cache[cache_key] = table_name
            self.fields_cache[cache_key] = fields
            self.item_cache[cache_key] = []
            self.insert_sql_cache[cache_key] = get_sql(
                table_name, fields, update_fields, on_conflict,
                db_type=self.db_type,
                insert_type=insert_type,
            )

        self.item_cache[cache_key].append([item[field] for field in self.fields_cache[cache_key]])
        return cache_key, len(self.item_cache[cache_key])


class DBPipelineBase(ItemCacheMixin):
    def __init__(self, settings, db_type: str):
        super().__init__(db_type)
        self.cache_num = settings.getint('SAVE_CACHE_NUM', 500)
        self.save_cache_interval = settings.getint('SAVE_CACHE_INTERVAL', 10)
        self.lock = asyncio.Lock()
        self.running: bool = True
        self.item_save_key: str = f'__{db_type}__'

    async def open_spider(self, spider):
        create_task(self.save_heartbeat())

    async def save_heartbeat(self):
        while self.running:
            await asyncio.sleep(self.save_cache_interval)
            create_task(self.save_all())

    async def process_item(self, item, spider):
        save_info = item.pop(self.item_save_key, None)
        if save_info is None:
            logger.warning(f"item Missing key {self.item_save_key}, not stored")
            return item

        await self.save_item(item, save_info)
        return item

    async def close_spider(self, spider):
        self.running = False
        await self.save_all()

    async def save_all(self):
        async with self.lock:
            for cache_key, items in self.item_cache.items():
                items and await self._save(cache_key)

    async def save_item(self, item: dict, save_info: dict):
        async with self.lock:
            cache_key, cache_count = self.parse_item_to_cache(item, save_info)
            if cache_count >= self.cache_num:
                await self._save(cache_key)

    async def _save(self, cache_key):
        raise NotImplementedError
