"""
Base class for Scrapy spiders

See documentation in docs/topics/spiders.rst
"""
import logging
import warnings
from typing import Optional

from aioscrapy import signals
from aioscrapy.http.request import Request
from aioscrapy.utils.url import url_is_from_spider
from aioscrapy.utils.deprecate import method_is_overridden
from aioscrapy.exceptions import DontCloseSpider
from aioscrapy.utils.tools import call_helper


class Spider(object):
    """Base class for scrapy spiders. All spiders must inherit from this
    class.
    """

    name: Optional[str] = None
    custom_settings: Optional[dict] = None

    def __init__(self, name=None, **kwargs):
        if name is not None:
            self.name = name
        elif not getattr(self, 'name', None):
            raise ValueError(f"{type(self).__name__} must have a name")
        self.__dict__.update(kwargs)
        if not hasattr(self, 'start_urls'):
            self.start_urls = []

    @property
    def logger(self):
        logger = logging.getLogger(self.name)
        return logging.LoggerAdapter(logger, {'spider': self})

    def log(self, message, level=logging.DEBUG, **kw):
        """Log the given message at the given log level

        This helper wraps a log call to the logger within the spider, but you
        can use it directly (e.g. Spider.logger.info('msg')) or use any other
        Python logger too.
        """
        self.logger.log(level, message, **kw)

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
        cls = self.__class__
        if not self.start_urls and hasattr(self, 'start_url'):
            raise AttributeError(
                "Crawling could not start: 'start_urls' not found "
                "or empty (but found 'start_url' attribute instead, "
                "did you miss an 's'?)")
        if method_is_overridden(cls, Spider, 'make_requests_from_url'):
            warnings.warn(
                "Spider.make_requests_from_url method is deprecated; it "
                "won't be called in future Scrapy releases. Please "
                "override Spider.start_requests method instead "
                f"(see {cls.__module__}.{cls.__name__}).",
            )
            for url in self.start_urls:
                yield self.make_requests_from_url(url)
        else:
            for url in self.start_urls:
                yield Request(url)

    def make_requests_from_url(self, url):
        """ This method is deprecated. """
        warnings.warn(
            "Spider.make_requests_from_url method is deprecated: "
            "it will be removed and not be called by the default "
            "Spider.start_requests method in future Scrapy releases. "
            "Please override Spider.start_requests method instead."
        )
        return Request(url, dont_filter=True)

    async def _parse(self, response, **kwargs):
        return await call_helper(self.parse, response, **kwargs)

    async def parse(self, response, **kwargs):
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
