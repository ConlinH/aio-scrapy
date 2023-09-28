import asyncio
import sys
import warnings
from typing import Type

from loguru import logger as _logger

from aioscrapy.spiders import Spider
from aioscrapy.settings import Settings

_logger.remove(0)


def configure_logging(spider: Type[Spider], settings: Settings):
    formatter = settings.get('LOG_FORMAT')
    level = settings.get('LOG_LEVEL', 'INFO')
    enqueue = settings.get('ENQUEUE', True)
    if settings.get('LOG_STDOUT', True):
        _logger.add(
            sys.stderr, format=formatter, level=level, enqueue=enqueue,
            filter=lambda record: record["extra"].get("spidername") == spider.name,
        )

    if filename := settings.get('LOG_FILE'):
        rotation = settings.get('LOG_ROTATION', '20MB')
        retention = settings.get('LOG_RETENTION', 10)
        encoding = settings.get('LOG_ENCODING', 'utf-8')
        _logger.add(
            sink=filename, format=formatter, encoding=encoding, level=level,
            enqueue=enqueue, rotation=rotation, retention=retention,
            filter=lambda record: record["extra"].get("spidername") == spider.name,
        )


class AioScrapyLogger:
    __slots__ = (
        'catch', 'complete', 'critical', 'debug', 'error', 'exception',
        'info', 'log', 'patch', 'success', 'trace', 'warning'
    )

    def __getattr__(self, method):
        try:
            spider_name = asyncio.current_task().get_name()
            return getattr(_logger.bind(spidername=spider_name), method)
        except Exception as e:
            warnings.warn(f'Error on get logger: {e}')
            return getattr(_logger, method)


logger = AioScrapyLogger()
