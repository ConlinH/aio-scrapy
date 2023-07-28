import logging
from abc import ABCMeta, abstractmethod

from aioscrapy.utils.python import global_object_name

logger = logging.getLogger('aioscrapy.proxy')


class AbsProxy(metaclass=ABCMeta):
    def __init__(self, settings):
        self.use_proxy = settings.getbool('USE_PROXY', False)
        self.max_count = settings.getint('PROXY_MAX_COUNT', 16)
        self.min_count = settings.getint('PROXY_MIN_COUNT', 1)
        self.allow_status_code = settings.get('PROXY_ALLOW_STATUS_CODE', [404])
        self.cache = []

    async def add_proxy(self, request):
        """add proxy for request"""
        if self.use_proxy and request.use_proxy:
            request.meta['proxy'] = await self.get()
        else:
            request.meta.pop('proxy', None)
        return request

    def remove(self, proxy, reason=None):
        if callable(reason):
            reason = reason()
        if isinstance(reason, Exception):
            reason = global_object_name(reason.__class__)

        if proxy in self.cache:
            logger.info(f"remove proxy: {proxy}, reason: {reason}")
            self.cache.remove(proxy)

    def check(self, request, response=None, exception=None):
        if not self.use_proxy:
            return

        if response and response.status >= 400 and response.status not in self.allow_status_code:
            self.remove(request.meta['proxy'], f"Don't allow response status code:{response.status}")

        if exception and isinstance(exception, BaseException):
            self.remove(request.meta['proxy'], exception)

    @classmethod
    @abstractmethod
    async def from_crawler(cls, crawler) -> "AbsProxy":
        """get proxy instance from spider"""

    @abstractmethod
    async def get(self) -> str:
        """get proxy"""
