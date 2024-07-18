import re

from aioscrapy import Spider, Request, logger


class DemoDuplicateSpider(Spider):
    name = 'DemoDuplicateSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        'LOG_LEVEL': 'INFO',
        "CLOSE_SPIDER_ON_IDLE": True,

        "DUPEFILTER_INFO": True,   # 是否以info级别的日志输出过滤器的信息

        # 'LOG_FILE': 'test.log',

        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.RFPDupeFilter',  # 本地文件存储指纹去重
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.RFPDupeFilter',  # redis set去重
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.BloomDupeFilter',  # 布隆过滤器去重

        # RFPDupeFilter去重的增强版: 当请求失败或解析失败时 从Set中移除指纹
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.ExRFPDupeFilter',

        # 布隆过滤器去重增强版：添加一个临时的Set集合缓存请求中的请求 在解析成功后再将指纹加入到布隆过滤器同时将Set中的清除
        'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.ExBloomDupeFilter',
        "DUPEFILTER_SET_KEY_TTL": 60 * 3,  # BloomSetDupeFilter过滤器的临时Redis Set集合的过期时间

        # 'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.redis.SpiderPriorityQueue',
        'SCHEDULER_SERIALIZER': 'aioscrapy.serializer.JsonSerializer',
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://127.0.0.1:6379/10',
                'max_connections': 2,
                'timeout': None,
                'retry_on_timeout': True,
                'health_check_interval': 30
            }
        }
    }

    async def start_requests(self):
        yield Request(
            'https://quotes.toscrape.com/page/1',
            dont_filter=False,
            fingerprint='1',    # 不使用默认的指纹计算规则 而是指定去重指纹值
            meta=dict(
                dupefilter_msg="page_1"  # 当Request被去重时 指定日志输出的内容为"page_1" 不设置则默认为request对象
            )
        )

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
        logger.info(item)


if __name__ == '__main__':
    DemoDuplicateSpider.start()
