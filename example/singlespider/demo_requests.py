import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider
from aioscrapy.http import Response

logger = logging.getLogger(__name__)


class DemoRequestsSpider(Spider):
    name = 'DemoRequestsSpider'

    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        DOWNLOAD_HANDLERS={
            'http': 'aioscrapy.core.downloader.handlers.requests.RequestsDownloadHandler',
            'https': 'aioscrapy.core.downloader.handlers.requests.RequestsDownloadHandler',
        },
    )

    start_urls = ['https://quotes.toscrape.com']

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
        print(item)


if __name__ == '__main__':
    DemoRequestsSpider.start()
