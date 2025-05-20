"""
Auto Throttle Extension
自动限速扩展

This extension automatically adjusts the download delay between requests based on
the response latency, helping to avoid overloading servers and improving crawling
efficiency. It dynamically increases or decreases the delay to maintain a target
level of concurrency.
此扩展根据响应延迟自动调整请求之间的下载延迟，有助于避免服务器过载并提高爬取效率。
它动态地增加或减少延迟以维持目标并发级别。

The extension works by measuring the latency of responses and adjusting the delay
to try to maintain a specified number of concurrent requests to each domain.
该扩展通过测量响应的延迟并调整延迟来尝试维持对每个域的指定数量的并发请求。
"""
from aioscrapy import signals
from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.log import logger


class AutoThrottle:
    """
    Extension for automatically adjusting download delays based on response latency.
    基于响应延迟自动调整下载延迟的扩展。

    This extension dynamically adjusts the download delay between requests to maintain
    a target level of concurrency. It helps to avoid overloading servers while
    maximizing the crawling speed.
    此扩展动态调整请求之间的下载延迟以维持目标并发级别。它有助于避免服务器过载，
    同时最大化爬取速度。
    """

    def __init__(self, crawler):
        """
        Initialize the AutoThrottle extension.
        初始化AutoThrottle扩展。

        Args:
            crawler: The crawler that will use this extension.
                    将使用此扩展的爬虫。

        Raises:
            NotConfigured: If AUTOTHROTTLE_ENABLED is not set to True in the settings.
                          如果在设置中未将AUTOTHROTTLE_ENABLED设置为True。
        """
        # Store the crawler
        # 存储爬虫
        self.crawler = crawler

        # Check if the extension is enabled
        # 检查扩展是否已启用
        if not crawler.settings.getbool('AUTOTHROTTLE_ENABLED'):
            raise NotConfigured

        # Get debug setting
        # 获取调试设置
        self.debug = crawler.settings.getbool("AUTOTHROTTLE_DEBUG")

        # Get target concurrency setting
        # 获取目标并发设置
        self.target_concurrency = crawler.settings.getfloat("AUTOTHROTTLE_TARGET_CONCURRENCY")

        # Connect to signals
        # 连接到信号
        crawler.signals.connect(self._spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(self._response_downloaded, signal=signals.response_downloaded)

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create an AutoThrottle instance from a crawler.
        从爬虫创建AutoThrottle实例。

        This is the factory method used by Scrapy to create the extension.
        这是Scrapy用于创建扩展的工厂方法。

        Args:
            crawler: The crawler that will use this extension.
                    将使用此扩展的爬虫。

        Returns:
            AutoThrottle: A new AutoThrottle instance.
                         一个新的AutoThrottle实例。
        """
        # Create and return a new instance
        # 创建并返回一个新实例
        return cls(crawler)

    def _spider_opened(self, spider):
        """
        Handle the spider_opened signal.
        处理spider_opened信号。

        This method is called when a spider is opened. It initializes the minimum,
        maximum, and starting download delays.
        当爬虫打开时调用此方法。它初始化最小、最大和起始下载延迟。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Calculate minimum delay
        # 计算最小延迟
        self.mindelay = self._min_delay(spider)

        # Calculate maximum delay
        # 计算最大延迟
        self.maxdelay = self._max_delay(spider)

        # Set initial download delay for the spider
        # 为爬虫设置初始下载延迟
        spider.download_delay = self._start_delay(spider)

    def _min_delay(self, spider):
        """
        Get the minimum download delay.
        获取最小下载延迟。

        This method returns the minimum download delay, which is either the spider's
        download_delay attribute or the DOWNLOAD_DELAY setting.
        此方法返回最小下载延迟，即爬虫的download_delay属性或DOWNLOAD_DELAY设置。

        Args:
            spider: The spider to get the minimum delay for.
                   要获取最小延迟的爬虫。

        Returns:
            float: The minimum download delay in seconds.
                  最小下载延迟（以秒为单位）。
        """
        # Get settings
        # 获取设置
        s = self.crawler.settings

        # Return spider's download_delay attribute or DOWNLOAD_DELAY setting
        # 返回爬虫的download_delay属性或DOWNLOAD_DELAY设置
        return getattr(spider, 'download_delay', s.getfloat('DOWNLOAD_DELAY'))

    def _max_delay(self, spider):
        """
        Get the maximum download delay.
        获取最大下载延迟。

        This method returns the maximum download delay from the AUTOTHROTTLE_MAX_DELAY setting.
        此方法从AUTOTHROTTLE_MAX_DELAY设置返回最大下载延迟。

        Args:
            spider: The spider to get the maximum delay for.
                   要获取最大延迟的爬虫。

        Returns:
            float: The maximum download delay in seconds.
                  最大下载延迟（以秒为单位）。
        """
        # Return AUTOTHROTTLE_MAX_DELAY setting
        # 返回AUTOTHROTTLE_MAX_DELAY设置
        return self.crawler.settings.getfloat('AUTOTHROTTLE_MAX_DELAY')

    def _start_delay(self, spider):
        """
        Get the initial download delay.
        获取初始下载延迟。

        This method returns the initial download delay, which is the maximum of
        the minimum delay and the AUTOTHROTTLE_START_DELAY setting.
        此方法返回初始下载延迟，即最小延迟和AUTOTHROTTLE_START_DELAY设置的最大值。

        Args:
            spider: The spider to get the start delay for.
                   要获取起始延迟的爬虫。

        Returns:
            float: The initial download delay in seconds.
                  初始下载延迟（以秒为单位）。
        """
        # Return the maximum of minimum delay and AUTOTHROTTLE_START_DELAY setting
        # 返回最小延迟和AUTOTHROTTLE_START_DELAY设置的最大值
        return max(self.mindelay, self.crawler.settings.getfloat('AUTOTHROTTLE_START_DELAY'))

    def _response_downloaded(self, response, request, spider):
        """
        Handle the response_downloaded signal.
        处理response_downloaded信号。

        This method is called when a response is downloaded. It adjusts the download
        delay based on the response latency and logs debug information if enabled.
        当下载响应时调用此方法。它根据响应延迟调整下载延迟，并在启用时记录调试信息。

        Args:
            response: The downloaded response.
                     下载的响应。
            request: The request that generated the response.
                    生成响应的请求。
            spider: The spider that made the request.
                   发出请求的爬虫。
        """
        # Get the download slot for the request
        # 获取请求的下载槽
        key, slot = self._get_slot(request, spider)

        # Get the download latency from the request metadata
        # 从请求元数据获取下载延迟
        latency = request.meta.get('download_latency')

        # If latency or slot is not available, do nothing
        # 如果延迟或槽不可用，则不执行任何操作
        if latency is None or slot is None:
            return

        # Store the old delay for logging
        # 存储旧延迟以供记录
        olddelay = slot.delay

        # Adjust the delay based on the latency and response
        # 根据延迟和响应调整延迟
        self._adjust_delay(slot, latency, response)

        # Log debug information if enabled
        # 如果启用，则记录调试信息
        if self.debug:
            # Calculate the delay difference
            # 计算延迟差异
            diff = slot.delay - olddelay

            # Get the response size
            # 获取响应大小
            size = len(response.body)

            # Get the number of concurrent requests
            # 获取并发请求数
            conc = len(slot.transferring)

            # Log the debug information
            # 记录调试信息
            logger.info(
                "slot: %(slot)s | conc:%(concurrency)2d | "
                "delay:%(delay)5d ms (%(delaydiff)+d) | "
                "latency:%(latency)5d ms | size:%(size)6d bytes" % {
                    'slot': key, 'concurrency': conc,
                    'delay': slot.delay * 1000, 'delaydiff': diff * 1000,
                    'latency': latency * 1000, 'size': size
                }
            )

    def _get_slot(self, request, spider):
        """
        Get the download slot for a request.
        获取请求的下载槽。

        This method returns the download slot key and the slot object for a request.
        此方法返回请求的下载槽键和槽对象。

        Args:
            request: The request to get the slot for.
                    要获取槽的请求。
            spider: The spider that made the request.
                   发出请求的爬虫。

        Returns:
            tuple: A tuple containing the slot key and the slot object.
                  包含槽键和槽对象的元组。
        """
        # Get the download slot key from the request metadata
        # 从请求元数据获取下载槽键
        key = request.meta.get('download_slot')

        # Return the key and the corresponding slot object
        # 返回键和相应的槽对象
        return key, self.crawler.engine.downloader.slots.get(key)

    def _adjust_delay(self, slot, latency, response):
        """
        Adjust the download delay based on the response latency.
        根据响应延迟调整下载延迟。

        This method implements the delay adjustment policy. It calculates a new
        download delay based on the response latency and the target concurrency,
        and updates the slot's delay if appropriate.
        此方法实现延迟调整策略。它根据响应延迟和目标并发计算新的下载延迟，
        并在适当时更新槽的延迟。

        Args:
            slot: The download slot to adjust the delay for.
                 要调整延迟的下载槽。
            latency: The download latency of the response.
                    响应的下载延迟。
            response: The downloaded response.
                     下载的响应。
        """
        # If a server needs `latency` seconds to respond then
        # we should send a request each `latency/N` seconds
        # to have N requests processed in parallel
        # 如果服务器需要`latency`秒来响应，那么我们应该每`latency/N`秒发送一个请求，
        # 以便并行处理N个请求
        target_delay = latency / self.target_concurrency

        # Adjust the delay to make it closer to target_delay
        # 调整延迟使其更接近target_delay
        new_delay = (slot.delay + target_delay) / 2.0

        # If target delay is bigger than old delay, then use it instead of mean.
        # It works better with problematic sites.
        # 如果目标延迟大于旧延迟，则使用它而不是平均值。
        # 这对于有问题的站点效果更好。
        new_delay = max(target_delay, new_delay)

        # Make sure self.mindelay <= new_delay <= self.max_delay
        # 确保self.mindelay <= new_delay <= self.max_delay
        new_delay = min(max(self.mindelay, new_delay), self.maxdelay)

        # Dont adjust delay if response status != 200 and new delay is smaller
        # than old one, as error pages (and redirections) are usually small and
        # so tend to reduce latency, thus provoking a positive feedback by
        # reducing delay instead of increase.
        # 如果响应状态 != 200且新延迟小于旧延迟，则不调整延迟，因为错误页面（和重定向）
        # 通常很小，因此倾向于减少延迟，从而引发正反馈，减少延迟而不是增加。
        if response.status != 200 and new_delay <= slot.delay:
            return

        # Update the slot's delay
        # 更新槽的延迟
        slot.delay = new_delay
