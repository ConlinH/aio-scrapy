# _*_ coding: utf-8 _*_

import asyncio
import logging
from time import time

from aioscrapy import signals
from aioscrapy.exceptions import DontCloseSpider
from aioscrapy.http import Response
from aioscrapy.http.request import Request
from aioscrapy.utils.log import (
    logformatter_adapter)
from aioscrapy.utils.misc import load_object

from aioscrapy.utils.tools import call_helper
from aioscrapy.db import db_manager

from .scraper import Scraper

logger = logging.getLogger(__name__)


class Slot:

    def __init__(self, start_requests, close_if_idle, scheduler):
        self.closing = None
        self.inprogress = set()  # requests in progress

        self.start_requests = start_requests
        self.doing_start_requests = False
        self.close_if_idle = close_if_idle
        self.scheduler = scheduler
        self.heartbeat = None

    def add_request(self, request):
        self.inprogress.add(request)

    def remove_request(self, request):
        self.inprogress.remove(request)
        self._maybe_fire_closing()

    async def close(self):
        self.closing = asyncio.Future()
        self._maybe_fire_closing()
        await self.closing

    def _maybe_fire_closing(self):
        if self.closing and not self.inprogress:
            if self.heartbeat:
                self.heartbeat.cancel()
            self.closing.set_result(None)


