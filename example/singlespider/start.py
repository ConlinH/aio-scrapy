import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))

from aioscrapy.crawler import CrawlerProcess
from demo_memory import DemoMemorySpider
from demo_redis import DemoRedisSpider
from demo_rabbitmq import DemoRabbitmqSpider


cp = CrawlerProcess()
cp.crawl(DemoMemorySpider)
cp.crawl(DemoRedisSpider)
cp.crawl(DemoRabbitmqSpider)
cp.start()

