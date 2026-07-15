from types import SimpleNamespace

import pytest

from aioscrapy.libs.pipelines import DBPipelineBase


class DummySettings(dict):
    def getint(self, name, default=0):
        return int(self.get(name, default))

    def getfloat(self, name, default=0.0):
        return float(self.get(name, default))

    def getbool(self, name, default=False):
        return bool(self.get(name, default))

    def getlist(self, name, default=None):
        return list(self.get(name, default or []))


class DummyPipeline(DBPipelineBase):
    def __init__(self, settings=None):
        super().__init__(settings or DummySettings(), "dummy")
        self.write_batch = None

    def parse_item_to_cache(self, item, save_info):
        raise NotImplementedError

    async def _write_batch(self, cache_key, items):
        await self.write_batch(items)


@pytest.mark.asyncio
async def test_failed_batch_remains_cached_for_retry():
    pipeline = DummyPipeline()
    original_items = [{"id": 1}, {"id": 2}]
    pipeline.item_cache["batch"] = list(original_items)

    async def fail(_items):
        raise RuntimeError("database unavailable")

    pipeline.write_batch = fail

    with pytest.raises(RuntimeError, match="database unavailable"):
        await pipeline._save("batch")

    assert pipeline.item_cache["batch"] == original_items


@pytest.mark.asyncio
async def test_successful_batch_acknowledges_only_its_snapshot():
    pipeline = DummyPipeline()
    pipeline.item_cache["batch"] = [{"id": 1}, {"id": 2}]

    async def save(items):
        assert items == [{"id": 1}, {"id": 2}]
        pipeline.item_cache["batch"].append({"id": 3})

    pipeline.write_batch = save
    await pipeline._save("batch")

    assert pipeline.item_cache["batch"] == [{"id": 3}]


@pytest.mark.asyncio
async def test_connection_failure_pauses_retries_and_resumes_spider():
    settings = DummySettings({
        "DB_PIPELINE_PAUSE_ON_CONNECTION_ERROR": True,
        "DB_PIPELINE_WRITE_ERROR_RETRY_INTERVAL": 0,
    })
    pipeline = DummyPipeline(settings)
    pipeline.item_cache["batch"] = [{"id": 1}]
    pipeline.spider = SimpleNamespace(pause=False, _pause_time=None)
    pause_states = []

    async def flaky_save(_items):
        pause_states.append(pipeline.spider.pause)
        if len(pause_states) == 1:
            raise ConnectionError("database unavailable")

    pipeline.write_batch = flaky_save
    await pipeline._save("batch")

    assert pause_states == [False, True]
    assert pipeline.item_cache["batch"] == []
    assert pipeline.spider.pause is False
    assert pipeline.spider._pause_time is None
    assert not hasattr(pipeline.spider, '_db_pipeline_pause_state')


@pytest.mark.asyncio
async def test_non_connection_failure_does_not_pause_or_retry():
    settings = DummySettings({"DB_PIPELINE_PAUSE_ON_CONNECTION_ERROR": True})
    pipeline = DummyPipeline(settings)
    pipeline.item_cache["batch"] = [{"id": 1}]
    pipeline.spider = SimpleNamespace(pause=False, _pause_time=None)
    attempts = 0

    async def invalid_data(_items):
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid column")

    pipeline.write_batch = invalid_data
    with pytest.raises(ValueError, match="invalid column"):
        await pipeline._save("batch")

    assert attempts == 1
    assert pipeline.item_cache["batch"] == [{"id": 1}]
    assert pipeline.spider.pause is False


@pytest.mark.asyncio
async def test_configured_write_error_type_pauses_and_retries():
    settings = DummySettings({
        "DB_PIPELINE_PAUSE_ON_WRITE_ERROR_TYPES": [ValueError],
        "DB_PIPELINE_WRITE_ERROR_RETRY_INTERVAL": 0,
    })
    pipeline = DummyPipeline(settings)
    pipeline.item_cache["batch"] = [{"id": 1}]
    pipeline.spider = SimpleNamespace(pause=False, _pause_time=None)
    attempts = 0

    async def retryable_write(_items):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("temporary write failure")

    pipeline.write_batch = retryable_write
    await pipeline._save("batch")

    assert attempts == 2
    assert pipeline.item_cache["batch"] == []
    assert pipeline.spider.pause is False


@pytest.mark.asyncio
async def test_connection_retry_is_disabled_by_default():
    pipeline = DummyPipeline()
    pipeline.item_cache["batch"] = [{"id": 1}]
    attempts = 0

    async def unavailable(_items):
        nonlocal attempts
        attempts += 1
        raise ConnectionError("database unavailable")

    pipeline.write_batch = unavailable
    with pytest.raises(ConnectionError, match="database unavailable"):
        await pipeline._save("batch")

    assert attempts == 1


@pytest.mark.asyncio
async def test_connection_retry_stops_when_engine_is_stopping():
    settings = DummySettings({
        "DB_PIPELINE_PAUSE_ON_CONNECTION_ERROR": True,
        "DB_PIPELINE_WRITE_ERROR_RETRY_INTERVAL": 0,
    })
    pipeline = DummyPipeline(settings)
    pipeline.item_cache["batch"] = [{"id": 1}]
    engine = SimpleNamespace(running=True)
    pipeline.spider = SimpleNamespace(
        pause=False,
        _pause_time=None,
        crawler=SimpleNamespace(engine=engine),
    )
    attempts = 0

    async def unavailable(_items):
        nonlocal attempts
        attempts += 1
        engine.running = False
        raise ConnectionError("database unavailable")

    pipeline.write_batch = unavailable
    with pytest.raises(ConnectionError, match="database unavailable"):
        await pipeline._save("batch")

    assert attempts == 1
    assert pipeline.item_cache["batch"] == [{"id": 1}]


def test_multiple_pipelines_do_not_resume_spider_early():
    spider = SimpleNamespace(pause=False, _pause_time=None)
    first = DummyPipeline()
    second = DummyPipeline()
    first.spider = spider
    second.spider = spider

    first._pause_spider_for_write_error()
    second._pause_spider_for_write_error()
    first._resume_spider_after_write_error()

    assert spider.pause is True

    second._resume_spider_after_write_error()

    assert spider.pause is False
    assert spider._pause_time is None
