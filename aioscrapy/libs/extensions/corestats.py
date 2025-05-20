"""
Core Stats Extension
核心统计扩展

This extension collects and records essential statistics about the crawling process,
including start and finish times, elapsed time, number of items scraped, number of
responses received, and information about dropped items.
此扩展收集并记录有关爬取过程的基本统计信息，包括开始和结束时间、经过的时间、
已抓取的项目数量、已接收的响应数量以及有关丢弃项目的信息。

These statistics are useful for monitoring the performance and behavior of spiders,
and can be accessed through the Scrapy stats collector.
这些统计信息对于监控爬虫的性能和行为很有用，可以通过Scrapy统计收集器访问。
"""
from datetime import datetime

from aioscrapy import signals


class CoreStats:
    """
    Extension for collecting core statistics about the crawling process.
    用于收集有关爬取过程的核心统计信息的扩展。

    This extension hooks into various Scrapy signals to collect statistics about
    the crawling process, such as start and finish times, number of items scraped,
    number of responses received, and information about dropped items.
    此扩展挂钩到各种Scrapy信号，以收集有关爬取过程的统计信息，例如开始和结束时间、
    已抓取的项目数量、已接收的响应数量以及有关丢弃项目的信息。
    """

    def __init__(self, stats):
        """
        Initialize the CoreStats extension.
        初始化CoreStats扩展。

        Args:
            stats: The Scrapy stats collector.
                  Scrapy统计收集器。
        """
        # Stats collector
        # 统计收集器
        self.stats = stats

        # Spider start time (will be set when spider opens)
        # 爬虫开始时间（将在爬虫打开时设置）
        self.start_time = None

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a CoreStats instance from a crawler.
        从爬虫创建CoreStats实例。

        This is the factory method used by Scrapy to create the extension.
        这是Scrapy用于创建扩展的工厂方法。

        Args:
            crawler: The crawler that will use this extension.
                    将使用此扩展的爬虫。

        Returns:
            CoreStats: A new CoreStats instance.
                      一个新的CoreStats实例。
        """
        # Create a new instance with the crawler's stats collector
        # 使用爬虫的统计收集器创建一个新实例
        o = cls(crawler.stats)

        # Connect to signals
        # 连接到信号
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.response_received, signal=signals.response_received)

        # Return the new instance
        # 返回新实例
        return o

    def spider_opened(self, spider):
        """
        Handle the spider_opened signal.
        处理spider_opened信号。

        This method is called when a spider is opened. It records the start time
        of the spider.
        当爬虫打开时调用此方法。它记录爬虫的开始时间。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Record the start time
        # 记录开始时间
        self.start_time = datetime.now()

        # Store the start time in the stats
        # 将开始时间存储在统计信息中
        self.stats.set_value('start_time', str(self.start_time), spider=spider)

    def spider_closed(self, spider, reason):
        """
        Handle the spider_closed signal.
        处理spider_closed信号。

        This method is called when a spider is closed. It calculates and records
        the finish time, elapsed time, and finish reason.
        当爬虫关闭时调用此方法。它计算并记录结束时间、经过的时间和结束原因。

        Args:
            spider: The spider that was closed.
                   被关闭的爬虫。
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        # Record the finish time
        # 记录结束时间
        finish_time = datetime.now()

        # Calculate elapsed time
        # 计算经过的时间
        elapsed_time = finish_time - self.start_time
        elapsed_time_seconds = elapsed_time.total_seconds()

        # Store finish statistics in the stats
        # 将结束统计信息存储在统计信息中
        self.stats.set_value('elapsed_time_seconds', elapsed_time_seconds, spider=spider)
        self.stats.set_value('finish_time', str(finish_time), spider=spider)
        self.stats.set_value('finish_reason', reason, spider=spider)

    def item_scraped(self, item, spider):
        """
        Handle the item_scraped signal.
        处理item_scraped信号。

        This method is called when an item is scraped by a spider. It increments
        the item_scraped_count statistic.
        当爬虫抓取项目时调用此方法。它增加item_scraped_count统计信息。

        Args:
            item: The item that was scraped.
                 被抓取的项目。
            spider: The spider that scraped the item.
                   抓取项目的爬虫。
        """
        # Increment the item scraped count
        # 增加已抓取项目计数
        self.stats.inc_value('item_scraped_count', spider=spider)

    def response_received(self, spider):
        """
        Handle the response_received signal.
        处理response_received信号。

        This method is called when a response is received by a spider. It increments
        the response_received_count statistic.
        当爬虫接收到响应时调用此方法。它增加response_received_count统计信息。

        Args:
            spider: The spider that received the response.
                   接收响应的爬虫。
        """
        # Increment the response received count
        # 增加已接收响应计数
        self.stats.inc_value('response_received_count', spider=spider)

    def item_dropped(self, item, spider, exception):
        """
        Handle the item_dropped signal.
        处理item_dropped信号。

        This method is called when an item is dropped by a spider. It increments
        the item_dropped_count statistic and records the reason why the item was dropped.
        当爬虫丢弃项目时调用此方法。它增加item_dropped_count统计信息，并记录项目被丢弃的原因。

        Args:
            item: The item that was dropped.
                 被丢弃的项目。
            spider: The spider that dropped the item.
                   丢弃项目的爬虫。
            exception: The exception that caused the item to be dropped.
                      导致项目被丢弃的异常。
        """
        # Get the reason from the exception class name
        # 从异常类名获取原因
        reason = exception.__class__.__name__

        # Increment the item dropped count
        # 增加已丢弃项目计数
        self.stats.inc_value('item_dropped_count', spider=spider)

        # Increment the count for this specific reason
        # 增加此特定原因的计数
        self.stats.inc_value(f'item_dropped_reasons_count/{reason}', spider=spider)
