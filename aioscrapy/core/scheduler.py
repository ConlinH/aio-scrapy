"""
Scheduler Module
调度器模块

This module provides the scheduler components for AioScrapy. The scheduler is responsible
for managing the request queue, deciding which requests should be processed next, and
ensuring that requests are properly prioritized and deduplicated.
此模块为AioScrapy提供调度器组件。调度器负责管理请求队列，决定下一步应处理哪些请求，
并确保请求被正确地优先级排序和去重。

The main components are:
主要组件包括：

1. BaseSchedulerMeta: Metaclass that defines the required interface for schedulers
                     定义调度器所需接口的元类
2. BaseScheduler: Abstract base class that all schedulers must inherit from
                 所有调度器必须继承的抽象基类
3. Scheduler: Default implementation of the scheduler with support for persistent
             queues and in-memory caching
             支持持久化队列和内存缓存的默认调度器实现

Schedulers work with queue implementations to store and retrieve requests efficiently,
and can be configured to persist requests between runs or to use in-memory caching
for faster access.
调度器与队列实现一起工作，以高效地存储和检索请求，并且可以配置为在运行之间持久化请求
或使用内存缓存以便更快地访问。
"""
from abc import abstractmethod
from typing import Optional, Type, TypeVar, List

import aioscrapy
from aioscrapy.queue import AbsQueue
from aioscrapy.statscollectors import StatsCollector
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper
from aioscrapy.utils.log import logger


class BaseSchedulerMeta(type):
    """
    Metaclass to check scheduler classes against the necessary interface.
    用于检查调度器类是否实现了必要接口的元类。

    This metaclass ensures that any class claiming to be a scheduler
    implements all the required methods.
    此元类确保任何声称是调度器的类都实现了所有必需的方法。
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
        - has_pending_requests: Check if there are pending requests
        - enqueue_request: Add a request to the queue
        - enqueue_request_batch: Add multiple requests to the queue
        - next_request: Get the next request from the queue

        Args:
            subclass: The class to check.
                     要检查的类。

        Returns:
            bool: True if the class implements the required interface.
                 如果类实现了所需的接口，则为True。
        """
        return (
                hasattr(subclass, "has_pending_requests") and callable(subclass.has_pending_requests)
                and hasattr(subclass, "enqueue_request") and callable(subclass.enqueue_request)
                and hasattr(subclass, "enqueue_request_batch") and callable(subclass.enqueue_request_batch)
                and hasattr(subclass, "next_request") and callable(subclass.next_request)
        )


