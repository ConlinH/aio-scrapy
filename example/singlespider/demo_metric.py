import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider

logger = logging.getLogger(__name__)


class DemoMetricSpider(Spider):
    name = 'DemoMetricSpider'
    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        # CONCURRENT_REQUESTS=1,
        LOG_LEVEL='DEBUG',
        CLOSE_SPIDER_ON_IDLE=True,


        EXTENSIONS={
            'aioscrapy.libs.extensions.metric.Metric': 0,
        },

        # http(侵入式) 使用http协议将监控指标写入influxdb2
        # METRIC_INFLUXDB_URL="http://127.0.0.1:8086/api/v2/write?org=spiderman&bucket=spider-metric&precision=ns",
        # METRIC_INFLUXDB_TOKEN="YequFPGDEuukHUG9l8l2nlaatufGQK_UOD7UBpo3KvB8jIg5-cFa89GLXYfgk76M2sHvEtERpAXK7_fMNsBjAA==",

        # log + vector(非侵入式) 将监控指标写入单独的日志文件，利用vector收集日志写入influxdb2
        METRIC_LOG_ARGS=dict(sink='DemoMetricSpider.metric', rotation='20MB', retention=3)
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
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            # yield response.follow(next_page, self.parse)
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)

    # async def process_item(self, item):
    #     print(item)


if __name__ == '__main__':
    DemoMetricSpider.start()
