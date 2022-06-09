import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class BaiduSpider(Spider):
    name = 'baidu'

    start_urls = ['https://hanyu.baidu.com/zici/s?wd=黄&query=黄']

    @staticmethod
    async def process_request(request, spider):
        request.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'
        }
        return request

    @staticmethod
    async def process_response(request, response, spider):
        if response.status in [401, 403]:
            return request
        return response

    @staticmethod
    async def process_exception(request, exception, spider):
        raise exception

    async def parse(self, response):
        img_url = response.xpath('//img[@class="bishun"]/@data-gif').get()
        response.meta.get('save_table_name', 'coupang_monitor_detail')
        item = {
            'save_table_name': 'baidu',  # 要存储的表名字
            'save_insert_type': 'insert',   # 存储的方式
            'save_db_alias': ['default'],     # 要存储的mysql的库

            # 下面为存储的字段
            'img_url': img_url,
            # 'response_url': response.url,
            # 'chinese_character': unquote(chinese_character)
        }
        yield item

        new_character = response.xpath('//a[@class="img-link"]/@href').getall()
        for character in new_character:
            new_url = 'https://hanyu.baidu.com/zici' + character
            yield Request(new_url, callback=self.parse, dont_filter=True)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    BaiduSpider.start()
