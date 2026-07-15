"""
Database Pipeline Utilities for AioScrapy
AioScrapy的数据库管道实用工具

This module provides base classes and utilities for implementing database pipelines
in AioScrapy. It includes SQL formatting utilities for different database types
and a base pipeline class with caching functionality.
此模块提供了在AioScrapy中实现数据库管道的基类和实用工具。
它包括用于不同数据库类型的SQL格式化实用工具和具有缓存功能的基本管道类。
"""

import asyncio

from aioscrapy.libs.pipelines.write_error_policy import WriteErrorPolicy
from aioscrapy.utils.log import logger
from aioscrapy.utils.tools import create_task


class SqlFormat:
    """
    SQL query formatter for different database types.
    不同数据库类型的SQL查询格式化器。

    This class provides static methods to generate SQL INSERT statements
    for different database types (PostgreSQL, MySQL) and different insert types
    (regular insert, ignore insert, update insert).
    此类提供静态方法，用于为不同的数据库类型（PostgreSQL、MySQL）
    和不同的插入类型（常规插入、忽略插入、更新插入）生成SQL INSERT语句。
    """

    @staticmethod
    def pg_insert(table: str, fields: list, *args) -> str:
        """
        Generate a PostgreSQL INSERT statement.
        生成PostgreSQL INSERT语句。

        Args:
            table: The table name to insert into.
                  要插入的表名。
            fields: List of field names to insert.
                   要插入的字段名列表。
            *args: Additional arguments (not used).
                  额外的参数（未使用）。

        Returns:
            str: The formatted PostgreSQL INSERT statement.
                 格式化的PostgreSQL INSERT语句。
        """
        placeholder = ','.join([f'${i + 1}' for i in range(len(fields))])
        return f'''INSERT INTO {table} ({",".join(fields)}) VALUES ({placeholder})'''

    @staticmethod
    def pg_ignore_insert(table: str, fields: list, *args) -> str:
        """
        Generate a PostgreSQL INSERT statement with ON CONFLICT DO NOTHING.
        生成带有ON CONFLICT DO NOTHING的PostgreSQL INSERT语句。

        This type of insert will not raise an error if a duplicate key conflict occurs.
        如果发生重复键冲突，这种类型的插入不会引发错误。

        Args:
            table: The table name to insert into.
                  要插入的表名。
            fields: List of field names to insert.
                   要插入的字段名列表。
            *args: Additional arguments (not used).
                  额外的参数（未使用）。

        Returns:
            str: The formatted PostgreSQL INSERT statement with conflict handling.
                 带有冲突处理的格式化PostgreSQL INSERT语句。
        """
        placeholder = ','.join([f'${i + 1}' for i in range(len(fields))])
        return f'''INSERT INTO {table} ({",".join(fields)}) VALUES ({placeholder}) ON CONFLICT DO NOTHING'''

    @staticmethod
    def pg_update_insert(table: str, fields: list, update_fields: list, on_conflict: str, *args) -> str:
        """
        Generate a PostgreSQL UPSERT statement (INSERT with ON CONFLICT UPDATE).
        生成PostgreSQL UPSERT语句（带有ON CONFLICT UPDATE的INSERT）。

        This type of insert will update existing rows if a conflict occurs.
        如果发生冲突，这种类型的插入将更新现有行。

        Args:
            table: The table name to insert into.
                  要插入的表名。
            fields: List of field names to insert.
                   要插入的字段名列表。
            update_fields: List of fields to update on conflict. If empty, all fields will be updated.
                          冲突时要更新的字段列表。如果为空，将更新所有字段。
            on_conflict: The field name(s) that determine the conflict.
                        确定冲突的字段名称。
            *args: Additional arguments (not used).
                  额外的参数（未使用）。

        Returns:
            str: The formatted PostgreSQL UPSERT statement.
                 格式化的PostgreSQL UPSERT语句。

        Raises:
            AssertionError: If on_conflict is None.
                           如果on_conflict为None。
        """
        assert on_conflict is not None, "on_conflict must be str, eg: 'id'"
        placeholder = ','.join([f'${i + 1}' for i in range(len(fields))])
        if not update_fields:
            update_fields = fields
        update_fields = ','.join([f"{key} = excluded.{key}" for key in update_fields])
        return f'''INSERT INTO {table} ({",".join(fields)}) VALUES ({placeholder}) ON CONFLICT({on_conflict}) DO UPDATE SET {update_fields}'''

    @staticmethod
    def mysql_insert(table: str, fields: list, *args) -> str:
        """
        Generate a MySQL INSERT statement.
        生成MySQL INSERT语句。

        Args:
            table: The table name to insert into.
                  要插入的表名。
            fields: List of field names to insert.
                   要插入的字段名列表。
            *args: Additional arguments (not used).
                  额外的参数（未使用）。

        Returns:
            str: The formatted MySQL INSERT statement.
                 格式化的MySQL INSERT语句。
        """
        placeholder = ','.join(['%s'] * len(fields))
        fields = ','.join(fields)
        return f'''INSERT INTO {table} ({fields}) VALUES ({placeholder})'''

    @staticmethod
    def mysql_ignore_insert(table: str, fields: list, *args) -> str:
        """
        Generate a MySQL INSERT IGNORE statement.
        生成MySQL INSERT IGNORE语句。

        This type of insert will not raise an error if a duplicate key conflict occurs.
        如果发生重复键冲突，这种类型的插入不会引发错误。

        Args:
            table: The table name to insert into.
                  要插入的表名。
            fields: List of field names to insert.
                   要插入的字段名列表。
            *args: Additional arguments (not used).
                  额外的参数（未使用）。

        Returns:
            str: The formatted MySQL INSERT IGNORE statement.
                 格式化的MySQL INSERT IGNORE语句。
        """
        placeholder = ','.join(['%s'] * len(fields))
        fields = ','.join(fields)
        return f'''INSERT IGNORE INTO {table} ({fields}) VALUES ({placeholder})'''

    @staticmethod
    def mysql_update_insert(table: str, fields: list, update_fields: list, *args) -> str:
        """
        Generate a MySQL INSERT ... ON DUPLICATE KEY UPDATE statement.
        生成MySQL INSERT ... ON DUPLICATE KEY UPDATE语句。

        This type of insert will update existing rows if a duplicate key conflict occurs.
        如果发生重复键冲突，这种类型的插入将更新现有行。

        Args:
            table: The table name to insert into.
                  要插入的表名。
            fields: List of field names to insert.
                   要插入的字段名列表。
            update_fields: List of fields to update on duplicate key. If empty, all fields will be updated.
                          重复键时要更新的字段列表。如果为空，将更新所有字段。
            *args: Additional arguments (not used).
                  额外的参数（未使用）。

        Returns:
            str: The formatted MySQL INSERT ... ON DUPLICATE KEY UPDATE statement.
                 格式化的MySQL INSERT ... ON DUPLICATE KEY UPDATE语句。
        """
        placeholder = ','.join(['%s'] * len(fields))
        if not update_fields:
            update_fields = fields
        update_fields = ','.join([f"{key} = VALUES({key})" for key in update_fields])
        fields = ','.join(fields)
        return f'INSERT INTO {table} ({fields}) VALUES ({placeholder}) ON DUPLICATE KEY UPDATE {update_fields}'

    def __call__(self, *args, db_type='mysql', insert_type='insert'):
        """
        Call the appropriate SQL formatting method based on database type and insert type.
        根据数据库类型和插入类型调用适当的SQL格式化方法。

        This method makes the SqlFormat instance callable, allowing it to be used as a function.
        此方法使SqlFormat实例可调用，允许将其用作函数。

        Args:
            *args: Arguments to pass to the SQL formatting method.
                  传递给SQL格式化方法的参数。
            db_type: The database type ('mysql' or 'pg').
                    数据库类型（'mysql'或'pg'）。
                    Defaults to 'mysql'.
                    默认为'mysql'。
            insert_type: The insert type ('insert', 'ignore_insert', or 'update_insert').
                        插入类型（'insert'、'ignore_insert'或'update_insert'）。
                        Defaults to 'insert'.
                        默认为'insert'。

        Returns:
            str: The formatted SQL statement.
                 格式化的SQL语句。

        Raises:
            Exception: If the requested database type and insert type combination is not supported.
                      如果不支持请求的数据库类型和插入类型组合。
        """
        if getattr(self, f'{db_type}_{insert_type}'):
            return getattr(self, f'{db_type}_{insert_type}')(*args)
        raise Exception(f"This write type is not supported： {db_type}_{insert_type}")


