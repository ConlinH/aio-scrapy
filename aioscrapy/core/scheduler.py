import asyncio
from abc import abstractmethod
from typing import List, Optional, Type, TypeVar

import aioscrapy

from aioscrapy.queue import AbsQueue, QueueDelivery
from aioscrapy.statscollectors import StatsCollector
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper


class BaseSchedulerMeta(type):
    def __instancecheck__(cls, instance):
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        return all(
            hasattr(subclass, name) and callable(getattr(subclass, name))
            for name in (
                'has_pending_requests',
                'enqueue_request',
                'enqueue_request_batch',
                'next_request',
            )
        )


class BaseScheduler(metaclass=BaseSchedulerMeta):
    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.Crawler") -> "BaseScheduler":
        return cls()

    async def close(self, reason: str) -> None:
        pass

    @abstractmethod
    async def has_pending_requests(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def enqueue_request_batch(self, requests: List[aioscrapy.Request]) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def enqueue_request(self, request: aioscrapy.Request) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def next_request(self, count: int = 1):
        raise NotImplementedError

    async def complete_request(self, request: aioscrapy.Request) -> None:
        pass

    async def release_request(self, request: aioscrapy.Request) -> None:
        pass


SchedulerTV = TypeVar('SchedulerTV', bound='Scheduler')


class Scheduler(BaseScheduler):
    """Default scheduler with explicit reserve/ack/nack ownership."""

    def __init__(
            self,
            queue: AbsQueue,
            spider: aioscrapy.Spider,
            stats: Optional[StatsCollector] = None,
            persist: bool = True,
            visibility_timeout: float = 600,
            ack_batch_size: int = 100,
            ack_flush_interval: float = 1,
    ) -> None:
        self.queue = queue
        self.spider = spider
        self.stats = stats
        self.persist = persist
        self.visibility_timeout = visibility_timeout
        self.ack_batch_size = max(1, ack_batch_size)
        self.ack_flush_interval = max(0, ack_flush_interval)
        self._active = {}
        self._pending_acks: List[QueueDelivery] = []
        self._ack_flush_task = None
        self._ack_lock = asyncio.Lock()
        self._closing = False

    @property
    def requires_periodic_poll(self) -> bool:
        return getattr(self.queue, 'requires_periodic_poll', True)

    @classmethod
    async def from_crawler(cls: Type[SchedulerTV], crawler: "aioscrapy.Crawler") -> SchedulerTV:
        if crawler.settings.getbool('USE_SCHEDULER_QUEUE_CACHE', False):
            raise ValueError(
                'USE_SCHEDULER_QUEUE_CACHE is incompatible with reliable delivery; '
                'write requests directly to the configured scheduler queue'
            )
        queue = await load_instance(crawler.settings['SCHEDULER_QUEUE_CLASS'], spider=crawler.spider)
        instance = cls(
            queue,
            crawler.spider,
            stats=crawler.stats,
            persist=crawler.settings.getbool('SCHEDULER_PERSIST', True),
            visibility_timeout=crawler.settings.getfloat('SCHEDULER_VISIBILITY_TIMEOUT', 600),
            ack_batch_size=crawler.settings.getint('SCHEDULER_ACK_BATCH_SIZE', 100),
            ack_flush_interval=crawler.settings.getfloat('SCHEDULER_ACK_FLUSH_INTERVAL', 1),
        )
        if crawler.settings.getbool('SCHEDULER_FLUSH_ON_START', False):
            await instance.flush()
        count = await call_helper(instance.queue.len)
        if count:
            logger.info('Resuming crawl (%d requests scheduled)' % count)
        return instance

    async def close(self, reason: str) -> None:
        self._closing = True
        if self._ack_flush_task is not None and not self._ack_flush_task.done():
            self._ack_flush_task.cancel()
            await asyncio.gather(self._ack_flush_task, return_exceptions=True)
        await self.flush_acks()

        active = list(self._active.values())
        self._active.clear()
        if active:
            try:
                await self.queue.nack_batch(active)
            except Exception:
                logger.exception('Failed to return active queue deliveries during shutdown')

        if not self.persist:
            await self.flush()
        await self.queue.close()

    async def flush(self) -> None:
        await call_helper(self.queue.clear)

    async def enqueue_request_batch(self, requests: List[aioscrapy.Request]) -> bool:
        await call_helper(self.queue.push_batch, requests)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, count=len(requests), spider=self.spider)
        return True

    async def enqueue_request(self, request: aioscrapy.Request) -> bool:
        await call_helper(self.queue.push, request)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, spider=self.spider)
        return True

    async def next_request(self, count: int = 1):
        deliveries = await self.queue.reserve(count, self.visibility_timeout)
        for delivery in deliveries:
            request = delivery.request
            setattr(request, '_queue_redelivered', delivery.redelivered)
            setattr(request, '_queue_task_id', delivery.task_id)
            self._active[id(request)] = delivery
            if self.stats:
                self.stats.inc_value('scheduler/reserved', spider=self.spider)
                if delivery.redelivered:
                    self.stats.inc_value('scheduler/redelivered', spider=self.spider)
            yield request

    async def complete_request(self, request: aioscrapy.Request) -> None:
        delivery = self._active.pop(id(request), None)
        if delivery is None:
            return
        self._pending_acks.append(delivery)
        if len(self._pending_acks) >= self.ack_batch_size or self.ack_flush_interval == 0:
            await self.flush_acks()
        else:
            self._ensure_ack_flush()

    async def release_request(self, request: aioscrapy.Request) -> None:
        delivery = self._active.pop(id(request), None)
        if delivery is None:
            return
        try:
            acknowledged = await self.queue.nack(delivery)
        except Exception:
            logger.exception('Failed to return unfinished queue delivery')
            return
        if self.stats and acknowledged:
            self.stats.inc_value('scheduler/requeued', spider=self.spider)

    def _ensure_ack_flush(self) -> None:
        if self._closing:
            return
        if self._ack_flush_task is None or self._ack_flush_task.done():
            self._ack_flush_task = asyncio.create_task(
                self._flush_acks_after_delay(),
                name='%s:queue-ack-flush' % self.spider.name,
            )

    async def _flush_acks_after_delay(self) -> None:
        try:
            await asyncio.sleep(self.ack_flush_interval)
            await self.flush_acks()
        except asyncio.CancelledError:
            raise

    async def flush_acks(self) -> None:
        async with self._ack_lock:
            if not self._pending_acks:
                return
            deliveries = self._pending_acks
            self._pending_acks = []
            try:
                results = await self.queue.ack_batch(deliveries)
            except Exception:
                self._pending_acks = deliveries + self._pending_acks
                logger.exception('Failed to acknowledge queue deliveries')
                self._ensure_ack_flush()
                return

            if self.stats:
                for acknowledged in results:
                    self.stats.inc_value(
                        'scheduler/acked' if acknowledged else 'scheduler/stale',
                        spider=self.spider,
                    )

    async def has_pending_requests(self) -> bool:
        if self._active or self._pending_acks:
            return True
        return await call_helper(self.queue.len) > 0
