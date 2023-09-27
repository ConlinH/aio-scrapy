"""
An extension to retry failed requests that are potentially caused by temporary
problems such as a connection timeout or HTTP 500 error.

You can change the behaviour of this middleware by modifing the scraping settings:
RETRY_TIMES - how many times to retry a failed page
RETRY_HTTP_CODES - which HTTP response codes to retry

Failed pages are collected on the scraping process and rescheduled at the end,
once the spider has finished crawling all regular (non failed) pages.
"""
from typing import Optional, Union

try:
    from asyncio.exceptions import TimeoutError
except:
    from concurrent.futures._base import TimeoutError

NEED_RETRY_ERROR = (TimeoutError, ConnectionRefusedError, IOError)

try:
    from aiohttp.client_exceptions import ClientError

    NEED_RETRY_ERROR += (ClientError,)
except ImportError:
    pass

try:
    from httpx import HTTPError as HttpxError

    NEED_RETRY_ERROR += (HttpxError,)
except ImportError:
    pass

try:
    from pyhttpx.exception import BaseExpetion as PyHttpxError

    NEED_RETRY_ERROR += (PyHttpxError,)
except ImportError:
    pass

try:
    from requests.exceptions import RequestException as RequestsError

    NEED_RETRY_ERROR += (RequestsError,)
except ImportError:
    pass

try:
    from playwright._impl._api_types import Error as PlaywrightError

    NEED_RETRY_ERROR += (PlaywrightError,)
except ImportError:
    pass

from aioscrapy.exceptions import NotConfigured
from aioscrapy.http.request import Request
from aioscrapy.spiders import Spider
from aioscrapy.utils.python import global_object_name
from aioscrapy.utils.log import logger as retry_logger


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
    使用了scrapy的retry，将日志等级改为info
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
            reason = global_object_name(reason.__class__)

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
    EXCEPTIONS_TO_RETRY = NEED_RETRY_ERROR

    def __init__(self, settings):
        if not settings.getbool('RETRY_ENABLED'):
            raise NotConfigured
        self.max_retry_times = settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status in self.retry_http_codes:
            reason = f"Retry response status code： {response.status}"
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        if (
                isinstance(exception, self.EXCEPTIONS_TO_RETRY)
                and not request.meta.get('dont_retry', False)
        ):
            return self._retry(request, exception, spider)

    def _retry(self, request, reason, spider):
        max_retry_times = request.meta.get('max_retry_times', self.max_retry_times)
        priority_adjust = request.meta.get('priority_adjust', self.priority_adjust)
        return get_retry_request(
            request,
            reason=reason,
            spider=spider,
            max_retry_times=max_retry_times,
            priority_adjust=priority_adjust,
        )
