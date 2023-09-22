import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class DemoPGSpider(Spider):
    name = 'DemoPGSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        # 'CONCURRENT_REQUESTS': 1,
        # 'LOG_LEVEL': 'INFO'
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.RFPDupeFilter',
        "CLOSE_SPIDER_ON_IDLE": True,
        # mongo parameter
        "PG_ARGS": {
            'default': {
                'user': 'user',
                'password': 'password',
                'database': 'spider_db',
                'host': '127.0.0.1'
            }
        },
        "ITEM_PIPELINES": {
            'aioscrapy.libs.pipelines.sink.PGPipeline': 100,
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
                '__pg__': {
                    'db_alias': 'default',  # 要存储的PostgreSQL, 参数“PG_ARGS”的key
                    'table_name': 'spider_db.article',  # 要存储的schema和表名字，用.隔开

                    # 写入数据库的方式：
                    # insert：普通写入 出现主键或唯一键冲突时抛出异常
                    # update_insert：更新插入 出现on_conflict指定的冲突时，更新写入
                    # ignore_insert：忽略写入 写入时出现冲突 丢掉该条数据 不抛出异常
                    'insert_type': 'update_insert',
                    'on_conflict': 'id',     # update_insert方式下的约束
                }
            }
        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            # yield response.follow(next_page, self.parse)
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoPGSpider.start()
