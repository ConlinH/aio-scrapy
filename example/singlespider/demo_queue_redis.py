
from aioscrapy import Spider, logger


class DemoRedisSpider(Spider):
    name = 'DemoRedisSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        "CLOSE_SPIDER_ON_IDLE": True,
        # 'LOG_FILE': 'test.log',

        # SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'
        # SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.rabbitmq.SpiderPriorityQueue'

        # DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'
        # DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RFPDupeFilter'
        # DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.BloomDupeFilter'

        # SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'
        # SCHEDULER_SERIALIZER = 'aioscrapy.serializer.PickleSerializer'

        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.redis.SpiderPriorityQueue',
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.RFPDupeFilter',
        'SCHEDULER_SERIALIZER': 'aioscrapy.serializer.JsonSerializer',
        'ENQUEUE_CACHE_NUM': 100,
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://192.168.18.129:6379/0',
                'max_connections': 2,
                'timeout': None,
                'retry_on_timeout': True,
                'health_check_interval': 30
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
            yield response.follow(next_page, self.parse, dont_filter=False)

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoRedisSpider.start()
