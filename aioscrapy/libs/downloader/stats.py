from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.request import request_httprepr
from aioscrapy.utils.python import global_object_name


class DownloaderStats:

    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('DOWNLOADER_STATS'):
            raise NotConfigured
        return cls(crawler.stats)

    def process_request(self, request, spider):
        self.stats.inc_value('downloader/request_count', spider=spider)
        self.stats.inc_value(f'downloader/request_method_count/{request.method}', spider=spider)
        self.stats.inc_value('downloader/request_bytes', len(request_httprepr(request)), spider=spider)

    def process_response(self, request, response, spider):
        self.stats.inc_value('downloader/response_count', spider=spider)
        self.stats.inc_value(f'downloader/response_status_count/{response.status}', spider=spider)
        self.stats.inc_value('downloader/response_bytes', len(response.body), spider=spider)
        return response

    def process_exception(self, request, exception, spider):
        ex_class = global_object_name(exception.__class__)
        self.stats.inc_value('downloader/exception_count', spider=spider)
        self.stats.inc_value(f'downloader/exception_type_count/{ex_class}', spider=spider)
