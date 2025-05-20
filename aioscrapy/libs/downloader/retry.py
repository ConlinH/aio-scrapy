"""
Retry Middleware for AioScrapy
AioScrapy的重试中间件

An extension to retry failed requests that are potentially caused by temporary
problems such as a connection timeout or HTTP 500 error.
一个扩展，用于重试可能由临时问题（如连接超时或HTTP 500错误）导致的失败请求。

You can change the behavior of this middleware by modifying the scraping settings:
您可以通过修改抓取设置来更改此中间件的行为：

RETRY_ENABLED - whether to enable the retry middleware (default: True)
RETRY_ENABLED - 是否启用重试中间件（默认：True）

RETRY_TIMES - how many times to retry a failed page (default: 2)
RETRY_TIMES - 重试失败页面的次数（默认：2）

RETRY_HTTP_CODES - which HTTP response codes to retry (default: [500, 502, 503, 504, 522, 524, 408, 429])
RETRY_HTTP_CODES - 要重试的HTTP响应代码（默认：[500, 502, 503, 504, 522, 524, 408, 429]）

RETRY_PRIORITY_ADJUST - adjust retry request priority (default: -1)
RETRY_PRIORITY_ADJUST - 调整重试请求优先级（默认：-1）

Failed pages are collected during the scraping process and rescheduled,
allowing the spider to continue crawling other pages while retrying failed ones.
失败的页面在抓取过程中被收集并重新安排，
允许爬虫在重试失败页面的同时继续抓取其他页面。
"""
from typing import Optional, Union

from anyio import EndOfStream

try:
    from asyncio.exceptions import TimeoutError
except:
    from concurrent.futures._base import TimeoutError

from aioscrapy.exceptions import ProxyException, DownloadError, NotConfigured
from aioscrapy.http.request import Request
from aioscrapy.spiders import Spider
from aioscrapy.utils.log import logger as retry_logger
from aioscrapy.utils.python import global_object_name

# Tuple of exception types that should trigger a retry
# 应触发重试的异常类型元组
NEED_RETRY_ERROR = (TimeoutError, ConnectionRefusedError, IOError, ProxyException, DownloadError, EndOfStream)


def get_retry_request(
        request: Request,
        *,
        spider: Spider,
        reason: Union[str, Exception] = 'unspecified',
        max_retry_times: Optional[int] = None,
        priority_adjust: Optional[int] = None,
        logger=retry_logger,
        stats_base_key: str = 'retry',
):
    """
    Create a new request object to retry the specified failed request.
    创建一个新的请求对象来重试指定的失败请求。

    This function is based on Scrapy's retry functionality but uses INFO level
    logging instead of DEBUG level for retry attempts. It creates a copy of the
    original request with updated retry count and adjusted priority.
    此函数基于Scrapy的重试功能，但对重试尝试使用INFO级别的日志记录而不是DEBUG级别。
    它创建原始请求的副本，更新重试计数并调整优先级。

    Args:
        request: The original Request object that failed.
                失败的原始Request对象。
        spider: The spider instance that generated the request.
               生成请求的爬虫实例。
        reason: The reason for the retry, either a string or an exception.
               重试的原因，可以是字符串或异常。
               Defaults to 'unspecified'.
               默认为'unspecified'。
        max_retry_times: Maximum number of times to retry this request.
                        重试此请求的最大次数。
                        If None, uses the value from request.meta['max_retry_times']
                        or the RETRY_TIMES setting.
                        如果为None，则使用request.meta['max_retry_times']
                        或RETRY_TIMES设置中的值。
        priority_adjust: Amount to adjust the request priority.
                        调整请求优先级的数量。
                        If None, uses the value from request.meta['priority_adjust']
                        or the RETRY_PRIORITY_ADJUST setting.
                        如果为None，则使用request.meta['priority_adjust']
                        或RETRY_PRIORITY_ADJUST设置中的值。
        logger: The logger to use for logging retry attempts.
               用于记录重试尝试的日志记录器。
               Defaults to the retry_logger.
               默认为retry_logger。
        stats_base_key: The base key to use for recording retry statistics.
                       用于记录重试统计信息的基本键。
                       Defaults to 'retry'.
                       默认为'retry'。

    Returns:
        Request: A new Request object with updated retry count and priority,
                or None if max_retry_times has been reached.
                具有更新的重试计数和优先级的新Request对象，
                如果已达到max_retry_times，则为None。
    """
    settings = spider.crawler.settings
    stats = spider.crawler.stats
    retry_times = request.meta.get('retry_times', 0) + 1
    if max_retry_times is None:
        max_retry_times = request.meta.get('max_retry_times')
        if max_retry_times is None:
            max_retry_times = settings.getint('RETRY_TIMES')
    if retry_times <= max_retry_times:
        if callable(reason):
            reason = reason()
        if isinstance(reason, Exception):
            reason = global_object_name((getattr(reason, "real_error", None) or reason).__class__)

        logger.info(
            "Retrying %(request)s (failed %(retry_times)d times): %(reason)s" % {
                'request': request, 'retry_times': retry_times, 'reason': reason
            },
        )
        new_request = request.copy()
        new_request.meta['retry_times'] = retry_times
        new_request.dont_filter = True
        if priority_adjust is None:
            priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')
        new_request.priority = request.priority + priority_adjust

        stats.inc_value(f'{stats_base_key}/count')
        stats.inc_value(f'{stats_base_key}/reason_count/{reason}')
        return new_request
    else:
        stats.inc_value(f'{stats_base_key}/max_reached')
        logger.error(
            "Gave up retrying %(request)s (failed %(retry_times)d times): "
            "%(reason)s" % {'request': request, 'retry_times': retry_times, 'reason': reason}
        )
        return None


