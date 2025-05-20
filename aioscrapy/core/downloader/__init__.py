"""
Downloader Module
下载器模块

This module provides the core downloader functionality for AioScrapy. The downloader
is responsible for fetching web pages and other resources from the internet, managing
concurrency, handling delays between requests, and processing the results through
middleware.
此模块为AioScrapy提供核心下载功能。下载器负责从互联网获取网页和其他资源，
管理并发，处理请求之间的延迟，并通过中间件处理结果。

The main components are:
主要组件包括：

1. BaseDownloader: Abstract base class defining the downloader interface
                  定义下载器接口的抽象基类
2. Downloader: Default implementation of the downloader
              下载器的默认实现
3. Slot: Class for managing per-domain or per-IP concurrency and delays
        用于管理每个域名或每个IP的并发和延迟的类

The downloader respects various settings like:
下载器遵循各种设置，如：

- CONCURRENT_REQUESTS: Global concurrency limit
                      全局并发限制
- CONCURRENT_REQUESTS_PER_DOMAIN: Per-domain concurrency limit
                                每个域名的并发限制
- CONCURRENT_REQUESTS_PER_IP: Per-IP concurrency limit
                            每个IP的并发限制
- DOWNLOAD_DELAY: Delay between requests
                 请求之间的延迟
- RANDOMIZE_DOWNLOAD_DELAY: Whether to randomize delays
                          是否随机化延迟
"""
import asyncio
import random
from abc import abstractmethod
from collections import deque
from datetime import datetime
from time import time
from typing import Optional, Set, Deque, Tuple, Callable, TypeVar

from aioscrapy import signals, Request, Spider
from aioscrapy.core.downloader.handlers import DownloadHandlerManager
from aioscrapy.dupefilters import DupeFilterBase
from aioscrapy.http import Response
from aioscrapy.middleware import DownloaderMiddlewareManager
from aioscrapy.proxy import AbsProxy
from aioscrapy.settings import Settings
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper, create_task


class BaseDownloaderMeta(type):
    """
    Metaclass for BaseDownloader that implements the virtual subclass pattern.
    BaseDownloader的元类，实现虚拟子类模式。

    This metaclass allows classes to be recognized as BaseDownloader subclasses
    if they implement the required interface, even if they don't explicitly inherit from it.
    该元类允许类被识别为BaseDownloader的子类，如果它们实现了所需的接口，即使它们没有显式地继承它。
    """

    def __instancecheck__(cls, instance):
        """
        Check if an instance is an instance of this class.
        检查实例是否是此类的实例。

        Args:
            instance: The instance to check.
                     要检查的实例。

        Returns:
            bool: True if the instance implements the required interface.
                 如果实例实现了所需的接口，则为True。
        """
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        """
        Check if a class is a subclass of this class.
        检查类是否是此类的子类。

        A class is considered a subclass if it implements the required methods:
        如果类实现了所需的方法，则被视为子类：
        - fetch: For downloading requests
        - needs_backout: For checking if the downloader is at capacity

        Args:
            subclass: The class to check.
                     要检查的类。

        Returns:
            bool: True if the class implements the required interface.
                 如果类实现了所需的接口，则为True。
        """
        return (
                hasattr(subclass, "fetch") and callable(subclass.fetch)
                and hasattr(subclass, "needs_backout") and callable(subclass.needs_backout)
        )


