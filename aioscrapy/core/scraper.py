"""This module implements the Scraper component which parses responses and
extracts information from them"""
import asyncio
import logging
from collections import deque
from typing import Any, Deque, AsyncGenerator, Set, Tuple, Union, Optional

from aioscrapy import signals, Spider
from aioscrapy.exceptions import CloseSpider, DropItem, IgnoreRequest
from aioscrapy.http import Request, Response
from aioscrapy.logformatter import LogFormatter
from aioscrapy.middleware import ItemPipelineManager
from aioscrapy.middleware import SpiderMiddlewareManager
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.log import logformatter_adapter
from aioscrapy.utils.misc import load_object
from aioscrapy.utils.tools import call_helper

logger = logging.getLogger(__name__)

QueueTuple = Tuple[Union[Response, BaseException], Request]


class Slot:
    """Scraper slot (one per running spider)"""

    MIN_RESPONSE_SIZE = 1024

    def __init__(self, max_active_size: int = 5000000):
        self.max_active_size = max_active_size
        self.queue: Deque[QueueTuple] = deque()
        self.active: Set[Request] = set()
        self.active_size: int = 0
        self.itemproc_size: int = 0

    def add_response_request(self, result: Union[Response, BaseException], request: Request) -> None:
        self.queue.append((result, request))
        if isinstance(result, Response):
            self.active_size += max(len(result.body), self.MIN_RESPONSE_SIZE)
        else:
            self.active_size += self.MIN_RESPONSE_SIZE

    def next_response_request(self) -> QueueTuple:
        response, request = self.queue.popleft()
        self.active.add(request)
        return response, request

    def finish_response(self, result: Union[Response, BaseException], request: Request) -> None:
        self.active.remove(request)
        if isinstance(result, Response):
            self.active_size -= max(len(result.body), self.MIN_RESPONSE_SIZE)
            result._cached_selector = None
        else:
            self.active_size -= self.MIN_RESPONSE_SIZE

    def is_idle(self) -> bool:
        return not (self.queue or self.active)

    def needs_backout(self) -> bool:
        return self.active_size > self.max_active_size


