import asyncio

from aioscrapy import signals
from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.log import logger
from aioscrapy.utils.tools import create_task


class LogStats:
    """Log basic scraping stats periodically"""

    def __init__(self, stats, interval=60.0):
        self.stats = stats
        self.interval = interval
        self.multiplier = 60.0 / self.interval
        self.task = None
        self.pagesprev = 0
        self.itemsprev = 0

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getfloat('LOGSTATS_INTERVAL')
        if not interval:
            raise NotConfigured
        o = cls(crawler.stats, interval)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        self.task = create_task(self.log(spider))

    async def log(self, spider):
        await asyncio.sleep(self.interval)
        items = self.stats.get_value('item_scraped_count', 0)
        pages = self.stats.get_value('response_received_count', 0)
        irate = (items - self.itemsprev) * self.multiplier
        prate = (pages - self.pagesprev) * self.multiplier
        self.pagesprev, self.itemsprev = pages, items

        msg = ("<%(spider_name)s> Crawled %(pages)d pages (at %(pagerate)d pages/min), "
               "scraped %(items)d items (at %(itemrate)d items/min)")
        log_args = {'pages': pages, 'pagerate': prate, 'spider_name': spider.name,
                    'items': items, 'itemrate': irate}
        logger.info(msg % log_args)
        self.task = create_task(self.log(spider))

    def spider_closed(self, spider, reason):
        if self.task and not self.task.done():
            self.task.cancel()
