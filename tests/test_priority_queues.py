from asyncio import PriorityQueue

import pytest

from aioscrapy import Request
from aioscrapy.queue.memory import MemoryPriorityQueue
from aioscrapy.queue.redis import PUSH_SCRIPT, RESERVE_SCRIPT, RedisPriorityQueue
from aioscrapy.serializer import JsonSerializer, PickleSerializer
from tests._fake_redis_queue import FakeReliableRedis


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


@pytest.mark.asyncio
async def test_redis_priority_queue_preserves_priority_and_batches_rtt():
    redis = FakeReliableRedis()
    queue = RedisPriorityQueue(
        redis,
        spider=None,
        key='spider:requests',
        serializer=JsonSerializer,
    )
    requests = [
        Request('https://example.com/low', priority=-10),
        Request('https://example.com/high', priority=100),
        Request('https://example.com/default', priority=0),
    ]

    await queue.push_batch(requests)
    deliveries = await queue.reserve(3, visibility_timeout=60)

    assert [delivery.request.priority for delivery in deliveries] == [100, 0, -10]
    assert [call[0] for call in redis.calls] == [PUSH_SCRIPT, RESERVE_SCRIPT]
    assert queue.ready_key == '{spider:requests}:ready'
    assert queue.processing_key == '{spider:requests}:processing'
    assert queue.payload_key == '{spider:requests}:payload'