class Scraper:

    def __init__(
            self,
            crawler,
            slot: Slot,
            spidermw: SpiderMiddlewareManager,
            itemproc: ItemPipelineManager,
    ):
        self.crawler = crawler
        self.spider: Spider = crawler.spider
        self.signals: SignalManager = self.crawler.signals
        self.logformatter: LogFormatter = self.crawler.logformatter

        self.slot = slot
        self.spidermw = spidermw
        self.itemproc = itemproc

        self.finish: bool = False
        self.concurrent_parser = asyncio.Semaphore(crawler.settings.getint('CONCURRENT_PARSER', 4))

    @classmethod
    async def from_crawler(cls, crawler):
        instance: "Scraper" = cls(
            crawler,
            Slot(crawler.settings.getint('SCRAPER_SLOT_MAX_ACTIVE_SIZE')),
            await call_helper(SpiderMiddlewareManager.from_crawler, crawler),
            await call_helper(load_object(crawler.settings['ITEM_PROCESSOR']).from_crawler, crawler)
        )
        await instance.itemproc.open_spider(crawler.spider)
        return instance

    async def close(self) -> None:
        """Close a spider being scraped and release its resources"""
        await self.itemproc.close_spider(self.spider)
        self.finish = True

    def is_idle(self) -> bool:
        """Return True if there isn't any more spiders to process"""
        return self.slot.is_idle()

    def needs_backout(self) -> bool:
        return self.slot.needs_backout()

    async def consume_queue(self) -> None:
        async with self.concurrent_parser:
            result, request = self.slot.next_response_request()
            try:
                await self._scrape(result, request)
            except BaseException as e:
                logger.error('Scraper bug processing %(request)s',
                             {'request': request},
                             exc_info=e,
                             extra={'spider': self.spider})
            finally:
                # 将slot中的缓存结果删除
                self.slot.finish_response(result, request)

    async def enqueue_scrape(self, result: Union[Response, BaseException], request: Request) -> None:
        # 将结果缓存到slot中
        self.slot.add_response_request(result, request)
        asyncio.create_task(self.consume_queue())

    async def _scrape(self, result: Union[Response, BaseException], request: Request) -> None:
        """
        Handle the downloaded response or failure through the spider callback/errback
        """
        if not isinstance(result, (Response, BaseException)):
            raise TypeError(f"Incorrect type: expected Response or Failure, got {type(result)}: {result!r}")
        try:
            output = await self._scrape2(result, request)  # returns spider's processed output
        except BaseException as e:
            await self.handle_spider_error(e, request, result)
        else:
            await self.handle_spider_output(output, request, result)

    async def _scrape2(self, result: Union[Response, BaseException], request: Request) -> Optional[AsyncGenerator]:
        """
        Handle the different cases of request's result been a Response or a Failure
        """
        if isinstance(result, Response):
            # 将Response丢给爬虫中间件处理, 处理结果将将给self.call_spider处理
            return await self.spidermw.scrape_response(self.call_spider, result, request, self.spider)
        else:
            try:
                # 处理下载错误或经过下载中间件时出现的错误
                return await self.call_spider(result, request)
            except BaseException as e:
                await self._log_download_errors(e, result, request)

    async def call_spider(self, result: Union[Response, BaseException], request: Request) -> Optional[AsyncGenerator]:
        if isinstance(result, Response):
            # 将Response丢给spider的解析函数
            callback = request.callback or self.spider._parse
            # 将parse解析出的结果,变成可迭代对象
            return await call_helper(callback, result, **result.request.cb_kwargs)
        else:
            if request.errback is None:
                raise result
            # 下载中间件或下载结果出现错误,回调request中的errback函数
            return await call_helper(request.errback, result)

    async def handle_spider_error(self, exc: BaseException, request: Request, response: Response) -> None:
        if isinstance(exc, CloseSpider):
            asyncio.create_task(self.crawler.engine.close_spider(self.spider, exc.reason or 'cancelled'))
            return
        logkws = self.logformatter.spider_error(exc, request, response, self.spider)
        logger.log(
            *logformatter_adapter(logkws),
            exc_info=exc,
            extra={'spider': self.spider}
        )
        await self.signals.send_catch_log(
            signal=signals.spider_error,
            failure=exc, response=response,
            spider=self.spider
        )
        self.crawler.stats.inc_value(
            "spider_exceptions/%s" % exc.__class__.__name__,
            spider=self.spider
        )

    async def handle_spider_output(self, result: AsyncGenerator, request: Request, response: Response) -> None:
        if not result:
            return

        while True:
            try:
                res = await result.__anext__()
            except StopAsyncIteration:
                break
            except Exception as e:
                await self.handle_spider_error(e, request, response)
            else:
                await self._process_spidermw_output(res, request, response)

    async def _process_spidermw_output(self, output: Any, request: Request, response: Response) -> None:
        """Process each Request/Item (given in the output parameter) returned
        from the given spider
        """
        if isinstance(output, Request):
            await self.crawler.engine.crawl(request=output)
        elif isinstance(output, dict):
            self.slot.itemproc_size += 1
            item = await self.itemproc.process_item(output, self.spider)
            process_item_method = getattr(self.spider, 'process_item', None)
            if process_item_method:
                await call_helper(process_item_method, item)
            await self._itemproc_finished(output, item, response)
        elif output is None:
            pass
        else:
            typename = type(output).__name__
            logger.error(
                'Spider must return request, item, or None, got %(typename)r in %(request)s',
                {'request': request, 'typename': typename},
                extra={'spider': self.spider},
            )

    async def _log_download_errors(
            self,
            spider_exception: BaseException,
            download_exception: BaseException,
            request: Request
    ) -> None:
        """
        处理并记录错误
        :param spider_exception: 将download_exception丢给request.errback处理时,触发的新错误
        :param download_exception: 下载过程发生的错误,或中间件中发生的错误
        :param request:
        :param spider:
        :return:
        """
        if isinstance(download_exception, BaseException) and not isinstance(download_exception, IgnoreRequest):
            logkws = self.logformatter.download_error(download_exception, request, self.spider)
            logger.log(
                *logformatter_adapter(logkws),
                extra={'spider': self.spider},
                exc_info=download_exception,
            )

        if spider_exception is not download_exception:
            raise spider_exception

    async def _itemproc_finished(self, output: Any, item: Any, response: Response) -> None:
        """ItemProcessor finished for the given ``item`` and returned ``output``
        """
        self.slot.itemproc_size -= 1
        if isinstance(output, BaseException):
            if isinstance(output, DropItem):
                logkws = self.logformatter.dropped(item, output, response, self.spider)
                if logkws is not None:
                    logger.log(*logformatter_adapter(logkws), extra={'spider': self.spider})
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_dropped, item=item, response=response,
                    spider=self.spider, exception=output)
            else:
                logkws = self.logformatter.item_error(item, output, response, self.spider)
                logger.log(*logformatter_adapter(logkws), extra={'spider': self.spider},
                           exc_info=output)
                return await self.signals.send_catch_log_deferred(
                    signal=signals.item_error, item=item, response=response,
                    spider=self.spider, failure=output)
        else:
            logkws = self.logformatter.scraped(output, response, self.spider)
            if logkws is not None:
                logger.log(*logformatter_adapter(logkws), extra={'spider': self.spider})
            return await self.signals.send_catch_log_deferred(
                signal=signals.item_scraped, item=output, response=response,
                spider=self.spider)
