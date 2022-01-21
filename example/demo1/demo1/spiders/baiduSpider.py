import re
from urllib.parse import unquote
import logging

from scrapy import Request
from aioscrapy.spiders import AioSpider

logger = logging.getLogger(__name__)


class BaiduSpider(AioSpider):
    name = 'baidu'

    start_urls = ['https://hanyu.baidu.com/zici/s?wd=王&query=王']

    async def parse(self, response):
        img_url = response.xpath('//img[@class="bishun"]/@data-gif').get()
        chinese_character = re.search('wd=(.*?)&', response.url).group(1)
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

    # def spider_idle(self):
    #     """跑完关闭爬虫"""

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    BaiduSpider.start()
