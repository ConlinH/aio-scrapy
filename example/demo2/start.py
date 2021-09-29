import sys
import os
sys.path.append(os.path.dirname(os.getcwd()) + '/aioscrapy')

from aioscrapy.utils.tools import get_project_settings
from aioscrapy.crawler import CrawlerProcess
from baiduSpider import BaiduSpider
from baidu2Spider import Baidu2Spider
from baidu3Spider import Baidu3Spider


settings = get_project_settings()
cp = CrawlerProcess(settings)
cp.crawl(BaiduSpider)
cp.crawl(Baidu2Spider)
cp.crawl(Baidu3Spider)
cp.start()



