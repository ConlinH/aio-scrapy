"""
Redis-based proxy implementation for aioscrapy.
aioscrapy的基于Redis的代理实现。

This module provides a Redis-based implementation of the proxy handler interface.
It fetches proxies from a Redis sorted set and manages them for use in requests.
此模块提供了代理处理程序接口的基于Redis的实现。
它从Redis有序集合中获取代理，并管理它们以用于请求。
"""

import asyncio
import time
from typing import Optional, Any

from aioscrapy.db import db_manager
from aioscrapy.exceptions import ProxyException
from aioscrapy.proxy import AbsProxy
from aioscrapy.utils.log import logger
from aioscrapy.utils.tools import create_task


class RedisProxy(AbsProxy):
    """
    Redis-based proxy handler implementation.
    基于Redis的代理处理程序实现。

    This class implements the AbsProxy interface using Redis as a backend.
    It fetches proxies from a Redis sorted set and manages them for use in requests.
    此类使用Redis作为后端实现AbsProxy接口。
    它从Redis有序集合中获取代理，并管理它们以用于请求。

    Attributes:
        crawler: The crawler instance.
                爬虫实例。
        proxy_queue: The Redis client used to fetch proxies.
                    用于获取代理的Redis客户端。
        proxy_key: The key of the Redis sorted set containing proxies.
                  包含代理的Redis有序集合的键。
        lock: An asyncio lock to prevent concurrent proxy fetching.
             防止并发代理获取的asyncio锁。
    """

    def __init__(
            self,
            settings,
            crawler,
            proxy_queue: Optional[Any] = None,
            proxy_key: Optional[str] = None
    ):
        """
        Initialize the Redis proxy handler.
        初始化Redis代理处理程序。

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。
            crawler: The crawler instance.
                    爬虫实例。
            proxy_queue: The Redis client used to fetch proxies.
                        用于获取代理的Redis客户端。
            proxy_key: The key of the Redis sorted set containing proxies.
                      包含代理的Redis有序集合的键。
        """
        super().__init__(settings)
        self.crawler = crawler
        self.proxy_queue = proxy_queue
        self.proxy_key = proxy_key
        self.lock = asyncio.Lock()

    @classmethod
    async def from_crawler(cls, crawler) -> "RedisProxy":
        """
        Create a RedisProxy instance from a crawler.
        从爬虫创建RedisProxy实例。

        This class method creates a RedisProxy instance from a crawler.
        It retrieves the necessary settings and initializes the Redis client.
        此类方法从爬虫创建RedisProxy实例。
        它检索必要的设置并初始化Redis客户端。

        Args:
            crawler: The crawler instance.
                    爬虫实例。

        Returns:
            RedisProxy: A RedisProxy instance.
                       RedisProxy实例。

        Raises:
            AssertionError: If PROXY_KEY is not configured in settings.
                           如果在设置中未配置PROXY_KEY。
        """
        # Get settings from crawler
        # 从爬虫获取设置
        settings = crawler.settings

        # Get proxy key from settings
        # 从设置获取代理键
        proxy_key = settings.get('PROXY_KEY')
        assert proxy_key is not None, "Not configured：'PROXY_KEY'"

        # Get Redis alias from settings, default to 'proxy'
        # 从设置获取Redis别名，默认为'proxy'
        alias = settings.get("PROXY_QUEUE_ALIAS", 'proxy')

        # Get Redis client
        # 获取Redis客户端
        proxy_queue = db_manager.redis(alias)

        # Create and return RedisProxy instance
        # 创建并返回RedisProxy实例
        return cls(
            settings,
            crawler,
            proxy_queue=proxy_queue,
            proxy_key=proxy_key
        )

    async def fill_proxy(self, redis_key: str, count: int) -> None:
        """
        Fill the proxy cache from Redis.
        从Redis填充代理缓存。

        This method fetches proxies from a Redis sorted set and adds them to the cache.
        It uses a Lua script to randomly select proxies from the sorted set.
        此方法从Redis有序集合中获取代理并将它们添加到缓存中。
        它使用Lua脚本从有序集合中随机选择代理。

        Args:
            redis_key: The key of the Redis sorted set containing proxies.
                      包含代理的Redis有序集合的键。
            count: The number of proxies to fetch.
                  要获取的代理数量。
        """
        # Lua script to randomly select proxies from a sorted set
        # Lua脚本，用于从有序集合中随机选择代理
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
        # Register and execute the script
        # 注册并执行脚本
        cmd_script = self.proxy_queue.register_script(script)

        # Try to get proxies with score between 100 and 100 (high quality proxies)
        # 尝试获取分数在100到100之间的代理（高质量代理）
        result = await cmd_script(keys=[redis_key], args=[100, 100])

        # If no high quality proxies are available, get any proxies
        # 如果没有高质量代理可用，获取任何代理
        if not result:
            result = await cmd_script(keys=[redis_key], args=[0, 100])

        # Format proxies and add them to the cache
        # 格式化代理并将它们添加到缓存中
        proxies = [ip.decode() if ip.decode().startswith('http') else f'http://{ip.decode()}' for ip in result]
        self.cache.extend(proxies)
        logger.info(f'Get proxy from redis: {proxies}')

    async def get(self) -> str:
        """
        Get a proxy from the cache.
        从缓存中获取代理。

        This method returns a proxy from the cache. If the cache is running low,
        it fills the cache with more proxies from Redis. If no proxies are available,
        it stops the crawler and raises an exception.
        此方法从缓存中返回代理。如果缓存不足，它会从Redis中填充更多代理到缓存中。
        如果没有可用的代理，它会停止爬虫并引发异常。

        Returns:
            str: A proxy string in the format 'scheme://host:port'.
                 格式为'scheme://host:port'的代理字符串。

        Raises:
            ProxyException: If no proxies are available.
                           如果没有可用的代理。
        """
        # If the cache is running low, fill it with more proxies
        # 如果缓存不足，用更多代理填充它
        if len(self.cache) < self.min_count:
            async with self.lock:
                # Check again inside the lock to avoid race conditions
                # 在锁内再次检查以避免竞争条件
                len(self.cache) < self.min_count and await self.fill_proxy(self.proxy_key, self.max_count - len(self.cache))

        try:
            # Get a proxy from the cache and move it to the end
            # 从缓存中获取代理并将其移到末尾
            proxy = self.cache.pop(0)
            self.cache.append(proxy)
            return proxy
        except IndexError:
            # If no proxies are available, stop the crawler and raise an exception
            # 如果没有可用的代理，停止爬虫并引发异常
            logger.warning("Not available proxy, Closing spider")
            create_task(self.crawler.engine.stop(reason="Not available proxy"))
            raise ProxyException("Not available proxy")
