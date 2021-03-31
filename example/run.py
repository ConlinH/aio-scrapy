from aioscrapy.utils.tools import get_project_settings
from aioscrapy.crawler import CrawlerProcess
from baiduSpider import BaiduSpider
from baidu2Spider import Baidu2Spider

settings = get_project_settings()
cp = CrawlerProcess(settings)
cp.add_crawler(BaiduSpider)
cp.add_crawler(Baidu2Spider)
cp.start()
