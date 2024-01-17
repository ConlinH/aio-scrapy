"""
Base class for Scrapy spiders

See documentation in docs/topics/spiders.rst
"""
import time
from typing import Optional, Union

from aioscrapy import signals
from aioscrapy.exceptions import DontCloseSpider
from aioscrapy.http.request import Request
from aioscrapy.http.response import Response
from aioscrapy.statscollectors import StatsCollector
from aioscrapy.utils.tools import call_helper
from aioscrapy.utils.url import url_is_from_spider


class Spider(object):
    """Base class for scrapy spiders. All spiders must inherit from this
    class.
    """

    name: Optional[str] = None
    proxy: Optional["aioscrapy.proxy.AbsProxy"] = None
    custom_settings: Optional[dict] = None
    stats: Optional[StatsCollector] = None

    pause: bool = False
    _pause_time: Optional[Union[int, float]] = None

    def __init__(self, name=None, **kwargs):
        if name is not None:
            self.name = name
        elif not getattr(self, 'name', None):
            raise ValueError(f"{type(self).__name__} must have a name")
        self.__dict__.update(kwargs)
        if not hasattr(self, 'start_urls'):
            self.start_urls = []

    @property
    def pause_time(self) -> int:
        if self._pause_time is None:
            self._pause_time = 600 + int(time.time())
        return self._pause_time

    @pause_time.setter
    def pause_time(self, value: Union[int, float]):
        self.pause = True
        if value is None:
            self._pause_time = float('inf')
        elif value < time.time():
            self._pause_time = value + int(time.time())
        else:
            self._pause_time = value

    @classmethod
    async def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def _set_crawler(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.close_on_idle = self.settings.get("CLOSE_SPIDER_ON_IDLE", True)
        crawler.signals.connect(self.close, signals.spider_closed)
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    async def start_requests(self):
        if not self.start_urls and hasattr(self, 'start_url'):
            raise AttributeError(
                "Crawling could not start: 'start_urls' not found "
                "or empty (but found 'start_url' attribute instead, "
                "did you miss an 's'?)")

        for url in self.start_urls:
            yield Request(url)

    async def request_from_dict(self, d: dict):
        """集成后重写改方法，将队列中的json根据情况构建成Request对象"""
        pass

    async def _parse(self, response: Response, **kwargs):
        return await call_helper(self.parse, response)

    async def parse(self, response: Response):
        raise NotImplementedError(f'{self.__class__.__name__}.parse callback is not defined')

    @classmethod
    def update_settings(cls, settings):
        settings.setdict(cls.custom_settings or {}, priority='spider')

    @classmethod
    def handles_request(cls, request):
        return url_is_from_spider(request.url, cls)

    @staticmethod
    def close(spider, reason):
        closed = getattr(spider, 'closed', None)
        if callable(closed):
            return closed(reason)

    def __str__(self):
        return f"<{type(self).__name__} {self.name!r} at 0x{id(self):0x}>"

    __repr__ = __str__

    @classmethod
    def start(cls, setting_path=None):
        from aioscrapy.crawler import CrawlerProcess
        from aioscrapy.utils.project import get_project_settings

        settings = get_project_settings()
        if setting_path is not None:
            settings.setmodule(setting_path)
        cp = CrawlerProcess(settings)
        cp.crawl(cls)
        cp.start()

    def spider_idle(self):
        if not self.close_on_idle:
            raise DontCloseSpider
