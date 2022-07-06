import logging
from abc import ABC

from aioscrapy.queue import AbsQueue
from aioscrapy.db import db_manager
from aioscrapy.utils.misc import load_object
from aioscrapy.serializer import AbsSerializer

logger = logging.getLogger(__name__)


class RedisQueueBase(AbsQueue, ABC):
    inc_key = 'scheduler/enqueued/redis'

    @classmethod
    def from_dict(cls, data: dict) -> "AbsQueue":
        alias = data.get("alias", 'queue')
        server = db_manager.redis(alias)
        spider_name = data["spider_name"]
        serializer = data.get("serializer", "aioscrapy.serializer.JsonSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            server,
            key='%(spider)s:requests' % {'spider': spider_name},
            serializer=serializer
        )

    @classmethod
    async def from_spider(cls, spider) -> "RedisQueueBase":
        settings = spider.settings
        alias = settings.get("SCHEDULER_QUEUE_ALIAS", 'queue')
        server = db_manager.redis(alias)
        queue_key = settings.get("SCHEDULER_QUEUE_KEY", '%(spider)s:requests')
        serializer = settings.get("SCHEDULER_SERIALIZER", "aioscrapy.serializer.JsonSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            server,
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer
        )

    async def clear(self):
        """Clear queue/stack"""
        await self.container.delete(self.key)


class RedisFifoQueue(RedisQueueBase):
    """Per-spider FIFO queue"""

    async def len(self):
        return await self.container.llen(self.key)

    async def push(self, request):
        """Push a request"""
        await self.container.lpush(self.key, self._encode_request(request))

    async def pop(self, count: int = 1):
        """Pop a request"""
        async with self.container.pipeline(transaction=True) as pipe:
            for _ in range(count):
                pipe.rpop(self.key)
            results = await pipe.execute()
        for result in results:
            if result:
                yield self._decode_request(result)


class RedisPriorityQueue(RedisQueueBase):
    """Per-spider priority queue abstraction using redis' sorted set"""

    async def len(self):
        return await self.container.zcard(self.key)

    async def push(self, request):
        """Push a request"""
        data = self._encode_request(request)
        score = request.priority
        await self.container.zadd(self.key, {data: score})

    async def pop(self, count: int = 1):
        async with self.container.pipeline(transaction=True) as pipe:
            stop = count - 1 if count - 1 > 0 else 0
            results, _ = await (
                pipe.zrange(self.key, 0, stop)
                    .zremrangebyrank(self.key, 0, stop)
                    .execute()
            )
        for result in results:
            yield self._decode_request(result)


class RedisLifoQueue(RedisQueueBase):
    """Per-spider LIFO queue."""

    async def len(self):
        return await self.container.llen(self.key)

    async def push(self, request):
        """Push a request"""
        await self.container.lpush(self.key, self._encode_request(request))

    async def pop(self, count: int = 1):
        """Pop a request"""
        async with self.container.pipeline(transaction=True) as pipe:
            for _ in range(count):
                pipe.lpop(self.key)
            results = await pipe.execute()
        for result in results:
            if result:
                yield self._decode_request(result)


# TODO: Deprecate the use of these names.
SpiderQueue = RedisFifoQueue
SpiderStack = RedisLifoQueue
SpiderPriorityQueue = RedisPriorityQueue
