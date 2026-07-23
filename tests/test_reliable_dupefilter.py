import asyncio
from types import SimpleNamespace

import pytest

from aioscrapy import Request
from aioscrapy.core.downloader import Downloader
from aioscrapy.dupefilters.redis import (
    ExRedisBloomDupeFilter,
    ExRedisRFPDupeFilter,
    RedisBloomDupeFilter,
    RedisRFPDupeFilter,
)
from aioscrapy.http import Response


class Settings(dict):
    def getint(self, name, default=0):
        return int(self.get(name, default))

    def getbool(self, name, default=False):
        return bool(self.get(name, default))

    def getfloat(self, name, default=0.0):
        return float(self.get(name, default))


class Engine:
    def __init__(self):
        self.outputs = []
        self.cancelled = []
        self.event = asyncio.Event()

    async def handle_downloader_output(self, result, request):
        self.outputs.append((result, request))
        self.event.set()

    async def handle_downloader_cancelled(self, request):
        self.cancelled.append(request)
        self.event.set()


class Signals:
    async def send_catch_log(self, *args, **kwargs):
        return []


class Handler:
    def __init__(self):
        self.calls = []

    async def download_request(self, request, spider):
        self.calls.append(request)
        return Response(request.url, request=request)


class Middleware:
    async def process_request(self, spider, request):
        return None

    async def process_response(self, spider, request, response):
        return response

    async def process_exception(self, spider, request, exception):
        return exception


class DupeFilter:
    def __init__(self, seen=False, error=None, done_error=None):
        self.seen = seen
        self.error = error
        self.done_error = done_error
        self.seen_requests = []
        self.done_calls = []
        self.logged = []

    async def request_seen(self, request):
        self.seen_requests.append(request)
        if self.error:
            raise self.error
        return self.seen

    async def done(self, request, done_type):
        self.done_calls.append((request, done_type))
        if self.done_error:
            raise self.done_error

    def log(self, request, spider):
        self.logged.append(request)

    async def close(self, reason=''):
        pass


class RedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def getbit(self, key, offset):
        self.commands.append(('getbit', key, offset))
        return self

    def setbit(self, key, offset, value):
        self.commands.append(('setbit', key, offset, value))
        return self

    def sadd(self, key, value):
        self.commands.append(('sadd', key, value))
        return self

    def expire(self, key, ttl):
        self.commands.append(('expire', key, ttl))
        return self

    async def execute(self):
        result = []
        for command in self.commands:
            name, *args = command
            result.append(await getattr(self.redis, name)(*args))
        return result


class DupeRedis:
    def __init__(self):
        self.sets = {}
        self.bits = {}

    def pipeline(self, transaction=True):
        return RedisPipeline(self)

    async def sadd(self, key, value):
        values = self.sets.setdefault(key, set())
        added = value not in values
        values.add(value)
        return int(added)

    async def srem(self, key, value):
        values = self.sets.setdefault(key, set())
        existed = value in values
        values.discard(value)
        return int(existed)

    async def getbit(self, key, offset):
        return int(offset in self.bits.setdefault(key, set()))

    async def setbit(self, key, offset, value):
        bits = self.bits.setdefault(key, set())
        previous = int(offset in bits)
        if value:
            bits.add(offset)
        else:
            bits.discard(offset)
        return previous

    async def expire(self, key, ttl):
        return int(key in self.sets)

    async def delete(self, *keys):
        for key in keys:
            self.sets.pop(key, None)
            self.bits.pop(key, None)


def make_downloader(dupefilter):
    engine = Engine()
    handler = Handler()
    spider = SimpleNamespace(
        name='test',
        proxy=None,
        crawler=SimpleNamespace(stats=SimpleNamespace(inc_value=lambda *args, **kwargs: None)),
    )
    crawler = SimpleNamespace(
        settings=Settings(
            CONCURRENT_REQUESTS=1,
            GET_REQUESTS_COUNT=1,
            CONCURRENT_REQUESTS_PER_DOMAIN=1,
            CONCURRENT_REQUESTS_PER_IP=0,
            RANDOMIZE_DOWNLOAD_DELAY=False,
            DOWNLOAD_DELAY=0,
        ),
        signals=Signals(),
        spider=spider,
        engine=engine,
    )
    return Downloader(crawler, handler, Middleware(), dupefilter=dupefilter), engine, handler


