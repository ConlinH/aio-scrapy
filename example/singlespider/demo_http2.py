import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class DemoMemorySpider(Spider):
    name = 'DemoMemorySpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        # 'CONCURRENT_REQUESTS': 1,
        # 'LOG_LEVEL': 'INFO'
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.RFPDupeFilter',
        "CLOSE_SPIDER_ON_IDLE": True,
        'DOWNLOAD_HANDLERS': {
            'http': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
            'https': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
        },
        'HTTPX_CLIENT_SESSION_ARGS': {
            'http2': True
        }
    }

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

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            # yield response.follow(next_page, self.parse)
            yield Request(f"https://quotes.toscrape.com/{next_page}", callback=self.parse)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoMemorySpider.start()