class RetryMiddleware:
    """
    Middleware to retry failed requests.
    重试失败请求的中间件。

    This middleware retries requests that have failed due to temporary issues
    such as connection problems or certain HTTP error codes. It works by
    intercepting responses with error status codes and exceptions, then
    creating new retry requests with updated retry counts.
    此中间件重试由于临时问题（如连接问题或某些HTTP错误代码）而失败的请求。
    它通过拦截具有错误状态代码和异常的响应，然后创建具有更新的重试计数的新重试请求来工作。
    """

    # List of exceptions that should trigger a retry
    # 应触发重试的异常列表
    EXCEPTIONS_TO_RETRY = NEED_RETRY_ERROR

    def __init__(self, settings):
        """
        Initialize the RetryMiddleware.
        初始化RetryMiddleware。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。

        Raises:
            NotConfigured: If RETRY_ENABLED is False.
                          如果RETRY_ENABLED为False。
        """
        if not settings.getbool('RETRY_ENABLED'):
            raise NotConfigured
        self.max_retry_times = settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a RetryMiddleware instance from a crawler.
        从爬虫创建RetryMiddleware实例。

        This is the factory method used by AioScrapy to create middleware instances.
        这是AioScrapy用于创建中间件实例的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            RetryMiddleware: A new RetryMiddleware instance.
                            一个新的RetryMiddleware实例。
        """
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        """
        Process a response to check if it needs to be retried.
        处理响应以检查是否需要重试。

        This method checks if the response status code is in the list of
        status codes that should be retried. If so, it creates a retry request.
        此方法检查响应状态代码是否在应重试的状态代码列表中。
        如果是，则创建重试请求。

        Args:
            request: The original request that generated the response.
                    生成响应的原始请求。
            response: The response to process.
                     要处理的响应。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            Response or Request: The original response or a new retry request.
                                原始响应或新的重试请求。
        """
        # Don't retry if the request has dont_retry set to True
        # 如果请求的dont_retry设置为True，则不重试
        if request.meta.get('dont_retry', False):
            return response

        # Retry if the status code is in the list of codes to retry
        # 如果状态代码在要重试的代码列表中，则重试
        if response.status in self.retry_http_codes:
            reason = f"Retry response status code： {response.status}"
            return self._retry(request, reason, spider) or response

        # Otherwise, return the response as is
        # 否则，按原样返回响应
        return response

    def process_exception(self, request, exception, spider):
        """
        Process an exception to check if the request should be retried.
        处理异常以检查是否应重试请求。

        This method checks if the exception is in the list of exceptions
        that should trigger a retry. If so, it creates a retry request.
        此方法检查异常是否在应触发重试的异常列表中。
        如果是，则创建重试请求。

        Args:
            request: The request that caused the exception.
                    导致异常的请求。
            exception: The exception that was raised.
                      引发的异常。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            Request or None: A new retry request or None if the request should not be retried.
                            新的重试请求，如果不应重试请求，则为None。
        """
        # Retry if the exception is in the list of exceptions to retry
        # and the request doesn't have dont_retry set to True
        # 如果异常在要重试的异常列表中，并且请求的dont_retry未设置为True，则重试
        if (
                isinstance(exception, self.EXCEPTIONS_TO_RETRY)
                and not request.meta.get('dont_retry', False)
        ):
            return self._retry(request, exception, spider)

        # Otherwise, return None to let the exception be processed by other middleware
        # 否则，返回None以让异常被其他中间件处理
        return None

    def _retry(self, request, reason, spider):
        """
        Create a retry request for the given request.
        为给定请求创建重试请求。

        This internal method gets the retry parameters from the request metadata
        or middleware settings, then calls get_retry_request to create a new request.
        此内部方法从请求元数据或中间件设置获取重试参数，
        然后调用get_retry_request创建新请求。

        Args:
            request: The original request to retry.
                    要重试的原始请求。
            reason: The reason for the retry (string or exception).
                   重试的原因（字符串或异常）。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            Request or None: A new retry request or None if max retries has been reached.
                            新的重试请求，如果已达到最大重试次数，则为None。
        """
        # Get retry parameters from request metadata or middleware settings
        # 从请求元数据或中间件设置获取重试参数
        max_retry_times = request.meta.get('max_retry_times', self.max_retry_times)
        priority_adjust = request.meta.get('priority_adjust', self.priority_adjust)

        # Create and return a retry request
        # 创建并返回重试请求
        return get_retry_request(
            request,
            reason=reason,
            spider=spider,
            max_retry_times=max_retry_times,
            priority_adjust=priority_adjust,
        )
