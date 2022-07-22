from abc import abstractmethod
from typing import Optional, Type, TypeVar

from aioscrapy import Spider
from aioscrapy.dupefilters import AbsDupeFilterBase
from aioscrapy.http.request import Request
from aioscrapy.queue import AbsQueue
from aioscrapy.statscollectors import StatsCollector
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper


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
                and hasattr(subclass, "next_request") and callable(subclass.next_request)
        )


class BaseScheduler(metaclass=BaseSchedulerMeta):

    @classmethod
    async def from_crawler(cls, crawler):
        """
        Factory method which receives the current :class:`~scrapy.crawler.Crawler` object as argument.
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
    async def enqueue_request(self, request: Request) -> bool:
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
    async def next_request(self) -> Optional[Request]:
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
            spider: Spider,
            df=Optional[AbsDupeFilterBase],
            stats=Optional[StatsCollector],
            persist: bool = True
    ):
        self.queue = queue
        self.spider = spider
        self.df = df
        self.stats = stats
        self.persist = persist

    @classmethod
    async def from_crawler(cls: Type[SchedulerTV], crawler) -> SchedulerTV:
        settings = crawler.settings
        instance = cls(
            await load_instance(settings['SCHEDULER_QUEUE_CLASS'], spider=crawler.spider),
            crawler.spider,
            df=settings.get('DUPEFILTER_CLASS') and await load_instance(settings['DUPEFILTER_CLASS'],
                                                                        spider=crawler.spider),
            stats=crawler.stats,
            persist=settings.getbool('SCHEDULER_PERSIST', True)
        )

        if settings.getbool('SCHEDULER_FLUSH_ON_START', False):
            await instance.flush()

        count = await call_helper(instance.queue.len)
        count and crawler.spider.log("Resuming crawl (%d requests scheduled)" % count)

        return instance

    async def close(self, reason: str) -> None:
        if not self.persist:
            await self.flush()
        self.df and await call_helper(self.df.close, reason)

    async def flush(self) -> None:
        self.df and await call_helper(self.df.clear)
        await call_helper(self.queue.clear)

    async def enqueue_request(self, request: Request) -> bool:
        if not request.dont_filter \
                and request.filter_mode == 'IN_QUEUE' \
                and self.df and await self.df.request_seen(request):
            self.df.log(request, self.spider)
            return False

        await call_helper(self.queue.push, request)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, spider=self.spider)
        return True

    async def next_request(self, count: int = 1) -> Optional[Request]:
        async for request in self.queue.pop(count):
            if request and not request.dont_filter \
                    and request.filter_mode == 'OUT_QUEUE' \
                    and self.df and await self.df.request_seen(request):
                self.df.log(request, self.spider)
                continue

            if request and self.stats:
                self.stats.inc_value(self.queue.inc_key, spider=self.spider)
            yield request

    async def has_pending_requests(self) -> bool:
        return await call_helper(self.queue.len) > 0
