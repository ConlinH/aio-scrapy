"""
CloseSpider Extension for AioScrapy
AioScrapy的CloseSpider扩展

CloseSpider is an extension that forces spiders to be closed after certain
conditions are met, such as a timeout, a maximum number of items scraped,
pages downloaded, or errors encountered.
CloseSpider是一个扩展，在满足特定条件后强制关闭爬虫，
例如超时、抓取的最大项目数、下载的页面数或遇到的错误数。

This extension can be configured using the following settings:
此扩展可以使用以下设置进行配置：

* CLOSESPIDER_TIMEOUT: Number of seconds after which the spider will be closed
                      爬虫将被关闭的秒数
* CLOSESPIDER_ITEMCOUNT: Maximum number of items to scrape before closing
                        关闭前要抓取的最大项目数
* CLOSESPIDER_PAGECOUNT: Maximum number of responses to download before closing
                        关闭前要下载的最大响应数
* CLOSESPIDER_ERRORCOUNT: Maximum number of errors to allow before closing
                         关闭前允许的最大错误数

See documentation in docs/topics/extensions.rst for more details.
有关更多详细信息，请参阅docs/topics/extensions.rst中的文档。
"""
import asyncio
from typing import Optional
from collections import defaultdict

from aioscrapy import signals
from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.tools import create_task


class CloseSpider:
    """
    Extension to close spiders when certain conditions are met.
    当满足特定条件时关闭爬虫的扩展。

    This extension monitors the spider's activity and closes it when one of the
    configured conditions is met: timeout, maximum number of items scraped,
    maximum number of pages downloaded, or maximum number of errors encountered.
    此扩展监控爬虫的活动，并在满足配置的条件之一时关闭它：
    超时、抓取的最大项目数、下载的最大页面数或遇到的最大错误数。
    """

    def __init__(self, crawler):
        """
        Initialize the CloseSpider extension.
        初始化CloseSpider扩展。

        Args:
            crawler: The crawler instance that will use this extension.
                    将使用此扩展的爬虫实例。

        Raises:
            NotConfigured: If none of the CLOSESPIDER_* settings are set.
                          如果未设置任何CLOSESPIDER_*设置。
        """
        self.crawler = crawler

        # Dictionary of closing conditions from settings
        # 来自设置的关闭条件字典
        self.close_on = {
            'timeout': crawler.settings.getfloat('CLOSESPIDER_TIMEOUT'),
            'itemcount': crawler.settings.getint('CLOSESPIDER_ITEMCOUNT'),
            'pagecount': crawler.settings.getint('CLOSESPIDER_PAGECOUNT'),
            'errorcount': crawler.settings.getint('CLOSESPIDER_ERRORCOUNT'),
        }

        # If no closing conditions are configured, don't enable the extension
        # 如果未配置关闭条件，则不启用扩展
        if not any(self.close_on.values()):
            raise NotConfigured

        # Counter for each condition
        # 每个条件的计数器
        self.counter = defaultdict(int)

        # Task for timeout handling
        # 用于超时处理的任务
        self.task: Optional[asyncio.tasks.Task] = None

        # Connect to signals based on configured conditions
        # 根据配置的条件连接到信号
        if self.close_on.get('errorcount'):
            crawler.signals.connect(self.error_count, signal=signals.spider_error)
        if self.close_on.get('pagecount'):
            crawler.signals.connect(self.page_count, signal=signals.response_received)
        if self.close_on.get('timeout'):
            crawler.signals.connect(self.timeout_close, signal=signals.spider_opened)
        if self.close_on.get('itemcount'):
            crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)

        # Always connect to spider_closed to clean up
        # 始终连接到spider_closed以进行清理
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a CloseSpider instance from a crawler.
        从爬虫创建CloseSpider实例。

        This is the factory method used by AioScrapy to create extension instances.
        这是AioScrapy用于创建扩展实例的工厂方法。

        Args:
            crawler: The crawler that will use this extension.
                    将使用此扩展的爬虫。

        Returns:
            CloseSpider: A new CloseSpider instance.
                        一个新的CloseSpider实例。
        """
        return cls(crawler)

    async def error_count(self, failure, response, spider):
        """
        Signal handler for the spider_error signal.
        spider_error信号的处理程序。

        Increments the error counter and closes the spider if the maximum
        number of errors has been reached.
        增加错误计数器，如果达到最大错误数，则关闭爬虫。

        Args:
            failure: The exception that was raised.
                    引发的异常。
            response: The response that caused the error.
                     导致错误的响应。
            spider: The spider that raised the exception.
                   引发异常的爬虫。
        """
        # Increment the error counter
        # 增加错误计数器
        self.counter['errorcount'] += 1

        # Check if we've reached the maximum number of errors
        # 检查是否达到最大错误数
        if self.counter['errorcount'] == self.close_on['errorcount']:
            create_task(self.crawler.engine.stop(reason='closespider_errorcount'))

    async def page_count(self, response, request, spider):
        """
        Signal handler for the response_received signal.
        response_received信号的处理程序。

        Increments the page counter and closes the spider if the maximum
        number of pages has been downloaded.
        增加页面计数器，如果下载的页面达到最大数量，则关闭爬虫。

        Args:
            response: The response that was received.
                     接收到的响应。
            request: The request that generated the response.
                    生成响应的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。
        """
        # Increment the page counter
        # 增加页面计数器
        self.counter['pagecount'] += 1

        # Check if we've reached the maximum number of pages
        # 检查是否达到最大页面数
        if self.counter['pagecount'] == self.close_on['pagecount']:
            create_task(self.crawler.engine.stop(reason='closespider_pagecount'))

    async def timeout_close(self, spider):
        """
        Signal handler for the spider_opened signal.
        spider_opened信号的处理程序。

        Starts a task that will close the spider after the configured timeout.
        启动一个任务，该任务将在配置的超时后关闭爬虫。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        async def close():
            """
            Inner function that waits for the timeout and then stops the engine.
            等待超时然后停止引擎的内部函数。
            """
            await asyncio.sleep(self.close_on['timeout'])
            create_task(self.crawler.engine.stop(reason='closespider_timeout'))

        # Start the timeout task
        # 启动超时任务
        self.task = create_task(close())

    async def item_scraped(self, item, spider):
        """
        Signal handler for the item_scraped signal.
        item_scraped信号的处理程序。

        Increments the item counter and closes the spider if the maximum
        number of items has been scraped.
        增加项目计数器，如果抓取的项目达到最大数量，则关闭爬虫。

        Args:
            item: The item that was scraped.
                 抓取的项目。
            spider: The spider that scraped the item.
                   抓取项目的爬虫。
        """
        # Increment the item counter
        # 增加项目计数器
        self.counter['itemcount'] += 1

        # Check if we've reached the maximum number of items
        # 检查是否达到最大项目数
        if self.counter['itemcount'] == self.close_on['itemcount']:
            create_task(self.crawler.engine.stop(reason='closespider_itemcount'))

    def spider_closed(self, spider):
        """
        Signal handler for the spider_closed signal.
        spider_closed信号的处理程序。

        Cancels the timeout task if it's still running when the spider is closed.
        如果爬虫关闭时超时任务仍在运行，则取消该任务。

        Args:
            spider: The spider that was closed.
                   被关闭的爬虫。
        """
        # Cancel the timeout task if it exists and is not done
        # 如果超时任务存在且未完成，则取消它
        if self.task and not self.task.done():
            self.task.cancel()
