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
    Metaclass to check scheduler classes against the necessary interface
    """

    def __instancecheck__(cls, instance):
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        return (
                hasattr(subclass, "has_pending_requests") and callable(subclass.has_pending_requests)
                and hasattr(subclass, "enqueue_request") and callable(subclass.enqueue_request)
                and hasattr(subclass, "enqueue_request_batch") and callable(subclass.enqueue_request_batch)
                and hasattr(subclass, "next_request") and callable(subclass.next_request)
        )


class BaseScheduler(metaclass=BaseSchedulerMeta):

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.Crawler") -> "BaseScheduler":
        """
        Factory method which receives the current :class:`~aioscrapy.crawler.Crawler` object as argument.
        """
        return cls()

    async def close(self, reason: str) -> None:
        """
        Called when the spider is closed by the engine. It receives the reason why the crawl
        finished as argument and it's useful to execute cleaning code.

        :param reason: a string which describes the reason why the spider was closed
        :type reason: :class:`str`
        """
        pass

    @abstractmethod
    async def has_pending_requests(self) -> bool:
        """
        ``True`` if the scheduler has enqueued requests, ``False`` otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    async def enqueue_request_batch(self, requests: List[aioscrapy.Request]) -> bool:
        """
        Process a batch requests received by the engine.

        Return ``True`` if the request is stored correctly, ``False`` otherwise.

        If ``False``, the engine will fire a ``request_dropped`` signal, and
        will not make further attempts to schedule the request at a later time.
        For reference, the default Scrapy scheduler returns ``False`` when the
        request is rejected by the dupefilter.
        """
        raise NotImplementedError()

    @abstractmethod
    async def enqueue_request(self, request: aioscrapy.Request) -> bool:
        """
        Process a request received by the engine.

        Return ``True`` if the request is stored correctly, ``False`` otherwise.

        If ``False``, the engine will fire a ``request_dropped`` signal, and
        will not make further attempts to schedule the request at a later time.
        For reference, the default Scrapy scheduler returns ``False`` when the
        request is rejected by the dupefilter.
        """
        raise NotImplementedError()

    @abstractmethod
    async def next_request(self) -> Optional[aioscrapy.Request]:
        """
        Return the next :class:`~scrapy.http.Request` to be processed, or ``None``
        to indicate that there are no requests to be considered ready at the moment.

        Returning ``None`` implies that no request from the scheduler will be sent
        to the downloader in the current reactor cycle. The engine will continue
        calling ``next_request`` until ``has_pending_requests`` is ``False``.
        """
        raise NotImplementedError()


SchedulerTV = TypeVar("SchedulerTV", bound="Scheduler")


class Scheduler(BaseScheduler):

    def __init__(
            self,
            queue: AbsQueue,
            spider: aioscrapy.Spider,
            stats=Optional[StatsCollector],
            persist: bool = True,
            cache_queue: Optional[AbsQueue] = None
    ):

        self.queue = queue
        self.cache_queue = cache_queue
        self.spider = spider
        self.stats = stats
        self.persist = persist

    @classmethod
    async def from_crawler(cls: Type[SchedulerTV], crawler: "aioscrapy.Crawler") -> SchedulerTV:
        cache_queue = None
        if crawler.settings.getbool('USE_SCHEDULER_QUEUE_CACHE', False):
            cache_queue = await load_instance('aioscrapy.queue.memory.SpiderPriorityQueue', spider=crawler.spider)
        instance = cls(
            await load_instance(crawler.settings['SCHEDULER_QUEUE_CLASS'], spider=crawler.spider),
            crawler.spider,
            stats=crawler.stats,
            persist=crawler.settings.getbool('SCHEDULER_PERSIST', True),
            cache_queue=cache_queue
        )

        if crawler.settings.getbool('SCHEDULER_FLUSH_ON_START', False):
            await instance.flush()

        count = await call_helper(instance.queue.len)
        count and logger.info("Resuming crawl (%d requests scheduled)" % count)

        return instance

    async def close(self, reason: str) -> None:

        if not self.persist:
            await self.flush()
            return

        # 如果持久化，将缓存中的任务放回到redis等分布式队列中
        if self.cache_queue is not None:
            while True:
                temp = []
                async for request in self.cache_queue.pop(2000):
                    temp.append(request)
                temp and await self.queue.push_batch(temp)
                if len(temp) < 2000:
                    break

    async def flush(self) -> None:
        await call_helper(self.queue.clear)

    async def enqueue_request_batch(self, requests: List[aioscrapy.Request]) -> bool:
        await call_helper(self.queue.push_batch, requests)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, count=len(requests), spider=self.spider)
        return True

    async def enqueue_request(self, request: aioscrapy.Request) -> bool:
        """
        如果启用了缓存队列(USE_SCHEDULER_QUEUE_CACHE)，则优先将任务放到缓存队列中
        """
        if self.cache_queue is not None:
            await call_helper(self.cache_queue.push, request)
        else:
            await call_helper(self.queue.push, request)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, spider=self.spider)
        return True

    async def next_request(self, count: int = 1) -> Optional[aioscrapy.Request]:
        """
        如果启用了缓存队列(USE_SCHEDULER_QUEUE_CACHE)，则优先从缓存队列中获取任务，然后从redis等分布式队列中获取任务
        """
        flag = False
        if self.cache_queue is not None:
            async for request in self.cache_queue.pop(count):
                if request and self.stats:
                    self.stats.inc_value(self.queue.inc_key, spider=self.spider)
                yield request
                flag = True

        if flag:
            return

        async for request in self.queue.pop(count):
            if request and self.stats:
                self.stats.inc_value(self.queue.inc_key, spider=self.spider)
            yield request

    async def has_pending_requests(self) -> bool:
        return await call_helper(self.queue.len) if self.cache_queue is None \
            else (await call_helper(self.queue.len) + await call_helper(self.cache_queue.len)) > 0
