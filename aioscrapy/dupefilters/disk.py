import os
from typing import Optional, Set

from aioscrapy import Request
from aioscrapy.dupefilters import DupeFilterBase


class DiskRFPDupeFilter(DupeFilterBase):
    """Request Fingerprint duplicates filter built with Disk storage"""

    def __init__(self, path: Optional[str] = None, debug: bool = False, info: bool = False):
        self.file: Optional["File object"] = None
        self.debug = debug
        self.fingerprints: Set = set()
        self.logdupes: bool = True
        self.info: bool = info
        if path:
            self.file = open(os.path.join(path, 'requests.seen'), 'a+')
            self.file.seek(0)
            self.fingerprints.update(x.rstrip() for x in self.file)

    @classmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG')
        info = crawler.settings.getbool('DUPEFILTER_INFO')
        path = crawler.settings.get('JOBDIR', './job_dir')
        if path and not os.path.exists(path):
            os.makedirs(path)
        return cls(path, debug, info)

    async def request_seen(self, request: Request) -> bool:
        if request.fingerprint in self.fingerprints:
            return True
        self.fingerprints.add(request.fingerprint)
        if self.file:
            self.file.write(request.fingerprint + '\n')
        return False

    async def close(self, reason: str = '') -> None:
        if self.file:
            self.file.close()


RFPDupeFilter = DiskRFPDupeFilter
