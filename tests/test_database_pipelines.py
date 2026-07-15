from types import SimpleNamespace

import pytest

from aioscrapy.libs.pipelines.mongo import MongoPipeline
from aioscrapy.libs.pipelines.mysql import MysqlPipeline
from aioscrapy.libs.pipelines.pg import PGPipeline
from aioscrapy.libs.pipelines.redis import RedisPipeline
import aioscrapy.libs.pipelines.mongo as mongo_module
import aioscrapy.libs.pipelines.mysql as mysql_module
import aioscrapy.libs.pipelines.pg as pg_module
import aioscrapy.libs.pipelines.redis as redis_module


class DummySettings(dict):
    def getint(self, name, default=0):
        return int(self.get(name, default))

    def getfloat(self, name, default=0.0):
        return float(self.get(name, default))

    def getbool(self, name, default=False):
        return bool(self.get(name, default))


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FailingCursor:
    async def executemany(self, statement, items):
        raise RuntimeError("write failed")


def configure_sql_pipeline(pipeline):
    pipeline.item_cache["batch"] = [[1], [2]]
    pipeline.table_cache["batch"] = "items"
    pipeline.db_alias_cache["batch"] = ["default"]
    pipeline.insert_sql_cache["batch"] = "INSERT INTO items VALUES (?)"


@pytest.mark.asyncio
async def test_mysql_failure_keeps_batch(monkeypatch):
    pipeline = MysqlPipeline(DummySettings(), "mysql")
    configure_sql_pipeline(pipeline)
    manager = SimpleNamespace(get=lambda alias, ping=False: AsyncContext((object(), FailingCursor())))
    monkeypatch.setattr(mysql_module.db_manager, "mysql", manager, raising=False)

    with pytest.raises(RuntimeError, match="write failed"):
        await pipeline._save("batch")

    assert pipeline.item_cache["batch"] == [[1], [2]]


@pytest.mark.asyncio
async def test_postgresql_failure_keeps_batch(monkeypatch):
    pipeline = PGPipeline(DummySettings(), "pg")
    configure_sql_pipeline(pipeline)
    manager = SimpleNamespace(get=lambda alias: AsyncContext(FailingCursor()))
    monkeypatch.setattr(pg_module.db_manager, "pg", manager, raising=False)

    with pytest.raises(RuntimeError, match="write failed"):
        await pipeline._save("batch")

    assert pipeline.item_cache["batch"] == [[1], [2]]


@pytest.mark.asyncio
async def test_mongo_failure_keeps_batch(monkeypatch):
    pipeline = MongoPipeline(DummySettings(), "mongo")
    pipeline.item_cache["batch"] = [{"id": 1}, {"id": 2}]
    pipeline.table_cache["batch"] = "items"
    pipeline.db_alias_cache["batch"] = ["default"]
    pipeline.db_cache["batch"] = "database"
    pipeline.ordered_cache["batch"] = False

    class Executor:
        async def insert(self, *args, **kwargs):
            raise RuntimeError("write failed")

    manager = SimpleNamespace(executor=lambda alias: Executor())
    monkeypatch.setattr(mongo_module.db_manager, "mongo", manager, raising=False)

    with pytest.raises(RuntimeError, match="write failed"):
        await pipeline._save("batch")

    assert pipeline.item_cache["batch"] == [{"id": 1}, {"id": 2}]


@pytest.mark.asyncio
async def test_redis_failure_keeps_batch(monkeypatch):
    pipeline = RedisPipeline(DummySettings(), "redis")
    pipeline.item_cache["batch"] = [{"id": 1}, {"id": 2}]
    pipeline.db_cache["batch"] = ["default"]
    pipeline.key_name_cache["batch"] = "items"
    pipeline.insert_method_cache["batch"] = "push"

    class Executor:
        async def push(self, *args):
            raise RuntimeError("write failed")

    manager = SimpleNamespace(executor=lambda alias: Executor())
    monkeypatch.setattr(redis_module.db_manager, "redis", manager, raising=False)

    with pytest.raises(RuntimeError, match="write failed"):
        await pipeline._save("batch")

    assert pipeline.item_cache["batch"] == [{"id": 1}, {"id": 2}]