class BaseDownloader(metaclass=BaseDownloaderMeta):
    """
    Abstract base class for downloaders.
    下载器的抽象基类。

    This class defines the interface that all downloaders must implement.
    此类定义了所有下载器必须实现的接口。
    """

    @classmethod
    async def from_crawler(cls, crawler) -> "BaseDownloader":
        """
        Create a downloader instance from a crawler.
        从爬虫创建下载器实例。

        This is a factory method that creates a downloader instance from a crawler.
        In the base class, the crawler parameter is not used, but subclasses can
        override this method to use crawler settings or other attributes to
        configure the downloader.
        这是一个工厂方法，从爬虫创建下载器实例。在基类中，crawler参数未被使用，
        但子类可以覆盖此方法以使用爬虫设置或其他属性来配置下载器。

        Args:
            crawler: The crawler instance that will use this downloader.
                    将使用此下载器的爬虫实例。
                    This parameter is not used in the base implementation but is
                    provided for subclasses to use.
                    此参数在基本实现中未使用，但提供给子类使用。

        Returns:
            BaseDownloader: A new downloader instance.
                           一个新的下载器实例。
        """
        # The crawler parameter is intentionally unused in the base implementation
        # 在基本实现中有意不使用crawler参数
        return cls()

    async def close(self) -> None:
        """
        Close the downloader and release its resources.
        关闭下载器并释放其资源。

        This method is called when the spider is closed.
        当爬虫关闭时调用此方法。
        """
        pass

    @abstractmethod
    async def fetch(self, request: Request) -> None:
        """
        Fetch a request.
        获取请求。

        This method should download the given request and call the appropriate
        callback with the result.
        此方法应下载给定的请求并使用结果调用适当的回调。

        Args:
            request: The request to fetch.
                    要获取的请求。
        """
        raise NotImplementedError()

    @abstractmethod
    def needs_backout(self) -> bool:
        """
        Check if the downloader needs to back out (stop accepting new requests).
        检查下载器是否需要退出（停止接受新请求）。

        Returns:
            bool: True if the downloader is at capacity and should not accept
                 new requests, False otherwise.
                 如果下载器已达到容量并且不应接受新请求，则为True，否则为False。
        """
        raise NotImplementedError()


DownloaderTV = TypeVar("DownloaderTV", bound="Downloader")


class Slot:
    """
    Downloader slot for managing per-domain or per-IP concurrency and delays.
    用于管理每个域名或每个IP的并发和延迟的下载器槽。

    Each domain or IP has its own slot to control:
    每个域名或IP都有自己的槽来控制：
    - Concurrency: How many requests can be processed simultaneously
      并发：可以同时处理多少请求
    - Delay: How long to wait between requests
      延迟：请求之间等待多长时间
    """

    def __init__(self, concurrency: int, delay: float, randomize_delay: bool) -> None:
        """
        Initialize a new downloader slot.
        初始化一个新的下载器槽。

        Args:
            concurrency: Maximum number of concurrent requests for this slot.
                        此槽的最大并发请求数。
            delay: Minimum delay between requests in seconds.
                  请求之间的最小延迟（秒）。
            randomize_delay: Whether to randomize the delay between requests.
                           是否随机化请求之间的延迟。
        """
        self.concurrency = concurrency
        self.delay = delay
        self.randomize_delay = randomize_delay

        self.active: Set[Request] = set()  # All requests being processed by this slot
                                          # 此槽正在处理的所有请求
        self.transferring: Set[Request] = set()  # Requests being downloaded
                                               # 正在下载的请求
        self.queue: Deque[Request] = deque()  # Requests queued for download
                                             # 排队等待下载的请求
        self.lastseen: float = 0  # Timestamp of last request processed
                                 # 上次处理请求的时间戳
        self.delay_lock: bool = False  # Lock to prevent concurrent delay processing
                                      # 锁定以防止并发延迟处理

    def free_transfer_slots(self) -> int:
        """
        Calculate how many more requests can be processed concurrently.
        计算可以同时处理多少个更多的请求。

        Returns:
            int: Number of available transfer slots.
                可用传输槽的数量。
        """
        return self.concurrency - len(self.transferring)

    def download_delay(self) -> float:
        """
        Get the delay to use between requests.
        获取请求之间使用的延迟。

        If randomize_delay is True, the delay will be randomized between
        0.5 and 1.5 times the configured delay.
        如果randomize_delay为True，延迟将在配置的延迟的0.5到1.5倍之间随机化。

        Returns:
            float: The delay in seconds.
                  延迟（秒）。
        """
        if self.randomize_delay:
            return random.uniform(0.5 * self.delay, 1.5 * self.delay)
        return self.delay

    def __repr__(self) -> str:
        """
        Return a string representation of the slot for debugging.
        返回用于调试的槽的字符串表示。

        Returns:
            str: A string representation of the slot.
                槽的字符串表示。
        """
        cls_name = self.__class__.__name__
        return "%s(concurrency=%r, delay=%0.2f, randomize_delay=%r)" % (
            cls_name, self.concurrency, self.delay, self.randomize_delay)

    def __str__(self) -> str:
        """
        Return a detailed string representation of the slot.
        返回槽的详细字符串表示。

        Returns:
            str: A detailed string representation of the slot.
                槽的详细字符串表示。
        """
        return (
                "<downloader.Slot concurrency=%r delay=%0.2f randomize_delay=%r "
                "len(active)=%d len(queue)=%d len(transferring)=%d lastseen=%s>" % (
                    self.concurrency, self.delay, self.randomize_delay,
                    len(self.active), len(self.queue), len(self.transferring),
                    datetime.fromtimestamp(self.lastseen).isoformat()
                )
        )


