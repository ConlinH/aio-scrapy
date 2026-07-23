import asyncio
from types import SimpleNamespace

import pytest

from aioscrapy import Request
from aioscrapy.queue.redis import ACK_SCRIPT, NACK_SCRIPT, RedisFifoQueue, RedisPriorityQueue
from aioscrapy.queue.memory import MemoryFifoQueue
from aioscrapy.core.scheduler import Scheduler
from aioscrapy.serializer import JsonSerializer
from tests._fake_redis_queue import FakeReliableRedis


@pytest.mark.asyncio
async def test_batch_ack_deletes_payload_in_one_rtt():
    redis = FakeReliableRedis()
    queue = RedisPriorityQueue(redis, key='jobs', serializer=JsonSerializer)
    requests = [
        Request('https://example.com/same', priority=2),
        Request('https://example.com/same', priority=1),
        Request('https://example.com/other', priority=0),
    ]

    await queue.push_batch(requests)
    deliveries = await queue.reserve(3, visibility_timeout=10)
    results = await queue.ack_batch(deliveries)

    assert len({delivery.task_id for delivery in deliveries}) == 3
    assert results == [True, True, True]
    assert await queue.len() == 0
    assert redis.payload == {}
    assert sum(call[0] == ACK_SCRIPT for call in redis.calls) == 1


@pytest.mark.asyncio
async def test_expired_delivery_is_redelivered_and_old_ack_is_fenced():
    redis = FakeReliableRedis()
    worker_a = RedisPriorityQueue(redis, key='jobs', serializer=JsonSerializer)
    worker_b = RedisPriorityQueue(redis, key='jobs', serializer=JsonSerializer)
    await worker_a.push(Request('https://example.com', priority=7))

    first = (await worker_a.reserve(1, visibility_timeout=10))[0]
    redis.advance(11)
    second = (await worker_b.reserve(1, visibility_timeout=10))[0]

    assert second.task_id == first.task_id
    assert second.token != first.token
    assert second.redelivered is True
    assert second.request.priority == 7
    assert await worker_a.ack(first) is False
    assert first.task_id in redis.payload
    assert await worker_b.ack(second) is True
    assert first.task_id not in redis.payload


@pytest.mark.asyncio
async def test_nack_requeues_with_redelivery_marker_in_one_rtt():
    redis = FakeReliableRedis()
    queue = RedisFifoQueue(redis, key='jobs', serializer=JsonSerializer)
    await queue.push_batch([
        Request('https://example.com/1'),
        Request('https://example.com/2'),
    ])
    deliveries = await queue.reserve(2)

    assert await queue.nack_batch(deliveries) == [True, True]
    redelivered = await queue.reserve(2)

    assert all(delivery.redelivered for delivery in redelivered)
    assert sum(call[0] == NACK_SCRIPT for call in redis.calls) == 1


@pytest.mark.asyncio
async def test_scheduler_batches_completed_deliveries():
    class RecordingQueue(MemoryFifoQueue):
        def __init__(self):
            super().__init__(asyncio.Queue(), spider=None, serializer=JsonSerializer)
            self.ack_batches = []

        async def ack_batch(self, deliveries):
            self.ack_batches.append(list(deliveries))
            return await super().ack_batch(deliveries)

    queue = RecordingQueue()
    scheduler = Scheduler(
        queue,
        SimpleNamespace(name='test'),
        ack_batch_size=3,
        ack_flush_interval=10,
    )
    await scheduler.enqueue_request_batch([
        Request('https://example.com/1'),
        Request('https://example.com/2'),
        Request('https://example.com/3'),
    ])
    requests = [request async for request in scheduler.next_request(3)]

    for request in requests:
        await scheduler.complete_request(request)

    assert len(queue.ack_batches) == 1
    assert len(queue.ack_batches[0]) == 3
    assert not await scheduler.has_pending_requests()
    await scheduler.close('finished')


@pytest.mark.asyncio
async def test_scheduler_flushes_low_volume_ack_after_interval():
    class RecordingQueue(MemoryFifoQueue):
        def __init__(self):
            super().__init__(asyncio.Queue(), spider=None, serializer=JsonSerializer)
            self.ack_event = asyncio.Event()

        async def ack_batch(self, deliveries):
            result = await super().ack_batch(deliveries)
            self.ack_event.set()
            return result

    queue = RecordingQueue()
    scheduler = Scheduler(
        queue,
        SimpleNamespace(name='test'),
        ack_batch_size=100,
        ack_flush_interval=0.05,
    )
    await scheduler.enqueue_request(Request('https://example.com'))
    request = [request async for request in scheduler.next_request(1)][0]

    await scheduler.complete_request(request)
    await asyncio.wait_for(queue.ack_event.wait(), 0.5)

    assert not await scheduler.has_pending_requests()
    await scheduler.close('finished')
