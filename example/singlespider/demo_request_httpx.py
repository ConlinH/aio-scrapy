from aioscrapy import Request, logger, Spider


class DemoHttpxSpider(Spider):
    name = 'DemoHttpxSpider'
    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        # CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        # DOWNLOAD_HANDLERS={
        #     'http': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
        #     'https': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
        # },
        DOWNLOAD_HANDLERS_TYPE="httpx",
        HTTPX_ARGS={'http2': True},     # 传递给httpx.AsyncClient构造函数的参数
        FIX_HTTPX_HEADER=True,  # 修复响应中的非标准HTTP头
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
            yield Request(f"https://quotes.toscrape.com/{next_page}", callback=self.parse)

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoHttpxSpider.start()
