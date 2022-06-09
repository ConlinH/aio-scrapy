import os
import logging

from aioscrapy.dupefilters import AbsDupeFilterBase

from aioscrapy.utils.request import referer_str, request_fingerprint


class DiskRFPDupeFilter(AbsDupeFilterBase):
    """Request Fingerprint duplicates filter"""

    def __init__(self, path=None, debug=False):
        self.file = None
        self.fingerprints = set()
        self.logdupes = True
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if path:
            self.file = open(os.path.join(path, 'requests.seen'), 'a+')
            self.file.seek(0)
            self.fingerprints.update(x.rstrip() for x in self.file)

    @classmethod
    def from_spider(cls, spider):
        settings = spider.settings
        debug = settings.getbool('DUPEFILTER_DEBUG')
        path = settings.get('JOBDIR', './job_dir')
        if path and not os.path.exists(path):
            os.makedirs(path)
        return cls(path, debug)

    async def request_seen(self, request):
        fp = self.request_fingerprint(request)
        if fp in self.fingerprints:
            return True
        self.fingerprints.add(fp)
        if self.file:
            self.file.write(fp + '\n')

    def request_fingerprint(self, request):
        return request_fingerprint(request)

    def close(self, reason):
        if self.file:
            self.file.close()

    def log(self, request, spider):
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
