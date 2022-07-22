import asyncio
import logging
import time
from abc import ABCMeta, abstractmethod
from typing import Optional

from aioscrapy.db import db_manager
from aioscrapy.utils.python import global_object_name

logger = logging.getLogger('aioscrapy.proxy')


class AbsProxy(metaclass=ABCMeta):
    def __init__(self, settings):
        self.use_proxy = settings.getbool('USE_PROXY', False)
        self.max_count = settings.getint('PROXY_MAX_COUNT', 16)
        self.min_count = settings.getint('PROXY_MIN_COUNT', 1)
        self.allow_status_code = settings.get('PROXY_ALLOW_STATUS_CODE', [200, 404, 302, 307])
        self.cache = []

    async def add_proxy(self, request):
        """add proxy for request"""
        if self.use_proxy:
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

        if response and response.status not in self.allow_status_code:
            self.remove(request.meta['proxy'], f'无效状态码:{response.status}')

        if exception and isinstance(exception, BaseException):
            self.remove(request.meta['proxy'], exception)

    @classmethod
    @abstractmethod
    async def from_crawler(cls, crawler) -> "AbsProxy":
        """get proxy instance from spider"""

    @abstractmethod
    async def get(self) -> str:
        """get proxy"""


class RedisProxy(AbsProxy):
    def __init__(
            self,
            settings,
            proxy_queue: Optional["Redis"] = None,
            proxy_key: Optional[str] = None
    ):
        super().__init__(settings)
        self.proxy_queue = proxy_queue
        self.proxy_key = proxy_key
        self.lock = asyncio.Lock()

    @classmethod
    async def from_crawler(cls, crawler) -> "RedisProxy":
        settings = crawler.settings
        proxy_key = settings.get('PROXY_KEY')
        assert proxy_key is not None, f"未配置代理得key值：'ROXY_KEY'"
        alias = settings.get("PROXY_QUEUE_ALIAS", 'proxy')
        proxy_queue = db_manager.redis(alias)
        return cls(
            settings,
            proxy_queue=proxy_queue,
            proxy_key=proxy_key
        )

    async def fill_proxy(self, redis_key: str, count: int) -> None:
        script = f"""
            local redis_key = KEYS[1]
            local min_score = ARGV[1]
            local max_score = ARGV[2]
            local num = redis.call('ZCOUNT', redis_key, min_score, max_score)
            local start = 0
            if num>{count} then
                math.randomseed({time.time() * 1000})
                start = math.random(0, num-{count})
            end
            return redis.call('ZRANGEBYSCORE', redis_key, min_score, max_score, 'LIMIT', start, {count})
        """
        cmd_script = self.proxy_queue.register_script(script)
        result = await cmd_script(keys=[redis_key], args=[100, 100])
        if not result:
            result = await cmd_script(keys=[redis_key], args=[0, 100])
        proxies = [f'http://{ip.decode()}' for ip in result]
        self.cache.extend(proxies)
        logger.info(f'Get proxy from redis: {proxies}')

    async def get(self) -> str:
        if len(self.cache) < self.min_count:
            async with self.lock:
                len(self.cache) < self.min_count and await self.fill_proxy(self.proxy_key, self.max_count - len(self.cache))
        proxy = self.cache.pop(0)
        self.cache.append(proxy)
        return proxy
