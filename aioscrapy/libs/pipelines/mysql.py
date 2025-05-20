"""
MySQL Pipeline for AioScrapy
AioScrapy的MySQL管道

This module provides a pipeline for storing scraped items in a MySQL database.
It extends the base database pipeline to implement MySQL-specific functionality
for batch inserting items.
此模块提供了一个用于将抓取的项目存储在MySQL数据库中的管道。
它扩展了基本数据库管道，以实现MySQL特定的批量插入项目功能。
"""

from aioscrapy.db import db_manager
from aioscrapy.libs.pipelines import DBPipelineBase

from aioscrapy.utils.log import logger


class MysqlPipeline(DBPipelineBase):
    """
    Pipeline for storing scraped items in a MySQL database.
    用于将抓取的项目存储在MySQL数据库中的管道。

    This pipeline extends the base database pipeline to implement MySQL-specific
    functionality for batch inserting items. It uses the database manager to
    handle connections and transactions.
    此管道扩展了基本数据库管道，以实现MySQL特定的批量插入项目功能。
    它使用数据库管理器来处理连接和事务。
    """

    @classmethod
    def from_settings(cls, settings):
        """
        Create a MysqlPipeline instance from settings.
        从设置创建MysqlPipeline实例。

        This is the factory method used by AioScrapy to create pipeline instances.
        It initializes the pipeline with the appropriate database type ('mysql').
        这是AioScrapy用于创建管道实例的工厂方法。
        它使用适当的数据库类型（'mysql'）初始化管道。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。

        Returns:
            MysqlPipeline: A new MysqlPipeline instance.
                          一个新的MysqlPipeline实例。
        """
        return cls(settings, 'mysql')

    async def _save(self, cache_key):
        """
        Save cached items with the given cache key to the MySQL database.
        将具有给定缓存键的缓存项目保存到MySQL数据库。

        This method implements the abstract _save method from the base class.
        It retrieves the cached items and SQL statement for the given cache key,
        then executes a batch insert operation on each configured database connection.
        此方法实现了基类中的抽象_save方法。
        它检索给定缓存键的缓存项目和SQL语句，然后在每个配置的数据库连接上执行批量插入操作。

        Args:
            cache_key: The cache key used to retrieve the cached items, SQL statement,
                      and other metadata needed for the database operation.
                      用于检索缓存项目、SQL语句和数据库操作所需的其他元数据的缓存键。
        """
        # Get the table name from the cache
        # 从缓存获取表名
        table_name = self.table_cache[cache_key]
        try:
            # Process each database alias (connection) configured for this cache key
            # 处理为此缓存键配置的每个数据库别名（连接）
            for alias in self.db_alias_cache[cache_key]:
                # Get a database connection and cursor with ping to ensure the connection is alive
                # 获取数据库连接和游标，并使用ping确保连接处于活动状态
                async with db_manager.mysql.get(alias, ping=True) as (conn, cursor):
                    try:
                        # Execute the batch insert operation
                        # 执行批量插入操作
                        num = await cursor.executemany(
                            self.insert_sql_cache[cache_key], self.item_cache[cache_key]
                        )
                        # Log the result of the operation
                        # 记录操作结果
                        logger.info(f'table:{alias}->{table_name} sum:{len(self.item_cache[cache_key])} ok:{num}')
                    except Exception as e:
                        # Log any errors that occur during the operation
                        # 记录操作期间发生的任何错误
                        logger.exception(f'save data error, table:{alias}->{table_name}, err_msg:{e}')
        finally:
            # Clear the cache after processing, regardless of success or failure
            # 处理后清除缓存，无论成功或失败
            self.item_cache[cache_key] = []
