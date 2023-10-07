from aioscrapy.db import db_manager
from aioscrapy.libs.pipelines import DBPipelineBase

from aioscrapy.utils.log import logger


class PGPipeline(DBPipelineBase):

    @classmethod
    def from_settings(cls, settings):
        return cls(settings, 'pg')

    async def _save(self, cache_key):
        table_name = self.table_cache[cache_key]
        try:
            for alias in self.db_alias_cache[cache_key]:
                async with db_manager.pg.get(alias) as conn:
                    try:
                        num = await conn.executemany(
                            self.insert_sql_cache[cache_key], self.item_cache[cache_key]
                        )
                        logger.info(f'table:{alias}->{table_name} sum:{len(self.item_cache[cache_key])} ok:{num}')
                    except Exception as e:
                        logger.exception(f'save data error, table:{alias}->{table_name}, err_msg:{e}')
        finally:
            self.item_cache[cache_key] = []
