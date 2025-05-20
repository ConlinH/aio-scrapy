"""
Logging utilities for aioscrapy.
aioscrapy的日志工具。

This module provides logging functionality for aioscrapy using the loguru library.
It configures logging based on settings and provides a spider-aware logger.
此模块使用loguru库为aioscrapy提供日志功能。
它根据设置配置日志记录，并提供一个感知爬虫的日志记录器。
"""

import asyncio
import sys
import warnings
from typing import Type

from loguru import logger as _logger

from aioscrapy.settings import Settings

# Remove the default stderr handler to avoid duplicate logs
# 移除默认的stderr处理程序以避免重复日志
for _handler in _logger._core.handlers.values():
    if _handler._name == '<stderr>':
        _logger.remove(_handler._id)


def configure_logging(spider: Type["Spider"], settings: Settings):
    """
    Configure logging for a spider based on settings.
    根据设置为爬虫配置日志记录。

    This function sets up logging handlers for a specific spider based on the provided settings.
    It can configure logging to stderr and/or to a file, with various options like log level,
    rotation, retention, etc.
    此函数根据提供的设置为特定爬虫设置日志处理程序。
    它可以配置日志记录到stderr和/或文件，具有各种选项，如日志级别、轮换、保留等。

    Args:
        spider: The spider instance for which to configure logging.
               要为其配置日志记录的爬虫实例。
        settings: The settings object containing logging configuration.
                 包含日志配置的设置对象。
    """
    # Get logging configuration from settings
    # 从设置中获取日志配置
    formatter = settings.get('LOG_FORMAT')
    level = settings.get('LOG_LEVEL', 'INFO')
    enqueue = settings.get('ENQUEUE', True)

    # Configure stderr logging if enabled
    # 如果启用，配置stderr日志记录
    if settings.get('LOG_STDOUT', True):
        _logger.add(
            sys.stderr, format=formatter, level=level, enqueue=enqueue,
            filter=lambda record: record["extra"].get("spidername") == spider.name,
        )

    # Configure file logging if a filename is provided
    # 如果提供了文件名，配置文件日志记录
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
    """
    Spider-aware logger for aioscrapy.
    aioscrapy的爬虫感知日志记录器。

    This class provides a wrapper around the loguru logger that automatically
    binds the current spider name to log records. This allows for filtering
    logs by spider name and provides context about which spider generated each log.
    此类提供了loguru日志记录器的包装器，它自动将当前爬虫名称绑定到日志记录。
    这允许按爬虫名称过滤日志，并提供关于哪个爬虫生成了每条日志的上下文。

    The logger methods (debug, info, warning, etc.) are dynamically accessed
    through __getattr__, so they're not explicitly defined.
    日志记录器方法（debug、info、warning等）是通过__getattr__动态访问的，
    因此它们没有明确定义。
    """
    __slots__ = (
        'catch', 'complete', 'critical', 'debug', 'error', 'exception',
        'info', 'log', 'patch', 'success', 'trace', 'warning'
    )

    def __getattr__(self, method):
        """
        Dynamically access logger methods with spider name binding.
        动态访问带有爬虫名称绑定的日志记录器方法。

        This method intercepts attribute access to provide logger methods that
        automatically include the current spider name in the log context.
        此方法拦截属性访问，以提供自动在日志上下文中包含当前爬虫名称的日志记录器方法。

        Args:
            method: The name of the logger method to access (e.g., 'info', 'debug').
                   要访问的日志记录器方法的名称（例如，'info'、'debug'）。

        Returns:
            The requested logger method, bound with the current spider name.
            请求的日志记录器方法，绑定了当前爬虫名称。

        Note:
            If the current task name cannot be determined, it falls back to the
            original logger method without binding a spider name.
            如果无法确定当前任务名称，它会回退到原始日志记录器方法，而不绑定爬虫名称。
        """
        try:
            # Get the current task name as the spider name
            # 获取当前任务名称作为爬虫名称
            spider_name = asyncio.current_task().get_name()
            # Return the logger method bound with the spider name
            # 返回绑定了爬虫名称的日志记录器方法
            return getattr(_logger.bind(spidername=spider_name), method)
        except Exception as e:
            # Fall back to the original logger method if binding fails
            # 如果绑定失败，回退到原始日志记录器方法
            warnings.warn(f'Error on get logger: {e}')
            return getattr(_logger, method)


# Create a singleton instance of the spider-aware logger
# 创建爬虫感知日志记录器的单例实例
logger = AioScrapyLogger()
