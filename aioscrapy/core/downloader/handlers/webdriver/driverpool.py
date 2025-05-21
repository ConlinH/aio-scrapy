# -*- coding: utf-8 -*-
"""
WebDriver pool implementation for Playwright/DrissionPage browsers.
Playwright/DrissionPage浏览器的WebDriver池实现。

This module provides a pool of Playwright browser instances that can be reused
across multiple requests, improving performance by avoiding the overhead of
creating a new browser for each request.
此模块提供了一个Playwright浏览器实例池，可以在多个请求之间重用，
通过避免为每个请求创建新浏览器的开销来提高性能。
"""

from asyncio import Lock
from asyncio.queues import Queue

from aioscrapy.utils.tools import singleton


class WebDriverBase:

    async def setup(self):
        raise NotImplementedError

    async def quit(self):
        raise NotImplementedError


@singleton
class WebDriverPool:
    """
    A pool of WebDriver instances for Playwright browsers.
    Playwright浏览器的WebDriver实例池。

    This class manages a pool of browser instances that can be reused across
    multiple requests. It handles creation, retrieval, release, and cleanup
    of browser instances.
    此类管理一个可以在多个请求之间重用的浏览器实例池。它处理浏览器实例的
    创建、检索、释放和清理。

    The @singleton decorator ensures only one pool exists per process.
    @singleton装饰器确保每个进程只存在一个池。
    """

    def __init__(
            self,
            driver_cls: WebDriverBase,
            use_pool: bool = True,
            pool_size: int = 1,
            **kwargs
    ):
        """
        Initialize the WebDriverPool.
        初始化WebDriverPool。

        Args:
            use_pool: Whether to use pooling (True) or create a new browser for each request (False).
                     是否使用池化（True）或为每个请求创建新浏览器（False）。
            pool_size: Maximum number of browser instances to keep in the pool.
                      池中保留的最大浏览器实例数。
            driver_cls: The WebDriver class to instantiate.
                       要实例化的WebDriver类。
            **kwargs: Additional arguments to pass to the WebDriver constructor.
                     传递给WebDriver构造函数的其他参数。
        """
        self.use_pool = use_pool  # Whether to reuse browser instances
                                 # 是否重用浏览器实例
        self.pool_size = pool_size  # Maximum number of browsers in the pool
                                   # 池中的最大浏览器数量
        self.driver_cls = driver_cls  # WebDriver class to instantiate
                                     # 要实例化的WebDriver类
        self.kwargs = kwargs  # Arguments for WebDriver initialization
                             # WebDriver初始化的参数

        # Queue to store available browser instances
        # 存储可用浏览器实例的队列
        self.queue = Queue(maxsize=pool_size)
        # Lock to synchronize access to the pool
        # 用于同步访问池的锁
        self.lock = Lock()
        # Counter for active browser instances
        # 活动浏览器实例的计数器
        self.driver_count = 0

    @property
    def is_full(self):
        """
        Check if the pool has reached its maximum capacity.
        检查池是否已达到其最大容量。

        Returns:
            bool: True if the pool is full, False otherwise.
                 如果池已满，则为True，否则为False。
        """
        return self.driver_count >= self.pool_size

    async def create_driver(self, **kw):
        """
        Create a new WebDriver instance.
        创建一个新的WebDriver实例。

        This method instantiates a new browser with the specified arguments
        merged with the default arguments provided at pool initialization.
        此方法使用指定的参数与池初始化时提供的默认参数合并来实例化新的浏览器。

        Args:
            **args: Additional arguments to override the default WebDriver arguments.
                   用于覆盖默认WebDriver参数的其他参数。

        Returns:
            WebDriver: A new, initialized WebDriver instance.
                      一个新的、已初始化的WebDriver实例。
        """
        # Merge default arguments with request-specific arguments
        # 将默认参数与请求特定参数合并
        kwargs = self.kwargs.copy()
        kwargs.update(kw)

        # Create the driver instance
        # 创建驱动程序实例
        driver = self.driver_cls(**kwargs)

        # Initialize the browser
        # 初始化浏览器
        await driver.setup()

        return driver

    async def get(self, **kwargs):
        """
        Get a WebDriver instance from the pool.
        从池中获取WebDriver实例。

        This method either returns an existing browser from the pool or creates
        a new one if the pool is not full. It also handles browser recycling
        based on usage count to prevent performance degradation.
        此方法从池中返回现有浏览器，或者如果池未满则创建新浏览器。
        它还根据使用计数处理浏览器回收，以防止性能下降。

        Args:
            **kwargs: Additional arguments to pass to the WebDriver constructor if creating a new instance.
                     如果创建新实例，则传递给WebDriver构造函数的其他参数。

        Returns:
            WebDriver: A WebDriver instance ready for use.
                      准备使用的WebDriver实例。
        """
        # Synchronize access to the pool
        # 同步访问池
        async with self.lock:
            # If pooling is disabled, always create a new browser
            # 如果禁用池化，始终创建新浏览器
            if not self.use_pool:
                return await self.create_driver(**kwargs)

            # If the pool is not full, create a new browser
            # 如果池未满，创建新浏览器
            if not self.is_full:
                driver = await self.create_driver(**kwargs)
                self.driver_count += 1
            # Otherwise, get an existing browser from the queue
            # 否则，从队列中获取现有浏览器
            else:
                driver = await self.queue.get()

        # Handle browser recycling based on usage count
        # 根据使用计数处理浏览器回收
        # 如果driver达到指定使用次数，则销毁，重新启动一个driver（处理有些driver使用次数变多则变卡的情况）
        if driver.max_uses is not None:
            driver.max_uses -= 1
            if driver.max_uses <= 0:
                # Browser has reached its maximum usage count, recycle it
                # 浏览器已达到其最大使用计数，回收它
                await self.remove(driver)
                return await self.get(**kwargs)

        return driver

    async def release(self, driver):
        """
        Release a WebDriver instance back to the pool.
        将WebDriver实例释放回池中。

        If pooling is disabled, the browser is closed. Otherwise, it's
        returned to the pool for reuse.
        如果禁用池化，则关闭浏览器。否则，它将返回到池中以供重用。

        Args:
            driver: The WebDriver instance to release.
                   要释放的WebDriver实例。
        """
        # If pooling is disabled, close the browser
        # 如果禁用池化，关闭浏览器
        if not self.use_pool:
            await driver.quit()
            return

        # Otherwise, return it to the pool
        # 否则，将其返回到池中
        await self.queue.put(driver)

    async def remove(self, driver):
        """
        Remove a WebDriver instance from the pool.
        从池中移除WebDriver实例。

        This method closes the browser and decrements the driver count.
        此方法关闭浏览器并减少驱动程序计数。

        Args:
            driver: The WebDriver instance to remove.
                   要移除的WebDriver实例。
        """
        # Close the browser
        # 关闭浏览器
        await driver.quit()
        # Decrement the driver count
        # 减少驱动程序计数
        self.driver_count -= 1

    async def close(self):
        """
        Close all WebDriver instances in the pool.
        关闭池中的所有WebDriver实例。

        This method is called when the spider is closing. It closes all
        browser instances and resets the pool.
        当爬虫关闭时调用此方法。它关闭所有浏览器实例并重置池。
        """
        # Close all browsers in the pool
        # 关闭池中的所有浏览器
        while not self.queue.empty():
            driver = await self.queue.get()
            await driver.quit()
            self.driver_count -= 1
