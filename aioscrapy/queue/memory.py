from asyncio import PriorityQueue, Queue, LifoQueue
from asyncio.queues import QueueEmpty
from typing import Optional

from aioscrapy.queue import AbsQueue
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


class MemoryQueueBase(AbsQueue):
    inc_key = 'scheduler/enqueued/memory'

    def __init__(
            self, container, spider,
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None,
            max_size: int = 0
    ):
        super().__init__(container, spider, key, serializer)
        self.max_size = max_size

    @classmethod
    async def from_spider(cls, spider) -> "MemoryQueueBase":
        settings = spider.settings
        max_size = settings.getint("QUEUE_MAXSIZE", 0)
        queue = cls.get_queue(max_size)
        queue_key = settings.get("SCHEDULER_QUEUE_KEY", '%(spider)s:requests')
        serializer = settings.get("SCHEDULER_SERIALIZER", "aioscrapy.serializer.PickleSerializer")
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
    def get_queue(max_size):
        raise NotImplementedError

    async def push(self, request):
        data = self._encode_request(request)
        await self.container.put(data)

    async def pop(self, count: int = 1):
        for _ in range(count):
            try:
                data = self.container.get_nowait()
            except QueueEmpty:
                break
            yield self._decode_request(data)

    async def clear(self, timeout: int = 0):
        self.container = self.get_queue(self.max_size)


class MemoryFifoQueue(MemoryQueueBase):

    @staticmethod
    def get_queue(max_size):
        return Queue(max_size)


class MemoryLifoQueue(MemoryFifoQueue):
    @staticmethod
    def get_queue(max_size):
        return LifoQueue(max_size)


class MemoryPriorityQueue(MemoryFifoQueue):
    @staticmethod
    def get_queue(max_size):
        return PriorityQueue(max_size)

    async def push(self, request):
        data = self._encode_request(request)
        score = request.priority
        await self.container.put((score, data))

    async def pop(self, count: int = 1):
        for _ in range(count):
            try:
                score, data = self.container.get_nowait()
            except QueueEmpty:
                break
            yield self._decode_request(data)


SpiderQueue = MemoryFifoQueue
SpiderStack = MemoryLifoQueue
SpiderPriorityQueue = MemoryPriorityQueue