@pytest.mark.asyncio
async def test_first_duplicate_is_completed_without_done_callback():
    dupefilter = DupeFilter(seen=True)
    downloader, engine, handler = make_downloader(dupefilter)
    request = Request('https://example.com')

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert handler.calls == []
    assert dupefilter.logged == [request]
    assert dupefilter.done_calls == []
    assert engine.outputs == [(None, request)]
    assert engine.cancelled == []
    await downloader.close()


@pytest.mark.asyncio
async def test_redelivery_checks_fingerprint_but_processes_when_seen():
    dupefilter = DupeFilter(seen=True)
    downloader, engine, handler = make_downloader(dupefilter)
    request = Request('https://example.com')
    request._queue_redelivered = True

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert dupefilter.seen_requests == [request]
    assert handler.calls == [request]
    assert dupefilter.done_calls == [(request, 'request_ok')]
    assert isinstance(engine.outputs[0][0], Response)
    await downloader.close()


@pytest.mark.asyncio
async def test_redelivery_registers_missing_fingerprint_and_processes():
    dupefilter = DupeFilter(seen=False)
    downloader, engine, handler = make_downloader(dupefilter)
    request = Request('https://example.com')
    request._queue_redelivered = True

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert dupefilter.seen_requests == [request]
    assert handler.calls == [request]
    assert dupefilter.done_calls == [(request, 'request_ok')]
    await downloader.close()


@pytest.mark.asyncio
async def test_dont_filter_bypasses_dupefilter():
    dupefilter = DupeFilter(seen=True)
    downloader, engine, handler = make_downloader(dupefilter)
    request = Request('https://example.com', dont_filter=True)

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert dupefilter.seen_requests == []
    assert dupefilter.done_calls == []
    assert handler.calls == [request]
    await downloader.close()


@pytest.mark.asyncio
async def test_dupefilter_failure_releases_delivery_instead_of_completing():
    dupefilter = DupeFilter(error=ConnectionError('redis unavailable'))
    downloader, engine, handler = make_downloader(dupefilter)
    request = Request('https://example.com')

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert handler.calls == []
    assert dupefilter.done_calls == []
    assert engine.outputs == []
    assert engine.cancelled == [request]
    await downloader.close()


@pytest.mark.asyncio
async def test_dupefilter_done_failure_releases_delivery_instead_of_completing():
    dupefilter = DupeFilter(done_error=ConnectionError('redis unavailable'))
    downloader, engine, handler = make_downloader(dupefilter)
    request = Request('https://example.com')

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert handler.calls == [request]
    assert dupefilter.done_calls == [(request, 'request_ok')]
    assert engine.outputs == []
    assert engine.cancelled == [request]
    await downloader.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('factory', [
    lambda redis: RedisRFPDupeFilter(redis, key='fingerprints'),
    lambda redis: ExRedisRFPDupeFilter(redis, key='fingerprints'),
    lambda redis: RedisBloomDupeFilter(
        redis, key='fingerprints', debug=False, bit=8, hash_number=3,
        keep_on_close=True, info=False,
    ),
    lambda redis: ExRedisBloomDupeFilter(
        redis, key='fingerprints', key_set='fingerprints:pending', ttl=60,
        debug=False, bit=8, hash_number=3, keep_on_close=True, info=False,
    ),
])
async def test_filtered_duplicate_preserves_all_redis_dupefilters(factory):
    redis = DupeRedis()
    dupefilter = factory(redis)
    downloader, engine, _handler = make_downloader(dupefilter)
    request = Request('https://example.com')
    assert await dupefilter.request_seen(request) is False

    await downloader.fetch(request)
    await asyncio.wait_for(engine.event.wait(), 1)

    assert await dupefilter.request_seen(request) is True
    await downloader.close()
