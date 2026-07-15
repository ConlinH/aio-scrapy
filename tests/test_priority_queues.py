from asyncio import PriorityQueue

import pytest

from aioscrapy import Request
from aioscrapy.queue.memory import MemoryPriorityQueue
from aioscrapy.queue.redis import RedisPriorityQueue
from aioscrapy.serializer import JsonSerializer, PickleSerializer


async def collect(queue, count):
    return [request async for request in queue.pop(count)]


@pytest.mark.asyncio
async def test_memory_priority_queue_returns_highest_priority_first():
    queue = MemoryPriorityQueue(
        PriorityQueue(),
        spider=None,
        serializer=PickleSerializer,
    )
    requests = [
        Request('https://example.com/low', priority=-10),
        Request('https://example.com/high', priority=100),
        Request('https://example.com/default', priority=0),
    ]

    await queue.push_batch(requests)

    assert [request.priority for request in await collect(queue, 3)] == [100, 0, -10]


class FakeRedisPipeline:
    def __init__(self, results):
        self.results = results
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def zadd(self, key, mapping):
        self.commands.append(('zadd', key, mapping))
        return self

    def zrange(self, key, start, stop):
        self.commands.append(('zrange', key, start, stop))
        return self

    def zremrangebyrank(self, key, start, stop):
        self.commands.append(('zremrangebyrank', key, start, stop))
        return self

    async def execute(self):
        return self.results, len(self.results)


class FakeRedis:
    def __init__(self, results):
        self.pipeline_instance = FakeRedisPipeline(results)
        self.transaction = None
        self.zadd_calls = []

    async def zadd(self, key, mapping):
        self.zadd_calls.append((key, mapping))

    def pipeline(self, transaction=True):
        self.transaction = transaction
        return self.pipeline_instance


@pytest.mark.asyncio
async def test_redis_priority_queue_matches_scrapy_redis_score_direction():
    requests = [
        Request('https://example.com/high', priority=100),
        Request('https://example.com/default', priority=0),
    ]
    encoded = [JsonSerializer.dumps(request.to_dict()) for request in requests]
    redis = FakeRedis(encoded)
    queue = RedisPriorityQueue(
        redis,
        spider=None,
        key='spider:requests',
        serializer=JsonSerializer,
    )

    await queue.push(requests[0])
    await queue.push_batch(requests)
    popped = await collect(queue, 2)

    assert [request.priority for request in popped] == [100, 0]
    assert redis.zadd_calls == [
        ('spider:requests', {encoded[0]: -100}),
    ]
    assert redis.transaction is True
    assert redis.pipeline_instance.commands == [
        ('zadd', 'spider:requests', {encoded[0]: -100}),
        ('zadd', 'spider:requests', {encoded[1]: 0}),
        ('zrange', 'spider:requests', 0, 1),
        ('zremrangebyrank', 'spider:requests', 0, 1),
    ]