def _get_concurrency_delay(concurrency: int, spider: Spider, settings: Settings) -> Tuple[int, float]:
    """
    Get the concurrency and delay settings for a spider.
    获取爬虫的并发和延迟设置。

    This function determines the appropriate concurrency and delay values
    by checking both the settings and spider attributes.
    此函数通过检查设置和爬虫属性来确定适当的并发和延迟值。

    Spider-specific settings take precedence over global settings.
    爬虫特定的设置优先于全局设置。

    Args:
        concurrency: Default concurrency value from settings.
                    来自设置的默认并发值。
        spider: The spider instance.
               爬虫实例。
        settings: The settings object.
                 设置对象。

    Returns:
        Tuple[int, float]: A tuple containing (concurrency, delay).
                          包含（并发，延迟）的元组。
    """
    # Get delay from settings, then override with spider attribute if available
    # 从设置获取延迟，然后如果可用，用爬虫属性覆盖
    delay = settings.getfloat('DOWNLOAD_DELAY')
    if hasattr(spider, 'download_delay'):
        delay = spider.download_delay

    # Get concurrency from settings, then override with spider attribute if available
    # 从设置获取并发，然后如果可用，用爬虫属性覆盖
    if hasattr(spider, 'max_concurrent_requests'):
        concurrency = spider.max_concurrent_requests

    return concurrency, delay


