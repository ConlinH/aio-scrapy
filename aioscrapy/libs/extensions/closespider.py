"""CloseSpider is an extension that forces spiders to be closed after certain
conditions are met.

See documentation in docs/topics/extensions.rst
"""
import asyncio
from typing import Optional
from collections import defaultdict

from aioscrapy import signals
from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.tools import create_task


class CloseSpider:

    def __init__(self, crawler):
        self.crawler = crawler

        self.close_on = {
            'timeout': crawler.settings.getfloat('CLOSESPIDER_TIMEOUT'),
            'itemcount': crawler.settings.getint('CLOSESPIDER_ITEMCOUNT'),
            'pagecount': crawler.settings.getint('CLOSESPIDER_PAGECOUNT'),
            'errorcount': crawler.settings.getint('CLOSESPIDER_ERRORCOUNT'),
        }

        if not any(self.close_on.values()):
            raise NotConfigured

        self.counter = defaultdict(int)
        self.task: Optional[asyncio.tasks.Task] = None

        if self.close_on.get('errorcount'):
            crawler.signals.connect(self.error_count, signal=signals.spider_error)
        if self.close_on.get('pagecount'):
            crawler.signals.connect(self.page_count, signal=signals.response_received)
        if self.close_on.get('timeout'):
            crawler.signals.connect(self.timeout_close, signal=signals.spider_opened)
        if self.close_on.get('itemcount'):
            crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def error_count(self, failure, response, spider):
        self.counter['errorcount'] += 1
        if self.counter['errorcount'] == self.close_on['errorcount']:
            create_task(self.crawler.engine.stop(reason='closespider_errorcount'))

    async def page_count(self, response, request, spider):
        self.counter['pagecount'] += 1
        if self.counter['pagecount'] == self.close_on['pagecount']:
            create_task(self.crawler.engine.stop(reason='closespider_pagecount'))

    async def timeout_close(self, spider):
        async def close():
            await asyncio.sleep(self.close_on['timeout'])
            create_task(self.crawler.engine.stop(reason='closespider_timeout'))

        self.task = create_task(close())

    async def item_scraped(self, item, spider):
        self.counter['itemcount'] += 1
        if self.counter['itemcount'] == self.close_on['itemcount']:
            create_task(self.crawler.engine.stop(reason='closespider_itemcount'))

    def spider_closed(self, spider):
        if self.task and not self.task.done():
            self.task.cancel()
