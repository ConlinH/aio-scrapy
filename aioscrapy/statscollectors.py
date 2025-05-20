"""
AioScrapy Statistics Collection System
AioScrapy统计数据收集系统

This module provides classes for collecting and managing statistics during the
scraping process. Statistics can include counters for items scraped, pages downloaded,
processing times, etc. These statistics are useful for monitoring the performance
and behavior of spiders.
此模块提供了用于在抓取过程中收集和管理统计数据的类。
统计数据可以包括已抓取项目的计数器、已下载页面、处理时间等。
这些统计数据对于监控爬虫的性能和行为很有用。

The module includes:
模块包括：
- StatsCollector: Base class for all statistics collectors
               所有统计收集器的基类
- MemoryStatsCollector: Stores stats in memory
                      在内存中存储统计数据
- DummyStatsCollector: No-op collector that doesn't store anything
                     不存储任何内容的空操作收集器
"""
import pprint

from aioscrapy.utils.log import logger


class StatsCollector:
    """
    Base class for all statistics collectors in AioScrapy.
    AioScrapy中所有统计收集器的基类。

    This class provides methods to store, retrieve, and manipulate statistics
    during the scraping process. It's designed to be extended by specific
    implementations that determine how statistics are stored and persisted.
    此类提供了在抓取过程中存储、检索和操作统计数据的方法。
    它被设计为可由确定统计数据如何存储和持久化的特定实现扩展。
    """

    def __init__(self, crawler):
        """
        Initialize the stats collector.
        初始化统计收集器。

        Args:
            crawler: The crawler instance that uses this stats collector.
                    使用此统计收集器的爬虫实例。
        """
        # Whether to dump stats when the spider closes
        # 爬虫关闭时是否转储统计数据
        self._dump = crawler.settings.getbool('STATS_DUMP')
        # Dictionary to store the stats
        # 用于存储统计数据的字典
        self._stats = {}

    def get_value(self, key, default=None, spider=None):
        """
        Get the value for a given stats key.
        获取给定统计键的值。

        Args:
            key: The stats key to get the value for.
                要获取值的统计键。
            default: The default value to return if the key is not found.
                    如果未找到键，则返回的默认值。
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。

        Returns:
            The value for the given stats key, or the default value if the key is not found.
            给定统计键的值，如果未找到键，则为默认值。
        """
        return self._stats.get(key, default)

    def get_stats(self, spider=None):
        """
        Get all stats.
        获取所有统计数据。

        Args:
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。

        Returns:
            dict: A dictionary containing all stats.
                 包含所有统计数据的字典。
        """
        return self._stats

    def set_value(self, key, value, spider=None):
        """
        Set the value for a given stats key.
        设置给定统计键的值。

        Args:
            key: The stats key to set the value for.
                要设置值的统计键。
            value: The value to set.
                  要设置的值。
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。
        """
        self._stats[key] = value

    def set_stats(self, stats, spider=None):
        """
        Set all stats at once.
        一次设置所有统计数据。

        Args:
            stats: A dictionary of stats to set.
                  要设置的统计数据字典。
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。
        """
        self._stats = stats

    def inc_value(self, key, count=1, start=0, spider=None):
        """
        Increment the value for a given stats key.
        增加给定统计键的值。

        If the key does not exist, it is set to the start value plus the count.
        如果键不存在，则将其设置为起始值加上计数。

        Args:
            key: The stats key to increment.
                要增加的统计键。
            count: The amount to increment by. Defaults to 1.
                  要增加的数量。默认为1。
            start: The starting value if the key does not exist. Defaults to 0.
                  如果键不存在，则为起始值。默认为0。
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。
        """
        d = self._stats
        d[key] = d.setdefault(key, start) + count

    def max_value(self, key, value, spider=None):
        """
        Set the maximum value for a given stats key.
        设置给定统计键的最大值。

        If the key does not exist, it is set to the given value.
        If it exists, it is set to the maximum of the current value and the given value.
        如果键不存在，则将其设置为给定值。
        如果存在，则将其设置为当前值和给定值的最大值。

        Args:
            key: The stats key to set the maximum value for.
                要设置最大值的统计键。
            value: The value to compare with the current value.
                  要与当前值比较的值。
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。
        """
        self._stats[key] = max(self._stats.setdefault(key, value), value)

    def min_value(self, key, value, spider=None):
        """
        Set the minimum value for a given stats key.
        设置给定统计键的最小值。

        If the key does not exist, it is set to the given value.
        If it exists, it is set to the minimum of the current value and the given value.
        如果键不存在，则将其设置为给定值。
        如果存在，则将其设置为当前值和给定值的最小值。

        Args:
            key: The stats key to set the minimum value for.
                要设置最小值的统计键。
            value: The value to compare with the current value.
                  要与当前值比较的值。
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。
        """
        self._stats[key] = min(self._stats.setdefault(key, value), value)

    def clear_stats(self, spider=None):
        """
        Clear all stats.
        清除所有统计数据。

        Args:
            spider: The spider instance (optional, not used in the base implementation).
                   爬虫实例（可选，在基本实现中未使用）。
        """
        self._stats.clear()

    def open_spider(self, spider):
        """
        Called when a spider is opened.
        当爬虫打开时调用。

        This method can be overridden by subclasses to perform initialization
        when a spider is opened.
        此方法可由子类覆盖，以在爬虫打开时执行初始化。

        Args:
            spider: The spider instance that was opened.
                   已打开的爬虫实例。
        """
        pass

    def close_spider(self, spider, reason):
        """
        Called when a spider is closed.
        当爬虫关闭时调用。

        If STATS_DUMP setting is True, this method dumps the stats to the log.
        It also calls _persist_stats to allow subclasses to persist the stats.
        如果STATS_DUMP设置为True，此方法会将统计数据转储到日志。
        它还调用_persist_stats以允许子类持久化统计数据。

        Args:
            spider: The spider instance that was closed.
                   已关闭的爬虫实例。
            reason: A string describing the reason why the spider was closed.
                   描述爬虫关闭原因的字符串。
        """
        if self._dump:
            logger.info("Dumping aioscrapy stats:\n" + pprint.pformat(self._stats))
        self._persist_stats(self._stats, spider)

    def _persist_stats(self, stats, spider):
        """
        Persist the given stats.
        持久化给定的统计数据。

        This method is called by close_spider and can be overridden by subclasses
        to persist the stats in a custom way.
        此方法由close_spider调用，可由子类覆盖以自定义方式持久化统计数据。

        Args:
            stats: The stats to persist.
                  要持久化的统计数据。
            spider: The spider instance that the stats belong to.
                   统计数据所属的爬虫实例。
        """
        pass


