import asyncio
import time
from typing import Optional

from aioscrapy.db import db_manager
from aioscrapy.proxy import AbsProxy
from aioscrapy.utils.log import logger


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
        assert proxy_key is not None, "Not configured：'PROXY_KEY'"
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
        proxies = [ip.decode() if ip.decode().startswith('http') else f'http://{ip.decode()}' for ip in result]
        self.cache.extend(proxies)
        logger.info(f'Get proxy from redis: {proxies}')

    async def get(self) -> str:
        if len(self.cache) < self.min_count:
            async with self.lock:
                len(self.cache) < self.min_count and await self.fill_proxy(self.proxy_key, self.max_count - len(self.cache))
        proxy = self.cache.pop(0)
        self.cache.append(proxy)
        return proxy
