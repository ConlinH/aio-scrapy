import logging
import os
from typing import Optional, Set

from aioscrapy import Request, Spider
from aioscrapy.dupefilters import DupeFilterBase
from aioscrapy.utils.request import referer_str


class DiskRFPDupeFilter(DupeFilterBase):
    """Request Fingerprint duplicates filter built with Disk storage"""

    def __init__(self, path: Optional[str] = None, debug: bool = False):
        self.file: Optional["File object"] = None
        self.debug = debug
        self.fingerprints: Set = set()
        self.logdupes: bool = True
        self.logger = logging.getLogger(__name__)
        if path:
            self.file = open(os.path.join(path, 'requests.seen'), 'a+')
            self.file.seek(0)
            self.fingerprints.update(x.rstrip() for x in self.file)

    @classmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG')
        path = crawler.settings.get('JOBDIR', './job_dir')
        if path and not os.path.exists(path):
            os.makedirs(path)
        return cls(path, debug)

    async def request_seen(self, request: Request) -> bool:
        if request.fingerprint in self.fingerprints:
            return True
        self.fingerprints.add(request.fingerprint)
        if self.file:
            self.file.write(request.fingerprint + '\n')
        return False

    def close(self, reason: str = '') -> None:
        if self.file:
            self.file.close()

    def log(self, request: Request, spider: Spider):
        if self.debug:
            msg = "Filtered duplicate request: %(request)s (referer: %(referer)s)"
            args = {'request': request, 'referer': referer_str(request)}
            self.logger.debug(msg, args, extra={'spider': spider})
        elif self.logdupes:
            msg = ("Filtered duplicate request: %(request)s"
                   " - no more duplicates will be shown"
                   " (see DUPEFILTER_DEBUG to show all duplicates)")
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
            self.logdupes = False

        spider.crawler.stats.inc_value('dupefilter/filtered', spider=spider)


RFPDupeFilter = DiskRFPDupeFilter
