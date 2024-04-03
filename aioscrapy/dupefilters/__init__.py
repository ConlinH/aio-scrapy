from abc import ABCMeta, abstractmethod

from aioscrapy import Request, Spider
from aioscrapy.utils.log import logger


class DupeFilterBase(metaclass=ABCMeta):
    """Request Fingerprint duplicates filter"""

    @classmethod
    @abstractmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        """ Get Instance of RFPDupeFilter from crawler """

    @abstractmethod
    async def request_seen(self, request: Request) -> bool:
        """ Check whether fingerprint of request exists """

    @abstractmethod
    async def close(self, reason: str = '') -> None:
        """ Delete data on close """

    def log(self, request: Request, spider: Spider):
        if self.info:
            logger.info("Filtered duplicate request: %(request)s" % {
                'request': request.meta.get('dupefilter_msg') or request
            })
        elif self.debug:
            logger.debug("Filtered duplicate request: %(request)s" % {
                'request': request.meta.get('dupefilter_msg') or request
            })
        elif self.logdupes:
            msg = ("Filtered duplicate request: %(request)s"
                   " - no more duplicates will be shown"
                   " (see DUPEFILTER_DEBUG to show all duplicates)")
            logger.debug(msg % {'request': request.meta.get('dupefilter_msg') or request})
            self.logdupes = False

        spider.crawler.stats.inc_value('dupefilter/filtered', spider=spider)
