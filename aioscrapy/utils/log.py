"""
Logging utilities for aioscrapy.
aioscrapy的日志工具。

This module provides logging functionality for aioscrapy using the loguru library.
It configures logging based on settings and provides a crawler-aware logger.
此模块使用loguru库为aioscrapy提供日志功能。
它根据设置配置日志记录，并提供一个感知爬虫运行上下文的日志记录器。
"""

import os
import sys
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterable, Optional, Type

from loguru import logger as _logger

from aioscrapy.settings import Settings


@dataclass(frozen=True)
class CrawlerLogContext:
    """
    Immutable logging identity for one crawler run.
    单次爬虫运行的不可变日志标识。
    """

    spider_name: str
    crawler_id: str


# Keep crawler identity independent from asyncio task names
# 让爬虫日志标识与asyncio任务名称相互独立
_log_context: ContextVar[Optional[CrawlerLogContext]] = ContextVar(
    'aioscrapy_log_context',
    default=None,
)


# Remove the default stderr handler to avoid duplicate logs
# 移除默认的stderr处理程序以避免重复日志
for _handler in _logger._core.handlers.values():
    if _handler._name == '<stderr>':
        _logger.remove(_handler._id)


def bind_log_context(spider_name: str, crawler_id: str) -> Token:
    """
    Bind crawler logging identity to the current execution context.
    将爬虫日志标识绑定到当前执行上下文。
    """
    return _log_context.set(CrawlerLogContext(spider_name, crawler_id))


def reset_log_context(token: Token) -> None:
    """
    Restore the logging context that existed before binding.
    恢复绑定前的日志上下文。
    """
    _log_context.reset(token)


def get_log_context() -> Optional[CrawlerLogContext]:
    """
    Return the crawler logging identity for the current execution context.
    返回当前执行上下文中的爬虫日志标识。
    """
    return _log_context.get()


def _record_belongs_to(crawler_id: str):
    """
    Build a Loguru filter for one crawler run.
    为单次爬虫运行创建Loguru过滤器。
    """
    return lambda record: record['extra'].get('crawler_id') == crawler_id


def _resolve_log_file(filename, spider_name: str, crawler_id: str, per_crawler: bool):
    """
    Resolve crawler placeholders and optionally create a per-run filename.
    解析爬虫占位符，并按需生成单次运行独立的文件名。
    """
    if not isinstance(filename, (str, os.PathLike)):
        return filename

    filename = os.fspath(filename)
    has_crawler_id = '{crawler_id}' in filename
    filename = filename.replace('{spider_name}', spider_name).replace('{crawler_id}', crawler_id)

    # Add the run identifier when the configured path does not provide one
    # 配置路径未提供运行标识时，将其自动追加到扩展名前
    if per_crawler and not has_crawler_id:
        stem, suffix = os.path.splitext(filename)
        filename = f'{stem}.{crawler_id}{suffix}'
    return filename


def configure_logging(
        spider: Type["Spider"],
        settings: Settings,
        crawler_id: Optional[str] = None,
):
    """
    Configure logging handlers for one crawler run.
    为单次爬虫运行配置日志处理器。

    Args:
        spider: The spider class for which to configure logging.
               要配置日志的爬虫类。
        settings: The settings object containing logging configuration.
                  包含日志配置的设置对象。
        crawler_id: Unique identifier for this crawler run.
                    本次爬虫运行的唯一标识。

    Returns:
        tuple: Loguru handler identifiers owned by this crawler.
               当前爬虫拥有的Loguru处理器标识。
    """
    if not settings.getbool('LOG_ENABLED', True):
        return ()

    context = get_log_context()
    crawler_id = crawler_id or (context.crawler_id if context else spider.name)

    # Read shared handler options once for stderr and file sinks
    # 为标准错误和文件输出统一读取处理器配置
    formatter = settings.get('LOG_FORMAT')
    level = settings.get('LOG_LEVEL', 'INFO')
    enqueue = settings.get('ENQUEUE', True)
    record_filter = _record_belongs_to(crawler_id)
    handler_ids = []

    try:
        # Configure stderr logging if enabled
        # 如果启用，配置stderr日志记录
        if settings.getbool('LOG_STDOUT', True):
            handler_ids.append(_logger.add(
                sys.stderr,
                format=formatter,
                level=level,
                enqueue=enqueue,
                filter=record_filter,
            ))

        # Configure file logging if a filename is provided
        # 如果提供了文件名，配置文件日志记录
        if filename := settings.get('LOG_FILE'):
            filename = _resolve_log_file(
                filename,
                spider.name,
                crawler_id,
                settings.getbool('LOG_FILE_PER_CRAWLER', True),
            )
            handler_ids.append(_logger.add(
                sink=filename,
                format=formatter,
                encoding=settings.get('LOG_ENCODING', 'utf-8'),
                level=level,
                enqueue=enqueue,
                rotation=settings.get('LOG_ROTATION', '20MB'),
                retention=settings.get('LOG_RETENTION', 10),
                filter=record_filter,
            ))
    except Exception:
        # Remove partially configured handlers before propagating the failure
        # 传播配置异常前移除已经创建的处理器
        for handler_id in handler_ids:
            _logger.remove(handler_id)
        raise

    return tuple(handler_ids)


async def close_logging(handler_ids: Iterable[int]) -> None:
    """
    Flush queued records and remove handlers owned by one crawler.
    刷新排队日志并移除单个爬虫拥有的处理器。
    """
    handler_ids = tuple(handler_ids)
    if not handler_ids:
        return

    try:
        await _logger.complete()
    finally:
        for handler_id in handler_ids:
            try:
                _logger.remove(handler_id)
            except ValueError:
                # The handler may already be removed during partial cleanup
                # 处理器可能已在部分清理过程中被移除
                pass


class AioScrapyLogger:
    """
    Crawler-aware logger for aioscrapy.
    aioscrapy的爬虫上下文感知日志记录器。

    This class binds the current crawler context to Loguru records. Task names
    remain available for asyncio diagnostics without controlling log routing.
    此类将当前爬虫上下文绑定到Loguru记录。任务名称继续用于asyncio诊断，
    不再控制日志路由。
    """

    __slots__ = (
        'bind', 'catch', 'complete', 'critical', 'debug', 'error', 'exception',
        'info', 'log', 'opt', 'patch', 'success', 'trace', 'warning',
    )

    def __getattr__(self, method):
        """
        Dynamically access logger methods with crawler context binding.
        动态访问带有爬虫上下文绑定的日志记录器方法。
        """
        context = get_log_context()
        extra = {
            'spidername': context.spider_name if context else 'system',
            'crawler_id': context.crawler_id if context else 'system',
        }
        return getattr(_logger.bind(**extra), method)


# Create a singleton instance of the crawler-aware logger
# 创建爬虫上下文感知日志记录器的单例实例
logger = AioScrapyLogger()
