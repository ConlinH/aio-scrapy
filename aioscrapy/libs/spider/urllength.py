"""
Url Length Spider Middleware

See documentation in docs/topics/spider-middleware.rst
"""

from aioscrapy.exceptions import NotConfigured
from aioscrapy.http import Request
from aioscrapy.utils.log import logger


class UrlLengthMiddleware:

    def __init__(self, maxlength):
        self.maxlength = maxlength

    @classmethod
    def from_settings(cls, settings):
        maxlength = settings.getint('URLLENGTH_LIMIT')
        if not maxlength:
            raise NotConfigured
        return cls(maxlength)

    async def process_spider_output(self, response, result, spider):
        def _filter(request):
            if isinstance(request, Request) and len(request.url) > self.maxlength:
                logger.info(
                    "Ignoring link (url length > %(maxlength)d): %(url)s " % {
                        'maxlength': self.maxlength, 'url': request.url
                    }
                )
                spider.crawler.stats.inc_value('urllength/request_ignored_count', spider=spider)
                return False
            else:
                return True

        return (r async for r in result or () if _filter(r))