class MemoryStatsCollector(StatsCollector):
    """
    Stats collector that keeps stats in memory.
    将统计数据保存在内存中的统计收集器。

    This collector stores stats in memory and persists them in a dictionary
    keyed by spider name. This allows retrieving stats for a spider even
    after it has been closed.
    此收集器将统计数据存储在内存中，并将其持久化在以爬虫名称为键的字典中。
    这允许即使在爬虫关闭后也能检索爬虫的统计数据。
    """

    def __init__(self, crawler):
        """
        Initialize the memory stats collector.
        初始化内存统计收集器。

        Args:
            crawler: The crawler instance that uses this stats collector.
                    使用此统计收集器的爬虫实例。
        """
        super().__init__(crawler)
        # Dictionary to store stats for each spider by name
        # 用于按名称存储每个爬虫的统计数据的字典
        self.spider_stats = {}

    def _persist_stats(self, stats, spider):
        """
        Persist stats in memory.
        在内存中持久化统计数据。

        This method stores the stats in the spider_stats dictionary,
        using the spider's name as the key.
        此方法将统计数据存储在spider_stats字典中，
        使用爬虫的名称作为键。

        Args:
            stats: The stats to persist.
                  要持久化的统计数据。
            spider: The spider instance that the stats belong to.
                   统计数据所属的爬虫实例。
        """
        self.spider_stats[spider.name] = stats


class DummyStatsCollector(StatsCollector):
    """
    Stats collector that does nothing.
    不执行任何操作的统计收集器。

    This collector is a no-op implementation that doesn't actually store any stats.
    It's useful when stats collection is not needed or should be disabled for
    performance reasons.
    此收集器是一个无操作实现，实际上不存储任何统计数据。
    当不需要统计数据收集或出于性能原因应禁用统计数据收集时，它很有用。
    """

    def get_value(self, key, default=None, spider=None):
        """
        Always returns the default value.
        始终返回默认值。

        Args:
            key: The stats key (ignored).
                统计键（被忽略）。
            default: The default value to return.
                    要返回的默认值。
            spider: The spider instance (ignored).
                   爬虫实例（被忽略）。

        Returns:
            The default value.
            默认值。
        """
        return default

    def set_value(self, key, value, spider=None):
        """
        Does nothing.
        不执行任何操作。

        Args:
            key: The stats key (ignored).
                统计键（被忽略）。
            value: The value to set (ignored).
                  要设置的值（被忽略）。
            spider: The spider instance (ignored).
                   爬虫实例（被忽略）。
        """
        pass

    def set_stats(self, stats, spider=None):
        """
        Does nothing.
        不执行任何操作。

        Args:
            stats: The stats to set (ignored).
                  要设置的统计数据（被忽略）。
            spider: The spider instance (ignored).
                   爬虫实例（被忽略）。
        """
        pass

    def inc_value(self, key, count=1, start=0, spider=None):
        """
        Does nothing.
        不执行任何操作。

        Args:
            key: The stats key (ignored).
                统计键（被忽略）。
            count: The amount to increment by (ignored).
                  要增加的数量（被忽略）。
            start: The starting value (ignored).
                  起始值（被忽略）。
            spider: The spider instance (ignored).
                   爬虫实例（被忽略）。
        """
        pass

    def max_value(self, key, value, spider=None):
        """
        Does nothing.
        不执行任何操作。

        Args:
            key: The stats key (ignored).
                统计键（被忽略）。
            value: The value to compare (ignored).
                  要比较的值（被忽略）。
            spider: The spider instance (ignored).
                   爬虫实例（被忽略）。
        """
        pass

    def min_value(self, key, value, spider=None):
        """
        Does nothing.
        不执行任何操作。

        Args:
            key: The stats key (ignored).
                统计键（被忽略）。
            value: The value to compare (ignored).
                  要比较的值（被忽略）。
            spider: The spider instance (ignored).
                   爬虫实例（被忽略）。
        """
        pass
