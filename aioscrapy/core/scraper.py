"""This module implements the Scraper component which parses responses and
extracts information from them"""
import asyncio
import logging
from collections import deque

from itemadapter import is_item
from scrapy import signals
from scrapy.exceptions import CloseSpider, DropItem, IgnoreRequest
from scrapy.http import Request, Response
from scrapy.utils.log import logformatter_adapter
from scrapy.utils.misc import load_object, warn_on_generator_with_return_value
from scrapy.utils.spider import iterate_spider_output

from aioscrapy.middleware import SpiderMiddlewareManager
from aioscrapy.utils.tools import iter_errback

logger = logging.getLogger(__name__)


class Slot:
    """Scraper slot (one per running spider)"""

    MIN_RESPONSE_SIZE = 1024

    def __init__(self, max_active_size=5000000):
        self.max_active_size = max_active_size
        self.queue = deque()
        self.active = set()
        self.active_size = 0
        self.itemproc_size = 0
        self.closing = None

    def add_response_request(self, response, request):
        self.queue.append((response, request))
        if isinstance(response, Response):
            self.active_size += max(len(response.body), self.MIN_RESPONSE_SIZE)
        else:
            self.active_size += self.MIN_RESPONSE_SIZE

    def next_response_request_deferred(self):
        response, request = self.queue.popleft()
        self.active.add(request)
        return response, request

    def finish_response(self, response, request):
        self.active.remove(request)
        if isinstance(response, Response):
            self.active_size -= max(len(response.body), self.MIN_RESPONSE_SIZE)
        else:
            self.active_size -= self.MIN_RESPONSE_SIZE

    def is_idle(self):
        return not (self.queue or self.active)

    def needs_backout(self):
        return self.active_size > self.max_active_size


