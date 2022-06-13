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

    async def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            data = await self.container.brpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = await self.container.rpop(self.key)
        if data:
            return self._decode_request(data)


class RedisPriorityQueue(RedisQueueBase):
    """Per-spider priority queue abstraction using redis' sorted set"""

    async def len(self):
        return await self.container.zcard(self.key)

    async def push(self, request):
        """Push a request"""
        data = self._encode_request(request)
        score = request.priority
        await self.container.zadd(self.key, {data: score})

    async def pop(self, timeout=0):
        """
        Pop a request
        timeout not support in this queue class
        """
        # use atomic range/remove using multi/exec
        async with self.container.pipeline(transaction=True) as pipe:
            results, count = await (
                pipe.zrange(self.key, 0, 0)
                    .zremrangebyrank(self.key, 0, 0)
                    .execute()
            )
        if results:
            return self._decode_request(results[0])


class RedisLifoQueue(RedisQueueBase):
    """Per-spider LIFO queue."""

    async def len(self):
        return await self.container.llen(self.key)

    async def push(self, request):
        """Push a request"""
        await self.container.lpush(self.key, self._encode_request(request))

    async def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            data = await self.container.blpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = await self.container.lpop(self.key)

        if data:
            return self._decode_request(data)


# TODO: Deprecate the use of these names.
SpiderQueue = RedisFifoQueue
SpiderStack = RedisLifoQueue
SpiderPriorityQueue = RedisPriorityQueue
