import re
from urllib.parse import unquote
import logging

from scrapy import Request
from aioscrapy.spiders import AioSpider

logger = logging.getLogger(__name__)


class Baidu3Spider(AioSpider):
    name = 'baidu3'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1,
        'RANDOM_TLS_CIPHERS': True,

        # 使用scrapy的调度
        # 'SCHEDULER': 'scrapy.core.scheduler.Scheduler',
        # 'DUPEFILTER_CLASS': 'scrapy.dupefilters.RFPDupeFilter',

        # 使用scrapy-redis的调度
        # 'SCHEDULER': 'scrapy_redis.scheduler.Scheduler',
        # 'SCHEDULER_QUEUE_CLASS': 'scrapy_redis.queue.PriorityQueue',
        # 'SCHEDULER_DUPEFILTER_CLASS': 'scrapy_redis.dupefilter.RFPDupeFilter',
        # 'REDIS_URL': 'redis://:password@l27.0.0.1:6379/1',

        # (默认)使用scrapy-aioredis的调度
        'SCHEDULER': 'aioscrapy.core.scheduler.Scheduler',
        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.core.scheduler.queue.PriorityQueue',
        'DUPEFILTER_CLASS': 'aioscrapy.core.scheduler.dupefilter.RFPDupeFilter',
        # 'SCHEDULER_SERIALIZER': 'aioscrapy.core.scheduler.serializ.JsonCompat',
        'REDIS_ARGS': {
            'url': 'redis://:erpteam_redis@192.168.5.216:6381/9',
            'max_connections': 2,
        },
    }

    start_urls = ['https://hanyu.baidu.com/zici/s?wd=王&query=王']

    async def parse(self, response):
        img_url = response.xpath('//img[@class="bishun"]/@data-gif').get()
        chinese_character = re.search('wd=(.*?)&', response.url).group(1)
        item = {
            'img_url': img_url,
            'response_url': response.url,
            'chinese_character': unquote(chinese_character)
        }
        yield item

        # new_character = response.xpath('//a[@class="img-link"]/@href').getall()
        # for character in new_character:
        #     new_url = 'https://hanyu.baidu.com/zici' + character
        #     yield Request(new_url, callback=self.parse, dont_filter=True)

    # def spider_idle(self):
    #     """跑完关闭爬虫"""

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    Baidu3Spider.start()
