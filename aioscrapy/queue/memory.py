from asyncio import LifoQueue, PriorityQueue, Queue
from asyncio.queues import QueueEmpty
from typing import List, Optional, Sequence
from uuid import uuid4

import aioscrapy

from aioscrapy.queue import AbsQueue, QueueDelivery
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


class MemoryQueueBase(AbsQueue):
    inc_key = 'scheduler/enqueued/memory'

    @property
    def requires_periodic_poll(self) -> bool:
        return False

    def __init__(
            self,
            container: Queue,
            spider: Optional[aioscrapy.Spider],
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None,
            max_size: int = 0,
    ) -> None:
        super().__init__(container, spider, key, serializer)
        self.max_size = max_size

    @classmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "MemoryQueueBase":
        max_size = spider.settings.getint("QUEUE_MAXSIZE", 0)
        queue_key = spider.settings.get("SCHEDULER_QUEUE_KEY", '%(spider)s:requests')
        serializer = load_object(
            spider.settings.get("SCHEDULER_SERIALIZER", "aioscrapy.serializer.PickleSerializer")
        )
        return cls(
            cls.get_queue(max_size),
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer,
            max_size=max_size,
        )

    async def len(self) -> int:
        return self.container.qsize()

    @staticmethod
    def get_queue(max_size: int) -> Queue:
        raise NotImplementedError

    def _make_entry(self, request, *, task_id=None, redelivered=False):
        return task_id or uuid4().hex, redelivered, self._encode_request(request)

    async def push(self, request) -> None:
        await self.container.put(self._make_entry(request))

    async def push_batch(self, requests) -> None:
        for request in requests:
            await self.push(request)

    def _pop_entry(self):
        return self.container.get_nowait()

    async def reserve(self, count: int = 1, visibility_timeout: float = 600) -> List[QueueDelivery]:
        deliveries = []
        for _ in range(max(0, count)):
            try:
                task_id, redelivered, data = self._pop_entry()
            except QueueEmpty:
                break
            token = uuid4().hex
            deliveries.append(QueueDelivery(
                request=await self._decode_request(data),
                task_id=task_id,
                token=token,
                receipt=(task_id, token, data),
                redelivered=redelivered,
            ))
        return deliveries

    async def ack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        return [True] * len(deliveries)

    async def nack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        for delivery in deliveries:
            _task_id, _token, data = delivery.receipt
            await self._put_requeued((delivery.task_id, True, data), delivery.score)
        return [True] * len(deliveries)

    async def _put_requeued(self, entry, score=0) -> None:
        await self.container.put(entry)

    async def clear(self) -> None:
        self.container = self.get_queue(self.max_size)


class MemoryFifoQueue(MemoryQueueBase):
    @staticmethod
    def get_queue(max_size: int) -> Queue:
        return Queue(max_size)


class MemoryLifoQueue(MemoryFifoQueue):
    @staticmethod
    def get_queue(max_size: int) -> LifoQueue:
        return LifoQueue(max_size)


class MemoryPriorityQueue(MemoryQueueBase):
    @staticmethod
    def get_queue(max_size: int) -> PriorityQueue:
        return PriorityQueue(max_size)

    async def push(self, request: aioscrapy.Request) -> None:
        task_id, redelivered, data = self._make_entry(request)
        await self.container.put((-request.priority, task_id, redelivered, data))

    def _pop_entry(self):
        score, task_id, redelivered, data = self.container.get_nowait()
        return task_id, redelivered, data, score

    async def reserve(self, count: int = 1, visibility_timeout: float = 600) -> List[QueueDelivery]:
        deliveries = []
        for _ in range(max(0, count)):
            try:
                task_id, redelivered, data, score = self._pop_entry()
            except QueueEmpty:
                break
            token = uuid4().hex
            deliveries.append(QueueDelivery(
                request=await self._decode_request(data),
                task_id=task_id,
                token=token,
                receipt=(task_id, token, data),
                redelivered=redelivered,
                score=score,
            ))
        return deliveries

    async def _put_requeued(self, entry, score=0) -> None:
        task_id, redelivered, data = entry
        await self.container.put((score, task_id, redelivered, data))


SpiderQueue = MemoryFifoQueue
SpiderStack = MemoryLifoQueue
SpiderPriorityQueue = MemoryPriorityQueue