class BaseScheduler(metaclass=BaseSchedulerMeta):
    """
    Base class for schedulers.
    调度器的基类。

    This class defines the interface that all schedulers must implement.
    此类定义了所有调度器必须实现的接口。
    """

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.Crawler") -> "BaseScheduler":
        """
        Factory method to create a scheduler from a crawler.
        从爬虫创建调度器的工厂方法。

        This method receives the current crawler object and returns a new
        scheduler instance. In the base class, the crawler parameter is not used,
        but subclasses can override this method to use crawler settings or other
        attributes to configure the scheduler.
        此方法接收当前的爬虫对象并返回一个新的调度器实例。在基类中，crawler参数未被使用，
        但子类可以覆盖此方法以使用爬虫设置或其他属性来配置调度器。

        Args:
            crawler: The crawler instance that will use this scheduler.
                    将使用此调度器的爬虫实例。
                    This parameter is not used in the base implementation but is
                    provided for subclasses to use.
                    此参数在基本实现中未使用，但提供给子类使用。

        Returns:
            BaseScheduler: A new scheduler instance.
                          一个新的调度器实例。
        """
        # The crawler parameter is intentionally unused in the base implementation
        # 在基本实现中有意不使用crawler参数
        # pylint: disable=unused-argument
        return cls()

    async def close(self, reason: str) -> None:
        """
        Close the scheduler.
        关闭调度器。

        Called when the spider is closed by the engine. It receives the reason why the crawl
        finished as argument and it's useful to execute cleaning code. In the base class,
        this method does nothing, but subclasses can override it to perform cleanup operations.
        当爬虫被引擎关闭时调用。它接收爬取完成的原因作为参数，对于执行清理代码很有用。
        在基类中，此方法不执行任何操作，但子类可以覆盖它以执行清理操作。

        Args:
            reason: A string which describes the reason why the spider was closed.
                   描述爬虫关闭原因的字符串。
                   Common values include 'finished', 'cancelled', or 'shutdown'.
                   常见值包括'finished'（完成）、'cancelled'（取消）或'shutdown'（关闭）。
                   This parameter is not used in the base implementation but is
                   provided for subclasses to use.
                   此参数在基本实现中未使用，但提供给子类使用。
        """
        # The reason parameter is intentionally unused in the base implementation
        # 在基本实现中有意不使用reason参数
        # pylint: disable=unused-argument
        pass

    @abstractmethod
    async def has_pending_requests(self) -> bool:
        """
        Check if the scheduler has pending requests.
        检查调度器是否有待处理的请求。

        Returns:
            bool: True if the scheduler has enqueued requests, False otherwise.
                 如果调度器有排队的请求，则为True，否则为False。
        """
        raise NotImplementedError()

    @abstractmethod
    async def enqueue_request_batch(self, requests: List[aioscrapy.Request]) -> bool:
        """
        Process a batch of requests received by the engine.
        处理引擎接收到的一批请求。

        This method adds multiple requests to the scheduler's queue at once.
        此方法一次将多个请求添加到调度器的队列中。

        Args:
            requests: A list of requests to enqueue.
                     要排队的请求列表。

        Returns:
            bool: True if the requests are stored correctly, False otherwise.
                 如果请求正确存储，则为True，否则为False。

        Notes:
            If False is returned, the engine will fire a request_dropped signal,
            and will not make further attempts to schedule the requests at a later time.
            如果返回False，引擎将触发request_dropped信号，并且不会在稍后尝试调度请求。
        """
        raise NotImplementedError()

    @abstractmethod
    async def enqueue_request(self, request: aioscrapy.Request) -> bool:
        """
        Process a single request received by the engine.
        处理引擎接收到的单个请求。

        This method adds a request to the scheduler's queue.
        此方法将请求添加到调度器的队列中。

        Args:
            request: The request to enqueue.
                    要排队的请求。

        Returns:
            bool: True if the request is stored correctly, False otherwise.
                 如果请求正确存储，则为True，否则为False。

        Notes:
            If False is returned, the engine will fire a request_dropped signal,
            and will not make further attempts to schedule the request at a later time.
            如果返回False，引擎将触发request_dropped信号，并且不会在稍后尝试调度请求。
        """
        raise NotImplementedError()

    @abstractmethod
    async def next_request(self) -> Optional[aioscrapy.Request]:
        """
        Get the next request to be processed.
        获取要处理的下一个请求。

        This method returns the next request from the scheduler's queue,
        or None if there are no requests ready to be processed.
        此方法从调度器的队列中返回下一个请求，如果没有准备好处理的请求，则返回None。

        Returns:
            Optional[Request]: The next request to be processed, or None if there
                              are no requests ready at the moment.
                              要处理的下一个请求，如果当前没有准备好的请求，则为None。

        Notes:
            Returning None implies that no request from the scheduler will be sent
            to the downloader in the current cycle. The engine will continue
            calling next_request until has_pending_requests is False.
            返回None意味着在当前周期中不会将调度器中的请求发送到下载器。
            引擎将继续调用next_request，直到has_pending_requests为False。
        """
        raise NotImplementedError()


SchedulerTV = TypeVar("SchedulerTV", bound="Scheduler")


