import asyncio
from types import SimpleNamespace

import pytest

from aioscrapy.libs.extensions.logstats import LogStats
from aioscrapy.settings import Settings
from aioscrapy.utils.log import (
    bind_log_context,
    close_logging,
    configure_logging,
    get_log_context,
    logger,
    reset_log_context,
)


class DemoSpider:
    name = 'demo'


@pytest.mark.asyncio
async def test_named_background_task_inherits_crawler_log_context():
    async def read_context():
        return get_log_context()

    token = bind_log_context('demo', 'run-a')
    try:
        task = asyncio.create_task(read_context(), name='demo:logstats')
    finally:
        reset_log_context(token)

    context = await task

    assert context.spider_name == 'demo'
    assert context.crawler_id == 'run-a'
    assert task.get_name() == 'demo:logstats'


@pytest.mark.asyncio
async def test_same_named_crawlers_write_to_separate_log_files(tmp_path):
    settings = Settings({
        'ENQUEUE': False,
        'LOG_FILE': str(tmp_path / 'crawler.log'),
        'LOG_FILE_PER_CRAWLER': True,
        'LOG_FORMAT': '{extra[spidername]}|{extra[crawler_id]}|{message}',
        'LOG_STDOUT': False,
    })

    handlers_a = configure_logging(DemoSpider, settings, crawler_id='run-a')
    handlers_b = configure_logging(DemoSpider, settings, crawler_id='run-b')

    async def emit(crawler_id, message):
        async def write_log():
            logger.info(message)

        token = bind_log_context('demo', crawler_id)
        try:
            task = asyncio.create_task(write_log(), name=f'demo:{crawler_id}')
            await task
        finally:
            reset_log_context(token)

    try:
        await asyncio.gather(
            emit('run-a', 'message-a'),
            emit('run-b', 'message-b'),
        )
    finally:
        await close_logging((*handlers_a, *handlers_b))

    log_a = (tmp_path / 'crawler.run-a.log').read_text(encoding='utf-8')
    log_b = (tmp_path / 'crawler.run-b.log').read_text(encoding='utf-8')

    assert 'demo|run-a|message-a' in log_a
    assert 'message-b' not in log_a
    assert 'demo|run-b|message-b' in log_b
    assert 'message-a' not in log_b


@pytest.mark.asyncio
async def test_logstats_named_task_writes_with_crawler_context(tmp_path):
    settings = Settings({
        'ENQUEUE': False,
        'LOG_FILE': str(tmp_path / '{spider_name}.{crawler_id}.log'),
        'LOG_FORMAT': '{extra[spidername]}|{extra[crawler_id]}|{message}',
        'LOG_STDOUT': False,
    })
    stats = SimpleNamespace(get_value=lambda name, default: default)
    spider = SimpleNamespace(name='demo')
    extension = LogStats(stats, interval=0.01)

    token = bind_log_context('demo', 'run-logstats')
    handlers = configure_logging(DemoSpider, settings, crawler_id='run-logstats')
    try:
        extension.spider_opened(spider)
        await asyncio.sleep(0.03)
        await extension.spider_closed(spider, reason='finished')
    finally:
        await close_logging(handlers)
        reset_log_context(token)

    content = (tmp_path / 'demo.run-logstats.log').read_text(encoding='utf-8')

    assert 'demo|run-logstats|<demo> Crawled 0 pages' in content
