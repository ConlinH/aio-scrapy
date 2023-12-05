from aioscrapy import Request, logger, Spider


class DemoRedisProxySpider(Spider):
    """
    适用于代理池 代理池的实现参考 https://github.com/Python3WebSpider/ProxyPool
    """
    name = 'DemoRedisProxySpider'
    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        LOG_LEVEL='DEBUG',
        CLOSE_SPIDER_ON_IDLE=True,
        # 代理配置
        USE_PROXY=True,  # 是否开启代理
        PROXY_HANDLER='aioscrapy.proxy.redis.RedisProxy',  # 代理类的加载路径
        PROXY_QUEUE_ALIAS='proxy',  # 代理的redis队列别名
        PROXY_KEY='proxies:universal',  # 代理的key名, 使用redis的ZSET结构存储代理
        PROXY_MAX_COUNT=10,  # 最多缓存到内存中的代理个数
        PROXY_MIN_COUNT=1,  # 最小缓存到内存中的代理个数
        REDIS_ARGS={  # 代理存放的redis位置
            'proxy': {
                'url': 'redis://username:password@192.168.234.128:6379/2',
                'max_connections': 2,
                'timeout': None,
                'retry_on_timeout': True,
                'health_check_interval': 30,
            }
        }
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
