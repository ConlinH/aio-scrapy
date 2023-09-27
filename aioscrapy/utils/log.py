import asyncio
import sys
import warnings
from typing import Type

from loguru import logger as _logger

from aioscrapy import Settings, Spider
from aioscrapy.exceptions import AioScrapyDeprecationWarning

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


def logformatter_adapter(logkws):
    """
    Helper that takes the dictionary output from the methods in LogFormatter
    and adapts it into a tuple of positional arguments for logger.log calls,
    handling backward compatibility as well.
    """
    if not {'level', 'msg', 'args'} <= set(logkws):
        warnings.warn('Missing keys in LogFormatter method',
                      AioScrapyDeprecationWarning)

    if 'format' in logkws:
        warnings.warn('`format` key in LogFormatter methods has been '
                      'deprecated, use `msg` instead',
                      AioScrapyDeprecationWarning)

    level = logkws.get('level', "INFO")
    message = logkws.get('format', logkws.get('msg'))
    # NOTE: This also handles 'args' being an empty dict, that case doesn't
    # play well in logger.log calls
    args = logkws if not logkws.get('args') else logkws['args']
    return level, message, args


class AioScrapyLogger:

    def __getattr__(self, item):
        spider_name = asyncio.current_task().get_name()
        return getattr(_logger.bind(spidername=spider_name), item)


logger: Type[_logger] = AioScrapyLogger()
