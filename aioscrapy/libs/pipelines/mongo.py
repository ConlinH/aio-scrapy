from aioscrapy.db import db_manager
from aioscrapy.libs.pipelines import DBPipelineBase

from aioscrapy.utils.log import logger


class MongoPipeline(DBPipelineBase):

    def __init__(self, settings, db_type: str):
        super().__init__(settings, db_type)
        self.db_cache = {}

    @classmethod
    def from_settings(cls, settings):
        return cls(settings, 'mongo')

    def parse_item_to_cache(self, item: dict, save_info: dict):
        db_name = save_info.get('db_name')
        table_name = save_info.get('table_name')
        assert table_name is not None, 'please set table_name'
        db_alias = save_info.get('db_alias', ['default'])
        if isinstance(db_alias, str):
            db_alias = [db_alias]

        cache_key = ''.join(db_alias) + (db_name or '') + table_name

        if self.table_cache.get(cache_key) is None:
            self.db_alias_cache[cache_key] = db_alias
            self.table_cache[cache_key] = table_name
            self.db_cache[cache_key] = db_name
            self.item_cache[cache_key] = []

        self.item_cache[cache_key].append(item)
        return cache_key, len(self.item_cache[cache_key])

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
                        f'table:{alias}->{table_name} sum:{len(self.item_cache[cache_key])} ok:{len(result.inserted_ids)}'
                    )
                except Exception as e:
                    logger.exception(f'save data error, table:{alias}->{table_name}, err_msg:{e}')
        finally:
            self.item_cache[cache_key] = []
