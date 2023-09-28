from aioscrapy import Spider, logger, Request


class DemoMongoSpider(Spider):
    name = 'DemoMongoSpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        # 'CONCURRENT_REQUESTS': 1,
        # 'LOG_LEVEL': 'INFO'
        # 'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.RFPDupeFilter',
        "CLOSE_SPIDER_ON_IDLE": True,
        # mongo parameter
        "MONGO_ARGS": {
            'default': {
                'host': 'mongodb://root:root@192.168.234.128:27017',
                'db': 'test',
            }
        },
        "ITEM_PIPELINES": {
            'aioscrapy.libs.pipelines.sink.MongoPipeline': 100,
        },
        "SAVE_CACHE_NUM": 1000,      # 每次存储1000条
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
                '__mongo__': {
                    'db_alias': 'default',  # 要存储的mongo, 参数“MONGO_ARGS”的key
                    'table_name': 'article',  # 要存储的表名字
                    # 'db_name': 'xxx',     # 要存储的mongo的库名， 不指定则默认为“MONGO_ARGS”中的“db”值
                }
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            # yield response.follow(next_page, self.parse)
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoMongoSpider.start()
