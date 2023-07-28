import logging
import re

from aioscrapy.spiders import Spider, Request

logger = logging.getLogger(__name__)


class DemoDuplicateSpider(Spider):
    name = 'DemoDuplicateSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        "CLOSE_SPIDER_ON_IDLE": True,
        # 'LOG_FILE': 'test.log',

        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.RFPDupeFilter',
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.RFPDupeFilter',
        'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.BloomDupeFilter',

        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.redis.SpiderPriorityQueue',
        'SCHEDULER_SERIALIZER': 'aioscrapy.serializer.JsonSerializer',
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://:@192.168.43.165:6379/10',
                'max_connections': 2,
            }
        }
    }

    async def start_requests(self):
        yield Request('https://quotes.toscrape.com/page/1', dont_filter=False, fingerprint='1')

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

        next_page_url = response.css('li.next a::attr("href")').get()
        if next_page_url is not None:
            page_fingerprint = ''.join(re.findall(r'page/(\d+)', next_page_url))
            yield response.follow(next_page_url, self.parse, dont_filter=False, fingerprint=page_fingerprint)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoDuplicateSpider.start()
