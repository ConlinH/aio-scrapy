import asyncio
from types import SimpleNamespace

import pytest

import aioscrapy.utils.tools as tools_module
from aioscrapy import Request
from aioscrapy.core.downloader import Downloader
from aioscrapy.core.engine import ExecutionEngine, Slot as EngineSlot
from aioscrapy.libs.extensions.logstats import LogStats
from aioscrapy.middleware.spider import SpiderMiddlewareManager
from aioscrapy.utils.signal import robustApplyWrap
from aioscrapy.utils.tools import TaskManager


class DummySettings(dict):
    def getint(self, name, default=0):
        return int(self.get(name, default))

    def getfloat(self, name, default=0.0):
        return float(self.get(name, default))

    def getbool(self, name, default=False):
        return bool(self.get(name, default))


@pytest.mark.asyncio
async def test_task_manager_names_cancels_and_awaits_tasks():
    manager = TaskManager('test')
    started = asyncio.Event()
    cleaned = asyncio.Event()

    async def worker():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    task = manager.create_task(worker(), name='owned-worker')
    await started.wait()

    assert task.get_name() == 'owned-worker'
    assert task in manager.tasks

    await manager.cancel_all()

    assert task.cancelled()
    assert cleaned.is_set()
    assert not manager.tasks


@pytest.mark.asyncio
async def test_task_manager_reports_background_exceptions(monkeypatch):
    reported = []

    class Logger:
        def opt(self, exception):
            reported.append(exception)
            return self

        def error(self, message):
            reported.append(message)

    async def fail():
        raise RuntimeError('background failed')

    monkeypatch.setattr(tools_module, 'logger', Logger())
    manager = TaskManager('test')
    task = manager.create_task(fail(), name='failing-worker')
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)

    assert isinstance(reported[0], RuntimeError)
    assert 'failing-worker' in reported[1]
    assert not manager.tasks


@pytest.mark.asyncio
async def test_periodic_extension_awaits_task_cancellation():
    stats = SimpleNamespace(get_value=lambda name, default: default)
    extension = LogStats(stats, interval=3600)
    spider = SimpleNamespace(name='test')

    extension.spider_opened(spider)
    task = extension.task
    await asyncio.sleep(0)
    await extension.spider_closed(spider, reason='finished')

    assert task.cancelled()
    assert not extension._tasks.tasks


@pytest.mark.asyncio
async def test_signal_wrapper_propagates_cancellation():
    async def receiver():
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await robustApplyWrap(lambda recv: recv(), receiver)


@pytest.mark.asyncio
async def test_spider_middleware_does_not_convert_cancellation_to_spider_error():
    class Middleware:
        async def process_spider_input(self, response, spider):
            raise asyncio.CancelledError

    manager = SpiderMiddlewareManager(Middleware())

    with pytest.raises(asyncio.CancelledError):
        await manager.scrape_response(
            lambda response, request: None,
            response=object(),
            request=object(),
            spider=object(),
        )


class BlockingHandler:
    def __init__(self):
        self.started = asyncio.Event()
        self.cleaned = asyncio.Event()

    async def download_request(self, request, spider):
        self.started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cleaned.set()


class PassthroughMiddleware:
    def __init__(self):
        self.exceptions = []

    async def process_request(self, spider, request):
        return None

    async def process_exception(self, spider, request, exception):
        self.exceptions.append(exception)
        return exception


@pytest.mark.asyncio
async def test_downloader_close_cancels_owned_download_without_swallowing_cancellation():
    outputs = []

    class Engine:
        async def handle_downloader_output(self, result, request):
            outputs.append((result, request))

    class Signals:
        async def send_catch_log(self, **kwargs):
            return []

    spider = SimpleNamespace(name='test', proxy=None)
    handler = BlockingHandler()
    middleware = PassthroughMiddleware()
    crawler = SimpleNamespace(
        settings=DummySettings(
            CONCURRENT_REQUESTS=1,
            GET_REQUESTS_COUNT=1,
            CONCURRENT_REQUESTS_PER_DOMAIN=1,
            CONCURRENT_REQUESTS_PER_IP=0,
            RANDOMIZE_DOWNLOAD_DELAY=False,
            DOWNLOAD_DELAY=0,
        ),
        signals=Signals(),
        spider=spider,
        engine=Engine(),
    )
    downloader = Downloader(crawler, handler, middleware)
    request = Request('https://example.com')

    await downloader.fetch(request)
    await handler.started.wait()
    await downloader.close()

    assert handler.cleaned.is_set()
    assert middleware.exceptions == []
    assert downloader.active == set()
    assert not downloader._tasks.tasks
    assert outputs == [(None, request)]


@pytest.mark.asyncio
async def test_engine_shutdown_timeout_closes_remaining_components():
    closed = []

    class Signals:
        async def send_catch_log_deferred(self, signal=None, **kwargs):
            return []

    class Downloader:
        active = {object()}

        async def close(self):
            closed.append('downloader')
            self.active.clear()

    class Scraper:
        def is_idle(self):
            return True

        async def close(self):
            closed.append('scraper')

    class Scheduler:
        async def close(self, reason):
            closed.append('scheduler')

    crawler = SimpleNamespace(
        settings=DummySettings(GRACEFUL_SHUTDOWN_TIMEOUT=0.01),
        signals=Signals(),
        logformatter=None,
        stats=None,
    )
    engine = ExecutionEngine(crawler)
    engine.running = True
    engine.spider = object()
    engine.slot = EngineSlot(None)
    engine.downloader = Downloader()
    engine.scraper = Scraper()
    engine.scheduler = Scheduler()

    await asyncio.wait_for(engine.stop(), timeout=0.5)

    assert closed == ['downloader', 'scraper', 'scheduler']
    assert engine.finish is True


@pytest.mark.asyncio
async def test_component_close_timeout_does_not_block_later_components():
    closed = []

    class Signals:
        async def send_catch_log_deferred(self, signal=None, **kwargs):
            return []

    class Downloader:
        active = set()

        async def close(self):
            closed.append('downloader')

    class Scraper:
        def is_idle(self):
            return True

        async def close(self):
            await asyncio.Event().wait()

    class Scheduler:
        async def close(self, reason):
            closed.append('scheduler')

    crawler = SimpleNamespace(
        settings=DummySettings(GRACEFUL_SHUTDOWN_TIMEOUT=0.01),
        signals=Signals(),
        logformatter=None,
        stats=None,
    )
    engine = ExecutionEngine(crawler)
    engine.running = True
    engine.spider = object()
    engine.slot = EngineSlot(None)
    engine.downloader = Downloader()
    engine.scraper = Scraper()
    engine.scheduler = Scheduler()

    await asyncio.wait_for(engine.stop(), timeout=0.5)

    assert closed == ['downloader', 'scheduler']
    assert engine.finish is True
