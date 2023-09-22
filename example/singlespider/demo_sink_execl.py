import datetime
import logging
import time

from aioscrapy import Request
from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class DemoExeclSpider(Spider):
    name = 'DemoExeclSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        # 'CONCURRENT_REQUESTS': 1,
        # 'LOG_LEVEL': 'INFO'
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.RFPDupeFilter',
        "CLOSE_SPIDER_ON_IDLE": True,

        "ITEM_PIPELINES": {
            'aioscrapy.libs.pipelines.sink.ExeclPipeline': 100,
        },
        "SAVE_CACHE_NUM": 1000,  # 每次存储1000条
        "SAVE_CACHE_INTERVAL": 10,  # 每次10秒存储一次
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
                '__execl__': {
                    'filename': 'article',  # 文件名 或 存储的路径及文件名 如：D:\article.xlsx
                    'sheet': 'sheet1',  # 表格的sheet名字 不指定默认为sheet1

                    # 'img_fields': ['img'],    # 图片字段 当指定图片字段时 自行下载图片 并保存到表格里
                    # 'img_size': (100, 100)    # 指定图片大小时 自动将图片转换为指定大小
                }
            }

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoExeclSpider.start()
