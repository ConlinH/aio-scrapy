
from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.spiders import Spider, CrawlSpider

from aioscrapy.settings import aio_settings

__all__ = ["AioSpider", "AioCrawlSpider"]


class ExtensionMixin:

    @classmethod
    def start(cls):
        from aioscrapy.crawler import CrawlerProcess
        from aioscrapy.utils.tools import get_project_settings

        settings = get_project_settings()
        cp = CrawlerProcess(settings)
        cp.add_crawler(cls)
        cp.start()

    def spider_idle(self):
        raise DontCloseSpider


class AioSpider(ExtensionMixin, Spider):
    def _set_crawler(self, crawler):
        super()._set_crawler(crawler)
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)


class AioCrawlSpider(ExtensionMixin, CrawlSpider):
    def _set_crawler(self, crawler):
        super()._set_crawler(crawler)
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
