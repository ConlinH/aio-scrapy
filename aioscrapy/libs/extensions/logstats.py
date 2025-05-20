"""
Log Stats Extension
日志统计扩展

This extension logs basic crawling statistics periodically during the spider run.
It provides information about the number of pages crawled, items scraped, and their
respective rates per minute, which is useful for monitoring the progress and
performance of spiders in real-time.
此扩展在爬虫运行期间定期记录基本的爬取统计信息。它提供有关已爬取的页面数量、
已抓取的项目数量及其各自的每分钟速率的信息，这对于实时监控爬虫的进度和性能很有用。
"""
import asyncio

from aioscrapy import signals
from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.log import logger
from aioscrapy.utils.tools import create_task


class LogStats:
    """
    Extension for logging basic crawling statistics periodically.
    用于定期记录基本爬取统计信息的扩展。

    This extension logs information about the number of pages crawled and items
    scraped, along with their respective rates per minute. The statistics are
    logged at regular intervals during the spider run, providing real-time
    feedback on the spider's performance.
    此扩展记录有关已爬取的页面数量和已抓取的项目数量的信息，以及它们各自的
    每分钟速率。统计信息在爬虫运行期间以固定的时间间隔记录，提供有关爬虫性能
    的实时反馈。
    """

    def __init__(self, stats, interval=60.0):
        """
        Initialize the LogStats extension.
        初始化LogStats扩展。

        Args:
            stats: The Scrapy stats collector.
                  Scrapy统计收集器。
            interval: The time interval (in seconds) between log messages.
                     日志消息之间的时间间隔（以秒为单位）。
                     Defaults to 60.0 seconds.
                     默认为60.0秒。
        """
        # Stats collector
        # 统计收集器
        self.stats = stats

        # Interval between log messages (in seconds)
        # 日志消息之间的间隔（以秒为单位）
        self.interval = interval

        # Multiplier to convert stats to per-minute rates
        # 将统计数据转换为每分钟速率的乘数
        self.multiplier = 60.0 / self.interval

        # Async task for periodic logging
        # 用于定期记录的异步任务
        self.task = None

        # Previous values for calculating rates
        # 用于计算速率的先前值
        self.pagesprev = 0
        self.itemsprev = 0

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a LogStats instance from a crawler.
        从爬虫创建LogStats实例。

        This is the factory method used by Scrapy to create the extension.
        这是Scrapy用于创建扩展的工厂方法。

        Args:
            crawler: The crawler that will use this extension.
                    将使用此扩展的爬虫。

        Returns:
            LogStats: A new LogStats instance.
                     一个新的LogStats实例。

        Raises:
            NotConfigured: If LOGSTATS_INTERVAL is not set or is zero in the settings.
                          如果在设置中未设置LOGSTATS_INTERVAL或其值为零。
        """
        # Get the log interval from settings
        # 从设置获取日志间隔
        interval = crawler.settings.getfloat('LOGSTATS_INTERVAL')

        # If no interval is configured, disable the extension
        # 如果未配置间隔，则禁用扩展
        if not interval:
            raise NotConfigured

        # Create a new instance with the crawler's stats collector and the configured interval
        # 使用爬虫的统计收集器和配置的间隔创建一个新实例
        o = cls(crawler.stats, interval)

        # Connect to signals
        # 连接到信号
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)

        # Return the new instance
        # 返回新实例
        return o

    def spider_opened(self, spider):
        """
        Handle the spider_opened signal.
        处理spider_opened信号。

        This method is called when a spider is opened. It starts the periodic
        logging task.
        当爬虫打开时调用此方法。它启动定期记录任务。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Start the periodic logging task
        # 启动定期记录任务
        self.task = create_task(self.log(spider))

    async def log(self, spider):
        """
        Log the current crawling statistics and schedule the next log.
        记录当前爬取统计信息并安排下一次记录。

        This method retrieves the current statistics, calculates the rates,
        logs the information, and then schedules itself to run again after
        the configured interval.
        此方法检索当前统计信息，计算速率，记录信息，然后安排自己在配置的
        间隔后再次运行。

        Args:
            spider: The spider whose statistics to log.
                   要记录其统计信息的爬虫。
        """
        # Wait for the configured interval
        # 等待配置的间隔
        await asyncio.sleep(self.interval)

        # Get current statistics
        # 获取当前统计信息
        items = self.stats.get_value('item_scraped_count', 0)
        pages = self.stats.get_value('response_received_count', 0)

        # Calculate rates (per minute)
        # 计算速率（每分钟）
        irate = (items - self.itemsprev) * self.multiplier
        prate = (pages - self.pagesprev) * self.multiplier

        # Update previous values for next calculation
        # 更新先前值以供下次计算
        self.pagesprev, self.itemsprev = pages, items

        # Prepare log message
        # 准备日志消息
        msg = ("<%(spider_name)s> Crawled %(pages)d pages (at %(pagerate)d pages/min), "
               "scraped %(items)d items (at %(itemrate)d items/min)")
        log_args = {'pages': pages, 'pagerate': prate, 'spider_name': spider.name,
                    'items': items, 'itemrate': irate}

        # Log the statistics
        # 记录统计信息
        logger.info(msg % log_args)

        # Schedule the next log
        # 安排下一次记录
        self.task = create_task(self.log(spider))

    def spider_closed(self, spider, reason):
        """
        Handle the spider_closed signal.
        处理spider_closed信号。

        This method is called when a spider is closed. It cancels the periodic
        logging task if it's still running.
        当爬虫关闭时调用此方法。如果定期记录任务仍在运行，它会取消该任务。

        Args:
            spider: The spider that was closed.
                   被关闭的爬虫。
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        # Cancel the logging task if it's still running
        # 如果记录任务仍在运行，则取消它
        if self.task and not self.task.done():
            self.task.cancel()
