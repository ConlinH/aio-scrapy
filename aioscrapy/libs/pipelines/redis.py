"""
Redis Pipeline for AioScrapy
AioScrapy的Redis管道

This module provides a pipeline for storing scraped items in a redis.
此模块提供了一个用于将抓取的项目存储在Redis数据库中的管道。
"""

import ujson
from aioscrapy.db import db_manager
from aioscrapy.libs.pipelines import DBPipelineBase

from aioscrapy.utils.log import logger

class RedisPipeline(DBPipelineBase):
    """
    Pipeline for storing scraped items in Redis.
    用于将抓取的项目存储到Redis的管道。

    This pipeline extends the base database pipeline to implement Redis-specific
    functionality for batch inserting items. It uses the database manager to handle
    connections and operations.
    此管道扩展了基本数据库管道，以实现Redis特定的批量插入项目功能。
    它使用数据库管理器来处理连接和操作。
    """
    def __init__(self, settings, db_type: str):
        """
        Initialize the RedisPipeline instance.
        初始化RedisPipeline实例。

        Args:
            settings: The AioScrapy settings object.
                      AioScrapy设置对象。
            db_type: The type of database, should be 'redis'.
                     数据库类型，应为'redis'。
        """
        super().__init__(settings, db_type)

        self.db_cache = {}  # 缓存数据库别名
        self.key_name_cache = {}  # 缓存Redis键名
        self.insert_method_cache = {}  # 缓存插入方法名
        self.item_cache = {}  # 缓存待插入的项目

    @classmethod
    def from_settings(cls, settings):
        """
        Create a RedisPipeline instance from settings.
        从设置创建RedisPipeline实例。

        Returns:
            RedisPipeline: A new RedisPipeline instance.
                           一个新的RedisPipeline实例。
        """
        return cls(settings, 'redis')

    def parse_item_to_cache(self, item: dict, save_info: dict):
        """
        Parse item and save info to cache for batch processing.
        解析item和保存信息到缓存以便批量处理。

        Args:
            item: The item to be cached.
                  要缓存的项目。
            save_info: Information about how and where to save the item.
                       关于如何以及在哪里保存项目的信息。

        Returns:
            cache_key: The key used for caching.
                       用于缓存的键。
            count: Number of items currently cached under this key.
                   当前此键下缓存的项目数量。
        """
        key_name = save_info.get("key_name")
        insert_method = save_info.get("insert_method")

        assert key_name is not None, "please set key_name"  # 必须设置key_name
        assert insert_method is not None, "please set insert_method"  # 必须设置insert_method

        db_alias = save_info.get("db_alias", ["default"])  # 获取数据库别名，默认为"default"

        if isinstance(db_alias, str):
            db_alias = [db_alias]  # 如果是字符串则转为列表

        cache_key = "-".join([key_name, insert_method])  # 生成缓存键

        if self.db_cache.get(cache_key) is None:
            self.db_cache[cache_key] = db_alias  # 缓存数据库别名
            self.key_name_cache[cache_key] = key_name  # 缓存Redis键名
            self.insert_method_cache[cache_key] = insert_method  # 缓存插入方法名
            self.item_cache[cache_key] = []  # 初始化项目缓存列表
        
        self.item_cache[cache_key].append(item)  # 添加项目到缓存

        return cache_key, len(self.item_cache[cache_key])  # 返回缓存键和当前缓存数量

    async def _save(self, cache_key):
        """
        Save cached items with the given cache key to Redis.
        将具有给定缓存键的缓存项目保存到Redis。

        Args:
            cache_key: The cache key used to retrieve the cached items and metadata.
                       用于检索缓存项目和元数据的缓存键。
        """
        insert_method_name = self.insert_method_cache[cache_key]  # 获取插入方法名
        key_name = self.key_name_cache[cache_key]  # 获取Redis键名
        items = self.item_cache[cache_key]  # 获取待插入项目列表

        try:
            for alias in self.db_cache[cache_key]:  # 遍历所有数据库别名
                try:
                    executor = db_manager.redis.executor(alias)  # 获取Redis执行器
                    insert_method = getattr(executor, insert_method_name)  # 获取插入方法
                    # 批量插入项目到Redis
                    result = await insert_method(key_name, *[ujson.dumps(item) for item in items])
                    logger.info(
                        f"redis:{alias}->{key_name} sum:{len(items)} ok:{result}"
                    )  # 记录插入结果
                except Exception as e:
                    logger.exception(f'redis:push data error: {e}')  # 记录异常
        finally:
            self.item_cache[cache_key] = []  # 清空缓存，无论成功
