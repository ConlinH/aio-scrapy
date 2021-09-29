import sys
import os
sys.path.append(os.path.dirname(os.getcwd()) + '/aioscrapy')

from aioscrapy.utils.tools import get_project_settings
from aioscrapy.crawler import CrawlerProcess
from demo_scrapy import DemoScrapySpider
from demo_scrapy_redis import DemoScrapyRedisSpider
from demo_aioscrapy_redis import DemoAioscrapyRedisSpider


settings = get_project_settings()
cp = CrawlerProcess(settings)
cp.crawl(DemoScrapySpider)
cp.crawl(DemoScrapyRedisSpider)
cp.crawl(DemoAioscrapyRedisSpider)
cp.start()



