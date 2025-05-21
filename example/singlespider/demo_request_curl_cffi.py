from aioscrapy import Spider, logger
from aioscrapy.http import Response, Request, FormRequest, JsonRequest


class DemoCurlCffiSpider(Spider):
    name = 'DemoCurlCffiSpider'

    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        # DOWNLOAD_HANDLERS={
        #     'http': 'aioscrapy.core.downloader.handlers.curl_cffi.CurlCffiDownloadHandler',
        #     'https': 'aioscrapy.core.downloader.handlers.curl_cffi.CurlCffiDownloadHandler',
        # },
        DOWNLOAD_HANDLERS_TYPE="curl_cffi",
        CURL_CFFI_ARGS=dict(impersonate="chrome110"),   # 传递给curl_cffi AsyncSession构造函数的参数
    )

    start_urls = ["https://quotes.toscrape.com"]

    async def start_requests(self):
        # for url in self.start_urls:
        #     yield Request(url)
        yield Request("https://tools.scrapfly.io/api/fp/ja3", meta=dict(impersonate="chrome110"))
        yield FormRequest("https://httpbin.org/post", formdata=dict(test="test"), meta=dict(impersonate="chrome110"))
        yield JsonRequest("https://httpbin.org/post", data=dict(test="test"), meta=dict(impersonate="chrome110"))

    @staticmethod
    async def process_request(request, spider):
        """ request middleware """
        pass

    @staticmethod
    async def process_response(request, response, spider):
        """ response middleware """
        return response

    @staticmethod
    async def process_exception(request, exception, spider):
        """ exception middleware """
        pass

    async def parse(self, response: Response):
        print(response.text)

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoCurlCffiSpider.start(use_windows_selector_eventLoop=True)