class Scheduler(BaseScheduler):
    """
    Default scheduler implementation.
    默认的调度器实现。

    This scheduler manages requests using a queue implementation and optionally
    a cache queue for faster access to requests.
    此调度器使用队列实现来管理请求，并可选择使用缓存队列以更快地访问请求。
    """

    def __init__(
            self,
            queue: AbsQueue,
            spider: aioscrapy.Spider,
            stats: Optional[StatsCollector] = None,
            persist: bool = True,
            cache_queue: Optional[AbsQueue] = None
    ):
        """
        Initialize the scheduler.
        初始化调度器。

        Args:
            queue: The main queue for storing requests.
                  存储请求的主队列。
            spider: The spider that will use this scheduler.
                   将使用此调度器的爬虫。
            stats: Optional stats collector for tracking metrics.
                  用于跟踪指标的可选统计收集器。
            persist: Whether to persist the queue between runs.
                    是否在运行之间持久化队列。
            cache_queue: Optional in-memory cache queue for faster access.
                        用于更快访问的可选内存缓存队列。
        """
        self.queue = queue  # Main queue (e.g., Redis queue)
                           # 主队列（例如，Redis队列）
        self.cache_queue = cache_queue  # Optional in-memory cache queue
                                       # 可选的内存缓存队列
        self.spider = spider
        self.stats = stats
        self.persist = persist  # Whether to persist the queue between runs
                               # 是否在运行之间持久化队列

    @classmethod
    async def from_crawler(cls: Type[SchedulerTV], crawler: "aioscrapy.Crawler") -> SchedulerTV:
        """
        Create a scheduler from a crawler.
        从爬虫创建调度器。

        This factory method creates a scheduler instance with the appropriate
        queue implementation and settings from the crawler.
        此工厂方法使用来自爬虫的适当队列实现和设置创建调度器实例。

        Args:
            crawler: The crawler instance that will use this scheduler.
                    将使用此调度器的爬虫实例。

        Returns:
            Scheduler: A new scheduler instance.
                      一个新的调度器实例。
        """
        # Initialize cache queue if enabled in settings
        # 如果在设置中启用，则初始化缓存队列
        cache_queue = None
        if crawler.settings.getbool('USE_SCHEDULER_QUEUE_CACHE', False):
            cache_queue = await load_instance('aioscrapy.queue.memory.SpiderPriorityQueue', spider=crawler.spider)

        # Create scheduler instance with the main queue and settings
        # 使用主队列和设置创建调度器实例
        instance = cls(
            await load_instance(crawler.settings['SCHEDULER_QUEUE_CLASS'], spider=crawler.spider),
            crawler.spider,
            stats=crawler.stats,
            persist=crawler.settings.getbool('SCHEDULER_PERSIST', True),
            cache_queue=cache_queue
        )

        # Flush the queue if requested in settings
        # 如果在设置中请求，则刷新队列
        if crawler.settings.getbool('SCHEDULER_FLUSH_ON_START', False):
            await instance.flush()

        # Log the number of pending requests if any
        # 如果有，记录待处理请求的数量
        count = await call_helper(instance.queue.len)
        count and logger.info("Resuming crawl (%d requests scheduled)" % count)

        return instance

    async def close(self, reason: str) -> None:
        """
        Close the scheduler.
        关闭调度器。

        This method is called when the spider is closed. It handles cleanup
        operations, including flushing the queue if persistence is disabled,
        or moving cached requests back to the main queue if persistence is enabled.
        当爬虫关闭时调用此方法。它处理清理操作，包括如果禁用持久性则刷新队列，
        或者如果启用持久性则将缓存的请求移回主队列。

        Args:
            reason: The reason why the spider was closed.
                   爬虫关闭的原因。
                   Common values include 'finished', 'cancelled', or 'shutdown'.
                   常见值包括'finished'（完成）、'cancelled'（取消）或'shutdown'（关闭）。
                   This parameter is not used in the current implementation but might
                   be used in future versions or subclasses to customize cleanup behavior.
                   此参数在当前实现中未使用，但可能在未来版本或子类中用于自定义清理行为。
        """
        # The reason parameter is not used in the current implementation
        # 当前实现中未使用reason参数
        # pylint: disable=unused-argument

        # If persistence is disabled, clear the queue
        # 如果禁用持久性，则清除队列
        if not self.persist:
            await self.flush()
            return

        # If persistence is enabled and we have a cache queue,
        # move all cached requests back to the main queue
        # 如果启用持久性并且我们有缓存队列，则将所有缓存的请求移回主队列
        if self.cache_queue is not None:
            # Process in batches of 2000 to avoid memory issues
            # 以2000个批次处理，以避免内存问题
            while True:
                temp = []
                async for request in self.cache_queue.pop(2000):
                    temp.append(request)
                # Push the batch to the main queue if not empty
                # 如果不为空，则将批次推送到主队列
                temp and await self.queue.push_batch(temp)
                # Break if we got less than a full batch (end of queue)
                # 如果我们得到的批次不足（队列结束），则中断
                if len(temp) < 2000:
                    break

    async def flush(self) -> None:
        """
        Clear the scheduler's queue.
        清除调度器的队列。

        This method removes all pending requests from the queue.
        此方法从队列中删除所有待处理的请求。
        """
        await call_helper(self.queue.clear)

    async def enqueue_request_batch(self, requests: List[aioscrapy.Request]) -> bool:
        """
        Add multiple requests to the queue at once.
        一次将多个请求添加到队列中。

        This method adds a batch of requests directly to the main queue
        and updates the stats if enabled.
        此方法将一批请求直接添加到主队列，并在启用时更新统计信息。

        Args:
            requests: A list of requests to enqueue.
                     要排队的请求列表。

        Returns:
            bool: Always returns True, indicating the requests were accepted.
                 始终返回True，表示请求被接受。
        """
        await call_helper(self.queue.push_batch, requests)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, count=len(requests), spider=self.spider)
        return True

    async def enqueue_request(self, request: aioscrapy.Request) -> bool:
        """
        Add a single request to the queue.
        将单个请求添加到队列中。

        If a cache queue is enabled (USE_SCHEDULER_QUEUE_CACHE), the request
        is added to the cache queue first for faster access. Otherwise, it's
        added directly to the main queue.
        如果启用了缓存队列(USE_SCHEDULER_QUEUE_CACHE)，则优先将请求添加到缓存队列中
        以便更快地访问。否则，它将直接添加到主队列中。

        Args:
            request: The request to enqueue.
                    要排队的请求。

        Returns:
            bool: Always returns True, indicating the request was accepted.
                 始终返回True，表示请求被接受。
        """
        if self.cache_queue is not None:
            await call_helper(self.cache_queue.push, request)
        else:
            await call_helper(self.queue.push, request)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, spider=self.spider)
        return True

    async def next_request(self, count: int = 1):
        """
        Get the next request(s) to be processed.
        获取要处理的下一个请求。

        This method is an async generator that yields requests from the queue.
        If a cache queue is enabled (USE_SCHEDULER_QUEUE_CACHE), it first tries
        to get requests from the cache queue, then falls back to the main queue.
        此方法是一个异步生成器，从队列中产生请求。
        如果启用了缓存队列(USE_SCHEDULER_QUEUE_CACHE)，它首先尝试从缓存队列中获取请求，
        然后回退到主队列。

        Note: This implementation differs from the BaseScheduler.next_request abstract
        method, which returns a single request or None. This implementation is an
        async generator that can yield multiple requests, making it more efficient
        for batch processing.
        注意：此实现与BaseScheduler.next_request抽象方法不同，后者返回单个请求或None。
        此实现是一个异步生成器，可以产生多个请求，使其更适合批处理。

        Args:
            count: Maximum number of requests to return.
                  要返回的最大请求数。
                  Defaults to 1.
                  默认为1。

        Yields:
            Request: The next request(s) to be processed.
                    要处理的下一个请求。
        """
        flag = False
        # First try to get requests from the cache queue if available
        # 如果可用，首先尝试从缓存队列获取请求
        if self.cache_queue is not None:
            async for request in self.cache_queue.pop(count):
                if request and self.stats:
                    self.stats.inc_value(self.queue.inc_key, spider=self.spider)
                yield request
                flag = True

        # If we got requests from the cache queue, we're done
        # 如果我们从缓存队列获取了请求，我们就完成了
        if flag:
            return

        # Otherwise, get requests from the main queue
        # 否则，从主队列获取请求
        async for request in self.queue.pop(count):
            if request and self.stats:
                self.stats.inc_value(self.queue.inc_key, spider=self.spider)
            yield request

    async def has_pending_requests(self) -> bool:
        """
        Check if the scheduler has pending requests.
        检查调度器是否有待处理的请求。

        This method checks both the main queue and the cache queue (if enabled)
        to determine if there are any pending requests.
        此方法检查主队列和缓存队列（如果启用）以确定是否有任何待处理的请求。

        Returns:
            bool: True if there are pending requests, False otherwise.
                 如果有待处理的请求，则为True，否则为False。
        """
        # If no cache queue, just check the main queue
        # 如果没有缓存队列，只检查主队列
        if self.cache_queue is None:
            return await call_helper(self.queue.len) > 0
        # Otherwise, check both queues
        # 否则，检查两个队列
        else:
            return (await call_helper(self.queue.len) + await call_helper(self.cache_queue.len)) > 0