class ExecutionEngine(object):

    def __init__(self, crawler, spider_closed_callback):
        self.lock = True
        self.start_time = time()
        self.crawler = crawler
        self.settings = crawler.settings
        self.signals = crawler.signals
        self.logformatter = crawler.logformatter
        self.slot = None
        self.spider = None
        self.scheduler = None
        self.running = False
        self.paused = False
        self.closing = False
        self.scheduler_cls = load_object(self.settings['SCHEDULER'])
        downloader_cls = load_object(self.settings['DOWNLOADER'])
        self.downloader = downloader_cls(crawler)
        self.scraper = Scraper(crawler)
        self._spider_closed_callback = spider_closed_callback

    async def start(self, spider, start_requests=None):
        """Start the execution engine"""
        if self.running:
            raise RuntimeError("Engine already running")

        # 创建所有数据库链接
        await db_manager.from_crawler(spider)

        self.start_time = time()
        await self.signals.send_catch_log_deferred(signal=signals.engine_started)
        self.running = True
        self._closewait = asyncio.Future()
        await self.open_spider(spider, start_requests, close_if_idle=True)
        await self._closewait

    async def stop(self):
        """Stop the execution engine gracefully"""
        if not self.running:
            raise RuntimeError("Engine not running")
        self.running = False
        await self._close_all_spiders()
        await self.signals.send_catch_log_deferred(signal=signals.engine_stopped)
        self._closewait.set_result(None)

    async def close(self):
        """Close the execution engine gracefully.

        If it has already been started, stop it. In all cases, close all spiders
        and the downloader.
        """
        if self.running:
            # Will also close spiders and downloader
            await self.stop()
        elif self.open_spiders:
            # Will also close downloader
            await self._close_all_spiders()
        else:
            self.downloader.close()

    def pause(self):
        """Pause the execution engine"""
        self.paused = True

    def unpause(self):
        """Resume the execution engine"""
        self.paused = False

    async def _next_request(self, spider):
        slot = self.slot
        if not slot:
            return

        if self.paused:
            return

        while self.lock and not self._needs_backout(spider) and self.lock:
            self.lock = False
            try:
                request = await call_helper(slot.scheduler.next_request)
                if not request:
                    break
                slot.add_request(request)
                await self.downloader.fetch(request, spider, self._handle_downloader_output)
            finally:
                self.lock = True

        if slot.start_requests and not self._needs_backout(spider) and not slot.doing_start_requests:
            slot.doing_start_requests = True
            try:
                request = await slot.start_requests.__anext__()
            except StopAsyncIteration:
                slot.start_requests = None
            except Exception:
                slot.start_requests = None
                logger.error('Error while obtaining start requests',
                             exc_info=True, extra={'spider': spider})
            else:
                request and await self.crawl(request, spider)
            finally:
                slot.doing_start_requests = False

        if self.running and await self.spider_is_idle(spider) and slot.close_if_idle:
            await self._spider_idle(spider)

    def _needs_backout(self, spider):
        return (
                not self.running
                or self.slot.closing
                or self.downloader.needs_backout()
                or self.scraper.slot.needs_backout()
        )

    async def _handle_downloader_output(self, result, request, spider):
        try:
            if not isinstance(result, (Request, Response, Exception, BaseException)):
                raise TypeError(
                    "Incorrect type: expected Request, Response or Failure, got %s: %r"
                    % (type(result), result)
                )

            if isinstance(result, Request):
                await self.crawl(result, spider)
                return

            if isinstance(result, Response):
                result.request = request
                logkws = self.logformatter.crawled(request, result, spider)
                if logkws is not None:
                    logger.log(*logformatter_adapter(logkws), extra={'spider': spider})
                await self.signals.send_catch_log(signals.response_received,
                                                  response=result, request=request, spider=spider)

        finally:
            self.slot.remove_request(request)
            asyncio.create_task(self._next_request(self.spider))
        await self.scraper.enqueue_scrape(result, request, spider)

    async def spider_is_idle(self, spider):
        if self.closing:
            return False

        if not self.scraper.slot.is_idle():
            # scraper is not idle
            return False

        if self.downloader.active:
            # downloader has pending requests
            return False

        if self.slot.start_requests is not None:
            # not all start requests are handled
            return False

        if self.slot.inprogress:
            # not requests are handled
            return False

        if await self.slot.scheduler.has_pending_requests():
            # scheduler has pending requests
            return False

        if self.downloader.active:
            # downloader has pending requests
            return False

        return True

    @property
    def open_spiders(self):
        return (self.spider,) if self.spider else set()

    def has_capacity(self):
        """Does the engine have capacity to handle more spiders"""
        return not bool(self.slot)

    async def crawl(self, request, spider):
        if spider not in self.open_spiders:
            raise RuntimeError("Spider %r not opened when crawling: %s" % (spider.name, request))

        await self.signals.send_catch_log(signals.request_scheduled, request=request, spider=spider)
        if not await call_helper(self.slot.scheduler.enqueue_request, request):
            await self.signals.send_catch_log(signals.request_dropped, request=request, spider=spider)
        else:
            asyncio.create_task(self._next_request(spider))

    async def open_spider(self, spider, start_requests=None, close_if_idle=True):
        if not self.has_capacity():
            raise RuntimeError("No free spider slot when opening %r" % spider.name)
        logger.info("Spider opened", extra={'spider': spider})
        scheduler = await call_helper(self.scheduler_cls.from_crawler, self.crawler)
        start_requests = await call_helper(self.scraper.spidermw.process_start_requests, start_requests, spider)
        self.slot = Slot(start_requests, close_if_idle, scheduler)
        self.spider = spider
        await call_helper(scheduler.open, spider)
        await call_helper(self.scraper.open_spider, spider)
        await call_helper(self.crawler.stats.open_spider, spider)
        await self.signals.send_catch_log_deferred(signals.spider_opened, spider=spider)
        asyncio.create_task(self._next_request(spider))
        self.slot.heartbeat = asyncio.create_task(self.heart_beat(1, spider, self.slot))

    async def _close_all_spiders(self):
        dfds = [self.close_spider(s, reason='shutdown') for s in self.open_spiders]
        await asyncio.gather(*dfds)

    async def close_spider(self, spider, reason='cancelled'):
        """Close (cancel) spider and clear all its outstanding requests"""
        if self.closing:
            return
        self.closing = True

        slot = self.slot
        if slot.closing:
            return slot.closing
        logger.info("Closing spider (%(reason)s)",
                    {'reason': reason},
                    extra={'spider': spider})

        await slot.close()

        async def close_handler(callback, *args, errmsg='', **kwargs):
            try:
                await call_helper(callback, *args, **kwargs)
            except (Exception, BaseException) as e:
                logger.error(
                    errmsg,
                    exc_info=e,
                    extra={'spider': spider}
                )

        await close_handler(self.downloader.close, errmsg='Downloader close failure')

        await close_handler(self.scraper.close_spider, spider, errmsg='Scraper close failure')

        await close_handler(self.slot.scheduler.close, reason, errmsg='Scheduler close failure')

        await close_handler(self.signals.send_catch_log_deferred, signal=signals.spider_closed, spider=spider,
                            reason=reason, errmsg='Error while sending spider_close signal')

        await close_handler(self.crawler.stats.close_spider, spider, reason=reason, errmsg='Stats close failure')

        logger.info("Spider closed (%(reason)s)", {'reason': reason}, extra={'spider': spider})

        await close_handler(setattr, self, 'slot', None, errmsg='Error while unassigning slot')

        await close_handler(setattr, self, 'spider', None, errmsg='Error while unassigning spider')

        await self._spider_closed_callback()

    async def _spider_idle(self, spider):
        """Called when a spider gets idle. This function is called when there
        are no remaining pages to download or schedule. It can be called
        multiple times. If some extension raises a DontCloseSpider exception
        (in the spider_idle signal handler) the spider is not closed until the
        next loop and this function is guaranteed to be called (at least) once
        again for this spider.
        """
        res = await self.signals.send_catch_log(signals.spider_idle, spider=spider, dont_log=DontCloseSpider)
        if any(isinstance(x, DontCloseSpider) for _, x in res):
            return

        if await self.spider_is_idle(spider):
            await self.close_spider(spider, reason='finished')

    async def heart_beat(self, delay, spider, slot):
        while not slot.closing:
            await asyncio.sleep(delay)
            asyncio.create_task(self._next_request(spider))
