# _*_ coding: utf-8 _*_

import asyncio
import logging
from typing import Optional, AsyncGenerator, Union, Callable
from asyncio import Queue
from asyncio.queues import QueueEmpty

import aioscrapy
from aioscrapy import Spider
from aioscrapy import signals
from aioscrapy.core.downloader import DownloaderTV
from aioscrapy.core.scheduler import BaseScheduler
from aioscrapy.core.scraper import Scraper
from aioscrapy.exceptions import DontCloseSpider
from aioscrapy.http import Response
from aioscrapy.http.request import Request
from aioscrapy.utils.log import logformatter_adapter
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper

logger = logging.getLogger(__name__)


class Slot:

    def __init__(self, start_requests: Optional[AsyncGenerator]) -> None:
        self.inprogress: set[Request] = set()  # requests in progress
        self.start_requests = start_requests
        self.lock: bool = False

    def add_request(self, request: Request) -> None:
        self.inprogress.add(request)

    def remove_request(self, request: Request) -> None:
        self.inprogress.remove(request)


class ExecutionEngine(object):

    def __init__(self, crawler: "aioscrapy.Crawler") -> None:
        self.crawler = crawler
        self.settings = crawler.settings
        self.signals = crawler.signals
        self.logformatter = crawler.logformatter

        self.enqueue_cache_num = self.settings.getint("ENQUEUE_CACHE_NUM")
        self.enqueue_cache: Queue = Queue(self.enqueue_cache_num)
        self.slot: Optional[Slot] = None
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderTV] = None
        self.scraper: Optional[Scraper] = None
        self.scheduler: Optional[BaseScheduler] = None

        self.running: bool = False
        self.unlock: bool = True
        self.finish: bool = False
        self.enqueue_unlock: bool = True

    async def start(
            self,
            spider: Spider,
            start_requests: Optional[AsyncGenerator] = None
    ) -> None:
        """Start the execution engine"""
        if self.running:
            raise RuntimeError("Engine already running")

        self.running = True
        await self.signals.send_catch_log_deferred(signal=signals.engine_started)
        await self.open(spider, start_requests)
        while not self.finish:
            self.running and await self._next_request()
            await asyncio.sleep(1)
            self.enqueue_cache_num != 1 and asyncio.create_task(self._crawl())
            self.running and await self._spider_idle(self.spider)

    async def stop(self, reason: str = 'shutdown') -> None:
        """Stop the execution engine gracefully"""
        if not self.running:
            raise RuntimeError("Engine not running")
        self.running = False

        while not self.is_idle():
            await asyncio.sleep(0.2)
            self.enqueue_cache_num != 1 and asyncio.create_task(self._crawl())
        await self.close_spider(self.spider, reason=reason)
        await self.signals.send_catch_log_deferred(signal=signals.engine_stopped)
        self.finish = True

    async def open(
            self,
            spider: Spider,
            start_requests: Optional[AsyncGenerator] = None
    ) -> None:
        logger.info("Spider opened", extra={'spider': spider})

        self.spider = spider
        await call_helper(self.crawler.stats.open_spider, spider)

        self.scheduler = await load_instance(self.settings['SCHEDULER'], crawler=self.crawler)
        self.downloader = await load_instance(self.settings['DOWNLOADER'], crawler=self.crawler)
        self.scraper = await call_helper(Scraper.from_crawler, self.crawler)

        start_requests = await call_helper(self.scraper.spidermw.process_start_requests, start_requests, spider)
        self.slot = Slot(start_requests)

        await self.signals.send_catch_log_deferred(signals.spider_opened, spider=spider)

    async def close(self) -> None:
        """Close the execution engine gracefully.

        If it has already been started, stop it. In all cases, close all spiders
        and the downloader.
        """
        if self.running:
            # Will also close spiders and downloader
            await self.stop()
        elif self.spider:
            # Will also close downloader
            await self.close_spider(self.spider, reason='shutdown')
        else:
            self.downloader.close()

    async def _next_request(self) -> None:
        assert self.slot is not None  # typing
        assert self.spider is not None  # typing

        while self.unlock and not self._needs_backout() and self.unlock:
            self.unlock = False
            try:
                async for request in self.scheduler.next_request(self.downloader.total_concurrency):
                    if request:
                        self.slot.add_request(request)
                        await self.downloader.fetch(request)
                break
            finally:
                self.unlock = True

        if self.slot.start_requests and not self._needs_backout() and not self.slot.lock:
            self.slot.lock = True
            try:
                request = await self.slot.start_requests.__anext__()
            except StopAsyncIteration:
                self.slot.start_requests = None
            except Exception as e:
                self.slot.start_requests = None
                logger.error('Error while obtaining start requests', exc_info=e, extra={'spider': self.spider})
            else:
                request and await self.crawl(request)
            finally:
                self.slot.lock = False

    def _needs_backout(self) -> bool:
        return (
                not self.running
                or self.downloader.needs_backout()
                or self.scraper.needs_backout()
        )

    async def handle_downloader_output(
            self, result: Union[Request, Response, BaseException, None], request: Request
    ) -> None:
        try:
            if result is None:
                return

            if not isinstance(result, (Request, Response, BaseException)):
                raise TypeError(
                    "Incorrect type: expected Request, Response or Failure, got %s: %r"
                    % (type(result), result)
                )

            if isinstance(result, Request):
                await self.crawl(result)
                return

            result.request = request
            if isinstance(result, Response):
                logkws = self.logformatter.crawled(request, result, self.spider)
                if logkws is not None:
                    logger.log(*logformatter_adapter(logkws), extra={'spider': self.spider})
                await self.signals.send_catch_log(signals.response_received,
                                                  response=result, request=request, spider=self.spider)
            await self.scraper.enqueue_scrape(result, request)

        finally:
            self.slot.remove_request(request)
            await self._next_request()

    def is_idle(self) -> bool:

        if self.downloader.active:
            # downloader has pending requests
            return False

        if self.slot.inprogress:
            # not all start requests are handled
            return False

        if not self.scraper.is_idle():
            # scraper is not idle
            return False

        return True

    async def crawl(self, request: Request) -> None:
        if self.enqueue_cache_num == 1:
            await self.scheduler.enqueue_request(request)
            asyncio.create_task(self._next_request())
        else:
            await self.enqueue_cache.put(request)

    async def _crawl(self) -> None:
        if not self.enqueue_unlock:
            return
        self.enqueue_unlock = False
        requests = []
        for _ in range(self.enqueue_cache.qsize()):
            try:
                request = self.enqueue_cache.get_nowait()
                requests.append(request)
            except QueueEmpty:
                break
        if requests:
            await call_helper(self.scheduler.enqueue_request_batch, requests)
            asyncio.create_task(self._next_request())
        self.enqueue_unlock = True

    async def close_spider(self, spider: Spider, reason: str = 'cancelled') -> None:
        """Close (cancel) spider and clear all its outstanding requests"""

        logger.info("Closing spider (%(reason)s)",
                    {'reason': reason},
                    extra={'spider': spider})

        async def close_handler(
                callback: Callable,
                *args,
                errmsg: str = '',
                **kwargs
        ) -> None:
            try:
                await call_helper(callback, *args, **kwargs)
            except (Exception, BaseException) as e:
                logger.error(
                    errmsg,
                    exc_info=e,
                    extra={'spider': spider}
                )

        await close_handler(self.downloader.close, errmsg='Downloader close failure')

        await close_handler(self.scraper.close, errmsg='Scraper close failure')

        await close_handler(self.scheduler.close, reason, errmsg='Scheduler close failure')

        await close_handler(self.signals.send_catch_log_deferred, signal=signals.spider_closed, spider=spider,
                            reason=reason, errmsg='Error while sending spider_close signal')

        await close_handler(self.crawler.stats.close_spider, spider, reason=reason, errmsg='Stats close failure')

        logger.info("Spider closed (%(reason)s)", {'reason': reason}, extra={'spider': spider})

        await close_handler(setattr, self, 'slot', None, errmsg='Error while unassigning slot')

        await close_handler(setattr, self, 'spider', None, errmsg='Error while unassigning spider')

    async def _spider_idle(self, spider: Spider) -> None:
        assert self.spider is not None
        res = await self.signals.send_catch_log(signals.spider_idle, spider=spider, dont_log=DontCloseSpider)
        if any(isinstance(x, DontCloseSpider) for _, x in res):
            return

        # method of 'has_pending_requests' has IO, so method of 'is_idle' execute twice
        if self.is_idle() \
                and self.slot.start_requests is None \
                and self.enqueue_unlock and self.enqueue_cache.empty() \
                and not await self.scheduler.has_pending_requests() \
                and self.is_idle():
            await self.stop(reason='finished')
