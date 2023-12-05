from aioscrapy import Request, Spider, logger
from aioscrapy.proxy.redis import AbsProxy


class MyProxy(AbsProxy):
    """
    TODO: 根据实际情况重写AbsProxy部分方法 实现自己的代理逻辑
    """

    def __init__(
            self,
            settings,
    ):
        super().__init__(settings)

    @classmethod
    async def from_crawler(cls, crawler) -> AbsProxy:
        settings = crawler.settings
        return cls(
            settings
        )

    async def get(self) -> str:
        # TODO: 实现ip获取逻辑
        logger.warning("未实现ip代理逻辑")
        return 'http://127.0.0.1:7890'


class DemoRedisProxySpider(Spider):
    """
    自定义代理 自己实现代理相关逻辑
    """
    name = 'DemoRedisProxySpider'
    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        LOG_LEVEL='DEBUG',
        CLOSE_SPIDER_ON_IDLE=True,

        # 代理配置
        USE_PROXY=True,  # 是否开启代理 默认为False
        PROXY_HANDLER='demo_proxy_self.MyProxy',  # 代理类的加载路径 根据情况自己实现一个代理类（可参考RedisProxy类）
    )

    start_urls = ['https://quotes.toscrape.com']

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

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoRedisProxySpider.start()
