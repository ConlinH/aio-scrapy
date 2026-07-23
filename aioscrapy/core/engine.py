# _*_ coding: utf-8 _*_
"""
Execution Engine Module
执行引擎模块

This module provides the core execution engine for AioScrapy, which coordinates
the crawling process. The engine manages the scheduling of requests, downloading
of pages, and processing of responses through the scraper.
此模块提供了AioScrapy的核心执行引擎，它协调爬取过程。引擎管理请求的调度、
页面的下载以及通过抓取器处理响应。

The main components are:
主要组件包括：

1. ExecutionEngine: Coordinates the entire crawling process
                   协调整个爬取过程
2. Slot: Holds spider running state and resources
        保存爬虫运行状态和资源

The engine is the central component that connects all other parts of the crawling
system: the scheduler, downloader, scraper, and spider.
引擎是连接爬取系统所有其他部分的中央组件：调度器、下载器、抓取器和爬虫。
"""

import asyncio
import time
from typing import Optional, AsyncGenerator, Union, Callable

import aioscrapy
from aioscrapy import Spider
from aioscrapy import signals
from aioscrapy.core.downloader import DownloaderTV
from aioscrapy.core.scheduler import BaseScheduler
from aioscrapy.core.scraper import Scraper
from aioscrapy.exceptions import DontCloseSpider
from aioscrapy.http import Response
from aioscrapy.http.request import Request
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper


class Slot:
    """
    A slot for holding spider running state and resources.
    用于保存爬虫运行状态和资源的槽。

    This class keeps track of in-progress requests and start requests
    for a spider.
    此类跟踪爬虫的进行中请求和起始请求。
    """

    def __init__(self, start_requests: Optional[AsyncGenerator]) -> None:
        """
        Initialize a new Slot.
        初始化一个新的Slot。

        Args:
            start_requests: An async generator that yields initial requests.
                           产生初始请求的异步生成器。
        """
        self.inprogress: set[Request] = set()  # requests in progress 进行中的请求
        self.start_requests = start_requests
        self.lock: bool = False  # lock for accessing start_requests 访问start_requests的锁

    def add_request(self, request: Request) -> None:
        """
        Add a request to the set of in-progress requests.
        将请求添加到进行中请求的集合中。

        Args:
            request: The request to add.
                    要添加的请求。
        """
        self.inprogress.add(request)

    def remove_request(self, request: Request) -> None:
        """
        Remove a request from the set of in-progress requests.
        从进行中请求的集合中移除请求。

        Args:
            request: The request to remove.
                    要移除的请求。
        """
        self.inprogress.remove(request)


