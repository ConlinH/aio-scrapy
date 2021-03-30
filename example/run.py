from aioscrapy.crawler import CrawlerProcess
from baiduSpider import BaiduSpider
from baidu2Spider import Baidu2Spider

cp = CrawlerProcess()
cp.add_crawler(BaiduSpider)
cp.add_crawler(Baidu2Spider)
cp.start()