class Downloader(BaseDownloader):
    """
    Default implementation of the downloader.
    下载器的默认实现。

    This class handles downloading requests, managing concurrency and delays,
    and processing the results through middleware.
    此类处理下载请求、管理并发和延迟，并通过中间件处理结果。
    """

    DOWNLOAD_SLOT: str = 'download_slot'  # Meta key for custom download slot
                                         # 自定义下载槽的元键

    def __init__(
            self,
            crawler,
            handler: DownloadHandlerManager,
            middleware: DownloaderMiddlewareManager,
            *,
            proxy: Optional[AbsProxy] = None,
            dupefilter: Optional[DupeFilterBase] = None,
    ):
        """
        Initialize the downloader.
        初始化下载器。

        Args:
            crawler: The crawler instance that this downloader belongs to.
                    此下载器所属的爬虫实例。
            handler: The download handler manager.
                    下载处理程序管理器。
            middleware: The downloader middleware manager.
                       下载器中间件管理器。
            proxy: Optional proxy handler for managing proxies.
                  可选的代理处理程序，用于管理代理。
            dupefilter: Optional duplicate filter for avoiding duplicate requests.
                       可选的重复过滤器，用于避免重复请求。
        """
        # Components from crawler
        # 来自爬虫的组件
        self.settings: Settings = crawler.settings
        self.signals: SignalManager = crawler.signals
        self.spider: Spider = crawler.spider
        self.spider.proxy = proxy
        self._call_engine: Callable = crawler.engine.handle_downloader_output

        # External components
        # 外部组件
        self.middleware = middleware
        self.handler = handler
        self.proxy = proxy
        self.dupefilter = dupefilter

        # Concurrency and delay settings
        # 并发和延迟设置
        self.total_concurrency: int = self.settings.getint('CONCURRENT_REQUESTS')
        self.get_requests_count: int = self.settings.getint('GET_REQUESTS_COUNT') or self.total_concurrency
        self.domain_concurrency: int = self.settings.getint('CONCURRENT_REQUESTS_PER_DOMAIN')
        self.ip_concurrency: int = self.settings.getint('CONCURRENT_REQUESTS_PER_IP')
        self.randomize_delay: bool = self.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY')

        # State
        # 状态
        self.active: Set[Request] = set()  # All active requests
                                          # 所有活动请求
        self.slots: dict = {}  # Domain/IP -> Slot mapping
                              # 域名/IP -> 槽映射
        self.running: bool = True

        # Start slot garbage collector
        # 启动槽垃圾收集器
        create_task(self._slot_gc(60))

    @classmethod
    async def from_crawler(cls, crawler) -> "Downloader":
        """
        Create a downloader instance from a crawler.
        从爬虫创建下载器实例。

        This factory method creates and initializes a downloader with all the
        necessary components from the crawler.
        此工厂方法创建并初始化具有爬虫中所有必要组件的下载器。

        Args:
            crawler: The crawler instance that will use this downloader.
                    将使用此下载器的爬虫实例。

        Returns:
            Downloader: A new downloader instance.
                       一个新的下载器实例。
        """
        # Initialize dupefilter if configured
        # 如果已配置，则初始化重复过滤器
        df = crawler.settings.get('DUPEFILTER_CLASS') and await load_instance(crawler.settings['DUPEFILTER_CLASS'],
                                                                              crawler=crawler)
        # Bind dupefilter to spider for access in spider callbacks
        # 将重复过滤器绑定到爬虫，以便在爬虫回调中访问
        crawler.spider.dupefilter = df  # 将指纹绑定到Spider 在解析成功的时候 调用DUPEFILTER_CLASS的success方法

        # Initialize proxy handler if configured
        # 如果已配置，则初始化代理处理程序
        proxy_handler = crawler.settings.get("PROXY_HANDLER") and await load_instance(
            crawler.settings["PROXY_HANDLER"],
            crawler=crawler
        )

        return cls(
            crawler,
            await call_helper(DownloadHandlerManager.from_crawler, crawler),
            await call_helper(DownloaderMiddlewareManager.from_crawler, crawler),
            proxy=proxy_handler,
            dupefilter=df
        )

    async def fetch(self, request: Request) -> None:
        """
        Fetch a request.
        获取请求。

        This method adds the request to the appropriate download slot and
        starts processing the queue if possible.
        此方法将请求添加到适当的下载槽，并在可能的情况下开始处理队列。

        Args:
            request: The request to fetch.
                    要获取的请求。
        """
        # Add to global active requests set
        # 添加到全局活动请求集
        self.active.add(request)

        # Get the appropriate slot for this request
        # 获取此请求的适当槽
        key, slot = self._get_slot(request, self.spider)
        request.meta[self.DOWNLOAD_SLOT] = key

        # Add to slot's active and queue sets
        # 添加到槽的活动和队列集
        slot.active.add(request)
        slot.queue.append(request)

        # Start processing the queue
        # 开始处理队列
        await self._process_queue(slot)

    async def _process_queue(self, slot: Slot) -> None:
        """
        Process the request queue for a slot.
        处理槽的请求队列。

        This method handles the download delay between requests and starts
        downloading requests when slots are available.
        此方法处理请求之间的下载延迟，并在槽可用时开始下载请求。

        Args:
            slot: The slot whose queue should be processed.
                 应处理其队列的槽。
        """
        # If the slot is already waiting for a delay, don't process again
        # 如果槽已经在等待延迟，则不要再次处理
        if slot.delay_lock:
            return

        now = time()
        delay = slot.download_delay()

        # Handle download delay between requests
        # 处理请求之间的下载延迟
        if delay:
            penalty = delay - now + slot.lastseen
            if penalty > 0:
                # Need to wait before processing next request
                # 需要等待才能处理下一个请求
                slot.delay_lock = True
                await asyncio.sleep(penalty)
                slot.delay_lock = False
                # Schedule another processing after the delay
                # 延迟后安排另一次处理
                create_task(self._process_queue(slot))
                return

        # Process as many queued requests as possible
        # 尽可能多地处理排队的请求
        while slot.queue and slot.free_transfer_slots() > 0:
            request = slot.queue.popleft()
            slot.transferring.add(request)
            create_task(self._download(slot, request))
            # If there's a delay, only process one request at a time
            # 如果有延迟，一次只处理一个请求
            if delay:
                break

    async def _download(self, slot: Slot, request: Request) -> None:
        """
        Download a request and process the result.
        下载请求并处理结果。

        This method handles the entire download process including:
        此方法处理整个下载过程，包括：

        1. Duplicate filtering
           重复过滤
        2. Middleware processing
           中间件处理
        3. Actual downloading
           实际下载
        4. Proxy handling
           代理处理
        5. Response processing
           响应处理
        6. Exception handling
           异常处理
        7. Cleanup and callback
           清理和回调

        Args:
            slot: The slot that the request belongs to.
                 请求所属的槽。
            request: The request to download.
                    要下载的请求。
        """
        result = None
        try:
            # Check if request is a duplicate
            # 检查请求是否重复
            if self.dupefilter and not request.dont_filter and await self.dupefilter.request_seen(request):
                self.dupefilter.log(request, self.spider)
                return

            # Update last seen timestamp
            # 更新上次看到的时间戳
            slot.lastseen = time()

            # Process request through middleware
            # 通过中间件处理请求
            result = await self.middleware.process_request(self.spider, request)

            # If middleware didn't return a response, download the request
            # 如果中间件没有返回响应，则下载请求
            if result is None:
                # Add proxy if available
                # 如果可用，添加代理
                self.proxy and await self.proxy.add_proxy(request)
                result = await self.handler.download_request(request, self.spider)
        except BaseException as exc:
            # Handle exceptions
            # 处理异常
            self.proxy and self.proxy.check(request, exception=exc)
            result = await self.middleware.process_exception(self.spider, request, exc)
        else:
            # Process successful response
            # 处理成功的响应
            if isinstance(result, Response):
                try:
                    # Check proxy status with response
                    # 使用响应检查代理状态
                    self.proxy and self.proxy.check(request, response=result)
                    result = await self.middleware.process_response(self.spider, request, result)
                except BaseException as exc:
                    result = exc
        finally:
            # Cleanup: remove request from all tracking collections
            # 清理：从所有跟踪集合中删除请求
            slot.transferring.remove(request)
            slot.active.remove(request)
            self.active.remove(request)

            # Send signal if we got a response
            # 如果我们得到响应，发送信号
            if isinstance(result, Response):
                await self.signals.send_catch_log(signal=signals.response_downloaded,
                                                  response=result,
                                                  request=request,
                                                  spider=self.spider)

            # Update dupefilter with request status
            # 使用请求状态更新重复过滤器
            self.dupefilter and \
                not request.dont_filter and \
                await self.dupefilter.done(request, done_type="request_ok" if isinstance(result, Response) else "request_err")

            # Send result to engine and process next request
            # 将结果发送到引擎并处理下一个请求
            await self._call_engine(result, request)
            await self._process_queue(slot)

    async def close(self) -> None:
        """
        Close the downloader and release its resources.
        关闭下载器并释放其资源。

        This method stops the downloader from accepting new requests and
        closes the dupefilter if one is being used.
        此方法停止下载器接受新请求，并在使用重复过滤器时关闭它。
        """
        # Stop accepting new requests
        # 停止接受新请求
        self.running = False

        # Close the dupefilter if one exists
        # 如果存在重复过滤器，则关闭它
        self.dupefilter and await self.dupefilter.close()

    async def _slot_gc(self, age=60):
        """
        Garbage collector for download slots.
        下载槽的垃圾收集器。

        This method periodically checks for inactive slots and removes them
        to free up memory.
        此方法定期检查不活动的槽并删除它们以释放内存。

        Args:
            age: The minimum age in seconds for a slot to be considered for removal.
                 槽被考虑删除的最小年龄（秒）。
        """
        while self.running:
            # Wait for the specified age before checking
            # 在检查之前等待指定的年龄
            await asyncio.sleep(age)

            # Iterate through a copy of the slots to avoid modification during iteration
            # 遍历槽的副本以避免在迭代期间修改
            for key, slot in list(self.slots.items()):
                # Log slot state for debugging
                # 记录槽状态以进行调试
                logger.debug(slot)

                # Remove slots that have been inactive for at least 'age' seconds
                # 删除至少'age'秒不活动的槽
                if not slot.active and slot.lastseen + slot.delay < (time() - age):
                    self.slots.pop(key)

    def needs_backout(self) -> bool:
        """
        Check if the downloader needs to stop accepting new requests.
        检查下载器是否停止接受新请求。

        This method checks if the downloader has reached its maximum concurrency
        limit and should not accept new requests.
        此方法检查下载器是否已达到其最大并发限制，并且不应接受新请求。

        Returns:
            bool: True if the downloader is at capacity and should not accept
                 new requests, False otherwise.
                 如果下载器已达到容量并且不应接受新请求，则为True，否则为False。
        """
        return len(self.active) >= self.total_concurrency

    def _get_slot(self, request, spider):
        """
        Get or create a download slot for a request.
        获取或创建请求的下载槽。

        This method determines which slot a request should use based on its
        domain, IP, or custom slot key, and creates the slot if it doesn't exist.
        此方法根据请求的域名、IP或自定义槽键确定请求应使用哪个槽，如果槽不存在则创建它。

        Args:
            request: The request to get a slot for.
                    要获取槽的请求。
            spider: The spider making the request.
                   发出请求的爬虫。

        Returns:
            Tuple[str, Slot]: A tuple containing the slot key and the slot object.
                             包含槽键和槽对象的元组。
        """
        # Get the slot key for this request
        # 获取此请求的槽键
        key = self._get_slot_key(request, spider)

        # Create the slot if it doesn't exist
        # 如果槽不存在，则创建它
        if key not in self.slots:
            # Determine concurrency based on settings
            # 根据设置确定并发
            conc = self.ip_concurrency if self.ip_concurrency else self.domain_concurrency

            # Get spider-specific concurrency and delay
            # 获取爬虫特定的并发和延迟
            conc, delay = _get_concurrency_delay(conc, spider, self.settings)

            # Create a new slot with the determined settings
            # 使用确定的设置创建新槽
            self.slots[key] = Slot(conc, delay, self.randomize_delay)

        return key, self.slots[key]

    def _get_slot_key(self, request, spider):
        """
        Get the key for determining which download slot to use for a request.
        获取用于确定请求使用哪个下载槽的键。

        The slot key is determined in the following order:
        槽键按以下顺序确定：

        1. Custom slot from request.meta['download_slot'] if present
           如果存在，则从request.meta['download_slot']获取自定义槽
        2. Proxy address if IP concurrency is enabled
           如果启用了IP并发，则使用代理地址
        3. Request hostname
           请求主机名

        Args:
            request: The request to get a slot key for.
                    要获取槽键的请求。
            spider: The spider making the request (not used in this implementation
                   but kept for interface consistency).
                   发出请求的爬虫（在此实现中未使用，但保留以保持接口一致性）。
                   This parameter is included to maintain a consistent interface with
                   other methods that might need the spider instance, and to allow
                   subclasses to use it if needed.
                   包含此参数是为了保持与可能需要爬虫实例的其他方法的一致接口，
                   并允许子类在需要时使用它。

        Returns:
            str: The slot key for the request.
                请求的槽键。
        """
        # Check for custom slot in request meta
        # 检查请求元数据中的自定义槽
        if self.DOWNLOAD_SLOT in request.meta:
            return request.meta[self.DOWNLOAD_SLOT]

        # Use proxy as key if IP concurrency is enabled
        # 如果启用了IP并发，则使用代理作为键
        if self.ip_concurrency:
            return request.meta.get("proxy", '')
        # Otherwise use hostname
        # 否则使用主机名
        else:
            return urlparse_cached(request).hostname or ''
