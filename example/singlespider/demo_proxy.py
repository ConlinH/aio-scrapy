from aioscrapy import Request, logger, Spider


class DemoProxySpider(Spider):
    """
    适用于隧道代理
    """
    name = 'DemoProxySpider'
    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        LOG_LEVEL='DEBUG',
        CLOSE_SPIDER_ON_IDLE=True,
    )

    start_urls = ['https://quotes.toscrape.com']

    @staticmethod
    async def process_request(request, spider):
        """ request middleware """
        # 添加代理 适用于隧道代理
        request.meta['proxy'] = 'http://127.0.0.1:7890'

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
    DemoProxySpider.start()
