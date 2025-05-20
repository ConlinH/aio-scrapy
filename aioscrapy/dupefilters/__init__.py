"""
Duplicate Filter Base Module for AioScrapy
AioScrapy的重复过滤器基础模块

This module provides the abstract base class for duplicate filters in AioScrapy.
Duplicate filters are used to avoid crawling the same URL multiple times by
tracking request fingerprints.
此模块提供了AioScrapy中重复过滤器的抽象基类。
重复过滤器用于通过跟踪请求指纹来避免多次爬取相同的URL。
"""

from typing import Literal
from abc import ABCMeta, abstractmethod

from aioscrapy import Request, Spider
from aioscrapy.utils.log import logger


class DupeFilterBase(metaclass=ABCMeta):
    """
    Abstract base class for request fingerprint duplicate filters.
    请求指纹重复过滤器的抽象基类。

    This class defines the interface that all duplicate filters must implement.
    Duplicate filters are used to avoid crawling the same URL multiple times by
    tracking request fingerprints.
    此类定义了所有重复过滤器必须实现的接口。
    重复过滤器用于通过跟踪请求指纹来避免多次爬取相同的URL。
    """

    @classmethod
    @abstractmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        """
        Create a duplicate filter instance from a crawler.
        从爬虫创建重复过滤器实例。

        This is the factory method used by AioScrapy to create the dupefilter.
        这是AioScrapy用于创建重复过滤器的工厂方法。

        Args:
            crawler: The crawler that will use this dupefilter.
                    将使用此重复过滤器的爬虫。

        Returns:
            DupeFilterBase: A new dupefilter instance.
                           一个新的重复过滤器实例。
        """
        pass

    @abstractmethod
    async def request_seen(self, request: Request) -> bool:
        """
        Check if a request has been seen before.
        检查请求是否已经被看到过。

        This method checks if the request's fingerprint is in the set of seen
        fingerprints. If it is, the request is considered a duplicate.
        此方法检查请求的指纹是否在已见过的指纹集合中。如果是，则认为请求是重复的。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            bool: True if the request has been seen before, False otherwise.
                 如果请求之前已经被看到过，则为True，否则为False。
        """
        pass

    @abstractmethod
    async def close(self, reason: str = '') -> None:
        """
        Close the dupefilter.
        关闭过滤器。

        This method is called when the spider is closed. It should clean up
        any resources used by the dupefilter.
        当爬虫关闭时调用此方法。它应该清理重复过滤器使用的任何资源。

        Args:
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        pass

    def log(self, request: Request, spider: Spider):
        """
        Log a filtered duplicate request.
        记录被过滤的重复请求。

        This method logs information about duplicate requests based on the
        logging settings (info, debug, logdupes). It also increments the
        dupefilter/filtered stats counter.
        此方法根据日志设置（info、debug、logdupes）记录有关重复请求的信息。
        它还增加dupefilter/filtered统计计数器。

        Args:
            request: The duplicate request that was filtered.
                    被过滤的重复请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。
        """
        # Log at INFO level if info is True
        # 如果info为True，则在INFO级别记录
        if self.info:
            logger.info("Filtered duplicate request: %(request)s" % {
                'request': request.meta.get('dupefilter_msg') or request
            })
        # Log at DEBUG level if debug is True
        # 如果debug为True，则在DEBUG级别记录
        elif self.debug:
            logger.debug("Filtered duplicate request: %(request)s" % {
                'request': request.meta.get('dupefilter_msg') or request
            })
        # Log the first duplicate at DEBUG level and disable further logging
        # 在DEBUG级别记录第一个重复项并禁用进一步的日志记录
        elif self.logdupes:
            msg = ("Filtered duplicate request: %(request)s"
                   " - no more duplicates will be shown"
                   " (see DUPEFILTER_DEBUG to show all duplicates)")
            logger.debug(msg % {'request': request.meta.get('dupefilter_msg') or request})
            self.logdupes = False

        # Increment the dupefilter/filtered stats counter
        # 增加dupefilter/filtered统计计数器
        spider.crawler.stats.inc_value('dupefilter/filtered', spider=spider)

    async def done(
            self,
            request: Request,
            done_type: Literal["request_ok", "request_err", "parse_ok", "parse_err"]
    ) -> None:
        """
        Control the removal of fingerprints based on the done_type status.
        根据done_type的状态控制指纹的移除。

        This method can be implemented by subclasses to handle the removal of
        fingerprints from the filter based on the status of the request processing.
        子类可以实现此方法，以根据请求处理的状态处理从过滤器中移除指纹。

        Args:
            request: The request that has been processed.
                    已处理的请求。
            done_type: The status of the request processing.
                      请求处理的状态。
                      Can be one of: "request_ok", "request_err", "parse_ok", "parse_err".
                      可以是以下之一："request_ok"、"request_err"、"parse_ok"、"parse_err"。
        """
        # Default implementation does nothing
        # 默认实现不执行任何操作
        pass