# Global instance of SqlFormat for generating SQL statements
get_sql = SqlFormat()


class ItemCacheMixin:
    """
    Mixin class for caching items before database insertion.
    用于在数据库插入前缓存项目的混入类。

    This class provides functionality to cache items and their metadata
    before batch insertion into a database. It helps optimize database
    operations by reducing the number of database calls.
    此类提供了在批量插入数据库之前缓存项目及其元数据的功能。
    它通过减少数据库调用次数来帮助优化数据库操作。
    """

    def __init__(self, db_type: str):
        """
        Initialize the ItemCacheMixin.
        初始化ItemCacheMixin。

        Args:
            db_type: The database type (e.g., 'mysql', 'pg', 'mongo').
                    数据库类型（例如'mysql'、'pg'、'mongo'）。
        """
        # The database type
        # 数据库类型
        self.db_type = db_type

        # Dictionary to cache items by cache key
        # 按缓存键缓存项目的字典
        self.item_cache = {}

        # Dictionary to cache field lists by cache key
        # 按缓存键缓存字段列表的字典
        self.fields_cache = {}

        # Dictionary to cache table names by cache key
        # 按缓存键缓存表名的字典
        self.table_cache = {}

        # Dictionary to cache SQL insert statements by cache key
        # 按缓存键缓存SQL插入语句的字典
        self.insert_sql_cache = {}

        # Dictionary to cache database aliases by cache key
        # 按缓存键缓存数据库别名的字典
        self.db_alias_cache = {}

    def parse_item_to_cache(self, item: dict, save_info: dict):
        """
        Parse an item and add it to the cache.
        解析项目并将其添加到缓存中。

        This method extracts information from the save_info dictionary,
        generates a cache key, and adds the item to the appropriate cache.
        此方法从save_info字典中提取信息，生成缓存键，并将项目添加到适当的缓存中。

        Args:
            item: The item to cache.
                 要缓存的项目。
            save_info: Dictionary containing information about how to save the item.
                      包含有关如何保存项目的信息的字典。
                      Must contain 'table_name' and may contain 'insert_type',
                      'update_fields', 'db_alias', and 'on_conflict'.
                      必须包含'table_name'，可能包含'insert_type'、
                      'update_fields'、'db_alias'和'on_conflict'。

        Returns:
            tuple: A tuple containing the cache key and the number of items in the cache.
                  包含缓存键和缓存中项目数量的元组。

        Raises:
            AssertionError: If table_name is not provided in save_info.
                           如果在save_info中未提供table_name。
        """
        # Extract information from save_info
        # 从save_info中提取信息
        table_name = save_info.get('table_name')
        assert table_name is not None, 'Missing table_name'
        insert_type = save_info.get('insert_type', 'insert')
        update_fields = save_info.get('update_fields', [])
        db_alias = save_info.get('db_alias', ['default'])
        on_conflict = save_info.get('on_conflict')

        # Convert string db_alias to list
        # 将字符串db_alias转换为列表
        if isinstance(db_alias, str):
            db_alias = [db_alias]

        # Generate a unique cache key based on the item and save_info
        # 根据项目和save_info生成唯一的缓存键
        fields = list(item.keys())
        cache_key = ''.join(fields + update_fields + db_alias) + insert_type + table_name + (on_conflict or '')

        # If this is a new cache key, initialize the caches
        # 如果这是一个新的缓存键，初始化缓存
        if self.fields_cache.get(cache_key) is None:
            self.db_alias_cache[cache_key] = db_alias
            self.table_cache[cache_key] = table_name
            self.fields_cache[cache_key] = fields
            self.item_cache[cache_key] = []

            # Generate the SQL insert statement
            # 生成SQL插入语句
            self.insert_sql_cache[cache_key] = get_sql(
                table_name, fields, update_fields, on_conflict,
                db_type=self.db_type,
                insert_type=insert_type,
            )

        # Add the item values to the cache
        # 将项目值添加到缓存
        self.item_cache[cache_key].append([item[field] for field in self.fields_cache[cache_key]])

        # Return the cache key and the number of items in the cache
        # 返回缓存键和缓存中的项目数量
        return cache_key, len(self.item_cache[cache_key])


