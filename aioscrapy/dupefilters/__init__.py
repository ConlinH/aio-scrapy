from abc import ABCMeta, abstractmethod

from aioscrapy import Request, Spider


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
    def close(self, reason: str = '') -> None:
        """ Delete data on close """

    @abstractmethod
    def log(self, request: Request, spider: Spider) -> None:
        """ Logs given request """
