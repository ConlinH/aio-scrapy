import asyncio
from types import SimpleNamespace

import pytest

from aioscrapy import Request
from aioscrapy.core.engine import ExecutionEngine, Slot
from aioscrapy.queue.memory import MemoryFifoQueue
from aioscrapy.queue.redis import RedisFifoQueue


class FakeSignals:
    async def send_catch_log_deferred(self, signal=None, **kwargs):
        return []


def make_engine(settings=None):
    crawler = SimpleNamespace(
        settings=settings or {},
        signals=FakeSignals(),
        logformatter=None,
        stats=None,
    )
    return ExecutionEngine(crawler)


def test_queue_poll_capability_is_resolved_from_instances():
    memory_queue = MemoryFifoQueue(asyncio.Queue(), spider=None)
    external_queue = RedisFifoQueue(object(), spider=None)

    assert memory_queue.requires_periodic_poll is False
    assert external_queue.requires_periodic_poll is True


@pytest.mark.asyncio
async def test_local_scheduler_waits_for_notification_without_polling():
    engine = make_engine({'SCHEDULER_POLL_INTERVAL': 0.01})
    engine.scheduler = SimpleNamespace(requires_periodic_poll=False)

    waiter = asyncio.create_task(engine._wait_for_wakeup())
    await asyncio.sleep(0.03)

    assert not waiter.done()

    engine.wakeup()
    await asyncio.wait_for(waiter, timeout=0.5)


@pytest.mark.asyncio
async def test_external_scheduler_keeps_configured_poll_fallback():
    engine = make_engine({'SCHEDULER_POLL_INTERVAL': 0.01})
    engine.scheduler = SimpleNamespace(requires_periodic_poll=True)

    await asyncio.wait_for(engine._wait_for_wakeup(), timeout=0.5)

    assert not engine._wakeup_event.is_set()


@pytest.mark.asyncio
async def test_crawl_notifies_scheduler_loop_after_enqueue():
    requests = []

    class Scheduler:
        async def enqueue_request(self, request):
            requests.append(request)
            return True

    engine = make_engine()
    engine.scheduler = Scheduler()
    request = Request('https://example.com')

    await engine.crawl(request)

    assert requests == [request]
    assert engine._wakeup_event.is_set()


@pytest.mark.asyncio
async def test_downloader_completion_notifies_central_scheduler_loop():
    engine = make_engine()
    request = Request('https://example.com')
    engine.slot = Slot(None)
    engine.slot.add_request(request)

    await engine.handle_downloader_output(None, request)

    assert request not in engine.slot.inprogress
    assert engine._wakeup_event.is_set()


@pytest.mark.asyncio
async def test_engine_processes_notification_without_fixed_one_second_sleep():
    engine = make_engine()
    spider = SimpleNamespace(pause=False)
    cycles = []

    async def open_engine(opened_spider, start_requests):
        engine.spider = opened_spider
        engine.scheduler = SimpleNamespace(requires_periodic_poll=False)

    async def process_next_request():
        cycles.append(asyncio.get_running_loop().time())
        if len(cycles) == 1:
            engine.wakeup()
        else:
            engine.finish = True

    async def check_idle(opened_spider):
        return None

    engine.open = open_engine
    engine._next_request = process_next_request
    engine._spider_idle = check_idle

    started_at = asyncio.get_running_loop().time()
    await asyncio.wait_for(engine.start(spider), timeout=0.5)

    assert len(cycles) == 2
    assert cycles[1] - started_at < 0.5
