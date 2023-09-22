import logging

from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class DemoRabbitmqSpider(Spider):
    name = 'DemoRabbitmqSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        "CLOSE_SPIDER_ON_IDLE": False,
        # 'SCHEDULER_FLUSH_ON_START': True,

        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.rabbitmq.SpiderPriorityQueue',
        # DUPEFILTER_CLASS = 'aioscrapy.dupefilters.desk.RFPDupeFilter'
        'SCHEDULER_SERIALIZER': 'aioscrapy.serializer.PickleSerializer',
        'RABBITMQ_ARGS': {
            'queue': {
                'url': "amqp://guest:guest@192.168.234.128:5673",
                'connection_max_size': 2,
                'channel_max_size': 10,
            }
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
            yield response.follow(next_page, self.parse)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoRabbitmqSpider.start()
