"""
MongoDB Pipeline for AioScrapy
AioScrapy的MongoDB管道

This module provides a pipeline for storing scraped items in a MongoDB database.
It extends the base database pipeline to implement MongoDB-specific functionality
for batch inserting items.
此模块提供了一个用于将抓取的项目存储在MongoDB数据库中的管道。
它扩展了基本数据库管道，以实现MongoDB特定的批量插入项目功能。
"""

from aioscrapy.db import db_manager
from aioscrapy.libs.pipelines import DBPipelineBase

from aioscrapy.utils.log import logger


class MongoPipeline(DBPipelineBase):
    """
    Pipeline for storing scraped items in a MongoDB database.
    用于将抓取的项目存储在MongoDB数据库中的管道。

    This pipeline extends the base database pipeline to implement MongoDB-specific
    functionality for batch inserting items. It supports multiple database connections,
    custom database names, and ordered/unordered inserts.
    此管道扩展了基本数据库管道，以实现MongoDB特定的批量插入项目功能。
    它支持多个数据库连接、自定义数据库名称和有序/无序插入。
    """

    def __init__(self, settings, db_type: str):
        """
        Initialize the MongoDB pipeline.
        初始化MongoDB管道。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
            db_type: The database type, should be 'mongo'.
                    数据库类型，应为'mongo'。
        """
        super().__init__(settings, db_type)

        # Dictionary to cache database names by cache key
        # 按缓存键缓存数据库名称的字典
        self.db_cache = {}

        # Dictionary to cache ordered insert flags by cache key
        # 按缓存键缓存有序插入标志的字典
        self.ordered_cache = {}

        # Number of times to retry MongoDB operations on timeout
        # MongoDB操作超时时重试的次数
        self.retry_times = settings.getint("MONGO_TIMEOUT_RETRY_TIMES", 3)

    @classmethod
    def from_settings(cls, settings):
        """
        Create a MongoPipeline instance from settings.
        从设置创建MongoPipeline实例。

        This is the factory method used by AioScrapy to create pipeline instances.
        It initializes the pipeline with the appropriate database type ('mongo').
        这是AioScrapy用于创建管道实例的工厂方法。
        它使用适当的数据库类型（'mongo'）初始化管道。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。

        Returns:
            MongoPipeline: A new MongoPipeline instance.
                          一个新的MongoPipeline实例。
        """
        return cls(settings, 'mongo')

    def parse_item_to_cache(self, item: dict, save_info: dict):
        """
        Parse an item and add it to the cache.
        解析项目并将其添加到缓存中。

        This method overrides the base class method to handle MongoDB-specific
        caching requirements, such as database names and ordered insert flags.
        此方法覆盖基类方法，以处理MongoDB特定的缓存需求，如数据库名称和有序插入标志。

        Args:
            item: The item to cache.
                 要缓存的项目。
            save_info: Dictionary containing information about how to save the item.
                      包含有关如何保存项目的信息的字典。
                      Must contain 'table_name' and may contain 'db_name',
                      'ordered', and 'db_alias'.
                      必须包含'table_name'，可能包含'db_name'、'ordered'和'db_alias'。

        Returns:
            tuple: A tuple containing the cache key and the number of items in the cache.
                  包含缓存键和缓存中项目数量的元组。

        Raises:
            AssertionError: If table_name is not provided in save_info.
                           如果在save_info中未提供table_name。
        """
        # Extract information from save_info
        # 从save_info中提取信息
        db_name = save_info.get('db_name')
        table_name = save_info.get('table_name')
        ordered = save_info.get('ordered', False)

        # Ensure table_name is provided
        # 确保提供了table_name
        assert table_name is not None, 'please set table_name'

        # Get database aliases, defaulting to ['default']
        # 获取数据库别名，默认为['default']
        db_alias = save_info.get('db_alias', ['default'])

        # Convert string db_alias to list
        # 将字符串db_alias转换为列表
        if isinstance(db_alias, str):
            db_alias = [db_alias]

        # Generate a unique cache key based on the save_info
        # 根据save_info生成唯一的缓存键
        cache_key = ''.join(db_alias) + (db_name or '') + table_name + str(ordered)

        # If this is a new cache key, initialize the caches
        # 如果这是一个新的缓存键，初始化缓存
        if self.table_cache.get(cache_key) is None:
            self.db_alias_cache[cache_key] = db_alias
            self.table_cache[cache_key] = table_name
            self.db_cache[cache_key] = db_name
            self.ordered_cache[cache_key] = ordered
            self.item_cache[cache_key] = []

        # Add the item to the cache
        # 将项目添加到缓存
        self.item_cache[cache_key].append(item)

        # Return the cache key and the number of items in the cache
        # 返回缓存键和缓存中的项目数量
        return cache_key, len(self.item_cache[cache_key])

    async def _save(self, cache_key):
        """
        Save cached items with the given cache key to the MongoDB database.
        将具有给定缓存键的缓存项目保存到MongoDB数据库。

        This method implements the abstract _save method from the base class.
        It retrieves the cached items for the given cache key, then executes
        a batch insert operation on each configured database connection.
        此方法实现了基类中的抽象_save方法。
        它检索给定缓存键的缓存项目，然后在每个配置的数据库连接上执行批量插入操作。

        Args:
            cache_key: The cache key used to retrieve the cached items and metadata.
                      用于检索缓存项目和元数据的缓存键。
        """
        # Get the table name from the cache
        # 从缓存获取表名
        table_name = self.table_cache[cache_key]
        try:
            # Process each database alias (connection) configured for this cache key
            # 处理为此缓存键配置的每个数据库别名（连接）
            for alias in self.db_alias_cache[cache_key]:
                try:
                    # Get a MongoDB executor for this alias
                    # 获取此别名的MongoDB执行器
                    executor = db_manager.mongo.executor(alias)

                    # Execute the batch insert operation
                    # 执行批量插入操作
                    result = await executor.insert(
                        table_name, self.item_cache[cache_key], db_name=self.db_cache[cache_key],
                        ordered=self.ordered_cache[cache_key], retry_times=self.retry_times
                    )

                    # Log the result of the operation
                    # 记录操作结果
                    logger.info(
                        f'table:{alias}->{table_name} sum:{len(self.item_cache[cache_key])} ok:{len(result.inserted_ids)}'
                    )
                except Exception as e:
                    # Log any errors that occur during the operation
                    # 记录操作期间发生的任何错误
                    logger.exception(f'save data error, table:{alias}->{table_name}, err_msg:{e}')
        finally:
            # Clear the cache after processing, regardless of success or failure
            # 处理后清除缓存，无论成功或失败
            self.item_cache[cache_key] = []
