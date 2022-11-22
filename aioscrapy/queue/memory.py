from asyncio import PriorityQueue, Queue, LifoQueue
from asyncio.queues import QueueEmpty
from typing import Optional

import aioscrapy
from aioscrapy.queue import AbsQueue
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


class MemoryQueueBase(AbsQueue):
    inc_key = 'scheduler/enqueued/memory'

    def __init__(
            self,
            container: Queue,
            spider: Optional[aioscrapy.Spider],
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None,
            max_size: int = 0
    ) -> None:
        super().__init__(container, spider, key, serializer)
        self.max_size = max_size

    @classmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "MemoryQueueBase":
        max_size: int = spider.settings.getint("QUEUE_MAXSIZE", 0)
        queue: Queue = cls.get_queue(max_size)
        queue_key: str = spider.settings.get("SCHEDULER_QUEUE_KEY", '%(spider)s:requests')
        serializer: str = spider.settings.get("SCHEDULER_SERIALIZER", "aioscrapy.serializer.PickleSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            queue,
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer
        )

    def len(self) -> int:
        """Return the length of the queue"""
        return self.container.qsize()

    @staticmethod
    def get_queue(max_size: int) -> Queue:
        raise NotImplementedError

    async def push(self, request) -> None:
        data = self._encode_request(request)
        await self.container.put(data)

    async def push_batch(self, requests) -> None:
        for request in requests:
            await self.push(request)

    async def pop(self, count: int = 1) -> None:
        for _ in range(count):
            try:
                data = self.container.get_nowait()
            except QueueEmpty:
                break
            yield self._decode_request(data)

    async def clear(self, timeout: int = 0) -> None:
        self.container = self.get_queue(self.max_size)


class MemoryFifoQueue(MemoryQueueBase):

    @staticmethod
    def get_queue(max_size: int) -> Queue:
        return Queue(max_size)


class MemoryLifoQueue(MemoryFifoQueue):
    @staticmethod
    def get_queue(max_size: int) -> LifoQueue:
        return LifoQueue(max_size)


class MemoryPriorityQueue(MemoryFifoQueue):
    @staticmethod
    def get_queue(max_size: int) -> PriorityQueue:
        return PriorityQueue(max_size)

    async def push(self, request: aioscrapy.Request) -> None:
        data = self._encode_request(request)
        score = request.priority
        await self.container.put((score, data))

    async def pop(self, count: int = 1) -> Optional[aioscrapy.Request]:
        for _ in range(count):
            try:
                score, data = self.container.get_nowait()
            except QueueEmpty:
                break
            yield self._decode_request(data)


SpiderQueue = MemoryFifoQueue
SpiderStack = MemoryLifoQueue
SpiderPriorityQueue = MemoryPriorityQueue
