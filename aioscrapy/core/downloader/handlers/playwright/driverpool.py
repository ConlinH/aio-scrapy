# -*- coding: utf-8 -*-

from asyncio import Lock
from asyncio.queues import Queue

from aioscrapy.utils.tools import singleton


@singleton
class WebDriverPool:
    def __init__(
            self, pool_size=5, driver_cls=None, **kwargs
    ):
        self.pool_size = pool_size
        self.driver_cls = driver_cls
        self.kwargs = kwargs

        self.queue = Queue(maxsize=pool_size)
        self.lock = Lock()
        self.driver_count = 0

    @property
    def is_full(self):
        return self.driver_count >= self.pool_size

    async def create_driver(self, **args):
        kwargs = self.kwargs.copy()
        kwargs.update(args)
        driver = self.driver_cls(**kwargs)
        await driver.setup()
        return driver

    async def get(self, **kwargs):
        async with self.lock:
            if not self.is_full:
                driver = await self.create_driver(**kwargs)
                self.driver_count += 1
            else:
                driver = await self.queue.get()
        return driver

    async def release(self, driver):
        await self.queue.put(driver)

    async def remove(self, driver):
        await driver.quit()
        self.driver_count -= 1

    async def close(self):
        while not self.queue.empty():
            driver = await self.queue.get()
            await driver.quit()
            self.driver_count -= 1
