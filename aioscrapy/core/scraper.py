"""
Scraper Module
抓取器模块

This module implements the Scraper component which parses responses and
extracts information from them. The Scraper is the central component that
coordinates the processing of downloaded content and manages the flow of
extracted data through the system.
此模块实现了Scraper组件，用于解析响应并从中提取信息。Scraper是协调下载内容处理
并管理提取数据在系统中流动的中央组件。

The Scraper is responsible for:
Scraper负责：
1. Processing downloaded responses through spider callbacks
   通过爬虫回调处理下载的响应
2. Handling spider output (requests and items)
   处理爬虫输出（请求和项目）
3. Processing items through the item pipeline
   通过项目管道处理项目
4. Handling errors during the scraping process
   处理抓取过程中的错误
5. Managing memory usage and concurrency
   管理内存使用和并发性

The module contains two main classes:
模块包含两个主要类：
1. Slot: Tracks active requests and memory usage for a spider
        跟踪爬虫的活动请求和内存使用情况
2. Scraper: Processes responses and extracts items
          处理响应并提取项目
"""
import asyncio
from typing import Any, AsyncGenerator, Set, Union, Optional

import aioscrapy
from aioscrapy import signals, Spider
from aioscrapy.exceptions import CloseSpider, DropItem, IgnoreRequest
from aioscrapy.http import WebDriverResponse
from aioscrapy.http import Request, Response
from aioscrapy.logformatter import LogFormatter
from aioscrapy.middleware import ItemPipelineManager, SpiderMiddlewareManager
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_object
from aioscrapy.utils.tools import call_helper, create_task


class Slot:
    """
    Scraper slot (one per running spider).
    抓取器槽（每个运行的爬虫一个）。

    This class keeps track of active requests and memory usage
    to control the scraper's memory footprint.
    此类跟踪活动请求和内存使用情况，以控制抓取器的内存占用。
    """

    MIN_RESPONSE_SIZE = 1024  # Minimum size in bytes to account for a response
                             # 计算响应的最小字节大小

    def __init__(self, max_active_size: int = 5000000):
        """
        Initialize a scraper slot.
        初始化抓取器槽。

        Args:
            max_active_size: Maximum allowed size in bytes for active responses.
                            活动响应允许的最大字节大小。
                            Default is 5MB.
                            默认为5MB。
        """
        self.max_active_size = max_active_size  # Maximum memory allowed for active responses
                                               # 活动响应允许的最大内存
        self.active: Set[Request] = set()  # Set of active requests being processed
                                          # 正在处理的活动请求集合
        self.active_size: int = 0  # Current memory usage of active responses
                                  # 活动响应的当前内存使用量
        self.itemproc_size: int = 0  # Number of items being processed by the item pipeline
                                    # 项目管道正在处理的项目数量

    def add_response_request(self, result: Union[Response, BaseException], request: Request) -> None:
        """
        Add a request and its result to the active set.
        将请求及其结果添加到活动集合中。

        This method tracks the request and updates the memory usage counter
        based on the size of the response.
        此方法跟踪请求并根据响应的大小更新内存使用计数器。

        Args:
            result: The response or exception from processing the request.
                   处理请求的响应或异常。
            request: The request being processed.
                    正在处理的请求。
        """
        self.active.add(request)
        if isinstance(result, Response):
            # Account for the response body size, with a minimum threshold
            # 计算响应体大小，设有最小阈值
            self.active_size += max(len(result.body), self.MIN_RESPONSE_SIZE)
        else:
            # For exceptions, use the minimum size
            # 对于异常，使用最小大小
            self.active_size += self.MIN_RESPONSE_SIZE

    def finish_response(self, request: Request, result: Union[Response, BaseException]) -> None:
        """
        Remove a request and its result from the active set.
        从活动集合中移除请求及其结果。

        This method is called when processing of a request is complete.
        It updates the memory usage counter and cleans up resources.
        当请求处理完成时调用此方法。它更新内存使用计数器并清理资源。

        Args:
            request: The request that has been processed.
                    已处理的请求。
            result: The response or exception from processing the request.
                   处理请求的响应或异常。
        """
        self.active.remove(request)
        if isinstance(result, Response):
            # Decrease the memory counter by the response size
            # 按响应大小减少内存计数器
            self.active_size -= max(len(result.body), self.MIN_RESPONSE_SIZE)
            # Clear cached selector to free memory
            # 清除缓存的选择器以释放内存
            result._cached_selector = None
        else:
            # For exceptions, decrease by the minimum size
            # 对于异常，按最小大小减少
            self.active_size -= self.MIN_RESPONSE_SIZE

    def is_idle(self) -> bool:
        """
        Check if the slot is idle (no active requests).
        检查槽是否空闲（没有活动请求）。

        Returns:
            bool: True if there are no active requests, False otherwise.
                 如果没有活动请求，则为True，否则为False。
        """
        return not self.active

    def needs_backout(self) -> bool:
        """
        Check if the slot needs to back out (stop accepting new requests).
        检查槽是否需要退出（停止接受新请求）。

        This method determines if the memory usage has exceeded the maximum
        allowed size, in which case the scraper should stop accepting new
        requests until some current ones complete.
        此方法确定内存使用是否已超过允许的最大大小，在这种情况下，
        抓取器应停止接受新请求，直到一些当前请求完成。

        Returns:
            bool: True if memory usage exceeds the maximum, False otherwise.
                 如果内存使用超过最大值，则为True，否则为False。
        """
        return self.active_size > self.max_active_size


