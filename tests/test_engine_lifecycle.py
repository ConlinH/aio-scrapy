import asyncio
from types import SimpleNamespace

import pytest

from aioscrapy import signals
from aioscrapy.core.engine import ExecutionEngine
from aioscrapy.core.scraper import Scraper
from aioscrapy.exceptions import CloseSpider
from aioscrapy.utils.tools import TaskManager


class FakeSignals:
    def __init__(self):
        self.sent = []

    async def send_catch_log_deferred(self, signal=None, **kwargs):
        self.sent.append((signal, kwargs))
        return []


class FakeStats:
    def __init__(self):
        self.closed = []

    def close_spider(self, spider, reason):
        self.closed.append((spider, reason))


def make_engine():
    signal_manager = FakeSignals()
    crawler = SimpleNamespace(
        settings={},
        signals=signal_manager,
        logformatter=None,
        stats=FakeStats(),
    )
    return ExecutionEngine(crawler), signal_manager


@pytest.mark.asyncio
async def test_close_before_open_is_idempotent():
    engine, signal_manager = make_engine()

    await engine.close()
    await engine.close()

    assert engine.finish is True
    stopped = [signal for signal, _ in signal_manager.sent if signal is signals.engine_stopped]
    assert len(stopped) == 1


@pytest.mark.asyncio
async def test_close_cleans_partially_initialized_components():
    engine, _ = make_engine()
    closed = []

    class Scheduler:
        async def close(self, reason):
            closed.append(reason)

    engine.spider = object()
    engine.scheduler = Scheduler()

    await engine.close()

    assert closed == ["shutdown"]
    assert engine.spider is None
    assert engine.finish is True


@pytest.mark.asyncio
async def test_close_spider_exception_routes_through_engine_stop():
    stopped = asyncio.Event()
    reasons = []

    class Engine:
        async def stop(self, reason):
            reasons.append(reason)
            stopped.set()

    tasks = TaskManager('test-crawler')
    scraper = object.__new__(Scraper)
    scraper.crawler = SimpleNamespace(engine=Engine(), create_task=tasks.create_task)
    scraper.spider = SimpleNamespace(name='test')

    await scraper.handle_spider_error(CloseSpider("callback_requested"), None, None)
    await asyncio.wait_for(stopped.wait(), timeout=1)
    await tasks.cancel_all()

    assert reasons == ["callback_requested"]