class DBPipelineBase(ItemCacheMixin):
    """
    Base class for database pipelines.
    数据库管道的基类。

    This class provides common functionality for database pipelines, including
    caching items and periodically saving them to the database.
    此类为数据库管道提供通用功能，包括缓存项目并定期将其保存到数据库。
    """

    def __init__(self, settings, db_type: str):
        """
        Initialize the database pipeline.
        初始化数据库管道。

        Args:
            settings: The settings object. 设置对象。
            db_type: The database type (e.g., 'mysql', 'pg', 'mongo'). 数据库类型（例如'mysql'、'pg'、'mongo'）。
        """
        super().__init__(db_type)
        self.cache_num = settings.getint('SAVE_CACHE_NUM', 500)
        self.save_cache_interval = settings.getint('SAVE_CACHE_INTERVAL', 10)
        self.write_error_policy = WriteErrorPolicy.from_settings(settings)
        self.pause_on_connection_error = self.write_error_policy.pause_on_connection_error
        # Keep the old setting as a compatibility fallback for existing projects.
        # 保留旧配置作为兼容回退，避免已有项目升级后重试间隔失效。
        self.write_error_retry_interval = max(
            0.0,
            settings.getfloat(
                'DB_PIPELINE_WRITE_ERROR_RETRY_INTERVAL',
                settings.getfloat('DB_PIPELINE_CONNECTION_RETRY_INTERVAL', 5.0),
            )
        )
        self.lock = asyncio.Lock()
        self.running: bool = True
        self.item_save_key: str = f'__{db_type}__'
        self._heartbeat_task = None
        self.spider = None

    async def open_spider(self, spider):
        """
        Called when the spider is opened.
        当爬虫打开时调用。

        This method starts the save heartbeat task.
        此方法启动保存心跳任务。

        Args:
            spider: The spider instance. 爬虫实例。
        """
        self.spider = spider
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self.running = True
            self._heartbeat_task = create_task(self.save_heartbeat())

    async def save_heartbeat(self):
        """
        Periodically save cached items to the database.
        定期将缓存的项目保存到数据库。

        This method runs in the background and saves cached items
        every `save_cache_interval` seconds.
        此方法在后台运行，每隔`save_cache_interval`秒保存一次缓存的项目。
        """
        while self.running:
            await asyncio.sleep(self.save_cache_interval)
            if not self.running:
                break
            try:
                await self.save_all()
            except Exception:
                logger.exception(
                    "Periodic pipeline flush failed; cached items remain available for retry"
                )

    async def process_item(self, item, spider):
        """
        Process an item.
        处理一个项目。

        This method is called for every item pipeline component.
        此方法对每个项目管道组件调用。

        Args:
            item: The item to process. 要处理的项目。
            spider: The spider instance. 爬虫实例。

        Returns:
            The processed item. 处理后的项目。
        """
        save_info = item.pop(self.item_save_key, None)
        if save_info is None:
            logger.warning(f"item Missing key {self.item_save_key}, not stored")
            return item

        await self.save_item(item, save_info)
        return item

    async def close_spider(self, spider):
        """
        Called when the spider is closed.
        当爬虫关闭时调用。

        This method stops the save heartbeat task and saves all remaining items.
        此方法停止保存心跳任务并保存所有剩余项目。

        Args:
            spider: The spider instance. 爬虫实例。
        """
        self.running = False
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        await self.save_all()

    async def save_all(self):
        """
        Save all cached items to the database.
        将所有缓存的项目保存到数据库。

        This method is called periodically by the save heartbeat task
        and when the spider is closed.
        此方法由保存心跳任务定期调用，并在爬虫关闭时调用。
        """
        async with self.lock:
            for cache_key, items in self.item_cache.items():
                items and await self._save(cache_key)

    async def _save(self, cache_key):
        """
        Persist a cache snapshot and acknowledge it only after a successful write.
        持久化缓存批次，并仅在写入成功后确认删除该批次。
        """
        cached_items = self.item_cache[cache_key]
        if not cached_items:
            return

        # Retry the same snapshot to keep cache acknowledgment deterministic.
        # 始终重试同一批次快照，保证缓存确认行为确定且可追踪。
        batch = list(cached_items)
        pause_acquired = False
        try:
            while True:
                try:
                    await self._write_batch(cache_key, batch)
                except Exception as exc:
                    pause_reason = self.should_pause_on_write_error(exc)
                    if not self._can_retry_write_error() or pause_reason is None:
                        raise

                    self._pause_spider_for_write_error()
                    pause_acquired = True
                    logger.warning(
                        f"{self.db_type} pipeline write paused by {pause_reason}; "
                        f"retrying in {self.write_error_retry_interval} seconds"
                    )
                    await asyncio.sleep(self.write_error_retry_interval)
                    continue

                # Remove only the successfully persisted snapshot. Newer items stay cached.
                # 只删除成功持久化的快照，写入期间新增的数据继续保留在缓存中。
                del cached_items[:len(batch)]
                return
        finally:
            if pause_acquired:
                self._resume_spider_after_write_error()

    def should_pause_on_write_error(self, exception):
        """
        Return the matching pause policy name for a write error.
        返回写入异常匹配的暂停策略名称。

        Subclasses may override this method for local rules. Prefer settings-based
        error types or checkers when the rule should be reusable across pipelines.
        子类可覆盖此方法实现局部规则；跨管道复用时优先使用配置的异常类型或判定函数。
        """
        return self.write_error_policy.match(exception)

    def _can_retry_write_error(self):
        """
        Return whether the pipeline may keep retrying a paused write.
        判断管道是否可以继续重试已暂停的写入。
        """
        if not self.running:
            return False

        crawler = getattr(self.spider, 'crawler', None)
        engine = getattr(crawler, 'engine', None)
        return engine is None or engine.running

    def _pause_spider_for_write_error(self):
        """
        Acquire this pipeline's shared spider-pause ownership.
        获取当前管道对共享爬虫暂停状态的所有权。
        """
        if self.spider is None:
            return

        state = getattr(self.spider, '_db_pipeline_pause_state', None)
        if state is None:
            state = {
                'owners': set(),
                'pause': self.spider.pause,
                'pause_time': getattr(self.spider, '_pause_time', None),
            }
            setattr(self.spider, '_db_pipeline_pause_state', state)

        state['owners'].add(self)
        self.spider.pause = True
        self.spider._pause_time = float('inf')

    def _resume_spider_after_write_error(self):
        """
        Release pause ownership and restore the original state when all recover.
        释放暂停所有权，并在全部管道恢复后还原爬虫原始状态。
        """
        if self.spider is None:
            return

        state = getattr(self.spider, '_db_pipeline_pause_state', None)
        if state is None:
            return

        state['owners'].discard(self)
        if state['owners']:
            return

        self.spider.pause = state['pause']
        self.spider._pause_time = state['pause_time']
        delattr(self.spider, '_db_pipeline_pause_state')

    async def save_item(self, item: dict, save_info: dict):
        """
        Save an item to the cache and possibly to the database.
        将项目保存到缓存，可能还会保存到数据库。

        If the cache reaches the configured size, all cached items are saved to the database.
        如果缓存达到配置的大小，所有缓存的项目都会保存到数据库。

        Args:
            item: The item to save. 要保存的项目。
            save_info: Information about how to save the item. 有关如何保存项目的信息。
        """
        async with self.lock:
            cache_key, cache_count = self.parse_item_to_cache(item, save_info)
            if cache_count >= self.cache_num:
                await self._save(cache_key)

    async def _write_batch(self, cache_key, items):
        """
        Write a fixed item batch to the database.
        将固定的数据批次写入数据库。

        This is an abstract method that must be implemented by subclasses.
        Cache acknowledgment, connection retries, and spider pause state are
        handled by ``_save``.
        这是一个必须由子类实现的抽象方法。
        缓存确认、连接重试和爬虫暂停状态由``_save``处理。

        Args:
            cache_key: The cache key used to retrieve the cached items, SQL statement,
                      and other metadata needed for the database operation.
                      用于检索缓存项目、SQL语句和数据库操作所需的其他元数据的缓存键。
            items: The batch snapshot to write. 要写入的批次快照。

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
                                此方法必须由子类实现。
        """
        raise NotImplementedError("Subclasses must implement the _write_batch method")
