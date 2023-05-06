import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class DemoMysqlSpider(Spider):
    name = 'DemoMysqlSpider'
    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # OWNLOAD_DELAY=3,
        # ANDOMIZE_DOWNLOAD_DELAY=True,
        # ONCURRENT_REQUESTS=1,
        # OG_LEVEL='INFO',
        # UPEFILTER_CLASS='aioscrapy.dupefilters.disk.RFPDupeFilter',
        CLOSE_SPIDER_ON_IDLE=True,
        # mysql parameter
        MYSQL_ARGS={
            'default': {
                'host': '127.0.0.1',
                'user': 'root',
                'password': 'root',
                'port': 3306,
                'charset': 'utf8mb4',
                'db': 'test',
            },
        },
        ITEM_PIPELINES={
            'aioscrapy.libs.pipelines.sink.MysqlPipeline': 100,
        },
        SAVE_CACHE_NUM=1000,  # 每次存储1000条
        SAVE_CACHE_INTERVAL=10,  # 每次10秒存储一次
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

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'save_table_name': 'article',  # 要存储的表名字
                'save_db_alias': 'default',  # 要存储的mongo, 参数“MYSQL_ARGS”的key
                # 'save_db_name': 'xxx',     # 要存储的mongo的库名， 不指定则默认为“MYSQL_ARGS”中的“db”值

                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            # yield response.follow(next_page, self.parse)
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoMysqlSpider.start()