class ExecutionEngine(object):
    """
    The execution engine coordinates the crawling process.
    执行引擎协调爬取过程。

    It manages the scheduling of requests, downloading of pages, and processing
    of responses through the scraper. The engine is the central component that
    connects all other parts of the crawling system.
    它管理请求的调度、页面的下载以及通过抓取器处理响应。引擎是连接爬取系统
    所有其他部分的中央组件。

    The engine's main responsibilities include:
    引擎的主要职责包括：

    1. Starting and stopping the crawling process
       启动和停止爬取过程
    2. Scheduling requests through the scheduler
       通过调度器调度请求
    3. Sending requests to the downloader
       将请求发送到下载器
    4. Passing responses to the scraper
       将响应传递给抓取器
    5. Handling spider idle state
       处理爬虫空闲状态

    The engine maintains a slot for each running spider, which keeps track of
    in-progress requests and start requests.
    引擎为每个运行的爬虫维护一个槽，该槽跟踪进行中的请求和起始请求。
    """

    def __init__(self, crawler: "aioscrapy.Crawler") -> None:
        """
        Initialize the execution engine.
        初始化执行引擎。

        Args:
            crawler: The crawler instance that this engine belongs to.
                    此引擎所属的爬虫实例。
        """
        self.crawler = crawler
        self.settings = crawler.settings
        self.signals = crawler.signals
        self.logformatter = crawler.logformatter

        # Components initialized during open()
        # 在open()期间初始化的组件
        self.slot: Optional[Slot] = None
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderTV] = None
        self.scraper: Optional[Scraper] = None
        self.scheduler: Optional[BaseScheduler] = None

        # Engine state
        # 引擎状态
        self.running: bool = False  # True when engine is running
        self.unlock: bool = True    # Lock for scheduler access
        self.finish: bool = False   # True when engine is completely finished
        self._stop_lock = asyncio.Lock()
        self._engine_stopped_sent: bool = False
        # Wake the scheduler loop when local work or lifecycle state changes
        # 本地工作或生命周期状态变化时唤醒调度循环
        self._wakeup_event = asyncio.Event()

    async def start(
            self,
            spider: Spider,
            start_requests: Optional[AsyncGenerator] = None
    ) -> None:
        """
        Start the execution engine.
        启动执行引擎。

        This method initializes the engine components, opens the spider,
        and starts the main crawling loop.
        此方法初始化引擎组件，打开爬虫，并启动主爬取循环。

        Args:
            spider: The spider instance to run.
                   要运行的爬虫实例。
            start_requests: Optional async generator of initial requests.
                           初始请求的可选异步生成器。

        Raises:
            RuntimeError: If the engine is already running.
                         如果引擎已经在运行。
        """
        if self.running:
            raise RuntimeError("Engine already running")

        self.running = True
        await self.signals.send_catch_log_deferred(signal=signals.engine_started)
        await self.open(spider, start_requests)

        # Process local notifications immediately and only poll external queues
        # 本地通知立即处理，仅对外部队列保留周期轮询
        while not self.finish:
            # Clear before processing so notifications raised during this cycle remain visible
            # 在处理前清除事件，确保本轮产生的通知不会丢失
            self._wakeup_event.clear()
            self.running and await self._next_request()
            if self.running and self.spider is not None:
                await self._spider_idle(self.spider)
            if not self.finish:
                await self._wait_for_wakeup()

    async def stop(self, reason: str = 'shutdown') -> None:
        """
        Stop the execution engine gracefully.
        优雅地停止执行引擎。

        This method stops the engine, waits for all pending requests to complete,
        closes the spider, and sends the engine_stopped signal.
        此方法停止引擎，等待所有待处理的请求完成，关闭爬虫，并发送engine_stopped信号。

        Args:
            reason: The reason for stopping the engine.
                   停止引擎的原因。

        Raises:
            RuntimeError: If the engine is not running.
                         如果引擎没有运行。
        """
        async with self._stop_lock:
            if self.finish:
                return

            self.running = False
            self.wakeup()

            # A partially initialized engine has nothing active to drain, but its
            # already-created components still need to be closed.
            # 部分初始化的引擎无需等待活动任务，但仍需关闭已创建的组件。
            if all((self.slot, self.downloader, self.scraper)):
                timeout = self._get_shutdown_timeout()
                try:
                    if timeout > 0:
                        await asyncio.wait_for(self._wait_until_idle(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(
                        f'Graceful shutdown timed out after {timeout} seconds; '
                        'cancelling remaining tasks'
                    )

            await self.close_spider(self.spider, reason=reason)
            if not self._engine_stopped_sent:
                await self.signals.send_catch_log_deferred(signal=signals.engine_stopped)
                self._engine_stopped_sent = True
            self.finish = True
            self.wakeup()

    def wakeup(self) -> None:
        """
        Notify the engine that scheduling or lifecycle state has changed.
        通知引擎调度状态或生命周期状态已经变化。
        """
        self._wakeup_event.set()

    def _get_scheduler_poll_interval(self) -> Optional[float]:
        """
        Return the fallback polling interval required by the current scheduler.
        返回当前调度器所需的兜底轮询间隔。

        In-memory queues rely entirely on local notifications. External and unknown
        queues keep polling so requests inserted by other processes are discovered.
        内存队列完全依赖本地通知；外部及未知队列保留轮询，以发现其他进程写入的请求。
        """
        if self.scheduler is not None and not getattr(self.scheduler, 'requires_periodic_poll', True):
            return None

        if hasattr(self.settings, 'getfloat'):
            interval = self.settings.getfloat('SCHEDULER_POLL_INTERVAL', 1.0)
        else:
            interval = float(self.settings.get('SCHEDULER_POLL_INTERVAL', 1.0))
        return interval if interval > 0 else None

    def _get_wakeup_timeout(self) -> Optional[float]:
        """
        Return the next timed wakeup for pause expiry or external queue polling.
        返回暂停到期或外部队列轮询所需的下一次定时唤醒时间。
        """
        if self.spider is not None and self.spider.pause:
            pause_time = self.spider.pause_time
            if pause_time == float('inf'):
                return None
            return max(0.0, pause_time - time.time())
        return self._get_scheduler_poll_interval()

    async def _wait_for_wakeup(self) -> None:
        """
        Wait for a local notification or the configured external queue poll tick.
        等待本地通知或配置的外部队列轮询时钟。
        """
        timeout = self._get_wakeup_timeout()
        if timeout is None:
            await self._wakeup_event.wait()
            return

        try:
            await asyncio.wait_for(self._wakeup_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # Timeout is the expected fallback for externally populated queues
            # 超时是外部生产者队列的预期兜底唤醒方式
            pass

    async def _wait_until_idle(self) -> None:
        """
        Wait until all engine components become idle.
        等待引擎所有组件进入空闲状态。
        """
        while not self.is_idle():
            await asyncio.sleep(0.2)

    def _get_shutdown_timeout(self) -> float:
        """
        Return the configured graceful shutdown timeout in seconds.
        返回配置的优雅关闭超时时间，单位为秒。
        """
        if hasattr(self.settings, 'getfloat'):
            return self.settings.getfloat('GRACEFUL_SHUTDOWN_TIMEOUT', 30.0)
        return float(self.settings.get('GRACEFUL_SHUTDOWN_TIMEOUT', 30.0))

    async def open(
            self,
            spider: Spider,
            start_requests: Optional[AsyncGenerator] = None
    ) -> None:
        """
        Open a spider for crawling.
        打开爬虫进行爬取。

        This method initializes all the components needed for crawling:
        scheduler, downloader, scraper, and slot. It also sends the spider_opened signal.
        此方法初始化爬取所需的所有组件：调度器、下载器、抓取器和槽。它还发送spider_opened信号。

        Args:
            spider: The spider instance to open.
                   要打开的爬虫实例。
            start_requests: Optional async generator of initial requests.
                           初始请求的可选异步生成器。
        """
        logger.info("Spider opened")

        self.spider = spider
        await call_helper(self.crawler.stats.open_spider, spider)

        # Initialize components
        # 初始化组件
        self.scheduler = await load_instance(self.settings['SCHEDULER'], crawler=self.crawler)
        self.downloader = await load_instance(self.settings['DOWNLOADER'], crawler=self.crawler)
        self.scraper = await call_helper(Scraper.from_crawler, self.crawler)

        # Process start requests through spider middleware
        # 通过爬虫中间件处理起始请求
        start_requests = await call_helper(self.scraper.spidermw.process_start_requests, start_requests, spider)
        self.slot = Slot(start_requests)

        await self.signals.send_catch_log_deferred(signals.spider_opened, spider=spider)

    async def close(self) -> None:
        """
        Close the execution engine gracefully.
        优雅地关闭执行引擎。

        If it has already been started, stop it. In all cases, close all spiders
        and the downloader.
        如果它已经启动，则停止它。在所有情况下，关闭所有爬虫和下载器。

        This method is the main entry point for shutting down the engine from
        outside the engine itself.
        此方法是从引擎外部关闭引擎的主要入口点。
        """
        await self.stop(reason='shutdown')

    async def _next_request(self) -> None:
        """
        Process the next request from the scheduler or start requests.
        处理来自调度器或起始请求的下一个请求。

        This method is the core of the crawling process. It handles:
        此方法是爬取过程的核心。它处理：

        1. Spider pause/resume logic
           爬虫暂停/恢复逻辑
        2. Getting requests from the scheduler and sending them to the downloader
           从调度器获取请求并将其发送到下载器
        3. Processing start requests
           处理起始请求
        """
        if self.slot is None or self.spider is None:
            return

        # Handle spider pause/resume logic
        # 处理爬虫暂停/恢复逻辑
        if self.spider.pause:
            now = int(time.time())
            last_log_time = getattr(self.spider, "last_log_time", None)
            if last_log_time is None or (now - last_log_time) >= 5:
                setattr(self.spider, "last_log_time", now)
                logger.info(f"The spider has been suspended, and will resume in "
                            f"{self.spider.pause_time - now} seconds")
            if self.spider.pause_time and self.spider.pause_time <= now:
                self.spider.pause = False
            return

        # Get requests from scheduler and send them to downloader
        # 从调度器获取请求并将其发送到下载器
        while self.unlock and not self._needs_backout() and self.unlock:
            self.unlock = False
            try:
                async for request in self.scheduler.next_request(self.downloader.get_requests_count):
                    if request:
                        self.slot.add_request(request)
                        try:
                            await self.downloader.fetch(request)
                        except BaseException:
                            self.slot.remove_request(request)
                            await self._release_scheduler_request(request)
                            raise
                break
            finally:
                self.unlock = True

        # Process start requests if available
        # 如果可用，处理起始请求
        if self.slot.start_requests and not self._needs_backout() and not self.slot.lock:
            self.slot.lock = True
            try:
                # Get the next request from start_requests
                # 从start_requests获取下一个请求
                request = await self.slot.start_requests.__anext__()
            except StopAsyncIteration:
                # No more start requests, set to None
                # 没有更多的起始请求，设置为None
                self.slot.start_requests = None
            except Exception as exc:
                # Log any errors and stop processing start requests
                # 记录任何错误并停止处理起始请求
                self.slot.start_requests = None
                logger.exception('Error while obtaining start requests: %s', str(exc))
            else:
                # If we got a request, schedule it for crawling
                # 如果我们得到了请求，安排它进行爬取
                request and await self.crawl(request)
            finally:
                # Always release the lock
                # 始终释放锁
                self.slot.lock = False

    def _needs_backout(self) -> bool:
        """
        Check if the engine should temporarily stop processing more requests.
        检查引擎是否应该暂时停止处理更多请求。

        This method determines if the request processing loop should pause by checking:
        此方法通过检查以下条件来确定请求处理循环是否应该暂停：

        1. If the engine is no longer running (self.running is False)
           引擎是否不再运行（self.running为False）
        2. If the downloader is at capacity or needs to pause
           下载器是否已达到容量或需要暂停
        3. If the scraper is at capacity or needs to pause
           抓取器是否已达到容量或需要暂停

        This is used to implement flow control in the request processing pipeline.
        这用于在请求处理管道中实现流量控制。

        Returns:
            True if request processing should pause, False if it can continue.
            如果请求处理应该暂停，则返回True；如果可以继续，则返回False。
        """
        return (
                not self.running
                or self.downloader.needs_backout()
                or self.scraper.needs_backout()
        )

    async def handle_downloader_output(
            self, result: Union[Request, Response, BaseException, None], request: Request
    ) -> None:
        """
        Handle the output from the downloader.
        处理下载器的输出。

        This method processes the result of a download, which can be:
        此方法处理下载的结果，可以是：

        - None: Download was cancelled or failed without an exception
          None：下载被取消或失败，没有异常
        - Request: A new request to crawl
          Request：要爬取的新请求
        - Response: A successful response
          Response：成功的响应
        - BaseException: An exception that occurred during download
          BaseException：下载过程中发生的异常

        Args:
            result: The result of the download.
                   下载的结果。
            request: The original request that was downloaded.
                    被下载的原始请求。

        Raises:
            TypeError: If the result is not None, Request, Response, or BaseException.
                      如果结果不是None、Request、Response或BaseException。
        """
        completed = False
        try:
            if result is None:
                completed = True
                return

            if not isinstance(result, (Request, Response, BaseException)):
                raise TypeError(
                    "Incorrect type: expected Request, Response or Failure, got %s: %r"
                    % (type(result), result)
                )

            if isinstance(result, Request):
                # Schedule new request
                # 调度新请求
                await self.crawl(result)
                completed = True
                return

            # Set the original request on the result
            # 在结果上设置原始请求
            result.request = request

            if isinstance(result, Response):
                # Log successful response and send signal
                # 记录成功的响应并发送信号
                logger.log(**self.logformatter.crawled(request, result, self.spider))
                await self.signals.send_catch_log(signals.response_received,
                                                  response=result, request=request, spider=self.spider)

            # Send result to scraper for processing
            # 将结果发送到抓取器进行处理
            await self.scraper.enqueue_scrape(result, request)
            completed = True

        finally:
            try:
                if completed:
                    await self._complete_scheduler_request(request)
                else:
                    await self._release_scheduler_request(request)
            finally:
                # Always remove the request and notify the central scheduler loop
                # 始终移除进行中的请求并通知中央调度循环
                self.slot.remove_request(request)
                self.wakeup()

    async def handle_downloader_cancelled(self, request: Request) -> None:
        """Return a reserved request that was cancelled before completion."""
        try:
            await self._release_scheduler_request(request)
        finally:
            if self.slot is not None and request in self.slot.inprogress:
                self.slot.remove_request(request)
            self.wakeup()

    async def _complete_scheduler_request(self, request: Request) -> None:
        callback = getattr(self.scheduler, 'complete_request', None)
        if callback is not None:
            await callback(request)

    async def _release_scheduler_request(self, request: Request) -> None:
        callback = getattr(self.scheduler, 'release_request', None)
        if callback is not None:
            await callback(request)

    def is_idle(self) -> bool:
        """
        Check if the engine is idle.
        检查引擎是否空闲。

        The engine is considered idle when:
        在以下情况下，引擎被认为是空闲的：

        1. The downloader has no active requests
           下载器没有活动的请求
        2. There are no requests in progress
           没有正在进行的请求
        3. The scraper is idle
           抓取器是空闲的

        Returns:
            True if the engine is idle, False otherwise.
            如果引擎空闲，则为True，否则为False。
        """
        if self.downloader is not None and self.downloader.active:
            # downloader has pending requests
            # 下载器有待处理的请求
            return False

        if self.slot is not None and self.slot.inprogress:
            # not all start requests are handled
            # 不是所有的起始请求都已处理
            return False

        if self.scraper is not None and not self.scraper.is_idle():
            # scraper is not idle
            # 抓取器不是空闲的
            return False

        return True

    async def crawl(self, request: Request) -> None:
        """
        Schedule a request for crawling.
        调度请求进行爬取。

        This method adds the request to the scheduler's queue.
        此方法将请求添加到调度器的队列中。

        Args:
            request: The request to schedule.
                    要调度的请求。
        """
        accepted = await self.scheduler.enqueue_request(request)
        if accepted:
            self.wakeup()

    async def close_spider(self, spider: Optional[Spider], reason: str = 'cancelled') -> None:
        """
        Close (cancel) spider and clear all its outstanding requests.
        关闭（取消）爬虫并清除其所有未完成的请求。

        This method gracefully shuts down all components related to the spider:
        此方法优雅地关闭与爬虫相关的所有组件：

        1. Downloader
           下载器
        2. Scraper
           抓取器
        3. Scheduler
           调度器
        4. Stats collector
           统计收集器
        5. Sends the spider_closed signal
           发送spider_closed信号

        Args:
            spider: The spider to close.
                   要关闭的爬虫。
            reason: The reason for closing the spider.
                   关闭爬虫的原因。
        """
        logger.info(f"Closing spider ({reason})")
        shutdown_timeout = self._get_shutdown_timeout()

        # Helper function to handle exceptions during close operations
        # 处理关闭操作期间异常的辅助函数
        async def close_handler(
                callback: Callable,
                *args,
                errmsg: str = '',  # Error message to log if an exception occurs
                                  # 如果发生异常时记录的错误消息
                **kwargs
        ) -> None:
            """
            Call a callback and log any exceptions that occur.
            调用回调并记录发生的任何异常。

            This is an internal helper function used during the spider closing process
            to ensure that exceptions in one closing operation don't prevent other
            closing operations from being attempted. It wraps each callback in a
            try-except block and logs any exceptions with the provided error message.
            这是在爬虫关闭过程中使用的内部辅助函数，用于确保一个关闭操作中的异常
            不会阻止尝试其他关闭操作。它将每个回调包装在try-except块中，并使用
            提供的错误消息记录任何异常。

            Args:
                callback: The callback function to call.
                         要调用的回调函数。
                *args: Positional arguments to pass to the callback.
                      传递给回调的位置参数。
                errmsg: Error message prefix to log if an exception occurs.
                       如果发生异常时记录的错误消息前缀。
                       This will be prepended to the exception string in the log.
                       这将在日志中添加到异常字符串之前。
                **kwargs: Keyword arguments to pass to the callback.
                         传递给回调的关键字参数。

            Note:
                Cancellation is propagated. Regular failures and close timeouts are
                logged so the remaining components still get a chance to close.
                取消异常会继续传播；普通异常和关闭超时会被记录，以便其余组件继续关闭。
            """
            try:
                # Apply the shutdown timeout independently to each close operation
                # 为每个关闭操作单独应用关闭超时
                operation = call_helper(callback, *args, **kwargs)
                if shutdown_timeout > 0:
                    await asyncio.wait_for(operation, timeout=shutdown_timeout)
                else:
                    await operation
            except asyncio.TimeoutError:
                logger.error(f"{errmsg}: timed out after {shutdown_timeout} seconds")
            except Exception as exc:
                # Log the error message along with the exception details
                # 记录错误消息以及异常详细信息
                logger.exception(f"{errmsg}: {str(exc)}")

        # Close all components in sequence
        # 按顺序关闭所有组件
        if self.downloader is not None:
            await close_handler(self.downloader.close, errmsg='Downloader close failure')

        if self.scraper is not None:
            await close_handler(self.scraper.close, errmsg='Scraper close failure')

        if self.scheduler is not None:
            await close_handler(self.scheduler.close, reason, errmsg='Scheduler close failure')

        if spider is not None:
            await close_handler(self.signals.send_catch_log_deferred, signal=signals.spider_closed, spider=spider,
                                reason=reason, errmsg='Error while sending spider_close signal')

            if self.crawler.stats is not None:
                await close_handler(self.crawler.stats.close_spider, spider, reason=reason,
                                    errmsg='Stats close failure')

        logger.info(f"Spider closed ({reason})")

        # Clean up references
        # 清理引用
        await close_handler(setattr, self, 'slot', None, errmsg='Error while unassigning slot')

        await close_handler(setattr, self, 'spider', None, errmsg='Error while unassigning spider')

    async def _spider_idle(self, spider: Spider) -> None:
        """
        Handle the spider_idle signal.
        处理spider_idle信号。

        This method is called when the spider becomes idle (no more requests to process).
        当爬虫变为空闲状态（没有更多请求要处理）时，调用此方法。

        It sends the spider_idle signal, which handlers can use to add more requests.
        它发送spider_idle信号，处理程序可以使用该信号添加更多请求。

        If no handler raises DontCloseSpider and there are no pending requests,
        the spider is stopped.
        如果没有处理程序引发DontCloseSpider且没有待处理的请求，则停止爬虫。

        Args:
            spider: The idle spider.
                   空闲的爬虫。
        """
        if self.spider is None or self.slot is None or self.scheduler is None:
            return

        if self.spider.pause:
            return

        # Send spider_idle signal and check if any handler wants to keep the spider open
        # 发送spider_idle信号并检查是否有任何处理程序希望保持爬虫打开
        res = await self.signals.send_catch_log(signals.spider_idle, spider=spider, dont_log=DontCloseSpider)
        if any(isinstance(x, DontCloseSpider) for _, x in res):
            return

        # method of 'has_pending_requests' has IO, so method of 'is_idle' execute twice
        # 'has_pending_requests'方法有IO操作，所以'is_idle'方法执行两次
        if self.is_idle() \
                and self.slot.start_requests is None \
                and not await self.scheduler.has_pending_requests() \
                and self.is_idle():
            await self.stop(reason='finished')