class Scraper:
    """
    The Scraper processes downloaded responses and extracts items.
    Scraper处理下载的响应并提取项目。

    This class is responsible for:
    此类负责：
    1. Processing responses through spider callbacks
       通过爬虫回调处理响应
    2. Handling spider output (requests and items)
       处理爬虫输出（请求和项目）
    3. Processing items through the item pipeline
       通过项目管道处理项目
    4. Managing memory usage and concurrency
       管理内存使用和并发
    """

    def __init__(
            self,
            crawler: "aioscrapy.Crawler",
            slot: Slot,
            spidermw: SpiderMiddlewareManager,
            itemproc: ItemPipelineManager,
    ):
        """
        Initialize the Scraper.
        初始化Scraper。

        Args:
            crawler: The crawler instance that this scraper belongs to.
                    此抓取器所属的爬虫实例。
            slot: The slot for tracking active requests and memory usage.
                 用于跟踪活动请求和内存使用的槽。
            spidermw: The spider middleware manager.
                     爬虫中间件管理器。
            itemproc: The item pipeline manager.
                     项目管道管理器。
        """
        self.crawler = crawler
        self.spider: Spider = crawler.spider
        self.signals: SignalManager = self.crawler.signals
        self.logformatter: LogFormatter = self.crawler.logformatter

        self.slot = slot  # Slot for tracking active requests and memory
                         # 用于跟踪活动请求和内存的槽
        self.spidermw = spidermw  # Spider middleware manager
                                 # 爬虫中间件管理器
        self.itemproc = itemproc  # Item pipeline manager
                                 # 项目管道管理器

        self.finish: bool = False  # Flag to indicate if scraper is shutting down
                                  # 指示抓取器是否正在关闭的标志
        # Semaphore to limit concurrent parsing
        # 用于限制并发解析的信号量
        self.concurrent_parser = asyncio.Semaphore(crawler.settings.getint('CONCURRENT_PARSER', 1))

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.Crawler") -> "Scraper":
        """
        Create a Scraper instance from a crawler.
        从爬虫创建Scraper实例。

        This factory method creates a new Scraper instance with all the
        necessary components initialized from the crawler.
        此工厂方法创建一个新的Scraper实例，所有必要的组件都从爬虫初始化。

        Args:
            crawler: The crawler instance that will use this scraper.
                    将使用此抓取器的爬虫实例。

        Returns:
            Scraper: A new scraper instance.
                    一个新的抓取器实例。
        """
        # Create the scraper instance with all required components
        # 创建具有所有必需组件的抓取器实例
        instance: "Scraper" = cls(
            crawler,
            # Create a slot with the maximum active size from settings
            # 使用设置中的最大活动大小创建槽
            Slot(crawler.settings.getint('SCRAPER_SLOT_MAX_ACTIVE_SIZE')),
            # Initialize the spider middleware manager
            # 初始化爬虫中间件管理器
            await call_helper(SpiderMiddlewareManager.from_crawler, crawler),
            # Initialize the item pipeline manager
            # 初始化项目管道管理器
            await call_helper(load_object(crawler.settings['ITEM_PROCESSOR']).from_crawler, crawler)
        )
        # Open the item processor for the spider
        # 为爬虫打开项目处理器
        await instance.itemproc.open_spider(crawler.spider)
        return instance

    async def close(self) -> None:
        """
        Close a spider being scraped and release its resources.
        关闭正在抓取的爬虫并释放其资源。

        This method closes the item processor for the spider and
        marks the scraper as finished.
        此方法关闭爬虫的项目处理器并将抓取器标记为已完成。
        """
        await self.itemproc.close_spider(self.spider)
        self.finish = True

    def is_idle(self) -> bool:
        """
        Check if the scraper is idle (no active requests).
        检查抓取器是否空闲（没有活动请求）。

        Returns:
            bool: True if there aren't any more requests to process, False otherwise.
                 如果没有更多要处理的请求，则为True，否则为False。
        """
        return self.slot.is_idle()

    def needs_backout(self) -> bool:
        """
        Check if the scraper needs to back out (stop accepting new requests).
        检查抓取器是否需要退出（停止接受新请求）。

        This method delegates to the slot to determine if memory usage
        has exceeded the maximum allowed size.
        此方法委托给槽来确定内存使用是否已超过允许的最大大小。

        Returns:
            bool: True if memory usage exceeds the maximum, False otherwise.
                 如果内存使用超过最大值，则为True，否则为False。
        """
        return self.slot.needs_backout()

    async def enqueue_scrape(self, result: Union[Response, BaseException], request: Request) -> None:
        """
        Enqueue a response or exception for scraping.
        将响应或异常排队等待抓取。

        This method adds the request and result to the active set in the slot
        and starts the scraping process.
        此方法将请求和结果添加到槽中的活动集合，并开始抓取过程。

        Args:
            result: The response or exception from processing the request.
                   处理请求的响应或异常。
            request: The request that was processed.
                    已处理的请求。
        """
        # Cache the results in the slot
        # 在槽中缓存结果
        self.slot.add_response_request(result, request)
        await self._scrape(result, request)

    async def _scrape(self, result: Union[Response, BaseException], request: Request) -> None:
        """
        Handle the downloaded response or failure through the spider callback/errback.
        通过爬虫回调/错误回调处理下载的响应或失败。

        This method processes the response or exception through the appropriate
        spider callback or errback, and handles any output or errors.
        此方法通过适当的爬虫回调或错误回调处理响应或异常，并处理任何输出或错误。

        Args:
            result: The response or exception from processing the request.
                   处理请求的响应或异常。
            request: The request that was processed.
                    已处理的请求。
        """
        # Use semaphore to limit concurrent parsing
        # 使用信号量限制并发解析
        async with self.concurrent_parser:
            try:
                # Validate the result type
                # 验证结果类型
                if not isinstance(result, (Response, BaseException)):
                    raise TypeError(f"Incorrect type: expected Response or Failure, got {type(result)}: {result!r}")
                try:
                    # Process the result through spider middleware and callbacks
                    # 通过爬虫中间件和回调处理结果
                    output = await self._scrape2(result, request)  # returns spider's processed output
                except BaseException as e:
                    # Handle any errors during processing
                    # 处理处理过程中的任何错误
                    await self.handle_spider_error(e, request, result)
                else:
                    # Handle the output from the spider
                    # 处理爬虫的输出
                    await self.handle_spider_output(output, request, result)
            except BaseException as e:
                # Handle any errors that weren't caught earlier
                # 处理之前未捕获的任何错误
                await self.handle_spider_error(e, request, result)
            finally:
                # Update dupefilter with parse status
                # 使用解析状态更新重复过滤器
                self.spider.dupefilter and \
                    not request.dont_filter and \
                    await self.spider.dupefilter.done(request, done_type="parse_ok" if getattr(request, "parse_ok", False) else "parse_err")

                # Release playwright/drissionpage response resources if applicable
                # 如果适用，释放playwright/drissionpage等响应资源
                if isinstance(result, WebDriverResponse):
                    await result.release()

                # Delete the cache result from the slot
                # 从槽中删除缓存结果
                self.slot.finish_response(request, result)

    async def _scrape2(self, result: Union[Response, BaseException], request: Request) -> Optional[AsyncGenerator]:
        """
        Handle the different cases of request's result being a Response or an Exception.
        处理请求结果为Response或Exception的不同情况。

        This method routes the result to the appropriate processing path based on
        whether it's a successful response or an exception.
        此方法根据结果是成功的响应还是异常，将结果路由到适当的处理路径。

        Args:
            result: The response or exception from processing the request.
                   处理请求的响应或异常。
            request: The request that was processed.
                    已处理的请求。

        Returns:
            Optional[AsyncGenerator]: The output from processing the result, or None.
                                     处理结果的输出，或None。
        """
        if isinstance(result, Response):
            # For responses, pass through spider middleware
            # 对于响应，通过爬虫中间件传递
            # Throw the response to the middleware of the spider,
            # and the processing results will be processed to the self.call_spider
            # 将响应抛给爬虫的中间件，处理结果将被处理到self.call_spider
            return await self.spidermw.scrape_response(self.call_spider, result, request, self.spider)
        else:
            try:
                # For exceptions, call spider directly (bypass middleware)
                # 对于异常，直接调用爬虫（绕过中间件）
                # Processing Exception of download and download's middleware
                # 处理下载和下载中间件的异常
                return await self.call_spider(result, request)
            except BaseException as e:
                # Log any errors that occur during exception handling
                # 记录异常处理期间发生的任何错误
                await self._log_download_errors(e, result, request)

    async def call_spider(self, result: Union[Response, BaseException], request: Request) -> Optional[AsyncGenerator]:
        """
        Call the appropriate spider method to handle a result.
        调用适当的爬虫方法来处理结果。

        This method calls either the callback or errback method of the spider
        based on whether the result is a response or an exception.
        此方法根据结果是响应还是异常，调用爬虫的回调或错误回调方法。

        Args:
            result: The response or exception to process.
                   要处理的响应或异常。
            request: The request associated with the result.
                    与结果关联的请求。

        Returns:
            Optional[AsyncGenerator]: The output from the spider method, or None.
                                     爬虫方法的输出，或None。

        Raises:
            BaseException: If result is an exception and no errback is defined.
                          如果结果是异常且未定义错误回调。
        """
        if isinstance(result, Response):
            # For responses, call the callback method
            # 对于响应，调用回调方法
            # throws Response to Spider's parse
            # 将Response抛给爬虫的parse
            callback = request.callback or self.spider._parse
            return await call_helper(callback, result, **result.request.cb_kwargs)
        else:
            # For exceptions, call the errback method if defined
            # 对于异常，如果定义了错误回调方法，则调用它
            if request.errback is None:
                # If no errback is defined, re-raise the exception
                # 如果未定义错误回调，则重新引发异常
                raise result
            # throws Exception of download and download's middleware to Spider's errback
            # 将下载和下载中间件的异常抛给爬虫的errback
            return await call_helper(request.errback, result)

    async def handle_spider_error(self, exc: BaseException, request: Request, response: Union[Response, BaseException]) -> None:
        """
        Handle errors raised during spider callback processing.
        处理爬虫回调处理期间引发的错误。

        This method handles exceptions that occur during the processing of
        responses by spider callbacks. It logs the error, sends the spider_error signal,
        and updates error statistics.
        此方法处理爬虫回调处理响应期间发生的异常。它记录错误、发送spider_error信号
        并更新错误统计信息。

        Args:
            exc: The exception that was raised.
                引发的异常。
            request: The request being processed when the error occurred.
                    发生错误时正在处理的请求。
            response: The response or exception being processed when the error occurred.
                     发生错误时正在处理的响应或异常。
                     This can be either a Response object or an Exception object in case
                     the error occurred during processing of an errback.
                     这可以是Response对象或Exception对象，以防错误发生在处理errback期间。
        """
        # Handle CloseSpider exceptions specially
        # 特别处理CloseSpider异常
        if isinstance(exc, CloseSpider):
            create_task(self.crawler.engine.close_spider(self.spider, exc.reason or 'cancelled'))
            return

        # Log the error
        # 记录错误
        logger.exception(self.logformatter.spider_error(exc, request, response, self.spider))

        # Send the spider_error signal
        # 发送spider_error信号
        await self.signals.send_catch_log(
            signal=signals.spider_error,
            failure=exc, response=response,
            spider=self.spider
        )

        # Update error statistics by exception type and total count
        # 按异常类型和总计数更新错误统计信息
        self.crawler.stats.inc_value("spider_exceptions/%s" % exc.__class__.__name__, spider=self.spider)
        self.crawler.stats.inc_value("spider_exceptions", spider=self.spider)

    async def handle_spider_output(self, result: Optional[AsyncGenerator], request: Request, response: Union[Response, BaseException]) -> None:
        """
        Process each Request/Item returned from the spider.
        处理从爬虫返回的每个Request/Item。

        This method iterates through the async generator returned by the spider
        callback and processes each yielded item. It handles any exceptions that
        occur during iteration and marks the request as successfully parsed or not.
        此方法遍历爬虫回调返回的异步生成器，并处理每个产生的项目。
        它处理迭代期间发生的任何异常，并将请求标记为成功解析或未成功解析。

        Args:
            result: The async generator returned by the spider callback, or None.
                   爬虫回调返回的异步生成器，或None。
                   If None, the method returns immediately.
                   如果为None，方法立即返回。
            request: The request that was processed.
                    已处理的请求。
            response: The response or exception that was processed.
                     已处理的响应或异常。
                     This can be either a Response object or an Exception object in case
                     the output came from an errback.
                     这可以是Response对象或Exception对象，以防输出来自errback。
        """
        if not result:
            return

        parse_ok = True
        while True:
            try:
                # Get the next item from the generator
                # 从生成器获取下一个项目
                output = await result.__anext__()
            except StopAsyncIteration:
                # End of generator
                # 生成器结束
                break
            except Exception as e:
                # Error during iteration
                # 迭代期间出错
                parse_ok = False
                await self.handle_spider_error(e, request, response)
            else:
                # Process the output item
                # 处理输出项目
                await self._process_spidermw_output(output, request, response)

        # Mark the request as successfully parsed (or not) for dupefilter
        # 将请求标记为成功解析（或未成功）以供重复过滤器使用
        self.spider.dupefilter and \
            not request.dont_filter and \
            setattr(request, "parse_ok", parse_ok)

    async def _process_spidermw_output(self, output: Any, request: Request, response: Union[Response, BaseException]) -> None:
        """
        Process each Request/Item returned from the spider.
        处理从爬虫返回的每个Request/Item。

        This method handles different types of output from the spider:
        此方法处理爬虫的不同类型的输出：

        - Request: Schedule it for crawling
          Request：安排它进行爬取
        - dict: Process it through the item pipeline
          dict：通过项目管道处理它
        - None: Ignore it
          None：忽略它
        - Other types: Log an error
          其他类型：记录错误

        Args:
            output: The output from the spider to process.
                   要处理的爬虫输出。
                   This can be a Request, a dict (item), None, or any other type.
                   这可以是Request、dict（项目）、None或任何其他类型。
            request: The original request that generated this output.
                    生成此输出的原始请求。
                    This is used for logging and tracking purposes.
                    这用于日志记录和跟踪目的。
            response: The response or exception that was processed.
                     已处理的响应或异常。
                     This can be either a Response object or an Exception object in case
                     the output came from an errback.
                     这可以是Response对象或Exception对象，以防输出来自errback。
        """
        if isinstance(output, Request):
            # Schedule new requests for crawling
            # 安排新请求进行爬取
            await self.crawler.engine.crawl(request=output)
        elif isinstance(output, dict):
            # Process items through the item pipeline
            # 通过项目管道处理项目
            self.slot.itemproc_size += 1
            try:
                # Process the item through the pipeline
                # 通过管道处理项目
                item = await self.itemproc.process_item(output, self.spider)
                # Call the spider's process_item method if it exists
                # 如果存在，调用爬虫的process_item方法
                if process_item_method := getattr(self.spider, 'process_item', None):
                    await call_helper(process_item_method, item)
            except Exception as e:
                # Handle exceptions during item processing
                # 处理项目处理期间的异常
                item = output
                output = e
            # Handle the processed item or exception
            # 处理已处理的项目或异常
            await self._itemproc_finished(output, item, response)
        elif output is None:
            # Ignore None outputs
            # 忽略None输出
            pass
        else:
            # Log an error for unexpected output types
            # 记录意外输出类型的错误
            typename = type(output).__name__
            logger.error(
                'Spider must return request, item, or None, got %(typename)r in %(request)s' % {'request': request,
                                                                                                'typename': typename},
            )

    async def _log_download_errors(
            self,
            spider_exception: BaseException,
            download_exception: BaseException,
            request: Request
    ) -> None:
        """
        Process and record download errors.
        处理和记录下载错误。

        This method logs download errors and re-raises spider exceptions
        if they are different from the download exception. It's typically called
        when an error occurs during the processing of an errback.
        此方法记录下载错误，如果爬虫异常与下载异常不同，则重新引发爬虫异常。
        它通常在处理errback期间发生错误时调用。

        Args:
            spider_exception: The exception raised during spider processing.
                             爬虫处理期间引发的异常。
                             This is the exception that occurred while processing
                             the download exception in the spider's errback.
                             这是在爬虫的errback中处理下载异常时发生的异常。
            download_exception: The exception raised during download.
                               下载期间引发的异常。
                               This is the original exception that occurred during
                               the download process.
                               这是下载过程中发生的原始异常。
            request: The request that caused the error.
                    导致错误的请求。
                    This is used for logging purposes and to provide context
                    about which request failed.
                    这用于日志记录目的，并提供有关哪个请求失败的上下文。

        Raises:
            BaseException: Re-raises spider_exception if it's different from download_exception.
                          如果spider_exception与download_exception不同，则重新引发spider_exception。
                          This ensures that new exceptions raised during errback processing
                          are properly propagated.
                          这确保在errback处理期间引发的新异常被正确传播。
        """
        # Log download errors (except IgnoreRequest which is not an error)
        # 记录下载错误（除了IgnoreRequest，它不是错误）
        if isinstance(download_exception, BaseException) and not isinstance(download_exception, IgnoreRequest):
            logger.exception(self.logformatter.download_error(download_exception, request, self.spider))

        # Re-raise spider exceptions if they're different from the download exception
        # 如果爬虫异常与下载异常不同，则重新引发爬虫异常
        if spider_exception is not download_exception:
            raise spider_exception

    async def _itemproc_finished(self, output: Any, item: Any, response: Response) -> None:
        """
        Handle the result of item processing.
        处理项目处理的结果。

        This method is called when the item pipeline has finished processing an item.
        It handles different outcomes based on the result:
        当项目管道完成处理项目时调用此方法。它根据结果处理不同的结果：

        - If output is a DropItem exception: Log it and send item_dropped signal
          如果输出是DropItem异常：记录它并发送item_dropped信号
        - If output is another exception: Log it and send item_error signal
          如果输出是另一个异常：记录它并发送item_error信号
        - If output is a valid item: Log it and send item_scraped signal
          如果输出是有效项目：记录它并发送item_scraped信号

        Args:
            output: The result of item processing (item or exception).
                   项目处理的结果（项目或异常）。
            item: The original item before processing.
                 处理前的原始项目。
            response: The response from which the item was extracted.
                     从中提取项目的响应。
        """
        # Decrease the item processing counter
        # 减少项目处理计数器
        self.slot.itemproc_size -= 1

        if isinstance(output, BaseException):
            if isinstance(output, DropItem):
                # Item was intentionally dropped by a pipeline
                # 项目被管道有意丢弃
                logger.log(**self.logformatter.dropped(item, output, response, self.spider))
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_dropped, item=item, response=response,
                    spider=self.spider, exception=output)
            else:
                # An error occurred during item processing
                # 项目处理期间发生错误
                logger.exception(self.logformatter.item_error(item, output, response, self.spider))
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_error, item=item, response=response,
                    spider=self.spider, failure=output)
        else:
            # Item was successfully processed
            # 项目已成功处理
            logger.log(**self.logformatter.scraped(output, response, self.spider))
            return await self.signals.send_catch_log_deferred(
                signal=signals.item_scraped, item=output, response=response,
                spider=self.spider)
