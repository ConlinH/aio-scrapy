from aioscrapy.db import db_manager
from aioscrapy.libs.pipelines import DBPipelineBase

from aioscrapy.utils.log import logger


class MysqlPipeline(DBPipelineBase):

    @classmethod
    def from_settings(cls, settings):
        return cls(settings, 'mysql')

    async def _save(self, cache_key):
        table_name = self.table_cache[cache_key]
        try:
            for alias in self.db_alias_cache[cache_key]:
                async with db_manager.mysql.get(alias, ping=True) as (conn, cursor):
                    try:
                        num = await cursor.executemany(
                            self.insert_sql_cache[cache_key], self.item_cache[cache_key]
                        )
                        logger.info(f'table:{alias}->{table_name} sum:{len(self.item_cache[cache_key])} ok:{num}')
                    except Exception as e:
                        logger.exception(f'save data error, table:{alias}->{table_name}, err_msg:{e}')
        finally:
            self.item_cache[cache_key] = []