class Scraper:

    def __init__(self, crawler):
        self.slot = None
        self.spidermw = SpiderMiddlewareManager.from_crawler(crawler)
        itemproc_cls = load_object(crawler.settings['ITEM_PROCESSOR'])
        self.itemproc = itemproc_cls.from_crawler(crawler)
        self.crawler = crawler
        self.signals = crawler.signals
        self.logformatter = crawler.logformatter
        self.concurrent_items_semaphore = asyncio.Semaphore(crawler.settings.getint('CONCURRENT_ITEMS'))

    async def open_spider(self, spider):
        """Open the given spider for scraping and allocate resources for it"""
        self.slot = Slot(self.crawler.settings.getint('SCRAPER_SLOT_MAX_ACTIVE_SIZE'))
        await self.itemproc.open_spider(spider)

    async def close_spider(self, spider):
        """Close a spider being scraped and release its resources"""
        slot = self.slot
        slot.closing = asyncio.Future()
        await self.itemproc.close_spider(spider)
        self._check_if_closing(spider, slot)
        await slot.closing

    def is_idle(self):
        """Return True if there isn't any more spiders to process"""
        return not self.slot

    def _check_if_closing(self, spider, slot):
        if slot.closing and slot.is_idle():
            slot.closing.set_result(spider)

    async def enqueue_scrape(self, response, request, spider):
        slot = self.slot
        slot.add_response_request(response, request)
        await self._scrape_next(spider, slot)

    async def _scrape_next(self, spider, slot):
        while slot.queue:
            response, request = slot.next_response_request_deferred()
            if not isinstance(response, (Response, Exception, BaseException)):
                raise TypeError(
                    "Incorrect type: expected Response or Failure, got %s: %r"
                    % (type(response), response)
                )

            if not isinstance(response, (Exception, BaseException)):
                iterable_or_exception = self.spidermw.scrape_response(self.call_spider, response, request, spider)
            else:
                iterable_or_exception = self.call_spider(response, request, spider)
                self._log_download_errors(iterable_or_exception, response, request, spider)
                logger.error('Scraper bug processing %(request)s',
                             {'request': request},
                             exc_info=response,
                             extra={'spider': spider})

            if hasattr(iterable_or_exception, '__iter__'):
                await self.handle_spider_output(iterable_or_exception, request, response, spider)
            else:
                await self.handle_spider_error(iterable_or_exception, request, response, spider)

            slot.finish_response(response, request)
            self._check_if_closing(spider, slot)
            asyncio.create_task(self._scrape_next(spider, slot))

    def call_spider(self, result, request, spider):
        if isinstance(result, Response):
            callback = request.callback or spider._parse
            warn_on_generator_with_return_value(spider, callback)
            result.request = request
            return iterate_spider_output(callback(result))
        elif request.errback is not None:
            warn_on_generator_with_return_value(spider, request.errback)
            return iterate_spider_output(request.errback(result))
        else:
            return result

    async def handle_spider_error(self, exc, request, response, spider):
        if isinstance(exc, CloseSpider):
            await self.crawler.engine.close_spider(spider, exc.reason or 'cancelled')
            return
        logkws = self.logformatter.spider_error(exc, request, response, spider)
        logger.log(
            *logformatter_adapter(logkws),
            exc_info=exc,
            extra={'spider': spider}
        )
        self.signals.send_catch_log(
            signal=signals.spider_error,
            failure=exc, response=response,
            spider=spider
        )
        self.crawler.stats.inc_value(
            "spider_exceptions/%s" % exc.__class__.__name__,
            spider=spider
        )

    async def handle_spider_output(self, result, request, response, spider):
        if not result:
            return
        it = iter_errback(result, self.handle_spider_error, request, response, spider)
        # sem = asyncio.Semaphore(self.concurrent_items)
        async for elem in it:
            async with self.concurrent_items_semaphore:
                if isinstance(elem, Request):
                    await self.crawler.engine.crawl(request=elem, spider=spider)
                else:
                    asyncio.create_task(self._process_spidermw_output(elem, request, response, spider))

    async def _process_spidermw_output(self, output, request, response, spider):
        """Process each Request/Item (given in the output parameter) returned
        from the given spider
        """
        if is_item(output):
            self.slot.itemproc_size += 1
            item = await self.itemproc.process_item(output, spider)
            await self._itemproc_finished(output, item, response, spider)
        elif output is None:
            pass
        else:
            typename = type(output).__name__
            logger.error(
                'Spider must return request, item, or None, got %(typename)r in %(request)s',
                {'request': request, 'typename': typename},
                extra={'spider': spider},
            )

    def _log_download_errors(self, spider_exception, download_exception, request, spider):
        """Log and silence errors that come from the engine (typically download
        errors that got propagated thru here)
        """
        if isinstance(download_exception, (Exception, BaseException)) \
                and not isinstance(download_exception, IgnoreRequest):
            logkws = self.logformatter.download_error(download_exception, request, spider)
            logger.log(
                *logformatter_adapter(logkws),
                extra={'spider': spider},
                exc_info=download_exception,
            )

        if spider_exception is not download_exception:
            return spider_exception

    async def _itemproc_finished(self, output, item, response, spider):
        """ItemProcessor finished for the given ``item`` and returned ``output``
        """
        self.slot.itemproc_size -= 1
        if isinstance(output, (Exception, BaseException)):
            if isinstance(output, DropItem):
                logkws = self.logformatter.dropped(item, output, response, spider)
                if logkws is not None:
                    logger.log(*logformatter_adapter(logkws), extra={'spider': spider})
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_dropped, item=item, response=response,
                    spider=spider, exception=output)
            else:
                logkws = self.logformatter.item_error(item, output, response, spider)
                logger.log(*logformatter_adapter(logkws), extra={'spider': spider},
                           exc_info=output)
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_error, item=item, response=response,
                    spider=spider, failure=output)
        else:
            logkws = self.logformatter.scraped(output, response, spider)
            if logkws is not None:
                logger.log(*logformatter_adapter(logkws), extra={'spider': spider})
            return await self.signals.send_catch_log_deferred(
                signal=signals.item_scraped, item=output, response=response,
                spider=spider)
